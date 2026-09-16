import json

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.subscriptions.models import Subscription
from payments_core.auth import ScopedByAppMixin
from payments_core.gateway import get_payment_gateway
from payments_core.ports.payment_gateway import ChargeRequest

from .models import Payment, WebhookEvent
from .serializers import PaymentInitiationSerializer, PaymentSerializer
from .services import process_webhook_status


class PaymentInitiationView(APIView):
    """`POST /api/v1/payments` (spec: payment-processing, "Payment Initiation").

    Creates a `Payment` row scoped to the caller's app (via the requested
    Subscription, which is scoped by `customer__app`) and asks the
    configured `PaymentGateway` to create a charge for it. The gateway's
    `checkout_url` (which may carry a QR payload, per the spike — the SDK
    does not parse or guarantee a separate `qr_payload` field, see
    sdd/payments-microservice/spike-pagopar finding (a)) is returned as-is;
    this service does not attempt to render or interpret it.
    """

    def post(self, request):
        serializer = PaymentInitiationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = get_object_or_404(
            Subscription.objects.select_related("customer", "plan"),
            pk=serializer.validated_data["subscription"],
            customer__app=request.app,
        )
        customer = subscription.customer

        payment = Payment.objects.create(
            subscription=subscription,
            amount_pyg=subscription.plan.price_pyg,
            gateway="pagopar",
        )

        gateway = get_payment_gateway()
        charge_request = ChargeRequest(
            order_id=str(payment.pk),
            amount_pyg=payment.amount_pyg,
            description=f"{subscription.plan.name} — {customer.app.name}",
            buyer_name=customer.display_name or customer.external_ref,
            buyer_email=customer.email,
            # Customer has no document/phone fields (design §3 does not
            # define them) — Pagopar's Buyer payload requires both.
            # Placeholder values are used and documented here as a known
            # gap; a follow-up slice should either add these fields to
            # Customer or confirm Pagopar accepts blanks in practice.
            buyer_document=getattr(customer, "tax_id", "") or "0000000",
            buyer_phone=getattr(customer, "phone", "") or "000000000",
        )
        try:
            result = gateway.create_charge(charge_request)
        except Exception:
            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])
            raise

        payment.gateway_order_id = result.gateway_order_id
        payment.checkout_url = result.checkout_url or ""
        payment.save(update_fields=["gateway_order_id", "checkout_url", "updated_at"])

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(ScopedByAppMixin, viewsets.ReadOnlyModelViewSet):
    """`GET /payments`, `/payments/{id}` — history/status (design §5)."""

    serializer_class = PaymentSerializer
    queryset = Payment.objects.select_related("subscription__customer").order_by("-created_at")
    app_scope_field = "subscription__customer__app"


class PagoparWebhookView(APIView):
    """`POST /api/v1/webhooks/pagopar` (spec: payment-processing, "Webhook Idempotency").

    Unauthenticated by API key — Pagopar does not hold one of our keys.
    Authenticity instead rests entirely on `PaymentGateway.verify_webhook`'s
    gateway-signature check (see `adapters/pagopar/signature.py`'s loud
    UNCONFIRMED-algorithm warning, and its fail-closed behavior when
    `PAGOPAR_PRIVATE_KEY` is unset).

    Design §5 layered security, items (3)-(5) implemented here:
    persist `WebhookEvent` BEFORE any state change (even for a payload that
    fails signature verification, for forensics), and rely on the
    `(gateway, event_id)` unique constraint as the idempotency gate — an
    `IntegrityError` means "already processed", answered with 200 and no
    side effects rather than an error (spec: "Duplicate/replayed callback").
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        gateway = get_payment_gateway()
        result = gateway.verify_webhook(dict(request.headers), request.body)

        try:
            raw_payload = json.loads(request.body) if request.body else {}
        except ValueError:
            raw_payload = {"_unparseable_body": True}

        if not result.is_valid:
            # Logged (forensics/incident review) but never actioned. No
            # unique-constraint gate here on purpose: a flood of invalid
            # signature attempts must not be able to trip the idempotency
            # constraint against a legitimate future event_id.
            WebhookEvent.objects.create(
                gateway="pagopar",
                event_id=f"invalid-{timezone.now().timestamp()}-{result.event_id or ''}",
                payload=raw_payload,
            )
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_401_UNAUTHORIZED)

        event_id = str(result.event_id or result.gateway_order_id or "")
        try:
            with transaction.atomic():
                event = WebhookEvent.objects.create(
                    gateway="pagopar", event_id=event_id, payload=raw_payload
                )
        except IntegrityError:
            # Same (gateway, event_id) already logged — replayed callback.
            # Per spec: "MUST NOT advance the subscription period again and
            # MUST return success without side effects".
            return Response({"detail": "Already processed."}, status=status.HTTP_200_OK)

        if result.gateway_order_id:
            process_webhook_status(
                gateway="pagopar",
                gateway_order_id=str(result.gateway_order_id),
                gateway_status=result.status,
            )

        event.processed_at = timezone.now()
        event.save(update_fields=["processed_at"])

        return Response({"detail": "ok"}, status=status.HTTP_200_OK)
