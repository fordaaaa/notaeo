from __future__ import annotations

import httpx
import pytest

from core import google_auth


def _tokeninfo_payload() -> dict[str, object]:
    return {"aud": "synthetic-client", "exp": 2000000000, "email_verified": "true",
            "email": "  Student@Example.test  ", "sub": "  synthetic-subject  "}


def test_tokeninfo_verification_normalizes_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(google_auth.time, "time", lambda: 1000000000)

    def get(url: str, *, params: dict[str, str], timeout: float, headers: dict[str, str]) -> httpx.Response:
        assert url == "https://oauth2.googleapis.com/tokeninfo"
        assert params == {"id_token": "synthetic-token"}
        assert timeout == 10.0
        return httpx.Response(200, json=_tokeninfo_payload())

    monkeypatch.setattr(google_auth.httpx, "get", get)
    assert google_auth.verify_google_id_token(" synthetic-token ", "synthetic-client") == (
        "student@example.test", "synthetic-subject",
    )


@pytest.mark.parametrize(("field", "value", "message"), [
    ("aud", "another-client", "invalid"), ("exp", 0, "expired"),
    ("exp", "not-a-number", "invalid"), ("exp", None, "invalid"),
    ("email_verified", False, "not verified"), ("email", "", "invalid"),
    ("email", "no-at-sign", "invalid"), ("sub", " ", "invalid"),
])
def test_tokeninfo_rejects_invalid_claims(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object, message: str,
) -> None:
    payload = _tokeninfo_payload()
    payload[field] = value
    monkeypatch.setattr(google_auth.time, "time", lambda: 1000000000)
    monkeypatch.setattr(google_auth.httpx, "get", lambda *args, **kwargs: httpx.Response(200, json=payload))
    with pytest.raises(google_auth.GoogleAuthError, match=message):
        google_auth.verify_google_id_token("synthetic-token", "synthetic-client")


@pytest.mark.parametrize("mode", ["http", "network", "invalid-json"])
def test_tokeninfo_upstream_failures_are_sanitized(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    def get(*args: object, **kwargs: object) -> httpx.Response:
        if mode == "network":
            raise httpx.ConnectError("synthetic upstream detail")
        if mode == "invalid-json":
            return httpx.Response(200, text="synthetic upstream detail")
        return httpx.Response(401, text="synthetic upstream detail")

    monkeypatch.setattr(google_auth.httpx, "get", get)
    with pytest.raises(google_auth.GoogleAuthError) as error:
        google_auth.verify_google_id_token("synthetic-token", "synthetic-client")
    assert "synthetic upstream detail" not in str(error.value)


@pytest.mark.parametrize("token", ["", "   "])
def test_tokeninfo_empty_credential_never_makes_request(monkeypatch: pytest.MonkeyPatch, token: str) -> None:
    def unexpected(*args: object, **kwargs: object) -> httpx.Response:
        raise AssertionError("empty credentials must not make requests")

    monkeypatch.setattr(google_auth.httpx, "get", unexpected)
    with pytest.raises(google_auth.GoogleAuthError, match="missing"):
        google_auth.verify_google_id_token(token, "synthetic-client")


def _anon_client(data_dir, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    from fastapi.testclient import TestClient

    from api.main import app

    return TestClient(app)


def test_google_status_disabled_without_client_id(data_dir, monkeypatch):
    client = _anon_client(data_dir, monkeypatch)
    with client:
        res = client.get("/api/auth/google/status")
        assert res.status_code == 200
        body = res.json()
        assert body["enabled"] is False


def test_google_status_enabled_with_client_id(data_dir, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        res = client.get("/api/auth/google/status")
        assert res.status_code == 200
        body = res.json()
        assert body["enabled"] is True
        assert body["client_id"] == "test-client-id.apps.googleusercontent.com"


def test_google_login_creates_user_and_reuses_sub(data_dir, monkeypatch):
    import api.auth as auth_module

    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth_module, "_verify_google_token", lambda token: ("guser@example.com", "google-sub-1")
    )
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        first = client.post("/api/auth/google", json={"id_token": "valid-token"})
        assert first.status_code == 200
        user_id = first.json()["user"]["id"]
        token = first.json()["token"]
        assert first.json()["user"]["email"] == "guser@example.com"
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200

        second = client.post("/api/auth/google", json={"id_token": "another-token"})
        assert second.status_code == 200
        assert second.json()["user"]["id"] == user_id


def test_google_login_does_not_link_an_existing_email_only_account(data_dir, monkeypatch):
    import api.auth as auth_module

    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth_module, "_verify_google_token", lambda token: ("student@example.com", "google-sub-9")
    )
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as anon:
        assert anon.post(
            "/api/auth/register",
            json={"email": "student@example.com", "password": "password123"},
        ).status_code == 201
        res = anon.post("/api/auth/google", json={"id_token": "valid-token"})
        assert res.status_code == 409
        assert "token" not in res.json()
        assert "user" not in res.json()
        assert app.state.store.get_user_by_google_sub("google-sub-9") is None
        with app.state.store._connect() as con:
            assert con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
        login = anon.post("/api/auth/login", json={"email": "student@example.com", "password": "password123"})
        assert login.status_code == 200


def test_google_login_does_not_replace_an_existing_google_identity(data_dir, monkeypatch):
    import api.auth as auth_module
    from fastapi.testclient import TestClient
    from api.main import app

    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(auth_module, "_verify_google_token", lambda token: ("student@example.com", "google-sub-new"))
    with TestClient(app) as anon:
        user = app.state.store.create_google_user("student@example.com", "google-sub-original")
        response = anon.post("/api/auth/google", json={"id_token": "valid-token"})
        assert response.status_code == 409
        assert app.state.store.get_user_by_google_sub("google-sub-original").id == user.id
        assert app.state.store.get_user_by_google_sub("google-sub-new") is None


def test_google_login_rejects_invalid_token(data_dir, monkeypatch):
    import api.auth as auth_module
    from core.google_auth import GoogleAuthError

    def _bad(token: str):
        raise GoogleAuthError("invalid Google token")

    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(auth_module, "_verify_google_token", _bad)
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        res = client.post("/api/auth/google", json={"id_token": "bad-token-12345"})
        assert res.status_code == 401


def test_google_login_503_without_client_id(data_dir, monkeypatch):
    client = _anon_client(data_dir, monkeypatch)
    with client:
        res = client.post("/api/auth/google", json={"id_token": "anything-12345"})
        assert res.status_code == 503
