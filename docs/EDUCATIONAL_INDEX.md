# Selected educational-site index

Spec approved by independent OpenCode review, 2026-10-07.

Owner addition, 2026-10-07: also maintain our own index of selected educational
sites. Extend native Discover with Indexed sites search, and provide a Site index
screen to add starting URLs, explicitly refresh, show page counts/last-indexed
status, and remove sites. Search is local/offline over account-owned cached
article text. Import still fetches the chosen live article using existing URL
ingestion; snippets remain available offline. No background crawler or paid key.

## Scope and safety

Only HTTPS public URLs on the educational allowlist from WEB_DISCOVERY.md.
Keep crawl on the exact starting origin; starting path scopes descendants (a
seed ending .html permits its containing directory). Ignore querystrings for
crawl identity and fragment-only/non-http links. Reject credentials, ports
other than 443, localhost/private/reserved IPs; reuse fetcher DNS validation on
every request/redirect. Never follow redirects outside the seed origin/path.
Read origin /robots.txt first. 404 means absent; 403/401 denies; all other error/
unreachable/malformed or oversized robots fails closed. Honor Notaeo agent
Disallow, Crawl-delay and Request-rate; refuse waits over 5 seconds rather than
ignore rules. No sitemap traversal, robots bypass, proxy/evasion or asset crawl.
Fetch HTML only, 2 MiB maximum decompressed bytes per response, max 5 pages total
per refresh, depth 2, max 20 sites per user, 20 second refresh scheduling/stream-reading budget,
per-request timeout <= 5 seconds / remaining budget (DNS/OS resolution may overrun), at least 1 second between requests.
Cap stored article text to 50k characters. Extract via existing trafilatura/article
helpers and built-in HTMLParser for links. Canonical queue deterministic; no
unbounded linked lists. Failed refresh keeps previous data; partial successful
refresh may replace it only with explicit partial notice. Report limit/skip
notice honestly. Refresh HTTP work is synchronous and bounded, cancellation
of native waiting invalidates UI; it does not promise aborting server work.

## Storage and API

SQLite app.db schema adds web_index_sites(id,user_id,url,created_at,indexed_at,
revision,notice) and web_index_pages(site_id,user_id,url,title,text,indexed_at).
Every row has owner; pages use composite site_id/user_id foreign key plus cascade.
All writes/reads through Store, atomic replacement after crawl, optimistic
revision compare so concurrent refresh/add/delete cannot resurrect or overwrite
newer refresh. User+url unique; no queries/history/providerkeys stored.
GET /api/web/index/sites (auth) returns [{id,url,created_at,indexed_at nullable,
page_count,notice,revision}]. POST same accepts {url} idempotent max 20 bound.
POST /api/web/index/sites/{id}/refresh (auth) updates or safe error; DELETE same
removes site/pages. Foreign/missing/malformed ID 404 before any network I/O.
Validation 422, fetch/robots error 502 with safe message; concurrent refresh 409.
No implicit I/O on adding/listing/removing/searching.

GET /api/web/discover adds engine=index. Authentication required for this engine
only (public engine paths stay compatible); supplied account header must be valid.
Read pages restricted to user id; reuse deterministic topic ranking/domain/type/
academic filters. Match cached full article passages, not only its leading snippet.
Return same WebDiscoveryPage/results contract; engine=index stays index, no DDGS
call. No provider dates fabricated: recency!=any rejected 422 (date hints apply
only to live web search). region is harmless retained filter metadata for index.
No network calls during indexed search. Empty index / no match returns honest empty.

## Exact crawl/storage rules

Sites PK=id, UNIQUE(id,user_id) and UNIQUE(user_id,url); pages PK(site_id,url),
FK(site_id,user_id) REFERENCES sites(id,user_id) ON DELETE CASCADE. Adding an
existing owner URL returns its site unchanged; cap 20 is checked in BEGIN IMMEDIATE.
Refresh claims site revision+1 under owner-scoped transaction before network;
replacement checks same owner/site/revision in BEGIN IMMEDIATE, else 409. Delete
removes row and cascades pages; refresh cannot recreate it. Failed crawls preserve
pages/indexed_at; claimed revision may increase even on failure. Replacements
commit only if >=1 page extracted. notice is complete, page_limit, time_limit,
or partial (safe generic enum/string; no underlying provider/DNS/HTML details).

Canonical crawl URL: normalized IDNA host/lower, default 443 removed, HTTPS,
remove query/fragment, normalized dot segments including percent-encoded dots,
reject encoded slash/backslash or control characters rather than expand scope.
Seed /book -> allowed prefix /book or /book/descendants; /book/ -> same prefix;
seed /book/chapter.html -> scope /book/ directory with exact seed included.
Origin exact scheme/host/defaultport, no subdomains. Scope checked before DNS
for queue and every redirect; redirected HTML must also pass robots for its
new path. robots.txt fetch may use origin /robots.txt outside seed path but no
cross-origin redirect. This implementation rejects any robots.txt redirect and
fails closed; HTML permits at most 3 redirects within the remaining time budget.

Robots custom matcher: merge case-insensitive exact Notaeo groups, otherwise
merge wildcard * groups; never use first-match-only RobotParser. Match Allow/
Disallow path from start, support wildcard * and terminal$, longest matching
pattern (excluding wildcard markers) wins; equal length Allow wins. Empty
Disallow means no restriction. Normalize percent escapes per RFC9309; reserved
characters remain encoded, unreserved decoded, non-ASCII percent encoded before
comparison. Invalid UTF8 or malformed directive values fail closed. Empty robots
valid=allow; no matching group=allow. Crawl-delay accepts finite nonnegative
seconds, Request-rate positive requests/positive seconds; conservative interval
max(1,delay,seconds/requests) across matched groups. If interval > 5 refuse crawl,
not ignore directive. References: https://www.rfc-editor.org/rfc/rfc9309.html .

All responses including robots streamed with 2 MiB decompressed cap and remaining
time checks per chunk; robots Content-Type text/plain only (missing permitted),
article Content-Type HTML/XHTML only. Robots first request counts scheduling
budget; subsequent requests spaced minimum interval, including redirects. BFS
starts depth0 seed; enqueue sorted normalized URLs throughdepth 2, queue cap 50,
ignore PDFs/assets/query variant links, no infinite queue from a huge page. A crawl
with zero successful pages is 502 and preserves prior index. If some pages succeed
and then limits/blocked/unreadable links occur, publish valid pages with honest
notice. Scope/security failures of seed or robots abort instead of partial publish.

## Native and verification

Both clients get index CRUD/refresh transport DTO tests and native management
screens. Direct user Refresh warns/labels up to 5 pages per pass. Native form
validates nonempty URL, API enforces educational / robots scope. Thinking orbs / cancel
cover waiting; course/account/tab/disposal invalidates late UI updates; import
and index are distinct. Never automatically start crawling on submit search or
filter changes. Indexed sites becomes an explicit engine in Discover. Screens
share current style/reduced motion, native accessibility and safe URL opens.

Tests first: ownership 404 / no egress, auth 401, user-isolated searches/deletes,
foreign composite FK, stable cached passage ranking, duplicate/cap/optimistic
revision, robots deny / delay / error, scope/SSRF/redirect, byte / time / page / depth bounds,
preserve old data on failure. Core crawl uses injectable fake transport/clock for
meaningful deterministic tests (no public website required). Backend full pytest,
macOS tests / signed build, Windows portable tests / Release / publish, independent
OpenCode code approval before separate conventional feature commits. Existing
legacy web routes and notebooks unaffected. Update PRODUCT schema boundary for
new explicit local crawling; no private research-server work.
