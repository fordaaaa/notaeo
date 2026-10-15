"""Keyless humanizer: flag AI-sounding patterns for free, rewrite with AI only
when the per-app AI service is enabled. Analysis never needs AI."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.deps import get_ai_service, get_current_user
from core import humanize
from core.api import AIError
from core.models import (
    HumanizeAnalyzeRequest,
    HumanizeAnalyzeResponse,
    HumanizeFinding,
    HumanizeRewriteRequest,
    HumanizeRewriteResponse,
    User,
)


class HumanizeFixRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    operations: list[str] = Field(min_length=1, max_length=4)

    @field_validator("operations")
    @classmethod
    def validate_operations(cls, operations: list[str]) -> list[str]:
        if len(set(operations)) != len(operations):
            raise ValueError("operations must not contain duplicates")
        unknown = [operation for operation in operations if operation not in humanize.FIX_OPERATIONS]
        if unknown:
            raise ValueError(f"unknown humanize operation: {unknown[0]}")
        return operations


class HumanizeFixOperation(BaseModel):
    operation: str
    count: int


class HumanizeFixResponse(BaseModel):
    text: str
    operations: list[HumanizeFixOperation]


def register(app: FastAPI) -> None:
    @app.post("/api/humanize/analyze", response_model=HumanizeAnalyzeResponse)
    def analyze(body: HumanizeAnalyzeRequest):
        findings = [HumanizeFinding(**f) for f in humanize.analyze(body.text)]
        return HumanizeAnalyzeResponse(findings=findings, signal_count=len(findings))

    @app.post("/api/humanize/fix", response_model=HumanizeFixResponse)
    def fix(body: HumanizeFixRequest):
        return humanize.apply_fixes(body.text, body.operations)

    @app.post("/api/humanize/rewrite", response_model=HumanizeRewriteResponse)
    def rewrite(body: HumanizeRewriteRequest, user: User = Depends(get_current_user)):
        service = get_ai_service(app)
        if not service.enabled:
            raise HTTPException(
                status_code=503,
                detail="AI is unavailable right now. Try again later.",
            )
        try:
            answer, used_model = service.generate(
                user.id,
                humanize.build_rewrite_prompt(body.text, body.voice_sample),
            )
        except AIError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return HumanizeRewriteResponse(text=answer, model=used_model)
