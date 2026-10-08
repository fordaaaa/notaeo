"""Provider safety: unsupported provider maps to AIError before network."""
from __future__ import annotations

import pytest

from core import providers


def test_unknown_provider_raises_ai_error_without_network(monkeypatch):
    def forbidden_post(*args, **kwargs):
        raise AssertionError("no network for unsupported provider")

    import httpx

    monkeypatch.setattr(httpx, "post", forbidden_post)
    # Also guard adapter-level transports in case dispatch changes.
    from core import gemini, groq, openrouter

    monkeypatch.setattr(gemini.httpx, "post", forbidden_post)
    monkeypatch.setattr(groq.httpx, "post", forbidden_post)
    monkeypatch.setattr(openrouter.httpx, "post", forbidden_post)

    with pytest.raises(providers.AIError) as exc_info:
        providers.generate("bogus-provider", "some-long-enough-key-123", "some-model", "prompt")
    message = str(exc_info.value).lower()
    assert "support" in message or "setting" in message
    assert "some-long-enough-key-123" not in str(exc_info.value)
