import pytest
from django.db import IntegrityError, transaction

from apps.customers.models import Customer


@pytest.mark.django_db
class TestCustomerTenantScoping:
    def test_external_ref_unique_per_app(self, app):
        Customer.objects.create(app=app, external_ref="cust-1")
        with pytest.raises(IntegrityError), transaction.atomic():
            Customer.objects.create(app=app, external_ref="cust-1")

    def test_same_external_ref_allowed_across_different_apps(self, app):
        from apps.apps_registry.models import ConsumingApp

        other_app = ConsumingApp.objects.create(name="other-app")
        Customer.objects.create(app=app, external_ref="cust-1")
        Customer.objects.create(app=other_app, external_ref="cust-1")
        assert Customer.objects.filter(external_ref="cust-1").count() == 2
