"""Per-tenant gateway merchant accounts (Flow B).

New table only — nothing existing is touched, so this is safe to apply at
any time ahead of the billing migrations.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("apps_registry", "0002_consumingapp_contract_template_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MerchantAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "external_ref",
                    models.CharField(
                        help_text="The consuming app's own identifier for the collecting company.",
                        max_length=255,
                    ),
                ),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("gateway", models.CharField(default="pagopar", max_length=50)),
                ("public_key", models.CharField(blank=True, max_length=255)),
                (
                    "private_key_encrypted",
                    models.TextField(
                        blank=True,
                        help_text="Fernet-encrypted gateway private key. Never exposed via the API.",
                    ),
                ),
                ("base_url", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "app",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="merchant_accounts",
                        to="apps_registry.consumingapp",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="merchantaccount",
            constraint=models.UniqueConstraint(
                fields=("app", "external_ref"), name="unique_app_merchant_external_ref"
            ),
        ),
    ]
