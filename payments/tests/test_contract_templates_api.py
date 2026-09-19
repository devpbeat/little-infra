"""Contract template management (staff) and document rendering tests."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.contracts.models import Contract, ContractTemplate
from tests.conftest import authed_client


@pytest.fixture
def staff_client(db):
    User.objects.create_user("operator", password="pw", is_staff=True)
    client = APIClient()
    client.post("/api/v1/auth/login", {"username": "operator", "password": "pw"}, format="json")
    return client


class TestTemplateCrud:
    def test_staff_creates_and_previews_template(self, staff_client):
        response = staff_client.post(
            "/api/v1/contract-templates/",
            {
                "name": "SaaS standard",
                "deal_type": "saas_subscription",
                "body": "# Contract\nClient: {{client_name}} — Fee: Gs. {{monthly_fee_pyg}}",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["is_approved"] is False

        preview = staff_client.get(
            f"/api/v1/contract-templates/{response.data['id']}/preview/"
        )
        assert preview.status_code == 200
        assert "ACME S.A." in preview.data["markdown"]
        assert "{{" not in preview.data["markdown"]

    def test_generate_creates_unapproved_draft(self, staff_client, monkeypatch):
        from apps.contracts import views

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(
            "adapters.anthropic_gen.generator.generate_template_body",
            lambda **kw: f"# Contrato\nCliente: {{{{client_name}}}} ({kw['deal_type']})",
        )
        # The view imports lazily from the module path above; also patch a
        # direct reference if one exists.
        assert views  # imported for monkeypatch scoping clarity

        response = staff_client.post(
            "/api/v1/contract-templates/generate/",
            {"name": "AI SaaS draft", "deal_type": "saas_subscription"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["is_approved"] is False
        assert "{{client_name}}" in response.data["body"]

    def test_generate_without_api_key_is_503(self, staff_client, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        response = staff_client.post(
            "/api/v1/contract-templates/generate/",
            {"name": "x", "deal_type": "saas_subscription"},
            format="json",
        )
        assert response.status_code == 503

    def test_api_key_cannot_touch_templates(self, provisioned_app):
        _app, raw = provisioned_app
        client = authed_client(raw)
        assert client.get("/api/v1/contract-templates/").status_code in (401, 403)
        assert client.post(
            "/api/v1/contract-templates/", {"name": "x"}, format="json"
        ).status_code in (401, 403)


class TestContractDocument:
    def _signed_up_contract(self, raw_key) -> Contract:
        authed_client(raw_key).post(
            "/api/v1/customers/signup",
            {"external_ref": "cust-doc", "display_name": "Ada Lovelace"},
            format="json",
        )
        return Contract.objects.get(customer__external_ref="cust-doc")

    def test_app_renders_document_from_approved_template(self, provisioned_app):
        app, raw = provisioned_app
        contract = self._signed_up_contract(raw)
        ContractTemplate.objects.filter(pk=contract.template_id).update(
            body="Client {{client_name}} of {{app_name}} pays Gs. {{monthly_fee_pyg}}.",
            is_approved=True,
        )

        response = authed_client(raw).get(f"/api/v1/contracts/{contract.pk}/document/")

        assert response.status_code == 200
        assert "Ada Lovelace" in response.data["markdown"]
        assert app.name in response.data["markdown"]
        assert "{{" not in response.data["markdown"]

    def test_unapproved_template_body_is_409(self, provisioned_app):
        _app, raw = provisioned_app
        contract = self._signed_up_contract(raw)
        ContractTemplate.objects.filter(pk=contract.template_id).update(
            body="Draft {{client_name}}", is_approved=False
        )

        assert (
            authed_client(raw).get(f"/api/v1/contracts/{contract.pk}/document/").status_code
            == 409
        )

    def test_send_creates_envelope_and_transitions(self, provisioned_app, monkeypatch):
        from payments_core.ports.contract_signer import EnvelopeResult

        _app, raw = provisioned_app
        client = authed_client(raw)
        client.post(
            "/api/v1/customers/signup",
            {"external_ref": "cust-sign", "display_name": "Ada", "email": "ada@example.com"},
            format="json",
        )
        contract = Contract.objects.get(customer__external_ref="cust-sign")
        ContractTemplate.objects.filter(pk=contract.template_id).update(
            body="Contrato de {{client_name}}", is_approved=True
        )

        class StubSigner:
            def create_envelope(self, request):
                assert "Ada" in request.document_html
                return EnvelopeResult(
                    envelope_id="sub-9", raw={}, signing_url="https://sign.test/s/abc"
                )

        monkeypatch.setattr(
            "payments_core.gateway.get_contract_signer", lambda: StubSigner()
        )

        response = client.post(f"/api/v1/contracts/{contract.pk}/send/")

        assert response.status_code == 200
        assert response.data["signing_url"] == "https://sign.test/s/abc"
        contract.refresh_from_db()
        assert contract.status == "sent"
        assert contract.external_envelope_id == "sub-9"

    def test_templatize_uploads_markdown(self, staff_client, monkeypatch):
        import io

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(
            "adapters.anthropic_gen.generator.templatize_document",
            lambda **kw: "# Contrato\n{{client_name}} firma este documento.",
        )
        upload = io.BytesIO(b"# Original\nACME SA firma este documento.")
        upload.name = "old-contract.md"

        response = staff_client.post(
            "/api/v1/contract-templates/templatize/",
            {"file": upload, "name": "Imported SaaS", "deal_type": "saas_subscription"},
            format="multipart",
        )

        assert response.status_code == 201
        assert response.data["is_approved"] is False
        assert "{{client_name}}" in response.data["body"]

    def test_builtin_click_sign_full_ceremony(self, provisioned_app, settings):
        settings.CONTRACT_SIGNER = "adapters.builtin_sign.signer.BuiltinClickSigner"
        _app, raw = provisioned_app
        client = authed_client(raw)
        client.post(
            "/api/v1/customers/signup",
            {"external_ref": "cust-click", "display_name": "Ada", "email": "ada@example.com"},
            format="json",
        )
        contract = Contract.objects.get(customer__external_ref="cust-click")
        ContractTemplate.objects.filter(pk=contract.template_id).update(
            body="Contrato de {{client_name}}", is_approved=True
        )

        sent = client.post(f"/api/v1/contracts/{contract.pk}/send/")
        assert sent.status_code == 200
        token = sent.data["envelope_id"]
        assert token in sent.data["signing_url"]

        from rest_framework.test import APIClient

        anon = APIClient()
        # Public read shows the FROZEN document.
        doc = anon.get(f"/api/v1/public/contract-signing/{token}/")
        assert doc.status_code == 200
        assert doc.data["markdown"] == "Contrato de Ada"

        # Template edits after send must not change what is signed.
        ContractTemplate.objects.filter(pk=contract.template_id).update(body="OTRO TEXTO")
        assert (
            anon.get(f"/api/v1/public/contract-signing/{token}/").data["markdown"]
            == "Contrato de Ada"
        )

        signed = anon.post(
            f"/api/v1/public/contract-signing/{token}/sign/",
            {"signer_name": "Ada Lovelace", "signer_document_id": "1234567", "accepted": True},
            format="json",
        )
        assert signed.status_code == 200
        contract.refresh_from_db()
        assert contract.status == "signed"
        assert contract.signed_at is not None
        assert contract.signer_document_id == "1234567"
        assert contract.signed_document == "Contrato de Ada"

        # Replay is a friendly no-op; missing acceptance is rejected.
        assert (
            anon.post(
                f"/api/v1/public/contract-signing/{token}/sign/",
                {"signer_name": "x", "signer_document_id": "1", "accepted": True},
                format="json",
            ).data["detail"]
            == "Already signed."
        )
        assert anon.get("/api/v1/public/contract-signing/wrong-token/").status_code == 404

    def test_sign_requires_acceptance_fields(self, provisioned_app, settings):
        settings.CONTRACT_SIGNER = "adapters.builtin_sign.signer.BuiltinClickSigner"
        _app, raw = provisioned_app
        client = authed_client(raw)
        client.post(
            "/api/v1/customers/signup",
            {"external_ref": "cust-click2", "email": "ada2@example.com"},
            format="json",
        )
        contract = Contract.objects.get(customer__external_ref="cust-click2")
        ContractTemplate.objects.filter(pk=contract.template_id).update(
            body="Doc {{client_name}}", is_approved=True
        )
        token = client.post(f"/api/v1/contracts/{contract.pk}/send/").data["envelope_id"]

        from rest_framework.test import APIClient

        response = APIClient().post(
            f"/api/v1/public/contract-signing/{token}/sign/",
            {"signer_name": "Ada", "accepted": False},
            format="json",
        )
        assert response.status_code == 400
        contract.refresh_from_db()
        assert contract.status == "sent"

    def test_cross_tenant_document_denied(self, provisioned_app, other_provisioned_app):
        _app_a, key_a = provisioned_app
        _app_b, key_b = other_provisioned_app
        contract_b = self._signed_up_contract(key_b)

        assert (
            authed_client(key_a).get(f"/api/v1/contracts/{contract_b.pk}/document/").status_code
            == 404
        )
