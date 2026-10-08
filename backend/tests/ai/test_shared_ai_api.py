"""Per-app AI service facade tests (BYOK removed, no provider keys)."""
from __future__ import annotations


def test_service_disabled_by_default():
    from core.api import AIService

    svc = AIService()
    assert svc.enabled is False
    assert svc.model is None


def test_service_enabled_with_handler_and_validates_reply():
    from core.api import AIError, AIService

    svc = AIService(model="notaeo-test", handler=lambda uid, prompt: ("hello", "notaeo-test"))
    assert svc.enabled is True
    assert svc.generate("u1", "hi") == ("hello", "notaeo-test")
    bad = AIService(model="m", handler=lambda uid, prompt: ("  ", "m"))
    try:
        bad.generate("u1", "hi")
        raise AssertionError("expected AIError")
    except AIError:
        pass


def test_service_sanitizes_unexpected_exceptions():
    from core.api import AIError, AIService

    def boom(uid, prompt):
        raise RuntimeError("secret-key-material-xyz should never surface")

    svc = AIService(model="m", handler=boom)
    try:
        svc.generate("u1", "hi")
        raise AssertionError("expected AIError")
    except AIError as exc:
        assert "secret-key-material-xyz" not in str(exc)


def test_chat_route_uses_per_app_service(client):
    from core.api import AIService

    notebook = client.post("/api/notebooks", json={"name": "Facade chat"}).json()
    client.post(f"/api/notebooks/{notebook['id']}/sources/text", json={
        "title": "Lecture", "text": "Mitochondria produce energy for cells.",
    })
    calls: list[tuple] = []

    def fake_handler(user_id, prompt):
        calls.append((user_id, prompt))
        assert "Mitochondria" in prompt or "mitochondria" in prompt.lower() or "energy" in prompt
        return ("Mitochondria produce energy [1].", "notaeo-test")

    client.app.state.ai_service = AIService(model="notaeo-test", handler=fake_handler)
    response = client.post(f"/api/notebooks/{notebook['id']}/chat", json={
        "message": "What do mitochondria produce?",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == "Mitochondria produce energy [1]."
    assert body["model"] == "notaeo-test"
    assert len(calls) == 1
