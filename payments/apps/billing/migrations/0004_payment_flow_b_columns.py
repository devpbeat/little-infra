"""Flow B, step 1 of 3: add the new Payment columns, all NULLABLE.

SAFE ON A LIVE TABLE. Every added column is nullable or has a constant
default, and `subscription` is only RELAXED to nullable — no existing row is
rewritten and no constraint is tightened here. Deliberately split from the
backfill (0005) and the tightening (0006) so a deploy can apply this, run,
and be rolled back without touching data.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0003_payment_checkout_url"),
        ("apps_registry", "0003_consumingapp_callback_fields"),
        ("customers", "0002_customer_address_customer_legal_name_customer_phone_and_more"),
        ("merchants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="app",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="apps_registry.consumingapp",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="customers.customer",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="merchant_account",
            field=models.ForeignKey(
                blank=True,
                help_text="Which merchant account the money settles into. NULL = global SaaS account.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payments",
                to="merchants.merchantaccount",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="kind",
            field=models.CharField(
                choices=[
                    ("subscription", "SaaS subscription period"),
                    ("one_off", "Tenant-scoped one-off charge"),
                ],
                default="subscription",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="external_ref",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text=(
                    "Caller-supplied reference for the thing being paid for (e.g. an "
                    "Installment pk). Doubles as the idempotency key, unique per app."
                ),
                max_length=255,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="payment",
            name="description",
            field=models.CharField(blank=True, default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="payment",
            name="charge_attempts",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "How many gateway orders this payment has asked for. Used to keep the "
                    "gateway-side order reference unique when a failed charge is retried "
                    "under the same external_ref."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="subscription",
            field=models.ForeignKey(
                blank=True,
                help_text="Flow A only. NULL for a one-off tenant charge.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="subscriptions.subscription",
            ),
        ),
    ]
