from django.db import models

from apps.apps_registry.models import ConsumingApp


class Customer(models.Model):
    """A tenant's end customer, identified by `external_ref` within that tenant.

    Cross-tenant isolation depends on always scoping queries by `app` — see
    `payments_core.auth.ScopedByAppMixin` (Slice D).
    """

    app = models.ForeignKey(ConsumingApp, on_delete=models.CASCADE, related_name="customers")
    external_ref = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["app", "external_ref"], name="unique_app_external_ref"),
        ]

    def __str__(self) -> str:
        return f"{self.app.name}:{self.external_ref}"
