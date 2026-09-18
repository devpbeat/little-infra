"""Staff-only app/API-key management endpoint tests."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.apps_registry.models import ApiKey
from tests.conftest import authed_client


@pytest.fixture
def staff_client(db):
    User.objects.create_user("operator", password="pw", is_staff=True)
    client = APIClient()
    client.post("/api/v1/auth/login", {"username": "operator", "password": "pw"}, format="json")
    return client


class TestAppManagement:
    def test_staff_lists_apps_with_key_metadata(self, staff_client, provisioned_app):
        app, _raw = provisioned_app

        response = staff_client.get("/api/v1/apps/")

        assert response.status_code == 200
        row = next(r for r in response.data["results"] if r["id"] == app.id)
        assert row["name"] == app.name
        assert len(row["api_keys"]) == 1
        # Metadata only — never the secret or its hash.
        assert "hashed_secret" not in row["api_keys"][0]

    def test_staff_issues_key_and_it_authenticates(self, staff_client, provisioned_app):
        app, _raw = provisioned_app

        response = staff_client.post(f"/api/v1/apps/{app.id}/issue-key/")

        assert response.status_code == 201
        raw_key = response.data["api_key"]
        assert "." in raw_key
        # The issued key actually works for machine auth.
        assert authed_client(raw_key).get("/api/v1/customers/").status_code == 200

    def test_staff_revokes_key(self, staff_client, provisioned_app):
        app, raw = provisioned_app
        prefix = raw.split(".")[0]

        response = staff_client.post(
            f"/api/v1/apps/{app.id}/revoke-key/", {"prefix": prefix}, format="json"
        )

        assert response.status_code == 200
        key = ApiKey.objects.get(prefix=prefix)
        assert key.is_active is False and key.revoked_at is not None
        assert authed_client(raw).get("/api/v1/customers/").status_code in (401, 403)

    def test_staff_creates_customer_under_app(self, staff_client, provisioned_app):
        from apps.contracts.models import Contract
        from apps.subscriptions.models import Subscription

        app, _raw = provisioned_app

        response = staff_client.post(
            f"/api/v1/apps/{app.id}/customers/",
            {"external_ref": "staff-cust-1", "display_name": "Grace Hopper"},
            format="json",
        )

        assert response.status_code == 201
        assert Contract.objects.filter(customer__external_ref="staff-cust-1").exists()
        assert Subscription.objects.filter(customer__external_ref="staff-cust-1").exists()
        # Idempotent retry returns the same customer with 200.
        retry = staff_client.post(
            f"/api/v1/apps/{app.id}/customers/",
            {"external_ref": "staff-cust-1"},
            format="json",
        )
        assert retry.status_code == 200

    def test_api_key_cannot_use_management_endpoints(self, provisioned_app):
        app, raw = provisioned_app
        client = authed_client(raw)

        assert client.get("/api/v1/apps/").status_code in (401, 403)
        assert client.post(f"/api/v1/apps/{app.id}/issue-key/").status_code in (401, 403)

    def test_anonymous_denied(self, db):
        assert APIClient().get("/api/v1/apps/").status_code in (401, 403)
