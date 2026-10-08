"""Cited notebook chat backed by the per-app AI service (no keys)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query

from api.deps import get_ai_service, get_current_user, get_store, notebook_or_404, safe_id
from core.api import AIError
from core import skills
from core.context import build_context, build_note_excerpts
from core.models import ChatMessage, ChatRequest, ChatResponse, ChatSession, ChatSessionCreate, User, utcnow
from core.store import new_id

MAX_SESSION_HISTORY_CHARS = 4_000


def register(app: FastAPI) -> None:
    @app.get("/api/ai/status")
    def ai_status(user: User = Depends(get_current_user)):
        service = get_ai_service(app)
        return {"enabled": service.enabled, "model": service.model if service.enabled else None}

    @app.get("/api/ai/hosted/status")
    def hosted_status(user: User = Depends(get_current_user)):
        """Hosted alias retained for private research-server compatibility."""
        service = get_ai_service(app)
        return {
            "enabled": service.enabled,
            "model": service.model if service.enabled else None,
            "allowance_remaining": None,
        }

    @app.get("/api/notebooks/{notebook_id}/chat/sessions", response_model=list[ChatSession])
    def list_sessions(notebook_id: str, user: User = Depends(get_current_user)):
        notebook_id = safe_id(notebook_id, "notebook_id")
        store = get_store(app)
        notebook_or_404(store, user.id, notebook_id)
        return store.list_chat_sessions(notebook_id)

    @app.post("/api/notebooks/{notebook_id}/chat/sessions", response_model=ChatSession, status_code=201)
    def create_session(notebook_id: str, body: ChatSessionCreate, user: User = Depends(get_current_user)):
        notebook_id = safe_id(notebook_id, "notebook_id")
        store = get_store(app)
        notebook_or_404(store, user.id, notebook_id)
        now = utcnow()
        return store.create_chat_session(ChatSession(id=new_id(), notebook_id=notebook_id, title=body.title.strip(), created_at=now, updated_at=now))

    @app.get("/api/notebooks/{notebook_id}/chat/sessions/{session_id}", response_model=ChatSession)
    def get_session(notebook_id: str, session_id: str, user: User = Depends(get_current_user)):
        notebook_id = safe_id(notebook_id, "notebook_id")
        session_id = safe_id(session_id, "session_id")
        store = get_store(app)
        notebook_or_404(store, user.id, notebook_id)
        session = store.get_chat_session(notebook_id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="chat session not found")
        return session

    @app.delete("/api/notebooks/{notebook_id}/chat/sessions/{session_id}", status_code=204)
    def delete_session(notebook_id: str, session_id: str, user: User = Depends(get_current_user)):
        notebook_id = safe_id(notebook_id, "notebook_id")
        session_id = safe_id(session_id, "session_id")
        store = get_store(app)
        notebook_or_404(store, user.id, notebook_id)
        if not store.delete_chat_session(notebook_id, session_id):
            raise HTTPException(status_code=404, detail="chat session not found")

    @app.get("/api/notebooks/{notebook_id}/chat/sessions/{session_id}/messages", response_model=list[ChatMessage])
    def list_messages(
        notebook_id: str,
        session_id: str,
        limit: int = Query(default=100, ge=1, le=500),
        before: str | None = None,
        user: User = Depends(get_current_user),
    ):
        notebook_id = safe_id(notebook_id, "notebook_id")
        session_id = safe_id(session_id, "session_id")
        if before is not None:
            before = safe_id(before, "before")
        store = get_store(app)
        notebook_or_404(store, user.id, notebook_id)
        if not store.get_chat_session(notebook_id, session_id):
            raise HTTPException(status_code=404, detail="chat session not found")
        if before is not None and store.get_chat_message(session_id, before) is None:
            # Cursor targets a missing/foreign message: same 404 body as a
            # malformed cursor so callers cannot probe message-id validity.
            raise HTTPException(status_code=404, detail="chat message not found")
        return store.list_chat_messages(session_id, limit=limit, before=before)

    @app.post("/api/notebooks/{notebook_id}/chat/sessions/{session_id}/messages", response_model=ChatMessage)
    def session_message(notebook_id: str, session_id: str, body: ChatRequest, user: User = Depends(get_current_user)):
        notebook_id = safe_id(notebook_id, "notebook_id")
        session_id = safe_id(session_id, "session_id")
        store = get_store(app)
        notebook_or_404(store, user.id, notebook_id)
        session = store.get_chat_session(notebook_id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="chat session not found")
        service = get_ai_service(app)
        if not service.enabled:
            raise HTTPException(status_code=503, detail="AI is unavailable right now. Try again later.")
        excerpts, citations = build_context(store, notebook_id, query=body.message)
        note_excerpts = build_note_excerpts(store, notebook_id)
        memory = store.get_memory(notebook_id).strip()[:3000]
        if memory:
            note_excerpts.append(memory)
        if not excerpts and not note_excerpts:
            raise HTTPException(status_code=400, detail="add a source or note before asking AI")
        history = store.list_chat_messages(session_id, limit=8)
        history_text = "\n".join(f"{message.role.upper()}: {message.text}" for message in history)
        if len(history_text) > MAX_SESSION_HISTORY_CHARS:
            history_text = history_text[-MAX_SESSION_HISTORY_CHARS:]
        notes_text = "\n\n".join(note_excerpts)
        sources_text = "\n\n".join(excerpts) if excerpts else "(No source excerpts; use the notebook notes below.)"
        prompt = (
            "Answer only from the notebook excerpts below. If the answer is not present, say so. "
            "Use citation markers like [1] for numbered source excerpts; identify notebook notes by title.\n\n"
            "SOURCES:\n" + sources_text + "\n\n"
            f"RECENT CHAT:\n{history_text}\n\nNOTE EXCERPTS:\n{notes_text}\n\nQUESTION: {body.message}"
        )
        matched = skills.match_skills(store.list_skills(user.id), body.message)
        if matched:
            prompt += "\n\n" + skills.skills_section(matched)
        try:
            answer, used_model = service.generate(user.id, prompt)
        except AIError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return store.append_chat_exchange(session, body.message, answer, citations, used_model)

    @app.post("/api/notebooks/{notebook_id}/chat", response_model=ChatResponse)
    def chat(notebook_id: str, body: ChatRequest, user: User = Depends(get_current_user)):
        notebook_id = safe_id(notebook_id, "notebook_id")
        store = get_store(app)
        notebook_or_404(store, user.id, notebook_id)
        service = get_ai_service(app)
        if not service.enabled:
            raise HTTPException(status_code=503, detail="AI is unavailable right now. Try again later.")

        excerpts, citations = build_context(store, notebook_id, query=body.message)
        if not excerpts:
            raise HTTPException(status_code=400, detail="add a source before asking AI")
        prompt = (
            "Answer only from the notebook excerpts below. If the answer is not present, say so. "
            "Use citation markers like [1] that match the supplied excerpt numbers.\n\n"
            f"QUESTION: {body.message}\n\nSOURCES:\n" + "\n\n".join(excerpts)
        )
        matched = skills.match_skills(store.list_skills(user.id), body.message)
        if matched:
            prompt += "\n\n" + skills.skills_section(matched)
        notes = store.get_memory(notebook_id)
        if notes.strip():
            prompt += "\n\n" + skills.memory_section(notes.strip())
        try:
            answer, used_model = service.generate(user.id, prompt)
        except AIError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ChatResponse(answer=answer, citations=citations, model=used_model)
