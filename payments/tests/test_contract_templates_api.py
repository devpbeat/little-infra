"""Contract template management (staff) and document rendering tests."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.contracts.models import Contract, ContractTemplate
from tests.conftest import authed_client


@pytest.fixture
def staff_client(db):
    User.objects.create_user("operator", password="pw", is_staff=True)
    client = APIClient()
    client.post("/api/v1/auth/login", {"username": "operator", "password": "pw"}, format="json")
    return client


class TestTemplateCrud:
    def test_staff_creates_and_previews_template(self, staff_client):
        response = staff_client.post(
            "/api/v1/contract-templates/",
            {
                "name": "SaaS standard",
                "deal_type": "saas_subscription",
                "body": "# Contract\nClient: {{client_name}} — Fee: Gs. {{monthly_fee_pyg}}",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["is_approved"] is False

        preview = staff_client.get(
            f"/api/v1/contract-templates/{response.data['id']}/preview/"
        )
        assert preview.status_code == 200
        assert "ACME S.A." in preview.data["markdown"]
        assert "{{" not in preview.data["markdown"]

    def test_generate_creates_unapproved_draft(self, staff_client, monkeypatch):
        from apps.contracts import views

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(
            "adapters.anthropic_gen.generator.generate_template_body",
            lambda **kw: f"# Contrato\nCliente: {{{{client_name}}}} ({kw['deal_type']})",
        )
        # The view imports lazily from the module path above; also patch a
        # direct reference if one exists.
        assert views  # imported for monkeypatch scoping clarity

        response = staff_client.post(
            "/api/v1/contract-templates/generate/",
            {"name": "AI SaaS draft", "deal_type": "saas_subscription"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["is_approved"] is False
        assert "{{client_name}}" in response.data["body"]

    def test_generate_without_api_key_is_503(self, staff_client, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        response = staff_client.post(
            "/api/v1/contract-templates/generate/",
            {"name": "x", "deal_type": "saas_subscription"},
            format="json",
        )
        assert response.status_code == 503

    def test_api_key_cannot_touch_templates(self, provisioned_app):
        _app, raw = provisioned_app
        client = authed_client(raw)
        assert client.get("/api/v1/contract-templates/").status_code in (401, 403)
        assert client.post(
            "/api/v1/contract-templates/", {"name": "x"}, format="json"
        ).status_code in (401, 403)


class TestContractDocument:
    def _signed_up_contract(self, raw_key) -> Contract:
        authed_client(raw_key).post(
            "/api/v1/customers/signup",
            {"external_ref": "cust-doc", "display_name": "Ada Lovelace"},
            format="json",
        )
        return Contract.objects.get(customer__external_ref="cust-doc")

    def test_app_renders_document_from_approved_template(self, provisioned_app):
        app, raw = provisioned_app
        contract = self._signed_up_contract(raw)
        ContractTemplate.objects.filter(pk=contract.template_id).update(
            body="Client {{client_name}} of {{app_name}} pays Gs. {{monthly_fee_pyg}}.",
            is_approved=True,
        )

        response = authed_client(raw).get(f"/api/v1/contracts/{contract.pk}/document/")

        assert response.status_code == 200
        assert "Ada Lovelace" in response.data["markdown"]
        assert app.name in response.data["markdown"]
        assert "{{" not in response.data["markdown"]

    def test_unapproved_template_body_is_409(self, provisioned_app):
        _app, raw = provisioned_app
        contract = self._signed_up_contract(raw)
        ContractTemplate.objects.filter(pk=contract.template_id).update(
            body="Draft {{client_name}}", is_approved=False
        )

        assert (
            authed_client(raw).get(f"/api/v1/contracts/{contract.pk}/document/").status_code
            == 409
        )

    def test_cross_tenant_document_denied(self, provisioned_app, other_provisioned_app):
        _app_a, key_a = provisioned_app
        _app_b, key_b = other_provisioned_app
        contract_b = self._signed_up_contract(key_b)

        assert (
            authed_client(key_a).get(f"/api/v1/contracts/{contract_b.pk}/document/").status_code
            == 404
        )
