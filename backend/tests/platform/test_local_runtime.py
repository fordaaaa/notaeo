"""Local-runtime/privacy boundary: loopback, per-launch session, explicit egress.

API-only server: no website is served. The packaged native shell talks to a
loopback FastAPI sidecar; an account (Bearer) is still mandatory and network
egress must stay explicit (web search / URL ingest / BYOK AI / Google OAuth).
"""
from __future__ import annotations

import inspect


def _data_dir(tmp_path, monkeypatch, data_dir_name="data"):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / data_dir_name))


def test_desktop_query_and_cookie_exchange_removed(tmp_path, monkeypatch):
    _data_dir(tmp_path, monkeypatch, "data-exchange")
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-token-123")
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    from fastapi.testclient import TestClient

    from api.main import create_app

    with TestClient(create_app(), follow_redirects=False) as client:
        for path in ("/?desktop_token=launch-token-123", "/index.html?desktop_token=launch-token-123"):
            response = client.get(path)
            assert response.status_code == 404
            assert "set-cookie" not in response.headers
            assert "research_session" not in response.headers.get("set-cookie", "")
        client.cookies.set("research_session", "launch-token-123")
        assert client.get("/api/notebooks").status_code == 403
        assert client.get("/api/notebooks", headers={"X-Notaeo-Desktop-Token": "launch-token-123"}).status_code == 401


def test_desktop_cors_is_same_origin_only(tmp_path, monkeypatch):
    _data_dir(tmp_path, monkeypatch, "data-cors")
    from fastapi.testclient import TestClient

    from api.main import create_app

    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-token-123")
    with TestClient(create_app()) as desktop_client:
        allowed = desktop_client.get(
            "/api/health", headers={"Origin": "http://localhost:5173"}
        ).headers.get("access-control-allow-origin")
        assert allowed is None

    monkeypatch.delenv("RESEARCH_DESKTOP_TOKEN", raising=False)
    with TestClient(create_app()) as dev_client:
        allowed = dev_client.get(
            "/api/health", headers={"Origin": "http://localhost:5173"}
        ).headers.get("access-control-allow-origin")
        assert allowed is None


def test_runtime_boundary_needs_launch_header_but_no_login(tmp_path, monkeypatch):
    _data_dir(tmp_path, monkeypatch, "data-runtime")
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "only-this-launch")
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    from fastapi.testclient import TestClient

    from api.main import create_app

    with TestClient(create_app()) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/runtime").status_code == 403
        body = client.get("/api/runtime", headers={"X-Notaeo-Desktop-Token": "only-this-launch"}).json()
        assert body["mode"] == "desktop"
        assert body["loopback_only"] is True
        assert body["desktop_session_required"] is True
        assert body["account_required"] is True
        assert body["ai_required"] is False
        assert "web-search-explicit" in body["network_egress"]
        assert "url-ingest-explicit" in body["network_egress"]
        assert "site-index-refresh-explicit" in body["network_egress"]
        assert "managed-ai-explicit" in body["network_egress"]
        assert "byok-ai-explicit" not in body["network_egress"]
        assert "google-oauth-explicit" in body["network_egress"]
        dumped = str(body).lower()
        assert "email" not in dumped
        assert "token" not in dumped or "desktop_session" in dumped
        assert "application support" not in dumped
        assert "users/" not in dumped


def test_runtime_boundary_server_mode_without_desktop_token(tmp_path, monkeypatch):
    _data_dir(tmp_path, monkeypatch, "data-runtime-server")
    monkeypatch.delenv("RESEARCH_DESKTOP_TOKEN", raising=False)
    from fastapi.testclient import TestClient

    from api.main import create_app

    with TestClient(create_app()) as client:
        body = client.get("/api/runtime").json()
        assert body["mode"] == "server"
        assert body["account_required"] is True
        assert body["ai_required"] is False
        assert body["desktop_session_required"] is False


def test_desktop_sidecar_is_loopback_only():
    import desktop

    assert desktop.DESKTOP_HOST == "127.0.0.1"
    source = inspect.getsource(desktop.serve)
    assert "DESKTOP_HOST" in source
    assert "0.0.0.0" not in source


def test_local_runtime_module_declares_explicit_egress_only():
    from core.local_runtime import EXPLICIT_EGRESS, describe_runtime

    assert "web-search-explicit" in EXPLICIT_EGRESS
    assert "url-ingest-explicit" in EXPLICIT_EGRESS
    assert "managed-ai-explicit" in EXPLICIT_EGRESS
    assert "byok-ai-explicit" not in EXPLICIT_EGRESS
    assert "google-oauth-explicit" in EXPLICIT_EGRESS
    assert not any("sync" in item for item in EXPLICIT_EGRESS)
    info = describe_runtime(desktop_session_required=True)
    assert info["mode"] == "desktop"
    assert info["loopback_only"] is True
    assert info["account_required"] is True
    assert info["ai_required"] is False
