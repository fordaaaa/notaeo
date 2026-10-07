# Native web discovery

Spec approved by independent OpenCode review, 2026-10-07.

Build Notaeo's own public-web research experience: query external indexes,
apply transparent filters and deterministic ranking, then import useful material
into an authenticated notebook. This is metasearch plus Notaeo ranking; a
whole-web index remains future work. Selected educational-site crawling and
offline search extend this contract; see `EDUCATIONAL_INDEX.md`.

## Backend contract

Keep GET /api/web/search?q=&limit= compatible (list of title/url/snippet).
Add GET /api/web/discover with q (trimmed 1..500), limit (default20,1..30),
engine (auto/google/duckduckgo/brave/mojeek), domain (optional bare host,
including IDNA; no scheme/path/credentials/ports/operators), file_type
(all/pdf/html), academic (boolean), recency (any/day/week/month/year), region
(us-en/ca-en/uk-en/au-en). Return typed query, effective_query, engine,
results[], took_ms, filters. Results have title/url/snippet/domain/file_type/
score; no fabricated publication dates, total web counts, verified quality or
provider attribution when engine=auto. No new dependency or provider key.

Existing DDGS handles explicit engine/region/safe-search/date hints. Selection
must never silently switch engines while reporting the requested engine. Use
bounded candidate retrieval (at most50) and timeout8; normalize results, exclude
non-http(s), credentials and malformed hosts/ports, strip tracking/fragments
for deduplication, enforce domain boundaries and file-type filters locally,
rank by meaningful topic overlap/coverage/title with repetition saturation and
stable ties. Domain-only queries must not confer topic relevance. Academic is
an educational-site scope (edu/ac.uk + clearly named public research/learning
sites such as arxiv.org, ncbi.nlm.nih.gov, openstax.org); explain this scope,
never equate a domain with trustworthy evidence. Reject whitespace-only queries
and invalid filters before network I/O. Engine errors use safe503 messages.
No cache, user query log, persistent search history, background crawl or implicit
network I/O. Search only runs when explicitly submitted. Existing public route
remains public; notebook import still requires account + ownership and uses
existing URL ingestion (including SSRF/duplicate protections).

Google adapter is the existing DDGS public-web adapter, not an official Google
API integration. Google Custom Search JSON API is closed to new customers and
ends January1,2027 for existing users; https://developers.google.com/custom-search/v1/overview .
DDGS supported engines/filters: https://github.com/deedy5/ddgs . Upstream
availability and date-hint support vary; do not invent dates or complete coverage.

## Exact semantics

`/api/web/discover` is public like existing discovery; native requests retain
per-launch and optional account headers. Validation is422 `{"detail":...}`;
external retrieval failure is503 `{"detail":"web search is temporarily unavailable"}`.
Response `engine` always means requested strategy: `auto` stays `auto` (label
Automatic); DDGS auto may aggregate/fall back, without asserting actual per-row
provenance. Explicit engines are single backend values with no app fallback. Validate
that a requested explicit engine exists in installed DDGS before calling it:
DDGS otherwise silently falls back to auto. Bing is not offered because the
installed version does not expose it.
`took_ms` is elapsed integer milliseconds; `DDGS(timeout=8)` is seconds (upstream
per-request timeouts, not a promise of an8second whole-operation deadline).

`filters` is domain nullable, file_type, academic, recency, region. Normalize
hosts with lowercase IDNA, trailing dot removal and strict DNS labels, no URL
components or private/reserved IPs/localhost. Domain accepts exact host or its
subdomains only; `evil-example.edu` never matches `example.edu`.
Link type is URL-path suffix `.pdf` (case-insensitive, percent-decoded), otherwise
html; this does not verify MIME. Native labels say PDF link/Web page. Academic
allowlist is `.edu`, `.ac.uk`, arxiv.org, ncbi.nlm.nih.gov, openstax.org,
khanacademy.org, ocw.mit.edu, coursera.org. Explain the educational-site scope in
both clients; domain membership is no endorsement. The backend adds structured
site/filetype operators to effective_query; academic adds an OR site group for
the allowlist; recency uses DDGS timelimit d/w/m/y, region uses DDGS region.
Local academic/domain/type checks still enforce filters if upstream ignores them.

Topic scoring uses original trimmed query with site:/filetype: tokens removed,
then existing parse_query/stemmed_words. Require at least one meaningful term or
phrase and at least one matching topic term/phrase. For unique query terms,
score=4*coverage + 2*title_coverage + sum(3*title_tf/(title_tf+1)
+ snippet_tf/(snippet_tf+1)) +3 per matched exact phrase; coverage fractions
use unique query term count (zero when none). Stable ties are title.casefold(),
canonical URL. Query filters and domains never become topic relevance. Deduplicate
by normalized host/path/query, ignore fragment and utm_*/gclid/fbclid parameters,
retain meaningful query args; sort before dedupe so best topical snippet wins.

Open in Google uses `https://www.google.com/search` with encoded q of original
submitted query plus validated site/domain and filetype:pdf (or -filetype:pdf
for html). Google link omits academic/recency/region and label/help says it opens
Google with query/site/type only. Accept search operators typed in q as normal
query text, but structured domain must be validated before building a link.
No automatic browser opens, tokens or provider credentials in links.

Mac tests/build run here. Portable Windows tests/Release/cross-publish run on
macOS using `/private/tmp/notaeo-dotnet-sdk/dotnet`. Final independent approval
and green checks gate commits; physical Windows UI/DPAPI/packaged-sidecar checks
are documented manual limitations, not claimed passing runtime checks.

## Native macOS and Windows

Add Discover beside existing course Search; retain local Search and Ctrl/Cmd+F.
A query field/submit and native filters expose engine, site, pages/PDF, academic,
recent period and region. Display result title, domain, readable snippet, actual
file type, a result count (returned count only), open website and import action.
No notebook selected: explain course selection needed; architecture may retain
notebook requirement as existing native workspace does. Import one chosen HTTPS web article
only, show pending/success/error/duplicate, offer Open source after import. Never
force duplicate import. Use current native URL-import API and source callbacks.
A deliberate Open in Google action opens HTTPS www.google.com/search with the
encoded submitted query and site/file-type filters, even if DDGS fails; no account
or desktop tokens in URLs. Google may require its own normal browser interaction. Existing URL ingestion
accepts HTTPS HTML articles only. PDF links offer Open/download plus a clear
"Download the PDF, then upload it in Sources" instruction; HTTP-only links offer
Open website and explain the HTTPS requirement. Do not promise direct PDF import.

Loading uses existing thinking orbs and a visible Cancel. Empty/error/retry are
explicit. Cancellation/notebook/account/navigation/disposal must invalidate late
results, imports' UI updates, browser/export actions, and spinners. Never open
websites automatically or crawl on tab activation/filter changes. Keyboard and
screen-reader names use native controls. macOS style/motion match existing app;
Windows obeys existing app/OS reduced motion control. Native runtime limitations
remain honestly documented.

## Delivery and ownership

OpenCode independently reviews this spec first. Backend worker owns new
core/webdiscovery.py, core/models.py additions, api/web.py addition and backend
tests. Separate macOS worker owns new discovery DTO/service/controller/view/API
tests and additive APIClient/Models changes; separate Windows worker owns new
DTO/API/controller/panel/tests and additive ApiClient/Models changes. Root owns
project file membership, MainView/MainForm wiring, source-opening integration,
docs and full verification. Workers never commit. Meaningful tests red first,
targeted green then full required checks. Root independently reviews final code,
fixes blockers, then conventional single-line commits per logical feature.
Run backend full pytest, macOS native tests and signed build, Windows portable
suite/Release/publish. No frontend edits, migrations, paid infrastructure or
private research-server changes. Windows runtime requires later Windows checks.
