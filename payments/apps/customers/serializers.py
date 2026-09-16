from rest_framework import serializers

from apps.contracts.models import Contract
from apps.subscriptions.models import Subscription, compute_entitlement

from .models import Customer


class SignupSerializer(serializers.Serializer):
    """Input for `POST /customers/signup`."""

    external_ref = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    display_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class ContractSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = ["id", "status", "external_envelope_id", "created_at", "signed_at"]


class SubscriptionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["id", "status", "trial_start", "trial_end", "current_period_end"]


class CustomerSerializer(serializers.ModelSerializer):
    contract = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["external_ref", "email", "display_name", "created_at", "contract", "subscription"]

    def get_contract(self, customer: Customer):
        contract = customer.contracts.order_by("-created_at").first()
        return ContractSummarySerializer(contract).data if contract else None

    def get_subscription(self, customer: Customer):
        subscription = customer.subscriptions.order_by("-created_at").first()
        return SubscriptionSummarySerializer(subscription).data if subscription else None


class EntitlementSerializer(serializers.Serializer):
    """The access-gating contract consuming apps poll (design §5)."""

    entitled = serializers.BooleanField()
    status = serializers.CharField()
    trial_end = serializers.DateTimeField(allow_null=True)
    current_period_end = serializers.DateTimeField(allow_null=True)

    @classmethod
    def from_subscription(cls, subscription: Subscription | None):
        if subscription is None:
            return cls(
                {
                    "entitled": False,
                    "status": "none",
                    "trial_end": None,
                    "current_period_end": None,
                }
            )
        return cls(
            {
                "entitled": compute_entitlement(subscription),
                "status": subscription.status,
                "trial_end": subscription.trial_end,
                "current_period_end": subscription.current_period_end,
            }
        )
