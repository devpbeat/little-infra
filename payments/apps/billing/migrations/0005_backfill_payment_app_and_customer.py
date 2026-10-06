"""Flow B, step 2 of 3: backfill `app`/`customer` on existing Payment rows.

Every pre-existing Payment is a Flow A subscription payment, so its tenant
is unambiguous: `payment.subscription.customer.app`. Done in batched
`UPDATE ... FROM` statements rather than row-by-row Python so a large table
does not need the whole queryset in memory.

Reverse is a deliberate no-op: 0006 is what makes `app` required, and
un-setting a correct value on the way down would only create the hole this
change exists to close.
"""

from django.db import migrations

BATCH_SIZE = 5000

def backfill(apps, schema_editor):
    Payment = apps.get_model("billing", "Payment")
    while True:
        batch = list(
            Payment.objects.filter(app__isnull=True, subscription__isnull=False)
            .values_list("pk", "subscription__customer_id", "subscription__customer__app_id")[
                :BATCH_SIZE
            ]
        )
        if not batch:
            break
        for pk, customer_id, app_id in batch:
            Payment.objects.filter(pk=pk).update(app_id=app_id, customer_id=customer_id)

def check_no_orphans(apps, schema_editor):
    """Refuse to continue if any row still has no tenant.

    A Payment with neither an app nor a subscription cannot be attributed to
    a tenant, and 0006's NOT NULL would fail anyway — failing here says why.
    """
    Payment = apps.get_model("billing", "Payment")
    orphans = Payment.objects.filter(app__isnull=True).count()
    if orphans:
        raise RuntimeError(
            f"{orphans} Payment row(s) have no app and no subscription to derive one from. "
            "Attribute or delete them before applying billing.0006."
        )

class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0004_payment_flow_b_columns"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.RunPython(check_no_orphans, migrations.RunPython.noop),
    ]
