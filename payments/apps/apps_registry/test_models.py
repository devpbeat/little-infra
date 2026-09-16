import pytest
from django.db import IntegrityError, transaction

from apps.apps_registry.models import ApiKey, ConsumingApp


@pytest.mark.django_db
class TestApiKeyRevocation:
    def test_revoke_marks_inactive_and_stamps_timestamp(self):
        consuming_app = ConsumingApp.objects.create(name="acme")
        key = ApiKey.objects.create(app=consuming_app, prefix="abcd1234", hashed_secret="hashed")

        key.revoke()

        assert key.is_active is False
        assert key.revoked_at is not None

    def test_prefix_must_be_unique(self):
        consuming_app = ConsumingApp.objects.create(name="acme")
        ApiKey.objects.create(app=consuming_app, prefix="abcd1234", hashed_secret="hashed")
        with pytest.raises(IntegrityError), transaction.atomic():
            ApiKey.objects.create(app=consuming_app, prefix="abcd1234", hashed_secret="hashed2")
