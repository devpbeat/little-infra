"""PagoparAdapter tests against recorded/mocked HTTP responses (respx).

Never call the real Pagopar API from tests — `--disable-socket` in
pyproject.toml already blocks real outbound sockets by default.
"""

import json
import os

import pytest
import respx
from httpx import Response

from adapters.pagopar.adapter import PagoparAdapter
from adapters.pagopar.signature import compute_candidate_signature, verify_signature
from payments_core.ports.payment_gateway import ChargeStatus


@pytest.fixture(autouse=True)
def pagopar_env(monkeypatch):
    monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "test-private")
    monkeypatch.setenv("PAGOPAR_BASE_URL", "https://api.pagopar.test")


class TestGetChargeStatus:
    @respx.mock
    def test_maps_pagado_to_confirmed(self):
        respx.post("https://api.pagopar.test/api/pedidos/1.1/traer").mock(
            return_value=Response(200, json={"respuesta": True, "resultado": {"estado": "pagado"}})
        )
        adapter = PagoparAdapter()

        assert adapter.get_charge_status("hash-1") == ChargeStatus.CONFIRMED

    @respx.mock
    def test_maps_rechazado_to_failed(self):
        respx.post("https://api.pagopar.test/api/pedidos/1.1/traer").mock(
            return_value=Response(200, json={"respuesta": True, "resultado": {"estado": "rechazado"}})
        )
        adapter = PagoparAdapter()

        assert adapter.get_charge_status("hash-1") == ChargeStatus.FAILED

    @respx.mock
    def test_unknown_status_defaults_to_pending(self):
        respx.post("https://api.pagopar.test/api/pedidos/1.1/traer").mock(
            return_value=Response(200, json={"respuesta": True, "resultado": {"estado": "algo-nuevo"}})
        )
        adapter = PagoparAdapter()

        assert adapter.get_charge_status("hash-1") == ChargeStatus.PENDING


class TestVerifyWebhook:
    def test_valid_signature_is_accepted(self, pagopar_env):
        private_key = os.environ["PAGOPAR_PRIVATE_KEY"]
        signature = compute_candidate_signature(private_key, "order-1", "pagado")
        body = json.dumps(
            {"id_pedido_comercio": "order-1", "estado": "pagado", "id_pedido": "evt-1"}
        ).encode()

        adapter = PagoparAdapter()
        result = adapter.verify_webhook({"X-Pagopar-Signature": signature}, body)

        assert result.is_valid is True
        assert result.gateway_order_id == "order-1"
        assert result.event_id == "evt-1"

    def test_invalid_signature_is_rejected(self, pagopar_env):
        body = json.dumps(
            {"id_pedido_comercio": "order-1", "estado": "pagado", "id_pedido": "evt-1"}
        ).encode()

        adapter = PagoparAdapter()
        result = adapter.verify_webhook({"X-Pagopar-Signature": "wrong"}, body)

        assert result.is_valid is False

    def test_missing_signature_header_is_rejected(self, pagopar_env):
        body = json.dumps({"id_pedido_comercio": "order-1", "estado": "pagado"}).encode()

        adapter = PagoparAdapter()
        result = adapter.verify_webhook({}, body)

        assert result.is_valid is False


class TestSignatureHelpers:
    def test_verify_signature_matches_candidate(self):
        candidate = compute_candidate_signature("secret", "order-1", "pagado")
        assert verify_signature(
            private_key="secret", order_id="order-1", status="pagado", provided_signature=candidate
        )

    def test_verify_signature_rejects_tampered_status(self):
        candidate = compute_candidate_signature("secret", "order-1", "pagado")
        assert not verify_signature(
            private_key="secret", order_id="order-1", status="rechazado", provided_signature=candidate
        )
