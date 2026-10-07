"""Native web discovery: metasearch plus Notaeo ranking.

Public-web research experience without provider keys or caching.
Uses existing DDGS public-web adapter with bounded retrieval.
"""
from __future__ import annotations

import ipaddress
import re
import time
from collections import Counter
from urllib.parse import parse_qsl, urlencode, urlsplit, unquote, urlunsplit

from ddgs import DDGS

from core.search import EmptyQuery, parse_query, stemmed_words

ALLOWED_ENGINES = ("auto", "google", "duckduckgo", "brave", "mojeek")
ALLOWED_FILE_TYPES = ("all", "pdf", "html")
RECENCY_TO_TIMELIMIT: dict[str, str | None] = {
    "any": None,
    "day": "d",
    "week": "w",
    "month": "m",
    "year": "y",
}
ALLOWED_REGIONS = ("us-en", "ca-en", "uk-en", "au-en")

ACADEMIC_HOSTS = (
    "arxiv.org",
    "ncbi.nlm.nih.gov",
    "openstax.org",
    "khanacademy.org",
    "ocw.mit.edu",
    "coursera.org",
)

_OPERATOR_RE = re.compile(r"(?i)\b(?:site|filetype):\S+")
_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class WebDiscoveryError(Exception):
    pass


def normalize_domain(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("domain must be a bare host")
    stripped = raw.strip()
    if not stripped:
        raise ValueError("domain must be a bare host")
    if any(ch.isspace() for ch in stripped):
        raise ValueError("domain must be a bare host")
    # Explicitly reject characters that never appear in a bare host.
    for bad in ('/', '?', '#', '@', ':', '"', "'", "(", ")", "<", ">", "[", "]"):
        if bad in stripped:
            raise ValueError("domain must be a bare host")
    lowered = stripped.lower().rstrip(".")
    if not lowered or "." not in lowered:
        raise ValueError("domain must be a bare host")
    if lowered == "localhost":
        raise ValueError("domain must be a bare host")
    try:
        ipaddress.ip_address(lowered)
    except ValueError:
        pass
    else:
        raise ValueError("domain must be a bare host")
    try:
        ascii_host = lowered.encode("idna").decode("ascii")
    except (UnicodeError, ValueError) as exc:
        raise ValueError("domain must be a bare host") from exc
    if len(ascii_host) > 253:
        raise ValueError("domain must be a bare host")
    labels = ascii_host.split(".")
    for label in labels:
        if not label or len(label) > 63 or not _LABEL_RE.match(label):
            raise ValueError("domain must be a bare host")
    if labels[-1].isdigit():
        raise ValueError("domain must be a bare host")
    return ascii_host


def matches_domain(host: str, domain_filter: str) -> bool:
    h = (host or "").lower()
    d = (domain_filter or "").lower()
    return h == d or h.endswith("." + d)


def is_academic_host(host: str) -> bool:
    h = (host or "").lower()
    if h.endswith(".edu") or h == "edu":
        return True
    if h.endswith(".ac.uk") or h == "ac.uk":
        return True
    for allowed in ACADEMIC_HOSTS:
        if h == allowed or h.endswith("." + allowed):
            return True
    return False


def file_type_for_url(url: str) -> str:
    try:
        path = urlsplit(url).path or ""
    except ValueError:
        path = ""
    try:
        decoded = unquote(path)
    except Exception:
        decoded = path
    if decoded.lower().endswith(".pdf"):
        return "pdf"
    return "html"


def _tracking_name(name: str) -> bool:
    n = name.lower()
    return n.startswith("utm_") or n in ("gclid", "fbclid")


def canonical_key(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return url.strip().lower()
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        ascii_host = host
    try:
        port = parts.port
    except ValueError:
        port = None
    host_part = ascii_host if port is None else f"{ascii_host}:{port}"
    try:
        raw_path = parts.path or "/"
        path = raw_path
    except Exception:
        path = parts.path or "/"
    try:
        pairs = parse_qsl(parts.query, keep_blank_values=True)
    except ValueError:
        pairs = []
    kept = [(k, v) for k, v in pairs if not _tracking_name(k)]
    kept.sort()
    q = urlencode(kept, doseq=True)
    return f"{host_part}{path}?{q}" if q else f"{host_part}{path}"


def deduplicate_results(scored: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in scored:
        key = row.get("canon") or canonical_key(row.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def strip_operators(query: str) -> str:
    return _OPERATOR_RE.sub(" ", query).strip()


def topic_score(query: str, title: str, snippet: str) -> float:
    topic_q = strip_operators(query or "")
    try:
        parsed = parse_query(topic_q)
    except EmptyQuery:
        return 0.0
    if not parsed.terms and not parsed.phrases:
        return 0.0
    uniq = list(dict.fromkeys(parsed.terms))
    n = len(uniq)
    title_counts = Counter(stemmed_words(title or ""))
    snippet_counts = Counter(stemmed_words(snippet or ""))
    matched = 0
    title_matched = 0
    total = 0.0
    for term in uniq:
        t_tf = title_counts.get(term, 0)
        s_tf = snippet_counts.get(term, 0)
        if t_tf + s_tf > 0:
            matched += 1
        if t_tf > 0:
            title_matched += 1
        total += 3 * t_tf / (t_tf + 1) + s_tf / (s_tf + 1) if (t_tf or s_tf) else 0.0
    coverage = (matched / n) if n else 0.0
    title_coverage = (title_matched / n) if n else 0.0
    combined = f"{(title or '').lower()} {(snippet or '').lower()}"
    phrase_hits = sum(1 for p in parsed.phrases if p and p in combined)
    if matched == 0 and phrase_hits == 0:
        return 0.0
    return 4 * coverage + 2 * title_coverage + total + 3 * phrase_hits


def build_effective_query(query: str, domain: str | None, file_type: str, academic: bool) -> str:
    parts = [query]
    if domain:
        parts.append(f"site:{domain}")
    if file_type == "pdf":
        parts.append("filetype:pdf")
    elif file_type == "html":
        parts.append("-filetype:pdf")
    if academic:
        group = (
            "(site:edu OR site:ac.uk OR site:arxiv.org OR site:ncbi.nlm.nih.gov "
            "OR site:openstax.org OR site:khanacademy.org OR site:ocw.mit.edu "
            "OR site:coursera.org)"
        )
        parts.append(group)
    return " ".join(parts)


def _canonicalize_url(raw: str) -> tuple[str, str, str, str] | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        parts = urlsplit(s)
    except ValueError:
        return None
    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https"):
        return None
    netloc = parts.netloc or ""
    if "@" in netloc:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return None
    if host == "localhost":
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return None
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        return None
    if "." not in ascii_host or len(ascii_host) > 253:
        return None
    for label in ascii_host.split("."):
        if not label or len(label) > 63 or not _LABEL_RE.match(label):
            return None
    if ascii_host.split(".")[-1].isdigit():
        return None
    try:
        port = parts.port
    except ValueError:
        return None
    if port is not None and not (1 <= port <= 65535):
        return None
    host_port = ascii_host if port is None else f"{ascii_host}:{port}"
    path = parts.path or ""
    try:
        pairs = parse_qsl(parts.query, keep_blank_values=True)
    except ValueError:
        return None
    kept = [(k, v) for k, v in pairs if not _tracking_name(k)]
    kept.sort()
    q = urlencode(kept, doseq=True)
    canonical_url = f"{scheme}://{host_port}{path}"
    if q:
        canonical_url += f"?{q}"
    ftype = file_type_for_url(canonical_url)
    key = canonical_key(canonical_url)
    return canonical_url, ascii_host, ftype, key


def discover(
    query: str,
    limit: int = 20,
    engine: str = "auto",
    domain: str | None = None,
    file_type: str = "all",
    academic: bool = False,
    recency: str = "any",
    region: str = "us-en",
) -> dict:
    if not isinstance(query, str):
        raise ValueError("q must be 1..500 characters")
    trimmed = query.strip()
    if not trimmed or len(trimmed) > 500:
        raise ValueError("q must be 1..500 characters")
    if not isinstance(limit, int) or not (1 <= limit <= 30):
        raise ValueError("limit must be 1..30")
    if engine not in ALLOWED_ENGINES:
        raise ValueError("engine must be one of auto/google/duckduckgo/brave/mojeek")
    domain_norm: str | None = None
    if domain is not None:
        if not isinstance(domain, str):
            raise ValueError("domain must be a bare host")
        # Empty string is invalid when explicitly supplied.
        if not domain.strip():
            raise ValueError("domain must be a bare host")
        domain_norm = normalize_domain(domain)
    if file_type not in ALLOWED_FILE_TYPES:
        raise ValueError("file_type must be one of all/pdf/html")
    if not isinstance(academic, bool):
        raise ValueError("academic must be a boolean")
    if recency not in RECENCY_TO_TIMELIMIT:
        raise ValueError("recency must be one of any/day/week/month/year")
    if region not in ALLOWED_REGIONS:
        raise ValueError("region must be one of us-en/ca-en/uk-en/au-en")

    try:
        topic = parse_query(strip_operators(trimmed))
    except EmptyQuery as exc:
        raise ValueError("enter a topic as well as search filters") from exc
    if not topic.terms and not topic.phrases:
        raise ValueError("enter a topic as well as search filters")
    effective = build_effective_query(trimmed, domain_norm, file_type, academic)

    if engine != "auto":
        try:
            from ddgs.engines import ENGINES as _ENGINES
        except Exception as exc:
            raise WebDiscoveryError("web search is temporarily unavailable") from exc
        if engine not in _ENGINES.get("text", {}):
            raise WebDiscoveryError("web search is temporarily unavailable")

    candidate_limit = min(50, max(40, limit * 2))
    timelimit = RECENCY_TO_TIMELIMIT[recency]
    backend = "auto" if engine == "auto" else engine

    start = time.monotonic()
    try:
        rows = DDGS(timeout=8).text(
            effective,
            max_results=candidate_limit,
            safesearch="moderate",
            backend=backend,
            region=region,
            timelimit=timelimit,
        )
    except Exception as exc:
        raise WebDiscoveryError("web search is temporarily unavailable") from exc

    scored: list[dict] = []
    for row in rows or []:
        href = row.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        raw_title = row.get("title")
        title = raw_title.strip() if isinstance(raw_title, str) else ""
        snippet = str(row.get("body") or "").strip()
        if not title:
            title = href.strip()
        canon = _canonicalize_url(href)
        if canon is None:
            continue
        canonical_url, host, ftype, key = canon
        if domain_norm is not None and not matches_domain(host, domain_norm):
            continue
        if file_type != "all" and ftype != file_type:
            continue
        if academic and not is_academic_host(host):
            continue
        score = topic_score(trimmed, title, snippet)
        if score <= 0:
            continue
        scored.append(
            {
                "title": title,
                "url": canonical_url,
                "snippet": snippet,
                "domain": host,
                "file_type": ftype,
                "score": float(score),
                "canon": key,
            }
        )

    scored.sort(key=lambda r: (-r["score"], r["title"].casefold(), r["url"]))
    seen: set[str] = set()
    results: list[dict] = []
    for row in scored:
        if row["canon"] in seen:
            continue
        seen.add(row["canon"])
        results.append(
            {
                "title": row["title"],
                "url": row["url"],
                "snippet": row["snippet"],
                "domain": row["domain"],
                "file_type": row["file_type"],
                "score": row["score"],
            }
        )
        if len(results) >= limit:
            break

    took_ms = int((time.monotonic() - start) * 1000)
    return {
        "query": trimmed,
        "effective_query": effective,
        "engine": engine,
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
