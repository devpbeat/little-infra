"""The ONLY module in this codebase allowed to `import pagopar_sdk`.

Design §1 boundary rule: third-party gateway SDKs are confined to a single
adapter module so they never leak into domain code, views, or tests. See
`payments/tests/test_adapter_boundary.py` for the fitness test that
enforces this.
"""

import os

import pagopar_sdk


def build_pagopar_client() -> pagopar_sdk.PagoparClient:
    """Build a `PagoparClient` from environment configuration.

    Sandbox availability is unconfirmed (see spike report
    sdd/payments-microservice/spike-pagopar) — `PAGOPAR_BASE_URL` defaults
    to the production API. Do not assume a sandbox exists.
    """
    return pagopar_sdk.PagoparClient(
        public_key=os.environ["PAGOPAR_PUBLIC_KEY"],
        private_key=os.environ["PAGOPAR_PRIVATE_KEY"],
        base_url=os.environ.get("PAGOPAR_BASE_URL", "https://api.pagopar.com"),
    )
