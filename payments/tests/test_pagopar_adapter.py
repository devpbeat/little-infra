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
from adapters.pagopar.signature import candidate_tokens, verify_token
from payments_core.ports.payment_gateway import ChargeRequest, ChargeStatus


@pytest.fixture(autouse=True)
def pagopar_env(monkeypatch):
    monkeypatch.setenv("PAGOPAR_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("PAGOPAR_PRIVATE_KEY", "test-private")
    monkeypatch.setenv("PAGOPAR_BASE_URL", "https://api.pagopar.test")


def _sample_charge_request() -> ChargeRequest:
    return ChargeRequest(
        order_id="42",
        amount_pyg=500_000,
        description="Standard Monthly",
        buyer_name="Ada Lovelace",
        buyer_email="ada@example.com",
        buyer_document="1234567",
        buyer_phone="+595981000000",
    )


class TestCreateCharge:
    @respx.mock
    def test_returns_gateway_order_id_and_checkout_url(self):
        respx.post("https://api.pagopar.test/api/comercios/2.0/iniciar-transaccion").mock(
            return_value=Response(
                200,
                json={
                    "respuesta": True,
                    "resultado": [{"hash_pedido": "hash-abc", "url_pago": "https://pagopar.test/pay/hash-abc"}],
                },
            )
        )
        adapter = PagoparAdapter()

        result = adapter.create_charge(_sample_charge_request())

        assert result.gateway_order_id == "hash-abc"
        assert result.checkout_url == "https://pagopar.test/pay/hash-abc"

    @respx.mock
    def test_accepts_dict_shaped_resultado(self):
        respx.post("https://api.pagopar.test/api/comercios/2.0/iniciar-transaccion").mock(
            return_value=Response(
                200,
                json={"respuesta": True, "resultado": {"hash_pedido": "hash-xyz", "url": "https://pagopar.test/x"}},
            )
        )
        adapter = PagoparAdapter()

        result = adapter.create_charge(_sample_charge_request())

        assert result.gateway_order_id == "hash-xyz"
        assert result.checkout_url == "https://pagopar.test/x"

    @respx.mock
    def test_raises_loudly_when_no_order_hash_is_present(self):
        respx.post("https://api.pagopar.test/api/comercios/2.0/iniciar-transaccion").mock(
            return_value=Response(200, json={"respuesta": True, "resultado": {}})
        )
        adapter = PagoparAdapter()

        with pytest.raises(ValueError):
            adapter.create_charge(_sample_charge_request())


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


def _callback_body(
    hash_pedido: str,
    *,
    pagado: bool = False,
    cancelado: bool = False,
    token: str = "",
    monto: str = "10000.00",
    numero_pedido: str = "22641115",
) -> bytes:
    """Real Pagopar callback shape, captured from staging on 2026-09-17."""
    return json.dumps(
        {
            "resultado": [
                {
                    "pagado": pagado,
                    "cancelado": cancelado,
                    "monto": monto,
                    "numero_pedido": numero_pedido,
                    "hash_pedido": hash_pedido,
                    "token": token,
                }
            ],
            "respuesta": True,
        }
    ).encode()


class TestVerifyWebhook:
    def test_valid_token_is_accepted(self, pagopar_env):
        private_key = os.environ["PAGOPAR_PRIVATE_KEY"]
        token = candidate_tokens(
            private_key, hash_pedido="hash-1", numero_pedido="22641115", monto="10000.00"
        )["priv+hash_pedido"]

        adapter = PagoparAdapter()
        result = adapter.verify_webhook({}, _callback_body("hash-1", pagado=True, token=token))

        assert result.is_valid is True
        assert result.gateway_order_id == "hash-1"
        assert result.status == ChargeStatus.CONFIRMED
        assert result.event_id == f"hash-1:{ChargeStatus.CONFIRMED}"

    def test_each_candidate_construction_is_accepted(self, pagopar_env):
        private_key = os.environ["PAGOPAR_PRIVATE_KEY"]
        for name, token in candidate_tokens(
            private_key, hash_pedido="hash-1", numero_pedido="22641115", monto="10000.00"
        ).items():
            adapter = PagoparAdapter()
            result = adapter.verify_webhook(
                {}, _callback_body("hash-1", pagado=True, token=token)
            )
            assert result.is_valid is True, f"candidate {name} should verify"

    def test_invalid_token_is_rejected(self, pagopar_env):
        adapter = PagoparAdapter()
        result = adapter.verify_webhook(
            {}, _callback_body("hash-1", pagado=True, token="wrong")
        )

        assert result.is_valid is False

    def test_missing_token_is_rejected(self, pagopar_env):
        adapter = PagoparAdapter()
        result = adapter.verify_webhook({}, _callback_body("hash-1", pagado=True))

        assert result.is_valid is False

    def test_cancelado_maps_to_failed(self, pagopar_env):
        private_key = os.environ["PAGOPAR_PRIVATE_KEY"]
        token = candidate_tokens(
            private_key, hash_pedido="hash-1", numero_pedido="22641115", monto="10000.00"
        )["priv+hash_pedido"]

        adapter = PagoparAdapter()
        result = adapter.verify_webhook(
            {}, _callback_body("hash-1", cancelado=True, token=token)
        )

        assert result.is_valid is True
        assert result.status == ChargeStatus.FAILED

    def test_unpaid_uncancelled_maps_to_pending(self, pagopar_env):
        private_key = os.environ["PAGOPAR_PRIVATE_KEY"]
        token = candidate_tokens(
            private_key, hash_pedido="hash-1", numero_pedido="22641115", monto="10000.00"
        )["priv+hash_pedido"]

        adapter = PagoparAdapter()
        result = adapter.verify_webhook({}, _callback_body("hash-1", token=token))

        assert result.is_valid is True
        assert result.status == ChargeStatus.PENDING


class TestSignatureHelpers:
    def test_verify_token_returns_matching_candidate_name(self):
        token = candidate_tokens(
            "secret", hash_pedido="h1", numero_pedido="n1", monto="5000.00"
        )["priv+numero_pedido+monto"]
        assert (
            verify_token(
                private_key="secret",
                provided_token=token,
                hash_pedido="h1",
                numero_pedido="n1",
                monto="5000.00",
            )
            == "priv+numero_pedido+monto"
        )

    def test_verify_token_rejects_empty_key(self):
        token = candidate_tokens("", hash_pedido="h1", numero_pedido="n1", monto="5000.00")[
            "priv+hash_pedido"
        ]
        assert (
            verify_token(
                private_key="",
                provided_token=token,
                hash_pedido="h1",
                numero_pedido="n1",
                monto="5000.00",
            )
            is None
        )
