from django.db import models
from django.utils import timezone

from apps.customers.models import Customer


class DealType(models.TextChoices):
    SAAS_SUBSCRIPTION = "saas_subscription", "SaaS monthly/annual fee"
    FIXED_WITH_OWNERSHIP = "fixed_with_ownership", "Fixed price with code ownership"
    FIXED_HOSTED = "fixed_hosted", "Fixed price without ownership, hosting provided"


class ContractTemplate(models.Model):
    """A reusable contract document template.

    `body` is markdown with `{{placeholder}}` variables substituted at
    render time from the customer/app/plan context (see `render`).
    Templates must be explicitly approved (`is_approved`) by a human
    before contracts render from them — AI-generated drafts arrive
    unapproved by design.
    """

    name = models.CharField(max_length=150, unique=True)
    reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="External template reference (e.g. e-signature provider template ID).",
    )
    deal_type = models.CharField(
        max_length=32, choices=DealType.choices, default=DealType.SAAS_SUBSCRIPTION
    )
    body = models.TextField(
        blank=True,
        help_text="Markdown with {{placeholder}} variables (client_name, plan_name, ...).",
    )
    is_approved = models.BooleanField(
        default=False, help_text="Human-reviewed and cleared for rendering real contracts."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def render(self, context: dict) -> str:
        """Substitute `{{key}}` placeholders; unknown keys stay visible.

        Deliberately dumb string substitution — no template-language
        execution, so a template body can never run code or reach model
        attributes beyond the explicit context dict.
        """
        rendered = self.body
        for key, value in context.items():
            rendered = rendered.replace("{{" + key + "}}", str(value))
        return rendered

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
        update_fields = ["status", "updated_at"]
        if target == ContractStatus.SIGNED and self.signed_at is None:
            self.signed_at = timezone.now()
            update_fields.append("signed_at")
        self.save(update_fields=update_fields)

    def __str__(self) -> str:
        return f"Contract#{self.pk} ({self.status})"
