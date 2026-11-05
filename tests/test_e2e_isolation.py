"""Real API throttling remains enforced across test-client identities."""

from uuid import uuid4

from fastapi.testclient import TestClient

from commander.api import create_app
from scripts.e2e_isolation import isolate_client


def attempt(client, identity):
    return client.post(
        "/api/auth/login",
        headers={"X-E2E-Client": identity},
        json={"username": "absent-owner", "password": "fictional-invalid-password"},
    )


def test_production_ignores_client_isolation_header(settings):
    with TestClient(create_app(settings)) as client:
        for _ in range(10):
            assert attempt(client, str(uuid4())).status_code == 401
        response = attempt(client, str(uuid4()))
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"


def test_disposable_app_isolates_clients_without_bypassing_auth(settings):
    app = create_app(settings)
    app.middleware("http")(isolate_client)
    first, second = str(uuid4()), str(uuid4())
    with TestClient(app) as client:
        for _ in range(10):
            assert attempt(client, first).status_code == 401
        assert attempt(client, first).status_code == 429
        assert attempt(client, second).status_code == 401
        # Malformed identifiers retain the actual client address and its limit.
        for _ in range(10):
            assert attempt(client, "invalid").status_code == 401
        assert attempt(client, "different-invalid").status_code == 429
