"""In-memory PaymentGateway fake for tests and local development.

Never call a real gateway from tests. This fake is the default adapter
selected via `settings.PAYMENT_GATEWAY` until a deployment configures a
real one.
"""

import itertools

from payments_core.ports.payment_gateway import (
    ChargeRequest,
    ChargeResult,
    ChargeStatus,
    PaymentGateway,
    WebhookVerificationResult,
)


class FakePaymentGateway(PaymentGateway):
    """Deterministic in-memory gateway. Statuses are controllable for tests."""

    _counter = itertools.count(1)

    def __init__(self) -> None:
        self._orders: dict[str, str] = {}

    def create_charge(self, request: ChargeRequest) -> ChargeResult:
        gateway_order_id = f"fake-order-{next(self._counter)}"
        self._orders[gateway_order_id] = ChargeStatus.PENDING
        return ChargeResult(
            gateway_order_id=gateway_order_id,
            checkout_url=f"https://fake-gateway.test/checkout/{gateway_order_id}",
            raw={"order_id": request.order_id, "amount_pyg": request.amount_pyg},
        )

    def get_charge_status(self, gateway_order_id: str) -> str:
        return self._orders.get(gateway_order_id, ChargeStatus.PENDING)

    def set_status(self, gateway_order_id: str, status: str) -> None:
        """Test helper: force a charge into a given status."""
        self._orders[gateway_order_id] = status

    def verify_webhook(self, headers: dict, body: bytes) -> WebhookVerificationResult:
        import json

        payload = json.loads(body)
        return WebhookVerificationResult(
            is_valid=True,
            event_id=payload.get("event_id"),
            gateway_order_id=payload.get("gateway_order_id"),
            status=payload.get("status"),
        )
