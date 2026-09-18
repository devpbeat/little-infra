"""Staff-only management endpoints for consuming apps and API keys.

Session-authenticated staff only (the operator dashboard) — API keys must
never be able to mint or revoke other API keys. Key issuance mirrors the
`issue_api_key` management command exactly: the raw secret is returned in
this one response and never stored or shown again.
"""

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ApiKey, ConsumingApp, _generate_key_prefix, _generate_key_secret


class ApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiKey
        fields = ["id", "prefix", "is_active", "created_at", "last_used_at", "revoked_at"]


class ConsumingAppSerializer(serializers.ModelSerializer):
    api_keys = ApiKeySerializer(many=True, read_only=True)

    class Meta:
        model = ConsumingApp
        fields = ["id", "name", "is_active", "trial_days", "created_at", "api_keys"]


class ConsumingAppViewSet(viewsets.ReadOnlyModelViewSet):
    """`GET /api/v1/apps/` + key issuance/revocation — staff sessions only."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ConsumingAppSerializer
    queryset = ConsumingApp.objects.prefetch_related("api_keys").order_by("name")

    @action(detail=True, methods=["post"], url_path="customers")
    def create_customer(self, request, pk=None):
        """Staff creates a customer UNDER an explicit app — the admin
        counterpart of the machine signup endpoint, sharing the same
        provisioning (contract from the app's template + trial)."""
        from apps.customers.serializers import CustomerSerializer, SignupSerializer
        from apps.customers.views import provision_customer

        app = self.get_object()
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            customer, created = provision_customer(app, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            CustomerSerializer(customer).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="issue-key")
    def issue_key(self, request, pk=None):
        app = self.get_object()
        prefix = _generate_key_prefix()
        secret = _generate_key_secret()
        ApiKey.objects.create(app=app, prefix=prefix, hashed_secret=make_password(secret))
        # The ONLY place the raw key ever exists in a response.
        return Response(
            {"api_key": f"{prefix}.{secret}", "prefix": prefix},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="revoke-key")
    def revoke_key(self, request, pk=None):
        app = self.get_object()
        prefix = str(request.data.get("prefix") or "")
        try:
            api_key = app.api_keys.get(prefix=prefix)
        except ApiKey.DoesNotExist:
            return Response({"detail": "Unknown key prefix."}, status=status.HTTP_404_NOT_FOUND)
        api_key.is_active = False
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["is_active", "revoked_at"])
        return Response(ApiKeySerializer(api_key).data)
