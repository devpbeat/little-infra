"""Root-level shared fixtures for both `tests/` and in-app `apps/*/tests.py` suites."""

import pytest

from apps.apps_registry.models import ConsumingApp
from apps.customers.models import Customer


@pytest.fixture
def app(db):
    return ConsumingApp.objects.create(name="test-app")


@pytest.fixture
def customer_factory(app):
    counter = {"n": 0}

    def _make(**kwargs):
        counter["n"] += 1
        defaults = {"app": app, "external_ref": f"ext-{counter['n']}"}
        defaults.update(kwargs)
        return Customer.objects.create(**defaults)

    return _make
