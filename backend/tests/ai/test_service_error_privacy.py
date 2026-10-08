"""Operator errors must never expose credentials or local paths to clients."""
import pytest

from core.api import AIError, AIService


@pytest.mark.parametrize("error_type", [AIError, RuntimeError])
def test_chat_and_rewrite_sanitize_handler_errors(client, error_type):
    secret = "test-secret-/private/operator/config"

    def fail(user_id: str, prompt: str) -> tuple[str, str]:
        raise error_type(secret)

    client.app.state.ai_service = AIService(model="fixed", handler=fail)
    notebook = client.post("/api/notebooks", json={"name": "Privacy"}).json()
    client.post(f"/api/notebooks/{notebook['id']}/sources/text", json={
        "title": "Lecture", "text": "Cells contain mitochondria that produce energy.",
    })
    for path, payload in [
        (f"/api/notebooks/{notebook['id']}/chat", {"message": "What produces energy?"}),
        ("/api/humanize/rewrite", {"text": "Cells contain mitochondria."}),
    ]:
        response = client.post(path, json=payload)
        assert response.status_code == 502
        assert response.json() == {"detail": "AI could not answer right now. Try again later."}
