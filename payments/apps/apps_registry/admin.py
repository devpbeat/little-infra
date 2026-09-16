from django.contrib import admin

from .models import ApiKey, ConsumingApp


@admin.register(ConsumingApp)
class ConsumingAppAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("app", "prefix", "is_active", "created_at", "last_used_at")
    list_filter = ("is_active",)
    readonly_fields = ("hashed_secret", "prefix", "created_at", "last_used_at")
