"""AI status routes: local default disabled, hosted alias retained."""


def test_r2_hosted_status_route(client):
    resp = client.get("/api/ai/hosted/status")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"enabled": False, "model": None, "allowance_remaining": None}
    from api.main import app

    paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/ai/hosted/status" in paths
    assert "/api/ai/status" in paths


def test_ai_status_requires_auth(data_dir, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as anon:
        assert anon.get("/api/ai/status").status_code == 401
        assert anon.get("/api/ai/hosted/status").status_code == 401


def test_ai_status_reflects_per_app_service(client):
    from core.api import AIService

    assert client.get("/api/ai/status").json() == {"enabled": False, "model": None}
    client.app.state.ai_service = AIService(
        model="notaeo-test", handler=lambda uid, prompt: ("hi", "notaeo-test")
    )
    assert client.get("/api/ai/status").json() == {"enabled": True, "model": "notaeo-test"}
    assert client.get("/api/ai/hosted/status").json() == {
        "enabled": True, "model": "notaeo-test", "allowance_remaining": None,
    }
