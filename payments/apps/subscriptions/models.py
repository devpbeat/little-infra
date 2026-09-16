import datetime

from django.db import models
from django.utils import timezone

from apps.customers.models import Customer

TRIAL_DURATION_DAYS = 30


class Plan(models.Model):
    """A billable plan customers can subscribe to."""

    name = models.CharField(max_length=150, unique=True)
    price_pyg = models.PositiveIntegerField(help_text="Recurring price in PYG (integer, no subunits).")
    period_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class SubscriptionStatus(models.TextChoices):
    TRIALING = "trialing", "Trialing"
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past due"
    CANCELED = "canceled", "Canceled"


class Subscription(models.Model):
    """A Customer's subscription to a Plan."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING
    )
    trial_start = models.DateTimeField()
    trial_end = models.DateTimeField()
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def start_trial(cls, customer: Customer, plan: Plan, now: datetime.datetime | None = None) -> "Subscription":
        """Create a Subscription in `trialing` status with a 30-day trial window."""
        now = now or timezone.now()
        return cls.objects.create(
            customer=customer,
            plan=plan,
            status=SubscriptionStatus.TRIALING,
            trial_start=now,
            trial_end=now + datetime.timedelta(days=TRIAL_DURATION_DAYS),
        )

    def __str__(self) -> str:
        return f"Subscription#{self.pk} ({self.status})"


def compute_entitlement(subscription: Subscription, now: datetime.datetime | None = None) -> bool:
    """Pure function: is `subscription` entitled to service access at `now`?

    No I/O — callers pass an already-fetched Subscription instance. Rules:
    - trialing: entitled while `now` is within [trial_start, trial_end).
    - active: entitled while `now` is before `current_period_end`.
    - past_due: never entitled (payment lapsed).
    - canceled: never entitled.
    """
    now = now or timezone.now()

    if subscription.status == SubscriptionStatus.TRIALING:
        return subscription.trial_start <= now < subscription.trial_end

    if subscription.status == SubscriptionStatus.ACTIVE:
        return subscription.current_period_end is not None and now < subscription.current_period_end

    return False
