"""`POST /api/v1/payments` API tests (Slice E1, spec: payment-processing).

Uses `FakePaymentGateway` (the default `settings.PAYMENT_GATEWAY` under
test) — never a real Pagopar call.
"""

import pytest

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
