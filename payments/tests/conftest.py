"""Shared pytest fixtures for the payments test suite.

Real outbound sockets are blocked by default via `--disable-socket` in
pyproject.toml. Tests that need to reach a real endpoint (rare, opt-in only)
should request pytest-socket's `socket_enabled` fixture explicitly rather
than relying on anything defined here.
"""

import pytest
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient

from apps.apps_registry.models import (
    ApiKey,
    ConsumingApp,
    _generate_key_prefix,
    _generate_key_secret,
)
from apps.contracts.models import ContractTemplate
from apps.subscriptions.models import Plan


@pytest.fixture
def contract_template(db):
    return ContractTemplate.objects.create(name="Standard SaaS Agreement", reference="tpl-standard")


@pytest.fixture
def plan(db):
    return Plan.objects.create(name="Standard Monthly", price_pyg=500_000)


def _make_app_with_key(name, contract_template=None, default_plan=None, trial_days=30):
    app = ConsumingApp.objects.create(
        name=name,
        contract_template=contract_template,
        default_plan=default_plan,
        trial_days=trial_days,
    )
    prefix = _generate_key_prefix()
    secret = _generate_key_secret()
    ApiKey.objects.create(app=app, prefix=prefix, hashed_secret=make_password(secret))
    return app, f"{prefix}.{secret}"


@pytest.fixture
def provisioned_app(db, contract_template, plan):
    """A ConsumingApp fully provisioned to call `/customers/signup`, plus its raw API key."""
    app, raw_key = _make_app_with_key("bims-shopify", contract_template, plan)
    return app, raw_key


@pytest.fixture
def other_provisioned_app(db, contract_template, plan):
    """A second, unrelated ConsumingApp — used to assert cross-tenant isolation."""
    app, raw_key = _make_app_with_key("other-app", contract_template, plan)
    return app, raw_key


@pytest.fixture
def api_client():
    return APIClient()


def authed_client(raw_key: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {raw_key}")
    return client
