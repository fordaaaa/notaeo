from collections.abc import Callable

import httpx
import pytest

from core import article as article_module
from core import fetcher as fetcher_module
from core.fetcher import MAX_HTML_BYTES, FetchError, _read_html, fetch_article


def test_rejects_non_http_scheme():
    try:
        fetch_article("file:///etc/passwd")
        assert False, "expected FetchError"
    except FetchError:
        pass


def test_rejects_unencrypted_http():
    try:
        fetch_article("http://example.com/article")
        assert False, "expected FetchError"
    except FetchError as exc:
        assert "https" in str(exc).lower()


def test_rejects_userinfo_and_private_hosts():
    for url in ("https://user:pass@example.com/a", "https://127.0.0.1/a"):
        try:
            fetch_article(url)
            assert False, "expected FetchError"
        except FetchError:
            pass


def test_reads_xhtml_articles():
    response = httpx.Response(
        200,
        headers={"content-type": "application/xhtml+xml; charset=utf-8"},
        text="<html><body><article><p>Research text.</p></article></body></html>",
    )
    assert "Research text." in _read_html(response)


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    original_client = httpx.Client
    monkeypatch.setattr(fetcher_module, "_validate_url", lambda url: None)

    def client_factory(
        *, follow_redirects: bool, timeout: float, headers: dict[str, str],
    ) -> httpx.Client:
        return original_client(
            follow_redirects=follow_redirects, timeout=timeout, headers=headers,
            transport=httpx.MockTransport(handler),
        )

    monkeypatch.setattr(httpx, "Client", client_factory)


def _html_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>Notes</p>")


@pytest.mark.parametrize("mime", ["text/plain", "application/json", "application/pdf"])
def test_read_html_rejects_non_html(mime: str) -> None:
    response = httpx.Response(200, headers={"content-type": mime}, text="<p>Notes</p>")
    with pytest.raises(FetchError) as error:
        _read_html(response)
    assert error.value.status == 415


def test_read_html_rejects_declared_oversize() -> None:
    response = httpx.Response(200, headers={
        "content-type": "text/html", "content-length": str(MAX_HTML_BYTES + 1),
    }, content=b"x")
    with pytest.raises(FetchError) as error:
        _read_html(response)
    assert error.value.status == 413


@pytest.mark.parametrize("size", [MAX_HTML_BYTES + 1, MAX_HTML_BYTES + 1024])
def test_read_html_enforces_streamed_limit(size: int) -> None:
    response = httpx.Response(200, headers={"content-type": "text/html"}, stream=httpx.ByteStream(b"a" * size))
    with pytest.raises(FetchError) as error:
        _read_html(response)
    assert error.value.status == 413


def test_read_html_accepts_exact_limit() -> None:
    response = httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * MAX_HTML_BYTES)
    assert len(_read_html(response)) == MAX_HTML_BYTES


@pytest.mark.parametrize("location", ["", "/again"])
def test_redirect_errors_are_bounded(monkeypatch: pytest.MonkeyPatch, location: str) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": location})

    _install_transport(monkeypatch, handler)
    with pytest.raises(FetchError) as error:
        fetch_article("https://example.test/a")
    assert error.value.status == 502
    assert len(requests) == (fetcher_module.MAX_REDIRECTS + 1 if location else 1)


@pytest.mark.parametrize("status", [404, 500])
def test_upstream_http_error_is_sanitized(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    _install_transport(monkeypatch, lambda request: httpx.Response(status, text="private upstream body"))
    with pytest.raises(FetchError) as error:
        fetch_article("https://example.test/a")
    assert error.value.status == 502
    assert str(error.value) == "failed to fetch url"


@pytest.mark.parametrize("extracted", [None, "   ", "Full readable text"])
def test_fetch_uses_structured_fallback(
    monkeypatch: pytest.MonkeyPatch, extracted: str | None,
) -> None:
    _install_transport(monkeypatch, _html_response)
    monkeypatch.setattr(fetcher_module.trafilatura, "extract", lambda *args, **kwargs: extracted)
    article = article_module.Article("Lecture", (
        article_module.ArticleParagraph("Résumé of μ cells."),
        article_module.ArticleParagraph("Second paragraph."),
    ))
    monkeypatch.setattr(article_module, "extract_article", lambda html, url: article)
    text, title = fetch_article("https://example.test/a")
    assert text == (extracted if extracted and extracted.strip() else "Résumé of μ cells.\n\nSecond paragraph.")
    assert title == "Lecture"


def test_fetch_rejects_empty_readable_content(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_transport(monkeypatch, _html_response)
    monkeypatch.setattr(fetcher_module.trafilatura, "extract", lambda *args, **kwargs: None)
    monkeypatch.setattr(article_module, "extract_article", lambda html, url: article_module.Article("", ()))
    with pytest.raises(FetchError, match="no readable article text"):
        fetch_article("https://example.test/a")
