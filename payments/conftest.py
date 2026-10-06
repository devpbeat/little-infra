"""Root-level shared fixtures for both `tests/` and in-app `apps/*/tests.py` suites."""

import pytest

from apps.apps_registry.models import ConsumingApp
from apps.customers.models import Customer


@pytest.fixture(autouse=True)
def credentials_encryption_key(settings):
    """Give every test a FRESH, generated encryption key.

    Generated rather than hardcoded on purpose: a literal Fernet key in a
    committed test file trips secret scanning (correctly — a scanner cannot
    tell a throwaway key from a live one), and a per-run key also proves
    nothing in the suite depends on a specific one.
    """
    from cryptography.fernet import Fernet

    settings.CREDENTIALS_ENCRYPTION_KEY = Fernet.generate_key().decode()


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
