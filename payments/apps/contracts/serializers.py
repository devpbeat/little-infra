from rest_framework import serializers

from .models import Contract, ContractStatus


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = [
            "id",
            "customer",
            "template",
            "status",
            "external_envelope_id",
            "created_at",
            "updated_at",
            "signed_at",
        ]
        read_only_fields = fields


class ContractTransitionSerializer(serializers.Serializer):
    """Body of `POST /contracts/{id}/transition`.

    Only forward moves the consuming app is allowed to report itself
    (`generated -> sent -> signed`) are accepted here; anything else — e.g.
    jumping straight to `signed`, or `declined`/`voided`/`terminated` — is
    rejected by `_ALLOWED_APP_REPORTED_TRANSITIONS`, independent of the
    broader state machine `Contract.transition_to` enforces (spec:
    contract-tracking, "Invalid transition rejected").
    """

    status = serializers.ChoiceField(choices=[ContractStatus.SENT, ContractStatus.SIGNED])
