"""Website-removal regression: API-only server, no static frontend.

Desired end state:
- create_app() takes no web_dir; legacy web config cannot restore a website.
- / , /index.html, /assets/* are always 404.
- Cookie/query desktop exchange is removed; only X-Notaeo-Desktop-Token works,
  whenever RESEARCH_DESKTOP_TOKEN exists (independent of RESEARCH_NATIVE_DESKTOP).
- /docs and /redoc are always disabled; /openapi.json stays on plain server,
  404 with a desktop token.
- Default CORS origins are empty (no ACAO for localhost:5173).
- create_desktop_app() is always API-only and requires absolute external data dir.
"""
from __future__ import annotations

import inspect

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
import desktop


def _make_web_dir(tmp_path):
    web = tmp_path / "web"
    web.mkdir(exist_ok=True)
    (web / "index.html").write_text("<main>Research</main>")
    assets = web / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "app.js").write_text("console.log(1)")
    return web


def test_create_app_takes_no_web_dir_param():
    sig = inspect.signature(create_app)
    assert "web_dir" not in sig.parameters
    assert len(sig.parameters) == 0


def test_legacy_web_dir_arg_cannot_restore_website(tmp_path):
    web = _make_web_dir(tmp_path)
    with pytest.raises(TypeError):
        create_app(web)  # type: ignore[arg-type]


def test_root_index_assets_always_404(tmp_path, monkeypatch):
    _make_web_dir(tmp_path)
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("RESEARCH_DESKTOP_TOKEN", raising=False)
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    monkeypatch.setenv("RESEARCH_WEB_DIR", str(tmp_path / "web"))
    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 404
        assert client.get("/index.html").status_code == 404
        assert client.get("/assets/app.js").status_code == 404


def test_desktop_sidecar_ignores_research_web_dir(tmp_path, monkeypatch):
    web = _make_web_dir(tmp_path)
    monkeypatch.setenv("RESEARCH_WEB_DIR", str(web))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-123")
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    assert not hasattr(desktop, "web_root")
    with TestClient(desktop.create_desktop_app()) as client:
        assert client.get("/").status_code == 404
        assert client.get("/index.html").status_code == 404


def test_cookie_and_query_exchange_removed(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "only-this-launch")
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    with TestClient(create_app(), follow_redirects=False) as client:
        root = client.get("/?desktop_token=only-this-launch")
        assert root.status_code == 404
        assert "set-cookie" not in root.headers
        index = client.get("/index.html?desktop_token=only-this-launch")
        assert index.status_code == 404
        assert "set-cookie" not in index.headers
        client.cookies.set("research_session", "only-this-launch")
        assert client.get("/api/notebooks").status_code == 403


@pytest.mark.parametrize("native", ["absent", "0", "1"])
def test_launch_header_required_independent_of_native_flag(tmp_path, monkeypatch, native):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / f"data-{native}"))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-secret")
    if native == "absent":
        monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    else:
        monkeypatch.setenv("RESEARCH_NATIVE_DESKTOP", native)
    with TestClient(create_app()) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/notebooks").status_code == 403
        assert client.get("/api/notebooks", headers={"X-Notaeo-Desktop-Token": "wrong"}).status_code == 403
        assert client.get("/api/notebooks", headers={"X-Notaeo-Desktop-Token": "launch-secret"}).status_code == 401


def test_valid_launch_header_plus_bearer_works_and_ownership_404(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-secret")
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    with TestClient(create_app()) as client:
        launch = {"X-Notaeo-Desktop-Token": "launch-secret"}
        first = client.post("/api/auth/register", headers=launch, json={"email": "a@example.com", "password": "password123"})
        assert first.status_code == 201
        own = {**launch, "Authorization": f"Bearer {first.json()['token']}"}
        created = client.post("/api/notebooks", headers=own, json={"name": "Exam"})
        assert created.status_code == 201
        nid = created.json()["id"]
        second = client.post("/api/auth/register", headers=launch, json={"email": "b@example.com", "password": "password123"})
        other = {**launch, "Authorization": f"Bearer {second.json()['token']}"}
        assert client.get(f"/api/notebooks/{nid}", headers=other).status_code == 404
        assert client.get(f"/api/notebooks/{nid}", headers={"Authorization": own["Authorization"]}).status_code == 403
        assert client.get("/api/notebooks", headers={"Authorization": own["Authorization"]}).status_code == 403


def test_docs_redoc_always_disabled_openapi_server_only(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("RESEARCH_DESKTOP_TOKEN", raising=False)
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    with TestClient(create_app()) as server:
        assert server.get("/docs").status_code == 404
        assert server.get("/redoc").status_code == 404
        assert server.get("/openapi.json").status_code == 200
        assert server.get("/api/health").status_code == 200
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-secret")
    with TestClient(create_app()) as desk:
        assert desk.get("/docs").status_code == 404
        assert desk.get("/redoc").status_code == 404
        assert desk.get("/openapi.json").status_code == 404


def test_default_cors_empty_no_localhost_accao(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("RESEARCH_DESKTOP_TOKEN", raising=False)
    with TestClient(create_app()) as server:
        allowed = server.get("/api/health", headers={"Origin": "http://localhost:5173"}).headers.get("access-control-allow-origin")
        assert allowed is None
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-secret")
    with TestClient(create_app()) as desk:
        allowed = desk.get("/api/health", headers={"Origin": "http://localhost:5173"}).headers.get("access-control-allow-origin")
        assert allowed is None


def test_native_without_launch_token_fails(monkeypatch):
    monkeypatch.setenv("RESEARCH_NATIVE_DESKTOP", "1")
    monkeypatch.delenv("RESEARCH_DESKTOP_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="RESEARCH_DESKTOP_TOKEN"):
        create_app()


@pytest.mark.parametrize("native", ["absent", "0", "1"])
def test_create_desktop_app_always_requires_external_absolute_data_dir(tmp_path, monkeypatch, native):
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch")
    if native == "absent":
        monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)
    else:
        monkeypatch.setenv("RESEARCH_NATIVE_DESKTOP", native)
    monkeypatch.delenv("RESEARCH_DATA_DIR", raising=False)
    with pytest.raises(RuntimeError, match="RESEARCH_DATA_DIR"):
        desktop.create_desktop_app()
    monkeypatch.setenv("RESEARCH_DATA_DIR", "relative/data")
    with pytest.raises(RuntimeError, match="RESEARCH_DATA_DIR"):
        desktop.create_desktop_app()
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    with TestClient(desktop.create_desktop_app()) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 404


def test_api_features_preserved_behind_launch_header(tmp_path, monkeypatch):
    from api import web as web_module

    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-secret")
    monkeypatch.setattr(web_module, "search_web", lambda q, limit: [{"title": "T", "url": "https://example.com", "snippet": "S"}])
    with TestClient(create_app()) as client:
        launch = {"X-Notaeo-Desktop-Token": "launch-secret"}
        assert client.get("/api/web/search", headers=launch, params={"q": "cells"}).status_code == 200
        token = client.post("/api/auth/register", headers=launch, json={"email": "s@example.com", "password": "password123"}).json()["token"]
        own = {**launch, "Authorization": f"Bearer {token}"}
        assert client.post("/api/notebooks", headers=own, json={"name": "N"}).status_code == 201
        assert client.get("/api/notebooks", headers=own).status_code == 200
