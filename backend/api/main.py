"""FastAPI app factory: lifespan, CORS, exception handler, and route mounting.

All route handlers live in `api.notebooks`, `api.sources`, and `api.search`.
Edit those files when adding or changing endpoints. Helpers (id validation,
store access, notebook-not-found) live in `api.deps`.
"""
from __future__ import annotations

import hmac
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import (
    ai,
    auth,
    classroom,
    classes,
    coach,
    dashboard,
    demo,
    humanize,
    notebooks,
    notes,
    outlines,
    research,
    review,
    search,
    siteindex,
    skills,
    sources,
    study,
    web,
)
from core.local_runtime import describe_runtime
from core.store import Store

logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

DESKTOP_TOKEN_HEADER = "X-Notaeo-Desktop-Token"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self';"
        " script-src 'self' https://accounts.google.com;"
        " frame-src https://accounts.google.com;"
        " connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com"
    ),
}


def _token_matches(supplied: str | None, expected: str) -> bool:
    if not supplied or not expected:
        return False
    try:
        return hmac.compare_digest(supplied.encode(), expected.encode())
    except (ValueError, TypeError):
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = Store()
    yield


def create_app() -> FastAPI:
    """Create the API-only app. No website is served; unknown paths are 404."""
    desktop_token = os.environ.get("RESEARCH_DESKTOP_TOKEN") or None
    if os.environ.get("RESEARCH_NATIVE_DESKTOP") == "1" and not desktop_token:
        raise RuntimeError("native desktop requires RESEARCH_DESKTOP_TOKEN")
    app = FastAPI(
        title="Notaeo", version="0.1.0", lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None if desktop_token else "/openapi.json",
    )
    # Native clients need no browser cross-origin access.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def desktop_session(request: Request, call_next):
        if desktop_token:
            if request.url.path.startswith("/api/") and request.url.path != "/api/health":
                credential = request.headers.get(DESKTOP_TOKEN_HEADER)
                if not _token_matches(credential, desktop_token):
                    return JSONResponse(status_code=403, content={"detail": "desktop session required"}, headers=SECURITY_HEADERS)

        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/runtime")
    def runtime():
        """Local-runtime privacy boundary facts; no user data, no paths."""
        return describe_runtime(bool(desktop_token))

    # API-only: route modules define every path; unknown paths are 404.
    notebooks.register(app)
    notes.register(app)
    auth.register(app)
    demo.register(app)
    sources.register(app)
    search.register(app)
    web.register(app)
    siteindex.register(app)
    ai.register(app)
    humanize.register(app)
    skills.register(app)
    study.register(app)
    coach.register(app)
    research.register(app)
    outlines.register(app)
    dashboard.register(app)
    classes.register(app)
    review.register(app)
    classroom.register(app)
    return app


app = create_app()
