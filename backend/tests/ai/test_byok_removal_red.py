"""RED: BYOK removal contract — per-app AIService, no key routes/providers."""
from __future__ import annotations


def test_ai_service_contract_validates_and_sanitizes():
    from core.api import AIError, AIService

    svc = AIService()
    assert svc.enabled is False
    assert svc.model is None

    svc2 = AIService(model="notaeo-test", handler=lambda uid, prompt: ("  hello  ", "notaeo-test"))
    assert svc2.enabled is True
    answer, model = svc2.generate("u1", "hi")
    assert answer == "  hello  " or answer.strip() == "hello"

    # empty reply -> AIError
    bad = AIService(model="m", handler=lambda uid, prompt: ("   ", "m"))
    try:
        bad.generate("u1", "hi")
        raise AssertionError("expected AIError for empty reply")
    except AIError:
        pass

    # unexpected exception sanitized without secret text
    def boom(uid, prompt):
        raise RuntimeError("super-secret-key-xyz-123 exploded")

    evil = AIService(model="m", handler=boom)
    try:
        evil.generate("u1", "hi")
        raise AssertionError("expected AIError")
    except AIError as exc:
        assert "super-secret-key-xyz-123" not in str(exc)

    # disabled -> AIError
    try:
        AIService().generate("u1", "hi")
        raise AssertionError("expected AIError when disabled")
    except AIError:
        pass


def test_settings_routes_404_and_status_shape(client):
    assert client.get("/api/settings/ai").status_code == 404
    assert client.put("/api/settings/ai", json={}).status_code == 404
    assert client.delete("/api/settings/ai").status_code == 404
    resp = client.get("/api/ai/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"enabled": False, "model": None}
    resp2 = client.get("/api/ai/hosted/status")
    assert resp2.status_code == 200
    assert resp2.json() == {"enabled": False, "model": None, "allowance_remaining": None}


def test_per_app_service_isolation():
    from api.main import create_app
    from core.api import AIService

    a = create_app()
    b = create_app()
    assert a.state.ai_service is not b.state.ai_service
    a.state.ai_service = AIService(model="a", handler=lambda u, p: ("x", "a"))
    assert b.state.ai_service.enabled is False


def test_provider_modules_removed():
    import importlib.util

    for name in ("core.providers", "core.gemini", "core.openrouter", "core.groq"):
        assert importlib.util.find_spec(name) is None, f"{name} should be removed"


def test_legacy_key_table_migration_preserves_data(tmp_path):
    import sqlite3

    from core.store import Store

    store = Store(root=tmp_path / "data")
    uid = store.create_user("mig@example.com", "password123").id
    nb = store.create_notebook(uid, "Keep me")
    # simulate legacy DB with ai_settings table populated
    con = sqlite3.connect(str(store.db_path))
    con.execute(
        "CREATE TABLE IF NOT EXISTS ai_settings (user_id TEXT PRIMARY KEY, provider TEXT, api_key TEXT, model TEXT)"
    )
    con.execute(
        "INSERT OR REPLACE INTO ai_settings VALUES (?,?,?,?)", (uid, "gemini", "secret-key-long-enough", "m")
    )
    con.commit()
    con.close()
    # reopening store must drop legacy table but preserve users/notebooks
    store2 = Store(root=tmp_path / "data")
    assert store2.get_notebook(uid, nb.id) is not None
    con2 = sqlite3.connect(str(store2.db_path))
    tables = {r[0] for r in con2.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con2.close()
    assert "ai_settings" not in tables


def test_disabled_pure_generation_503(client):
    nb = client.post("/api/notebooks", json={"name": "NoAI"}).json()
    client.post(f"/api/notebooks/{nb['id']}/sources/text", json={"title": "T", "text": "Some facts here."})
    assert client.post(f"/api/notebooks/{nb['id']}/chat", json={"message": "hi?"}).status_code == 503
    sess = client.post(f"/api/notebooks/{nb['id']}/chat/sessions", json={}).json()
    assert client.post(
        f"/api/notebooks/{nb['id']}/chat/sessions/{sess['id']}/messages", json={"message": "hi?"}
    ).status_code == 503
    assert client.post("/api/humanize/rewrite", json={"text": "hello world"}).status_code == 503


def test_key_table_migration_failure_does_not_silently_succeed(tmp_path):
    import sqlite3
    from contextlib import contextmanager

    import pytest

    from core.store import Store

    root = tmp_path / "data"
    store = Store(root=root)
    with sqlite3.connect(store.db_path) as con:
        con.execute("CREATE TABLE ai_settings (user_id TEXT, api_key TEXT)")

    class DeniedMigrationStore(Store):
        @contextmanager
        def _connect(self):
            with super()._connect() as con:
                con.set_authorizer(lambda action, *args: (
                    sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_DROP_TABLE else sqlite3.SQLITE_OK
                ))
                yield con

    with pytest.raises(sqlite3.DatabaseError):
        DeniedMigrationStore(root=root)
