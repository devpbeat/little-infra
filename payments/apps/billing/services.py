"""Billing domain services: payment confirmation and period extension.

Kept out of views.py so the webhook handler and any future reconciliation
job (design §6 D1's "advance_billing" fallback) share exactly one
implementation of "what does a confirmed payment mean for a subscription".
"""

import datetime

from django.db import transaction
from django.utils import timezone

from apps.subscriptions.models import Subscription, SubscriptionStatus
from payments_core.ports.payment_gateway import ChargeStatus

from .models import Payment, PaymentStatus


def apply_gateway_status(payment: Payment, gateway_status: str) -> Payment:
    """Apply a gateway-reported status to `payment`, with side effects.

    Idempotent by construction: if `payment` is already `confirmed`, a
    repeat "confirmed" report is a no-op (period extension happens exactly
    once per Payment, per spec: payment-processing "Webhook Idempotency and
    Failure Handling"). Must be called with `payment` already locked
    (`select_for_update`) by the caller when invoked from a concurrent
    context such as a webhook handler.
    """
    if gateway_status == ChargeStatus.CONFIRMED:
        return _confirm(payment)
    if gateway_status == ChargeStatus.FAILED:
        return _fail(payment)
    if gateway_status == ChargeStatus.EXPIRED:
        return _expire(payment)
    # PENDING or unrecognized: nothing to do yet.
    return payment


def _confirm(payment: Payment) -> Payment:
    if payment.status == PaymentStatus.CONFIRMED:
        return payment  # already applied — replay/duplicate report, no-op.

    now = timezone.now()
    payment.status = PaymentStatus.CONFIRMED
    payment.confirmed_at = now
    payment.save(update_fields=["status", "confirmed_at", "updated_at"])
    _extend_subscription_period(payment.subscription, now=now)
    return payment


def _fail(payment: Payment) -> Payment:
    if payment.status in (PaymentStatus.CONFIRMED, PaymentStatus.FAILED):
        return payment
    payment.status = PaymentStatus.FAILED
    payment.save(update_fields=["status", "updated_at"])
    return payment


def _expire(payment: Payment) -> Payment:
    if payment.status in (PaymentStatus.CONFIRMED, PaymentStatus.EXPIRED):
        return payment
    payment.status = PaymentStatus.EXPIRED
    payment.save(update_fields=["status", "updated_at"])
    return payment


def _extend_subscription_period(subscription: Subscription, *, now) -> None:
    """Extend `subscription`'s current period by one `plan.period_days`.

    Per the customer-initiated renewal model (decision:
    sdd/payments-microservice renewal-model #752): each confirmed payment
    buys exactly one more period, starting from whichever is later — the
    existing `current_period_end` (renewing before lapse) or `now`
    (renewing after a lapse, so the customer doesn't get "free" backdated
    days). A trialing subscription that pays is promoted straight to
    `active`.
    """
    base = subscription.current_period_end
    if base is None or base < now:
        base = now
    subscription.current_period_end = base + datetime.timedelta(
        days=subscription.plan.period_days
    )
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.save(update_fields=["current_period_end", "status"])


@transaction.atomic
def process_webhook_status(gateway: str, gateway_order_id: str, gateway_status: str) -> Payment | None:
    """Lock the Payment matching `(gateway, gateway_order_id)` and apply `gateway_status`.

    Returns `None` if no Payment matches (unknown `gateway_order_id` — the
    caller already persisted a `WebhookEvent` for forensics; there is simply
    no payment row to transition, which is not itself an error worth
    surfacing to the gateway as a failure).
    """
    payment = (
        Payment.objects.select_for_update()
        .filter(gateway=gateway, gateway_order_id=gateway_order_id)
        .select_related("subscription__plan")
        .first()
    )
    if payment is None:
        return None
    return apply_gateway_status(payment, gateway_status)
