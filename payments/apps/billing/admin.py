from django.contrib import admin

from .models import CallbackDelivery, Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "kind",
        "app",
        "external_ref",
        "merchant_account",
        "amount_pyg",
        "status",
        "gateway",
        "created_at",
    )
    list_filter = ("kind", "status", "gateway", "app")
    search_fields = ("external_ref", "gateway_order_id")

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "gateway", "event_id", "received_at", "processed_at")
    list_filter = ("gateway",)
    readonly_fields = ("gateway", "event_id", "payload", "received_at")

@admin.register(CallbackDelivery)
class CallbackDeliveryAdmin(admin.ModelAdmin):
    """Operator view for the outbound leg: what was sent, what gave up, why."""

    list_display = ("delivery_id", "payment", "event", "status", "attempts", "next_attempt_at")
    list_filter = ("status", "event")
    readonly_fields = ("delivery_id", "payment", "event", "url", "body", "attempts", "last_error")
