"""Smoke test: confirms the Django project boots and the health endpoint responds.

This is intentionally the only test in Slice A. Domain tests land with the
apps that implement them (Slice B onward).
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_returns_ok(client):
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
