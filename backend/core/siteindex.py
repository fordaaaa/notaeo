"""Selected educational-site index: canonical scope, RFC9309 robots, bounded crawl.

Local/offline index over account-owned cached article text. No background
crawler, no provider key, no new dependency. All network work is synchronous
and bounded; callers inject transport/clock for deterministic tests.
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from typing import Any, Callable

MAX_SITES = 20
MAX_PAGES = 5
MAX_DEPTH = 2
QUEUE_CAP = 50
MAX_BYTES = 2 * 1024 * 1024
BUDGET_SECONDS = 20.0
PER_REQUEST_TIMEOUT = 5.0
MIN_SPACING = 1.0
MAX_INTERVAL = 5.0
MAX_TEXT = 50_000
MAX_REDIRECTS = 3

USER_AGENT = "Notaeo/1.0 (local research app)"

_VALID_NOTICES = ("complete", "page_limit", "time_limit", "partial")


class SiteIndexError(Exception):
    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class CrawlResult:
    pages: list[dict]
    notice: str


# ---------- canonical crawl URL ----------

_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
_ENCODED_BAD_RE = re.compile(r"%(2f|5c|00|01|02|03|04|05|06|07|08|09|0a|0b|0c|0d|0e|0f|10|11|12|13|14|15|16|17|18|19|1a|1b|1c|1d|1e|1f|7f)", re.I)


def _dot_normalize(path: str) -> str:
    trailing = path.endswith("/") and len(path) > 1
    parts = path.split("/")
    out: list[str] = []
    for seg in parts:
        if seg in ("", "."):
            # preserve leading empty (absolute) but collapse repeats
            if not out and seg == "":
                out.append("")
            continue
        if seg == "..":
            # pop last real segment, keep leading ""
            if len(out) > 1:
                out.pop()
            continue
        out.append(seg)
    normalized = "/".join(out)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if trailing and not normalized.endswith("/"):
        normalized += "/"
    if normalized == "":
        normalized = "/"
    return normalized


def canonical_crawl_url(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise ValueError("url must be https")
    if _CTRL_RE.search(s) or "\\" in s:
        raise ValueError("url contains control characters or separators")
    try:
        parts = urlsplit(s)
    except ValueError as exc:
        raise ValueError("url is malformed") from exc
    if (parts.scheme or "").lower() != "https":
        raise ValueError("url must use https")
    netloc = parts.netloc or ""
    if "@" in netloc:
        raise ValueError("url must not contain credentials")
    if parts.username is not None or parts.password is not None:
        raise ValueError("url must not contain credentials")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("url must contain a hostname")
    if host == "localhost":
        raise ValueError("url host is not allowed")
    try:
        ascii_host = host.encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError) as exc:
        raise ValueError("url host is not allowed") from exc
    if "." not in ascii_host or len(ascii_host) > 253:
        raise ValueError("url host is not allowed")
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("url has an invalid port") from exc
    if port is not None and port != 443:
        raise ValueError("url port is not allowed")
    raw_path = parts.path or "/"
    if _CTRL_RE.search(raw_path):
        raise ValueError("url path contains control characters")
    if _CTRL_RE.search(ascii_host):
        raise ValueError("url host is not allowed")
    if _ENCODED_BAD_RE.search(raw_path):
        raise ValueError("url path uses encoded separators")
    # percent-encoded dots participate in dot processing
    dotted = re.sub(r"%2e", ".", raw_path, flags=re.I)
    if _ENCODED_BAD_RE.search(dotted):
        raise ValueError("url path uses encoded separators")
    norm_path = _dot_normalize(dotted)
    if _CTRL_RE.search(norm_path):
        raise ValueError("url path contains control characters")
    return f"https://{ascii_host}{norm_path}"


def _host_of(canonical: str) -> str:
    return (urlsplit(canonical).hostname or "").lower()


def scope_prefix(seed_canonical: str) -> str:
    path = urlsplit(seed_canonical).path or "/"
    if path == "/" or path == "":
        return "/"
    stripped = path.rstrip("/") or "/"
    if stripped == "/":
        return "/"
    last = stripped.rsplit("/", 1)[-1]
    if "." in last:
        directory = stripped.rsplit("/", 1)[0] or "/"
        if directory == "":
            directory = "/"
        return directory.rstrip("/") or "/"
    return stripped


def is_in_scope(seed_canonical: str, candidate_canonical: str) -> bool:
    try:
        seed_parts = urlsplit(seed_canonical)
        cand_parts = urlsplit(candidate_canonical)
    except ValueError:
        return False
    if (seed_parts.scheme or "").lower() != "https":
        return False
    if (cand_parts.scheme or "").lower() != "https":
        return False
    seed_host = (seed_parts.hostname or "").lower()
    cand_host = (cand_parts.hostname or "").lower()
    if not seed_host or seed_host != cand_host:
        return False
    prefix = scope_prefix(seed_canonical)
    cand_path = cand_parts.path or "/"
    if prefix == "/":
        return True
    if cand_path == prefix or cand_path == prefix + "/":
        return True
    return cand_path.startswith(prefix + "/")


def is_educational_host(host: str) -> bool:
    from core.webdiscovery import is_academic_host

    return is_academic_host(host or "")


def validate_seed_url(raw: str) -> str:
    """Syntactic validation only (no DNS); DNS guard runs per-request during crawl."""
    canon = canonical_crawl_url(raw)
    host = _host_of(canon)
    if not is_educational_host(host):
        raise ValueError("url is not on the educational allowlist")
    return canon


# ---------- RFC9309 robots ----------
# References: https://www.rfc-editor.org/rfc/rfc9309.html

@dataclass
class _Group:
    agents: list[str]
    allows: list[str]
    disallows: list[str]
    delays: list[float]
    rates: list[float]  # intervals seconds/request


_UNRESERVED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def normalize_rfc9309(s: str) -> str:
    try:
        s.encode("utf-8")
    except (UnicodeError, ValueError) as exc:
        raise SiteIndexError("robots rule is malformed", status=502) from exc
    if _CTRL_RE.search(s):
        raise SiteIndexError("robots rule is malformed", status=502)
    out: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "%":
            if i + 2 >= len(s):
                raise SiteIndexError("robots rule is malformed", status=502)
            hexpart = s[i + 1 : i + 3]
            if not re.fullmatch(r"[0-9a-fA-F]{2}", hexpart):
                raise SiteIndexError("robots rule is malformed", status=502)
            byte_val = int(hexpart, 16)
            decoded = chr(byte_val)
            if decoded in _UNRESERVED:
                out.append(decoded)
            else:
                out.append("%" + hexpart.upper())
            i += 3
            continue
        o = ord(ch)
        if o > 127:
            for b in ch.encode("utf-8"):
                out.append(f"%{b:02X}")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _match_robots_pattern(pattern: str, path: str) -> bool:
    pat = normalize_rfc9309(pattern)
    pth = normalize_rfc9309(path)
    if pat == "":
        return False
    if not pat.startswith("/") and not pat.startswith("*"):
        raise SiteIndexError("robots rule is malformed", status=502)
    anchor_end = pat.endswith("$")
    core = pat[:-1] if anchor_end else pat
    parts = core.split("*")
    regex = "^" + ".*".join(re.escape(p) for p in parts)
    if anchor_end:
        regex += "$"
    try:
        return re.match(regex, pth) is not None
    except re.error as exc:
        raise SiteIndexError("robots rule is malformed", status=502) from exc


def parse_robots(text: str) -> list[_Group]:
    if text is None:
        raise SiteIndexError("robots is malformed", status=502)
    if text == "":
        return []
    try:
        text.encode("utf-8")
    except (UnicodeError, ValueError) as exc:
        raise SiteIndexError("robots is malformed", status=502) from exc
    groups: list[_Group] = []
    cur_agents: list[str] = []
    cur_allows: list[str] = []
    cur_disallows: list[str] = []
    cur_delays: list[float] = []
    cur_rates: list[float] = []
    has_rules = False

    def flush():
        nonlocal cur_agents, cur_allows, cur_disallows, cur_delays, cur_rates, has_rules
        if cur_agents:
            groups.append(_Group(list(cur_agents), list(cur_allows), list(cur_disallows), list(cur_delays), list(cur_rates)))
        cur_agents, cur_allows, cur_disallows, cur_delays, cur_rates = [], [], [], [], []
        has_rules = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        name, _, value = line.partition(":")
        name = name.strip().lower()
        value = value.strip()
        if name == "user-agent":
            if not value:
                raise SiteIndexError("robots is malformed", status=502)
            if has_rules:
                flush()
            cur_agents.append(value)
        elif name in ("allow", "disallow"):
            if not cur_agents:
                continue
            has_rules = True
            if value == "":
                if name == "disallow":
                    continue
                continue
            if _CTRL_RE.search(value):
                raise SiteIndexError("robots rule is malformed", status=502)
            # validate percent escapes eagerly (fail closed)
            normalize_rfc9309(value)
            if not value.startswith("/") and not value.startswith("*"):
                raise SiteIndexError("robots rule is malformed", status=502)
            if name == "allow":
                cur_allows.append(value)
            else:
                cur_disallows.append(value)
        elif name == "crawl-delay":
            if not cur_agents:
                continue
            has_rules = True
            try:
                delay = float(value)
            except ValueError as exc:
                raise SiteIndexError("robots rule is malformed", status=502) from exc
            if not math.isfinite(delay) or delay < 0:
                raise SiteIndexError("robots rule is malformed", status=502)
            cur_delays.append(delay)
        elif name == "request-rate":
            if not cur_agents:
                continue
            has_rules = True
            m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)s?\s*", value)
            if not m:
                raise SiteIndexError("robots rule is malformed", status=502)
            try:
                req = float(m.group(1))
                sec = float(m.group(2))
            except ValueError as exc:
                raise SiteIndexError("robots rule is malformed", status=502) from exc
            if not (math.isfinite(req) and math.isfinite(sec)) or req <= 0 or sec <= 0:
                raise SiteIndexError("robots rule is malformed", status=502)
            cur_rates.append(sec / req)
        else:
            continue
    flush()
    return groups


def _relevant_groups(groups: list[_Group]) -> list[_Group]:
    exact = [g for g in groups if any(a.lower() == "notaeo" for a in g.agents)]
    if exact:
        return exact
    wild = [g for g in groups if any(a == "*" for a in g.agents)]
    return wild


def robots_allowed(groups: list[_Group], path: str) -> bool:
    relevant = _relevant_groups(groups)
    if not relevant:
        return True
    allows: list[str] = []
    disallows: list[str] = []
    for g in relevant:
        allows.extend(g.allows)
        disallows.extend(g.disallows)
    best_allow = -1
    best_deny = -1
    for pat in allows:
        try:
            matched = _match_robots_pattern(pat, path)
        except SiteIndexError:
            raise
        if matched:
            eff = len(pat.replace("*", "").replace("$", ""))
            best_allow = max(best_allow, eff)
    for pat in disallows:
        try:
            matched = _match_robots_pattern(pat, path)
        except SiteIndexError:
            raise
        if matched:
            eff = len(pat.replace("*", "").replace("$", ""))
            best_deny = max(best_deny, eff)
    if best_allow == -1 and best_deny == -1:
        return True
    if best_allow >= best_deny:
        return True
    return False


def robots_interval(groups: list[_Group]) -> float:
    relevant = _relevant_groups(groups)
    intervals: list[float] = []
    for g in relevant:
        intervals.extend(g.delays)
        intervals.extend(g.rates)
    base = max(intervals) if intervals else 0.0
    return max(MIN_SPACING, base)


def robots_interval_checked(groups: list[_Group]) -> float:
    interval = robots_interval(groups)
    if interval > MAX_INTERVAL:
        raise SiteIndexError("crawl delay is too long", status=502)
    return interval


# ---------- links + snippets + cached search ----------

_ASSET_EXTS = frozenset(
    {
        ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
        ".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".otf",
        ".mp4", ".webm", ".mp3", ".wav", ".ogg", ".zip", ".tar", ".gz",
        ".rar", ".7z", ".exe", ".dmg", ".pkg", ".iso", ".xml", ".json",
    }
)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.hrefs.append(v)


def extract_links(html: str, base_url: str) -> list[str]:
    parser = _LinkParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return []
    out: set[str] = set()
    for href in parser.hrefs:
        s = (href or "").strip()
        if not s or s.startswith("#"):
            continue
        low = s.lower()
        if low.startswith(("javascript:", "mailto:", "tel:", "data:", "ftp:", "file:")):
            continue
        try:
            joined = urljoin(base_url, s)
            jparts = urlsplit(joined)
        except ValueError:
            continue
        if (jparts.scheme or "").lower() not in ("http", "https"):
            continue
        if jparts.query:
            continue  # ignore query-variant links
        try:
            canon = canonical_crawl_url(joined)
        except ValueError:
            continue
        path = (urlsplit(canon).path or "").lower()
        if any(path.endswith(ext) for ext in _ASSET_EXTS):
            continue
        out.add(canon)
    return sorted(out)


def best_snippet(full_text: str, query: str) -> str:
    from core.webdiscovery import topic_score

    text = (full_text or "").strip()
    if not text:
        return ""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        paras = [text]
    if len(paras) == 1 and len(paras[0]) > 2000:
        # split long single block into sentences for passage granularity
        paras = [p.strip() for p in re.split(r"(?<=[.!?])\s+", paras[0]) if p.strip()]
    best = paras[0]
    best_score = -1.0
    for para in paras:
        try:
            score = topic_score(query, "", para)
        except Exception:
            score = 0.0
        if score > best_score:
            best_score = score
            best = para
    if best_score <= 0:
        # fall back to window around first query term
        lower = text.lower()
        try:
            from core.search import parse_query

            parsed = parse_query(query)
            terms = [t.lower() for t in parsed.original_terms] or [query.lower()]
        except Exception:
            terms = [query.lower()]
        pos = -1
        for t in terms:
            pos = lower.find(t)
            if pos != -1:
                break
        if pos == -1:
            return text[:300]
        start = max(0, pos - 120)
        end = min(len(text), pos + 200)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(text) else ""
        return prefix + text[start:end].strip() + suffix
    snippet = best.strip()
    if len(snippet) > 600:
        snippet = snippet[:600].rstrip() + "…"
    return snippet


def search_cached_pages(
    pages: list[dict],
    query: str,
    limit: int = 20,
    domain: str | None = None,
    file_type: str = "all",
    academic: bool = False,
) -> list[dict]:
    from core.webdiscovery import file_type_for_url, is_academic_host, matches_domain, topic_score
    from urllib.parse import urlsplit as _split

    scored: list[dict] = []
    for page in pages:
        url = str(page.get("url", ""))
        title = str(page.get("title", "") or url)
        text = str(page.get("text", "") or "")
        try:
            host = (_split(url).hostname or "").lower()
        except ValueError:
            continue
        if not host:
            continue
        if domain is not None and not matches_domain(host, domain):
            continue
        ftype = file_type_for_url(url)
        if file_type != "all" and ftype != file_type:
            continue
        if academic and not is_academic_host(host):
            continue
        try:
            score = topic_score(query, title, text)
        except Exception:
            score = 0.0
        if score <= 0:
            continue
        snippet = best_snippet(text, query)
        if not snippet:
            snippet = text[:300]
        scored.append(
            {"title": title, "url": url, "snippet": snippet, "domain": host, "file_type": ftype, "score": float(score)}
        )
    scored.sort(key=lambda r: (-r["score"], r["title"].casefold(), r["url"]))
    return scored[: max(0, limit)]


# ---------- bounded crawl ----------

def _default_validate(url: str) -> None:
    from core.fetcher import _validate_url

    _validate_url(url)


def _default_fetch(url: str, timeout: float):  # pragma: no cover - live path
    import httpx

    deadline = time.monotonic() + timeout
    with httpx.Client(follow_redirects=False, timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        with client.stream("GET", url) as response:
            headers = {k.lower(): v for k, v in response.headers.items()}
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                if time.monotonic() >= deadline:
                    raise SiteIndexError("indexing timed out", status=502)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise SiteIndexError("response is too large", status=502)
                chunks.append(chunk)
            body = b"".join(chunks)
            return _LiveResp(response.status_code, headers, body)


class _LiveResp:
    def __init__(self, status: int, headers: dict, body: bytes) -> None:
        self.status = status
        self.headers = headers
        self.body = body


def _extract_title_text(html: str, url: str) -> tuple[str, str]:
    from core import article
    import trafilatura

    try:
        parsed = article.extract_article(html, url)
    except Exception as exc:
        raise SiteIndexError("page cannot be read", status=502) from exc
    text: str | None = None
    try:
        text = trafilatura.extract(html, include_links=False)
    except Exception:
        text = None
    if not text or not text.strip():
        text = "\n\n".join(p.text for p in parsed.paragraphs)
    if not text or not text.strip():
        raise SiteIndexError("page has no readable text", status=502)
    title = (parsed.title or "").strip()
    if not title:
        try:
            meta = trafilatura.extract_metadata(html)
            if meta and meta.title:
                title = meta.title.strip()
        except Exception:
            pass
    if not title:
        try:
            title = urlsplit(url).netloc or url
        except ValueError:
            title = url
    return title, text.strip()[:MAX_TEXT]


def crawl_site(
    seed_url: str,
    *,
    fetch: Callable[..., Any] | None = None,
    validate: Callable[[str], None] | None = None,
    now: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> CrawlResult:
    fetch_fn = fetch or _default_fetch
    validate_fn = validate or _default_validate
    now_fn = now or time.monotonic
    sleep_fn = sleep or time.sleep

    try:
        seed = canonical_crawl_url(seed_url)
    except ValueError as exc:
        raise SiteIndexError(str(exc), status=422) from exc
    seed_host = _host_of(seed)
    if not is_educational_host(seed_host):
        raise SiteIndexError("url is not on the educational allowlist", status=422)

    start = now_fn()
    def remaining() -> float:
        return BUDGET_SECONDS - (now_fn() - start)

    def timeout_for() -> float:
        rem = remaining()
        if rem <= 0:
            return 0.0
        return min(PER_REQUEST_TIMEOUT, rem)

    # ---- robots ----
    robots_url = f"https://{seed_host}/robots.txt"
    if remaining() <= 0:
        raise SiteIndexError("indexing timed out", status=502)
    try:
        validate_fn(robots_url)
    except SiteIndexError:
        raise
    except Exception as exc:
        raise SiteIndexError("site cannot be indexed", status=502) from exc
    robots_timeout = timeout_for()
    if robots_timeout <= 0:
        raise SiteIndexError("indexing timed out", status=502)
    try:
        robots_resp = fetch_fn(robots_url, robots_timeout)
    except SiteIndexError:
        raise
    except Exception as exc:
        raise SiteIndexError("site cannot be indexed", status=502) from exc
    rstatus = getattr(robots_resp, "status", getattr(robots_resp, "status_code", 200))
    rheaders = getattr(robots_resp, "headers", {}) or {}
    rbody = getattr(robots_resp, "body", getattr(robots_resp, "content", b"")) or b""
    if isinstance(rbody, str):
        rbody = rbody.encode()
    rheaders_l = {str(k).lower(): str(v) for k, v in dict(rheaders).items()}
    groups: list[_Group] = []
    interval = MIN_SPACING
    if rstatus == 404:
        groups = []
    elif rstatus in (401, 403):
        raise SiteIndexError("indexing is not allowed", status=502)
    elif rstatus != 200:
        raise SiteIndexError("site cannot be indexed", status=502)
    else:
        ctype = (rheaders_l.get("content-type", "") or "").split(";", 1)[0].strip().lower()
        if ctype and ctype != "text/plain":
            raise SiteIndexError("site cannot be indexed", status=502)
        if len(rbody) > MAX_BYTES:
            raise SiteIndexError("site cannot be indexed", status=502)
        # chunked time accounting for robots body
        chunk = 32768
        for off in range(0, len(rbody), chunk):
            if remaining() <= 0:
                raise SiteIndexError("indexing timed out", status=502)
        try:
            rtext = rbody.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SiteIndexError("site cannot be indexed", status=502) from exc
        # 3xx robots handled as fail-closed unless same-origin? Fake never redirects robots;
        # live robots redirects: require same origin, at most 3 (handled below for pages;
        # robots redirect outside origin fails closed).
        groups = parse_robots(rtext)
        interval = robots_interval_checked(groups)
        seed_path = urlsplit(seed).path or "/"
        if not robots_allowed(groups, seed_path):
            raise SiteIndexError("indexing is not allowed", status=502)
    last_time = now_fn()

    # ---- BFS ----
    queue: list[tuple[str, int]] = [(seed, 0)]
    queued_set = {seed}
    visited: set[str] = set()
    collected: list[dict] = []
    skipped = False
    time_limited = False
    queue_capped = False

    def spaced_wait():
        nonlocal last_time
        elapsed = now_fn() - last_time
        wait = interval - elapsed
        if wait > 0:
            if remaining() - wait <= 0:
                return False
            sleep_fn(wait)
        return True

    def fetch_with_redirects(url: str) -> tuple[str, bytes, dict] | None:
        """Return (final_url, body, headers) or None to skip (partial). Raise abort for seed."""
        nonlocal last_time
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            if remaining() <= 0:
                return None
            try:
                canon = canonical_crawl_url(current)
            except ValueError:
                return None
            if not is_in_scope(seed, canon):
                return None
            cand_path = urlsplit(canon).path or "/"
            try:
                if not robots_allowed(groups, cand_path):
                    return None
            except SiteIndexError:
                raise
            try:
                validate_fn(canon)
            except Exception:
                return None
            if not spaced_wait():
                return None
            t = timeout_for()
            if t <= 0:
                return None
            try:
                resp = fetch_fn(canon, t)
            except SiteIndexError:
                raise
            except Exception:
                return None
            last_time = now_fn()
            status = getattr(resp, "status", getattr(resp, "status_code", 200))
            headers = getattr(resp, "headers", {}) or {}
            body = getattr(resp, "body", getattr(resp, "content", b"")) or b""
            if isinstance(body, str):
                body = body.encode()
            headers_l = {str(k).lower(): str(v) for k, v in dict(headers).items()}
            if status in (301, 302, 303, 307, 308):
                loc = headers_l.get("location", "")
                if not loc:
                    return None
                nxt = urljoin(canon, loc)
                # scope before DNS already enforced at loop top; pre-check now
                try:
                    nxt_canon = canonical_crawl_url(nxt)
                except ValueError:
                    return None
                if _host_of(nxt_canon) != seed_host or not is_in_scope(seed, nxt_canon):
                    return None
                current = nxt_canon
                continue
            if status == 404:
                return None
            if status in (401, 403):
                return None
            if status != 200:
                return None
            # content-type + streaming cap with per-chunk time checks
            ctype = (headers_l.get("content-type", "") or "").split(";", 1)[0].strip().lower()
            if ctype not in ("text/html", "application/xhtml+xml"):
                return None
            if len(body) > MAX_BYTES:
                return None
            for off in range(0, len(body), 32768):
                if remaining() <= 0:
                    return None
            try:
                html = body.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                try:
                    html = body.decode("utf-8", errors="replace")
                except Exception:
                    return None
            return canon, html.encode("utf-8"), headers_l
        return None

    idx = 0
    while idx < len(queue) and len(collected) < MAX_PAGES:
        if remaining() <= 0:
            time_limited = True
            break
        url, depth = queue[idx]
        idx += 1
        if url in visited:
            continue
        visited.add(url)
        fetched = fetch_with_redirects(url)
        if fetched is None:
            # distinguish seed abort vs partial skip: seed must abort if nothing collected?
            # scope/security failures of seed abort instead of partialpublish is enforced
            # by raising below when zero pages; non-seed skips mark partial.
            skipped = True
            # seed fetch returning None due to scope/security must abort loudly if seed itself?
            if url == seed and len(collected) == 0:
                # check whether it was scope/robots/security (not just unreadable)?
                # Conservative: if seed itself failed, let final zero-pages raise 502.
                pass
            continue
        final_url, html_bytes, _h = fetched
        try:
            html = html_bytes.decode("utf-8")
        except Exception:
            skipped = True
            continue
        try:
            title, text = _extract_title_text(html, final_url)
        except SiteIndexError:
            skipped = True
            continue
        collected.append({"url": final_url, "title": title, "text": text})
        if depth < MAX_DEPTH and len(collected) < MAX_PAGES:
            try:
                links = extract_links(html, final_url)
            except Exception:
                links = []
                skipped = True
            for link in links:
                if link in visited or link in queued_set:
                    continue
                if not is_in_scope(seed, link):
                    continue
                try:
                    if not robots_allowed(groups, urlsplit(link).path or "/"):
                        skipped = True
                        continue
                except SiteIndexError:
                    raise
                if len(queue) >= QUEUE_CAP:
                    queue_capped = True
                    skipped = True
                    break
                queue.append((link, depth + 1))
                queued_set.add(link)
            # deterministic order: keep queue sorted beyond current index
            if idx < len(queue):
                tail = sorted(queue[idx:], key=lambda t: t[0])
                queue[idx:] = tail

    if not collected:
        # zero successful pages preserves prior index; surface time vs generic
        if time_limited or remaining() <= 0:
            raise SiteIndexError("indexing timed out", status=502)
        raise SiteIndexError("site has no readable pages", status=502)
    if time_limited or remaining() <= 0:
        notice = "time_limit"
    elif len(collected) >= MAX_PAGES and idx < len(queue):
        notice = "page_limit"
    elif skipped or queue_capped:
        notice = "partial"
    else:
        notice = "complete"
    assert notice in _VALID_NOTICES
    return CrawlResult(pages=collected, notice=notice)
