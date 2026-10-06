"""Outbound signed callbacks: telling the consuming app a charge was confirmed.

yvyreta must learn that an installment was paid so it can mark it PAID and
flip the plot to SOLD. The webhook handler updates the Payment locally; these
tests pin the outbound leg — enqueued exactly once per (payment, event),
HMAC-signed, retried with backoff, and idempotent on redelivery.
"""

import hashlib
import hmac
import json

import pytest
from django.utils import timezone

from apps.billing.callbacks import (
    CALLBACK_MAX_ATTEMPTS,
    build_signature,
    deliver,
    dispatch_pending,
    enqueue_payment_callback,
)
from apps.billing.models import CallbackDelivery, DeliveryStatus, Payment, PaymentKind
from apps.billing.services import process_webhook_status
from apps.customers.models import Customer
from apps.merchants.models import MerchantAccount
from payments_core.ports.payment_gateway import ChargeStatus


@pytest.fixture
def callback_app(db, provisioned_app):
    app, raw_key = provisioned_app
    app.callback_url = "https://yvyreta.test/webhooks/payments"
    app.set_callback_secret("shared-secret")
    app.save()
    return app


@pytest.fixture
def one_off(db, callback_app):
    customer = Customer.objects.create(app=callback_app, external_ref="buyer-9912")
    merchant = MerchantAccount.objects.create(
        app=callback_app, external_ref="company-3", public_key="pub-3"
    )
    merchant.set_private_key("priv-3")
    merchant.save()
    return Payment.objects.create(
        app=callback_app,
        customer=customer,
        merchant_account=merchant,
        kind=PaymentKind.ONE_OFF,
        external_ref="installment:4471",
        description="Cuota 7/130",
        amount_pyg=1_500_000,
        gateway="pagopar",
        gateway_order_id="hash-4471",
    )


class TestEnqueueOnConfirmation:
    def test_confirmation_enqueues_a_delivery(self, one_off):
        process_webhook_status(
            gateway="pagopar", gateway_order_id="hash-4471", gateway_status=ChargeStatus.CONFIRMED
        )

        delivery = CallbackDelivery.objects.get(payment=one_off)
        assert delivery.event == "payment.confirmed"
        assert delivery.url == "https://yvyreta.test/webhooks/payments"
        assert delivery.status == DeliveryStatus.PENDING

    def test_replayed_webhook_does_not_enqueue_twice(self, one_off):
        for _ in range(3):
            process_webhook_status(
                gateway="pagopar",
                gateway_order_id="hash-4471",
                gateway_status=ChargeStatus.CONFIRMED,
            )

        assert CallbackDelivery.objects.filter(payment=one_off).count() == 1

    def test_no_delivery_when_the_app_has_no_callback_url(self, one_off, callback_app):
        callback_app.callback_url = ""
        callback_app.save(update_fields=["callback_url"])

        process_webhook_status(
            gateway="pagopar", gateway_order_id="hash-4471", gateway_status=ChargeStatus.CONFIRMED
        )

        assert CallbackDelivery.objects.count() == 0

    def test_failed_payment_does_not_enqueue_a_confirmation(self, one_off):
        process_webhook_status(
            gateway="pagopar", gateway_order_id="hash-4471", gateway_status=ChargeStatus.FAILED
        )

        assert CallbackDelivery.objects.count() == 0


class TestPayload:
    def test_body_carries_the_fields_yvyreta_needs(self, one_off):
        delivery = enqueue_payment_callback(one_off)
        body = json.loads(delivery.body)

        assert body["event"] == "payment.confirmed"
        assert body["delivery_id"] == str(delivery.delivery_id)
        assert body["payment_id"] == one_off.pk
        assert body["external_ref"] == "installment:4471"
        assert body["customer_ref"] == "buyer-9912"
        assert body["amount_pyg"] == 1_500_000
        assert body["gateway_order_id"] == "hash-4471"
        assert "status" in body

    def test_body_never_contains_credentials(self, one_off):
        delivery = enqueue_payment_callback(one_off)
        assert "secret" not in delivery.body.lower()


class TestSigning:
    def test_signature_is_hmac_sha256_over_timestamp_and_body(self):
        signature = build_signature(secret="shared-secret", timestamp="1760000000", body='{"a":1}')

        expected = hmac.new(
            b"shared-secret", b'1760000000.{"a":1}', hashlib.sha256
        ).hexdigest()
        assert signature == f"sha256={expected}"

    def test_a_different_secret_produces_a_different_signature(self):
        assert build_signature(secret="a", timestamp="1", body="{}") != build_signature(
            secret="b", timestamp="1", body="{}"
        )


class TestDelivery:
    def test_successful_delivery_is_marked_delivered_and_signed(self, one_off, monkeypatch):
        from apps.billing import callbacks

        sent = {}

        def fake_post(url, body, headers, timeout):
            sent.update(url=url, body=body, headers=headers)
            return 200

        monkeypatch.setattr(callbacks, "post_json", fake_post)
        delivery = enqueue_payment_callback(one_off)

        deliver(delivery)

        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.DELIVERED
        assert delivery.attempts == 1
        assert delivery.delivered_at is not None
        assert sent["url"] == "https://yvyreta.test/webhooks/payments"
        assert sent["headers"]["X-Payments-Event"] == "payment.confirmed"
        assert sent["headers"]["X-Payments-Delivery"] == str(delivery.delivery_id)
        assert sent["headers"]["X-Payments-Signature"] == build_signature(
            secret="shared-secret",
            timestamp=sent["headers"]["X-Payments-Timestamp"],
            body=sent["body"],
        )

    def test_a_delivered_callback_is_not_sent_again(self, one_off, monkeypatch):
        from apps.billing import callbacks

        calls = {"n": 0}

        def fake_post(url, body, headers, timeout):
            calls["n"] += 1
            return 200

        monkeypatch.setattr(callbacks, "post_json", fake_post)
        delivery = enqueue_payment_callback(one_off)

        deliver(delivery)
        deliver(delivery)
        dispatch_pending()

        assert calls["n"] == 1

    def test_failure_schedules_a_retry_with_backoff(self, one_off, monkeypatch):
        from apps.billing import callbacks

        def boom(url, body, headers, timeout):
            raise OSError("connection refused")

        monkeypatch.setattr(callbacks, "post_json", boom)
        delivery = enqueue_payment_callback(one_off)
        first_due = delivery.next_attempt_at

        deliver(delivery)

        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.PENDING
        assert delivery.attempts == 1
        assert delivery.next_attempt_at > first_due
        assert "connection refused" in delivery.last_error

    def test_gives_up_after_max_attempts(self, one_off, monkeypatch):
        from apps.billing import callbacks

        monkeypatch.setattr(
            callbacks, "post_json", lambda url, body, headers, timeout: 500
        )
        delivery = enqueue_payment_callback(one_off)

        for _ in range(CALLBACK_MAX_ATTEMPTS):
            delivery.next_attempt_at = timezone.now()
            delivery.save(update_fields=["next_attempt_at"])
            deliver(delivery)
            delivery.refresh_from_db()

        assert delivery.attempts == CALLBACK_MAX_ATTEMPTS
        assert delivery.status == DeliveryStatus.FAILED

    def test_dispatch_pending_skips_deliveries_not_yet_due(self, one_off, monkeypatch):
        import datetime

        from apps.billing import callbacks

        calls = {"n": 0}
        monkeypatch.setattr(
            callbacks,
            "post_json",
            lambda url, body, headers, timeout: calls.__setitem__("n", calls["n"] + 1) or 200,
        )
        delivery = enqueue_payment_callback(one_off)
        delivery.next_attempt_at = timezone.now() + datetime.timedelta(hours=1)
        delivery.save(update_fields=["next_attempt_at"])

        dispatch_pending()

        assert calls["n"] == 0
