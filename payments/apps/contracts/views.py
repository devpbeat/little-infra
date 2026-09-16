from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from payments_core.auth import ScopedByAppMixin

from .models import Contract, InvalidContractTransition
from .serializers import ContractSerializer, ContractTransitionSerializer


class ContractViewSet(ScopedByAppMixin, viewsets.ReadOnlyModelViewSet):
    """`GET /contracts`, `/contracts/{id}`, `POST /contracts/{id}/transition`.

    Scoped one hop from `ConsumingApp` via `customer__app` — `Contract` has
    no direct `app` FK (design §3).
    """

    serializer_class = ContractSerializer
    queryset = Contract.objects.select_related("customer", "template").order_by("-created_at")
    app_scope_field = "customer__app"

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        contract = self.get_object()
        serializer = ContractTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            contract.transition_to(serializer.validated_data["status"])
        except InvalidContractTransition as exc:
            return Response({"detail": str(exc), "code": "invalid_transition"}, status=status.HTTP_409_CONFLICT)

        return Response(ContractSerializer(contract).data)
