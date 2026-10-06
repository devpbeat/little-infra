import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.billing.models import Payment, WebhookEvent
from apps.merchants.models import MerchantAccount
from apps.subscriptions.models import Plan, Subscription, SubscriptionStatus


@pytest.fixture
def subscription(db, customer_factory):
    plan = Plan.objects.create(name="Pro", price_pyg=150_000)
    now = datetime.datetime.now(datetime.UTC)
    return Subscription.objects.create(
        customer=customer_factory(),
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        trial_start=now,
        trial_end=now,
        current_period_end=now + datetime.timedelta(days=30),
    )


@pytest.mark.django_db
class TestPaymentPygConstraint:
    def test_positive_amount_is_valid(self, subscription):
        payment = Payment.objects.create(subscription=subscription, amount_pyg=150_000)
        assert payment.amount_pyg == 150_000

    def test_zero_amount_violates_constraint(self, subscription):
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(subscription=subscription, amount_pyg=0)

    def test_negative_amount_rejected_by_field(self, subscription):
        # PositiveIntegerField rejects negative values at the DB level too.
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(subscription=subscription, amount_pyg=-1)


@pytest.mark.django_db
class TestWebhookEventIdempotency:
    def test_duplicate_event_id_for_same_gateway_rejected(self):
        WebhookEvent.objects.create(gateway="pagopar", event_id="evt-1", payload={})
        with pytest.raises(IntegrityError), transaction.atomic():
            WebhookEvent.objects.create(gateway="pagopar", event_id="evt-1", payload={})

    def test_same_event_id_different_gateway_allowed(self):
        WebhookEvent.objects.create(gateway="pagopar", event_id="evt-1", payload={})
        WebhookEvent.objects.create(gateway="other", event_id="evt-1", payload={})
        assert WebhookEvent.objects.count() == 2

@pytest.mark.django_db
class TestPaymentKindConstraints:
    """`Payment` represents both flows; invalid combinations are rejected by the DB.

    Flow A (`kind=subscription`) MUST have a subscription. Flow B
    (`kind=one_off`) MUST have a customer and a caller-supplied
    `external_ref`, and MUST NOT have a subscription.
    """

    def test_subscription_kind_requires_a_subscription(self, db, customer_factory):
        from apps.billing.models import PaymentKind

        customer = customer_factory()
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                app=customer.app,
                customer=customer,
                kind=PaymentKind.SUBSCRIPTION,
                subscription=None,
                amount_pyg=1_000,
            )

    def test_one_off_kind_rejects_a_subscription(self, subscription):
        from apps.billing.models import PaymentKind

        merchant = MerchantAccount.objects.create(
            app=subscription.customer.app, external_ref="company-1"
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                app=subscription.customer.app,
                customer=subscription.customer,
                merchant_account=merchant,
                subscription=subscription,
                kind=PaymentKind.ONE_OFF,
                external_ref="installment:1",
                amount_pyg=1_000,
            )

    def test_one_off_kind_requires_a_nonblank_external_ref(self, db, customer_factory):
        from apps.billing.models import PaymentKind

        customer = customer_factory()
        merchant = MerchantAccount.objects.create(app=customer.app, external_ref="company-1")
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                app=customer.app,
                customer=customer,
                merchant_account=merchant,
                kind=PaymentKind.ONE_OFF,
                external_ref="",
                amount_pyg=1_000,
            )

    def test_one_off_kind_requires_a_customer(self, db, app):
        from apps.billing.models import PaymentKind

        merchant = MerchantAccount.objects.create(app=app, external_ref="company-1")
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                app=app,
                customer=None,
                merchant_account=merchant,
                kind=PaymentKind.ONE_OFF,
                external_ref="installment:1",
                amount_pyg=1_000,
            )

    def test_external_ref_is_unique_per_app(self, db, customer_factory):
        from apps.billing.models import PaymentKind

        customer = customer_factory()
        merchant = MerchantAccount.objects.create(app=customer.app, external_ref="company-1")
        fields = {
            "app": customer.app,
            "customer": customer,
            "merchant_account": merchant,
            "kind": PaymentKind.ONE_OFF,
            "external_ref": "installment:1",
            "amount_pyg": 1_000,
        }
        Payment.objects.create(**fields)
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(**fields)

    def test_one_off_kind_requires_a_merchant_account(self, db, customer_factory):
        """Flow B's compliance control: no merchant means no charge, at the DB."""
        from apps.billing.models import PaymentKind

        customer = customer_factory()
        with pytest.raises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                app=customer.app,
                customer=customer,
                merchant_account=None,
                kind=PaymentKind.ONE_OFF,
                external_ref="installment:no-merchant",
                amount_pyg=1_000,
            )

    def test_blank_external_refs_do_not_collide(self, subscription):
        """Flow A rows leave `external_ref` blank; the unique index is partial."""
        Payment.objects.create(subscription=subscription, amount_pyg=1_000)
        Payment.objects.create(subscription=subscription, amount_pyg=1_000)
        assert Payment.objects.filter(external_ref="").count() == 2

    def test_app_is_backfilled_from_the_subscription(self, subscription):
        payment = Payment.objects.create(subscription=subscription, amount_pyg=1_000)
        assert payment.app_id == subscription.customer.app_id
        assert payment.customer_id == subscription.customer_id
