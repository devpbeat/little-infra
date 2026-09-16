from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("external_ref", "app", "email", "created_at")
    list_filter = ("app",)
    search_fields = ("external_ref", "email")
