"""Root URL configuration.

Domain endpoints (customers, contracts, subscriptions, billing, webhooks) are
wired in Slices D and E. This scaffold only exposes a health check so CI and
the deploy pipeline have something to probe.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/v1/health", health, name="health"),
    path("admin/", admin.site.urls),
]
