"""API webdiscovery tests (TDD)."""
from __future__ import annotations


def _ok_rows():
    return [
        {"href": "https://example.edu/notes", "title": "Cells", "body": "Cells divide."},
    ]


def test_discover_wire_shape_defaults(monkeypatch, client):
    from core import webdiscovery as wd

    class FakeDDGS:
        def __init__(self, timeout):
            assert timeout == 8

        def text(self, query, max_results, safesearch, backend, region, timelimit):
            assert backend == "auto"
            return list(_ok_rows())

    monkeypatch.setattr(wd, "DDGS", FakeDDGS)
    r = client.get("/api/web/discover", params={"q": "cells"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == "cells"
    assert body["engine"] == "auto"
    assert "effective_query" in body and "cells" in body["effective_query"]
    assert body["filters"] == {
        "domain": None, "file_type": "all", "academic": False, "recency": "any", "region": "us-en",
    }
    assert isinstance(body["took_ms"], int)
    assert len(body["results"]) == 1
    row = body["results"][0]
    assert row == {
        "title": "Cells", "url": "https://example.edu/notes", "snippet": "Cells divide.",
        "domain": "example.edu", "file_type": "html", "score": row["score"],
    }
    assert isinstance(row["score"], (int, float))
    # no fabricated fields
    assert "published" not in row and "date" not in row
    assert "total" not in body and "engine" not in row


def test_discover_public_without_auth(monkeypatch):
    import os
    from fastapi.testclient import TestClient
    from core import webdiscovery as wd

    class FakeDDGS:
        def __init__(self, timeout):
            pass

        def text(self, *a, **k):
            return list(_ok_rows())

    monkeypatch.setattr(wd, "DDGS", FakeDDGS)
    monkeypatch.delenv("RESEARCH_DESKTOP_TOKEN", raising=False)
    # ensure plain app without desktop token is public
    from api.main import app

    with TestClient(app) as anon:
        r = anon.get("/api/web/discover", params={"q": "cells"})
        assert r.status_code == 200


def test_discover_validation_422_before_io(monkeypatch, client):
    from core import webdiscovery as wd

    called = {"n": 0}

    class FakeDDGS:
        def __init__(self, timeout):
            called["n"] += 1

        def text(self, *a, **k):
            called["n"] += 1
            return []

    monkeypatch.setattr(wd, "DDGS", FakeDDGS)
    cases = [
        {"q": "   "},
        {"q": "cells", "engine": "bing"},
        {"q": "cells", "engine": "nope"},
        {"q": "cells", "domain": "https://example.com"},
        {"q": "cells", "domain": "example.com:8080"},
        {"q": "cells", "file_type": "doc"},
        {"q": "cells", "recency": "hour"},
        {"q": "cells", "region": "fr-fr"},
        {"q": "cells", "limit": 0},
        {"q": "cells", "limit": 31},
    ]
    for params in cases:
        r = client.get("/api/web/discover", params=params)
        assert r.status_code == 422, f"{params} -> {r.status_code} {r.text}"
        assert "detail" in r.json()
    assert called["n"] == 0


def test_discover_domain_normalized_and_effective_query(monkeypatch, client):
    from core import webdiscovery as wd

    seen = {}

    class FakeDDGS:
        def __init__(self, timeout):
            pass

        def text(self, query, max_results, safesearch, backend, region, timelimit):
            seen["q"] = query
            return list(_ok_rows())

    monkeypatch.setattr(wd, "DDGS", FakeDDGS)
    r = client.get("/api/web/discover", params={"q": "cells", "domain": "Example.EDU."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filters"]["domain"] == "example.edu"
    assert "site:example.edu" in body["effective_query"]
    assert "site:example.edu" in seen["q"]


def test_discover_explicit_engine_reported_not_switched(monkeypatch, client):
    from core import webdiscovery as wd

    seen = {}

    class FakeDDGS:
        def __init__(self, timeout):
            pass

        def text(self, query, max_results, safesearch, backend, region, timelimit):
            seen["backend"] = backend
            return list(_ok_rows())

    monkeypatch.setattr(wd, "DDGS", FakeDDGS)
    r = client.get("/api/web/discover", params={"q": "cells", "engine": "google"})
    assert r.status_code == 200
    assert r.json()["engine"] == "google"
    assert seen["backend"] == "google"


def test_discover_503_safe_message(monkeypatch, client):
    from core import webdiscovery as wd

    class Broken:
        def __init__(self, timeout):
            pass

        def text(self, *a, **k):
            raise RuntimeError("secret provider detail")

    monkeypatch.setattr(wd, "DDGS", Broken)
    r = client.get("/api/web/discover", params={"q": "cells"})
    assert r.status_code == 503
    assert r.json() == {"detail": "web search is temporarily unavailable"}
    assert "secret" not in r.text


def test_legacy_search_unchanged(monkeypatch, client):
    from api import web

    monkeypatch.setattr(
        web, "search_web",
        lambda query, limit: [{"title": "Cells", "url": "https://example.com", "snippet": "Biology"}],
    )
    r = client.get("/api/web/search", params={"q": "cells"})
    assert r.status_code == 200
    assert r.json()[0]["url"] == "https://example.com"
