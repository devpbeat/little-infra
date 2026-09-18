from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contracts.models import Contract, ContractStatus
from apps.subscriptions.models import Subscription
from payments_core.auth import IsAuthenticatedAppOnly, ScopedByAppMixin

from .models import Customer
from .serializers import CustomerSerializer, EntitlementSerializer, SignupSerializer


def provision_customer(app, validated_data):
    """Create customer + contract (from the app's template) + trial.

    Shared by machine signup (API key) and staff creation (dashboard).
    Returns (customer, created) — idempotent by (app, external_ref).
    Raises ValueError when the app lacks its template/plan wiring.
    """
    existing = Customer.objects.filter(
        app=app, external_ref=validated_data["external_ref"]
    ).first()
    if existing is not None:
        return existing, False
    if app.contract_template is None or app.default_plan is None:
        raise ValueError("App is not provisioned with a contract_template and default_plan.")
    try:
        with transaction.atomic():
            customer = Customer.objects.create(app=app, **validated_data)
            contract = Contract.objects.create(customer=customer, template=app.contract_template)
            contract.transition_to(ContractStatus.GENERATED)
            Subscription.start_trial(customer, app.default_plan, trial_days=app.trial_days)
    except IntegrityError:
        # A concurrent signup with the same external_ref won the race.
        return Customer.objects.get(app=app, external_ref=validated_data["external_ref"]), False
    return customer, True


class SignupView(APIView):
    """`POST /api/v1/customers/signup` (spec: client-onboarding).

    Idempotent by `(app, external_ref)`: retrying with the same identifying
    credentials returns the already-provisioned Customer/Contract/Subscription
    instead of creating duplicates (design §5).
    """

    permission_classes = [IsAuthenticatedAppOnly]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            customer, created = provision_customer(request.app, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            CustomerSerializer(customer).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CustomerViewSet(ScopedByAppMixin, viewsets.ReadOnlyModelViewSet):
    """`GET /customers/{external_ref}` and `/customers/{external_ref}/entitlement`."""

    serializer_class = CustomerSerializer
    lookup_field = "external_ref"
    queryset = Customer.objects.all()

    @action(detail=True, methods=["get"])
    def entitlement(self, request, external_ref=None):
        customer = get_object_or_404(self.get_queryset(), external_ref=external_ref)
        subscription = customer.subscriptions.order_by("-created_at").first()
        return Response(EntitlementSerializer.from_subscription(subscription).data)
