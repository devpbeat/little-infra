"""Outbound confirmation callbacks: one delivery row per (payment, event).

New table only. The unique constraint on `(payment, event)` is the
idempotency gate that stops a replayed gateway webhook from producing a
second outbound notification.
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0006_payment_flow_b_constraints"),
    ]

    operations = [
        migrations.CreateModel(
            name="CallbackDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delivery_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event", models.CharField(default="payment.confirmed", max_length=50)),
                ("url", models.CharField(max_length=500)),
                (
                    "body",
                    models.TextField(
                        help_text="Exact JSON bytes signed and POSTed. Never contains secrets."
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("delivered", "Delivered"),
                            ("failed", "Failed (gave up)"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("next_attempt_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="callback_deliveries",
                        to="billing.payment",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="callbackdelivery",
            index=models.Index(
                fields=["status", "next_attempt_at"], name="billing_cal_status_7a9b47_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="callbackdelivery",
            constraint=models.UniqueConstraint(
                fields=("payment", "event"), name="unique_payment_callback_event"
            ),
        ),
    ]
