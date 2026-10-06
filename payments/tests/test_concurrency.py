"""Concurrency fitness tests for the two money-moving paths.

These run on real threads against real connections (`transaction=True`), so
the row locks are actually exercised — a `select_for_update` that is missing
or scoped wrong fails here and nowhere else.
"""

import threading

import pytest
from django.db import close_old_connections
from django.utils import timezone

from apps.billing import callbacks, views
from apps.billing.models import CallbackDelivery, DeliveryStatus, Payment, PaymentStatus
from apps.customers.models import Customer
from apps.merchants.models import MerchantAccount
from payments_core.ports.payment_gateway import ChargeResult
from tests.conftest import authed_client

CHARGES = "/api/v1/charges"


def run_concurrently(target, times=2):
    """Run `target()` on `times` threads released as close together as possible."""
    start = threading.Barrier(times)
    results, errors = [], []

    def runner():
        try:
            start.wait(timeout=10)
            results.append(target())
        except Exception as exc:  # surfaced below so a thread failure is not silent
            errors.append(exc)
        finally:
            close_old_connections()

    threads = [threading.Thread(target=runner) for _ in range(times)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not errors, errors
    return results


@pytest.mark.django_db(transaction=True)
class TestConcurrentChargeRetry:
    def test_two_simultaneous_retries_create_only_one_gateway_order(
        self, settings, monkeypatch, django_db_serialized_rollback
    ):
        """Without the row lock, both retries would charge the buyer."""
        settings.PAYMENT_CALLBACKS_DISPATCH = False

        from django.contrib.auth.hashers import make_password

        from apps.apps_registry.models import ApiKey, ConsumingApp

        app = ConsumingApp.objects.create(name="concurrency-app")
        ApiKey.objects.create(app=app, prefix="conc1234", hashed_secret=make_password("s3cret"))
        raw_key = "conc1234.s3cret"
        merchant = MerchantAccount.objects.create(
            app=app, external_ref="company-c", public_key="pub-c"
        )
        merchant.set_private_key("priv-c")
        merchant.save()
        customer = Customer.objects.create(app=app, external_ref="buyer-c")
        # A previous attempt that failed: the retryable state.
        Payment.objects.create(
            app=app,
            kind="one_off",
            customer=customer,
            merchant_account=merchant,
            external_ref="installment:conc",
            amount_pyg=1_000_000,
            status=PaymentStatus.FAILED,
            gateway="pagopar",
        )

        calls = []
        lock = threading.Lock()

        class CountingGateway:
            def __init__(self, credentials=None):
                pass

            def create_charge(self, request):
                with lock:
                    calls.append(request.order_id)
                return ChargeResult(
                    gateway_order_id=f"hash-{len(calls)}",
                    checkout_url="https://x.test",
                    raw={},
                )

        monkeypatch.setattr(
            views, "get_payment_gateway", lambda credentials=None: CountingGateway()
        )

        body = {
            "external_ref": "installment:conc",
            "amount_pyg": 1_000_000,
            "description": "Cuota concurrente",
            "customer_ref": "buyer-c",
            "merchant_ref": "company-c",
        }
        statuses = run_concurrently(
            lambda: authed_client(raw_key).post(CHARGES, body, format="json").status_code
        )

        assert len(calls) == 1, f"gateway charged {len(calls)} times: {calls}"
        assert sorted(statuses) == [200, 201]
        payment = Payment.objects.get(app=app, external_ref="installment:conc")
        assert payment.charge_attempts == 1
        assert payment.gateway_order_id == "hash-1"


@pytest.mark.django_db(transaction=True)
class TestConcurrentCallbackDelivery:
    def test_two_simultaneous_deliveries_post_once(self, settings, monkeypatch):
        """Without SKIP LOCKED claiming, yvyreta would be notified twice."""

        from apps.apps_registry.models import ConsumingApp

        app = ConsumingApp.objects.create(name="callback-conc-app")
        app.callback_url = "https://yvyreta.test/webhooks/payments"
        app.set_callback_secret("shared-secret")
        app.save()
        customer = Customer.objects.create(app=app, external_ref="buyer-cb")
        merchant = MerchantAccount.objects.create(
            app=app, external_ref="company-cb", public_key="pub-cb"
        )
        merchant.set_private_key("priv-cb")
        merchant.save()
        payment = Payment.objects.create(
            app=app,
            kind="one_off",
            customer=customer,
            merchant_account=merchant,
            external_ref="installment:cb",
            amount_pyg=1_000_000,
            status=PaymentStatus.CONFIRMED,
            confirmed_at=timezone.now(),
            gateway="pagopar",
            gateway_order_id="hash-cb",
        )
        delivery = callbacks.enqueue_payment_callback(payment)

        posted = []
        lock = threading.Lock()

        def slow_post(url, body, headers, timeout):
            with lock:
                posted.append(headers["X-Payments-Delivery"])
            return 200

        monkeypatch.setattr(callbacks, "post_json", slow_post)

        run_concurrently(lambda: callbacks.deliver(delivery))

        assert len(posted) == 1, f"delivered {len(posted)} times"
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.DELIVERED
        assert delivery.attempts == 1
        assert CallbackDelivery.objects.count() == 1
