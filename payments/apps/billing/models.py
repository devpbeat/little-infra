"""Billing models: one `Payment` table serving BOTH money flows.

Flow A — SaaS subscriptions (`kind=subscription`): the SaaS owner charges a
tenant company a recurring fee, settled into the SaaS owner's own Pagopar
account (global `PAGOPAR_*` env pair).

Flow B — tenant-scoped one-off charges (`kind=one_off`): a tenant charges
its OWN buyer an arbitrary amount, settled into the COLLECTING COMPANY's
Pagopar account (`MerchantAccount`). There is no `Subscription` to point at.

Why one table with a `kind` discriminator rather than a second model:
status, gateway identifiers, the webhook/idempotency machinery and the
`payments/{id}` + `payments/result/{hash}` routes are identical for both
flows — splitting would duplicate all of it and fork the webhook handler.
The cost is that `subscription` is now nullable, which makes "a
subscription payment with no subscription" expressible; that is why the
valid combinations are pinned by DATABASE CheckConstraints below, not by
Python validation that a management command or a shell can bypass.
"""

import uuid

from django.db import models

from apps.apps_registry.models import ConsumingApp
from apps.customers.models import Customer
from apps.merchants.models import MerchantAccount
from apps.subscriptions.models import Subscription


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"

class PaymentKind(models.TextChoices):
    SUBSCRIPTION = "subscription", "SaaS subscription period"
    ONE_OFF = "one_off", "Tenant-scoped one-off charge"

RETRYABLE_STATUSES = (PaymentStatus.FAILED, PaymentStatus.EXPIRED)

class Payment(models.Model):
    """A single payment/charge attempt.

    `amount_pyg` is a plain integer — PYG has no decimal subunit in
    circulation (see payments_core.money).

    `app` is a DIRECT, non-null FK and the tenant scope used by
    `ScopedByAppMixin`. It is deliberately denormalized: scoping used to run
    through `subscription__customer__app`, and a Flow B payment has no
    subscription, so it would have had NO path to a `ConsumingApp` and would
    have dropped out of scoping entirely — i.e. become visible to every
    tenant. The column is NOT NULL so that hole cannot reopen.
    """

    app = models.ForeignKey(ConsumingApp, on_delete=models.CASCADE, related_name="payments")
    kind = models.CharField(
        max_length=20, choices=PaymentKind.choices, default=PaymentKind.SUBSCRIPTION
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="payments", null=True, blank=True
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
        help_text="Flow A only. NULL for a one-off tenant charge.",
    )
    merchant_account = models.ForeignKey(
        MerchantAccount,
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
        help_text=(
            "Which merchant account the money settles into. NULL means the global SaaS "
            "account and is only valid for kind=subscription (Flow A) — enforced by "
            "the payment_one_off_requires_customer_and_external_ref check constraint."
        ),
    )
    external_ref = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text=(
            "Caller-supplied reference for the thing being paid for (e.g. an "
            "Installment pk). Doubles as the idempotency key, unique per app."
        ),
    )
    description = models.CharField(max_length=255, blank=True)
    amount_pyg = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    charge_attempts = models.PositiveIntegerField(
        default=0,
        help_text=(
            "How many gateway orders this payment has asked for. Used to keep the "
            "gateway-side order reference unique when a failed charge is retried "
            "under the same external_ref."
        ),
    )
    gateway = models.CharField(max_length=50, default="pagopar")
    gateway_order_id = models.CharField(max_length=255, blank=True, db_index=True)
    checkout_url = models.TextField(blank=True)
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
            # Idempotency gate for Flow B, scoped per consuming app so two
            # tenants cannot collide on the same reference. Partial, like the
            # gateway_order_id index above, because Flow A leaves it blank.
            models.UniqueConstraint(
                fields=["app", "external_ref"],
                condition=~models.Q(external_ref=""),
                name="unique_app_payment_external_ref",
            ),
            # A subscription payment MUST have its subscription.
            models.CheckConstraint(
                condition=~models.Q(kind=PaymentKind.SUBSCRIPTION)
                | models.Q(subscription__isnull=False),
                name="payment_subscription_kind_requires_subscription",
            ),
            # A one-off charge MUST have a customer, a non-blank external_ref
            # AND a merchant account, and MUST NOT carry a subscription.
            #
            # The merchant_account clause is the compliance control: without
            # it, ANY code path that creates a one_off Payment outside the
            # charges endpoint (a shell, a management command, bulk_create)
            # could leave it NULL and settle a tenant's buyer payment into the
            # SaaS owner's global account with nothing to catch it.
            models.CheckConstraint(
                condition=~models.Q(kind=PaymentKind.ONE_OFF)
                | (
                    models.Q(subscription__isnull=True)
                    & models.Q(customer__isnull=False)
                    & models.Q(merchant_account__isnull=False)
                    & ~models.Q(external_ref="")
                ),
                name="payment_one_off_requires_customer_and_external_ref",
            ),
        ]

    def save(self, *args, **kwargs):
        """Back-fill `app`/`customer` from the subscription when unset.

        Convenience for Flow A call sites (and the existing fixtures) that
        only know the subscription. It is NOT the isolation guarantee — the
        NOT NULL column is. `.update()`/`bulk_create` bypass this on purpose.
        """
        if self.subscription_id is not None:
            if self.customer_id is None:
                self.customer_id = self.subscription.customer_id
            if self.app_id is None:
                self.app_id = self.subscription.customer.app_id
        elif self.app_id is None and self.customer_id is not None:
            self.app_id = self.customer.app_id
        return super().save(*args, **kwargs)

    @property
    def is_retryable(self) -> bool:
        """True when a repeat charge request may re-issue a gateway order.

        A gateway outage or a declined attempt must not permanently burn the
        caller's `external_ref` — otherwise a buyer whose first attempt
        failed could never pay that installment again.
        """
        return self.status in RETRYABLE_STATUSES or not self.gateway_order_id

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

class DeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed (gave up)"

class CallbackDelivery(models.Model):
    """One outbound notification to a consuming app about a payment.

    The consuming app (yvyreta) must learn that an installment was paid so
    it can mark it PAID and flip the plot to SOLD. Local-only state changes
    never propagate, so confirmation is PUSHED.

    Exactly one row per `(payment, event)`: that unique constraint is what
    makes a replayed gateway webhook (which `WebhookEvent` already absorbs)
    unable to produce a second outbound notification. The `delivery_id` is
    sent in the body and header so the RECEIVER can also dedupe, since a
    retry after an ambiguous timeout may legitimately re-send a payload the
    receiver already applied.
    """

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="callback_deliveries")
    delivery_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event = models.CharField(max_length=50, default="payment.confirmed")
    url = models.CharField(max_length=500)
    body = models.TextField(help_text="Exact JSON bytes signed and POSTed. Never contains secrets.")
    status = models.CharField(
        max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    next_attempt_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "event"], name="unique_payment_callback_event"
            ),
        ]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]

    def __str__(self) -> str:
        return f"CallbackDelivery({self.event} -> payment#{self.payment_id}, {self.status})"
