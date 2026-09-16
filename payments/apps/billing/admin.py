from django.contrib import admin

from .models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "subscription", "amount_pyg", "status", "gateway", "created_at")
    list_filter = ("status", "gateway")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "gateway", "event_id", "received_at", "processed_at")
    list_filter = ("gateway",)
    readonly_fields = ("gateway", "event_id", "payload", "received_at")
