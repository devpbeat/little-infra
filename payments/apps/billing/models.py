from django.db import models

from apps.subscriptions.models import Subscription


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"


class Payment(models.Model):
    """A single payment/charge attempt against a Subscription.

    `amount_pyg` is a plain integer — PYG has no decimal subunit in
    circulation (see payments_core.money).
    """

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    amount_pyg = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    gateway = models.CharField(max_length=50, default="pagopar")
    gateway_order_id = models.CharField(max_length=255, blank=True, db_index=True)
    # Uniqueness is enforced only for non-blank values (blank until checkout
    # is created at the gateway); see partial constraint in Meta.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_pyg__gt=0), name="payment_amount_pyg_positive"
            ),
            models.UniqueConstraint(
                fields=["gateway", "gateway_order_id"],
                condition=~models.Q(gateway_order_id=""),
                name="unique_nonblank_gateway_order_id",
            ),
        ]

    def __str__(self) -> str:
        return f"Payment#{self.pk} ({self.status}, {self.amount_pyg} PYG)"


class WebhookEvent(models.Model):
    """Log of every inbound gateway webhook, keyed for idempotency.

    Deliberately NOT tenant-scoped: the gateway does not identify our
    tenant at receipt time, so events are logged raw and attributed to a
    tenant only during processing.

    The unique constraint on (gateway, event_id) is the idempotency gate:
    a webhook handler must attempt to persist this row BEFORE applying any
    state change, and treat an IntegrityError as "already processed, no-op".
    """

    gateway = models.CharField(max_length=50)
    event_id = models.CharField(max_length=255)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["gateway", "event_id"], name="unique_gateway_event_id"),
        ]

    def __str__(self) -> str:
        return f"WebhookEvent({self.gateway}:{self.event_id})"
