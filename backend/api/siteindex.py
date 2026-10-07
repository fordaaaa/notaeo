"""Selected educational-site index routes (account-owned, offline search)."""
from __future__ import annotations

import re

from fastapi import Depends, FastAPI, HTTPException

from api.deps import get_current_user, get_store
from core.models import SiteIndexCreate, SiteIndexSite, User
from core.store import IndexConflict, Store

_ID = re.compile(r"^[a-f0-9]{12}$")


def _site_or_404(store: Store, user_id: str, site_id: str) -> dict:
    if not _ID.match(site_id or ""):
        raise HTTPException(status_code=404, detail="site not found")
    site = store.get_index_site(user_id, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="site not found")
    return site


def register(app: FastAPI) -> None:
    @app.get("/api/web/index/sites", response_model=list[SiteIndexSite])
    def list_sites(user: User = Depends(get_current_user)):
        return get_store(app).list_index_sites(user.id)

    @app.post("/api/web/index/sites")
    def add_site(body: SiteIndexCreate, user: User = Depends(get_current_user)):
        from fastapi.responses import JSONResponse

        from core.siteindex import validate_seed_url

        raw = (body.url or "").strip()
        try:
            canon = validate_seed_url(raw)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        store = get_store(app)
        pre = next((s for s in store.list_index_sites(user.id) if s["url"] == canon), None)
        try:
            site = store.create_index_site(user.id, canon)
        except ValueError as exc:
            if "site limit" in str(exc).lower():
                raise HTTPException(status_code=409, detail="site limit reached") from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        status = 200 if pre is not None and pre["id"] == site["id"] else 201
        return JSONResponse(status_code=status, content=site)

    @app.post("/api/web/index/sites/{site_id}/refresh", response_model=SiteIndexSite)
    def refresh_site(site_id: str, user: User = Depends(get_current_user)):
        from core.models import utcnow
        from core.siteindex import SiteIndexError

        store = get_store(app)
        _site_or_404(store, user.id, site_id)
        try:
            claimed = store.claim_index_refresh(user.id, site_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="site not found") from exc
        site = store.get_index_site(user.id, site_id)
        # site must still exist after claim (delete race -> 404, no resurrect)
        if not site:
            raise HTTPException(status_code=404, detail="site not found")
        from core import siteindex as si

        try:
            result = si.crawl_site(site["url"])
        except SiteIndexError as exc:
            status = int(getattr(exc, "status", 502) or 502)
            if status == 422:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            if status == 409:
                raise HTTPException(status_code=409, detail="site was modified concurrently") from exc
            raise HTTPException(status_code=502, detail="site cannot be indexed") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="site cannot be indexed") from exc
        try:
            return store.replace_index_pages(
                user.id, site_id, claimed,
                result.pages, utcnow().isoformat(), result.notice,
            )
        except IndexConflict as exc:
            raise HTTPException(status_code=409, detail="site was modified concurrently") from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="site not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="site cannot be indexed") from exc

    @app.delete("/api/web/index/sites/{site_id}", status_code=204)
    def delete_site(site_id: str, user: User = Depends(get_current_user)):
        store = get_store(app)
        if not _ID.match(site_id or ""):
            raise HTTPException(status_code=404, detail="site not found")
        if not store.delete_index_site(user.id, site_id):
            raise HTTPException(status_code=404, detail="site not found")
        return None
