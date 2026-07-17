from django.contrib import admin
from django.urls import include, path

from contracts_app import views

admin.site.site_header = "Contracts Admin"
admin.site.site_title = "Contracts Admin"
admin.site.index_title = "Manage clients, templates and contracts"

urlpatterns = [
    path("webhooks/docuseal/", views.docuseal_webhook, name="docuseal-webhook"),
    path("healthz/", views.healthz, name="healthz"),
    path("martor/", include("martor.urls")),
    path("", admin.site.urls),
]
