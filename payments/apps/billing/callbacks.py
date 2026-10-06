"""Outbound, signed payment-confirmation callbacks to consuming apps.

WHY PUSH RATHER THAN POLL: yvyreta must flip an `Installment` to PAID and a
plot to SOLD the moment Pagopar confirms. Polling would mean every consuming
app running a scheduler against `payments/{id}` for every open charge —
130-month installment plans across many companies — to learn something this
service already knows within milliseconds of the gateway webhook. Polling is
still fully supported as a fallback (`GET /payments/{id}` is authoritative),
but it is not the primary path.

Security properties:
- SIGNED: `X-Payments-Signature: sha256=<hmac>` over `"{timestamp}.{body}"`
  with the app's shared secret. The timestamp is in the signed string and in
  `X-Payments-Timestamp` so the receiver can reject stale replays.
- IDEMPOTENT: one `CallbackDelivery` per `(payment, event)` (DB constraint),
  and a stable `delivery_id` in body + header so the receiver can dedupe a
  retry that duplicates a delivery it already applied.
- RETRIED: exponential backoff, capped attempts, then `failed` and left for
  an operator. Sweeping is done by `manage.py dispatch_callbacks` (cron) so a
  recycled worker never loses a pending delivery.

Transport deliberately uses stdlib `urllib` and an in-process daemon thread:
this service has no broker (same tradeoff documented in
`apps/contracts/jobs.py`), and the cron sweep covers the worker-recycled case.
"""

import datetime
import hashlib
import hmac
import json
import logging
import threading
import urllib.error
import urllib.request

from django.conf import settings
from django.db import IntegrityError, close_old_connections, transaction
from django.utils import timezone

from .models import CallbackDelivery, DeliveryStatus, PaymentStatus

logger = logging.getLogger(__name__)

CALLBACK_EVENT_CONFIRMED = "payment.confirmed"
CALLBACK_MAX_ATTEMPTS = 8
CALLBACK_TIMEOUT_SECONDS = 10
CALLBACK_BACKOFF_BASE_SECONDS = 30

def build_signature(*, secret: str, timestamp: str, body: str) -> str:
    """`sha256=<hex hmac>` over `"{timestamp}.{body}"` — the wire contract.

    The timestamp is inside the signed string on purpose: signing the body
    alone would let an intercepted delivery be replayed forever.
    """
    mac = hmac.new(
        secret.encode("utf-8"), f"{timestamp}.{body}".encode(), hashlib.sha256
    )
    return f"sha256={mac.hexdigest()}"

def _build_body(payment, event: str, delivery_id) -> str:
    """The callback payload. Contains NO credentials and no other tenant's data."""
    return json.dumps(
        {
            "delivery_id": str(delivery_id),
            "event": event,
            "payment_id": payment.pk,
            "kind": payment.kind,
            "external_ref": payment.external_ref,
            "customer_ref": payment.customer.external_ref if payment.customer_id else None,
            "merchant_ref": (
                payment.merchant_account.external_ref if payment.merchant_account_id else None
            ),
            "amount_pyg": payment.amount_pyg,
            "status": payment.status,
            "gateway": payment.gateway,
            "gateway_order_id": payment.gateway_order_id,
            "confirmed_at": payment.confirmed_at.isoformat() if payment.confirmed_at else None,
        },
        separators=(",", ":"),
        sort_keys=True,
    )

def enqueue_payment_callback(payment, event: str = CALLBACK_EVENT_CONFIRMED):
    """Create the single delivery row for `(payment, event)`, or return None.

    Returns None when the app opted out (no `callback_url`/secret) or when a
    delivery for this `(payment, event)` already exists — which is how a
    replayed gateway webhook is absorbed.
    """
    app = payment.app
    if not app.callbacks_enabled:
        return None

    delivery = CallbackDelivery(
        payment=payment,
        event=event,
        url=app.callback_url,
        next_attempt_at=timezone.now(),
    )
    delivery.body = _build_body(payment, event, delivery.delivery_id)
    try:
        with transaction.atomic():
            delivery.save()
    except IntegrityError:
        return None
    return delivery

def post_json(url: str, body: str, headers: dict, timeout: int) -> int:
    """POST `body` and return the HTTP status code. Seam for tests."""
    request = urllib.request.Request(
        url, data=body.encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code

def deliver(delivery: CallbackDelivery) -> bool:
    """Attempt one delivery. Returns True on success.

    The row is CLAIMED with `SELECT ... FOR UPDATE SKIP LOCKED` and the lock is
    held across the HTTP call. A plain "refresh, check status, POST" is not
    enough: the cron sweep and the in-process thread (or two app processes both
    running the sweep) can both read `pending` before either of them POSTs, and
    the consuming app receives `payment.confirmed` twice. `skip_locked` makes
    the loser a no-op instead of a second notification.

    The DB uniqueness on `(payment, event)` only stops a second delivery ROW;
    it does nothing about two workers processing the same row.
    """
    with transaction.atomic():
        claimed = (
            # `of=("self",)` locks ONLY the delivery row: the joined payment
            # relations below are nullable, i.e. LEFT JOINs, and Postgres
            # refuses FOR UPDATE on the nullable side of an outer join.
            CallbackDelivery.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("payment__app", "payment__customer", "payment__merchant_account")
            .filter(pk=delivery.pk, status=DeliveryStatus.PENDING)
            .first()
        )
        if claimed is None:
            # Either already terminal, or another worker holds it right now.
            delivery.refresh_from_db()
            return delivery.status == DeliveryStatus.DELIVERED
        ok = _attempt(claimed)
    delivery.refresh_from_db()
    return ok


def _attempt(delivery: CallbackDelivery) -> bool:
    """One signed POST plus the resulting state transition. Caller holds the lock."""
    secret = delivery.payment.app.get_callback_secret()
    timestamp = str(int(timezone.now().timestamp()))
    headers = {
        "Content-Type": "application/json",
        "X-Payments-Event": delivery.event,
        "X-Payments-Delivery": str(delivery.delivery_id),
        "X-Payments-Timestamp": timestamp,
        "X-Payments-Signature": build_signature(
            secret=secret, timestamp=timestamp, body=delivery.body
        ),
    }

    delivery.attempts += 1
    try:
        code = post_json(delivery.url, delivery.body, headers, CALLBACK_TIMEOUT_SECONDS)
        ok = 200 <= int(code) < 300
        error = "" if ok else f"HTTP {code}"
    except Exception as exc:  # network/DNS/TLS — all retryable
        ok, error = False, str(exc)[:2000]

    now = timezone.now()
    if ok:
        delivery.status = DeliveryStatus.DELIVERED
        delivery.delivered_at = now
        delivery.last_error = ""
    else:
        delivery.last_error = error
        if delivery.attempts >= CALLBACK_MAX_ATTEMPTS:
            delivery.status = DeliveryStatus.FAILED
            logger.error(
                "callback delivery %s gave up after %s attempts: %s",
                delivery.delivery_id,
                delivery.attempts,
                error,
            )
        else:
            delivery.next_attempt_at = now + datetime.timedelta(
                seconds=CALLBACK_BACKOFF_BASE_SECONDS * (2 ** (delivery.attempts - 1))
            )
    delivery.save(
        update_fields=[
            "status",
            "attempts",
            "last_error",
            "next_attempt_at",
            "delivered_at",
        ]
    )
    return ok

def dispatch_pending(limit: int = 100) -> int:
    """Deliver every due pending callback. Entry point for the cron sweep."""
    due = (
        CallbackDelivery.objects.filter(
            status=DeliveryStatus.PENDING, next_attempt_at__lte=timezone.now()
        )
        .select_related("payment__app")
        .order_by("next_attempt_at")[:limit]
    )
    delivered = 0
    for delivery in list(due):
        # `deliver` claims each row with SKIP LOCKED, so a sweep running
        # concurrently with another sweep or with the in-process thread simply
        # skips whatever is already in flight.
        if deliver(delivery):
            delivered += 1
    return delivered

def _deliver_in_thread(delivery_id: int) -> None:
    try:
        delivery = CallbackDelivery.objects.select_related("payment__app").get(pk=delivery_id)
        deliver(delivery)
    except CallbackDelivery.DoesNotExist:
        # Should be unreachable: the thread is started from `on_commit`, so the
        # row is committed before it runs. Logged as a warning rather than
        # swallowed, because if it DOES happen the only thing still covering
        # the delivery is the `dispatch_callbacks` sweep.
        logger.warning("callback delivery %s vanished before dispatch", delivery_id)
    except Exception:
        logger.exception("callback delivery thread failed for %s", delivery_id)
    finally:
        close_old_connections()

def notify_payment_confirmed(payment) -> None:
    """Enqueue and (unless disabled) immediately attempt the confirmation callback.

    Called from `services._confirm`, i.e. once per Payment, by construction.
    Dispatch is skipped when `PAYMENT_CALLBACKS_DISPATCH` is False (tests),
    leaving the row for `dispatch_pending`.

    Dispatch is deferred with `transaction.on_commit`. `_confirm` runs inside
    `process_webhook_status`'s atomic block, so a thread started inline would
    open its OWN connection and could look the delivery row up BEFORE that
    transaction committed — losing the first attempt to a `DoesNotExist` and
    leaving the notification sitting until the next cron sweep.
    """
    if payment.status != PaymentStatus.CONFIRMED:
        return
    delivery = enqueue_payment_callback(payment)
    if delivery is None:
        return
    if not getattr(settings, "PAYMENT_CALLBACKS_DISPATCH", True):
        return
    delivery_id = delivery.pk
    if getattr(settings, "PAYMENT_CALLBACKS_SYNC", False):
        transaction.on_commit(lambda: _deliver_in_thread(delivery_id))
        return
    transaction.on_commit(
        lambda: threading.Thread(
            target=_deliver_in_thread, args=(delivery_id,), daemon=True
        ).start()
    )
