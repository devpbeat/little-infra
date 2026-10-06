"""The ONLY module in this codebase allowed to `import pagopar_sdk`.

Design §1 boundary rule: third-party gateway SDKs are confined to a single
adapter module so they never leak into domain code, views, or tests. See
`payments/tests/test_adapter_boundary.py` for the fitness test that
enforces this.
"""

import pagopar_sdk

from payments_core.merchant_credentials import GatewayCredentials, global_credentials


def build_pagopar_client(
    credentials: GatewayCredentials | None = None,
) -> pagopar_sdk.PagoparClient:
    """Build a `PagoparClient` for `credentials`, defaulting to the global env pair.

    Credentials are selected PER CHARGE now — a Flow B charge settles into
    the collecting company's merchant account, so its key pair must be used
    rather than whatever happens to be in process env. `credentials=None`
    keeps the Flow A behaviour (the SaaS owner's own account) exactly.

    Sandbox availability is unconfirmed (see spike report
    sdd/payments-microservice/spike-pagopar) — `PAGOPAR_BASE_URL` defaults
    to the production API. Do not assume a sandbox exists.
    """
    credentials = credentials or global_credentials()
    if not credentials.public_key or not credentials.private_key:
        raise RuntimeError(
            "No Pagopar credentials resolved. For a tenant charge, configure the "
            "MerchantAccount's key pair; for SaaS billing, set PAGOPAR_PUBLIC_KEY "
            "and PAGOPAR_PRIVATE_KEY."
        )
    return pagopar_sdk.PagoparClient(
        public_key=credentials.public_key,
        private_key=credentials.private_key,
        base_url=credentials.base_url,
    )
