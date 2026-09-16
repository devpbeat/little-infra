import datetime

import pytest
from django.db import IntegrityError, transaction

from apps.billing.models import Payment, WebhookEvent
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
