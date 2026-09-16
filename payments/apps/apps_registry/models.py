import secrets

from django.db import models
from django.utils import timezone


def _generate_key_secret() -> str:
    return secrets.token_urlsafe(32)


def _generate_key_prefix() -> str:
    return secrets.token_hex(4)


class ConsumingApp(models.Model):
    """A tenant application allowed to call the payments API."""

    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Used by the signup endpoint (Slice D1) to autogenerate a Contract and
    # start a Subscription without the caller having to specify either.
    # Nullable so an app can be provisioned before its template/plan exist;
    # signup fails loudly (not silently) if either is unset when called.
    contract_template = models.ForeignKey(
        "contracts.ContractTemplate",
        on_delete=models.PROTECT,
        related_name="consuming_apps",
        null=True,
        blank=True,
    )
    default_plan = models.ForeignKey(
        "subscriptions.Plan",
        on_delete=models.PROTECT,
        related_name="consuming_apps",
        null=True,
        blank=True,
    )
    trial_days = models.PositiveIntegerField(default=30)

    def __str__(self) -> str:
        return self.name


class ApiKey(models.Model):
    """An API key issued to a ConsumingApp.

    Only the salted hash of the secret is stored. The raw secret is returned
    exactly once, at issuance time (see the `issue_api_key` management
    command), and never persisted or logged in plaintext.
    """

    app = models.ForeignKey(ConsumingApp, on_delete=models.CASCADE, related_name="api_keys")
    prefix = models.CharField(max_length=16, unique=True, db_index=True)
    hashed_secret = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def revoke(self) -> None:
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_active", "revoked_at"])

    def __str__(self) -> str:
        return f"{self.app.name}:{self.prefix}"
