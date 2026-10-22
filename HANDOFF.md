# HANDOFF.md

## Next product milestone — connected student workspace (2026-10-22)

Latest owner feedback: both mobile and macOS are bare bones. The desired product
combines engaging Gizmo-like study with an organized coursework workspace for
planning, alerts, citations and papers. Read [PRODUCT](docs/PRODUCT.md) and
[the grounded direction](docs/STUDENT_WORKSPACE.md). This expands exam-coach-only
positioning; it does not restore a website, require AI or remove release gates.

Planning only in this update: no app redesign has been implemented. The next
visible milestone is Today plus connected course/material/assignment navigation
on both clients, with due review directly reachable. Existing backend classes,
assignments, dashboard/calendar, notes and outlines provide foundations currently
poorly exposed by the clients. Formal bibliographies, paper writing and native
reminders are substantial missing work, not capabilities already shipped.

Investigate before wiring: dashboard/calendar exclude overdue assignments and
bucket server/UTC days; class and notebook are distinct; assignment notebook-link
ownership must be proven. Do not assume dashboard data powers overdue work or
rename all notebooks to courses. Source references are not APA/MLA bibliographies.
Use the owner waiver of repeated approvals; develop bounded specs/plans and real
connected interactions, not another isolated test/polish milestone. Independent
OpenCode product critique informed this direction, not student validation.

The latest mobile work is committed in `research-mobile` as `5f88dfa`, `98ec6e6`
and `930a9ba`. Its HANDOFF.md records the running Expo Go preview, 189 unit tests,
22 browser-profile interface checks, a real backend workflow, 50% whole-app line
coverage and remaining release risks. Those fixes do not establish a compelling
mobile product. Preserve the unrelated `.serena/project.yml` edit in this repo.

## Current milestone — duplicate safety and real native workflows (2026-10-22)

The authorized desktop review/fix/retest loop is complete locally for this
bounded milestone. Use [SPEC](docs/native-workflows/SPEC.md),
[PLAN](docs/native-workflows/PLAN.md) and [review evidence](docs/native-workflows/REVIEW.md).
The owner waived repeated approvals. Current delegation is through OpenCode;
older Luna-only routing and previous milestone counts below are historical.

### Shipped locally

- `476277a fix: require explicit consent for duplicate pastes`: removes the
  automatic forced retry. A snapshot/scope-aware controller and native dialog
  require Save a copy; cancel/dismiss/account/notebook changes cannot trigger a
  later implicit copy. Twelve new tests include async races and draft recovery.
- The commit containing this handoff adds `scripts/test_macos_workflows.sh`:
  build the signed app/sidecar, compile production Swift client/state sources,
  then exercise auth, source import/read/search, duplicate consent, basic
  revision, maps/export, ownership and token revocation against real SQLite.
  Synthetic data only; no Keychain, real sound or AI/discovery calls.
- Four supervisor fault cases cover missing/exited/invalid/interrupted backend
  preparation. An actual interruption failure exposed a leaked synthetic child
  in the first harness; it was stopped and the shell now directly owns both
  children and removes scratch only after stopping them. Final cases all pass.

### Verification and limits

Full native XCTest 106/106 passes; controller line coverage 82/83 (98.80%).
Signed arm64 sidecar/Release app build and the canonical real workflow pass.
OpenCode independently reran that workflow and all 12 consent tests, exit 0;
final independent code review APPROVE with zero confirmed findings. New runner
Python checks pass Ruff/Pyright, shell syntax and whitespace checks pass.
Native whole-app line coverage remains 1201/7008 (17.14%); Swift branch coverage
and full GUI E2E are absent. This is not a production-ready certification.
The prior unchanged backend's 670-case verifier remains prior evidence.

The free GLM 5.3 Flash bridge model was catalog/price checked explicitly; no
native or paid fallback. Brig `research-native-macos` was refreshed over the
26 production Swift files. A broad coding worker timed out without edits;
the coordinator implemented and bounded reviewers/retests completed. Full
provenance, temporary log paths and exact commands are in REVIEW.md.

No push/deployment, website/mobile/Windows work, provider/billing changes or
private-server changes in this milestone. Preserve the preexisting unrelated
`.serena/project.yml` edit. Rebuilt local app:
`macos/build/Build/Products/Release/Notaeo.app` (ad-hoc signed, not notarized).

### Resume / next three steps

1. Try a real course in the GUI: duplicate cancel/copy, notebook/account changes,
   complete basic practice and export. Record concrete friction; listen to the
   opt-in chime manually. Student usefulness and polish ratings remain unvalidated.
2. Add critical GUI interaction coverage and fix observed notebook/search
   defects in bounded test-first commits; the whole-native coverage gap remains.
3. Follow `docs/desktop-polish/AI_PLAN.md` for an optional grounded explanation
   evaluation. Keep basic study useful with AI disabled; hosted parity and
   deployment require their own scope, not public-repo credential changes.

From root, `sh scripts/test_macos_workflows.sh` builds and checks the packaged
workflow; `--no-build` reuses the existing sidecar. From `backend/`, run
`env -u VIRTUAL_ENV uv sync` for setup and
`env -u VIRTUAL_ENV uv run python ../macos/WorkflowChecks/check_runner_failures.py`
for all four runner faults. Use the exact full native XCTest command in PLAN.md.
To work next session: read the current native-workflows SPEC/PLAN/REVIEW, preserve
the unrelated edit, confirm the bridge/catalog, run the relevant reproduction
and implement one observed gap test-first with independent review before commit.
Do not interpret passing CLI/API checks as GUI E2E or student validation.

## Previous milestone — desktop polish review loop (2026-10-22)

The owner asked to resume OpenCode testing/rating, implement fixes, improve
logo/sounds, center a normal launch window, add loading polish and plan optional
AI. The owner previously waived repeated approvals. This bounded iteration is
complete locally; the older backend/Luna-only routing notes below are historical.
Use the current [desktop SPEC](docs/desktop-polish/SPEC.md),
[PLAN](docs/desktop-polish/PLAN.md), [review evidence](docs/desktop-polish/REVIEW.md)
and [AI plan](docs/desktop-polish/AI_PLAN.md).

### What changed

- `f1bc878 feat: center native launch and add folio startup`: main-only,
  once-per-window placement in the screen visibleFrame; normal launch preference
  and nonrestorable window; preserve later movement/Settings. Original folio/N
  startup with actual backend lifecycle status, no AI request/fake percentage or
  minimum delay, and static reduced-motion rendering.
- `ef795a6 feat: polish native identity and completion feedback`: matching
  original generated app icons, offline 0.52s C4/E4 cozy cue, native Settings
  opt-in/default-off and explicit preview. Export feedback follows a successful
  atomic file write; cancellation/failure/mute stays silent. Tests inject a
  playback callback and never physically play sound. No startup audio.
- This documentation commit saves reviewed evidence, an optional-AI roadmap
  and the corrected bridge catalog check/default in AGENTS.md. No bridge source
  change, provider setting or paid fallback was introduced. The bridge rebuild
  created no tracked cline changes from this work.

### Bridge recovery and review provenance

Client restart alone did not resolve the retired Muse model. The bridge built
and started successfully, and MCP configuration points at the expected dist
entry point. Actual CLI stderr identified ProviderModelNotFoundError; the
free-only bridge list is hard-coded. Verify health with the actual CLI catalog
(`freeOnly=false`) as well. Explicit current zero-price free bridge models used:
Nemotron 3 Ultra for baseline, Big Pickle for launch review/retest, GLM 5.3 Flash for
bounded final reviews/retest. No native coding agents or paid model substitution.
Current recommended default is catalog-checked GLM free; stale-model recovery
is documented without weakening the real missing-bridge stop gate.

Baseline OpenCode ran 68 backend cases successfully and provisionally rated
usefulness 8/coherence 8/polish 7/trust 8 out of 10. The coordinator checked actual
session tool output and rejected unsupported findings, including a claimed
answer-draft leak (keys already include session and task). Review is not student
validation. After fixes, OpenCode held polish at7/10 because no listening or
hands-on usability trial establishes improvement yet.

### Checks and limits

- Full native XCTest 94/94 pass. OpenCode independently reran all 12 new cases:
  7 presentation + 5 feedback, zero failures. The actual test-host main app window
  is centered, windowed and inside its current screen; snapshot renders offline.
- Full arm64 sidecar/Release build and ad-hoc app signature checks pass. Rebuilt
  app: `macos/build/Build/Products/Release/Notaeo.app` (local, not notarized).
- Full backend verifier exits0: build/types/lint/security pass,670 tests,
  combined 88.93% coverage (91.34%lines/81.14%branches). Backend source unchanged;
  its earlier four-file diff snapshot is not the final native diff count.
- NativePresentation helper 171/176 lines 97.16%; ResearchApp 215/254 (84.65%).
  Full native app 1119/6871 lines 16.29%, MainView 0/1055, SettingsView 10/274.
  xccov supplies no Swift branch percentage here. Native whole-app coverage
  and critical interaction E2E remain below the owner's requested gate.
- Independent final launch/helper/UI/generator/AI-plan reviews approve with
  zero unresolved findings. Timed-out reviewers are not recorded as approvals.
  GitHub license references are saved in REVIEW.md; no third-party assets were
  bundled. The mark/chime are original reproducible code-native assets.

Evidence `/tmp/notaeo-desktop-*` includes placement/restoration/feedback/icon/
export RED logs, full native GREEN, image/coverage JSON and signed build logs.
`/tmp/notaeo-opencode-native-retest-final.log`:12/12 pass.
`/tmp/notaeo-desktop-backend-gate.log`: backend 670-case verification report.
Preview PNG `/tmp/notaeo-startup-preview.png`; optional listenable sample
`/tmp/notaeo-cozy-chime.wav` (not played by the agent). Temporary evidence is
local and is not a durable release artifact.

Local feature checks are green; **public production release is NO-GO**. Native
UI coverage/branch evidence, critical-flow GUI trials, fullscreen/multi-monitor
relaunch, physical listening, Windows packaging/runtime, notarization and hosted
operations remain separate gates. No deploy, push, private-server/mobile change,
real user-data operation or actual AI inference occurred. Preserve the existing
`.serena/project.yml` edit; it stays outside these commits.

### Next three steps and resume

1. Run the owner trial in REVIEW.md with a disposable course account: relaunch,
   move/resize/Settings, preview/opt-in/export/cancel/mute, then import/search/
   coach/self-rating/export. Record observed friction and preference.
2. Add a bounded native critical-flow test phase and improve measured UI coverage;
   verify Windows on Windows and macOS 14/fullscreen/multiple displays on hosts
   that exercise those paths. Do not substitute API/logic tests for GUI use.
3. Start AI_PLAN Phase A with synthetic course/evidence fixtures, then ground a
   Phase B contract plan in the existing coach API/client and selectively verify
   hosted parity. No personal keys, local LLMs, paid provider, invented allowance,
   automatic inference, grading or mastery scores. Quality/capacity targets TBD.

Resume from root with git status/log and the four desktop docs. Native tests:

```sh
DEVELOPER_DIR=/Applications/Xcode-26.3.0.app/Contents/Developer xcodebuild -project macos/Research.xcodeproj -scheme Research -configuration Debug -derivedDataPath /tmp/notaeo-desktop-tests -destination 'platform=macOS,arch=arm64' CODE_SIGNING_ALLOWED=NO -enableCodeCoverage YES -parallel-testing-enabled NO test
sh scripts/build_macos_app.sh
# backend; never system python3 or --active
cd backend
env -u VIRTUAL_ENV uv run scripts/verify.py
```

Use Brig index `research-native-macos` for `macos/Research` source, not generated
build files. A future agent can start from the clean feature commits, preserve
the unrelated public edit, use functioning catalog-verified free OpenCode review
workers, run meaningful tests before code changes and retain actual evidence.
The next step is a concrete native-flow/fixture increment, not a fresh interview
or another approval prompt. Backend and hosted handoffs remain separately scoped.

## Historical backend milestone and earlier context


Updated 2026-10-22. Branch `main`; installed native macOS and Windows apps
are the priority. The website, browser frontend and static serving were
removed from both public and hosted repositories on 2026-10-07. Mobile lives
in `research-mobile`; its bounded Settings/coach pass is active.

## Current milestone: Phase 2b trust-store fix and Phase 3 verifier guide complete

Owner approved `Yes—implement Phase 3`, then separately approved Phase 2b with
`you can implent`, both on 2026-10-22. Neither needs reapproval. This milestone
covers the certifi-only patch, regression tests, rebuild/verification, verifier
guide, release assessment and reviewed handoff. No deployment. Existing native
Luna-low identities provided test authoring and independent reviews, with no
OpenCode agents. The required bridge health check passed. Brig backend context
was refreshed; conversation decisions remain in SPEC/PLAN/HANDOFF.

Actual command from backend, `uv run scripts/verify.py`, exits 0:

VERIFICATION REPORT — Build: PASS, Types: PASS (0), Lint: PASS (0), Tests: PASS (670/670, 88.93%), Security: PASS (0), Diff: (10 files). Overall: READY. Issues to fix (numbered).

1. No blocking issue in the approved backend change. That pre-commit snapshot
   counts nine intended files plus unrelated preexisting `.serena/project.yml`,
   which remains outside our commits. It is not a post-commit diff count.
2. Public application release remains NO-GO: native critical-flow/clean-machine
   runtime tests, Windows packaging/runtime, migration-recovery evidence,
   notarization and hosted monitoring/operations are separate unfinished gates.

Phase 2b fixes PYSEC-2026-4320 / GHSA-6q48-6c7w-9gw2 by updating certifi
2026.7.22 → 2026.10.19. Before the patch, new lock-floor and actual SSL trust-store
regressions produced 2 failed / 21 passed. Afterward all 23 configuration tests
pass. Only certifi changes in the complete resolved lock metadata and installed
package maps. `uv sync --locked --inexact` preserved unrelated installed tools.
HTTPS verification stays enabled; no application source, data or schema changed.
Fresh strict pip-audit checks 85 packages with zero vulnerabilities; scoped
source scan is clean. No exposure/interception evidence or secret-rotation need.

The full application coverage scope still contains all 51 API/core modules:
5845/6399 lines (91.34%), 1605/1978 branches (81.14%), combined 88.93%; 22 old
excluded lines, no new exclusions/suppressions. The touched configuration-test
scaffold is separately 293/300 lines (97.67%), 42/52 branches (80.77%), with no
exclusions. Type/lint checks pass. No test deleted, disabled or skipped.

Full `sh scripts/build_macos_app.sh` exits 0 after the update: arm64 sidecar,
Release app and ad-hoc signature checks pass. The actual development, rebuilt
sidecar and app certificate PEMs share SHA256
`50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785` and
120 roots. Host Python SSLContext loads each file: compromised emSign ECC Root
CA - G3 absent, CERT_REQUIRED and hostname checks enabled. This inspects real
packaged files; it does not exercise TLS through a running sidecar or establish
native runtime E2E. .NET/PowerShell and the old temporary SDK remain absent.

Evidence logs: `/tmp/notaeo-phase2b-red.log`, `-green.log`, `-types.log`,
`-lint.log`, `-config-coverage.log`, `-final-gate.log`, `-audit.log`,
`-macos-build.log`, `-bundle-check.log` (all use the `notaeo-phase2b` prefix).
Ignored `backend/build/verification/` snapshots: `phase2b-final-coverage.json`,
`phase2b-config-coverage.json`, `phase2b-final-audit.json`,
`phase2b-bundle-check.json`. A read-only observer preserved full coverage before
per-run cleanup; the CLI itself leaves no export copy. Initial failed October
22 evidence remains in `phase3-current-*` logs/JSON; it is superseded by this
final gate. Earlier October 17 clean results below remain historical.

Phase 2b files: `backend/uv.lock`,
`backend/tests/platform/test_verification_configuration.py`. Phase 3 files:
new `docs/VERIFICATION.md`, README link, corrected macOS distribution guide,
development-loop routing/unknown convention, SPEC/PLAN/HANDOFF. Docs checks
include whitespace, local Markdown links and command/status consistency.
Independent Luna code review approves the lock/tests; scoped security review
approves the final gate/audit/bundle evidence with zero CRITICAL/HIGH/MEDIUM/LOW
findings and no rotation requirement. Final docs status reconciliation passed
independent review; its MEDIUM stale-status and LOW scope-wording findings are
resolved, final APPROVE with zero unresolved findings. Certificate fix committed
as `620ca68 fix: remove compromised certificate trust bundle`; the separate
documentation commit is identified by `git log`. Public research only; no push/deployment,
private-server, mobile or native UI changes. Preserve `.serena/project.yml`.

Next three steps: (1) manually try the rebuilt native macOS app with synthetic
course material; (2) plan a bounded native critical-flow/E2E phase with explicit
approval and Windows evidence on an appropriate host; (3) select the next
student-facing feature using actual trial observations. Hosted operations and
migration recovery need their own owners/evidence; no release approval inferred.

Resume from root: `git status --short`, `git log -3 --oneline`, then read
SPEC.md, PLAN.md Phases 2b/3 and docs/VERIFICATION.md. Setup from backend:
`uv sync --locked --inexact`. Targeted tests: `uv run pytest
tests/platform/test_verification_configuration.py -q`; full gate:
`uv run scripts/verify.py`; development API: `uv run uvicorn api.main:app
--reload --no-proxy-headers`. Root native build: `sh scripts/build_macos_app.sh`;
manual launch: `open macos/build/Build/Products/Release/Notaeo.app`. Never use
system python3 or real student data for tests. Learned: fresh advisories expire
old passes, and patched Python environments do not update already-built apps.

## Historical completion: Phase 2 verifier — gate green on 2026-10-17

Owner approved `Yes—implement Phase 2` on 2026-10-16 and requested six native
Luna workers at low reasoning, with no OpenCode agents. Used exactly six in two
waves: core/CLI/security test authors, then three matching implementers. Root
passed the existing bridge startup health check without invoking OpenCode
agents; the explicit session routing override supersedes the delegation
preference. Phase 2 needs no reapproval. At that time Phase 3 was unapproved;
it was subsequently approved as recorded above.

Three new production files: `backend/core/verification.py`,
`backend/core/verification_security.py`, `backend/scripts/verify.py`. Tests:
`backend/tests/core/test_verification.py`, `test_verification_security.py`,
`backend/tests/platform/test_verification_cli.py`. Pure ordered evidence parser,
fixed-argv CLI, bounded child output/lifecycle, per-run coverage/JUnit artifacts,
read-only redacted source scanning and dependency audit are implemented. Initial
RED: core/security import failures; CLI 12 failed/1 passed. Independent native
reviews and root regressions exposed real bool-code/coverage-omission/source-
inventory/symlink/untracked/diagnostic-bound failures, all now fixed.
Saved RED logs: `/tmp/notaeo-phase2-*-red.log`; worker results in
`/tmp/notaeo-phase2-*-green.log` may predate later fixes; the final gate below
supersedes those intermediate worker results.
Current contract: `backend/build/verification/PHASE2_CONTRACT.md` (ignored);
PLAN.md records its durable scope. Child output now uses a bounded selector-
drained pipe instead of a potentially unbounded temporary output file.

Root completed integration and the actual end-to-end gate on 2026-10-17:

VERIFICATION REPORT — Build: PASS, Types: PASS (0), Lint: PASS (0), Tests: PASS (668/668, 88.93%), Security: PASS (0), Diff: (11 files). Overall: READY. Issues to fix (numbered).

1. No blocking issue in this approved backend change. The 11-file verification
   snapshot includes 10 intended files and the unrelated preexisting
   `.serena/project.yml`; that unrelated file stays outside our commits.
2. Complete application release remains NO-GO: native runtime E2E, Windows
   packaging/runtime, notarization and hosted operations/monitoring are separate
   unvalidated gates. No push or deployment performed.

Actual command from backend: `uv run scripts/verify.py`, exit 0. It runs the
real PyInstaller sidecar build before type/lint/full coverage tests/audit/diff.
Pyright checked 58 files with 0 errors/warnings. Application coverage keeps every
API/core module: 5845/6399 lines (91.34%), 1605/1978 branches (81.14%), combined
88.93%. Scripts are additionally collected for touched CLI coverage. Per-file
line/branch floors: evidence 92.99%/85.29%, security 91.49%/85.71%, CLI
90.49%/80.77%. No new exclusions or suppressions; 22 old excluded lines remain.
Read-only scan checks 53 production source paths with zero findings. Fresh
strict pip-audit has zero findings. `uv run scripts/verify.py --security-only`
also exited 0 and printed `SECURITY: PASS.` without an overall READY claim.

Evidence: `/tmp/notaeo-phase2-real-gate.log`,
`/tmp/notaeo-phase2-security-only.log`, `/tmp/notaeo-phase2-types.json`,
`/tmp/notaeo-phase2-lint.log`, and ignored
`backend/build/verification/phase2-final-coverage.json`. A read-only observer
preserved coverage JSON before the gate removed its unique temporary directory;
it did not alter checks. Earlier manual full suite: 1 failed/659 passed exposed
the calendar test's fixed October 15 date; only its clock fixture was frozen.
The five calendar tests now pass, as does the final 668-test suite. No test was
deleted, disabled or skipped. Root integration also fixed the real pip-audit
stderr/JSON conflict; both output streams are independently drained under one
128 KiB live cap, only stdout is parsed, and raw diagnostics are not printed.

Independent reviews reuse test-author identities that did not implement the
reviewed modules: `luna_core_tests` approves CLI/core/calendar plus stream delta;
`luna_cli_tests` approves combined evidence/security/CLI boundaries;
`luna_security_tests` approves the final security boundary. Final unresolved
CRITICAL/HIGH/MEDIUM/LOW counts all zero; no immediate secret rotation indicated.
They read full scoped code/tests and requirements; root ran the real gate.
The other three Luna workers implemented evidence, security and CLI respectively.

All changed files: `backend/core/verification.py`,
`backend/core/verification_security.py`, `backend/scripts/verify.py`,
`backend/tests/core/test_verification.py`,
`backend/tests/core/test_verification_security.py`,
`backend/tests/platform/test_verification_cli.py`,
`backend/tests/api/test_classes.py`, `PLAN.md`, `SPEC.md`, `HANDOFF.md`.
Only public research changed. No runtime dependencies, schema/data, native UI,
mobile or private hosted code changed. Brig `research-backend` and
`research-verification-tests` indexes refreshed. Decisions remain in these docs.

Next three steps: (1) use the verifier on the next approved change;
(2) select the next desktop/product priority or explicitly approve PLAN.md
Phase 3 if its documentation/release work is desired; (3) validate native
critical flows on actual platforms before any application-release claim.
These were the next actions on October 17; the current scope is above. Do not infer deployment
authorization from passing local checks.

Resume from `git status --short`, read PLAN.md Phase 2 and these new files, then
run targeted tests with `uv run pytest tests/core/test_verification.py
tests/core/test_verification_security.py tests/platform/test_verification_cli.py -q`
from backend. Full actual gate is `uv run scripts/verify.py` from backend;
`--security-only` runs just the scoped audit. It packages the macOS sidecar; full native app
runtime, Windows packaging and hosted operations remain separate release gates.

## Completed: Phase 1b remediation — local gate green

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

At Phase 1b completion the next three steps were: (1) owner manually tests the rebuilt
`macos/build/Build/Products/Release/Notaeo.app`; (2) choose the next priority and
explicitly approve PLAN.md Phase 2 if the automated verifier is desired;
(3) implement only that approved phase with RED/GREEN, independent OpenCode
review and the full gate. Phase 2 was subsequently approved/completed above;
Phase 3 was pending at that historical checkpoint. Local
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
are complete under the later explicit Phase 1b approval. Phase 2 received its
separate approval on 2026-10-16 and is now complete as recorded above.
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

## Historical product backlog (not the current approved phase)

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
.NET and PowerShell are absent on this host as of 2026-10-22; the previously
used `/private/tmp/notaeo-dotnet-sdk/dotnet` no longer exists. Do not claim the
old Windows evidence as a fresh run or silently reinstall tools.
MacBook Pro M1 Pro, 16 GB. Owner prefers `caffeinate -dimsu` during long work.
Mobile: `npm test`, `npm run typecheck`, `npx playwright test`; physical
native device checks remain separate. Private server: `uv run pytest tests
tests_hosted`, plus disposable API-only Docker verification.

OpenCode bridge health gate in `AGENTS.md` applies before code work. Default
routing prefers bounded OpenCode workers using
`opencode/muse-spark-1.3-contributor-free` at `xhigh`; the owner's current explicit
override is the existing six native Luna-low identities, no OpenCode agents.
The earlier broad worker timed out after 600 seconds; the retry splits file
ownership and lets the coordinator handle broader checks. If bridge tools fail,
follow the documented recovery procedure and stop; do not silently switch
workers or providers as a workaround.
