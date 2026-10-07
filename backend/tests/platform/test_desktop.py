from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import desktop
from api.main import create_app


def test_desktop_app_is_api_only_and_persists_to_configured_data_dir(
    tmp_path, monkeypatch
):
    data = tmp_path / "Library" / "Application Support" / "research" / "data"
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-123")
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)

    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 404
        assert client.get("/index.html").status_code == 404
        assert client.get("/app.js").status_code == 404
        launch = {"X-Notaeo-Desktop-Token": "launch-123"}
        token = client.post(
            "/api/auth/register",
            headers=launch,
            json={"email": "desk@example.com", "password": "password123"},
        ).json()["token"]
        headers = {**launch, "Authorization": f"Bearer {token}"}
        notebook = client.post("/api/notebooks", json={"name": "Desktop"}, headers=headers).json()
        assert client.get("/api/health").json() == {"ok": True}

    assert (data / "app.db").is_file()
    assert notebook["name"] == "Desktop"


def test_legacy_web_config_cannot_restore_website(tmp_path, monkeypatch):
    web = tmp_path / "Resources" / "web"
    web.mkdir(parents=True)
    (web / "index.html").write_text("desktop")
    monkeypatch.setenv("RESEARCH_WEB_DIR", str(web))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "launch-123")
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))

    assert not hasattr(desktop, "web_root")
    with pytest.raises(TypeError):
        create_app(web)  # type: ignore[arg-type]
    with TestClient(desktop.create_desktop_app()) as client:
        assert client.get("/").status_code == 404
        assert client.get("/index.html").status_code == 404


def test_desktop_session_requires_launch_header_and_bearer_ownership(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RESEARCH_DESKTOP_TOKEN", "only-this-launch")
    monkeypatch.delenv("RESEARCH_NATIVE_DESKTOP", raising=False)

    with TestClient(create_app(), follow_redirects=False) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/notebooks").status_code == 403
        response = client.get("/?desktop_token=only-this-launch")
        assert response.status_code == 404
        assert "set-cookie" not in response.headers
        client.cookies.set("research_session", "only-this-launch")
        assert client.get("/api/notebooks").status_code == 403
        launch = {"X-Notaeo-Desktop-Token": "only-this-launch"}
        assert client.get("/api/notebooks", headers=launch).status_code == 401
        token = client.post(
            "/api/auth/register",
            headers=launch,
            json={"email": "desk@example.com", "password": "password123"},
        ).json()["token"]
        own = {**launch, "Authorization": f"Bearer {token}"}
        assert client.get("/api/notebooks", headers=own).status_code == 200
        assert client.get("/api/notebooks", headers={"Authorization": own["Authorization"]}).status_code == 403
        second = client.post(
            "/api/auth/register",
            headers=launch,
            json={"email": "other@example.com", "password": "password123"},
        ).json()["token"]
        nid = client.post("/api/notebooks", headers=own, json={"name": "N"}).json()["id"]
        other = {**launch, "Authorization": f"Bearer {second}"}
        assert client.get(f"/api/notebooks/{nid}", headers=other).status_code == 404
        assert client.get("/api/runtime", headers=launch).headers["x-frame-options"] == "DENY"
