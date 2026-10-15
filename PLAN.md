# Summary

Feature: proposed production verification gate. SPEC.md is the requirements
source. Interview waived by the owner on 2026-10-12 because the app has not been
tested enough to provide evidence. Product assumptions remain unvalidated.

**Status: Phase 1 baseline and approved Phase 1b remediation complete (2026-10-15); local backend gate green.**
The 2026-10-12 approval covered Phase 1; the owner explicitly added Phase 1b
on 2026-10-15. Phase 2 and later phases remain unapproved. A request to
continue generally does not override the owner's Step 2 approval boundary.

Restated requirements:

- Run build → types → lint → tests/coverage → security → diff in order.
- Stop after a failing build. Missing, interrupted or unexecuted mandatory
  checks block readiness and cannot be reported as passing or zero errors.
- Produce the owner's exact report structure with measured counts, numbered
  issues and real evidence; verification makes no fixes automatically.
- Measure at least 80% lines and branches on touched code. Measure the entire
  approved suite separately; its coverage denominator needs approval.
- Preserve privacy, temporary-data integration tests and no-AI functionality.
- Keep feature completion separate from app release, native runtime validation,
  security review and production operations.
- Persist phase/approval/evidence context; use Brig and bounded OpenCode workers.

Proposed v1 boundary: public Python backend gate with separately documented
native desktop checks. Hosted/mobile integration, operational deployment and
new student features stay outside this plan. This boundary was approved with the plan on 2026-10-12; it is not evidence
of owner interview answers or student usefulness.

Complexity: **Medium**, estimated **10–16 engineering hours**, excluding native
runtime validation and remediation of existing application issues. This is a
planning estimate; the Phase 1 baseline may change it. No completion date or
existing global coverage percentage is asserted.

# Patterns to Mirror

| Category | Top observed example | Application |
| --- | --- | --- |
| Naming / pure logic | `backend/core/local_runtime.py:22` — typed `describe_runtime`, no framework imports | Pure report evaluation separate from the command adapter |
| Error handling | `backend/api/deps.py:75` — explicit missing/invalid session rejection | Invalid or absent verification evidence fails closed; CLI failures are not HTTP routes |
| Logging | `backend/api/auth.py:41` — metadata-only rate-limit warning | Record stage/exit/paths, redact secret values; no credentials in reports |
| Data access | `backend/core/store.py:516` — lookup through Store with bound SQL arguments | Any API integration uses existing Store and a temporary SQLite database, no new persistence layer |
| Tests | `backend/tests/platform/test_local_runtime.py:16` — temporary-data real TestClient checks | Hermetic integration that exercises the actual API and CLI boundary |
| Build | `scripts/build_macos_app.sh:11` and `backend/scripts/build_macos_sidecar.sh:9` | Reuse the actual sidecar/app build; do not invent a frontend build |

No unified production verifier exists. Its stage/report semantics are new and
must be established by tests; existing auth behavior is not a template for a
new auth implementation. No backend lint/type/coverage configuration was found
in `backend/pyproject.toml:1`. Source inspection is not a successful tool run.

# Files to Change

These are proposed implementation files. This planning commit changes only
SPEC.md, PLAN.md, docs/DEVELOPMENT_LOOP.md and HANDOFF.md.

| File | Action | Why / phase |
| --- | --- | --- |
| `backend/pyproject.toml` | UPDATE | Explicit dev-only check dependencies/configuration; Phase 1 |
| `backend/uv.lock` | UPDATE | Lock approved check tools after resolution; Phase 1 |
| `docs/VERIFICATION_BASELINE.md` | CREATE | Capture measured scope, exact commands and unresolved baseline issues; Phase 1 |
| `backend/tests/platform/test_verification_configuration.py` | CREATE | Test config/coverage policy with temporary fixtures; Phase 1 |
| `backend/core/verification.py` | CREATE | Pure evidence validation, stage ordering and report evaluation; Phase 2 |
| `backend/scripts/verify.py` | CREATE | Explicit CLI commands, exit status, bounded/redacted diagnostics; Phase 2 |
| `backend/tests/core/test_verification.py` | CREATE | Pure rule, boundary and formatting regressions; Phase 2 |
| `backend/tests/platform/test_verification_cli.py` | CREATE | CLI/subprocess/API integration on owned temporary fixtures; Phase 2 |
| `docs/VERIFICATION.md` | CREATE | Invocation, meaning of results, platform limits and resume instructions; Phase 3 |
| `.gitignore` | UPDATE | Ignore coverage/generated reports without hiding source or baseline evidence; Phase 3 |
| `SPEC.md`, `PLAN.md`, `HANDOFF.md` | UPDATE | Approval, phase/evidence and handoff status at each approved step |

DELETE: none. The original Phase 1 remains measurement-only. Proposed Phase 1b
below is the separate bounded remediation scope for the observed application
issues; the owner approved that scope on 2026-10-15. No native/hosted/mobile implementation change
or Phase 2 verifier is proposed in that scope.

# Tasks

## Phase 1 — Establish scope and expose baseline feasibility

Goal: measure what the proposed backend gate can honestly verify before
building a runner or claiming readiness. **Riskiest phase first.**

Dependencies: owner approves this plan and the proposed backend/native boundary.
Estimate: 3–5 hours. Status: baseline/config work complete; required full
verification FAILS, so no commit/release/Phase 2 (2026-10-12).

Evidence: original RED 14 failed/3 passed; additional policy RED 4 failed/16
passed; GREEN 20 passed. Full suite 497 passed; new test/scaffold coverage
97.50% lines, 80.77% branches. App baseline: build PASS, Pyright 22 errors,
Ruff 3 errors, full app 89.42% lines/77.33% branches (combined 86.62%), and
3 preexisting urllib3 advisories. See docs/VERIFICATION_BASELINE.md for exact
commands, all diagnostics, contextual security review and remaining scope.
Independent code review APPROVE, new-scope security findings zero; existing
package findings are separate. Changes remain uncommitted while gates are red.

Learned: combined coverage can pass while branch coverage fails; actual
coverage output must be configured under the ignored build directory rather
than relying on metadata alone. No baseline app fix was made.

1. **Action:** write RED configuration tests for declared Python version,
   check commands, coverage branch collection and separate line/branch floors.
   Exercise missing/invalid config, empty scope, thresholds 79.99/80/100,
   zero branch denominator and excluded/unexecuted source. **Mirror:** pure
   `describe_runtime` tests and temp fixtures. **Validate:** targeted command
   below must fail before adding policy/configuration.
2. **Action:** add dev-only Ruff, Pyright, coverage.py and pip-audit through uv;
   no runtime service or paid dependency. Declare full backend `api`/`core`
   coverage and a visible touched-code set, including unexecuted files. Never
   lower thresholds, disable diagnostics or exclude failing app modules to pass.
   The complete suite denominator is all `api`/`core` modules, approved
   with Phase 1; it is not narrowed to the new tests. **Mirror:**
   `pyproject.toml` dev group and locked uv dependencies. **Validate:** RED
   tests become GREEN; all existing backend tests still pass.
3. **Action:** run the actual build first, then full proposed type/lint/coverage
   baseline in order. Stop after failed build. Record first 30 type/lint
   diagnostics and complete counts without making application fixes. Explain
   missing tools and any tool download/network requirement. **Mirror:** existing
   sidecar build. **Validate:** commands below and baseline evidence; tool
   failures are real blockers, not fabricated passes.
4. **Action:** stop for remediation/scope decision if legacy errors make the
   next phase's required green checks impossible within this approved scope.
   **Mirror:** owner's report-before-fix rule. **Validate:** baseline states
   accurate outcomes and remaining questions.

Exact targeted RED/GREEN command, from `backend/`:

```bash
uv run pytest tests/platform/test_verification_configuration.py -q
```

Broader validation: `uv run pytest`, then declared type/lint checks after a
successful build. Phase tests unit-test policy parsing and integrate the real
project configuration with temporary report fixtures. Existing API/DB tests
remain part of every broader check: `uv run pytest
tests/auth/test_auth_security_audit.py tests/platform/test_local_runtime.py -q`.
They use synthetic accounts and temporary SQLite; no production DB needed.

Risks/open questions: legacy diagnostics; coverage denominator; whether zero
branches is not-applicable (all applicable branches covered) or requires an
additional policy; check-tool installation and advisory-service reachability.

## Phase 1b — Fix application blockers before adding verification automation

Goal: clear the measured backend gate with real robustness fixes, safe typing
and useful behavior tests, before writing any new verification runner.
**Status: COMPLETE — owner explicitly approved Phase 1b on 2026-10-15.**

Measured completion: the two behavior regressions showed 5 failed/19 passed,
then 24 passed; static RED was 22 type/3 lint errors. Final expanded type scope
including every changed test is 59 files, zero errors/warnings; Ruff zero.
582 tests pass, with 7 existing dependency deprecation warnings. Full application
coverage: 5560/6091 lines (91.28%), 1482/1834 branches (80.81%), combined 88.86%.
Each of the 12 changed production files independently exceeds both floors.
Configuration-test scaffold alone: 97.56% lines, 80.77% branches. Actual macOS
app/sidecar build and ad-hoc signature/arm64 checks pass; fresh pip-audit checks
85 installed packages with zero vulnerabilities. Only previously locked version
changed: urllib3 2.7.0 → 2.8.0. Three fresh OpenCode review slices approve with
zero findings, including a separate security assessment. Exact commands,
coverage table, review sessions and limits: docs/VERIFICATION_BASELINE.md.

Three broad OpenCode coding jobs timed out without edits; after the successful
bridge CLI recheck the coordinator implemented the fixes and used bounded
OpenCode test-generation/review packets. No native worker substitution. Brig's
`research-backend` index refreshed successfully after the source changes.
Learned: use exact branch counts, not rounded display percentages; 79.61%
displayed as 80 still failed policy, and useful upstream/error tests cleared it.

Dependencies: Phase 1 baseline captured; owner approves this specific application
and dependency remediation scope. Complexity Medium; estimate 4–8 hours,
excluding newly discovered failures. New unrelated failures are reported before
scope expansion. The earlier gate-runner estimate excludes this remediation.

Fresh independent OpenCode investigations on 2026-10-15 agree that most of the
22 diagnostics are annotation/narrowing issues, not 22 proven runtime bugs.
Two meaningful bugs were identified: article extraction crashes on an unmatched
heading end tag, and a source deleted between lookup and update can cause a 500.
Coordinator reproduced the first with synthetic `</h2><p>Notes</p>` input:
`TypeError` at `core/article.py:131`. Proposed user-visible improvements are
resilient URL imports and a proper missing-source response under that race.
Student usefulness beyond these behavior fixes remains unvalidated.

Freeze Phase 2 automation. Keep existing full `api`/`core` denominators, floor
80% for both lines and branches, and no diagnostic suppression/coverage omissions.
At the dated baseline denominator 1826, 49 additional branches would reach 80%;
new guards change that denominator, so actual success must be remeasured rather
than claiming a guaranteed +49. Do not add arbitrary/static tests for the score.

### Files to change and ownership after approval

| Files | Action / reason | Worker ownership |
| --- | --- | --- |
| `backend/api/coach.py`, `notebooks.py`, `sources.py`, `outlines.py`, `research.py`, `humanize.py` | UPDATE: preserve narrowed goal/name values; explicitly construct existing summary models; handle disappearing source; remove one unused import | API worker |
| `backend/core/article.py`, `parsers.py` | UPDATE: handle stray heading end tags; satisfy HTMLParser callback contract; use supported indexed PDF page access and preserve page numbering | Core worker |
| `backend/core/coach.py`, `classroom.py` | UPDATE: explicit JSON/local narrowing, preserve invalid-response fallback and expiry behavior | Core worker |
| `backend/core/store.py`, `webdiscovery.py` | UPDATE: accurate SQLite parameter-value union and remove two unused imports; no query/schema change | Core worker |
| `backend/tests/ingest/test_article.py`, `test_parsers.py` | UPDATE: malformed HTML, boolean attributes, PDF page numbering/text and parser-error behavior | Core worker |
| `backend/tests/api/test_api.py`, `test_notebook_title_alias.py`, `test_api_outlines.py`, `test_api_research.py`, `test_classroom.py` | UPDATE where needed: real temp-DB source race, response/alias contracts, expiry edge cases | API worker; coordinate classroom tests with core worker |
| `backend/tests/coach/test_coach.py`, `backend/tests/ingest/test_webdiscovery.py` | UPDATE: source-ID/field type boundaries and basic fallback; valid/invalid Discover filters and URL normalization preserve search behavior | Core worker |
| `backend/tests/auth/test_auth_google.py`, `test_auth_client_ip.py`, `backend/tests/ingest/test_fetcher.py`, `test_ingest_extraction.py` | UPDATE only for observed uncovered error/ownership/response-bound branches with meaningful observable behavior | Coordinator; no production changes from coverage work alone |
| `backend/uv.lock`, `backend/tests/platform/test_verification_configuration.py` | UPDATE: targeted urllib3 patch and locked-version safety regression; preserve all existing dev-tool work/tests | Coordinator |
| `PLAN.md`, `SPEC.md`, `HANDOFF.md`, `docs/VERIFICATION_BASELINE.md` | UPDATE: approval, dated evidence, learned line, actual files changed and current blocker status | Coordinator |

No deletion. No changes to `.serena/project.yml` (already modified independently),
user databases, auth ownership/storage schema, desktop/mobile interface, private
hosted repo, AI providers or paid services. No Phase 2 files. Existing staged
Phase 1 configuration/tests remain intact. Candidate test files above are an
upper bound, not permission for unrelated refactors or redundant new assertions.

### Ordered work (one bounded remediation phase)

1. **Action — RED:** add regressions that fail for stray/repeated heading closes
   while preserving subsequent paragraphs, and the real DB source-delete race
   between owned lookup and update. Use synthetic HTML/owned temporary SQLite;
   reproduce ordering deterministically rather than flaky threaded sleeps.
   Record the existing 22-error type check and 3-error lint check as the static
   RED oracle for annotation/import-only changes; do not invent behavioral tests
   that claim already-working validated aliases or integer SQLite values fail.
   **Mirror:** `tests/ingest/test_article.py`, authed temp-DB TestClient fixtures.
   **Validate:** targeted test commands below show the real failures before code.
2. **Action — GREEN:** apply minimal fixes. Keep goal/name in narrowed locals;
   preserve NotebookCreate's existing title/name/null validation contract. Use
   `SourceSummary.model_validate` where response models already validate dicts.
   Return 404 if source update reports missing data. Fix parser state handling
   and callback signature without broad extraction redesign. Narrow AI JSON
   fields explicitly, preserving supported grounding and basic fallback. Match
   SQLite values with `str | int | None`, not a new Any escape hatch. Preserve
   PDF page numbers/text and expiry fallback; remove only the three unused names.
   **Mirror:** existing ownership/error guards and model validation.
   **Validate:** failing behavior tests turn green, Pyright/lint become clean.
3. **Action — dependency RED/GREEN:** first add a real lock/resolved-version
   regression rejecting affected urllib3 versions. Then use
   `uv lock --upgrade-package urllib3`, inspect the exact delta, and `uv sync
   --locked`; accept a patched compatible release (known fix >=2.8.0), not an
   unrestricted dependency refresh. Do not force unrelated upgrades or override
   constraints silently. This is a runtime transitive dependency change and
   requires fresh packaging plus pip-audit. Update no direct provider/service.
   **Mirror:** existing version/config policy tests and hash-locked uv workflow.
   **Validate:** regression initially fails, passes after patch; fresh audit has
   zero known findings for the approved environment, otherwise report blockers.
4. **Action — meaningful branch tests:** start with uncovered malformed/bounded
   fetch responses, redirect/empty-body fallback, goal/task errors, account
   isolation and malformed optional-AI fields. Mock HTTP/DNS/advisories, use
   real temporary SQLite for API integration. Boundary cases include empty,
   missing/invalid fields, bool-versus-integer IDs, Unicode source text, limit
   boundaries and cancellation/race outcomes where supported. Each test asserts
   an observable result; no static source-code bans or private helper arithmetic
   simply to raise scores. A new failing behavior beyond this phase's described
   contracts is reported before adding a production fix.
   **Mirror:** existing fetcher and coach/ownership fixtures.
   **Validate:** full suite and exact JSON line/branch denominators; no floors
   lowered, modules omitted, tests deleted/skipped or new exclusions introduced.
5. **Action — REFACTOR/review/verify:** remove only duplication introduced in this
   phase while green. Independent fresh reviewer reads full changed files plus
   callers/tests, severity table and verdict. A separate OpenCode security audit
   reports before any follow-up fixes. Run actual build first, then types, lint,
   full branch-coverage tests, dependency/contextual source audit and diff. Stop
   after failed build. Missing/incomplete evidence is not PASS. Commit only with
   required gates green and reviewer approval; do not deploy. Save each logical
   change with conventional prefixes, exact results and manual reproduction.

### Exact targeted commands (from backend)

```bash
uv run pytest tests/ingest/test_article.py tests/ingest/test_parsers.py -q
uv run pytest tests/api/test_api.py tests/api/test_notebook_title_alias.py tests/api/test_api_outlines.py tests/api/test_api_research.py tests/api/test_classroom.py -q
uv run pytest tests/coach/test_coach.py tests/auth/test_auth_google.py tests/auth/test_auth_client_ip.py tests/ingest/test_fetcher.py tests/ingest/test_ingest_extraction.py -q
uv run pytest tests/platform/test_verification_configuration.py -q
uv run pyright
uv run ruff check core api scripts tests/platform/test_verification_configuration.py
```

Also pass every actually changed test file explicitly to Pyright and Ruff; the
original profile includes only the original configuration test and is not
evidence that new remediation tests were checked. Use the final changed-file
list, not unrelated tests or the candidate upper bound. Add selected Discover
regressions with `uv run pytest tests/ingest/test_webdiscovery.py -q`.

Then use the full ordered Validation commands below; add no future CLI invocation
before the Phase 2 implementation exists. Collect full-source and touched-file
coverage separately; touched production files require >=80% lines AND branches,
not just the whole-backend combined score. Missing touched-file floors remain
explicit blockers rather than hidden in aggregate coverage.

### Risks / acceptance

| Risk | Mitigation |
| --- | --- |
| Typing cleanup changes previously accepted request shapes | Freeze alias/null/response/SQLite contracts in current integration tests; no schema rewrite |
| Overbroad parser error swallowing loses content | Handle only the missing-heading state and test preserved later paragraphs/valid metadata |
| Patch resolver changes unrelated runtime packages | Inspect version delta; stop rather than accepting unrelated churn |
| Branch tests pass the score without useful protection | Review observable effects and exact denominator; retain every module |
| Fresh agents suggest Any/casts or static grep tests for convenience | Reject those suggestions; use real narrowing, explicit SQL value types and behavior tests |
| Large touched files need more than the aggregate floor | Measure touched-file floors explicitly and report remaining gaps honestly |

- [x] Owner explicitly approved Phase 1b (`Yes—implement Phase 1b`, 2026-10-15).
- [x] Real bug regressions show RED before minimal fixes; static RED retained.
- [x] Pyright 0, Ruff 0; API/alias/response/ownership contracts preserved.
- [x] Compatible patched urllib3 locked; no unrelated runtime upgrades.
- [x] All tests pass; full and touched-code line/branch floors meet approved policy.
- [x] Independent review and security audit complete; full gate green before commit.
- [x] PLAN/SPEC/HANDOFF and dated evidence updated; no deployment implied.

## Phase 2 — Implement a truthful ordered gate

Goal: expose deterministic reports that cannot turn missing or failing evidence
into READY. Dependencies: Phase 1 complete and its blocking scope/tool decisions
resolved. Estimate: 5–8 hours. Status: pending, not started.

1. **Action:** write RED unit tests for every stage failure, missing tools,
   not-run/cancelled/timed-out stages, malformed output, empty suite, absent
   coverage, integer/boolean/type confusion, NaN/out-of-range percentages,
   count mismatches, null fields, large diagnostics and special-character paths.
   Cover combined and separate line/branch percentage failures. **Mirror:**
   typed pure logic under `core`. **Validate:** both new test commands fail
   before implementation.
2. **Action:** implement minimal pure evidence/report logic and a CLI adapter.
   Command selection is a fixed reviewed allowlist; no arbitrary shell command
   input, shell concatenation or secret-bearing arguments. Only owned processes
   may be stopped. A build failure stops subsequent stages. Keep measured zeros
   distinct from unknown values. Proposed unknown convention: stage FAIL,
   numeric field `unknown`, reason in numbered issues; approval of this plan
   confirms that convention within the owner's fixed PASS/FAIL format.
   **Mirror:** existing explicit error paths and bounded runtime facts.
   **Validate:** unit/CLI tests become GREEN.
3. **Action:** integration-test subprocess behavior with temporary executables
   and controlled outputs, including large streams, interrupts and concurrent
   invocations. Exercise API readiness with a real TestClient and temporary
   SQLite account; fake advisory/API/AI dependencies only, never live accounts.
   Verify argv handling for spaces, Unicode and shell metacharacters.
   **Mirror:** existing temp DB and owned-process tests. **Validate:** CLI
   exit/report, no orphan child and no changes outside owned temporary paths.
4. **Action:** test security scan handling with synthetic secrets, placeholders,
   public values and test fixtures. Report path/rule/line and redacted evidence;
   never print raw matching values. Review distinguishes contextual findings
   from raw grep matches; no claim that grep is an OWASP audit. A dependency
   advisory fetch failure is incomplete verification, not a clean audit.
   **Mirror:** metadata-only logging. **Validate:** no synthetic credential
   appears in captured reports/stdout/stderr.
5. **Action:** refactor duplication while all tests remain green. Run the full
   declared checks and independent review/security audit before committing.
   **Validate:** separate line and branch coverage are each >=80 on all new
   verifier source; show full backend coverage separately without changing its
   denominator. If declared app gates fail, stop and report for authorization.

Exact targeted commands, from `backend/`:

```bash
uv run pytest tests/core/test_verification.py tests/platform/test_verification_cli.py -q
uv run coverage run --branch --source=core,api -m pytest
uv run coverage json -o .verification-coverage.json
uv run coverage report --fail-under=80
uv run pyright
uv run ruff check core api scripts/verify.py tests/core/test_verification.py tests/platform/test_verification_cli.py
```

Important: `coverage report --fail-under=80` is the combined reported threshold;
the implementation must separately inspect line and branch totals per declared
scope. That command alone does not prove two separate 80% floors. No E2E user
flow is introduced; API/CLI integration is required, native runtime validation
remains a separate gate.

## Phase 3 — Close the review and resume loop

Goal: a maintainer can resume the correct approved phase and assess a candidate
without mistaking local evidence for release approval. Dependencies: Phase 2
and independent review/security findings resolved or explicitly blocking.
Estimate: 2–3 hours. Status: pending, not started.

1. **Action:** document exact invocations and platform capability limits, artifact
   locations, approval/evidence state, and how to reproduce a seeded failed
   command using temporary fixtures. **Mirror:** Windows README's compile-versus-
   runtime distinction. **Validate:** link/command consistency and diff check.
2. **Action:** give a fresh OpenCode reviewer SPEC/PLAN/diff only; require complete
   changed-file and caller/test reads, confidence >80% and severity table/verdict.
   Give a separate security reviewer dependency/source evidence and enforce
   report-before-fix. **Validate:** saved reports; no unresolved critical
   findings; fixes only in authorized phases.
3. **Action:** run the complete declared verification order, then record spec
   demoability, phase completion, critical flows, migration/rollback,
   monitoring/alerts and docs as PASS/FAIL/N/A with reasons. No application data
   migration is proposed; no deploy authority or alert system is assumed.
   **Validate:** measured verification report and explicit release blockers.
4. **Action:** update statuses, one learned line per completed phase and HANDOFF's
   shipped/pending/next three actions/resume commands. Commit per logical feature
   only after independent approval and required green checks. **Validate:**
   `git diff --check`, reviewed commit and accurate next-session instructions.

Docs-only Phase 3 changes use `git diff --check` plus consistency greps; app
checks belong to the release verification stage, not tests invented for prose.

# Validation

These are proposed commands for approved implementation, **not evidence of
execution on 2026-10-12**. Install/configuration happens only in approved Phase 1.
The CLI described below does not exist yet.

```bash
# From repository root: Phase 1 build, stop the gate immediately on failure.
sh backend/scripts/build_macos_sidecar.sh

# From backend/, only after build succeeds:
uv run pyright
uv run ruff check core api scripts tests/platform/test_verification_configuration.py
# Phase 1b also explicitly checks each changed test listed in its evidence table.
uv run coverage run --branch --source=core,api -m pytest
uv run coverage json -o build/verification/coverage.json
uv run coverage report --fail-under=80
# Read JSON to enforce independent line and branch floors on declared scopes.
uv run pip-audit --local
# Audit runtime dependencies separately; dev-only packages are not hosted services.
# After Phase 2 exists: separately run context-aware scanning for the audit.
uv run scripts/verify.py --security-only
# This scan-only mode never emits overall READY or substitutes for the full gate.

# From repository root: diff stage.
git diff --stat
git diff --check

# Proposed end-to-end gate invocation after Phase 2 exists, from backend/:
uv run scripts/verify.py

# Native checks are additional evidence when approving native release scope.
# A failed build stops the corresponding native gate.
sh scripts/build_macos_app.sh
# Uses the locally available portable SDK on this machine:
/private/tmp/notaeo-dotnet-sdk/dotnet build windows/Research/Research.csproj -c Release
/private/tmp/notaeo-dotnet-sdk/dotnet test windows/Research.Tests/Research.Tests.csproj
# Windows runtime/DPAPI/packaged sidecar/installer evidence requires Windows.
# No claim that cross-targeted compilation substitutes for those checks.
```

The backend build packages a local arm64 sidecar, not a notarized release. The
macOS app build is ad-hoc signed. Windows compilation/tests here do not create a
signed Windows distribution. Live hosted TLS, migration recovery, monitoring and
release identity remain separate unverified prerequisites. No verification run
may silently modify code or perform deployment.

Chosen check-tool references: [Ruff configuration](https://docs.astral.sh/ruff/configuration/),
[Pyright configuration](https://microsoft.github.io/pyright/#/configuration),
[coverage branch measurement](https://coverage.readthedocs.io/en/latest/branch.html),
[pip-audit](https://pypi.org/project/pip-audit/). These are plan choices, not installed dependencies.

# Risks

| Risk | Evidence / impact | Mitigation / open decision |
| --- | --- | --- |
| Baseline type/lint/coverage blockers expand scope | No current configuration; actual diagnostics unmeasured | Phase 1 first; report, do not disable or mass-fix |
| Platform-specific checks unavailable | Windows runtime not available on macOS | Keep native runtime release-blocking; never call it PASS |
| Missing numeric evidence conflicts with fixed report placeholders | Build failure stops later stages | Proposed `unknown` fields and numbered not-run reasons; plan approval confirms |
| Coverage is overstated | Combined line/branch score differs from separate floors | Inspect JSON denominators and include unexecuted declared files |
| Dependency audit unavailable/offline | Advisory network required for fresh results | Report incomplete; no empty-clean fallback |
| Scan output exposes private values | Grep can match real credentials | Synthetic tests, bounded/redacted output, context-aware review |
| Review/code context drifts | Brig root duplicate-symbol index failure; worker index may differ | Fresh backend slug plus verified source refs; save context in docs |

# Acceptance checklist

- [x] One-round interview offered; owner waived it, no user evidence fabricated.
- [x] Root Brig backend index refreshed and compact outlines retrieved.
- [x] OpenCode planning agent inspected real source patterns.
- [x] Independent OpenCode planning review: APPROVE, zero findings (2026-10-12).
- [x] Owner approved plan, backend boundary and unknown-value convention (`yes`, 2026-10-12); Phase 1 only.
- [x] Phase 1 baseline/policy tests and evidence collected; full verification blocked by recorded existing issues, not accepted for release.
- [ ] Phase 2 ordered report/CLI passes RED→GREEN and unit/API/CLI integration.
- [ ] Separate >=80% line and branch coverage verified on approved touched code.
- [x] Full declared suite scope (`api`/`core`, all modules) approved and reported accurately; branch floor FAILS.
- [ ] Review reads full changed files and ends with severity counts/verdict.
- [ ] Security audit reports contextual findings, rotation decision and top fixes.
- [ ] Mandatory scoped build/types/lint/tests/security/diff checks measured.
- [ ] Pre-launch controls and platform runtime evidence actually verified.
- [ ] Handoff and phase lessons saved; no unresolved critical finding shipped.

Learned during planning: root Brig retrieval requires explicit
`slug="research-backend"`; an OpenCode worker reported that slug unavailable in
its own index. Supply compact verified outlines to workers rather than claiming
shared conversation memory or identical index visibility.
