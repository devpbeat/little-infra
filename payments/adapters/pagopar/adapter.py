"""PagoparAdapter: implements the PaymentGateway port against Pagopar.

Imports from `.client` only — never `pagopar_sdk` directly. `client.py` is
the single module allowed to `import pagopar_sdk` (see its docstring and
`payments/tests/test_adapter_boundary.py`). `create_charge` therefore builds
a plain dict matching `pagopar_sdk.models.StartTransactionRequest.to_payload()`'s
shape instead of importing the SDK's dataclasses directly — the SDK's
`CommerceAPI.create_transaction()` accepts either a `StartTransactionRequest`
or a plain `Mapping`, so this keeps the boundary rule intact with no loss of
functionality.
"""

import datetime
import json
import os

from django.utils import timezone

from payments_core.ports.payment_gateway import (
    ChargeRequest,
    ChargeResult,
    ChargeStatus,
    PaymentGateway,
    WebhookVerificationResult,
)

from .client import build_pagopar_client
from .signature import verify_signature

# Checkout payment window: how long the buyer has to complete a QR/checkout
# payment before Pagopar expires it. Not confirmed against product
# requirements or Pagopar defaults (see spike report, sdd/payments-microservice
# /spike-pagopar) — 3 days is a reasonable placeholder for a B2B monthly
# invoice and is intentionally generous. Revisit once real checkout
# behavior is observed against a live/sandbox order.
_CHECKOUT_WINDOW = datetime.timedelta(days=3)

# `tipo_pedido` and `forma_pago` are undocumented in the SDK (plain str/int
# passthrough fields with no enum in `models.py`). The values below are
# ASSUMPTIONS, not confirmed against Pagopar's own docs or support (out of
# scope for Task 0's spike, which only read the SDK source):
#   - tipo_pedido="1": a single, standard commerce order (as opposed to a
#     marketplace/split-payment order — this service always sells to one
#     merchant, itself, so the simplest order type is assumed correct).
#   - forma_pago=1: let the buyer choose their payment method at Pagopar's
#     checkout (QR included) rather than forcing a single method. This
#     matches the spec's "QR and other Pagopar methods" requirement without
#     the adapter needing to know Pagopar's full method-code table.
# If Pagopar rejects either value in practice, this is the first place to
# revisit; nothing else in this adapter or the port depends on the exact
# value chosen here.
_TIPO_PEDIDO_SINGLE_COMMERCE_ORDER = "1"
_FORMA_PAGO_LET_BUYER_CHOOSE = 1

# A single line item representing "this billing period" — Payment/Plan in
# this domain has no line-item concept of its own (it's a flat monthly fee),
# so `compras_items` (required by the SDK's payload shape) gets exactly one
# synthetic row describing the charge as a whole.
_LINE_ITEM_PRODUCT_ID = "subscription-period"
_LINE_ITEM_CATEGORY = "servicios"
# Pagopar requires a `ciudad` id (a documented catalog we don't have access
# to) for buyer and line-item city fields. "1" is ASSUMED to be Asunción's
# id per common Pagopar integration references — UNCONFIRMED. Revisit once
# Pagopar's city catalog is available.
_CIUDAD_ASUNCION_ASSUMED = "1"

# Pagopar order-status codes are not documented in the SDK (dataclasses
# only, no enum) — mapped defensively; anything unrecognized is treated
# as pending rather than silently misclassified. Reused for both order-status
# polling (`get_charge_status`) and inbound webhook payloads (`verify_webhook`)
# so a "confirmed" means the same thing everywhere in this adapter.
_STATUS_MAP = {
    "pagado": ChargeStatus.CONFIRMED,
    "rechazado": ChargeStatus.FAILED,
    "cancelado": ChargeStatus.FAILED,
    "vencido": ChargeStatus.EXPIRED,
}


def _map_status(raw_status: str) -> str:
    return _STATUS_MAP.get(str(raw_status or "").lower(), ChargeStatus.PENDING)


class PagoparAdapter(PaymentGateway):
    def __init__(self) -> None:
        self._client = build_pagopar_client()

    def create_charge(self, request: ChargeRequest) -> ChargeResult:
        """Create a Pagopar checkout/QR order for `request`.

        Field mapping is a REASONABLE, DOCUMENTED BEST EFFORT against the
        SDK's `StartTransactionRequest`/`Buyer`/`PurchaseItem` shapes (read
        from `pagopar_sdk.models` source, not live-tested) — see module
        docstring and the `_TIPO_PEDIDO_*`/`_FORMA_PAGO_*`/`_CIUDAD_*`
        constants above for every non-obvious assumption. This is
        intentionally NOT blocked on a product/Pagopar-support decision per
        the Slice E1 scope — if any assumed field is wrong, this is the
        single place to fix it.
        """
        deadline = (timezone.now() + _CHECKOUT_WINDOW).strftime("%Y-%m-%d")
        payload = {
            "id_pedido_comercio": request.order_id,
            "monto_total": request.amount_pyg,
            "tipo_pedido": _TIPO_PEDIDO_SINGLE_COMMERCE_ORDER,
            "forma_pago": _FORMA_PAGO_LET_BUYER_CHOOSE,
            "fecha_maxima_pago": deadline,
            "descripcion_resumen": request.description,
            "comprador": {
                "nombre": request.buyer_name,
                "email": request.buyer_email,
                "documento": request.buyer_document,
                "telefono": request.buyer_phone,
                "ciudad": _CIUDAD_ASUNCION_ASSUMED,
                "direccion": "",
                "coordenadas": "",
                "ruc": None,
                "razon_social": request.buyer_name,
                "tipo_documento": "CI",
                "direccion_referencia": None,
            },
            "compras_items": [
                {
                    "id_producto": _LINE_ITEM_PRODUCT_ID,
                    "nombre": request.description,
                    "descripcion": request.description,
                    "cantidad": 1,
                    "precio_total": request.amount_pyg,
                    "categoria": _LINE_ITEM_CATEGORY,
                    "ciudad": _CIUDAD_ASUNCION_ASSUMED,
                    "url_imagen": "",
                }
            ],
        }

        response = self._client.commerce.create_transaction(payload)

        # `resultado`'s exact shape for a successful `iniciar-transaccion`
        # call is UNCONFIRMED (spike only read `get_order`'s response shape
        # for status polling, not this endpoint's). Defensively accept
        # either a dict or a one-item list of dicts (both are common Pagopar
        # response conventions), and probe a few plausible key names for the
        # order hash / checkout URL rather than assuming one. If NONE of the
        # candidate keys are present, fail loudly rather than silently
        # returning an unusable ChargeResult.
        result = response.get("resultado")
        if isinstance(result, list):
            result = result[0] if result else {}
        if not isinstance(result, dict):
            result = {}

        gateway_order_id = (
            result.get("hash_pedido") or result.get("hash") or result.get("id_pedido") or ""
        )
        checkout_url = (
            result.get("url_pago") or result.get("url_boleta") or result.get("url") or None
        )
        if not gateway_order_id:
            raise ValueError(
                "Pagopar create_transaction response did not contain a recognized order-hash "
                f"field (checked hash_pedido/hash/id_pedido). Raw resultado: {result!r}"
            )

        return ChargeResult(
            gateway_order_id=str(gateway_order_id),
            checkout_url=checkout_url,
            raw=response,
        )

    def get_charge_status(self, gateway_order_id: str) -> str:
        response = self._client.commerce.get_order(hash_pedido=gateway_order_id)
        raw_status = response.get("resultado", {}).get("estado", "")
        return _map_status(raw_status)

    def verify_webhook(self, headers: dict, body: bytes) -> WebhookVerificationResult:
        """Verify an inbound Pagopar webhook.

        See `signature.py` module docstring: the underlying algorithm is
        UNCONFIRMED against real Pagopar callback docs. This method wires
        the plumbing (payload parsing, DTO shape) so Slice E can focus on
        confirming the signature scheme rather than the wiring.

        FAIL CLOSED (review finding W4): if `PAGOPAR_PRIVATE_KEY` is unset
        or empty, verification MUST reject the webhook rather than compare
        against a candidate signature computed with an empty key (which an
        attacker could trivially reproduce). An unconfigured deployment
        must never silently accept forged webhooks.
        """
        payload = json.loads(body)
        order_id = payload.get("id_pedido_comercio")
        raw_status = payload.get("estado")
        provided_signature = headers.get("X-Pagopar-Signature", "")
        private_key = os.environ.get("PAGOPAR_PRIVATE_KEY", "")

        is_valid = (
            bool(private_key)
            and bool(order_id and raw_status and provided_signature)
            and verify_signature(
                private_key=private_key,
                order_id=str(order_id),
                status=str(raw_status),
                provided_signature=provided_signature,
            )
        )
        return WebhookVerificationResult(
            is_valid=is_valid,
            event_id=payload.get("id_pedido"),
            gateway_order_id=order_id,
            status=_map_status(raw_status) if is_valid else raw_status,
        )
