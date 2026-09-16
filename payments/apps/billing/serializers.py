from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "subscription",
            "amount_pyg",
            "status",
            "gateway",
            "gateway_order_id",
            "checkout_url",
            "created_at",
            "updated_at",
            "confirmed_at",
        ]
        read_only_fields = fields


class PaymentInitiationSerializer(serializers.Serializer):
    """Input for `POST /payments`: which subscription to pay the next period for."""

    subscription = serializers.IntegerField(help_text="Subscription id to initiate a payment for.")
