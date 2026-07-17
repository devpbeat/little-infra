import logging

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import TextField
from django.utils import timezone
from django.utils.html import format_html
from martor.widgets import AdminMartorWidget
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Client, Contract, ContractTemplate
from .services import docuseal, rendering, storage

logger = logging.getLogger("contracts_app")

STATUS_BADGES = {
    Contract.Status.DRAFT: "info",
    Contract.Status.SENT: "warning",
    Contract.Status.VIEWED: "warning",
    Contract.Status.COMPLETED: "success",
    Contract.Status.DECLINED: "danger",
}


# Re-skin the built-in auth admin with Unfold's styled forms.
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UnfoldUserAdmin(UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class UnfoldGroupAdmin(GroupAdmin, ModelAdmin):
    pass


CLIENT_STATUS_BADGES = {
    Client.Status.LEAD: "info",
    Client.Status.NEGOTIATING: "warning",
    Client.Status.WON: "success",
    Client.Status.LOST: "danger",
    Client.Status.ARCHIVED: "",
}


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    list_display = ("full_name", "company", "email", "status_badge", "updated_at")
    list_filter = ("status",)
    search_fields = ("full_name", "email", "company")
    fields = (
        "full_name", "email", "company", "phone", "address", "tax_id",
        "status", "notes",
    )

    @display(description="Status", label=CLIENT_STATUS_BADGES, ordering="status")
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()


@admin.register(ContractTemplate)
class ContractTemplateAdmin(ModelAdmin):
    list_display = ("name", "description", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    formfield_overrides = {TextField: {"widget": AdminMartorWidget}}


def _generate_and_push(contract) -> None:
    """Render one contract and create a DocuSeal submission for it."""
    html = rendering.render_contract(contract)

    submitters = [{
        "role": "Client",
        "email": contract.client.email,
        "name": contract.client.full_name,
    }]
    if settings.OWNER_SIGNER_EMAIL:
        submitters.append({
            "role": "Owner",
            "email": settings.OWNER_SIGNER_EMAIL,
            "name": settings.OWNER_SIGNER_NAME or "Owner",
        })

    response = docuseal.create_submission_from_html(
        name=contract.title, html=html, submitters=submitters
    )
    records = docuseal.parse_submitters(response)

    contract.rendered_html = html
    contract.client_signing_url = ""
    contract.owner_signing_url = ""
    for rec in records:
        slug = rec.get("slug")
        if not slug:
            continue
        if not contract.docuseal_submission_id:
            contract.docuseal_submission_id = str(
                rec.get("submission_id") or rec.get("id") or ""
            )
        url = docuseal.public_signing_url(slug)
        if rec.get("role") == "Owner":
            contract.owner_signing_url = url
        else:
            contract.client_signing_url = url

    contract.status = Contract.Status.SENT
    contract.sent_at = timezone.now()
    contract.save()


@admin.register(Contract)
class ContractAdmin(ModelAdmin):
    list_display = (
        "title", "client", "template", "status_badge", "signing_links",
        "updated_at",
    )
    list_filter = ("status", "template")
    search_fields = ("title", "client__full_name", "client__email")
    autocomplete_fields = ("client",)
    readonly_fields = (
        "status", "docuseal_submission_id", "signing_links",
        "signed_pdf_link", "sent_at", "completed_at", "created_at", "updated_at",
    )
    actions = ("generate_and_push",)
    fieldsets = (
        (None, {"fields": ("title", "client", "template", "variables")}),
        ("Signing", {
            "fields": (
                "status", "docuseal_submission_id", "signing_links",
                "signed_pdf_link",
            )
        }),
        ("Timestamps", {
            "fields": ("sent_at", "completed_at", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @display(description="Status", label=STATUS_BADGES, ordering="status")
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @admin.display(description="Signing links")
    def signing_links(self, obj):
        links = []
        if obj.client_signing_url:
            links.append(
                format_html('<a href="{}" target="_blank">Client</a>',
                            obj.client_signing_url)
            )
        if obj.owner_signing_url:
            links.append(
                format_html('<a href="{}" target="_blank">Owner</a>',
                            obj.owner_signing_url)
            )
        return format_html(" &nbsp;|&nbsp; ".join(links)) if links else "—"

    @admin.display(description="Signed PDF")
    def signed_pdf_link(self, obj):
        if not obj.signed_pdf_object:
            return "—"
        try:
            url = storage.presigned_url(obj.signed_pdf_object)
        except Exception:  # noqa: BLE001 - never break the admin page
            logger.exception("Failed to presign %s", obj.signed_pdf_object)
            return obj.signed_pdf_object
        return format_html('<a href="{}" target="_blank">Download signed PDF</a>', url)

    @admin.action(description="Generate & push to DocuSeal")
    def generate_and_push(self, request, queryset):
        sent, failed = 0, 0
        for contract in queryset:
            try:
                _generate_and_push(contract)
                sent += 1
            except Exception as exc:  # noqa: BLE001 - report per-row
                failed += 1
                logger.exception("Failed to push contract %s", contract.pk)
                self.message_user(
                    request, f"'{contract.title}': {exc}", level=messages.ERROR
                )
        if sent:
            self.message_user(
                request,
                f"Pushed {sent} contract(s) to DocuSeal. Signing links are on "
                "each contract.",
                level=messages.SUCCESS,
            )
        if failed and not sent:
            self.message_user(
                request, "No contracts were pushed.", level=messages.WARNING
            )
