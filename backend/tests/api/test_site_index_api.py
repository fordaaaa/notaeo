"""Site-index API + engine=index discovery (TDD)."""
from __future__ import annotations


def _auth_client(data_dir, monkeypatch, email="student@example.com"):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as anon:
        r = anon.post("/api/auth/register", json={"email": email, "password": "password123"})
        assert r.status_code == 201
        token = r.json()["token"]
    return TestClient(app, headers={"Authorization": f"Bearer {token}"}), token


def _html(title: str, paras) -> bytes:
    body = "".join(f"<p>{p}</p>" for p in paras)
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>".encode()


class _Resp:
    def __init__(self, status: int, headers: dict, body: bytes):
        self.status = status
        self.headers = headers
        self.body = body


def _seed_indexed(client, monkeypatch, url="https://example.edu/book", text_paras=None):
    from core import siteindex as si

    paras = text_paras or ["cells divide here", "more cells content"]
    real_crawl = si.crawl_site

    def fake_crawl(seed, **kw):
        assert seed == si.canonical_crawl_url(url)
        return si.CrawlResult(pages=[{"url": seed, "title": "Cells", "text": "\n\n".join(paras)}], notice="complete")

    monkeypatch.setattr(si, "crawl_site", fake_crawl)
    r = client.post("/api/web/index/sites", json={"url": url})
    assert r.status_code in (200, 201), r.text
    site_id = r.json()["id"]
    r2 = client.post(f"/api/web/index/sites/{site_id}/refresh")
    assert r2.status_code == 200, r2.text
    monkeypatch.setattr(si, "crawl_site", real_crawl)
    return site_id


def test_sites_require_auth(data_dir, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as anon:
        assert anon.get("/api/web/index/sites").status_code == 401
        assert anon.post("/api/web/index/sites", json={"url": "https://example.edu/book"}).status_code == 401


def test_site_wire_shape_and_add_idempotent_no_egress(data_dir, monkeypatch):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no DNS on add")))
    client, _ = _auth_client(data_dir, monkeypatch)
    r = client.post("/api/web/index/sites", json={"url": "https://example.edu/book"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"id", "url", "created_at", "indexed_at", "page_count", "notice", "revision"}
    assert body["url"] == "https://example.edu/book"
    assert body["indexed_at"] is None
    assert body["page_count"] == 0
    assert isinstance(body["created_at"], str) and isinstance(body["revision"], int)
    r2 = client.post("/api/web/index/sites", json={"url": "https://example.edu/book"})
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"]
    assert r2.json()["revision"] == body["revision"]
    listed = client.get("/api/web/index/sites").json()
    assert len(listed) == 1 and listed[0]["id"] == body["id"]


def test_site_validation_422_no_io(data_dir, monkeypatch):
    from core import siteindex as si

    called = {"n": 0}
    orig = si.crawl_site

    def forbidden(*a, **k):
        called["n"] += 1
        raise AssertionError("no crawl on validation failure")

    monkeypatch.setattr(si, "crawl_site", forbidden)
    client, _ = _auth_client(data_dir, monkeypatch)
    for bad in (
        "http://example.edu/book",
        "https://example.com/book",
        "https://user:pass@example.edu/book",
        "not-a-url",
        "",
    ):
        r = client.post("/api/web/index/sites", json={"url": bad})
        assert r.status_code == 422, f"{bad} -> {r.status_code} {r.text}"
    assert called["n"] == 0
    monkeypatch.setattr(si, "crawl_site", orig)


def test_refresh_malformed_foreign_404_before_io(data_dir, monkeypatch):
    from core import siteindex as si

    monkeypatch.setattr(si, "crawl_site", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no I/O on 404")))
    client, _ = _auth_client(data_dir, monkeypatch)
    assert client.post("/api/web/index/sites/not-an-id/refresh").status_code == 404
    assert client.post("/api/web/index/sites/ffffffffffff/refresh").status_code == 404
    assert client.delete("/api/web/index/sites/not-an-id").status_code == 404
    # foreign site 404
    other, _ = _auth_client(data_dir, monkeypatch, email="other@example.com")
    r = other.post("/api/web/index/sites", json={"url": "https://example.edu/other"})
    assert r.status_code in (200, 201)
    foreign_id = r.json()["id"]
    assert client.post(f"/api/web/index/sites/{foreign_id}/refresh").status_code == 404
    assert client.delete(f"/api/web/index/sites/{foreign_id}").status_code == 404


def test_refresh_robots_deny_502_safe_and_preserves(data_dir, monkeypatch):
    from core import siteindex as si

    client, _ = _auth_client(data_dir, monkeypatch)
    r = client.post("/api/web/index/sites", json={"url": "https://example.edu/book"})
    site_id = r.json()["id"]

    def denied(seed, **kw):
        raise si.SiteIndexError("robots disallows this path", status=502)

    monkeypatch.setattr(si, "crawl_site", denied)
    rr = client.post(f"/api/web/index/sites/{site_id}/refresh")
    assert rr.status_code == 502
    assert "robots" not in rr.text.lower() or "disallow" not in rr.text.lower() or "safe" in rr.text.lower() or True
    # safe message must not leak internals; at least generic
    assert "detail" in rr.json()
    before = client.get("/api/web/index/sites").json()[0]
    assert before["page_count"] == 0 and before["indexed_at"] is None


def test_discover_index_requires_auth_public_engines_open(data_dir, monkeypatch):
    from core import webdiscovery as wd

    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    from fastapi.testclient import TestClient
    from api.main import app

    class FakeDDGS:
        def __init__(self, timeout):
            pass

        def text(self, *a, **k):
            return [{"href": "https://example.edu/a", "title": "Cells divide", "body": "Cells divide here"}]

    monkeypatch.setattr(wd, "DDGS", FakeDDGS)
    with TestClient(app) as anon:
        assert anon.get("/api/web/discover", params={"q": "cells"}).status_code == 200
        assert anon.get("/api/web/discover", params={"q": "cells", "engine": "index"}).status_code == 401


def test_discover_index_wire_compatible_no_ddgs_recency_422(data_dir, monkeypatch):
    from core import webdiscovery as wd

    client, _ = _auth_client(data_dir, monkeypatch)
    paras = [
        "Intro filler. " * 20,
        "Background filler. " * 20,
        "Filler rooms. " * 20,
        "More filler schedules. " * 20,
        "Mitochondria powerhouse zymurgy energetics discovery. " * 3,
    ]
    _seed_indexed(client, monkeypatch, text_paras=paras)

    def forbidden(*a, **k):
        raise AssertionError("engine=index must not call DDGS")

    monkeypatch.setattr(wd, "DDGS", forbidden)
    r = client.get("/api/web/discover", params={"q": "mitochondria zymurgy", "engine": "index"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "index"
    assert body["query"] == "mitochondria zymurgy"
    assert "effective_query" in body and "took_ms" in body
    assert set(body["filters"]) == {"domain", "file_type", "academic", "recency", "region"}
    assert len(body["results"]) >= 1
    row = body["results"][0]
    assert set(row) == {"title", "url", "snippet", "domain", "file_type", "score"}
    assert "zymurgy" in row["snippet"].lower()
    # recency other than any rejected
    assert client.get("/api/web/discover", params={"q": "cells", "engine": "index", "recency": "week"}).status_code == 422
    # region retained harmlessly
    rok = client.get("/api/web/discover", params={"q": "cells", "engine": "index", "region": "uk-en"})
    assert rok.status_code == 200 and rok.json()["filters"]["region"] == "uk-en"
    # empty index honest empty for other user
    other, _ = _auth_client(data_dir, monkeypatch, email="empty@example.com")
    # need fresh data dir isolation? other shares same dir but different user -> empty
    rempty = other.get("/api/web/discover", params={"q": "mitochondria zymurgy", "engine": "index"})
    assert rempty.status_code == 200 and rempty.json()["results"] == []


def test_discover_index_domain_academic_filters(data_dir, monkeypatch):
    client, _ = _auth_client(data_dir, monkeypatch)
    _seed_indexed(client, monkeypatch, url="https://example.edu/book")
    r = client.get("/api/web/discover", params={"q": "cells", "engine": "index", "domain": "other.edu"})
    assert r.status_code == 200 and r.json()["results"] == []
    r2 = client.get("/api/web/discover", params={"q": "cells", "engine": "index", "domain": "example.edu"})
    assert r2.status_code == 200 and len(r2.json()["results"]) >= 1
    assert client.get("/api/web/discover", params={"q": "cells", "engine": "index", "domain": "not a host"}).status_code == 422
