"""Flow B, step 3 of 3: make `app` required and pin the valid combinations.

Runs only after 0005 has backfilled every row. `app` becoming NOT NULL is
the fix for the tenant-scoping hole: `ScopedByAppMixin` now filters Payment
on this column, and a row without it would be visible to no tenant — or,
worse, fall out of the scope path entirely as a subscription-less payment did
before.

The two CheckConstraints are what make "a subscription payment with no
subscription" or "a one-off charge with no customer" unrepresentable in the
DATABASE, not merely discouraged in Python.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0005_backfill_payment_app_and_customer"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="app",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="apps_registry.consumingapp",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("external_ref", ""), _negated=True),
                fields=("app", "external_ref"),
                name="unique_app_payment_external_ref",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(("kind", "subscription"), _negated=True)
                | models.Q(("subscription__isnull", False)),
                name="payment_subscription_kind_requires_subscription",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(("kind", "one_off"), _negated=True)
                | (
                    models.Q(("subscription__isnull", True))
                    & models.Q(("customer__isnull", False))
                    & models.Q(("external_ref", ""), _negated=True)
                ),
                name="payment_one_off_requires_customer_and_external_ref",
            ),
        ),
    ]
