"""Cross-tenant isolation fitness tests for `ScopedByAppMixin`.

The dangerous case is a Flow B one-off Payment: it has NO subscription, so
the old `subscription__customer__app` scope path did not exist for it and
such a row would have fallen out of scoping entirely. `Payment.app` is now
a direct, non-null FK and the scope field, which is what these tests pin.
"""

import pytest

from apps.billing.models import Payment, PaymentKind, PaymentStatus
from apps.customers.models import Customer
from apps.merchants.models import MerchantAccount
from apps.subscriptions.models import Subscription
from payments_core.auth import ScopedByAppMixin
from tests.conftest import authed_client


def make_one_off(app, external_ref="installment:1", **kwargs):
    """A Flow B payment: buyer + collecting company, no subscription."""
    customer = Customer.objects.create(app=app, external_ref=f"buyer-{external_ref}")
    merchant, _ = MerchantAccount.objects.get_or_create(
        app=app, external_ref="company-scoping", defaults={"public_key": "pub"}
    )
    return Payment.objects.create(
        app=app,
        customer=customer,
        merchant_account=merchant,
        kind=PaymentKind.ONE_OFF,
        external_ref=external_ref,
        amount_pyg=1_000_000,
        gateway="pagopar",
        **kwargs,
    )


class TestPaymentScopeField:
    def test_payment_viewset_scopes_on_the_direct_app_fk(self):
        from apps.billing.views import PaymentViewSet

        assert PaymentViewSet.app_scope_field == "app"

    def test_mixin_default_denies_without_request_app(self, db, app):
        class Base:
            def get_queryset(self):
                return Payment.objects.all()

        class Dummy(ScopedByAppMixin, Base):
            app_scope_field = "app"
            request = type("R", (), {"app": None, "user": None})()

        make_one_off(app)
        assert Dummy().get_queryset().count() == 0


class TestOneOffPaymentIsolation:
    def test_list_excludes_another_apps_one_off_payment(
        self, provisioned_app, other_provisioned_app
    ):
        app, raw_key = provisioned_app
        other_app, other_raw_key = other_provisioned_app
        make_one_off(app, "installment:a")
        make_one_off(other_app, "installment:b")

        mine = authed_client(raw_key).get("/api/v1/payments/")
        theirs = authed_client(other_raw_key).get("/api/v1/payments/")

        assert mine.data["count"] == 1
        assert theirs.data["count"] == 1
        assert mine.data["results"][0]["external_ref"] == "installment:a"
        assert theirs.data["results"][0]["external_ref"] == "installment:b"

    def test_detail_of_another_apps_one_off_payment_is_404(
        self, provisioned_app, other_provisioned_app
    ):
        app, _raw_key = provisioned_app
        other_app, other_raw_key = other_provisioned_app
        payment = make_one_off(app, "installment:a")

        response = authed_client(other_raw_key).get(f"/api/v1/payments/{payment.pk}/")

        assert response.status_code == 404

    def test_cannot_refresh_another_apps_one_off_payment(
        self, provisioned_app, other_provisioned_app
    ):
        app, _raw_key = provisioned_app
        _other_app, other_raw_key = other_provisioned_app
        payment = make_one_off(app, "installment:a", gateway_order_id="hash-a")

        response = authed_client(other_raw_key).post(f"/api/v1/payments/{payment.pk}/refresh/")

        assert response.status_code == 404

    def test_subscription_payments_stay_visible_to_their_own_app(
        self, provisioned_app, other_provisioned_app, plan
    ):
        """Flow A must not regress: subscription payments remain scoped and visible."""
        app, raw_key = provisioned_app
        _other_app, other_raw_key = other_provisioned_app
        customer = Customer.objects.create(app=app, external_ref="saas-1")
        subscription = Subscription.start_trial(customer, plan)
        Payment.objects.create(
            app=app,
            customer=customer,
            subscription=subscription,
            kind=PaymentKind.SUBSCRIPTION,
            amount_pyg=plan.price_pyg,
        )

        assert authed_client(raw_key).get("/api/v1/payments/").data["count"] == 1
        assert authed_client(other_raw_key).get("/api/v1/payments/").data["count"] == 0

    def test_no_payment_row_can_exist_without_an_app(self, db, app):
        """The scoping hole is closed at the database level, not only in Python.

        `.update()` bypasses `Payment.save()`'s app back-fill, so this asserts
        the NOT NULL column itself rather than the Python convenience.
        """
        from django.db import IntegrityError, transaction

        payment = make_one_off(app, "installment:x")
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.filter(pk=payment.pk).update(app=None)


class TestMerchantAccountIsolation:
    def test_merchant_accounts_are_scoped_per_app(self, db, app):
        from apps.apps_registry.models import ConsumingApp

        other = ConsumingApp.objects.create(name="other-tenant")
        MerchantAccount.objects.create(app=app, external_ref="company-3")
        MerchantAccount.objects.create(app=other, external_ref="company-9")

        assert MerchantAccount.objects.filter(app=app).count() == 1
        assert not MerchantAccount.objects.filter(app=app, external_ref="company-9").exists()


class TestPaymentResultIsStatusOnly:
    def test_public_result_reveals_only_the_status(self, db, app, api_client):
        payment = make_one_off(app, "installment:pub", gateway_order_id="hash-pub")

        response = api_client.get(f"/api/v1/payments/result/{payment.gateway_order_id}")

        assert response.status_code == 200
        assert response.data == {"status": PaymentStatus.PENDING}
