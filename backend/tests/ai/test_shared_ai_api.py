"""Shared AI facade (core.api) behavioral tests.

core.api is the bounded entrypoint for supported providers (gemini /
openrouter / groq). It re-exports the exact AIError / DEFAULT_MODELS /
FALLBACK_MODELS objects from core.providers and its generate() dynamically
delegates to core.providers.generate so existing monkeypatches keep working.
"""
from __future__ import annotations

import httpx
import pytest


def _status_error(url: str, status: int, headers: dict[str, str] | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", url)
    response = httpx.Response(status, headers=headers or {}, request=request)
    return httpx.HTTPStatusError(f"{status} error", request=request, response=response)


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


GEMINI_PAYLOAD = {"candidates": [{"content": {"parts": [{"text": " gemini answer "}]}}]}
OPENROUTER_PAYLOAD = {"choices": [{"message": {"content": "openrouter answer"}}]}
GROQ_PAYLOAD = {"choices": [{"message": {"content": " groq answer "}}]}


def test_facade_reexports_same_objects():
    from core import api, providers

    assert api.AIError is providers.AIError
    assert api.DEFAULT_MODELS is providers.DEFAULT_MODELS
    assert api.FALLBACK_MODELS is providers.FALLBACK_MODELS
    assert set(api.__all__) == {"generate", "AIError", "DEFAULT_MODELS", "FALLBACK_MODELS"}


def test_facade_dispatch_gemini_with_real_transport(monkeypatch):
    from core import api, gemini

    monkeypatch.setattr(gemini.httpx, "post", lambda *a, **k: _Response(GEMINI_PAYLOAD))
    answer, model = api.generate("gemini", "key", "gemini-2.5-flash", "prompt")
    assert answer == "gemini answer"
    assert model == "gemini-2.5-flash"


def test_facade_dispatch_openrouter_with_real_transport(monkeypatch):
    from core import api, openrouter

    calls: list[dict] = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return _Response(OPENROUTER_PAYLOAD)

    monkeypatch.setattr(openrouter.httpx, "post", post)
    answer, model = api.generate("openrouter", "key-123456", "some-model:free", "prompt")
    assert answer == "openrouter answer"
    assert model == "some-model:free"
    assert calls[0]["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls[0]["headers"] == {"Authorization": "Bearer key-123456"}


def test_facade_dispatch_groq_with_real_transport(monkeypatch):
    from core import api, groq

    calls: list[dict] = []

    def post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return _Response(GROQ_PAYLOAD)

    monkeypatch.setattr(groq.httpx, "post", post)
    answer, model = api.generate("groq", "gsk-test-key-123", "openai/gpt-oss-20b", "prompt")
    assert answer == "groq answer"
    assert model == "openai/gpt-oss-20b"
    assert calls[0]["url"] == "https://api.groq.com/openai/v1/chat/completions"


def test_facade_retry_after_short_circuits_through_wrapper(monkeypatch):
    from core import api, gemini, providers

    outcomes = [
        _status_error("https://generativelanguage.googleapis.com/", 429, {"retry-after": "3"}),
        None,
    ]
    calls: list[int] = []

    def post(*args, **kwargs):
        calls.append(1)
        outcome = outcomes[min(len(calls) - 1, len(outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return _Response(GEMINI_PAYLOAD)

    monkeypatch.setattr(gemini.httpx, "post", post)
    sleeps: list[float] = []
    monkeypatch.setattr(providers, "sleep", lambda seconds: sleeps.append(seconds))
    answer, _ = api.generate("gemini", "key", "gemini-2.5-flash", "prompt")
    assert answer == "gemini answer"
    assert sleeps == [3.0]
    assert len(calls) == 2


def test_facade_auth_failure_aborts_without_backups(monkeypatch):
    from core import api, openrouter

    calls: list[int] = []

    def post(*args, **kwargs):
        calls.append(1)
        raise _status_error("https://openrouter.ai/api/v1/chat/completions", 401)

    monkeypatch.setattr(openrouter.httpx, "post", post)
    with pytest.raises(api.AIError) as exc_info:
        api.generate("openrouter", "bad-key", "stale-model:free", "prompt")
    assert len(calls) == 1
    assert "key" in str(exc_info.value).lower()


def test_facade_falls_back_to_backup_model(monkeypatch):
    from core import api, openrouter, providers

    def post(url, headers=None, json=None, timeout=None):
        if json["model"] == "stale-model:free":
            raise _status_error(url, 404)
        return _Response(OPENROUTER_PAYLOAD)

    monkeypatch.setattr(openrouter.httpx, "post", post)
    monkeypatch.setattr(providers, "sleep", lambda seconds: None)
    answer, model = api.generate("openrouter", "key", "stale-model:free", "prompt")
    assert answer == "openrouter answer"
    assert model == "nvidia/nemotron-3-ultra-550b-a55b:free"


def test_providers_generate_monkeypatch_honored_through_facade(monkeypatch):
    from core import api, providers

    def fake_generate(provider, api_key, model, prompt):
        return ("wrapped answer", "wrapped-model")

    monkeypatch.setattr(providers, "generate", fake_generate)
    assert api.generate("groq", "key", "openai/gpt-oss-20b", "prompt") == ("wrapped answer", "wrapped-model")


def test_chat_route_honors_core_api_generate_patch(client, monkeypatch):
    from core import api

    notebook = client.post("/api/notebooks", json={"name": "Facade chat"}).json()
    client.post(f"/api/notebooks/{notebook['id']}/sources/text", json={
        "title": "Lecture", "text": "Mitochondria produce energy for cells.",
    })
    client.put("/api/settings/ai", json={"api_key": "long-enough-test-key-12345", "model": "test-model"})
    calls: list[tuple] = []

    def fake_generate(provider, key, model, prompt):
        calls.append((provider, key, model, prompt))
        assert key == "long-enough-test-key-12345"
        assert "Mitochondria" in prompt or "mitochondria" in prompt.lower() or "energy" in prompt
        return ("Mitochondria produce energy [1].", model)

    monkeypatch.setattr(api, "generate", fake_generate)
    response = client.post(f"/api/notebooks/{notebook['id']}/chat", json={
        "message": "What do mitochondria produce?",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == "Mitochondria produce energy [1]."
    assert body["model"] == "test-model"
    assert len(calls) == 1
    assert "long-enough-test-key-12345" not in response.text
