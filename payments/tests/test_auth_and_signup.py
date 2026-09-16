"""D1: ApiKeyAuthentication + POST /customers/signup."""

from apps.contracts.models import Contract, ContractStatus
from apps.customers.models import Customer
from apps.subscriptions.models import Subscription, SubscriptionStatus
from tests.conftest import authed_client


def test_signup_requires_auth(api_client):
    response = api_client.post("/api/v1/customers/signup", {"external_ref": "cust-1"})
    assert response.status_code == 401


def test_signup_rejects_invalid_key(db, api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Api-Key not.a-real-key")
    response = api_client.post("/api/v1/customers/signup", {"external_ref": "cust-1"})
    assert response.status_code == 401


def test_signup_rejects_revoked_key(provisioned_app):
    app, raw_key = provisioned_app
    app.api_keys.get().revoke()
    client = authed_client(raw_key)
    response = client.post("/api/v1/customers/signup", {"external_ref": "cust-1"})
    assert response.status_code == 401


def test_signup_happy_path_creates_contract_and_trial_subscription(provisioned_app):
    app, raw_key = provisioned_app
    client = authed_client(raw_key)

    response = client.post("/api/v1/customers/signup", {"external_ref": "cust-1", "email": "a@b.com"})

    assert response.status_code == 201
    customer = Customer.objects.get(app=app, external_ref="cust-1")
    contract = Contract.objects.get(customer=customer)
    subscription = Subscription.objects.get(customer=customer)

    assert contract.status == ContractStatus.GENERATED
    assert subscription.status == SubscriptionStatus.TRIALING
    assert response.data["contract"]["status"] == "generated"
    assert response.data["subscription"]["status"] == "trialing"


def test_signup_is_idempotent_by_external_ref(provisioned_app):
    app, raw_key = provisioned_app
    client = authed_client(raw_key)

    first = client.post("/api/v1/customers/signup", {"external_ref": "cust-1"})
    second = client.post("/api/v1/customers/signup", {"external_ref": "cust-1"})

    assert first.status_code == 201
    assert second.status_code == 200
    assert Customer.objects.filter(app=app, external_ref="cust-1").count() == 1
    assert Contract.objects.filter(customer__app=app).count() == 1
    assert Subscription.objects.filter(customer__app=app).count() == 1


def test_signup_conflicts_when_app_not_provisioned(db, api_client):
    from apps.apps_registry.models import ApiKey, ConsumingApp

    app = ConsumingApp.objects.create(name="unprovisioned-app")
    from django.contrib.auth.hashers import make_password

    from apps.apps_registry.models import _generate_key_prefix, _generate_key_secret

    prefix, secret = _generate_key_prefix(), _generate_key_secret()
    ApiKey.objects.create(app=app, prefix=prefix, hashed_secret=make_password(secret))

    client = authed_client(f"{prefix}.{secret}")
    response = client.post("/api/v1/customers/signup", {"external_ref": "cust-1"})
    assert response.status_code == 409


def test_cross_tenant_signup_isolation(provisioned_app, other_provisioned_app):
    """The fitness test from design §5: app A must never read app B's data."""
    app_a, key_a = provisioned_app
    app_b, key_b = other_provisioned_app

    client_a = authed_client(key_a)
    client_b = authed_client(key_b)

    client_a.post("/api/v1/customers/signup", {"external_ref": "shared-ref"})
    client_b.post("/api/v1/customers/signup", {"external_ref": "shared-ref"})

    # Same external_ref under two different apps is NOT the same customer.
    response = client_b.get("/api/v1/customers/shared-ref/")
    customer_b = Customer.objects.get(app=app_b, external_ref="shared-ref")
    assert response.status_code == 200
    assert response.data["external_ref"] == "shared-ref"

    # App A cannot see app B's contract/subscription ids by any means exposed here.
    contract_b_id = Contract.objects.get(customer=customer_b).id
    forbidden = client_a.get(f"/api/v1/contracts/{contract_b_id}/")
    assert forbidden.status_code == 404
