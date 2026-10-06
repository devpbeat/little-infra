"""Factory for resolving the configured `PaymentGateway` adapter.

`settings.PAYMENT_GATEWAY` holds a dotted path (e.g.
`"adapters.fakes.fake_gateway.FakePaymentGateway"` or
`"adapters.pagopar.adapter.PagoparAdapter"`). Callers (views, webhook
handler) use this factory instead of importing an adapter directly, so
swapping gateways is a settings/env change, never a code change.
"""

from django.conf import settings
from django.utils.module_loading import import_string

from payments_core.ports.payment_gateway import PaymentGateway


def get_payment_gateway(credentials=None) -> PaymentGateway:
    """Build the configured adapter, optionally bound to specific credentials.

    `credentials=None` means "the global env key pair" — the Flow A
    behaviour. Flow B passes the collecting company's
    `GatewayCredentials` so the charge settles into THAT company's
    merchant account (see `payments_core.merchant_credentials`).
    """
    gateway_class = import_string(settings.PAYMENT_GATEWAY)
    return gateway_class(credentials=credentials)


def get_contract_signer():
    """Resolve the configured `ContractSigner` adapter (same pattern)."""
    signer_class = import_string(settings.CONTRACT_SIGNER)
    return signer_class()
