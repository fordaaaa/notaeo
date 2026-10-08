"""Bounded exam-coach AI reliability/transparency regressions.

Covers: actual fallback model preserved in API + saved reload, requested==actual
has no substitution notice, malformed/basic have model None, legacy compat,
explain substitution notice, and real-dispatcher transient->fallback path.
"""
from __future__ import annotations

import json
from datetime import timedelta

import httpx

from core.models import CoachSession, utcnow

TEXT = (
    "Photosynthesis converts sunlight into chemical energy inside chloroplasts. "
    "Chlorophyll pigments capture photons in the thylakoid membranes. "
    "Mitochondria release energy from glucose during cellular respiration. "
    "Meiosis produces four haploid cells with half the chromosomes."
)

QUOTE = "Photosynthesis converts sunlight into chemical energy inside chloroplasts."


def _setup(client, *, minutes=20):
    notebook = client.post("/api/notebooks", json={"name": "Biology exam"}).json()
    path = f"/api/notebooks/{notebook['id']}/coach"
    source = client.post(
        f"/api/notebooks/{notebook['id']}/sources/text",
        json={"title": "Lecture", "text": TEXT},
    ).json()
    goal = {
        "title": "Biology midterm",
        "exam_date": (utcnow().date() + timedelta(days=7)).isoformat(),
        "daily_minutes": minutes,
        "focus_topics": [],
    }
    response = client.put(path + "/goal", json=goal)
    assert response.status_code == 200, response.text
    return notebook, path, source, goal


def _tasks_payload(source_id: str) -> str:
    return json.dumps(
        {
            "tasks": [
                {
                    "topic": "Photosynthesis",
                    "prompt": "What does photosynthesis convert?",
                    "answer": QUOTE,
                    "source_id": source_id,
                    "chunk_seq": 0,
                }
            ]
        }
    )


def _status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://provider.invalid/v1")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(f"{status} error", request=request, response=response)


def test_real_dispatcher_fallback_model_preserved_in_api_and_reload(client, monkeypatch):
    """Real providers.generate with transient failure falls back and preserves actual model."""
    from core import openrouter, providers

    notebook, path, source, _ = _setup(client)
    requested = "stale-model:free"
    fallback = "nvidia/nemotron-3-ultra-550b-a55b:free"
    client.put(
        "/api/settings/ai",
        json={"provider": "openrouter", "api_key": "sk-or-long-enough-key-123", "model": requested},
    )
    ai_tasks_json = _tasks_payload(source["id"])

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": ai_tasks_json}}]}

    def post(url, headers=None, json=None, timeout=None):  # noqa: A002
        assert json is not None
        if json["model"] == requested:
            raise _status_error(500)
        return Response()

    monkeypatch.setattr(openrouter.httpx, "post", post)
    monkeypatch.setattr(providers, "sleep", lambda seconds: None)

    response = client.post(path + "/sessions", json={"use_ai": True})
    assert response.status_code in (200, 201), response.text
    session = response.json()
    assert session["generated_by"] == "ai"
    # Actual fallback model must be exposed, with a friendly substitution notice.
    assert session["model"] == fallback
    assert session["notice"] is not None and fallback in session["notice"]

    store = client.app.state.store
    uid = store.get_session_user(client.headers["authorization"].split()[1]).id
    reloaded = store.get_coach_session(uid, notebook["id"], session["id"])
    assert reloaded.model == fallback
    assert reloaded.notice is not None and fallback in reloaded.notice
    state = client.get(path).json()
    saved = next(item for item in state["sessions"] if item["id"] == session["id"])
    assert saved["model"] == fallback


def test_requested_model_same_has_no_substitution_notice(client, monkeypatch):
    from core import providers

    _, path, source, _ = _setup(client)
    client.put("/api/settings/ai", json={"provider": "groq", "api_key": "gsk-test-key-long-enough"})
    # Read back the configured requested model so equality is exact.
    store = client.app.state.store
    uid = store.get_session_user(client.headers["authorization"].split()[1]).id
    requested = store.get_ai_settings(uid).model
    assert requested

    def generate(provider, key, model, prompt):
        assert model == requested
        return _tasks_payload(source["id"]), model

    monkeypatch.setattr(providers, "generate", generate)
    session = client.post(path + "/sessions", json={"use_ai": True}).json()
    assert session["generated_by"] == "ai"
    assert session["model"] == requested
    assert session["notice"] is None


def test_model_notice_uses_settings_at_request_start(client, monkeypatch):
    from core import providers
    from core.models import AISettingsUpdate

    _, path, source, _ = _setup(client)
    client.put("/api/settings/ai", json={"provider": "groq", "api_key": "gsk-test-key-long-enough"})
    store = client.app.state.store
    user = store.get_session_user(client.headers["authorization"].split()[1])
    requested = store.get_ai_settings(user.id).model

    def generate(provider, key, model, prompt):
        # A settings save while the provider request is in flight must not
        # turn an unchanged answering model into an alleged fallback.
        store.save_ai_settings(user.id, AISettingsUpdate(
            provider="groq", api_key="gsk-test-key-long-enough", model="openai/gpt-oss-120b",
        ))
        return _tasks_payload(source["id"]), model

    monkeypatch.setattr(providers, "generate", generate)
    session = client.post(path + "/sessions", json={"use_ai": True}).json()
    assert session["model"] == requested
    assert session["notice"] is None


def test_malformed_payload_and_basic_have_no_model(client, monkeypatch):
    from core import providers

    _, path, _, _ = _setup(client)
    client.put("/api/settings/ai", json={"provider": "groq", "api_key": "gsk-test-key-long-enough"})
    monkeypatch.setattr(providers, "generate", lambda *args: ("not json", "some-model"))
    bad = client.post(path + "/sessions", json={"use_ai": True}).json()
    assert bad["generated_by"] == "basic"
    assert "model" in bad and bad["model"] is None

    basic = client.post(path + "/sessions", json={}).json()
    assert basic["generated_by"] == "basic"
    assert "model" in basic and basic["model"] is None


def test_legacy_session_without_model_field_deserializes():
    from datetime import date

    legacy = {
        "id": "abcdef123456",
        "notebook_id": "abcdef123457",
        "goal": {
            "title": "Midterm",
            "exam_date": date.today().isoformat(),
            "daily_minutes": 20,
            "focus_topics": [],
        },
        "status": "draft",
        "generated_by": "basic",
        "notice": None,
        "tasks": [],
        "attempts": [],
        "created_at": utcnow().isoformat(),
        "completed_at": None,
    }
    session = CoachSession.model_validate(legacy)
    assert session.model is None


def test_explain_substitution_notice_and_fallback_preserved(client, monkeypatch):
    from core import providers

    _, path, source, _ = _setup(client)
    client.put("/api/settings/ai", json={"provider": "groq", "api_key": "gsk-test-key-long-enough"})
    store = client.app.state.store
    uid = store.get_session_user(client.headers["authorization"].split()[1]).id
    requested = store.get_ai_settings(uid).model
    assert requested
    actual = "openai/gpt-oss-120b"
    assert actual != requested

    session = client.post(path + "/sessions", json={}).json()
    task = session["tasks"][0]

    def generate(provider, key, model, prompt):
        payload = {
            "answer": "Sunlight is converted into stored chemical energy [1].",
            "evidence_quote": QUOTE,
        }
        return json.dumps(payload), actual

    monkeypatch.setattr(providers, "generate", generate)
    result = client.post(
        f"{path}/sessions/{session['id']}/tasks/{task['id']}/explain", json={"use_ai": True}
    ).json()
    assert result["generated_by"] == "ai"
    assert result["model"] == actual
    assert result["notice"] is not None and actual in result["notice"]

    def failing(provider, key, model, prompt):
        raise providers.AIError("AI could not answer right now.")

    monkeypatch.setattr(providers, "generate", failing)
    fallback = client.post(
        f"{path}/sessions/{session['id']}/tasks/{task['id']}/explain", json={"use_ai": True}
    ).json()
    assert fallback["generated_by"] == "basic"
    assert fallback["model"] is None
    assert fallback["notice"]
