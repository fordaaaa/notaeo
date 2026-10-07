# HANDOFF.md

Live state of the project. **Read this first** before doing anything.

> Status: branch `main`, hosted multi-user pivot landed (SQLite + email auth,
> per-user data). Installed macOS and Windows apps are the current priority
> (owner update 2026-10-07). The website/browser app is removed; the
> owner selected native controls throughout: SwiftUI and WinForms. A first
> native exam-coach alpha is implemented; additional feature screens still need
> porting. No frontend source or website assets are retained.
> Mobile lives
> in `research-mobile`; a bounded Settings/style pass was resumed on
> 2026-10-07, while desktop remains the priority.
> Owner direction: hosted backend (`research-server`) with thin clients, App
> Store later ($99 program budgeted then, not now). Login order: email (done)
> → Google (implemented, client-ID config pending) → Apple last.
> Owner vision (2026-09-29): Notion for students — academic tailoring plus a
> near-addictive sound/motion feel; see Next milestones.
> Shipped:
> `5e40a21 fix: authenticate notebook exports` (notebook .zip via Bearer
> fetch, server filename preserved, token kept out of the URL) and
> `5eef8ac fix: authenticate study exports` (cards TSV + mindmap exports,
> same guarantees). Both carry frontend tests (`api.export.test.ts`,
> `api.study-export.test.ts`); 401s clear the token and signal login.

## Website removal (2026-10-07)

- Owner explicitly requested complete website removal, including the local
  `research-server` checkout. Both React frontends and static-serving paths
  are removed; server Docker, CI and snapshot sync become backend-only.
- Installed apps keep accounts, sources, search, exports, study tools and
  optional AI. Launch authentication uses the native request header only;
  query-token/cookie exchange is removed. Browser docs UIs and development
  CORS origins are removed. Server OpenAPI JSON remains available for tooling.
- No live host has been redeployed and no data, keys or mobile development
  harness has been removed. Older sections below record historical frontend
  work; their browser file paths and build commands are no longer current.
- OpenCode workers implemented each repo independently after meaningful red
  tests: main removal 12 failed/4 passed; hosted removal 12 failed/1 passed.
  Root also removed the hosted admin HTML/JS/CSS while preserving protected
  statistics/user JSON APIs (4 failing regressions, then 9 admin tests passed).
  Final hosted review found weaker sidecar startup checks; 8 new failing
  regressions confirmed the gap before token/data-dir/bundle guards were fixed.
- Final verification: main backend **484 passed**; hosted backend **356 passed**;
  macOS XCTest **79 passed**; Windows portable suite **165 passed**; signed
  arm64 macOS package and self-contained win-x64 cross-publish passed. Counts
  for native suites exclude tests of removed, unused browser helpers.
- Hosted Docker build passed. A disposable container proved website and
  former admin assets return 404 while health, OpenAPI JSON, account login,
  paste ingestion, search, export and protected admin JSON work; the image has
  no frontend/web/.env. Its anonymous test volume and container were removed.
  The shipping C# client also passed the packaged-sidecar search/ownership
  probe. Both final patches received independent OpenCode APPROVE reviews.

## Mobile Settings quality pass (2026-10-07)

- Owner requested updating `research-mobile` alongside macOS. That separate
  private repo now has a visible Settings entry, warm paper/sage styling,
  account controls, sound, shared app/system reduced motion and a three-second
  local loading preview. Optional Gemini/OpenRouter/Groq settings use the same
  authenticated backend routes and preserve guest notebooks.
- Mobile verification: 116 unit tests, TypeScript, 12 iPhone/Pixel browser
  journeys and iOS/Android/web bundle export passed. Native device testing is
  still required; no public release, upload or private hosted backend changes.
  Details live in `research-mobile/docs/MOBILE_SETTINGS.md`.
- The subsequent owner request on 2026-10-07 explicitly removes the website
  completely, superseding the earlier download/help-site recommendation.

## Shared AI API entry point (2026-10-07)

- Backend features now import `core.api` for optional AI generation. It exports
  `generate`, `AIError`, `DEFAULT_MODELS` and `FALLBACK_MODELS`; the existing
  provider dispatcher and Gemini/OpenRouter/Groq adapters remain underneath.
  Dynamic forwarding preserves old imports, monkeypatches, retry behavior,
  fallback models and error identity. No endpoints, saved keys, provider IDs,
  dependencies or account boundaries changed.
- OpenCode independently approved the spec, implemented the facade/imports,
  and reviewed the final patch. Tests first: 9 failed due to missing facade;
  targeted 106 passed; full backend 466 passed. The signed arm64 macOS package
  was rebuilt with the shared entry point. No live AI request was required.
- New AI callers should import `from core import api as ai_api`; HTTP routes
  continue to live in the separate `backend/api/` package. `core/openrouter.py`
  is still the provider-specific transport, while `core/api.py` is the common
  entry point for all three supported providers.

## Native discovery and educational-site index (2026-10-07)

- macOS and Windows now have native Discover: submitted query, engine choice,
  site, page/PDF type, academic scope, recency and region. Notaeo ranks and
  deduplicates bounded live candidates with deterministic topic scores. The
  existing `/api/web/search` stays compatible; `/api/web/discover` returns
  typed filters/results. Live discovery needs no AI key. Google uses the
  existing DDGS adapter; the live Google check returned a safe 503, so direct
  retrieval is best effort. The deliberate Open in Google action remains
  available after search failure and sends only the submitted query/site/type.
- Both native apps have Site index: add an educational HTTPS starting URL,
  explicitly Refresh, inspect page count/status, remove. Adding/listing never
  crawls. Refresh honors robots, exact origin/path, DNS/private-address checks,
  redirects, two MiB streamed responses, five pages, depth two, a 50-entry queue
  and a 20-second scheduling/reading budget (DNS/OS resolution may overrun).
  Robots redirects fail closed. The cache supports at most 20 sites per user.
- Indexed sites in Discover searches owned cached article passages offline,
  with the same ranking/domain/type/academic filters. Recency is unavailable
  for this engine. Index tables are additive SQLite schema in app.db, with
  composite owner FK, cascade delete and claimed-revision atomic replacement.
  Failed refresh preserves prior pages; overlapping refresh/delete cannot
  resurrect or overwrite newer content. Runtime privacy metadata now lists
  explicit site refresh as a network action. No automatic crawl or AI request.
- Article Import uses existing authenticated HTTPS HTML ingestion, keeps
  duplicate protection, and offers Open source. PDF links explain download
  followed by Sources upload; HTTP links offer browser opening only. Indexed
  snippets work offline, while importing their live article still needs network.
  Loading uses current reduced-motion-aware orbs; cancellation stops native
  waiting and invalidates late updates, while a bounded server refresh may finish.
- OpenCode independently approved both specs, implemented the backend and
  native units, then reviewed final code. Root added regressions for encoded
  slash dedupe, operator-only queries, IDNA, account reset, Google error fallback,
  raw URL controls, slow stream deadlines and explicit egress metadata. Native
  final review caught the Google error action and account lifetime before fixes.
- Verification: full backend **457 passed**, full macOS XCTest **82 passed**,
  Windows portable suite **166 passed**; Windows Release **0 warnings/errors**,
  self-contained win-x64 cross-publish and signed arm64 macOS package passed.
  Actual shipping C# API client against a disposable packaged loopback sidecar
  verified cached full-text passages, filters, site add/list/delete, 204 cascade,
  account-isolated cache/listing, missing account 401 and foreign-owner 404.
  This probe made no public network requests. The deterministic crawler suite
  uses fake transport/clock; real-site access depends on robots and availability.
  Physical WinForms layout/accessibility, real DPAPI and Windows sidecar launch
  still require a Windows machine. No private research-server changes or deploy.
- Specs: `docs/WEB_DISCOVERY.md`, `docs/EDUCATIONAL_INDEX.md`. Next: manually try
  course-specific queries and small allowed site refreshes on the installed apps;
  expand index coverage/incremental crawling only after reviewing the limits.

## Windows study workspace parity (2026-10-06)

- Windows now includes native Search (Ctrl+F), source sorting/import dates,
  thinking orbs and Mind map. Search uses the existing paginated ranking API
  with phrases, related terms, source-type filters and full cited snippets.
  Source actions from Search and maps select Sources and scroll to the actual
  cited page, including chunk-only documents. Search survives tab changes;
  notebook/account changes cancel and clear pending content.
- Device-only sort and Reduce Motion choices live in `preferences.json`,
  separate from the DPAPI account file. Natural names, UTC date comparisons,
  invalid-date placement and stable ties match the macOS behavior. Orbs stop
  for either Windows or app reduced motion and when hidden/disposed. Native
  Settings provides a three-second local preview without an AI request.
- Mind map has a connected scrollable/zoomable graph, collapse/expand,
  native TreeView outline and keyboard source actions. All branches remain
  reachable. Authenticated Markdown export uses a sanitized server filename
  and prepares a temporary file before replacing the chosen destination.
- The existing backend already supplies search ranking, pagination and cited
  maps; this port adds no backend routes, migrations, providers or dependencies.
  Windows source/AI/account calls retain both authentication headers.
- OpenCode approved the spec, implemented transport, Search and map units;
  root integrated navigation, sorting, orbs and lifecycle corrections. Tests
  were red before implementation; root regressions caught pre-cancelled search,
  same-page reader offsets and a clipped single-source map before fixes.
- Verification: full portable Windows suite **109 passed**; Release build
  **0 warnings/errors**; self-contained `win-x64` publish succeeded. Independent
  OpenCode reviewers approved the final contracts/motion, Search/navigation and
  map corrections before feature commits. The signed arm64 macOS rebuild passed.
  The actual C# API client passed a disposable packaged-loopback check for
  search pagination, cited reader/map, Unicode export, missing auth 401 and
  foreign-owner 404.
  Actual WinForms layout/accessibility, OS animation settings, real DPAPI and
  Windows-packaged sidecar launch still require Windows runtime verification.

## Native study workspace features (2026-10-06)

- Thinking orbs replace the small loading dots in startup, optional AI,
  search and mind-map loading. Settings retains its three-second local AI
  loading preview. Either system or app Reduce Motion pauses the timeline
  and leaves static orbs; no sound was added.
- Sources remember the device's newest/oldest/name/file-type sort choice
  and show import dates. Timestamp comparisons use actual instants, including
  fractional seconds and offsets; invalid dates sort last. Names use natural
  ordering (Lecture 2 before Lecture 10), with stable ID tie breaks.
- Backend search adds BM25-style term-frequency saturation and chunk-length
  normalization while preserving exact AND, literal phrases, prefix fallback,
  related aliases/typos, filters, citations and deterministic pagination.
  The legacy scoring helper defaults remain compatible; no schema migration,
  service, AI key or dependency is needed.
- Native Mind map shows a connected notebook/source/concept graph with
  scroll, zoom, collapse/expand, a readable Outline alternative, refresh,
  source/page actions and authenticated Markdown export. Concepts are key
  terms extracted from imported material, not inferred semantic connections.
  The API retains `name`/`children` and adds typed stable IDs and source/page
  citations. A one-pass token index avoids double stemming and fabricated
  page references. Export headers use safe ASCII filenames while content
  preserves non-English course names.
- Verification: search ranking tests first 3 failed/5 passed, then 8 passed;
  root citation-stemming and Unicode-export regressions each failed before
  their fixes. New native sorting/orb/map API tests failed to compile before
  implementation. Full backend: 404 passed; native: 42 passed. The signed
  arm64 package builds. Actual Swift loopback calls verified recursive map
  citations against source-page text and authenticated Markdown export.
  Native preview inspection covered connected branches, sorting dates and
  a concept click opening its correct source reader. Physical trackpad zoom,
  large-course usability and the Save dialog's final file write remain manual
  checks. The Windows counterparts are now implemented; see the parity entry above.
- OpenCode implemented the ranking pass and the initial cited-map backend/UI;
  root completed map wiring, graph/zoom, cancellation, accessibility and export
  corrections. Independent OpenCode reviewers approved both the search diff
  and the final native/map diff before the separate feature commits.

## Native macOS course search and backend pagination (2026-10-06)

- Native Search tab and Cmd+F support queries, exact phrases, supported
  related terms, source-type filters, result counts and pagination. Results
  open the selected source at its cited page. Returning to Search retains
  results and query; changing notebooks clears them. Generation and task
  cancellation checks prevent stale results and loading state races.
- Backend adds typed `GET /api/notebooks/{id}/search/page`; the legacy list
  endpoint remains compatible. Both share the existing one-pass engine,
  filters, account ownership checks, timing and progress tracking. No new
  provider, key requirement, dependency or database migration.
- Verification: new backend tests first **8 failed, 1 passed**, then **9
  passed**; full backend **388 passed**. New native transport/state tests
  first failed to compile before implementation; full native suite **35
  passed**. The signed arm64 macOS package builds and verifies. The actual
  Swift client passed a real packaged-loopback check for pagination, related
  metadata, cited-source page lookup and out-of-range results with disposable
  data. Native Search layout was inspected. Full physical-keyboard/source
  navigation click-through remains a manual check.
- OpenCode implemented the backend and independently approved the combined
  feature after root integration. Typography/motion is committed separately
  as `97437ad`; this search batch is a separate feature commit. Windows search
  controls and the other remaining native feature screens still need porting.

## Native macOS typography and motion (2026-10-06)

- Added a shared native style: rounded San Francisco headings, larger body
  text, serif source reading, warm neutral surfaces and an adaptive teal
  accent. Sidebar, notebook header, sign-in and source reader have clearer
  spacing and hierarchy; import controls collapse without animating every page.
- Coach uses native cards, actual question/time-budget progress, gentle
  question/session/reference-answer transitions and explicit answer focus.
  Loading has a small staggered-dot capsule; Settings previews it locally.
  Both system and in-app Reduce Motion disable decorative movement; the
  timeline pauses and shows static dots. No audio added.
- OpenCode implemented the coach/Settings polish and independently reviewed
  the diff. Root integrated it and corrected animation scope, notice contrast,
  editor labels, auth field behavior, picker layout and question focus.
- A Debug-only XCTest host uses isolated preferences and in-memory account
  credentials and does not start the sidecar. This prevents tests from asking
  for the owner's real Keychain account. Release retains normal Keychain auth.
- Verification: meaningful motion-policy and test-host isolation checks first
  failed, then passed. Full macOS suite **31 passed**; arm64 native packaging
  and ad-hoc signature verification passed. A temporary SwiftUI host exercised
  the actual source/coach/Settings views against a disposable packaged API,
  including light/dark layout and animated/static loading preview. Full
  physical-keyboard revision navigation and provider inference remain manual
  checks. Backend, Windows and legacy frontend were not changed in this batch.
- App: `macos/build/Build/Products/Release/Notaeo.app`. Reviewed and approved
  for a separate feature commit; no release or deployment.

## Native desktop alpha (2026-10-05, uncommitted)

- macOS now uses SwiftUI for account login, notebooks, source reading/import,
  native ZIP export, exam goals, revision selection/resume, written answers,
  self-ratings, explanations and session history. Settings opens from the gear
  and app menu before login; includes appearance, reduced motion and a local
  AI-loading preview. Account credentials use Keychain.
- Windows has equivalent core WinForms screens, native settings and export.
  DPAPI protects account tokens. Expired sessions and delayed logout responses
  preserve newer logins. Process ownership, stale callbacks, upload limits and
  duplicate revision requests were reviewed and corrected after OpenCode work.
- Native packages call the API directly with a launch-token header plus account
  Bearer authentication. Browser docs/cookie exchange are disabled in native
  mode. Startup requires external data storage. A real loopback wire check
  verifies forwarded-IP headers cannot bypass native auth rate limits.
- Verification: backend **379 passed**; macOS **28 passed**; Windows portable
  suite **62 passed**. macOS package builds, verifies arm64 and its ad-hoc
  signature. Windows Release cross-build and self-contained win-x64 publish
  passed; the Windows Python bundle and real WinForms/DPAPI runtime still need
  Windows verification. Native Mac Settings and local loading preview were
  exercised via accessibility controls and inspected visually. The packaged
  sidecar passed auth/source/revision/history/explanation/export smoke checks
  with disposable data. Legacy frontend production build passed.
- The signed macOS app is at `macos/build/Build/Products/Release/Notaeo.app`.
  No commits, releases or deployments. Own mobile preview processes on 8002
  and 8082 were stopped; existing development servers were left running.
- Remaining native screens at this milestone: search, notes, chat, flashcard management, study
  artifacts, outlines, public-web discovery and Google login. Existing APIs
  and legacy React source remain. Full native revision click-through, physical
  keyboard shortcuts, provider inference and Windows layout need manual checks.

## Study/mobile batch shipped (2026-09-20)

- Flashcards v2 adds safe legacy SQLite migration, due-card queues, persisted
  again/hard/good/easy scheduling, editing, tags/filtering, source-grounded
  draft suggestions, and mobile swipe grading with accessible button/keyboard
  alternatives. Suggestions are deterministic, keyless, and save only after a
  user action.
- Keyless glossary and quiz endpoints/UI derive stable, source-cited entries
  and questions from notebook chunks. Glossary entries can open their source,
  be copied, or become a flashcard; quiz scoring stays in the UI session.
- Playwright now tests the app itself on iPhone/WebKit and Pixel/Chromium. Local
  runs start isolated FastAPI/Vite servers; remote runs use
  `RESEARCH_E2E_BASE_URL` and gate stateful tests behind explicit credentials or
  `RESEARCH_E2E_ALLOW_REGISTRATION=1`.
- Historical verification at that milestone: backend `195 passed`; frontend
  `93 passed`; production build, six local mobile E2E tests, and the signed
  arm64 app build passed.

## Web and macOS polish (2026-09-23)

- Thinking orbs use contrasting ink on deep-sea primary buttons. The web app
  and macOS shell share this frontend. The separate `research-mobile` app has
  its own `expo-thinking-orbs` integration and spinner fallback.
- The macOS shell uses a native save panel for WebKit downloads, has startup
  timeout/crash handling, an app icon, and an Xcode unit-test target. Local
  builds remain ad-hoc signed; notarization is not required.
- New Gemini settings use `gemini-3.5-flash-lite`; fallback models are
  `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite`. Saved user model choices
  remain unchanged. Session chat now includes matching saved skills.
- Verification for this batch: backend `214 passed`; frontend `107 passed`,
  build clean, lint warnings only, mobile browser E2E `6 passed`, Xcode unit
  tests pass, and `sh scripts/build_macos_app.sh` builds/signs the arm64 app.

## Notaeo, sounds, and auth hardening (2026-09-24 → 2026-09-27)

- **Notaeo rebrand + workspace remake** (`d6da355`, `a95ee63`, `dcdb327`,
  `4e7db2e`): the product name is Notaeo; workspace UI, sign-in, and student
  themes/typography redesigned. Source-to-essay workflow documented
  (`e604113`). macOS polish + first-run tour: `eb2d695`, `05e1a8d`.
- **Notes module** (`api/notes.py`): notebook markdown notes CRUD with
  validated source/chunk citations and optimistic concurrency — the seed of
  the Notion-style editor direction.
- **Cited passages + ingest/search upgrades**: the reader lifts cited
  passages (`core/keypassages.py`, `9ab49ed`); XHTML article ingest
  (`core/article.py`, `35a2b1d`); search ranks closer terms higher
  (`dd624a1`) and falls back to grouped prefix matches for single-token
  queries (`a3aa3a4`).
- **Onboarding progress**: `user_progress` table + `GET /api/me/progress`
  (`mark_progress` fires from add-source/search/export/review flows);
  `FolioLoader.tsx` staged boot animation; 4-item `Checklist.tsx` fed by
  server-or-local flags and playing `playSuccess` on completion.
  `GET /api/runtime` (`core/local_runtime.py`) advertises privacy-boundary
  facts.
- **Sound + press physics, default on** (`0510da2`, `25212d2`, `66cc326`):
  `src/sound.ts` synthesizes everything offline over one shared
  lazily-unlocked AudioContext — boot lift, success confirm, quiet tap tick,
  and a settings preview that deliberately bypasses the mute gate.
  `armTapSounds()` is one delegated document-level listener wired in
  `main.tsx`; `index.css` adds universal `:active` press physics
  (`scale(0.96)` + brightness) with `prefers-reduced-motion` collapse. One
  toggle in SettingsDialog (`notaeo:sound`); design doc
  `frontend/docs/LOADING_SOUND.md`.
- **Auth hardening** (`c42af08`): three-layer login rate limiting (verify-first
  per-key 10/5min, per-IP 60/5min, per-email 50/5min), 20/hour/IP register
  throttle, `purge_expired_sessions()`, uniform-404 cross-user oracle
  (sweep-tested), XFF ignored unless `RESEARCH_TRUST_XFF=1`.
- **Google OAuth implemented** (postdates the last test-count citation):
  `core/google_auth.py` id_token verification, `POST /api/auth/google` +
  status route, frontend wiring in `api.ts`. Configuration with a real client
  ID still pending.
- **Duplicate-source warning** (`8e9d02f`): ingest precheck returns
  `DuplicateRef`; add paths accept `force` to proceed. Duplicate register
  answers `200 {registered: false}` (anti-enumeration), not 409.
- Confirm deletes + dialog focus traps (`a162c84`), study-builder cleanup
  (`bf7f53a`).
- Hosted note: `research-server`'s backend snapshot was synced through this
  range (2026-09-29); the private overlay needed a `/api/ai/hosted/status`
  route-precedence fix and its tests adopted the new duplicate-register
  contract.

## Dashboard + calendar + Classroom batch (2026-09-30)

- **Home dashboard** replaces the file-picker-first home: greeting + due-card
  count + study streak (new `user_activity_days` table fed by review/source/
  note routes; math in `core/dashboard.py`), a 35-day month calendar
  (`CalendarMonth.tsx`, no deps) with class-colored assignment dots + card-due
  dots, classes/assignments CRUD (`api/classes.py`, user-scoped, notebook-
  linkable), recent notes/sources, and the notebook library as a section
  (`NotebookPicker variant="library"`: no hero/footer/main landmark).
- **Cross-notebook review**: `GET /api/me/review-queue` + `POST
  /api/me/cards/{id}/review` grade across every notebook; ReviewSession takes
  optional `gradeCard`/`notebookNames`; App hosts the queue in a dialog and
  bumps the dashboard on exit.
- **Google Classroom** (`api/classroom.py` + `core/classroom.py`): consent
  URL as JSON (browser hops can't carry the bearer), stateless HMAC state
  (`digest.user_id`), token exchange/refresh into a new `google_tokens` table,
  idempotent coursework sync into classes/assignments (`source=
  'google_classroom'`, keyed by external_id). Activates with
  `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` + `RESEARCH_PUBLIC_BASE_URL`
  and test-user access to the two classroom.readonly scopes.
- Verification: backend `295 passed`; frontend `500 passed` (218 files);
  `npm run build` clean. Note: the full frontend suite flakes ~1 random
  timer/announcement App test per run under local parallel load (passes in
  isolation; clean tree passed once) — worth watching in CI.

## Current state

- Branch `main`, remote `origin` = `https://github.com/fordaaaa/research`.
- **Practice/search quality and cozy sound (2026-10-05, uncommitted):**
  Basic coach sessions deduplicate repeated passages and prioritize missed
  topics, explicit focus topics, due cards, fresh material, then previously
  successful review. Missed flashcards use current edited content. Ungraded
  answers survive question navigation and grading another question while the
  panel stays mounted; self-rating persists them. Explanations expose rating
  controls immediately; navigation moves keyboard focus to the new heading.
  Source Search has an opt-in **Find related passages** mode with partial
  lexical coverage, scoped aliases and unambiguous one-edit typo correction;
  exact keyword search remains default and quoted phrases stay literal.
  Chat context shares the expansion groups. This is not embedding retrieval.
  Success now plays a quiet C4/E4 sine chime with a short fade (owner chose
  a pretty, cozy sound); opening and button cues are softer too. All browser
  test pages, including auth and previews, disable audio before navigation.
  The bridge gate passed. Two OpenCode coding jobs timed out after writing
  failing regression tests; the coordinator implemented and integrated the
  changes. Independent backend review approved. Frontend review found focus
  loss, reproduced and fixed; follow-up explicitly approved. Its proposed
  explanation/navigation race was ruled out with a deferred-response test:
  navigation is disabled while busy, and clears explanations afterwards.
  Final checks: backend **372 passed**; frontend **546 passed**, 232 files
  (`npm test -- --maxWorkers=2`); production build passed; lint exits 0 with
  React effect/organization warnings. **16 Chromium/WebKit browser checks
  passed**, using throwaway data and ports 8011/5181. Native arm64 sidecar,
  Xcode app build, ad-hoc signing and signature verification passed. Artifact:
  `macos/build/Build/Products/Release/Notaeo.app`.
  The packaged sidecar smoke passed desktop cookie exchange, account auth,
  related search, mixed source/card practice, finish, and edited-card follow-up
  with temporary data removed afterwards.
  See `docs/CODE_REVIEW_2026-10-05.md` and `docs/EXAM_COACH.md` for evidence
  and limits. Live provider inference/student evaluation remains pending.
  Owner-owned :8000/:5173 processes and the review.py whitespace edit remain
  preserved. No commits, app AI calls, hosted operations or native-subagent
  substitution were performed.
- **Exam-coach first loop (2026-10-02, uncommitted):** Home now says
  "Know what to study next" and opens a selected notebook's Exam coach.
  Goals/date/time/focus, proposed source/card practice, question selection and
  order, explicit start, written attempts, self-ratings, completion, and saved
  sessions are implemented. Latest missed topics lead the next session across
  the full completed history; the UI shows twenty recent sessions. A rare
  chosen topic on page 101 survives repetitive earlier material. Reference
  snippets now actually contain their glossary topic instead of always
  quoting the first sentence of a chunk. Optional AI generation validates
  source references and verbatim quotes; explanations require supporting
  quotes and valid citation numbers, falling back to basic content on errors.
  Request motion follows actual AI wait time; stale notebook requests abort
  and cannot replace the current plan. See `docs/EXAM_COACH.md`.
  Two OpenCode implementation jobs failed before producing code, and an
  initial small review timed out. The coordinator implemented this batch;
  subsequent independent OpenCode review found five issues, regression tests
  reproduced them, and all were fixed. Final follow-up: **approved, no
  concrete remaining blockers** in the inspected coach code. No native
  subagents were substituted. Quote/citation validation does not establish
  explanation factuality; live inference/student evaluation remains pending.
  Final suites: backend **345 passed**, frontend **536 passed** (228 files),
  **10 Chromium/WebKit browser journeys passed** with temporary data and
  ports 8011/5181. Lint exits 0 with React effect/organization warnings.
  `sh scripts/build_macos_app.sh` passed: production frontend, arm64 sidecar,
  Xcode app build, ad-hoc signature and deep/strict verification. Output:
  `macos/build/Build/Products/Release/Notaeo.app`.
  The packaged arm64 sidecar also passed a real API smoke flow with desktop
  cookie exchange, account auth, goal, practice, finish, and missed-topic
  follow-up using a throwaway data directory (removed afterwards).
  Working changes remain uncommitted; user-owned :8000/:5173 processes and
  the pre-existing review.py whitespace edit remain preserved.
- **Exam-coach direction + retrieval/free-provider groundwork (2026-10-02,
  uncommitted):** Owner selected explanations, practice, and a revision plan
  as the first student need. PRODUCT.md now prioritizes that loop; the first
  implementation is recorded above. Three OpenCode investigation workers plus independent
  product/code reviews informed `docs/NOTAEO_DIRECTION_DRAFT.md` (slogans,
  homepage draft, demo, milestones) and
  `docs/AI_RETRIEVAL_RESEARCH_2026-10-02.md` (observed search baseline and current
  provider sources).
  Both chat routes now select passages for the question using bounded lexical
  ranking. Distinct-topic representatives prevent a repetitive long source
  from evicting the other side of a comparison. No-query synthesis/outline
  behavior and strict keyword-search semantics are preserved; synonyms/typos
  and model answer quality still need evaluation.
  Groq is an optional per-user provider in Settings (default
  `openai/gpt-oss-20b`, same-provider `openai/gpt-oss-120b` fallback). Settings
  reload uses the supported-provider registry, avoiding incorrect Gemini
  dispatch. There is no bundled key or hosted allowance. Tests mock inference;
  no live AI answers were evaluated.
  Workers recorded failing tests before implementation; coordinator added and
  observed failing starvation and real API settings-reload regressions, then
  fixed them. Independent OpenCode final review approved.
  Verification: backend **325 passed**; frontend **527 passed** (225 files,
  `npm test -- --maxWorkers=2`); frontend build clean; lint exits 0 with existing
  warnings; **8 Chromium/WebKit E2E passed** on isolated ports 8011/5181 and
  temporary data (cleaned up). `sh scripts/build_macos_app.sh` passed and rebuilt
  the ad-hoc-signed arm64 Notaeo.app with the new backend and frontend.
  The existing dev backend on :8000 still exposes the old two-provider schema
  and needs a restart for Groq; it was preserved along with the Vite server and
  the pre-existing `backend/api/review.py` whitespace edit.
- **Review, optimization, and motion previews (2026-10-02, uncommitted):**
  OpenCode workers implemented single-pass search totals and flashcard gesture
  fixes; the coordinator integrated and reviewed the changes. Notebook opens
  fetch sources once, stale searches/chat operations are guarded, loading
  cadence survives rerenders, and thinking ink follows Night appearance.
  Settings → Motion → Try motion exercises loading, flashcard reveals, all
  nine thinking styles, and sample answer/error outcomes without provider
  requests or saved study progress. Real chat uses the shared thinking state
  until its request settles and animates arriving messages. Reduced motion
  remains supported. See `docs/CODE_REVIEW_2026-10-02.md` for scope/evidence.
  Verification: backend **298 passed**, frontend **523 passed** (224 files),
  frontend build and lint (warnings only), **10 Chromium/WebKit E2E passed**,
  and signed arm64 macOS app build passed. E2E selectors now match the current
  Notaeo auth, mobile library, and delete-confirm flows. The pre-existing
  whitespace edit in `backend/api/review.py` is preserved.
- **FX polish (2026-10-01):** WebAudio tones now fade in and out smoothly;
  saves/exports use a short rising pair, and finished review sessions use a
  quieter four-note rise. Review cards animate into place, the completion
  panel gets a brief glow, the upload dropzone responds while dragging, and
  calendar day changes and assignment checks get short transitions. The
  existing reduced-motion rule collapses these effects. This uses the current
  CSS/WebAudio stack with no added dependency.
- **Code organization (2026-10-01):** `frontend/src/api.ts` remains the stable
  import barrel over domain modules in `frontend/src/api/`, with contracts
  grouped under `frontend/src/api/types/`. Backend tests are grouped under
  `backend/tests/` by feature; the shared `conftest.py` stays at the root.
- **Owner direction (latest): hosted multi-user backend first.** Accounts are
  required on every data route; AI keys stay optional and per-user. License is
  MIT (matches fordaaaa/panoply). Google OAuth implemented (client-ID config
  pending); Apple at App Store time.
- Run the development API: `cd backend && uv run uvicorn api.main:app --reload --no-proxy-headers`; use native apps for the interface.
- Tests: `cd backend && uv run pytest`; native build checks are below.

## Native macOS alpha

- `macos/Research.xcodeproj` is a real SwiftUI app (macOS 14+, arm64). It owns
  the child process and uses native SwiftUI controls. The Windows target uses
  WinForms. The native interface migration is in progress.
- `backend/desktop.py` binds a random `127.0.0.1` port and announces readiness.
  The sidecar always starts API-only, with no static asset dependency.
- `scripts/build_macos_app.sh` builds the PyInstaller `onedir` sidecar
  and the Xcode app, copies the sidecar into Resources, then
  ad-hoc signs and verifies the bundle. Run it from the repository root.
- The shell writes to `~/Library/Application Support/research/data`; every
  launch has a random `X-Notaeo-Desktop-Token` request credential, in addition
  to account Bearer authentication. Windows uses AppData. Development remains
  unguarded when `RESEARCH_DESKTOP_TOKEN` is absent.
- The local build is not notarized or publicly distributable. Notarization
  requires Apple’s paid developer program and must remain optional under $0.

## Keyless discovery

- `/api/web/search` uses DDGS with moderate SafeSearch and no key or account.
  Its results can be added through the UI as URL sources and become local
  notebook data after ingest.
- The search panel has separate **Your sources** and **Search the web** modes;
  it does not silently send source searches to the internet.
- Keyless discovery, ingestion, search, reading, study workflows, and exports
  are the product direction. Do not make any of these rely on the optional AI
  adapter.
- Optional remote AI supports Gemini, OpenRouter, and Groq (user picks in
  Settings). The exam-coach milestone can lead with AI, while core study
  remains useful without a key. Keys are stored per-user; AI remains disabled
  when unconfigured. `core/providers.py` retries 429s
  (honoring `Retry-After`) and falls back to backup free models before erroring.

## Locked owner decisions

1. **Accounts required, AI optional** — login (email + Google done, Apple at App Store time) gates every data route; AI keys stay optional and per-user. Self-hosting stays $0.
2. **No local LLMs** (no Ollama) — optional remote AI is not a product dependency.
3. **No-AI mode is first-class** — ingest/search/web discovery/reader/exports work with no provider configured.
4. **Python backend (FastAPI + uv) + native clients** — SwiftUI on macOS and WinForms on Windows; website removed.
5. **Commits: conventional prefixes, single line, no body, no Co-Authored-By.**
6. **SQLite store** — multi-user data lives in `app.db` (WAL) under the data dir; per-user rows everywhere, cross-user access is 404. Swap inside `core/store.py` only. One-shot JSON import: `backend/scripts/migrate_json_to_sqlite.py`.
7. **Public/private boundary (locked)** — this repo stays MIT and holds the complete useful keyless/no-AI local/self-hosted product (ingest, search, reader, study, exports, discovery, shared UI, local service, BYOK adapters). Private `fordaaaa/research-server` owns hosted operations only: cloud accounts, managed storage/sync, subscriptions/entitlements, hosted AI credits/routing, rate limits/abuse controls, admin/ops, production secrets/infra. Never imply access to private code or gate local flows on it.
8. **Three AI modes (locked)** — no-AI first-class, BYOK (per-user Gemini/OpenRouter key), hosted credits later (limited free allowance + paid tiers, routed/entitled by the private server).
9. **Platforms (owner update 2026-10-07)** — native SwiftUI macOS and WinForms Windows apps first; website and browser source removed from both repos. iOS and Android live in `research-mobile`; bounded Settings/style work resumed while desktop remains the priority.
10. **Hosted-launch legal (locked, owner + lawyer required)** — launch needs Terms of Service, Privacy Policy, Acceptable Use/AI terms, subscription/cancellation language, retention/export/deletion commitments, copyright/takedown handling, and student/minor-data treatment. Legal review is required; docs must not draft definitive legal claims.
11. **Coding-worker policy (locked)** — every future coding worker writes a meaningful failing test first, implements, runs targeted tests, runs the repo-required broader checks, reports exact evidence, and commits only after reviewer approval.

## Environment facts (this machine)

- MacBook Pro M1 Pro, 16 GB, macOS. `uv 0.12.1`, Python **3.12.13** (uv-managed; system python3 is 3.14 — do not use), Node 26, npm 11.
- npm installs can exceed 30s tool timeouts — use `npm install --maxsockets=25 --fetch-retries=1 --fetch-retry-maxtimeout=6000 --loglevel=error` and split installs. `setsid` does not exist on macOS; use `nohup` for background jobs.
- Long work sessions: owner wants `caffeinate -dimsu` running (`nohup caffeinate -dimsu &`, `pkill caffeinate` when done).
- Backend deps installed: pymupdf, python-docx, python-multipart, trafilatura, httpx, pyinstaller.

## Stack versions

FastAPI + pydantic v2 (backend, `uv.lock` pinned) · SwiftUI (macOS) · WinForms/.NET 10 (Windows) · storage: SQLite `app.db` under the data dir (gitignored). Note newer fix commits: streamed uploads (50 MB cap mid-stream), path-id validation via `api/deps.safe_id`, generic 500 handler, capped query/paste lengths.

## Backend map (current)

- `api/main.py` — FastAPI factory; lifespan sets `app.state.store`; global exception handler returns generic 500 (no stack leak); serves APIs only; no static assets or browser docs UIs.
- `desktop.py` — ephemeral loopback Uvicorn entrypoint for the native app.
- `api/deps.py` — `safe_id()` (regex `^[a-f0-9]{12}$`), `get_store(app)`, `notebook_or_404(store, user_id, ...)` (ownership-checked), `get_current_user()` (Bearer → 401).
- `api/auth.py` — `POST /api/auth/register|login` (pbkdf2, 30-day sessions; register answers duplicates `200 {registered: false}` — anti-enumeration), `POST /api/auth/logout`, `GET /api/auth/me`, `POST /api/auth/google` + `GET /api/auth/google/status` (id_token verification via `core/google_auth.py`, 503 unconfigured), `GET /api/me/progress` (onboarding flags). Login is rate-limited in three layers (verify-first per-key 10/5min, per-IP 60/5min, per-email 50/5min) plus a 20/hour/IP register throttle; XFF is ignored unless `RESEARCH_TRUST_XFF=1`.
- `api/notebooks.py` — `POST/GET /api/notebooks`, `GET /api/notebooks/{id}` (detail), `DELETE /api/notebooks/{id}`, `GET /api/notebooks/{id}/export` (Obsidian-style markdown zip).
- `api/sources.py` — upload (multipart, ≤50 MB streamed cap, ≤20 files, per-file errors), paste (`/sources/text`), URL (`/sources/url`), list, get, chunks (offset/limit), `PATCH /api/sources/{id}` (rename + tags), delete.
- `api/outlines.py` — persistent deep-research outlines per notebook: CRUD, `POST /outlines/draft` (heuristic angles + optional AI items/fields), `POST /outlines/{id}/deep` (per-item web pass, never ingests), `POST /outlines/{id}/report` (outline-structured digest or AI report saved as a source).
- `api/humanize.py` — `POST /api/humanize/analyze` (keyless pattern flags, no notebook needed), `POST /api/humanize/rewrite` (optional AI rewrite with voice sample; 503 without a key).
- `api/skills.py` — per-user skills library CRUD (`/api/skills`) + per-notebook memory notes (`GET/PUT /api/notebooks/{id}/memory`). Matched skills + memory are appended to chat/synthesis/report prompts only when AI is configured.
- `api/demo.py` — `POST /api/demo` builds a "Cell biology demo" notebook (3 original study sources + outline + memory) so new users can try everything with one click.
- `api/study.py` — keyless study tools: flashcard CRUD, persisted review scheduling and due queues, source-grounded card suggestions, glossary, quiz, Anki-ready TSV export, one-page study guide (`GET/POST /guide`, saveable as a source), and mind map tree + markdown export (`/mindmap`).
- `api/search.py` — `GET /api/notebooks/{id}/search?q=&kind=&source=&tag=&limit=&offset=`; delegates to `store.search(...)`.
- `api/ai.py` — optional BYOK chat: provider settings (`GET/PUT/DELETE /api/settings/ai`), chat session CRUD + messages, `POST .../chat`; `GET /api/ai/hosted/status` honestly answers `{enabled: false}` locally (the private hosted server overrides this route).
- `api/notes.py` — notebook markdown notes CRUD with validated source/chunk citations and optimistic concurrency.
- `core/models.py` — pydantic: `Page`, `Chunk`, `Source` (`tags`, `meta`), `SourceSummary`, `Notebook`, `SearchHit`, `NotebookCreate`, `PasteCreate`, `SourceUpdate`, `UrlCreate`. `SourceKind` includes `"url"`.
- `core/parsers.py` — magic-byte + ext + content-type detection; PDF→pages via PyMuPDF, DOCX via python-docx (single page), txt/md utf-8. Unknown → 415 (`IngestError`).
- `core/chunker.py` — normalize → sentence split → greedy ~1200-char chunks, ~150 overlap, **never spans pages**.
- `core/search.py` — query parsing + relevance: keyword AND, phrase, filters; closer-term ranking and grouped prefix fallback for single-token queries.
- `core/deepresearch.py` — outline draft/parse helpers, per-item query builder, outline-structured report digest + prompt.
- `core/humanize.py` — 13 deterministic AI-writing pattern checks + rewrite prompt builder (all keyless; rewrite itself needs a provider).
- `core/skills.py` — trigger matching (substring, cap 3) + prompt-section builders for skills and memory.
- `core/study.py` — term-frequency key terms, markdown study-guide builder, mind-map tree + markdown serializers (all keyless).
- `core/websearch.py` — keyless DDGS public-web discovery.
- `core/gemini.py` / `core/openrouter.py` — provider REST clients; errors carry `status` + `retry_after`.
- `core/api.py` — common optional AI entry point for all supported providers; new callers use this facade.
- `core/providers.py` — internal dispatch `generate(provider, key, model, prompt) -> (answer, model)`; retry on 429/5xx, skip to backup models on 404/400, abort on 401/403; `FALLBACK_MODELS`/`DEFAULT_MODELS` constants live here.
- `core/store.py` — SQLite store (`app.db`, WAL): users (pbkdf2), sessions (hashed tokens, 30d, `purge_expired_sessions()`), per-user notebooks/sources/outlines/cards/notes/skills/memory/chat sessions/AI settings/`user_progress` (`mark_progress`/`get_progress`); `RESEARCH_DATA_DIR` override; `search()` (keyword AND, phrase, filters).
- `core/ingest.py` — `ingest_bytes` (files), `ingest_text` (paste), `ingest_url` (calls `fetcher`).
- `core/fetcher.py` — httpx GET + trafilatura article extraction; `FetchError` → mapped to HTTP status.
- `core/article.py` — XHTML article extraction for ingest.
- `core/keypassages.py` — deterministic passage ranking behind reader cited passages.
- `core/local_runtime.py` — privacy-boundary facts served by `GET /api/runtime` (desktop/server mode, loopback-only, explicit egress list).
- `core/google_auth.py` — Google id_token verification for OAuth sign-in; 503 when unconfigured.
- `core/export.py` — notebook → `index.md` + per-source `.md` with YAML frontmatter, zipped.

## Native client map

`macos/Research/` contains SwiftUI screens, the authenticated API client and
loopback process manager. `windows/Research/` contains the corresponding
WinForms screens and native process/API clients. Frontend source and browser
build/test commands were removed on 2026-10-07.

## Testing

- `backend/tests/` — feature folders keep API, auth, AI, core, ingest, search, study, export, and platform tests together. Root `conftest.py` sets `RESEARCH_DATA_DIR` to a temp dir per test and exposes an **authed** `client` fixture (registers one user, sends its bearer token). See `auth/test_auth.py` for register/login/logout/isolation coverage.
- Build checks: `cd backend && uv run pytest`; `sh scripts/build_macos_app.sh` for the signed arm64 app and sidecar; macOS XCTest; Windows portable tests and Release cross-publish. Build the Windows Python sidecar on Windows. Mobile browser journeys belong to its separate Expo development harness.

## Next milestones

- **Owner selection (2026-10-02): AI exam coach.** Course material →
  explanations → practice → revision plan. Prioritize useful retrieval, then
  one editable exam revision session, then attempts/missed topics and a
  reasoned follow-up session. This supersedes the earlier essay-first milestone
  order; accounts, useful no-key core flows, and hosted boundaries remain.
  See `docs/PRODUCT.md`, `docs/NOTAEO_DIRECTION_DRAFT.md`, and `docs/EXAM_COACH.md`.
  The first goal/session/attempt/follow-up loop is implemented; evaluate real
  course material and AI explanations next. Calendar integration, AI grading,
  whole-course coverage, and readiness estimates remain future work.
- **M3** — icon, native export/download handoff, and automated Xcode tests shipped. Distribution status is documented in `docs/MACOS_DISTRIBUTION.md`; streamed chat and public distribution work remain, with paid notarization optional for local builds.
- **M7 — SHIPPED (multi-user):** SQLite store, email auth (pbkdf2 + 30d sessions), per-user everything, login UI, JSON→SQLite migration script, private `research-server` self-host repo.
- **Next: verify Google OAuth end-to-end** (real client ID + web button flow), then Apple at App Store time ($99 program).
- **Owner vision (2026-09-29) — Notion for students:** grow the notes module into a block editor (slash commands, drag handles, inline `@source` citations linked to chunks), add academic citation exports (APA/MLA/BibTeX) from notebook sources, and make the app near-addictive with tasteful streaks/due badges/review celebrations built on the existing sound + press-physics language.
- **M5 — SHIPPED (student-ready v2 in working tree):** scheduled flashcards with grounded drafts, mobile review, glossary, quiz, Anki TSV export, keyless one-page study guides, keyless mind maps, in-app source reader, one-click demo notebook, and notebook zip export.
- **M4 polish** — possible follow-ups: persist research plans per notebook, cap bulk-add selections, retry failed adds.

## Keyless research mode (M4, shipped)

- Staged, frontend-driven pipeline — no background jobs. `POST /api/notebooks/{id}/research/plan|gather|synthesize` in `api/research.py`; algorithm in `core/research.py` (5-template heuristic planner with optional AI planner and line-based parse + heuristic fallback; URL-normalized cross-query ranking `3×queries + max(0,4−pos) + min(5,overlap)`, ≤2/domain, cap 15; digest builder). Shared cited-context helper lives in `core/context.py` (extracted from api/ai.py; used by chat and synthesis).
- Gather never ingests: the UI bulk-adds through the existing per-URL `/sources/url`. Failed queries degrade individually (0.35s `QUERY_DELAY`); 503 only when all fail. Synthesize falls back to the keyless digest on any AI error and records `{research_topic, queries, origin}` in source meta via `ingest_text(extra_meta=...)`.
- Frontend: `ResearchPanel.tsx` state machine (topic → editable query chips → ranked checklist with top-5 preselect → per-URL add progress → optional overview), wired into App.tsx between ChatPanel and SearchPanel.
- **Deep-research outlines (Deep-Research-skills-inspired, shipped):** persistent per-notebook outlines (SQLite-backed, per-user) with editable items + fields, human-in-the-loop at every stage (draft → edit → per-item deep pass → bulk add → outline-structured report). Heuristic draft reuses the 5 plan angles + 4 default fields; AI draft upgrades to concrete items/fields when configured. Same keyless guarantees as quick research (never ingests during deep pass, digest fallback, 503 only on total failure). UI: `OutlinePanel.tsx` under the Deep research tab.
- **Humanizer (humanizer-skill-inspired, shipped):** `core/humanize.py` implements 13 of the 25 public patterns as deterministic regex checks (staging, AI vocab, inflation, formatting, chat residue, rhythm). `POST /api/humanize/analyze` is keyless and notebook-free; `POST /api/humanize/rewrite` needs a configured key and accepts an optional voice sample. UI: `HumanizerPanel.tsx` under the Humanize tab.
- **Skills + memory (hermes-agent-inspired, shipped keyless subset):** global skills library (SQLite-backed, per-user; trigger-word matching, cap 3) and per-notebook memory notes. Both work with no key, and only reach a provider as prompt sections in chat/synthesis/report when AI is configured. Deliberately NOT vendored: Hermes gateway, messaging platforms, cron, subagents, TUI — all require keys/servers and would break keyless-first. UI: `SkillsPanel.tsx` under the Skills tab.
- **M5 — shipped**, see Next milestones (study kit: flashcards, guides, mind maps, reader, demo).
- **M6** — improve optional remote AI quality/provider choices and streaming alongside the exam-coach milestone; provider availability must not gate core study.

## Parking lot

SQLite FTS5/sqlite-vec migration · chunk-level notes/annotations · source file-type passthrough (keep original bytes for re-parse) · field search (e.g. `title:`) · tag collections/folders · reader API (highlighted page text).
