"""Authentication responses carry secrets and must never be cached."""
from fastapi.testclient import TestClient

from api.main import create_app


def test_auth_and_private_responses_are_not_cacheable(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    with TestClient(create_app()) as client:
        registration = client.post("/api/auth/register", json={
            "email": "privacy@example.test", "password": "password123",
        })
        assert registration.status_code == 201
        token = registration.json()["token"]
        for response in [
            registration,
            client.post("/api/auth/login", json={"email": "privacy@example.test", "password": "wrong-password"}),
            client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}),
            client.get("/api/notebooks", headers={"Authorization": f"Bearer {token}"}),
            client.get("/api/auth/me"),
        ]:
            assert response.headers.get("Cache-Control") == "no-store"
            assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_unhandled_auth_error_is_generic_and_not_cacheable(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        def fail(email):
            raise RuntimeError("synthetic-secret /private/operator")

        monkeypatch.setattr(app.state.store, "get_user_by_email", fail)
        response = client.post("/api/auth/login", json={
            "email": "failure@example.test", "password": "password123",
        })
        assert response.status_code == 500
        assert response.json() == {"detail": "internal server error"}
        assert response.headers.get("Cache-Control") == "no-store"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
