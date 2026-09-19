"""Built-in click-to-sign adapter — no external e-signature provider.

The "envelope" is an unguessable capability token; the signing ceremony
is this service's own public page (`/contracts/sign/<token>` on the
dashboard), where the signer reads the rendered document and accepts it
with name + document id. A simple electronic signature in the sense of
Paraguay's Ley 4017/2010 — adequate for B2B SaaS click-wrap acceptance,
chosen over DocuSeal because its per-document API is Pro-only (decision
2026-09-19). The ContractSigner port stays, so a provider with a formal
ceremony remains a configuration swap.
"""

import os
import secrets

from payments_core.ports.contract_signer import (
    ContractSigner,
    EnvelopeRequest,
    EnvelopeResult,
    EnvelopeStatus,
)


def signing_base_url() -> str:
    return os.environ.get("SIGNING_BASE_URL", "https://pay.ignitesolutions.click").rstrip("/")


class BuiltinClickSigner(ContractSigner):
    def create_envelope(self, request: EnvelopeRequest) -> EnvelopeResult:
        token = secrets.token_urlsafe(32)
        return EnvelopeResult(
            envelope_id=token,
            raw={"provider": "builtin"},
            signing_url=f"{signing_base_url()}/contracts/sign/{token}",
        )

    def get_envelope_status(self, envelope_id: str) -> str:
        # Status lives on the Contract row itself (the public sign endpoint
        # transitions it); nothing external to poll.
        return EnvelopeStatus.SENT
