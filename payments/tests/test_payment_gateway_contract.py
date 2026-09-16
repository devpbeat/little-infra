"""Shared port-contract tests, run against every PaymentGateway implementation.

Only `FakePaymentGateway` is exercised here. A `@pytest.mark.live` variant
against the real `PagoparAdapter` can be added once create_charge is
implemented (Slice E) and sandbox/live credentials are available — never
run automatically in CI.
"""

import pytest

from adapters.fakes.fake_gateway import FakePaymentGateway
from payments_core.ports.payment_gateway import ChargeRequest, ChargeStatus


@pytest.fixture(params=[FakePaymentGateway])
def gateway(request):
    return request.param()


def _sample_request() -> ChargeRequest:
    return ChargeRequest(
        order_id="order-1",
        amount_pyg=150_000,
        description="Pro plan",
        buyer_name="Ada Lovelace",
        buyer_email="ada@example.com",
        buyer_document="1234567",
        buyer_phone="+595981000000",
    )


def test_create_charge_returns_gateway_order_id(gateway):
    result = gateway.create_charge(_sample_request())
    assert result.gateway_order_id

def test_new_charge_status_is_pending(gateway):
    result = gateway.create_charge(_sample_request())
    assert gateway.get_charge_status(result.gateway_order_id) == ChargeStatus.PENDING
