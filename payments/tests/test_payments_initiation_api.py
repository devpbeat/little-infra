"""`POST /api/v1/payments` API tests (Slice E1, spec: payment-processing).

Uses `FakePaymentGateway` (the default `settings.PAYMENT_GATEWAY` under
test) — never a real Pagopar call.
"""

import pytest
from rest_framework.test import APIClient

from apps.billing.models import Payment, PaymentStatus
from apps.customers.models import Customer
from apps.subscriptions.models import Subscription
from tests.conftest import authed_client


@pytest.fixture
def customer(db, provisioned_app):
    app, _raw_key = provisioned_app
    return Customer.objects.create(app=app, external_ref="cust-1", display_name="Ada Lovelace")


@pytest.fixture
def subscription(db, customer, plan):
    return Subscription.start_trial(customer, plan)


class TestPaymentResult:
    def test_returns_only_status_without_auth(self, db, subscription):
        payment = Payment.objects.create(
            subscription=subscription,
            amount_pyg=subscription.plan.price_pyg,
            gateway="pagopar",
            gateway_order_id="hash-public-1",
        )

        response = APIClient().get(f"/api/v1/payments/result/{payment.gateway_order_id}")

        assert response.status_code == 200
        assert response.data == {"status": PaymentStatus.PENDING}

    def test_unknown_hash_is_404(self, db):

        assert APIClient().get("/api/v1/payments/result/nope").status_code == 404


class TestPaymentRefresh:
    def test_refresh_applies_gateway_status(
        self, provisioned_app, subscription, monkeypatch
    ):
        from adapters.fakes.fake_gateway import FakePaymentGateway
        from apps.billing import views
        from payments_core.ports.payment_gateway import ChargeStatus

        _app, raw_key = provisioned_app
        payment = Payment.objects.create(
            subscription=subscription,
            amount_pyg=subscription.plan.price_pyg,
            gateway="pagopar",
            gateway_order_id="hash-refresh-1",
        )
        fake = FakePaymentGateway()
        fake.set_status("hash-refresh-1", ChargeStatus.CONFIRMED)
        monkeypatch.setattr(views, "get_payment_gateway", lambda: fake)

        client = authed_client(raw_key)
        response = client.post(f"/api/v1/payments/{payment.pk}/refresh/")

        assert response.status_code == 200
        assert response.data["status"] == PaymentStatus.CONFIRMED
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CONFIRMED

    def test_refresh_without_gateway_order_is_409(self, provisioned_app, subscription):
        _app, raw_key = provisioned_app
        payment = Payment.objects.create(
            subscription=subscription,
            amount_pyg=subscription.plan.price_pyg,
            gateway="pagopar",
        )

        client = authed_client(raw_key)
        assert client.post(f"/api/v1/payments/{payment.pk}/refresh/").status_code == 409


class TestPaymentInitiation:
    def test_creates_pending_payment_and_returns_checkout_info(
        self, provisioned_app, subscription
    ):
        _app, raw_key = provisioned_app
        client = authed_client(raw_key)

        response = client.post("/api/v1/payments", {"subscription": subscription.pk}, format="json")

        assert response.status_code == 201
        assert response.data["status"] == PaymentStatus.PENDING
        assert response.data["gateway_order_id"]
        assert response.data["checkout_url"]

        payment = Payment.objects.get(pk=response.data["id"])
        assert payment.subscription_id == subscription.pk
        assert payment.amount_pyg == subscription.plan.price_pyg

    def test_retry_returns_existing_pending_payment(self, provisioned_app, subscription):
        _app, raw_key = provisioned_app
        client = authed_client(raw_key)

        first = client.post("/api/v1/payments", {"subscription": subscription.pk}, format="json")
        second = client.post("/api/v1/payments", {"subscription": subscription.pk}, format="json")

        assert first.status_code == 201
        assert second.status_code == 200
        assert second.data["id"] == first.data["id"]
        assert Payment.objects.filter(subscription=subscription).count() == 1

    def test_rejects_subscription_belonging_to_another_app(
        self, provisioned_app, other_provisioned_app, contract_template, plan
    ):
        _app, raw_key = provisioned_app
        other_app, _ = other_provisioned_app
        other_customer = Customer.objects.create(app=other_app, external_ref="cust-2")
        other_subscription = Subscription.start_trial(other_customer, plan)

        client = authed_client(raw_key)
        response = client.post(
            "/api/v1/payments", {"subscription": other_subscription.pk}, format="json"
        )

        assert response.status_code == 404

    def test_rejects_missing_key(self, subscription, api_client):
        response = api_client.post(
            "/api/v1/payments", {"subscription": subscription.pk}, format="json"
        )
        assert response.status_code == 401

    def test_gateway_failure_surfaces_reason_and_marks_failed(
        self, provisioned_app, subscription, monkeypatch
    ):
        """A gateway/misconfig error is a 502 with the real reason, not a bare 500."""
        from apps.billing import views

        class BoomGateway:
            def create_charge(self, request):
                raise RuntimeError("boom")

        _app, raw_key = provisioned_app
        monkeypatch.setattr(views, "get_payment_gateway", lambda: BoomGateway())

        client = authed_client(raw_key)
        response = client.post(
            "/api/v1/payments", {"subscription": subscription.pk}, format="json"
        )

        assert response.status_code == 502
        assert "boom" in response.data["detail"]
        payment = Payment.objects.filter(subscription=subscription).first()
        assert payment.status == PaymentStatus.FAILED


class TestPaymentListing:
    def test_list_scoped_to_app(self, provisioned_app, subscription):
        _app, raw_key = provisioned_app
        client = authed_client(raw_key)
        client.post("/api/v1/payments", {"subscription": subscription.pk}, format="json")

        response = client.get("/api/v1/payments/")

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_list_excludes_other_apps_payments(
        self, provisioned_app, other_provisioned_app, subscription
    ):
        _app, raw_key = provisioned_app
        other_app, other_raw_key = other_provisioned_app
        client = authed_client(raw_key)
        client.post("/api/v1/payments", {"subscription": subscription.pk}, format="json")

        other_client = authed_client(other_raw_key)
        response = other_client.get("/api/v1/payments/")

        assert response.status_code == 200
        assert response.data["count"] == 0
