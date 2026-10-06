"""Require a merchant account on every one-off (Flow B) payment.

Tightens `payment_one_off_requires_customer_and_external_ref` so a
tenant-scoped charge can no longer be created with `merchant_account = NULL`,
which would settle a buyer's money into the SaaS owner's global account.

SAFE: no existing row can violate it. Every pre-existing Payment is
`kind=subscription` (see 0004/0005), and the constraint is a no-op for that
kind. Any one-off row created between 0006 and this migration would have gone
through the charges endpoint, which has required `merchant_ref` from the
start.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0007_callbackdelivery"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="payment",
            name="payment_one_off_requires_customer_and_external_ref",
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(("kind", "one_off"), _negated=True)
                | (
                    models.Q(("subscription__isnull", True))
                    & models.Q(("customer__isnull", False))
                    & models.Q(("merchant_account__isnull", False))
                    & models.Q(("external_ref", ""), _negated=True)
                ),
                name="payment_one_off_requires_customer_and_external_ref",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="merchant_account",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Which merchant account the money settles into. NULL means the global SaaS "
                    "account and is only valid for kind=subscription (Flow A) — enforced by "
                    "the payment_one_off_requires_customer_and_external_ref check constraint."
                ),
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="payments",
                to="merchants.merchantaccount",
            ),
        ),
    ]
