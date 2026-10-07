"""Keyless public web discovery routes."""
from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException, Query, Request

from api.deps import get_current_user, get_store
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
        request: Request,
        q: str = Query(min_length=1, max_length=500),
        limit: int = Query(default=20, ge=1, le=30),
        engine: str = Query(default="auto"),
        domain: str | None = Query(default=None),
        file_type: str = Query(default="all"),
        academic: bool = Query(default=False),
        recency: str = Query(default="any"),
        region: str = Query(default="us-en"),
    ):
        if engine == "index":
            return _discover_index(request, q, limit, domain, file_type, academic, recency, region)
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


def _discover_index(
    request: Request,
    q: str,
    limit: int,
    domain: str | None,
    file_type: str,
    academic: bool,
    recency: str,
    region: str,
) -> dict:
    """Account-owned cached search over indexed educational sites (no DDGS, no I/O)."""
    try:
        user = get_current_user(request)
    except HTTPException as exc:
        raise HTTPException(status_code=401, detail="login required") from exc
    from core.search import EmptyQuery, parse_query
    from core.webdiscovery import (
        ALLOWED_REGIONS,
        build_effective_query,
        normalize_domain,
        strip_operators,
    )

    start = time.monotonic()
    trimmed = (q or "").strip()
    if not trimmed or len(trimmed) > 500:
        raise HTTPException(status_code=422, detail="q must be 1..500 characters")
    if not isinstance(limit, int) or not (1 <= limit <= 30):
        raise HTTPException(status_code=422, detail="limit must be 1..30")
    if recency != "any":
        raise HTTPException(status_code=422, detail="recency must be any for engine=index")
    if region not in ALLOWED_REGIONS:
        raise HTTPException(status_code=422, detail="region must be one of us-en/ca-en/uk-en/au-en")
    if file_type not in ("all", "pdf", "html"):
        raise HTTPException(status_code=422, detail="file_type must be one of all/pdf/html")
    if not isinstance(academic, bool):
        raise HTTPException(status_code=422, detail="academic must be a boolean")
    domain_norm: str | None = None
    if domain is not None:
        if not isinstance(domain, str) or not domain.strip():
            raise HTTPException(status_code=422, detail="domain must be a bare host")
        try:
            domain_norm = normalize_domain(domain)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        topic = parse_query(strip_operators(trimmed))
    except EmptyQuery as exc:
        raise HTTPException(status_code=422, detail="enter a topic as well as search filters") from exc
    if not topic.terms and not topic.phrases:
        raise HTTPException(status_code=422, detail="enter a topic as well as search filters")
    effective = build_effective_query(trimmed, domain_norm, file_type, academic)
    from core import siteindex as si

    pages = get_store(request.app).list_index_pages(user.id)
    results = si.search_cached_pages(
        pages, trimmed, limit=limit, domain=domain_norm, file_type=file_type, academic=academic,
    )
    took_ms = int((time.monotonic() - start) * 1000)
    return {
        "query": trimmed,
        "effective_query": effective,
        "engine": "index",
        "results": results,
        "took_ms": took_ms,
        "filters": {
            "domain": domain_norm,
            "file_type": file_type,
            "academic": academic,
            "recency": recency,
            "region": region,
        },
    }
