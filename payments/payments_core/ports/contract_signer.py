"""ContractSigner port: the boundary every e-signature adapter implements."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EnvelopeRequest:
    template_reference: str
    signer_name: str
    signer_email: str


@dataclass(frozen=True, slots=True)
class EnvelopeResult:
    envelope_id: str
    raw: dict


class EnvelopeStatus:
    SENT = "sent"
    SIGNED = "signed"
    DECLINED = "declined"
    VOIDED = "voided"


class ContractSigner(Protocol):
    """Port implemented by every e-signature provider adapter."""

    def create_envelope(self, request: EnvelopeRequest) -> EnvelopeResult:
        """Create and send a signature envelope, returning the provider's envelope id."""
        ...

    def get_envelope_status(self, envelope_id: str) -> str:
        """Return one of the `EnvelopeStatus` values for `envelope_id`."""
        ...
