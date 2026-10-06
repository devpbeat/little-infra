"""`POST /api/v1/charges` — Flow B: a tenant charges its own buyer.

Flow A (`POST /api/v1/payments`) charges a SaaS subscription into the SaaS
owner's Pagopar account. Flow B charges an arbitrary PYG amount on behalf of
one of the tenant's own customers, into the SELLING COMPANY's Pagopar
account. Uses `FakePaymentGateway` — never a real Pagopar call.
"""

import pytest

from apps.billing.models import Payment, PaymentKind, PaymentStatus
from apps.customers.models import Customer
from apps.merchants.models import MerchantAccount
from tests.conftest import authed_client

CHARGES = "/api/v1/charges"


@pytest.fixture
def merchant(db, provisioned_app):
    app, _ = provisioned_app
    account = MerchantAccount.objects.create(
        app=app, external_ref="company-3", display_name="Loteadora Sur", public_key="pub-3"
    )
    account.set_private_key("priv-3")
    account.save()
    return account


def payload(**overrides):
    body = {
        "external_ref": "installment:4471",
        "amount_pyg": 1_500_000,
        "description": "Cuota 7/130 - Lote 42",
        "customer_ref": "buyer-9912",
        "merchant_ref": "company-3",
        "buyer": {
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "document": "1234567",
            "phone": "0981123456",
        },
    }
    body.update(overrides)
    return body


class TestChargeCreation:
    def test_creates_one_off_payment_and_returns_checkout_url(self, provisioned_app, merchant):
        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(), format="json")

        assert response.status_code == 201, response.data
        assert response.data["kind"] == PaymentKind.ONE_OFF
        assert response.data["status"] == PaymentStatus.PENDING
        assert response.data["amount_pyg"] == 1_500_000
        assert response.data["external_ref"] == "installment:4471"
        assert response.data["customer_ref"] == "buyer-9912"
        assert response.data["merchant_ref"] == "company-3"
        assert response.data["subscription"] is None
        assert response.data["checkout_url"]
        assert response.data["gateway_order_id"]

    def test_autocreates_the_buyer_customer(self, provisioned_app, merchant):
        """A plot buyer is not a SaaS signup — no contract, no subscription."""
        app, raw_key = provisioned_app
        authed_client(raw_key).post(CHARGES, payload(), format="json")

        customer = Customer.objects.get(app=app, external_ref="buyer-9912")
        assert customer.display_name == "Ada Lovelace"
        assert customer.email == "ada@example.com"
        assert customer.subscriptions.count() == 0
        assert customer.contracts.count() == 0

    def test_reuses_an_existing_customer(self, provisioned_app, merchant):
        app, raw_key = provisioned_app
        Customer.objects.create(app=app, external_ref="buyer-9912", display_name="Existing")

        authed_client(raw_key).post(CHARGES, payload(), format="json")

        assert Customer.objects.filter(app=app, external_ref="buyer-9912").count() == 1

    def test_buyer_fields_fall_back_to_the_customer_record(self, provisioned_app, merchant):
        app, raw_key = provisioned_app
        Customer.objects.create(
            app=app,
            external_ref="buyer-9912",
            display_name="Grace Hopper",
            email="grace@example.com",
            tax_id="7654321",
            phone="0971000000",
        )
        body = payload()
        body.pop("buyer")

        response = authed_client(raw_key).post(CHARGES, body, format="json")

        assert response.status_code == 201, response.data

    def test_charges_into_the_merchants_account_not_the_global_one(
        self, provisioned_app, merchant, monkeypatch
    ):
        """The compliance requirement: the gateway is built with the tenant's keys."""
        from apps.billing import views

        seen = {}

        class RecordingGateway:
            def __init__(self, credentials=None):
                seen["credentials"] = credentials

            def create_charge(self, request):
                from payments_core.ports.payment_gateway import ChargeResult

                return ChargeResult(gateway_order_id="hash-1", checkout_url="https://x.test", raw={})

        monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "global-pub")
        monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "global-priv")
        monkeypatch.setattr(
            views, "get_payment_gateway", lambda credentials=None: RecordingGateway(credentials)
        )

        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(), format="json")

        assert response.status_code == 201, response.data
        assert seen["credentials"].public_key == "pub-3"
        assert seen["credentials"].private_key == "priv-3"

    def test_records_the_merchant_on_the_payment(self, provisioned_app, merchant):
        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(), format="json")

        payment = Payment.objects.get(pk=response.data["id"])
        assert payment.merchant_account_id == merchant.pk


class TestChargeIdempotency:
    def test_repeat_external_ref_returns_the_same_payment(self, provisioned_app, merchant):
        """A double-clicked "pay" button must not create two Pagopar orders."""
        _app, raw_key = provisioned_app
        client = authed_client(raw_key)

        first = client.post(CHARGES, payload(), format="json")
        second = client.post(CHARGES, payload(), format="json")

        assert first.status_code == 201
        assert second.status_code == 200
        assert second.data["id"] == first.data["id"]
        assert second.data["gateway_order_id"] == first.data["gateway_order_id"]
        assert Payment.objects.filter(external_ref="installment:4471").count() == 1

    def test_repeat_with_a_different_amount_is_a_conflict(self, provisioned_app, merchant):
        _app, raw_key = provisioned_app
        client = authed_client(raw_key)

        client.post(CHARGES, payload(), format="json")
        response = client.post(CHARGES, payload(amount_pyg=2_000_000), format="json")

        assert response.status_code == 409
        assert Payment.objects.filter(external_ref="installment:4471").count() == 1

    def test_two_apps_may_use_the_same_external_ref(
        self, provisioned_app, other_provisioned_app, merchant
    ):
        """Idempotency is scoped per consuming app, so tenants cannot collide."""
        _app, raw_key = provisioned_app
        other_app, other_raw_key = other_provisioned_app
        other_merchant = MerchantAccount.objects.create(
            app=other_app, external_ref="company-3", public_key="pub-other"
        )
        other_merchant.set_private_key("priv-other")
        other_merchant.save()

        first = authed_client(raw_key).post(CHARGES, payload(), format="json")
        second = authed_client(other_raw_key).post(CHARGES, payload(), format="json")

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.data["id"] != first.data["id"]
        assert other_merchant.payments.count() == 1


class TestChargeValidation:
    def test_requires_an_api_key(self, api_client, merchant):
        assert api_client.post(CHARGES, payload(), format="json").status_code == 401

    @pytest.mark.parametrize("amount", [0, -1])
    def test_rejects_non_positive_amounts(self, provisioned_app, merchant, amount):
        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(amount_pyg=amount), format="json")
        assert response.status_code == 400

    def test_rejects_a_blank_external_ref(self, provisioned_app, merchant):
        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(external_ref=""), format="json")
        assert response.status_code == 400

    def test_rejects_an_unknown_merchant_ref(self, provisioned_app, merchant):
        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(merchant_ref="nope"), format="json")
        assert response.status_code == 400

    def test_cannot_charge_into_another_apps_merchant_account(
        self, provisioned_app, other_provisioned_app
    ):
        _app, raw_key = provisioned_app
        other_app, _ = other_provisioned_app
        foreign = MerchantAccount.objects.create(
            app=other_app, external_ref="company-foreign", public_key="pub-foreign"
        )
        foreign.set_private_key("priv-foreign")
        foreign.save()

        response = authed_client(raw_key).post(
            CHARGES, payload(merchant_ref="company-foreign"), format="json"
        )

        assert response.status_code == 400

    def test_rejects_an_inactive_merchant_account(self, provisioned_app, merchant):
        merchant.is_active = False
        merchant.save(update_fields=["is_active"])

        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(), format="json")

        assert response.status_code == 400

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_merchant_ref_is_required(self, provisioned_app, merchant, bad):
        """No default merchant: omitting it would pay the SaaS owner, not the company."""
        _app, raw_key = provisioned_app
        client = authed_client(raw_key)
        body = payload()
        body.pop("merchant_ref")

        assert client.post(CHARGES, body, format="json").status_code == 400
        assert client.post(CHARGES, payload(merchant_ref=bad), format="json").status_code == 400
        assert not Payment.objects.filter(external_ref="installment:4471").exists()

    def test_never_leaks_merchant_credentials(self, provisioned_app, merchant):
        _app, raw_key = provisioned_app
        response = authed_client(raw_key).post(CHARGES, payload(), format="json")

        body = str(response.data)
        assert "priv-3" not in body
        assert "pub-3" not in body
        assert "private_key" not in body

    def test_gateway_failure_is_502_and_marks_the_payment_failed(
        self, provisioned_app, merchant, monkeypatch
    ):
        from apps.billing import views

        class BoomGateway:
            def __init__(self, credentials=None):
                pass

            def create_charge(self, request):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            views, "get_payment_gateway", lambda credentials=None: BoomGateway()
        )
        _app, raw_key = provisioned_app

        response = authed_client(raw_key).post(CHARGES, payload(), format="json")

        assert response.status_code == 502
        payment = Payment.objects.get(external_ref="installment:4471")
        assert payment.status == PaymentStatus.FAILED

    def test_a_failed_charge_can_be_retried_with_the_same_external_ref(
        self, provisioned_app, merchant, monkeypatch
    ):
        """Idempotency must not permanently burn the reference on a gateway outage."""
        from apps.billing import views

        class BoomGateway:
            def __init__(self, credentials=None):
                pass

            def create_charge(self, request):
                raise RuntimeError("boom")

        _app, raw_key = provisioned_app
        client = authed_client(raw_key)
        monkeypatch.setattr(views, "get_payment_gateway", lambda credentials=None: BoomGateway())
        assert client.post(CHARGES, payload(), format="json").status_code == 502

        monkeypatch.undo()
        retry = client.post(CHARGES, payload(), format="json")

        assert retry.status_code == 201, retry.data
        assert retry.data["status"] == PaymentStatus.PENDING
        assert Payment.objects.filter(external_ref="installment:4471").count() == 1


class TestMerchantAccountIsMandatoryAtTheDatabase:
    """The compliance control, below the API: a one-off charge needs a merchant."""

    def test_cannot_create_a_one_off_payment_without_a_merchant_account(
        self, db, provisioned_app
    ):
        from django.db import IntegrityError, transaction

        from apps.billing.models import PaymentKind

        app, _ = provisioned_app
        customer = Customer.objects.create(app=app, external_ref="buyer-direct")

        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                app=app,
                kind=PaymentKind.ONE_OFF,
                customer=customer,
                merchant_account=None,
                external_ref="installment:bypass",
                amount_pyg=1_000,
            )
