"""Per-tenant gateway merchant accounts (Flow B).

WHY THIS MODEL EXISTS, and why the credentials do NOT live on `ConsumingApp`:
one consuming app (yvyreta/LoteamientoPro) serves MANY land-development
companies, and each company collects its buyers' installments into its own
Pagopar account. Per-`ConsumingApp` credentials would pool every company's
money into one account; per-`Customer` credentials are wrong too, because in
Flow B the `Customer` is the BUYER, not the collecting company.

So a merchant account is its own aggregate: owned by a `ConsumingApp`
(for tenant isolation) and addressed by the consuming app's own identifier
for the collecting company (`external_ref`), exactly like `Customer`.

Flow A (SaaS subscriptions) has no merchant account and resolves to the
global `PAGOPAR_*` env pair — see `payments_core.merchant_credentials`.
"""

from django.db import models

from apps.apps_registry.models import ConsumingApp
from payments_core.crypto import decrypt_secret, encrypt_secret


class MerchantAccount(models.Model):
    """A gateway merchant account money is settled into, owned by one tenant.

    `private_key_encrypted` holds a Fernet token, never the raw key. The raw
    key is reachable only through `get_private_key()`; it is never a model
    field, never serialized, and never logged.
    """

    app = models.ForeignKey(ConsumingApp, on_delete=models.CASCADE, related_name="merchant_accounts")
    external_ref = models.CharField(
        max_length=255,
        help_text="The consuming app's own identifier for the collecting company.",
    )
    display_name = models.CharField(max_length=255, blank=True)
    gateway = models.CharField(max_length=50, default="pagopar")
    public_key = models.CharField(max_length=255, blank=True)
    private_key_encrypted = models.TextField(
        blank=True, help_text="Fernet-encrypted gateway private key. Never exposed via the API."
    )
    base_url = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["app", "external_ref"], name="unique_app_merchant_external_ref"
            ),
        ]

    def set_private_key(self, raw_private_key: str) -> None:
        """Encrypt and stage `raw_private_key`. Caller must `save()`."""
        self.private_key_encrypted = encrypt_secret(raw_private_key)

    def get_private_key(self) -> str:
        return decrypt_secret(self.private_key_encrypted)

    @property
    def has_credentials(self) -> bool:
        return bool(self.public_key and self.private_key_encrypted)

    def __str__(self) -> str:
        return f"{self.app.name}:{self.external_ref}"
