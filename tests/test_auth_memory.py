from fastapi.testclient import TestClient

from commander.api import create_app


def test_auth_memory_lifecycle(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/memory").status_code == 401
        assert (
            client.post(
                "/api/auth/bootstrap",
                json={
                    "username": "owner",
                    "password": "fictional-test-password",
                    "token": "wrong" * 8,
                },
            ).status_code
            == 403
        )
        r = client.post(
            "/api/auth/bootstrap",
            json={
                "username": "owner",
                "password": "fictional-test-password",
                "token": settings.bootstrap_token,
            },
        )
        assert r.status_code == 200
        headers = {"X-CSRF-Token": r.json()["csrf"]}
        assert (
            client.post(
                "/api/memory", json={"key": "format", "content": "Use short bullets"}
            ).status_code
            == 403
        )
        r = client.post(
            "/api/memory", headers=headers, json={"key": "format", "content": "Use short bullets"}
        )
        assert r.status_code == 200
        item = r.json()
        assert client.get("/api/memory/export").json()[0]["content"] == "Use short bullets"
        assert (
            client.put(
                "/api/memory/" + item["id"],
                headers=headers,
                json={"key": "format", "content": "Use paragraphs", "revision": 5},
            ).status_code
            == 409
        )
        assert (
            client.put(
                "/api/memory/" + item["id"],
                headers=headers,
                json={"key": "format", "content": "Use paragraphs", "revision": 1},
            ).status_code
            == 200
        )
        assert client.post("/api/auth/logout", headers=headers).status_code == 200
        assert client.get("/api/memory").status_code == 401
    with TestClient(create_app(settings)) as client:
        r = client.post(
            "/api/auth/login", json={"username": "owner", "password": "fictional-test-password"}
        )
        headers = {"X-CSRF-Token": r.json()["csrf"]}
        assert client.get("/api/memory").json()[0]["content"] == "Use paragraphs"
        assert client.delete("/api/memory/" + item["id"], headers=headers).status_code == 200
        assert client.get("/api/memory").json() == []
