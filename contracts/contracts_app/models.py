from django.db import models
from martor.models import MartorField


class Client(models.Model):
    """A lead / independent client you sell to and contract with."""

    class Status(models.TextChoices):
        LEAD = "lead", "Lead"
        NEGOTIATING = "negotiating", "Negotiating"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        ARCHIVED = "archived", "Archived"

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField("Tax ID", max_length=50, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.LEAD
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.company})" if self.company else self.full_name

    def merge_context(self):
        """Fields exposed to templates as ${client_*} merge variables."""
        return {
            "client_name": self.full_name,
            "client_email": self.email,
            "client_company": self.company,
            "client_phone": self.phone,
            "client_address": self.address,
            "client_tax_id": self.tax_id,
        }


class ContractTemplate(models.Model):
    """A reusable, admin-authored contract body in Markdown.

    Two placeholder syntaxes live side by side in the body:

    * ``${merge_var}`` — filled in by this app before sending (Python
      string.Template). Available keys come from the client
      (``${client_name}`` …) plus whatever you put in a contract's
      ``variables`` JSON (``${amount}``, ``${start_date}`` …).
    * ``{{Field;role=Client;type=signature}}`` — a DocuSeal interactive
      field, left untouched so the signer fills it in DocuSeal.
    """

    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=300, blank=True)
    body_markdown = MartorField(
        help_text=(
            "Markdown. Use ${var} for merge fields (e.g. ${client_name}, "
            "${amount}) and {{Signature;role=Client;type=signature}} for "
            "DocuSeal signature fields."
        )
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Contract(models.Model):
    """A single contract: a template rendered for one client, then pushed
    to DocuSeal for signature."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent for signature"
        VIEWED = "viewed", "Viewed"
        COMPLETED = "completed", "Completed"
        DECLINED = "declined", "Declined"

    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="contracts"
    )
    template = models.ForeignKey(
        ContractTemplate, on_delete=models.PROTECT, related_name="contracts"
    )
    title = models.CharField(max_length=200)
    variables = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Extra merge values as JSON, e.g. '
            '{"amount": "$5,000", "start_date": "2026-08-01"}. '
            "Referenced in the template as ${amount}, ${start_date}."
        ),
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    rendered_html = models.TextField(blank=True, editable=False)

    docuseal_submission_id = models.CharField(max_length=64, blank=True)
    client_signing_url = models.URLField(blank=True)
    owner_signing_url = models.URLField(blank=True)
    signed_pdf_object = models.CharField(
        max_length=500, blank=True, help_text="MinIO object key of the signed PDF."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.client}"

    def merge_context(self):
        """All merge variables available to the template renderer."""
        ctx = self.client.merge_context()
        ctx["contract_title"] = self.title
        if isinstance(self.variables, dict):
            ctx.update({str(k): v for k, v in self.variables.items()})
        return ctx
