"""PagoparAdapter: implements the PaymentGateway port against Pagopar.

Imports from `.client` only — never `pagopar_sdk` directly. `client.py` is
the single module allowed to `import pagopar_sdk` (see its docstring and
`payments/tests/test_adapter_boundary.py`).
"""

import json
import os

from payments_core.ports.payment_gateway import (
    ChargeRequest,
    ChargeResult,
    ChargeStatus,
    PaymentGateway,
    WebhookVerificationResult,
)

from .client import build_pagopar_client
from .signature import verify_signature

# Pagopar order-status codes are not documented in the SDK (dataclasses
# only, no enum) — mapped defensively; anything unrecognized is treated
# as pending rather than silently misclassified.
_STATUS_MAP = {
    "pagado": ChargeStatus.CONFIRMED,
    "rechazado": ChargeStatus.FAILED,
    "cancelado": ChargeStatus.FAILED,
    "vencido": ChargeStatus.EXPIRED,
}


class PagoparAdapter(PaymentGateway):
    def __init__(self) -> None:
        self._client = build_pagopar_client()

    def create_charge(self, request: ChargeRequest) -> ChargeResult:
        raise NotImplementedError(
            "PagoparAdapter.create_charge requires the Buyer/PurchaseItem field mapping "
            "confirmed against Pagopar's real checkout requirements — deferred to Slice E1 "
            "(payment initiation), which owns the request-shaping decisions. This adapter "
            "class and its port wiring are the Slice C deliverable; the charge-creation body "
            "is intentionally stubbed here to avoid guessing checkout field semantics."
        )

    def get_charge_status(self, gateway_order_id: str) -> str:
        response = self._client.commerce.get_order(hash_pedido=gateway_order_id)
        raw_status = str(response.get("resultado", {}).get("estado", "")).lower()
        return _STATUS_MAP.get(raw_status, ChargeStatus.PENDING)

    def verify_webhook(self, headers: dict, body: bytes) -> WebhookVerificationResult:
        """Verify an inbound Pagopar webhook.

        See `signature.py` module docstring: the underlying algorithm is
        UNCONFIRMED against real Pagopar callback docs. This method wires
        the plumbing (payload parsing, DTO shape) so Slice E can focus on
        confirming the signature scheme rather than the wiring.
        """
        payload = json.loads(body)
        order_id = payload.get("id_pedido_comercio")
        status = payload.get("estado")
        provided_signature = headers.get("X-Pagopar-Signature", "")
        private_key = os.environ.get("PAGOPAR_PRIVATE_KEY", "")

        is_valid = bool(order_id and status and provided_signature) and verify_signature(
            private_key=private_key,
            order_id=str(order_id),
            status=str(status),
            provided_signature=provided_signature,
        )
        return WebhookVerificationResult(
            is_valid=is_valid,
            event_id=payload.get("id_pedido"),
            gateway_order_id=order_id,
            status=status,
        )
