"""Shared AI entrypoint for supported providers (gemini/openrouter/groq).

Bounded facade over core.providers: same exact AIError, DEFAULT_MODELS,
and FALLBACK_MODELS objects, with generate() dynamically delegating to
core.providers.generate so existing monkeypatches keep working.
"""
from __future__ import annotations

from core import providers

AIError = providers.AIError
DEFAULT_MODELS = providers.DEFAULT_MODELS
FALLBACK_MODELS = providers.FALLBACK_MODELS

__all__ = ["generate", "AIError", "DEFAULT_MODELS", "FALLBACK_MODELS"]


def generate(provider: str, api_key: str, model: str, prompt: str) -> tuple[str, str]:
    """Return (answer, model_that_answered) via core.providers."""
    return providers.generate(provider, api_key, model, prompt)
