from django.db import models

from apps.customers.models import Customer


class ContractTemplate(models.Model):
    """A reusable contract document template."""

    name = models.CharField(max_length=150, unique=True)
    reference = models.CharField(
        max_length=255,
        help_text="External template reference (e.g. e-signature provider template ID).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ContractStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    GENERATED = "generated", "Generated"
    SENT = "sent", "Sent"
    SIGNED = "signed", "Signed"
    DECLINED = "declined", "Declined"
    VOIDED = "voided", "Voided"
    TERMINATED = "terminated", "Terminated"


# Valid forward transitions. Any transition not listed here is rejected by
# `Contract.transition_to`.
_ALLOWED_TRANSITIONS = {
    ContractStatus.DRAFT: {ContractStatus.GENERATED, ContractStatus.VOIDED},
    ContractStatus.GENERATED: {ContractStatus.SENT, ContractStatus.VOIDED},
    ContractStatus.SENT: {ContractStatus.SIGNED, ContractStatus.DECLINED, ContractStatus.VOIDED},
    ContractStatus.SIGNED: {ContractStatus.TERMINATED},
    ContractStatus.DECLINED: set(),
    ContractStatus.VOIDED: set(),
    ContractStatus.TERMINATED: set(),
}


class InvalidContractTransition(Exception):
    pass


class Contract(models.Model):
    """A contract instance generated for a Customer from a ContractTemplate."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contracts")
    template = models.ForeignKey(ContractTemplate, on_delete=models.PROTECT, related_name="contracts")
    status = models.CharField(
        max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT
    )
    external_envelope_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    def transition_to(self, new_status: str) -> None:
        """Move the contract to `new_status`, enforcing the lifecycle graph.

        Raises InvalidContractTransition if the transition is not allowed.
        """
        current = ContractStatus(self.status)
        target = ContractStatus(new_status)
        if target not in _ALLOWED_TRANSITIONS[current]:
            raise InvalidContractTransition(f"Cannot transition contract from {current} to {target}.")
        self.status = target
        self.save(update_fields=["status", "updated_at"])

    def __str__(self) -> str:
        return f"Contract#{self.pk} ({self.status})"
