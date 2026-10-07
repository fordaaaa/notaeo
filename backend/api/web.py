"""Keyless public web discovery routes."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from core.models import WebDiscoveryResponse
from core.websearch import WebSearchError, search_web
from core.webdiscovery import WebDiscoveryError, discover


def register(app: FastAPI) -> None:
    @app.get("/api/web/search")
    def search_the_web(
        q: str = Query(min_length=1, max_length=500),
        limit: int = Query(default=8, ge=1, le=10),
    ):
        try:
            return search_web(q, limit)
        except WebSearchError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/web/discover", response_model=WebDiscoveryResponse)
    def discover_the_web(
        q: str = Query(min_length=1, max_length=500),
        limit: int = Query(default=20, ge=1, le=30),
        engine: str = Query(default="auto"),
        domain: str | None = Query(default=None),
        file_type: str = Query(default="all"),
        academic: bool = Query(default=False),
        recency: str = Query(default="any"),
        region: str = Query(default="us-en"),
    ):
        try:
            return discover(
                q,
                limit=limit,
                engine=engine,
                domain=domain,
                file_type=file_type,
                academic=academic,
                recency=recency,
                region=region,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except WebDiscoveryError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
