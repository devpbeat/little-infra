"""`POST /api/v1/webhooks/pagopar` tests (Slice E2, spec: payment-processing
"Webhook Idempotency and Failure Handling").

Uses `FakePaymentGateway` (the default `settings.PAYMENT_GATEWAY` under
test) whose `verify_webhook` passes payload fields straight through —
tests craft payloads with `status` values already matching `ChargeStatus`
strings, which is what a real, verified Pagopar payload would resolve to
after `PagoparAdapter.verify_webhook`'s status mapping.
"""

import json

import pytest
from django.utils import timezone

from apps.billing.models import Payment, PaymentStatus, WebhookEvent
from apps.customers.models import Customer
from apps.subscriptions.models import Subscription, SubscriptionStatus

WEBHOOK_URL = "/api/v1/webhooks/pagopar"


@pytest.fixture
def customer(db, provisioned_app):
    app, _raw_key = provisioned_app
    return Customer.objects.create(app=app, external_ref="cust-1", display_name="Ada Lovelace")


@pytest.fixture
def subscription(db, customer, plan):
    return Subscription.start_trial(customer, plan)


@pytest.fixture
def pending_payment(db, subscription):
    return Payment.objects.create(
        subscription=subscription,
        amount_pyg=subscription.plan.price_pyg,
        gateway="pagopar",
        gateway_order_id="fake-order-1",
        status=PaymentStatus.PENDING,
    )


def _payload(gateway_order_id: str, status: str, event_id: str = "evt-1") -> bytes:
    return json.dumps(
        {"gateway_order_id": gateway_order_id, "status": status, "event_id": event_id}
    ).encode()


class TestWebhookConfirmation:
    def test_confirms_payment_and_extends_subscription_period(self, api_client, pending_payment):
        subscription = pending_payment.subscription
        assert subscription.status == SubscriptionStatus.TRIALING
        assert subscription.current_period_end is None

        response = api_client.post(
            WEBHOOK_URL,
            data=_payload(pending_payment.gateway_order_id, "confirmed"),
            content_type="application/json",
        )

        assert response.status_code == 200
        pending_payment.refresh_from_db()
        assert pending_payment.status == PaymentStatus.CONFIRMED
        assert pending_payment.confirmed_at is not None

        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.current_period_end is not None
        expected_end = timezone.now() + timezone.timedelta(days=subscription.plan.period_days)
        assert abs((subscription.current_period_end - expected_end).total_seconds()) < 5

    def test_failed_status_marks_payment_failed_without_touching_subscription(
        self, api_client, pending_payment
    ):
        subscription = pending_payment.subscription

        response = api_client.post(
            WEBHOOK_URL,
            data=_payload(pending_payment.gateway_order_id, "failed"),
            content_type="application/json",
        )

        assert response.status_code == 200
        pending_payment.refresh_from_db()
        assert pending_payment.status == PaymentStatus.FAILED

        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.TRIALING
        assert subscription.current_period_end is None

    def test_expired_status_marks_payment_expired(self, api_client, pending_payment):
        response = api_client.post(
            WEBHOOK_URL,
            data=_payload(pending_payment.gateway_order_id, "expired"),
            content_type="application/json",
        )

        assert response.status_code == 200
        pending_payment.refresh_from_db()
        assert pending_payment.status == PaymentStatus.EXPIRED

    def test_unknown_gateway_order_id_is_logged_but_does_not_error(self, api_client, db):
        response = api_client.post(
            WEBHOOK_URL,
            data=_payload("does-not-exist", "confirmed", event_id="evt-unknown"),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert WebhookEvent.objects.filter(event_id="evt-unknown").exists()


class TestWebhookIdempotency:
    def test_replayed_event_id_is_a_no_op(self, api_client, pending_payment):
        first = api_client.post(
            WEBHOOK_URL,
            data=_payload(pending_payment.gateway_order_id, "confirmed", event_id="evt-once"),
            content_type="application/json",
        )
        assert first.status_code == 200
        pending_payment.refresh_from_db()
        subscription = pending_payment.subscription
        subscription.refresh_from_db()
        period_end_after_first = subscription.current_period_end

        second = api_client.post(
            WEBHOOK_URL,
            data=_payload(pending_payment.gateway_order_id, "confirmed", event_id="evt-once"),
            content_type="application/json",
        )

        assert second.status_code == 200
        assert WebhookEvent.objects.filter(event_id="evt-once").count() == 1

        subscription.refresh_from_db()
        assert subscription.current_period_end == period_end_after_first

    def test_replayed_confirmation_does_not_extend_period_twice(
        self, api_client, pending_payment
    ):
        """Same idempotency guarantee, exercised via the payment-level
        no-op path (services.apply_gateway_status) rather than only the
        WebhookEvent unique-constraint gate — covers the "already
        confirmed" branch directly."""
        subscription = pending_payment.subscription

        api_client.post(
            WEBHOOK_URL,
            data=_payload(pending_payment.gateway_order_id, "confirmed", event_id="evt-a"),
            content_type="application/json",
        )
        subscription.refresh_from_db()
        period_end_after_first = subscription.current_period_end

        # A different event_id but reporting the same already-confirmed
        # order — simulates Pagopar sending a second, distinct
        # notification for the same underlying charge.
        api_client.post(
            WEBHOOK_URL,
            data=_payload(pending_payment.gateway_order_id, "confirmed", event_id="evt-b"),
            content_type="application/json",
        )

        subscription.refresh_from_db()
        assert subscription.current_period_end == period_end_after_first


class TestWebhookSignatureRejection:
    def test_bad_signature_is_rejected(self, api_client, settings, monkeypatch, pending_payment):
        settings.PAYMENT_GATEWAY = "adapters.pagopar.adapter.PagoparAdapter"
        monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "test-public")
        monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "test-private")
        monkeypatch.setenv("PAGOPAR_BASE_URL", "https://api.pagopar.test")

        body = json.dumps(
            {"id_pedido_comercio": pending_payment.gateway_order_id, "estado": "pagado", "id_pedido": "evt-bad"}
        ).encode()

        response = api_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAGOPAR_SIGNATURE="not-the-real-signature",
        )

        assert response.status_code == 401
        pending_payment.refresh_from_db()
        assert pending_payment.status == PaymentStatus.PENDING
        # Logged for forensics even though rejected (design §5, layer 4).
        assert WebhookEvent.objects.filter(payload__id_pedido_comercio=pending_payment.gateway_order_id).exists()

    def test_empty_private_key_fails_closed_even_with_valid_looking_signature(
        self, api_client, settings, monkeypatch, pending_payment
    ):
        """Review finding W4: an unconfigured PAGOPAR_PRIVATE_KEY must never
        let a webhook through, even if the attacker computes a signature
        assuming an empty key."""
        from adapters.pagopar.signature import compute_candidate_signature

        settings.PAYMENT_GATEWAY = "adapters.pagopar.adapter.PagoparAdapter"
        monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "test-public")
        monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "")
        monkeypatch.setenv("PAGOPAR_BASE_URL", "https://api.pagopar.test")

        forged_signature = compute_candidate_signature("", pending_payment.gateway_order_id, "pagado")
        body = json.dumps(
            {
                "id_pedido_comercio": pending_payment.gateway_order_id,
                "estado": "pagado",
                "id_pedido": "evt-empty-key",
            }
        ).encode()

        response = api_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_PAGOPAR_SIGNATURE=forged_signature,
        )

        assert response.status_code == 401
        pending_payment.refresh_from_db()
        assert pending_payment.status == PaymentStatus.PENDING
