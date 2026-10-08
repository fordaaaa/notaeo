"""Per-app AI service facade (BYOK removed).

The hosted/private integration injects a ready handler per app via
``app.state.ai_service``. Local default is disabled (handler None).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


class AIError(Exception):
    pass


@dataclass
class AIService:
    model: str | None = None
    handler: Callable[[str, str], tuple[str, str]] | None = None

    @property
    def enabled(self) -> bool:
        return self.handler is not None

    def generate(self, user_id: str, prompt: str) -> tuple[str, str]:
        """Return (answer, model_that_answered) via the injected handler."""
        if self.handler is None:
            raise AIError("AI is unavailable right now. Try again later.")
        try:
            result = self.handler(user_id, prompt)
        except Exception as exc:
            raise AIError("AI could not answer right now. Try again later.") from exc
        if not isinstance(result, (tuple, list)) or len(result) != 2:
            raise AIError("AI could not answer right now. Try again later.")
        answer, used_model = result
        if not isinstance(answer, str) or not answer.strip():
            raise AIError("AI could not answer right now. Try again later.")
        if not isinstance(used_model, str) or not used_model.strip():
            raise AIError("AI could not answer right now. Try again later.")
        return answer, used_model


__all__ = ["AIService", "AIError"]
