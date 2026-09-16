"""Null ContractSigner adapter: no real e-signature provider wired yet.

This is the default adapter selected via `settings.CONTRACT_SIGNER`. It
immediately reports envelopes as signed, useful for local development and
tests that don't exercise the real e-signature flow (not yet built — no
provider decision has been made for this project).
"""

import itertools

from payments_core.ports.contract_signer import (
    ContractSigner,
    EnvelopeRequest,
    EnvelopeResult,
    EnvelopeStatus,
)


class NullContractSigner(ContractSigner):
    """No-op signer: creates a fake envelope id and reports it as already signed."""

    _counter = itertools.count(1)

    def create_envelope(self, request: EnvelopeRequest) -> EnvelopeResult:
        envelope_id = f"null-envelope-{next(self._counter)}"
        return EnvelopeResult(envelope_id=envelope_id, raw={"template_reference": request.template_reference})

    def get_envelope_status(self, envelope_id: str) -> str:
        return EnvelopeStatus.SIGNED
