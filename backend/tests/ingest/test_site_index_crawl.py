"""Selected educational-site index: core crawl/scope/robots/bounds (TDD)."""
from __future__ import annotations


def _html(title: str, paras: list[str], links: list[str] | None = None) -> bytes:
    body = "".join(f"<p>{p}</p>" for p in paras)
    anchors = "".join(f'<a href="{h}">x</a>' for h in (links or []))
    return f"<html><head><title>{title}</title></head><body>{body}{anchors}</body></html>".encode()


class _Resp:
    def __init__(self, status: int, headers: dict, body: bytes):
        self.status = status
        self.headers = headers
        self.body = body


def _clock():
    t = {"now": 100.0, "sleeps": []}

    def now():
        return t["now"]

    def sleep(s: float):
        t["sleeps"].append(s)
        t["now"] += s

    return now, sleep, t


def test_canonical_rejects_encoded_slash_and_controls():
    from core import siteindex as si

    for bad in (
        "https://example.edu/a%2Fb",
        "https://example.edu/a%5Cb",
        "https://example.edu/a%00b",
        "https://example.edu/a%2e%2fsecret",
    ):
        try:
            si.canonical_crawl_url(bad)
        except ValueError:
            continue
        raise AssertionError(f"should reject {bad}")


def test_canonical_dotsegments_and_query_stripped():
    from core import siteindex as si

    assert si.canonical_crawl_url("https://Example.EDU:443/a/./b/../c?x=1#frag") == "https://example.edu/a/c"
    # percent-encoded dots participate in dot processing
    assert si.canonical_crawl_url("https://example.edu/a/%2e/b") == "https://example.edu/a/b"


def test_scope_seed_file_and_dir():
    from core import siteindex as si

    seed = si.canonical_crawl_url("https://example.edu/book/chapter.html")
    assert si.is_in_scope(seed, si.canonical_crawl_url("https://example.edu/book/other.html"))
    assert si.is_in_scope(seed, seed)
    assert not si.is_in_scope(seed, si.canonical_crawl_url("https://example.edu/other/page"))
    assert not si.is_in_scope(seed, si.canonical_crawl_url("https://sub.example.edu/book/x"))
    dir_seed = si.canonical_crawl_url("https://example.edu/book")
    assert si.is_in_scope(dir_seed, si.canonical_crawl_url("https://example.edu/book"))
    assert si.is_in_scope(dir_seed, si.canonical_crawl_url("https://example.edu/book/ch"))
    assert not si.is_in_scope(dir_seed, si.canonical_crawl_url("https://example.edu/books"))


def test_scope_checked_before_dns_no_foreign_dns():
    from core import siteindex as si

    calls: list[str] = []

    def validate(url: str) -> None:
        calls.append(url)

    seed = si.canonical_crawl_url("https://example.edu/book")
    # foreign origin must be rejected by scope before validator runs
    assert not si.is_in_scope(seed, "https://evil.com/book")
    # simulate queue filtering: validator must not be called for out-of-scope
    candidates = ["https://evil.com/book", "https://example.edu/book/ok"]
    kept = []
    for cand in candidates:
        try:
            canon = si.canonical_crawl_url(cand)
        except ValueError:
            continue
        if not si.is_in_scope(seed, canon):
            continue
        validate(canon)
        kept.append(canon)
    assert kept == ["https://example.edu/book/ok"]
    assert calls == ["https://example.edu/book/ok"]


def test_robots_exact_notaoe_merge_beats_wildcard_first_match():
    from core import siteindex as si

    txt = (
        "User-agent: *\nDisallow: /\n\n"
        "User-agent: Notaeo\nDisallow: /private\n\n"
        "User-agent: notaeo\nDisallow: /secret\n"
    )
    groups = si.parse_robots(txt)
    # exact Notaeo groups merged: /public allowed, both disallows enforced
    assert si.robots_allowed(groups, "/public") is True
    assert si.robots_allowed(groups, "/private") is False
    assert si.robots_allowed(groups, "/secret") is False
    # wildcard-only would deny /public; exact merge must win over first-match-only
    assert si.robots_allowed(groups, "/public") is True


def test_robots_longest_allow_wins_and_dollar_star():
    from core import siteindex as si

    txt = "User-agent: *\nDisallow: /book\nAllow: /book/public$\n"
    groups = si.parse_robots(txt)
    assert si.robots_allowed(groups, "/book/public") is True
    assert si.robots_allowed(groups, "/book/public/more") is False
    txt2 = "User-agent: *\nDisallow: /a/*\nAllow: /a/b\n"
    groups2 = si.parse_robots(txt2)
    assert si.robots_allowed(groups2, "/a/b/c") is True
    assert si.robots_allowed(groups2, "/a/other") is False


def test_robots_empty_disallow_allows_and_invalid_fails_closed():
    from core import siteindex as si
    import pytest

    groups = si.parse_robots("User-agent: *\nDisallow:\n")
    assert si.robots_allowed(groups, "/anything") is True
    assert si.robots_allowed(si.parse_robots(""), "/anything") is True
    with pytest.raises(si.SiteIndexError):
        si.parse_robots("User-agent: *\nDisallow: /%\n")
    with pytest.raises(si.SiteIndexError):
        si.parse_robots("User-agent: *\nCrawl-delay: -1\n")


def test_robots_delay_rate_interval_and_refuse_over5():
    from core import siteindex as si
    import pytest

    groups = si.parse_robots("User-agent: *\nCrawl-delay: 2\nRequest-rate: 1/2\n")
    assert si.robots_interval(groups) == 2.0
    groups_big = si.parse_robots("User-agent: *\nCrawl-delay: 10\n")
    with pytest.raises(si.SiteIndexError):
        si.robots_interval_checked(groups_big)
    # Request-rate 1/10 => 10s interval refuses
    groups_rate = si.parse_robots("User-agent: *\nRequest-rate: 1/10\n")
    with pytest.raises(si.SiteIndexError):
        si.robots_interval_checked(groups_rate)


def test_crawl_honors_robots_deny_without_egress_to_page():
    from core import siteindex as si

    now, sleep, _ = _clock()
    fetched: list[str] = []

    def fetch(url: str, timeout: float):
        fetched.append(url)
        if url == "https://example.edu/robots.txt":
            return _Resp(200, {"content-type": "text/plain"}, b"User-agent: Notaeo\nDisallow: /book\n")
        raise AssertionError(f"page must not be fetched when robots denies: {url}")

    import pytest

    with pytest.raises(si.SiteIndexError):
        si.crawl_site(
            "https://example.edu/book",
            fetch=fetch,
            validate=lambda u: None,
            now=now,
            sleep=sleep,
        )
    assert fetched == ["https://example.edu/robots.txt"]


def test_crawl_byte_page_depth_time_bounds():
    from core import siteindex as si

    now, sleep, state = _clock()
    big = b"x" * (2 * 1024 * 1024 + 10)
    pages = {
        "https://example.edu/robots.txt": _Resp(200, {"content-type": "text/plain"}, b"User-agent: *\nDisallow:\n"),
        "https://example.edu/book": _Resp(200, {"content-type": "text/html"}, _html("Seed", ["seed text about cells"], ["/book/a", "/book/b", "/book/c", "/book/d", "/book/e", "/book/f"])),
    }
    for name in ("a", "b", "c", "d", "e", "f"):
        pages[f"https://example.edu/book/{name}"] = _Resp(
            200, {"content-type": "text/html"}, _html(f"T {name}", [f"cells content {name}"])
        )
    # oversized page must be skipped, not stored
    pages["https://example.edu/book/a"] = _Resp(200, {"content-type": "text/html"}, big)

    def fetch(url: str, timeout: float):
        assert timeout <= 5.0
        return pages[url]

    result = si.crawl_site(
        "https://example.edu/book",
        fetch=fetch,
        validate=lambda u: None,
        now=now,
        sleep=sleep,
    )
    assert 1 <= len(result.pages) <= 5
    assert result.notice in ("complete", "page_limit", "partial", "time_limit")
    # depth2 respected: seed links depth1 only fetch, no infinite queue
    assert all(u.startswith("https://example.edu/book") for u in [p["url"] for p in result.pages])
    # spacing enforced between requests
    assert any(s >= 1.0 for s in state["sleeps"])


def test_crawl_redirect_scope_and_robots_recheck():
    from core import siteindex as si
    import pytest

    now, sleep, _ = _clock()

    def fetch(url: str, timeout: float):
        if url == "https://example.edu/robots.txt":
            return _Resp(200, {"content-type": "text/plain"}, b"User-agent: *\nDisallow: /blocked\n")
        if url == "https://example.edu/book":
            return _Resp(302, {"location": "https://evil.com/x"}, b"")
        raise AssertionError("must not follow cross-origin redirect")

    with pytest.raises(si.SiteIndexError):
        si.crawl_site("https://example.edu/book", fetch=fetch, validate=lambda u: None, now=now, sleep=sleep)


def test_best_snippet_uses_late_passage_not_first_chars():
    from core import siteindex as si

    paras = [
        "Introduction to cells and tissues with generic filler. " * 4,
        "Methods and background with no distinctive terms. " * 4,
        "More context about lab work and history. " * 4,
        "Even more filler about schedules and rooms. " * 4,
        "The mitochondria powerhouse discovery revolutionized energetics with unique zymurgy term. " * 2,
    ]
    text = "\n\n".join(paras)
    snippet = si.best_snippet(text, "mitochondria zymurgy")
    assert "zymurgy" in snippet.lower()
    assert "mitochondria" in snippet.lower()
    # must not be just the first 160 chars
    assert snippet[:160] != text[:160] or "zymurgy" in snippet[:160].lower()


def test_no_live_crawl_in_tests_uses_injected_transport(monkeypatch):
    from core import siteindex as si
    import socket

    def forbidden(*a, **k):
        raise AssertionError("live DNS/network forbidden in site-index tests")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    now, sleep, _ = _clock()

    def fetch(url: str, timeout: float):
        if url.endswith("/robots.txt"):
            return _Resp(200, {"content-type": "text/plain"}, b"User-agent: *\nDisallow:\n")
        return _Resp(200, {"content-type": "text/html"}, _html("T", ["cells divide here"]))

    result = si.crawl_site("https://example.edu/book", fetch=fetch, validate=lambda u: None, now=now, sleep=sleep)
    assert len(result.pages) >= 1


def test_live_fetch_aborts_slow_stream_within_request_budget(monkeypatch):
    import httpx
    import pytest
    from core import siteindex
    clock = [0.0]
    class Response:
        status_code = 200
        headers = {"content-type": "text/html"}
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def iter_bytes(self, chunk_size=None):
            for _ in range(10):
                clock[0] += 2.0
                yield b"<p>cells</p>"
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def stream(self, *args): return Response()
    monkeypatch.setattr(httpx, "Client", Client)
    monkeypatch.setattr(siteindex.time, "monotonic", lambda: clock[0])
    with pytest.raises(siteindex.SiteIndexError, match="timed out"):
        siteindex._default_fetch("https://example.edu/book", 5.0)
    assert clock[0] <= 6.0


def test_crawl_url_rejects_controls_before_urlsplit_can_remove_them():
    import pytest
    from core.siteindex import canonical_crawl_url
    with pytest.raises(ValueError):
        canonical_crawl_url("https://example.edu/bo\nok")
