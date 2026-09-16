from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from payments_core.auth import ScopedByAppMixin

from .models import Subscription
from .serializers import SubscriptionEntitlementSerializer, SubscriptionSerializer


class SubscriptionViewSet(ScopedByAppMixin, viewsets.ReadOnlyModelViewSet):
    """`GET /subscriptions`, `/subscriptions/{id}`, `/subscriptions/{id}/entitlement`.

    Scoped one hop from `ConsumingApp` via `customer__app` — `Subscription`
    has no direct `app` FK (design §3). This is the second gating surface
    alongside `customers/{external_ref}/entitlement`, kept for callers that
    already hold a subscription id rather than an external_ref.
    """

    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.select_related("customer", "plan").order_by("-created_at")
    app_scope_field = "customer__app"

    @action(detail=True, methods=["get"])
    def entitlement(self, request, pk=None):
        subscription = self.get_object()
        return Response(SubscriptionEntitlementSerializer(subscription).data)
