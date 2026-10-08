"""Bounded exam-coach AI reliability/transparency regressions (managed service).

Covers: actual returned model preserved in API + saved reload,
requested==actual has no substitution notice, malformed/basic have
model None, legacy compat, and explain actual-model + fallback.
"""
from __future__ import annotations

import json
from datetime import timedelta

from core.api import AIService
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


def test_managed_service_actual_model_preserved_in_api_and_reload(client):
    """Managed handler's actual model is preserved in API, store reload, and state."""
    notebook, path, source, _ = _setup(client)
    requested = "requested-model"
    actual = "actual-model"
    client.app.state.ai_service = AIService(
        model=requested,
        handler=lambda user_id, prompt: (_tasks_payload(source["id"]), actual),
    )

    response = client.post(path + "/sessions", json={"use_ai": True})
    assert response.status_code in (200, 201), response.text
    session = response.json()
    assert session["generated_by"] == "ai"
    assert session["model"] == actual

    store = client.app.state.store
    uid = store.get_session_user(client.headers["authorization"].split()[1]).id
    reloaded = store.get_coach_session(uid, notebook["id"], session["id"])
    assert reloaded.model == actual
    state = client.get(path).json()
    saved = next(item for item in state["sessions"] if item["id"] == session["id"])
    assert saved["model"] == actual


def test_requested_model_same_has_no_substitution_notice(client):
    _, path, source, _ = _setup(client)
    requested = "test-model"
    client.app.state.ai_service = AIService(
        model=requested,
        handler=lambda user_id, prompt: (_tasks_payload(source["id"]), requested),
    )
    session = client.post(path + "/sessions", json={"use_ai": True}).json()
    assert session["generated_by"] == "ai"
    assert session["model"] == requested
    assert session["notice"] is None


def test_malformed_payload_and_basic_have_no_model(client):
    _, path, _, _ = _setup(client)
    client.app.state.ai_service = AIService(
        model="test-model",
        handler=lambda user_id, prompt: ("not json", "some-model"),
    )
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


def test_explain_actual_model_preserved_and_fallback(client):
    _, path, source, _ = _setup(client)
    requested = "test-model"
    actual = "actual-explain-model"
    session = client.post(path + "/sessions", json={}).json()
    task = session["tasks"][0]

    def generate(user_id, prompt):
        payload = {
            "answer": "Sunlight is converted into stored chemical energy [1].",
            "evidence_quote": QUOTE,
        }
        return json.dumps(payload), actual

    client.app.state.ai_service = AIService(model=requested, handler=generate)
    result = client.post(
        f"{path}/sessions/{session['id']}/tasks/{task['id']}/explain", json={"use_ai": True}
    ).json()
    assert result["generated_by"] == "ai"
    assert result["model"] == actual

    def failing(user_id, prompt):
        raise RuntimeError("managed service unavailable")

    client.app.state.ai_service = AIService(model=requested, handler=failing)
    fallback = client.post(
        f"{path}/sessions/{session['id']}/tasks/{task['id']}/explain", json={"use_ai": True}
    ).json()
    assert fallback["generated_by"] == "basic"
    assert fallback["model"] is None
    assert fallback["notice"]


def test_disabled_service_falls_back_with_notice(client):
    """Default disabled managed service never infers; use_ai falls back to basic."""
    _, path, _, _ = _setup(client)
    client.app.state.ai_service = AIService()
    assert not client.app.state.ai_service.enabled
    session = client.post(path + "/sessions", json={"use_ai": True}).json()
    assert session["generated_by"] == "basic"
    assert session["model"] is None
    assert session["notice"]
