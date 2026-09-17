"""Operator (staff) session login and cross-app visibility tests."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.customers.models import Customer

LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
LOGOUT_URL = "/api/v1/auth/logout"


@pytest.fixture
def staff_user(db):
    return User.objects.create_user("operator", password="pw-operator", is_staff=True)


@pytest.fixture
def non_staff_user(db):
    return User.objects.create_user("mortal", password="pw-mortal", is_staff=False)


def _login(client: APIClient, username: str, password: str):
    return client.post(LOGIN_URL, {"username": username, "password": password}, format="json")


class TestLogin:
    def test_staff_login_succeeds(self, staff_user):
        client = APIClient()
        response = _login(client, "operator", "pw-operator")

        assert response.status_code == 200
        assert response.data == {"username": "operator", "is_staff": True}
        assert client.get(ME_URL).status_code == 200

    def test_bad_credentials_rejected(self, staff_user):
        assert _login(APIClient(), "operator", "wrong").status_code == 401

    def test_non_staff_rejected(self, non_staff_user):
        assert _login(APIClient(), "mortal", "pw-mortal").status_code == 403

    def test_me_unauthenticated_is_401(self, db):
        assert APIClient().get(ME_URL).status_code == 401

    def test_logout_ends_session(self, staff_user):
        client = APIClient()
        _login(client, "operator", "pw-operator")

        assert client.post(LOGOUT_URL).status_code == 200
        assert client.get(ME_URL).status_code == 401


class TestStaffCrossAppVisibility:
    def test_staff_sees_customers_of_all_apps(
        self, staff_user, provisioned_app, other_provisioned_app
    ):
        app_a, _ = provisioned_app
        app_b, _ = other_provisioned_app
        Customer.objects.create(app=app_a, external_ref="cust-a")
        Customer.objects.create(app=app_b, external_ref="cust-b")

        client = APIClient()
        _login(client, "operator", "pw-operator")
        response = client.get("/api/v1/customers/")

        assert response.status_code == 200
        refs = {row["external_ref"] for row in response.data["results"]}
        assert refs == {"cust-a", "cust-b"}

    def test_staff_cannot_signup_customers(self, staff_user, provisioned_app):
        client = APIClient()
        _login(client, "operator", "pw-operator")

        response = client.post(
            "/api/v1/customers/signup", {"external_ref": "x"}, format="json"
        )

        assert response.status_code == 403

    def test_staff_cannot_initiate_payments(self, staff_user, db):
        client = APIClient()
        _login(client, "operator", "pw-operator")

        response = client.post("/api/v1/payments", {"subscription": 1}, format="json")

        assert response.status_code == 403

    def test_anonymous_still_denied(self, db, provisioned_app):
        app, _ = provisioned_app
        Customer.objects.create(app=app, external_ref="cust-a")

        # 401 vs 403 depends on which authenticator sets the challenge
        # header; both mean "denied" for an anonymous caller.
        assert APIClient().get("/api/v1/customers/").status_code in (401, 403)
