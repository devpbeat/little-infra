"""PaymentGateway port: the boundary every payment gateway adapter implements.

No adapter-specific types (Pagopar, or any future gateway) may leak past
this module. Callers (views, services) depend only on this Protocol and
the DTOs defined here.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChargeRequest:
    """Everything a gateway needs to create a charge, gateway-agnostic."""

    order_id: str
    amount_pyg: int
    description: str
    buyer_name: str
    buyer_email: str
    buyer_document: str
    buyer_phone: str


@dataclass(frozen=True, slots=True)
class ChargeResult:
    """Result of creating a charge: opaque gateway order id plus checkout info."""

    gateway_order_id: str
    checkout_url: str | None
    raw: dict


class ChargeStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class WebhookVerificationResult:
    """Result of verifying an inbound webhook payload."""

    is_valid: bool
    event_id: str | None
    gateway_order_id: str | None
    status: str | None


class PaymentGateway(Protocol):
    """Port implemented by every payment gateway adapter."""

    def create_charge(self, request: ChargeRequest) -> ChargeResult:
        """Create a charge/order with the gateway and return its identifiers."""
        ...

    def get_charge_status(self, gateway_order_id: str) -> str:
        """Return one of the `ChargeStatus` values for `gateway_order_id`."""
        ...

    def verify_webhook(self, headers: dict, body: bytes) -> WebhookVerificationResult:
        """Verify an inbound webhook's authenticity and extract identifying fields."""
        ...
