from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """The single read shape for both flows.

    Identifiers are exposed as the CALLER's own references
    (`customer_ref`, `merchant_ref`) rather than our primary keys, so a
    consuming app never has to store our ids to make sense of a payment.
    Merchant CREDENTIALS are not representable here — only the ref.
    """

    customer_ref = serializers.CharField(source="customer.external_ref", read_only=True, default=None)
    merchant_ref = serializers.CharField(
        source="merchant_account.external_ref", read_only=True, default=None
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "kind",
            "external_ref",
            "customer_ref",
            "merchant_ref",
            "subscription",
            "description",
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
    """Input for `POST /payments` (Flow A): which subscription to pay for."""

    subscription = serializers.IntegerField(help_text="Subscription id to initiate a payment for.")

class BuyerSerializer(serializers.Serializer):
    """Buyer identity the gateway requires. Any field omitted falls back to the Customer."""

    name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    document = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")

class ChargeInitiationSerializer(serializers.Serializer):
    """Input for `POST /charges` (Flow B): a tenant-scoped one-off charge.

    `external_ref` identifies the thing being paid for in the CALLER's own
    system (for yvyreta: an `Installment` pk) and is the idempotency key,
    unique per consuming app.
    """

    external_ref = serializers.CharField(
        max_length=255,
        help_text="Caller's reference for what is being paid (e.g. 'installment:4471'). "
        "Idempotency key, unique per app.",
    )
    amount_pyg = serializers.IntegerField(
        min_value=1, help_text="Amount in PYG. Integer — PYG has no subunits."
    )
    description = serializers.CharField(max_length=255, help_text="Shown to the buyer at checkout.")
    customer_ref = serializers.CharField(
        max_length=255,
        help_text="The buyer, by the caller's own reference. Created on first use.",
    )
    merchant_ref = serializers.CharField(
        max_length=255,
        help_text="REQUIRED. MerchantAccount.external_ref of the company collecting this "
        "money. There is no default: omitting it would settle a buyer's payment into the "
        "SaaS owner's account.",
    )
    buyer = BuyerSerializer(required=False)

class ProblemSerializer(serializers.Serializer):
    """The error body every endpoint returns (see `payments_core.exceptions`).

    Published so callers branch on the machine-readable `code`, not on prose.
    """

    type = serializers.CharField()
    title = serializers.CharField()
    detail = serializers.CharField()
    code = serializers.CharField()


class PaymentResultSerializer(serializers.Serializer):
    """The ONLY field the public result route exposes."""

    status = serializers.ChoiceField(choices=["pending", "confirmed", "failed", "expired"])
