# HANDOFF.md

Updated 2026-10-15. Branch `main`; installed native macOS and Windows apps
are the priority. The website, browser frontend and static serving were
removed from both public and hosted repositories on 2026-10-07. Mobile lives
in `research-mobile`; its bounded Settings/coach pass is active.

## Current work: Phase 1b remediation — complete, local gate green

Owner asked to continue development with fresh subagent perspectives on
2026-10-15. Two independent read-only OpenCode agents reassessed the baseline.
They agree not to build the Phase 2 verifier while app gates fail, and that
22 type errors do not mean 22 runtime bugs. Coordinator reproduced a real
`TypeError` importing synthetic `</h2><p>Notes</p>` at core/article.py:131;
an owned source disappearing between lookup/update also lacked a 404 guard.
The remaining diagnostics are mostly safe existing invariants/annotations.

Owner explicitly answered `Yes—implement Phase 1b` on 2026-10-15 after the
plan review approved it with zero findings. Implemented only Phase 1b plus the
preserved Phase 1 configuration/tests: resilient malformed headings, missing
source-update 404, safe narrowing/annotations/import cleanup, urllib3 patch and
meaningful behavior tests. Real behavior RED was 5 failed/19 passed, then 24
passed; static RED was 22 types/3 lint. The dependency regression showed 1
failed/20 passed, then 21 passed with urllib3 2.8.0. No other previously locked
package version changed, no new suppression/Any or coverage omission was added.

Final measured gate: complete macOS app/sidecar Release build, ad-hoc signature
and arm64 checks PASS; Pyright 59 files / 0 errors or warnings; Ruff 0; 582 tests
pass with 7 existing dependency deprecations. Full api/core coverage is 5560/6091
lines (91.28%), 1482/1834 branches (80.81%), combined 88.86%. Each of 12 touched
production files exceeds 80% lines AND branches. New config scaffold alone is
97.56% lines/80.77% branches. Fresh pip-audit checks 85 installed packages with
0 vulnerabilities; contextual source scan has 0 candidates in 51 tracked
backend code files. Three fresh OpenCode review slices approve with zero
findings, including separate security review. Exact commands, changed-file
list, review sessions and limitations: docs/VERIFICATION_BASELINE.md's
2026-10-15 section. Logs `/tmp/notaeo-phase1b-*` and ignored
`backend/build/verification/phase1b-*` contain detailed local evidence.

The three broad OpenCode implementation jobs timed out at 600 seconds without
source edits. CLI recheck succeeded; coordinator implemented and integrated,
using smaller OpenCode test-generation and independent review packets. No
native subagent substitution. `.serena/project.yml` was modified on arrival and
is preserved outside our commits. Only the public research repo changed; no
push, deployment, schema/data migration or native/private/mobile source change.

Next three steps: (1) owner manually tests the rebuilt
`macos/build/Build/Products/Release/Notaeo.app`; (2) choose the next priority and
explicitly approve PLAN.md Phase 2 if the automated verifier is desired;
(3) implement only that approved phase with RED/GREEN, independent OpenCode
review and the full gate. Phase 2/3 remain unapproved and unimplemented. Local
patch readiness is separate from application release: native critical-flow E2E,
Windows runtime/packaging, notarization and hosted operations/monitoring are
still unvalidated; application release remains NO-GO.

Resume from root with `git status --short`, then read SPEC.md, PLAN.md Phase 1b
completion and the latest baseline section. Startup gate still requires the
three bridge tools and `list_opencode_models(freeOnly=true)`. From backend,
`uv sync --locked`, `uv run pytest`, `uv run pyright`, and
`uv run ruff check core api scripts tests/platform/test_verification_configuration.py`.
Run the expanded changed-test checks in the baseline when editing those tests.
From root, `sh scripts/build_macos_app.sh` rebuilds the native app. Never use
system python3 or real student data for test fixtures.

Accepted fresh perspective: app fixes and useful tests before more automation;
reject using extra Any/casts or static source bans just to satisfy checks.
Root Brig `research-backend` index refreshed; `build_session` source lookup was
fresh; the `research-verification-tests` index also refreshed after test edits.
Full-repo duplicate-symbol limitation and worker namespace caveat below
still apply. Old coverage/audit results below are dated 2026-10-12, not a new
verification run. Read SPEC.md/PLAN.md Phase 1b before resuming.

## Previous phase: Phase 1 verification baseline — NOT READY, uncommitted

Owner approved PLAN.md Phase 1 with `yes` on 2026-10-12, after waiving the
one-round interview due to limited testing. Implemented only verification
configuration/tests: dev-only Ruff/Pyright/coverage/pip-audit, declared scope,
separate 80% line/branch floors and ignored coverage output. No API/core/native,
hosted/mobile source or runtime dependency version changed. Phase 2 runner is
absent and not authorized. SPEC/PLAN/DEVELOPMENT_LOOP persist the scope/approval
process; read docs/VERIFICATION_BASELINE.md before any continuation.

Actual RED: 14 failed / 3 passed before config; coordinator policy regressions
4 failed / 16 passed; GREEN 20 passed. Full backend suite: 497 passed, 7 existing
deprecation warnings. New test/scaffold coverage: 97.50% lines, 80.77% branches.
The actual gate is red: sidecar build PASS, Pyright 22 existing app errors,
Ruff 3 existing unused imports, full api/core line coverage 89.42%, branch
coverage 77.33% (FAIL; combined 86.62% PASS alone is insufficient), pip-audit
3 advisories in preexisting urllib3 2.7.0. No new test type/lint diagnostics.
Independent OpenCode code review APPROVE, zero new-scope security issues;
dependency findings separately HIGH 1 / MEDIUM 2, applicability conditional.
Tracked-source scan found no exposed secret requiring rotation; private/live
secrets and deployment remain outside the audit. No app release is READY.

**Historical state on 2026-10-12, superseded by Phase 1b above:** changes could
not be committed while required gates were red. They were staged/unstaged in
the correct public `research` repo, not pushed or deployed. No test was deleted/skipped/disabled, no application diagnostic
suppressed, no coverage scope narrowed. Seven intended changed files: SPEC.md,
PLAN.md, HANDOFF.md, docs/VERIFICATION_BASELINE.md, backend/pyproject.toml,
backend/uv.lock and backend/tests/platform/test_verification_configuration.py.
Generated reports are ignored under backend/build/verification; temporary
logs /tmp/notaeo-phase1-* hold RED/GREEN/build/types/lint/test evidence. Do not
claim an automated verifier exists or that prior 2026-10-08 checks ran today.

The then-pending three actions were: (1) obtain approval for a specific remediation scope based
on the 22 types, 3 lint, dependency advisories and missing branch coverage;
(2) implement only approved fixes with RED-first behavior tests, independent
review and security assessment; (3) rerun the complete ordered gate and commit
only after green, then request the next named phase. These remediation actions
are complete under the later explicit Phase 1b approval. Phase 2 still needs
separate approval.
The proposed patched urllib3 version is 2.8.0; that would be a runtime dependency
change requiring new packaging and audit evidence, not a no-op tool update.

Resume setup: `cd backend && uv sync`. Targeted policy test:
`uv run pytest tests/platform/test_verification_configuration.py -q` (20 pass).
From root, build `sh backend/scripts/build_macos_sidecar.sh`; only after PASS,
from backend run `uv run pyright`, `uv run ruff check core api scripts
tests/platform/test_verification_configuration.py`, `uv run coverage run
--branch --source=core,api -m pytest`, JSON/report then `uv run pip-audit --local`.
Exact commands/exits/denominators and all diagnostics are in the baseline doc.
No real user DB or cloud secrets were accessed; no manual simulator server was
restarted or user data changed in this phase.

Brig root index still has the documented duplicate-symbol failure; backend
slug `research-backend` refreshed and root retrieved fresh API outlines. Worker
lookup may use a different index namespace; provide compact verified root
context. Root also saved fresh configuration-test outlines under Brig slug
`research-verification-tests`. Final review supplement approved the phase
artifacts with zero new findings while blocking release. OpenCode startup
gate passed, worker/reviews used
muse-spark-1.3-contributor-free at xhigh. Future context retrieval supplements,
not replaces, these durable approval/phase/evidence documents.

## Previous change: backend authentication and security audit

Account login uses backend email lookup and salted PBKDF2 verification; session
bearers are hashed in SQLite and account routes enforce ownership. Hardened
stored-hash parsing/cost bounds, added KDF work for missing/unusable hashes,
normalized logout revocation and added no-store headers, including errors.
Google login now refuses email-only linking/replacement with 409; explicit
account linking remains future work. No existing identities were migrated.

Mobile validates backend auth responses, rejects duplicate-registration 200
without token/user, protects replacement sessions from stale 401/logout and
serializes SecureStore writes. Bootstrap verifies saved tokens with /auth/me;
transport failures preserve them while showing guest mode. Auth screen requests
abort on disposal. No local fake account or password persistence was added.

OpenCode bounded workers and independent final backend/mobile reviewers
approved the code. Public backend: 477 tests. Private backend: 407 tests.
Mobile: 144 unit tests, clean type checking, 20 browser-profile E2E checks.
macOS arm64 sidecar/app build and signature verification passed.
The [audit report](docs/SECURITY_AUDIT_2026-10-08.md) records fixed findings and
limits; this is not a live penetration test or deployment certification.

Manual mobile testing remains available in Expo Go 57 on the iPhone 17 Pro
simulator, Metro on localhost:8082 and a synthetic local backend on :8002.
Compiled Expo 57 iOS builds require Xcode 26.4+; installed 26.3 cannot build
that target. This does not block the SwiftUI macOS packaging workflow.
No server deployment, push, personal keys or provider changes in this pass.

## Previous change: personal AI keys removed

Owner decision, 2026-10-08: Notaeo should help students study independently.
One optional operator-managed AI service can add explanations or practice.
Users no longer supply credentials, choose providers or enter models.
The local service defaults to unavailable. No paid provider, local LLM or
model download has been introduced.

The OpenCode retry on 2026-10-08 succeeded with bounded workers for public
backend tests, hosted tests and mobile availability gating. Independent
backend, desktop and mobile reviewers approved the implementation, recorded
as one feature commit per repository. This entry does not establish live deployment.

Validation of the final code:

- Public backend: 467 tests passed.
- Hosted backend plus private overlay: 396 tests passed.
- Windows: 169 tests passed; Release build had no warnings or errors.
- macOS: XCTest passed; full arm64 sidecar/app packaging and signature checks passed.
- Mobile: 131 unit tests, typecheck and 14 Playwright checks passed.
- Disposable Docker build and read-only API verifier passed with AI disabled,
  no external network or live data; test container and volume were removed.

Tests cover retired key routes, migration/data preservation, disabled/basic
flows, app isolation, grounding/history, actual model provenance, sanitized
errors, guest settings and mobile availability/disposal. No real AI inference
or production user database was used. Existing dependency deprecation warnings
remain in the Python suites.

- `core/api.py`: per-app `AIService` with a handler receiving user ID and
  grounded prompt, returning text and the actual model that answered.
  App factory initializes disabled service; hosted injection survives lifespan.
  Upstream error details are replaced with generic client messages.
- Authenticated `GET /api/ai/status` returns `enabled` and nullable `model`.
  Compatibility `/api/ai/hosted/status` also returns
  `allowance_remaining: null`; no allowance is promised or enforced.
- `GET/PUT/DELETE /api/settings/ai`, key DTOs/store methods, provider catalogs
  and Gemini/OpenRouter/Groq direct adapters are removed. SQLite startup
  drops the retired `ai_settings` table idempotently, preserving workspace
  data. Failure stops startup; this is logical removal, not forensic erasure
  of free pages, WAL files or backups. JSON migration skips retired keys.
- Basic coach, search, import, reader, cards, mind maps and exports remain
  usable without AI. Pure generation returns 503 when unavailable. Invalid
  AI practice/explanations fall back with a notice. Ownership remains 404
  before checking service availability. Actual successful model is persisted.
- Native/mobile Settings shows read-only availability and optional model;
  account, sound, appearance, reduced motion and orb previews remain.
- Jev and Laya are research candidates only. See `docs/DECISION_MODELS.md`;
  neither has been installed, benchmarked on course material or integrated.

## Product and owner decisions

Slogan: **Know what to study next.** The exam coach turns course material
into a short revision session, records self-ratings, and revisits missed topics.
Source-based practice leads; AI is optional. Ratings are not automatic grades
or an exam-readiness estimate. See `docs/PRODUCT.md` and `docs/EXAM_COACH.md`.

Accounts are required; email auth works, Google needs client-ID configuration,
and Apple sign-in comes at App Store time. Every workspace resource has an
owner; foreign access returns 404. Data lives in SQLite/WAL under the data
directory. Passwords use PBKDF2; sessions store hashed bearer tokens.

Budget stays $0 for now. Self-hosting is free; the Apple Developer Program's
$99/year is deferred until submission. No local LLMs. Public code stays MIT.
The private `research-server` owns hosted operations, credentials, routing,
quotas, storage limits, subscriptions, abuse controls and production secrets.
Public local flows must not depend on private subscriptions or credentials.

Use conventional single-line commits (`feat:`, `fix:`, `docs:`, `chore:`), one
logical change per commit, no body or Co-Authored-By. Meaningful failing tests
precede implementation; run targeted and required broader checks, then obtain
independent reviewer approval before committing. Do not commit a red tree.

## Desktop and mobile boundary

SwiftUI macOS and WinForms Windows call the loopback API sidecar. macOS data
uses Application Support; Windows uses AppData. Never put data inside bundles.
Native launch requires `RESEARCH_NATIVE_DESKTOP=1` and per-launch
`X-Notaeo-Desktop-Token`, alongside account Bearer authentication. Schemas are
private in desktop mode; `/api/health` remains a bounded health check.

Native features include sources/reader, local and web search, educational-site
index controls, sorting, cards, revision sessions, study guide and mind map,
settings and thinking motion. General native chat remains pending. The local
macOS build is arm64 and ad-hoc signed, not notarized or publicly distributable.
Windows portable checks run here; Windows sidecar packaging and actual WinForms
layout/navigation still require Windows.

Mobile uses Expo 57, with physical-device SecureStore, keyboard, safe-area,
SQLite reader and audio verification still pending. Read the exact versioned
Expo docs before editing mobile code. Its web harness is for testing the mobile
client, not a restored standalone browser product.

Search is lexical: stemming, phrase/exclusion parsing, weighted relevance,
academic aliases and conservative typo correction. Public discovery is explicit
and separate from local search. Selected educational sites are indexed only on
explicit refresh; importing results creates notebook sources. These are useful
without AI, with heuristic ranking limitations documented in
`docs/WEB_DISCOVERY.md`, `docs/EDUCATIONAL_INDEX.md` and `docs/EXAM_COACH.md`.

## Hosted state and deployment

The hosted repository is present locally and was selectively updated for this
feature. Its older shared snapshot still lacks the public native backend's
coach and query-aware context selection. Do not blindly run `scripts/sync.sh`
or claim full hosted/native feature parity.

Hosted AI remains disabled by default. Existing OpenCode operator configuration
is retained; no real inference or login change was made. HTTP inference is
stateless upstream; saved conversations include only owned bounded history,
not opaque upstream sessions. Global concurrency is two per process; persistent
account allowances, token accounting and aggregate storage quotas remain pending.

Live deployment is still unverified: run 37778397899 lost SSH during an image
build, then the retry could not reach the Tailscale host. Local Tailscale is
stopped. Restore host connectivity before deployment; no local test establishes
live health. Previous CI run 37778217446 passed for the older c60b5d9 server
snapshot. The validated, reviewed changes remain local; they have not been pushed or
deployed.

## Next work

Reconcile hosted coach/retrieval contracts, test the installed UI manually,
and improve native chat plus retrieval quality with public/synthetic fixtures.
Before public hosted invitations, add private admission/usage accounting,
owned storage ceilings, backup/restore checks and service-data disclosures.
Hosted launch still needs owner/lawyer review of Terms, Privacy, acceptable use,
retention/export/deletion, copyright handling and student/minor-data treatment.

## Environment and verification

Use Python 3.12 through `uv run` from `backend/`; never system python3 (3.14).
Backend: `uv run pytest`. Native packaging: `sh scripts/build_macos_app.sh`,
which selects Xcode 26.3 explicitly and verifies arm64 sidecar/app signature.
.NET portable SDK: `/private/tmp/notaeo-dotnet-sdk/dotnet`.
MacBook Pro M1 Pro, 16 GB. Owner prefers `caffeinate -dimsu` during long work.
Mobile: `npm test`, `npm run typecheck`, `npx playwright test`; physical
native device checks remain separate. Private server: `uv run pytest tests
tests_hosted`, plus disposable API-only Docker verification.

OpenCode bridge gate in `AGENTS.md` applies before code work. Prefer bounded
OpenCode workers using `opencode/muse-spark-1.3-contributor-free` at `xhigh`.
The earlier broad worker timed out after 600 seconds; the retry splits file
ownership and lets the coordinator handle broader checks. If bridge tools fail,
follow the documented recovery procedure and stop; do not silently use native
agents or switch providers.
