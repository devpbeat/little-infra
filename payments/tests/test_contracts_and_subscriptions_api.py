"""D2: contract lifecycle-over-API, entitlement boundaries, cross-tenant isolation, schema."""


from freezegun import freeze_time

from apps.contracts.models import Contract, ContractStatus
from apps.subscriptions.models import Subscription
from tests.conftest import authed_client


def _signup(raw_key, external_ref="cust-1"):
    client = authed_client(raw_key)
    response = client.post("/api/v1/customers/signup", {"external_ref": external_ref})
    assert response.status_code == 201
    return response.data


def test_contract_transition_lifecycle_over_api(provisioned_app):
    app, raw_key = provisioned_app
    _signup(raw_key)
    contract = Contract.objects.get(customer__app=app)
    client = authed_client(raw_key)

    sent = client.post(f"/api/v1/contracts/{contract.id}/transition/", {"status": "sent"})
    assert sent.status_code == 200
    assert sent.data["status"] == "sent"

    signed = client.post(f"/api/v1/contracts/{contract.id}/transition/", {"status": "signed"})
    assert signed.status_code == 200
    assert signed.data["status"] == "signed"
    assert signed.data["signed_at"] is not None


def test_contract_transition_rejects_skipping_states(provisioned_app):
    app, raw_key = provisioned_app
    _signup(raw_key)
    contract = Contract.objects.get(customer__app=app)
    client = authed_client(raw_key)

    response = client.post(f"/api/v1/contracts/{contract.id}/transition/", {"status": "signed"})
    assert response.status_code == 409
    assert response.data["code"] == "invalid_transition"

    contract.refresh_from_db()
    assert contract.status == ContractStatus.GENERATED


def test_contract_list_and_retrieve_scoped_to_app(provisioned_app, other_provisioned_app):
    app_a, key_a = provisioned_app
    app_b, key_b = other_provisioned_app
    _signup(key_a, "cust-a")
    _signup(key_b, "cust-b")

    client_a = authed_client(key_a)
    listing = client_a.get("/api/v1/contracts/")
    assert listing.status_code == 200
    assert len(listing.data["results"]) == 1

    contract_b = Contract.objects.get(customer__app=app_b)
    forbidden = client_a.get(f"/api/v1/contracts/{contract_b.id}/")
    assert forbidden.status_code == 404


def test_subscription_list_scoped_to_app(provisioned_app, other_provisioned_app):
    _, key_a = provisioned_app
    _, key_b = other_provisioned_app
    _signup(key_a, "cust-a")
    _signup(key_b, "cust-b")

    client_a = authed_client(key_a)
    listing = client_a.get("/api/v1/subscriptions/")
    assert listing.status_code == 200
    assert len(listing.data["results"]) == 1


def test_entitlement_true_during_trial(provisioned_app):
    app, raw_key = provisioned_app
    _signup(raw_key)
    client = authed_client(raw_key)

    response = client.get("/api/v1/customers/cust-1/entitlement/")
    assert response.status_code == 200
    assert response.data["entitled"] is True
    assert response.data["status"] == "trialing"


def test_entitlement_false_after_trial_expires(provisioned_app):
    app, raw_key = provisioned_app
    with freeze_time("2026-01-01T00:00:00Z"):
        _signup(raw_key)

    client = authed_client(raw_key)
    with freeze_time("2026-02-01T00:00:01Z"):  # 31 days later — trial_end was +30d
        response = client.get("/api/v1/customers/cust-1/entitlement/")

    assert response.status_code == 200
    assert response.data["entitled"] is False
    assert response.data["status"] == "trialing"


def test_entitlement_true_exactly_at_trial_boundary_minus_one_second(provisioned_app):
    app, raw_key = provisioned_app
    with freeze_time("2026-01-01T00:00:00Z"):
        _signup(raw_key)

    client = authed_client(raw_key)
    with freeze_time("2026-01-30T23:59:59Z"):
        response = client.get("/api/v1/customers/cust-1/entitlement/")

    assert response.data["entitled"] is True


def test_entitlement_via_subscription_endpoint_matches_customer_endpoint(provisioned_app):
    app, raw_key = provisioned_app
    _signup(raw_key)
    subscription = Subscription.objects.get(customer__app=app)
    client = authed_client(raw_key)

    via_customer = client.get("/api/v1/customers/cust-1/entitlement/")
    via_subscription = client.get(f"/api/v1/subscriptions/{subscription.id}/entitlement/")

    assert via_customer.data["entitled"] == via_subscription.data["entitled"]
    assert via_customer.data["status"] == via_subscription.data["status"]


def test_cross_tenant_entitlement_denied(provisioned_app, other_provisioned_app):
    """App A must never read app B's subscription entitlement by id."""
    app_a, key_a = provisioned_app
    app_b, key_b = other_provisioned_app
    _signup(key_a, "cust-a")
    _signup(key_b, "cust-b")

    subscription_b = Subscription.objects.get(customer__app=app_b)
    client_a = authed_client(key_a)
    response = client_a.get(f"/api/v1/subscriptions/{subscription_b.id}/entitlement/")
    assert response.status_code == 404


def test_cross_tenant_contract_transition_denied(provisioned_app, other_provisioned_app):
    """App A must never advance app B's contract lifecycle by id."""
    app_a, key_a = provisioned_app
    app_b, key_b = other_provisioned_app
    _signup(key_a, "cust-a")
    _signup(key_b, "cust-b")

    contract_b = Contract.objects.get(customer__app=app_b)
    client_a = authed_client(key_a)
    response = client_a.post(
        f"/api/v1/contracts/{contract_b.id}/transition/", {"status": "sent"}
    )
    assert response.status_code == 404
    contract_b.refresh_from_db()
    assert contract_b.status == ContractStatus.GENERATED


def test_openapi_schema_lists_key_endpoints(provisioned_app):
    _, raw_key = provisioned_app
    client = authed_client(raw_key)
    response = client.get("/api/schema")
    assert response.status_code == 200
    body = response.content.decode()
    for fragment in ["/customers/signup", "/contracts", "/subscriptions"]:
        assert fragment in body
