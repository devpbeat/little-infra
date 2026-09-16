"""Root URL configuration.

Domain endpoints (customers, contracts, subscriptions, billing, webhooks) are
wired in Slices D and E. This scaffold only exposes a health check so CI and
the deploy pipeline have something to probe.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

import payments_core.spectacular  # noqa: F401 — registers the ApiKeyAuth scheme with drf-spectacular


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/v1/health", health, name="health"),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.contracts.urls")),
    path("api/v1/", include("apps.subscriptions.urls")),
    path("api/v1/", include("apps.billing.urls")),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("admin/", admin.site.urls),
]
