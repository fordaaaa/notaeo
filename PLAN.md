# Summary

Feature: proposed production verification gate. SPEC.md is the requirements
source. Interview waived by the owner on 2026-10-12 because the app has not been
tested enough to provide evidence. Product assumptions remain unvalidated.

**Status: DRAFT — awaiting explicit owner approval; no implementation authorized.**
Approval of this plan permits Phase 1 only. Later phases require the owner to
name the phase or explicitly authorize the remaining phases. A request to
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
new student features stay outside this plan. This boundary is a proposal for
approval, not evidence of owner interview answers.

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

DELETE: none. No baseline API/auth/store/native implementation changes are
planned. Fixes to existing issues need their own approved scope; a failing
baseline is reported, not silenced or refactored away.

# Tasks

## Phase 1 — Establish scope and expose baseline feasibility

Goal: measure what the proposed backend gate can honestly verify before
building a runner or claiming readiness. **Riskiest phase first.**

Dependencies: owner approves this plan and the proposed backend/native boundary.
Estimate: 3–5 hours. Status: pending, not started.

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
   The complete suite denominator remains pending scope approval. **Mirror:**
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
uv run ruff check core api scripts tests
uv run coverage run --branch --source=core,api -m pytest
uv run coverage json -o .verification-coverage.json
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
- [ ] Owner explicitly approves plan, backend boundary and unknown-value convention.
- [ ] Phase 1 baseline/policy tests and evidence complete.
- [ ] Phase 2 ordered report/CLI passes RED→GREEN and unit/API/CLI integration.
- [ ] Separate >=80% line and branch coverage verified on approved touched code.
- [ ] Full declared suite coverage scope approved and reported accurately.
- [ ] Review reads full changed files and ends with severity counts/verdict.
- [ ] Security audit reports contextual findings, rotation decision and top fixes.
- [ ] Mandatory scoped build/types/lint/tests/security/diff checks measured.
- [ ] Pre-launch controls and platform runtime evidence actually verified.
- [ ] Handoff and phase lessons saved; no unresolved critical finding shipped.

Learned during planning: root Brig retrieval requires explicit
`slug="research-backend"`; an OpenCode worker reported that slug unavailable in
its own index. Supply compact verified outlines to workers rather than claiming
shared conversation memory or identical index visibility.
