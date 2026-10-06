from django import forms
from django.contrib import admin

from .models import MerchantAccount


class MerchantAccountForm(forms.ModelForm):
    """Write-only private key: entered once, never rendered back."""

    private_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to keep the stored key. Never displayed once saved.",
    )

    class Meta:
        model = MerchantAccount
        fields = ["app", "external_ref", "display_name", "gateway", "public_key", "base_url", "is_active"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw = self.cleaned_data.get("private_key")
        if raw:
            instance.set_private_key(raw)
        if commit:
            instance.save()
        return instance

@admin.register(MerchantAccount)
class MerchantAccountAdmin(admin.ModelAdmin):
    form = MerchantAccountForm
    list_display = ["external_ref", "app", "display_name", "gateway", "is_active", "has_credentials"]
    list_filter = ["app", "gateway", "is_active"]
    search_fields = ["external_ref", "display_name"]

    @admin.display(boolean=True, description="Credentials set")
    def has_credentials(self, obj: MerchantAccount) -> bool:
        return obj.has_credentials
