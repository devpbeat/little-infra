import datetime

import pytest
from freezegun import freeze_time

from apps.subscriptions.models import (
    TRIAL_DURATION_DAYS,
    Plan,
    Subscription,
    SubscriptionStatus,
    compute_entitlement,
)


@pytest.fixture
def plan(db):
    return Plan.objects.create(name="Pro", price_pyg=150_000, period_days=30)


@pytest.mark.django_db
class TestEntitlementMatrix:
    def test_trialing_entitled_on_day_zero(self, customer_factory, plan):
        with freeze_time("2026-01-01T00:00:00Z"):
            sub = Subscription.start_trial(customer_factory(), plan)
            assert compute_entitlement(sub) is True

    def test_trialing_entitled_one_day_before_expiry(self, customer_factory, plan):
        with freeze_time("2026-01-01T00:00:00Z"):
            sub = Subscription.start_trial(customer_factory(), plan)
        with freeze_time("2026-01-30T00:00:00Z"):
            assert compute_entitlement(sub, now=_now()) is True

    def test_trialing_not_entitled_after_30_days(self, customer_factory, plan):
        with freeze_time("2026-01-01T00:00:00Z"):
            sub = Subscription.start_trial(customer_factory(), plan)
        expired_at = sub.trial_start + datetime.timedelta(days=TRIAL_DURATION_DAYS)
        assert compute_entitlement(sub, now=expired_at) is False

    def test_active_entitled_before_period_end(self, customer_factory, plan):
        sub = Subscription.objects.create(
            customer=customer_factory(),
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            trial_start=_now(),
            trial_end=_now(),
            current_period_end=_now() + datetime.timedelta(days=10),
        )
        assert compute_entitlement(sub) is True

    def test_active_not_entitled_after_period_end(self, customer_factory, plan):
        sub = Subscription.objects.create(
            customer=customer_factory(),
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            trial_start=_now(),
            trial_end=_now(),
            current_period_end=_now() - datetime.timedelta(seconds=1),
        )
        assert compute_entitlement(sub) is False

    def test_past_due_never_entitled(self, customer_factory, plan):
        sub = Subscription.objects.create(
            customer=customer_factory(),
            plan=plan,
            status=SubscriptionStatus.PAST_DUE,
            trial_start=_now(),
            trial_end=_now(),
            current_period_end=_now() + datetime.timedelta(days=10),
        )
        assert compute_entitlement(sub) is False

    def test_canceled_never_entitled(self, customer_factory, plan):
        sub = Subscription.objects.create(
            customer=customer_factory(),
            plan=plan,
            status=SubscriptionStatus.CANCELED,
            trial_start=_now(),
            trial_end=_now(),
            current_period_end=_now() + datetime.timedelta(days=10),
        )
        assert compute_entitlement(sub) is False


def _now():
    from django.utils import timezone

    return timezone.now()
