import json
import logging

from django.db import IntegrityError, models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import Customer
from apps.merchants.models import MerchantAccount
from apps.subscriptions.models import Subscription
from payments_core.auth import IsAuthenticatedAppOnly, ScopedByAppMixin
from payments_core.gateway import get_payment_gateway
from payments_core.merchant_credentials import credentials_for_payment, resolve_credentials
from payments_core.ports.payment_gateway import ChargeRequest

from .models import Payment, PaymentKind, PaymentStatus, WebhookEvent
from .serializers import (
    ChargeInitiationSerializer,
    PaymentInitiationSerializer,
    PaymentResultSerializer,
    PaymentSerializer,
    ProblemSerializer,
)
from .services import process_webhook_status

logger = logging.getLogger(__name__)


def gateway_for_payment(payment):
    """The adapter bound to the account `payment` settles into.

    A Flow A payment has no `merchant_account`, so it resolves with no
    explicit credentials — byte-for-byte the pre-Flow-B call, which keeps
    SaaS billing on the global env key pair.
    """
    if payment.merchant_account_id is None:
        return get_payment_gateway()
    return get_payment_gateway(credentials=credentials_for_payment(payment))


@extend_schema(
    request=None,
    responses={
        200: PaymentResultSerializer,
        404: OpenApiResponse(ProblemSerializer, description="Unknown gateway order hash."),
    },
)
class PaymentResultView(APIView):
    """`GET /api/v1/payments/result/<gateway_order_id>` — public, minimal.

    The Pagopar checkout redirects the payer's browser here (via the
    dashboard's result page) with the order hash. Unauthenticated by
    design: the hash is an opaque, gateway-generated capability token,
    and the response exposes ONLY the payment status — no amounts, no
    customer data, nothing enumerable.

    KEPT PUBLIC FOR FLOW B, deliberately. The party who needs this route is
    the BUYER's browser coming back from Pagopar, and a plot buyer holds no
    API key — requiring one would break the return page. The order hash is
    high-entropy and gateway-generated, so it is a capability token, and the
    only thing it unlocks is a single enum. Consuming apps MUST NOT treat
    this as authoritative: the authoritative, tenant-scoped reads are
    `GET /payments/{id}` and the signed confirmation callback.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, gateway_order_id: str):
        payment = (
            Payment.objects.filter(gateway="pagopar", gateway_order_id=gateway_order_id)
            .only("status")
            .first()
        )
        if payment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": payment.status})


@extend_schema(
    request=PaymentInitiationSerializer,
    responses={
        201: OpenApiResponse(PaymentSerializer, description="New pending payment created."),
        200: OpenApiResponse(
            PaymentSerializer, description="An equivalent pending payment already existed."
        ),
        404: OpenApiResponse(ProblemSerializer, description="Subscription not found for this app."),
        502: OpenApiResponse(ProblemSerializer, description="Gateway rejected or was unreachable."),
    },
)
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

    permission_classes = [IsAuthenticatedAppOnly]

    def post(self, request):
        serializer = PaymentInitiationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = get_object_or_404(
            Subscription.objects.select_related("customer", "plan"),
            pk=serializer.validated_data["subscription"],
            customer__app=request.app,
        )
        customer = subscription.customer

        # Idempotent initiation: a retry (double-click, client timeout) must
        # reuse the open charge instead of minting a second checkout/QR for
        # the same period.
        pending = (
            Payment.objects.filter(subscription=subscription, status=PaymentStatus.PENDING)
            .exclude(gateway_order_id="")
            .order_by("-created_at")
            .first()
        )
        if pending is not None:
            return Response(PaymentSerializer(pending).data, status=status.HTTP_200_OK)

        payment = Payment.objects.create(
            app=request.app,
            kind=PaymentKind.SUBSCRIPTION,
            customer=customer,
            subscription=subscription,
            amount_pyg=subscription.plan.price_pyg,
            description=f"{subscription.plan.name} — {customer.app.name}",
            gateway="pagopar",
        )

        charge_request = ChargeRequest(
            order_id=str(payment.pk),
            amount_pyg=payment.amount_pyg,
            description=f"{subscription.plan.name} — {customer.app.name}",
            buyer_name=customer.display_name or customer.external_ref,
            buyer_email=customer.email,
            # Real customer identity when captured; documented fallbacks
            # otherwise (Pagopar's Buyer payload requires both fields).
            buyer_document=customer.tax_id or "0000000",
            buyer_phone=customer.phone or "000000000",
        )
        try:
            gateway = get_payment_gateway()
            result = gateway.create_charge(charge_request)
        except Exception as exc:
            # Surface the real misconfig/provider error instead of a bare 500
            # (mirrors the contract `send` action's 502 pattern). The UI
            # shows `detail`; the log keeps a full traceback for ops.
            logger.exception("Payment initiation failed for payment %s", payment.pk)
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": f"Payment gateway error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment.gateway_order_id = result.gateway_order_id
        payment.checkout_url = result.checkout_url or ""
        payment.save(update_fields=["gateway_order_id", "checkout_url", "updated_at"])

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(ScopedByAppMixin, viewsets.ReadOnlyModelViewSet):
    """`GET /payments`, `/payments/{id}` — history/status (design §5)."""

    serializer_class = PaymentSerializer
    queryset = Payment.objects.select_related(
        "customer", "merchant_account", "subscription"
    ).order_by("-created_at")
    # Direct FK, not `subscription__customer__app`: a Flow B payment has no
    # subscription, so the old path did not exist for it and such a row would
    # have escaped tenant scoping entirely. See `tests/test_auth_scoping.py`.
    app_scope_field = "app"

    @action(detail=True, methods=["post"])
    def refresh(self, request, pk=None):
        """Poll Pagopar for the order's current status and apply it.

        Pagopar validation circuit "Paso 3" (the merchant site queries an
        order's state) and the operator's manual fallback when a webhook
        was missed. Reuses the same state machinery as webhooks, so a
        confirmed payment stays final and confirmation extends the period
        exactly once.
        """
        payment = self.get_object()
        if not payment.gateway_order_id:
            return Response(
                {"detail": "Payment has no gateway order to query."},
                status=status.HTTP_409_CONFLICT,
            )
        gateway = gateway_for_payment(payment)
        gateway_status = gateway.get_charge_status(payment.gateway_order_id)
        process_webhook_status(
            gateway=payment.gateway,
            gateway_order_id=payment.gateway_order_id,
            gateway_status=gateway_status,
        )
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment).data)


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(description="Pagopar's `resultado` array, echoed verbatim."),
        401: OpenApiResponse(ProblemSerializer, description="Signature verification failed."),
    },
)
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
        gateway = self._gateway_for(request.body)
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
            return Response(self._echo_body(raw_payload), status=status.HTTP_200_OK)

        if result.gateway_order_id:
            process_webhook_status(
                gateway="pagopar",
                gateway_order_id=str(result.gateway_order_id),
                gateway_status=result.status,
            )

        event.processed_at = timezone.now()
        event.save(update_fields=["processed_at"])

        return Response(self._echo_body(raw_payload), status=status.HTTP_200_OK)

    @staticmethod
    def _gateway_for(body: bytes):
        """Build the adapter bound to the credentials this callback was signed with.

        A Flow B charge was created with the COLLECTING COMPANY's key pair,
        so Pagopar signs its callback with that company's private key —
        verifying against the global SaaS key would always fail. The claimed
        order id (`peek_order_id`, unverified and attacker-controlled) is
        used ONLY to select which key to check against; the signature check
        afterwards still has to prove knowledge of that key, so a forged
        hash buys an attacker nothing.
        """
        probe = get_payment_gateway()
        claimed_order_id = None
        peek = getattr(probe, "peek_order_id", None)
        if peek is not None:
            try:
                claimed_order_id = peek(body)
            except Exception:  # never let a malformed body 500 the webhook
                claimed_order_id = None
        if not claimed_order_id:
            return probe

        payment = (
            Payment.objects.filter(gateway="pagopar", gateway_order_id=claimed_order_id)
            .select_related("merchant_account")
            .first()
        )
        if payment is None or payment.merchant_account_id is None:
            return probe
        return gateway_for_payment(payment)

    @staticmethod
    def _echo_body(raw_payload):
        """Pagopar's validation circuit ("Paso 2") requires the response
        body to be the `resultado` array echoed back verbatim. For payloads
        without one (e.g. the fake gateway in tests), keep a plain ok."""
        resultado = raw_payload.get("resultado") if isinstance(raw_payload, dict) else None
        if isinstance(resultado, list):
            return resultado
        return {"detail": "ok"}

@extend_schema(
    request=ChargeInitiationSerializer,
    responses={
        201: OpenApiResponse(
            PaymentSerializer,
            description="Charge created (or re-issued after a previous failure). "
            "Send the buyer to `checkout_url`.",
        ),
        200: OpenApiResponse(
            PaymentSerializer,
            description="Idempotent replay: a payment for this `external_ref` already "
            "exists with the same amount. Reuse its `checkout_url`.",
        ),
        400: OpenApiResponse(
            ProblemSerializer,
            description="Validation error, or `merchant_ref` unknown/inactive/uncredentialed "
            "for this app.",
        ),
        409: OpenApiResponse(
            ProblemSerializer,
            description="`external_ref` already exists with a DIFFERENT `amount_pyg`.",
        ),
        502: OpenApiResponse(ProblemSerializer, description="Gateway rejected or was unreachable."),
    },
)
class ChargeInitiationView(APIView):
    """`POST /api/v1/charges` — Flow B: a tenant charges its OWN buyer.

    Flow A (`POST /api/v1/payments`) charges a SaaS subscription into the
    SaaS owner's Pagopar account. This endpoint charges an arbitrary positive
    PYG amount on behalf of one of the caller's own customers, and settles it
    into the COLLECTING COMPANY's merchant account. `merchant_ref` is
    REQUIRED and has no default: running buyer payments on the global key
    pair would pool every company's money into the SaaS owner's account, so a
    missing, unknown, inactive or uncredentialed merchant account is a hard
    400 — never a silent fallback.

    IDEMPOTENT on `(app, external_ref)` — the caller's own reference for the
    thing being paid for. A double-clicked "pay" button or a retried timeout
    returns the SAME pending payment (200) instead of creating a second
    Pagopar order. A payment that never reached a terminal success (failed,
    expired, or never got a gateway order) is re-issued on the SAME row
    (201), so a gateway outage does not permanently burn the reference.
    A repeat with a DIFFERENT amount is a 409: same reference, different
    money is a caller bug, and guessing which amount is right is worse than
    refusing.
    """

    permission_classes = [IsAuthenticatedAppOnly]
    serializer_class = ChargeInitiationSerializer

    def post(self, request):
        serializer = ChargeInitiationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        merchant = self._resolve_merchant(request.app, data.get("merchant_ref") or "")
        external_ref = data["external_ref"]

        if Payment.objects.filter(app=request.app, external_ref=external_ref).exists():
            return self._reuse_or_retry(request.app, data, merchant)

        customer = self._resolve_customer(request.app, data)
        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    app=request.app,
                    kind=PaymentKind.ONE_OFF,
                    customer=customer,
                    merchant_account=merchant,
                    external_ref=external_ref,
                    description=data["description"],
                    amount_pyg=data["amount_pyg"],
                    gateway="pagopar",
                )
        except IntegrityError:
            # Lost the race against a concurrent identical request: the
            # unique (app, external_ref) index is the real idempotency gate,
            # not the `exists()` check above.
            return self._reuse_or_retry(request.app, data, merchant)

        return self._create_gateway_order(payment, customer, merchant)

    def _reuse_or_retry(self, app, data, merchant):
        """Decide and act on an ALREADY-EXISTING payment for this external_ref.

        Everything from the status check to the gateway call happens while
        holding `SELECT ... FOR UPDATE` on that one row. Without the lock, two
        simultaneous retries of a previously-failed charge would both read
        `is_retryable=True`, both ask Pagopar for an order, and the second
        `save()` would silently discard the first order's `gateway_order_id` —
        leaving a real, un-recorded charge against the buyer. The lock
        serializes them, so the loser re-reads a now-PENDING row and gets the
        winner's checkout URL instead of creating a second order.

        Yes, this holds a row lock across an outbound HTTP call (bounded by the
        gateway client's own timeout). The contention is a single payment row
        that by definition only one buyer is paying, and the alternative is
        double-charging that buyer.
        """
        external_ref = data["external_ref"]
        with transaction.atomic():
            payment = (
                Payment.objects.select_for_update(of=("self",))
                .select_related("customer", "merchant_account")
                .get(app=app, external_ref=external_ref)
            )
            if payment.amount_pyg != data["amount_pyg"]:
                return Response(
                    {
                        "detail": (
                            f"external_ref '{external_ref}' already exists with amount "
                            f"{payment.amount_pyg} PYG; refusing to re-charge it as "
                            f"{data['amount_pyg']} PYG."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if not payment.is_retryable:
                return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)

            customer = self._resolve_customer(app, data)
            payment.merchant_account = merchant
            payment.description = data["description"]
            payment.customer = customer
            payment.status = PaymentStatus.PENDING
            payment.save(
                update_fields=[
                    "merchant_account",
                    "description",
                    "customer",
                    "status",
                    "updated_at",
                ]
            )
            return self._create_gateway_order(payment, customer, merchant)

    @staticmethod
    def _resolve_merchant(app, merchant_ref: str):
        """The merchant account the money settles into. Never None, never global."""
        merchant_ref = merchant_ref.strip()
        if not merchant_ref:
            raise ValidationError(
                {"merchant_ref": "This field is required and may not be blank."}
            )
        merchant = MerchantAccount.objects.filter(
            app=app, external_ref=merchant_ref, gateway="pagopar"
        ).first()
        if merchant is None or not merchant.is_active:
            # Scoped by `app`, so another tenant's merchant_ref is simply
            # not found — a tenant can never collect into a foreign account.
            raise ValidationError(
                {"merchant_ref": f"No active merchant account '{merchant_ref}' for this app."}
            )
        if not merchant.has_credentials:
            raise ValidationError(
                {
                    "merchant_ref": (
                        f"Merchant account '{merchant_ref}' has no gateway credentials "
                        "configured; refusing to charge into the wrong account."
                    )
                }
            )
        return merchant

    @staticmethod
    def _resolve_customer(app, data):
        """Get or create the buyer by the caller's own reference.

        A plot buyer is NOT a SaaS signup: no contract, no subscription, no
        trial — `customers/signup` would create all three and would fail for
        an app with no `contract_template`/`default_plan`. Created here so
        yvyreta needs exactly one call per charge.
        """
        buyer = data.get("buyer") or {}
        customer, created = Customer.objects.get_or_create(
            app=app,
            external_ref=data["customer_ref"],
            defaults={
                "display_name": buyer.get("name", ""),
                "email": buyer.get("email", ""),
                "tax_id": buyer.get("document", ""),
                "phone": buyer.get("phone", ""),
            },
        )
        if not created:
            # Buyer details may legitimately change between installments;
            # fill blanks without clobbering what the tenant already stored.
            updates = {
                "display_name": buyer.get("name", ""),
                "email": buyer.get("email", ""),
                "tax_id": buyer.get("document", ""),
                "phone": buyer.get("phone", ""),
            }
            changed = [
                field
                for field, value in updates.items()
                if value and getattr(customer, field) != value
            ]
            for field in changed:
                setattr(customer, field, updates[field])
            if changed:
                customer.save(update_fields=changed)
        return customer

    @staticmethod
    def _create_gateway_order(payment, customer, merchant):
        # F() rather than read-modify-write: the increment must not be lost if
        # anything ever reaches here without the row lock `_reuse_or_retry`
        # takes.
        Payment.objects.filter(pk=payment.pk).update(
            charge_attempts=models.F("charge_attempts") + 1, updated_at=timezone.now()
        )
        payment.refresh_from_db(fields=["charge_attempts"])
        # Pagopar keys its side on the commerce order reference; a retry under
        # the same external_ref must not reuse a reference Pagopar already saw.
        order_id = (
            str(payment.pk)
            if payment.charge_attempts <= 1
            else f"{payment.pk}-{payment.charge_attempts}"
        )
        charge_request = ChargeRequest(
            order_id=order_id,
            amount_pyg=payment.amount_pyg,
            description=payment.description,
            buyer_name=customer.display_name or customer.legal_name or customer.external_ref,
            buyer_email=customer.email,
            buyer_document=customer.tax_id or "0000000",
            buyer_phone=customer.phone or "000000000",
        )
        try:
            gateway = get_payment_gateway(credentials=resolve_credentials(merchant=merchant))
            result = gateway.create_charge(charge_request)
        except Exception as exc:
            logger.exception("Charge initiation failed for payment %s", payment.pk)
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": f"Payment gateway error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment.gateway_order_id = result.gateway_order_id
        payment.checkout_url = result.checkout_url or ""
        payment.save(update_fields=["gateway_order_id", "checkout_url", "updated_at"])
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
