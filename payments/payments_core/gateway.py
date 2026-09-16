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


def get_payment_gateway() -> PaymentGateway:
    gateway_class = import_string(settings.PAYMENT_GATEWAY)
    return gateway_class()
