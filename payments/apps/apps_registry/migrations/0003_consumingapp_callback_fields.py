"""Outbound callback configuration on ConsumingApp.

Both columns default to blank, which means "callbacks disabled" — existing
apps keep polling exactly as before until an operator configures a URL and
secret.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("apps_registry", "0002_consumingapp_contract_template_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="consumingapp",
            name="callback_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="HTTPS endpoint notified when a payment is confirmed. Blank disables callbacks.",
                max_length=500,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="consumingapp",
            name="callback_secret_encrypted",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Fernet-encrypted HMAC shared secret. Never exposed via the API.",
            ),
            preserve_default=False,
        ),
    ]
