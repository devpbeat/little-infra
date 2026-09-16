from rest_framework import serializers

from .models import Subscription, compute_entitlement


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id",
            "customer",
            "plan",
            "status",
            "trial_start",
            "trial_end",
            "current_period_end",
            "canceled_at",
            "created_at",
        ]
        read_only_fields = fields


class SubscriptionEntitlementSerializer(serializers.Serializer):
    entitled = serializers.SerializerMethodField()
    status = serializers.CharField()
    trial_end = serializers.DateTimeField()
    current_period_end = serializers.DateTimeField()

    def get_entitled(self, subscription: Subscription) -> bool:
        return compute_entitlement(subscription)
