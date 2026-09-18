from rest_framework import permissions, serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from payments_core.auth import ScopedByAppMixin

from .models import Contract, ContractTemplate, InvalidContractTransition
from .serializers import ContractSerializer, ContractTransitionSerializer


def _markdown_to_html(markdown_text: str) -> str:
    """Markdown → simple styled HTML for e-signature document rendering."""
    import markdown as md

    body = md.markdown(markdown_text, extensions=["tables"])
    return (
        "<html><head><meta charset='utf-8'><style>"
        "body{font-family:Georgia,serif;font-size:12pt;line-height:1.5;margin:2cm;}"
        "table{border-collapse:collapse;width:100%;}td,th{border:1px solid #999;padding:6px;}"
        "</style></head><body>" + body + "</body></html>"
    )


def build_contract_context(contract: Contract) -> dict:
    """The explicit, closed set of variables a template may reference."""
    customer = contract.customer
    app = customer.app
    plan = app.default_plan
    subscription = customer.subscriptions.order_by("-created_at").first()
    return {
        "client_name": customer.display_name or customer.external_ref,
        "client_email": customer.email or "",
        "app_name": app.name,
        "plan_name": plan.name if plan else "",
        "monthly_fee_pyg": f"{plan.price_pyg:,}".replace(",", ".") if plan else "",
        "trial_days": app.trial_days,
        "trial_end": subscription.trial_end.date().isoformat()
        if subscription and subscription.trial_end
        else "",
        "contract_date": contract.created_at.date().isoformat(),
    }


class ContractViewSet(ScopedByAppMixin, viewsets.ReadOnlyModelViewSet):
    """`GET /contracts`, `/contracts/{id}`, `POST /contracts/{id}/transition`.

    Scoped one hop from `ConsumingApp` via `customer__app` — `Contract` has
    no direct `app` FK (design §3).
    """

    serializer_class = ContractSerializer
    queryset = Contract.objects.select_related("customer", "template").order_by("-created_at")
    app_scope_field = "customer__app"

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        contract = self.get_object()
        serializer = ContractTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            contract.transition_to(serializer.validated_data["status"])
        except InvalidContractTransition as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=status.HTTP_409_CONFLICT)

        return Response(ContractSerializer(contract).data)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Render the contract and create the e-signature envelope.

        Uses the configured ContractSigner (DocuSeal in production) with
        the rendered document; transitions generated→sent and returns the
        public signing link for the consuming app to surface to its
        customer.
        """
        from payments_core.gateway import get_contract_signer
        from payments_core.ports.contract_signer import EnvelopeRequest

        contract = self.get_object()
        template = contract.template
        if not template.body or not template.is_approved:
            return Response(
                {"detail": "Template has no approved body to render."},
                status=status.HTTP_409_CONFLICT,
            )
        customer = contract.customer
        if not customer.email:
            return Response(
                {"detail": "Customer has no email to send the signature request to."},
                status=status.HTTP_409_CONFLICT,
            )

        markdown_doc = template.render(build_contract_context(contract))
        html = _markdown_to_html(markdown_doc)
        signer = get_contract_signer()
        result = signer.create_envelope(
            EnvelopeRequest(
                template_reference=template.reference or template.name,
                signer_name=customer.display_name or customer.external_ref,
                signer_email=customer.email,
                document_name=f"{template.name} — {customer.display_name or customer.external_ref}",
                document_html=html,
            )
        )
        contract.external_envelope_id = result.envelope_id
        try:
            contract.transition_to("sent")
        except InvalidContractTransition as exc:
            return Response(
                {"detail": str(exc), "code": "invalid_transition"},
                status=status.HTTP_409_CONFLICT,
            )
        contract.save(update_fields=["external_envelope_id", "updated_at"])
        return Response(
            {
                "contract_id": contract.pk,
                "status": contract.status,
                "envelope_id": result.envelope_id,
                "signing_url": result.signing_url,
            }
        )

    @action(detail=True, methods=["get"])
    def document(self, request, pk=None):
        """Rendered contract document (markdown) for this contract.

        App-scoped like every contract route: a consuming app fetches this
        to show the digital contract to ITS customer (e.g. before DocuSign
        or in-app acceptance). 409s until the template has an approved body.
        """
        contract = self.get_object()
        template = contract.template
        if not template.body or not template.is_approved:
            return Response(
                {"detail": "Template has no approved body to render."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {
                "contract_id": contract.pk,
                "status": contract.status,
                "template": template.name,
                "deal_type": template.deal_type,
                "markdown": template.render(build_contract_context(contract)),
            }
        )


class ContractTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractTemplate
        fields = [
            "id",
            "name",
            "reference",
            "deal_type",
            "body",
            "is_approved",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ContractTemplateViewSet(viewsets.ModelViewSet):
    """Full CRUD over contract templates — staff sessions only.

    Machines never edit legal documents: API keys cannot reach this
    surface at all.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ContractTemplateSerializer
    queryset = ContractTemplate.objects.order_by("name")

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """AI-draft a template body with Claude (staff-triggered, reviewed).

        The draft is saved with `is_approved=False` — it renders nothing
        for real customers until a human approves it in the editor.
        """
        import os

        from adapters.anthropic_gen.generator import generate_template_body

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return Response(
                {"detail": "ANTHROPIC_API_KEY is not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        name = str(request.data.get("name") or "").strip()
        deal_type = str(request.data.get("deal_type") or "")
        instructions = str(request.data.get("instructions") or "")
        if not name or deal_type not in dict(ContractTemplate._meta.get_field("deal_type").choices):
            return Response(
                {"detail": "name and a valid deal_type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        body = generate_template_body(
            deal_type=deal_type, name=name, instructions=instructions
        )
        template = ContractTemplate.objects.create(
            name=name, deal_type=deal_type, body=body, is_approved=False
        )
        return Response(
            ContractTemplateSerializer(template).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"])
    def templatize(self, request):
        """Upload an existing contract (PDF or markdown/text) and have
        Claude convert it into a placeholder template — saved unapproved."""
        import os

        from adapters.anthropic_gen.generator import templatize_document

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return Response(
                {"detail": "ANTHROPIC_API_KEY is not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        upload = request.FILES.get("file")
        name = str(request.data.get("name") or "").strip()
        deal_type = str(request.data.get("deal_type") or "")
        if not upload or not name or deal_type not in dict(
            ContractTemplate._meta.get_field("deal_type").choices
        ):
            return Response(
                {"detail": "file, name and a valid deal_type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > 10 * 1024 * 1024:
            return Response(
                {"detail": "File too large (10 MB max)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        body = templatize_document(
            file_bytes=upload.read(), filename=upload.name, deal_type=deal_type
        )
        template = ContractTemplate.objects.create(
            name=name, deal_type=deal_type, body=body, is_approved=False
        )
        return Response(
            ContractTemplateSerializer(template).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Render the template with SAMPLE data so the editor can preview."""
        template = self.get_object()
        sample = {
            "client_name": "ACME S.A.",
            "client_email": "billing@acme.example",
            "app_name": "sample-app",
            "plan_name": "Standard Monthly",
            "monthly_fee_pyg": "350.000",
            "trial_days": 30,
            "trial_end": "2026-10-18",
            "contract_date": "2026-09-18",
        }
        return Response({"markdown": template.render(sample), "sample_context": sample})
