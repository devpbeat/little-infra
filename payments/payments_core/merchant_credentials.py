"""Resolving WHICH gateway credentials a charge is created with.

Two money flows, one service:

- Flow A (SaaS subscriptions): the SaaS owner charges tenant companies. The
  money belongs in the SaaS owner's account, so the global `PAGOPAR_*` env
  pair is CORRECT — and stays the fallback so Flow A is untouched.
- Flow B (a tenant charges its own buyers): the money belongs in the
  COLLECTING COMPANY's account. A `MerchantAccount` supplies it.

Resolution:
- a `MerchantAccount` was passed -> ITS key pair, or a hard error. There is
  deliberately NO fallback here: silently charging into the global account
  because a tenant's row is half-configured is the exact compliance failure
  this module exists to prevent.
- no merchant was passed -> the global env pair (Flow A).
"""

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.pagopar.com"


class UnusableMerchantAccount(Exception):
    """A merchant account was named for a charge but cannot be charged with."""

@dataclass(frozen=True, slots=True)
class GatewayCredentials:
    """A gateway key pair plus its endpoint. Never log or serialize this."""

    public_key: str
    private_key: str
    base_url: str

    def __repr__(self) -> str:  # defensive: keep secrets out of tracebacks/logs
        return f"GatewayCredentials(public_key={self.public_key!r}, private_key='***')"

def global_credentials() -> GatewayCredentials:
    """The SaaS owner's own merchant account, from process env (Flow A)."""
    return GatewayCredentials(
        public_key=os.environ.get("PAGOPAR_PUBLIC_KEY", ""),
        private_key=os.environ.get("PAGOPAR_PRIVATE_KEY", ""),
        base_url=os.environ.get("PAGOPAR_BASE_URL", DEFAULT_BASE_URL),
    )

def resolve_credentials(*, merchant=None) -> GatewayCredentials:
    """Credentials for a charge. FAILS rather than falling back for a merchant.

    Raises `UnusableMerchantAccount` when a merchant account is named but has
    no key pair. Callers must surface that as a 4xx — never as "we used the
    SaaS owner's account instead", which would move a buyer's money to the
    wrong company with no error anywhere.
    """
    if merchant is not None:
        if not merchant.has_credentials:
            raise UnusableMerchantAccount(
                f"MerchantAccount '{merchant.external_ref}' has no gateway credentials "
                "configured; refusing to fall back to the global merchant account."
            )
        return GatewayCredentials(
            public_key=merchant.public_key,
            private_key=merchant.get_private_key(),
            base_url=merchant.base_url or os.environ.get("PAGOPAR_BASE_URL", DEFAULT_BASE_URL),
        )
    return global_credentials()

def credentials_for_payment(payment) -> GatewayCredentials:
    """Credentials for an existing `Payment` — used by webhook verification.

    A Flow B webhook is signed with the COLLECTING COMPANY's private key, so
    verifying it against the global key would always fail. The claimed order
    id selects the row; verification still proves key knowledge.
    """
    return resolve_credentials(merchant=getattr(payment, "merchant_account", None))
