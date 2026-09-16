from django.contrib import admin

from .models import Contract, ContractTemplate


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "reference", "is_active")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "template", "status", "created_at")
    list_filter = ("status", "template")
