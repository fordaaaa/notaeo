# Verification baseline — 2026-10-12

Historical baseline below. The approved 2026-10-15 Phase 1b remediation and
current green local backend result are recorded at the end of this document.

Scope: approved Phase 1 only, public backend. Source baseline is commit
`f93d8fb` plus the Phase 1 config/test changes in this working tree. No app
API/core source, native interface, hosted/mobile repo or real database changed.
These are measured local results, not production certification. Application
source coverage uses all `core` and `api`, including unexecuted declared files.
The owner waived the interview; product outcomes remain assumptions.

## Result

VERIFICATION REPORT — Build: PASS, Types: FAIL (22), Lint: FAIL (3), Tests: FAIL (497/497, 86.62%), Security: FAIL (3), Diff: (7 files). Overall: NOT READY. Issues to fix (numbered).

1. Twenty-two existing app type errors; none remain in the new config tests.
2. Three existing F401 unused imports fail the declared lint policy.
3. Full app branch coverage is 77.33%, below the independent 80% floor.
4. Previously locked urllib3 2.7.0 has three known advisories; fixes listed at 2.8.0.
5. Required gates are not green: Phase 1 changes remain uncommitted, no release
   or Phase 2 implementation. App remediation requires separate authorization.

## RED → GREEN and refactor evidence

Worker's original missing-policy regression: `14 failed, 3 passed in 0.69s`,
then `17 passed`. Coordinator regressions for actual coverage output path,
explicit rules/workdirs and declaration-only future scope: `4 failed, 16 passed`,
then `20 passed`. No test was skipped, disabled or deleted. Future-file checks
now validate scope declarations instead of permanently forbidding valid later
implementation. Test scaffold uses object narrowing instead of new Any types;
duplicate unreachable NaN checks were removed without removing test coverage.
Three diagnostics introduced during that test-only typing refactor were fixed;
remaining type diagnostics are in unchanged application files.

Final full suite: `497 passed, 7 warnings in 63.81s`; no failed/skipped tests.
New module coverage is test/scaffold coverage, not production verifier coverage:
273/280 lines (97.50%) and
42/52 branches (80.77%).
Phase 2 verifier implementation is still absent.

## Build and tools

`sh backend/scripts/build_macos_sidecar.sh` ran from repository root and exited 0.
It built the real PyInstaller sidecar. It is not the complete signed/notarized
native release gate, and does not prove Windows runtime or live hosted TLS.
Python used: 3.12.13, through uv (no system python3).

| Dev-only tool | Installed version |
| --- | --- |
| ruff | 0.17.0 |
| pyright | 1.1.414 |
| coverage | 7.16.2 |
| pip-audit | 2.10.1 |

Runtime dependency declarations and versions of previously locked packages are
unchanged. New dependencies are development checks and their transitive tools.

## Ordered baseline commands and exit status

Run build from root. After it passed, run checks from `backend/`, in this order.
A failed type/lint/test/security check was recorded, not automatically fixed;
only a failed build would stop subsequent stages. Outputs live in ignored
build/verification or temporary logs, never student data directories.

| Stage | Actual command | Exit | Evidence |
| --- | --- | --- | --- |
| Build | `sh backend/scripts/build_macos_sidecar.sh` | 0 | `/tmp/notaeo-phase1-build.log` |
| Types | `uv run pyright --outputjson` | 1 | `/tmp/notaeo-phase1-pyright.json` |
| Lint | `uv run ruff check core api scripts tests/platform/test_verification_configuration.py --output-format=json` | 1 | `/tmp/notaeo-phase1-ruff.json` |
| Tests | `uv run coverage run --branch --source=core,api -m pytest` | 0 | `/tmp/notaeo-phase1-tests.log` |
| Coverage JSON | `uv run coverage json -o build/verification/coverage.json` | 0 | `backend/build/verification/coverage.json` |
| Combined floor | `uv run coverage report --fail-under=80` | 0 | `/tmp/notaeo-phase1-coverage.log` |
| Separate floors | Inspect measured JSON totals: lines >=80 AND branches >=80 | FAIL | Exact denominators below; no automated gate exists yet |
| Dependencies | `uv run pip-audit --local --format=json --output build/verification/pip-audit.json` | 1 | `backend/build/verification/pip-audit.json` |
| Source scan | Contextual tracked-source scan; prints rule/path/line, not values | Complete | `backend/build/verification/security-scan.json` |
| Diff | `git diff HEAD --stat`; `git diff --cached --check`; `git diff --check` | 0 | Seven declared phase/config/docs files; no runtime code change |

The final diff contains SPEC.md, PLAN.md, HANDOFF.md,
docs/VERIFICATION_BASELINE.md, backend/pyproject.toml, backend/uv.lock and
backend/tests/platform/test_verification_configuration.py. Git diff before
staging omits untracked files; final review must include staged contents too.

## Types — all diagnostics (under the first-30 cap)

| Location, relative to backend | Diagnostic first line |
| --- | --- |
| `api/coach.py:51` | Argument of type "ExamGoal  /  None" cannot be assigned to parameter "goal" of type "ExamGoal" in function "build_session" |
| `api/notebooks.py:22` | Argument of type "str  /  None" cannot be assigned to parameter "name" of type "str" in function "create_notebook" |
| `api/outlines.py:242` | Argument of type "dict[Unknown, Unknown]" cannot be assigned to parameter "source" of type "SourceSummary" in function "__init__" |
| `api/research.py:135` | Argument of type "dict[Unknown, Unknown]" cannot be assigned to parameter "source" of type "SourceSummary" in function "__init__" |
| `api/sources.py:144` | Argument of type "Source  /  None" cannot be assigned to parameter "source" of type "Source" in function "_summary" |
| `core/article.py:79` | Method "handle_starttag" overrides class "HTMLParser" in an incompatible manner |
| `core/article.py:131` | No overloads for "join" match the provided arguments |
| `core/article.py:131` | Argument of type "list[str]  /  None" cannot be assigned to parameter "iterable" of type "Iterable[str]" in function "join" |
| `core/classroom.py:169` | Argument of type "Unknown  /  None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" |
| `core/classroom.py:169` | Argument of type "Unknown  /  None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__" |
| `core/coach.py:119` | Argument of type "tuple[Unknown  /  None, Unknown]" cannot be assigned to parameter "key" of type "tuple[str, int]" in function "get" |
| `core/coach.py:126` | Argument of type "Unknown  /  None" cannot be assigned to parameter "obj" of type "Sized" in function "len" |
| `core/coach.py:126` | Argument of type "Unknown  /  None" cannot be assigned to parameter "obj" of type "Sized" in function "len" |
| `core/coach.py:126` | Argument of type "Unknown  /  None" cannot be assigned to parameter "obj" of type "Sized" in function "len" |
| `core/coach.py:128` | "split" is not a known attribute of "None" |
| `core/coach.py:130` | Argument of type "Unknown  /  None" cannot be assigned to parameter "value" of type "str" in function "_topic" |
| `core/coach.py:132` | Argument of type "Unknown  /  None" cannot be assigned to parameter "value" of type "str" in function "_topic" |
| `core/coach.py:133` | "strip" is not a known attribute of "None" |
| `core/coach.py:133` | "strip" is not a known attribute of "None" |
| `core/coach.py:133` | "strip" is not a known attribute of "None" |
| `core/parsers.py:62` | Argument of type "open" cannot be assigned to parameter "iterable" of type "Iterable[_T@enumerate]" in function "__new__" |
| `core/store.py:772` | Argument of type "Literal[1, 0]" cannot be assigned to parameter "value" of type "str" in function "__setitem__" |

No Pyright warnings. New config-test file has zero diagnostics. Declared scope:
core, api, scripts and the new policy tests. No application files were excluded
or diagnostic rules disabled to make the result pass.

## Lint — all diagnostics

| Location, relative to backend | Diagnostic |
| --- | --- |
| `api/humanize.py:8` | F401 — `api.deps.get_store` imported but unused |
| `core/store.py:15` | F401 — `datetime.timezone` imported but unused |
| `core/webdiscovery.py:12` | F401 — `urllib.parse.urlunsplit` imported but unused |

Ruff rule families: E4, E7, E9, F, explicit py312 target, no ignore list.
No lint diagnostic in the new test/scaffold file.

## Coverage — exact declared denominator

49 `core`/`api` files. Statements: 5433/6076 =
89.42%. Branches: 1412/1826 =
77.33%. Combined: 86.62%.
Existing exclusions: 22 lines under coverage's existing/default pragma
handling, no new omit/exclude configuration. The combined PASS is insufficient
because the independent branch floor fails. Do not narrow scope or lower floors.

The new configuration test's separate supplemental coverage command was:
`uv run coverage run --branch --source=tests/platform --data-file=build/verification/configuration.coverage -m pytest tests/platform/test_verification_configuration.py -q`,
then JSON extraction of that file only. That test/scaffold metric is separately
labelled and does not replace the full app denominator above.

## Dependency advisories

| Package | Advisory | Reported fixed version |
| --- | --- | --- |
| urllib3 2.7.0 | PYSEC-2026-4177 / GHSA-vxq7-64xx-v4gw, CVE-2026-97689 | 2.8.0 |
| urllib3 2.7.0 | PYSEC-2026-4176 / CVE-2026-97688, GHSA-gh4c-6fx4-qh6g | 2.8.0 |
| urllib3 2.7.0 | PYSEC-2026-4175 / GHSA-8988-9cw3-xx77, CVE-2026-97687 | 2.8.0 |

`urllib3` was already 2.7.0 in HEAD before Phase 1; this change exposed the issue
rather than introducing a runtime version upgrade/downgrade. Advisory presence
is confirmed; applicability to each deployed request/proxy path is not proven
by package presence. No live exploit was attempted. Upgrade/remediation has not
been performed because Phase 1 only authorizes measurement/configuration.

Primary maintainer references:
[unbounded chunk header](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw),
[Deflate streaming loop](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g),
[HTTPS proxy TLS policy](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77).

## Contextual source scan and limits

Zero key-like secret values, HTML sink matches or unticketed TODO/FIXME matches
in the inspected tracked code. Candidate api_key occurrences are removal/
migration fixtures, console.log is a website-removal test asset, SQL interpolation
is an allowlisted synthetic migration-test column, URL fetch matches are crawler
fakes, and the apparent password comparison is a native URL-userinfo guard.
These candidate matches alone are not security findings. Matching values were
not printed. This scan is not a full secret detector or penetration test.

Independent code review: APPROVE, zero findings. Independent security review:
new Phase 1 findings CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0. Existing dependency
findings separately classified CRITICAL 0 / HIGH 1 / MEDIUM 2 / LOW 0; package
advisory impact is conditional and deployed reachability is not established.

| Existing finding at `backend/uv.lock:1652-1653` | Scenario and guard limit | Proposed safe fix |
| --- | --- | --- |
| HIGH — GHSA-8988-9cw3-xx77 | An affected HTTPS forwarding-proxy configuration can apply a target TLS policy to the proxy, permitting interception. No such app configuration was found in the inspected source. | Locked urllib3 >=2.8.0; separate proxy TLS policy with verification enabled; re-test packaging/audit |
| MEDIUM — GHSA-vxq7-64xx-v4gw | A malicious chunked server response can exhaust memory while affected urllib3 streaming buffers an unterminated size line. App fetches use httpx and byte caps; an affected transitive path was not demonstrated. | Locked patched version; preserve bounded real-response ingestion tests |
| MEDIUM — GHSA-gh4c-6fx4-qh6g | An affected decoded Deflate stream with trailing bytes can loop without another network read, so a socket timeout does not bound CPU. App usage of that urllib3 path was not demonstrated. | Locked patched version; test compressed-response termination/bounds if that path is introduced |

Top risk-ranked actions: (1) approve a patched dependency update, treating it as
an actual runtime dependency change and re-running audit/packaging; (2) address
the 22 type errors and 3 unused imports with behavior-preserving tests; (3) add
meaningful tests for uncovered application branches until the independent 80%
floor passes. No scan-only assertions that ban a library replace behavior tests.
OWASP assessment is limited to changed config plus inspected auth/store/fetch
context; full access-control/cryptography/injection, operational monitoring,
actual proxy settings and live SSRF resistance were not comprehensively tested.
Final independent review supplement: APPROVE, zero findings in new scope;
release remains BLOCKED by the recorded existing gate failures. Live
secrets, production databases, actual Windows/native mobile runtime, hosted
configuration and existing broader DNS/abuse risks were not revalidated here.
No credential exposure was found in the inspected tracked-code scan; no
rotation is indicated by that limited evidence. No application release is READY.

## Manual reproduction / next action

From backend, `uv run pytest tests/platform/test_verification_configuration.py -q`
reproduces 20 passing policy tests. Then reproduce the commands above in order;
inspect exact coverage denominators rather than trusting the combined score.
Open questions: approve separate remediation scope for type/lint issues,
missing branch tests and the dependency update; then re-run the complete gate.
Do not start Phase 2 or deploy from a passing subset of checks.

## Approved remediation result — 2026-10-15

Owner explicitly approved `Yes—implement Phase 1b`. Implemented that bounded
scope, preserving the earlier Phase 1 configuration/tests. The following result
supersedes the dated baseline failures above; it does not implement the proposed
automated verifier or authorize an application release.

VERIFICATION REPORT — Build: PASS, Types: PASS (0), Lint: PASS (0), Tests: PASS (582/582, 88.86%), Security: PASS (0), Diff: (27 files). Overall: READY. Issues to fix (numbered).

1. No blocking issue remains in the approved local backend remediation scope.
   READY refers to this reviewed change, not a complete production release.
2. Phase 2 remains unapproved and unimplemented. Native runtime E2E, Windows
   packaging/runtime, notarization, hosted operations and release monitoring
   have not been validated by this backend milestone.

### Behavior fixes and RED/GREEN evidence

Malformed or repeated heading closes now preserve following valid paragraphs
instead of raising TypeError. An owned source deleted between lookup and update
returns 404 rather than a 500. Four malformed-HTML cases plus a deterministic
real temporary-SQLite deletion race showed **5 failed/19 passed** before the
fixes, then **24 passed**. Logs: `/tmp/notaeo-phase1b-behavior-red.log` and
`/tmp/notaeo-phase1b-behavior-green.log`.

The existing **22 type/3 lint** failures were retained as the static RED oracle
for annotation/import-only changes; no pretend failing behavior test was added
for previously working aliases or SQLite integers. PDF text uses indexed pages
and the equivalent default text flags, retaining page numbering/text. Explicit
JSON narrowing retains basic coach fallback. Existing alias/null, parser,
outline/research and classroom contracts passed a targeted **65-test** run.

The real locked-version safety regression showed **1 failed/20 passed** with
urllib3 2.7.0, then **21 passed** with 2.8.0. Comparing HEAD's previously locked
packages to the final lock confirms urllib3 is the only version changed; new
Phase 1 dev tools remain. Dependency logs: `/tmp/notaeo-phase1b-dependency-red.log`
and `/tmp/notaeo-phase1b-dependency-green.log`.

New behavior tests cover invalid optional-AI fields, missing coach goal/task,
outline draft/report upstream fallback and selected-source isolation, malformed
search-result URLs and Unicode/tracking deduplication, bounded HTML bodies,
redirect/status errors, structured extraction fallback, tokeninfo claim/errors,
and Classroom expiry/token/API errors. External HTTP and AI are synthetic; API
integration uses real temporary owned SQLite. No tests were skipped, disabled
or deleted. Previously unused test fixtures now have real deduplication
assertions; touched-test optional-source assumptions are explicit assertions.

### Ordered verification and exact evidence

Build ran first and passed. Final types, lint and full test run then passed,
followed by coverage inspection, dependency/source audit and diff checks.
The earlier 554-test coverage exploration was not the final gate: its actual
branch result was 79.61%, despite the rounded display of 80, and was rejected.

| Stage | Actual command / scope | Result / artifact |
| --- | --- | --- |
| Build, from root | `sh scripts/build_macos_app.sh` | exit 0; `/tmp/notaeo-phase1b-build.log`; PyInstaller sidecar + Xcode Release + ad-hoc signature/deep verification + arm64 check |
| Types, backend | `uv run pyright core api scripts tests/platform/test_verification_configuration.py tests/api/test_api.py tests/api/test_api_outlines.py tests/api/test_classroom.py tests/auth/test_auth_google.py tests/coach/test_coach.py tests/ingest/test_article.py tests/ingest/test_fetcher.py tests/ingest/test_webdiscovery.py --outputjson` | exit 0; 59 files, 0 errors/warnings; `/tmp/notaeo-phase1b-types.json` |
| Lint, backend | `uv run ruff check core api scripts tests/platform/test_verification_configuration.py tests/api/test_api.py tests/api/test_api_outlines.py tests/api/test_classroom.py tests/auth/test_auth_google.py tests/coach/test_coach.py tests/ingest/test_article.py tests/ingest/test_fetcher.py tests/ingest/test_webdiscovery.py` | exit 0; `/tmp/notaeo-phase1b-lint.log` |
| Full tests | `uv run coverage run --branch --source=core,api -m pytest` | exit 0; **582 passed**, 7 existing deprecation warnings, 68.80s; `/tmp/notaeo-phase1b-tests.log` |
| Coverage JSON | `uv run coverage json -o build/verification/phase1b-coverage.json` | exit 0; full api/core, no new exclusions |
| Combined floor | `uv run coverage report --fail-under=80` | exit 0; `/tmp/notaeo-phase1b-coverage.log` |
| Separate floors | Inspect unrounded JSON totals and each changed production file against 80% lines AND 80% branches | PASS all 13 scopes; `backend/build/verification/phase1b-coverage-floors.json`; one-off inspection, no Phase 2 runner |
| Dependency audit | `uv run pip-audit --local --format json --output build/verification/phase1b-pip-audit.json` | exit 0; 85 packages, 0 vulnerabilities; `/tmp/notaeo-phase1b-audit.log` |
| Contextual scan | Read-only metadata-only patterns over tracked backend api/core/scripts | 51 files, 0 candidates for key-like literals, browser logs/sinks, unticketed markers, unsafe execution/TLS patterns; `phase1b-security-scan.json` |
| Diff, root | `git diff HEAD --stat`; `git diff --cached --check`; `git diff --check` | PASS; 27 intended files, plus unrelated `.serena/project.yml` excluded from the commit |

Configuration scaffold measured separately with
`uv run coverage run --branch --source=tests/platform --data-file=build/verification/.coverage-configuration -m pytest tests/platform/test_verification_configuration.py -q`
and
`uv run coverage json --data-file=build/verification/.coverage-configuration --include=tests/platform/test_verification_configuration.py -o build/verification/phase1b-configuration-coverage.json`.
Result: 21 tests, **280/287 lines (97.56%)**, **42/52 branches (80.77%)**.
This supplemental file-only denominator does not replace application coverage.
The first supplemental export included unexecuted, unrelated platform tests and
returned exit 2 at 44%; the corrected export explicitly measures the declared
scaffold only. No application scope, exclusions or threshold changed.

### Coverage floors

Full api/core: **5560/6091 lines (91.28%)**, **1482/1834 branches (80.81%)**,
combined **88.86%**. The 22 existing/default excluded lines remain unchanged;
no new exclusion or omit rule was introduced.

| Changed production file, relative to backend | Lines | Branches |
| --- | ---: | ---: |
| api/coach.py | 100.00% | 100.00% |
| api/humanize.py | 97.67% | 83.33% |
| api/notebooks.py | 100.00% | 100.00% |
| api/outlines.py | 98.75% | 93.75% |
| api/research.py | 97.80% | 90.00% |
| api/sources.py | 98.36% | 93.33% |
| core/article.py | 97.62% | 91.38% |
| core/classroom.py | 98.75% | 93.75% |
| core/coach.py | 93.86% | 85.85% |
| core/parsers.py | 91.07% | 88.89% |
| core/store.py | 92.64% | 81.55% |
| core/webdiscovery.py | 86.89% | 84.62% |

### Fresh independent reviews and context

All use `opencode/muse-spark-1.3-contributor-free` at xhigh through the bridge.
Each received actual scoped diffs, full changed files and caller/test context;
the code reviewers also received SPEC/PLAN. They made no edits.

| Review | Session | Verdict / findings |
| --- | --- | --- |
| API + coach | `ses_ebe943750ffeGe9UfA6PPGUjRT` | APPROVE scoped code; final gate/model-context caveat resolved by coordinator's existing alias/null tests and final evidence |
| Article / parsers / classroom / search | `ses_ebe941b36ffeeJqH85oPTIp6Gs` | APPROVE; no findings |
| Store / config / lock / Google tests + security context | `ses_ebe933d1effey3dirCwRnAxsgH` | Code APPROVE, security APPROVE; no findings |

CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0. No immediate secret rotation indicated
by inspected source. No top-three security fixes remain within the audited
change. These reviews are not a penetration test, proof of all OWASP controls,
or validation of live/private settings, DNS rebinding, hosted abuse/monitoring
or Windows runtime. Prior urllib3 package findings are remediated in this lock.
Full review responses are saved under ignored `backend/build/verification/` as
`phase1b-api-review.txt`, `phase1b-core-review.txt`, `phase1b-security-review.txt`.

The three original broad implementation workers timed out after 600 seconds
without source edits; bridge CLI recheck succeeded. Coordinator implemented the
fixes, then used bounded OpenCode test-generation and independent review packets.
No native subagent was substituted. Brig `research-backend` refreshed after
source edits; full-repo indexing still has the documented duplicate-symbol
limitation. SPEC/PLAN/HANDOFF persist decisions rather than treating Brig as
conversation storage.

### Actual changed files and manual reproduction

The 12 production files are enumerated in the coverage table. The remaining
15 files are: `backend/pyproject.toml`, `backend/uv.lock`,
`backend/tests/platform/test_verification_configuration.py`,
`backend/tests/api/test_api.py`, `backend/tests/api/test_api_outlines.py`,
`backend/tests/api/test_classroom.py`, `backend/tests/auth/test_auth_google.py`,
`backend/tests/coach/test_coach.py`, `backend/tests/ingest/test_article.py`,
`backend/tests/ingest/test_fetcher.py`, `backend/tests/ingest/test_webdiscovery.py`,
`SPEC.md`, `PLAN.md`, `HANDOFF.md`, `docs/VERIFICATION_BASELINE.md`.
No native/private/mobile source, student database, schema or provider changed.

To reproduce the visible fixes without touching real data, run from backend:
`uv run pytest tests/ingest/test_article.py -k unmatched -q` and
`uv run pytest tests/api/test_api.py -k deleted_after_owned_lookup -q`.
The built app is `macos/build/Build/Products/Release/Notaeo.app`; manual native
interaction was not part of this gate. Full suite and expanded commands above
reproduce the quality checks. Phase 2 needs separate approval.

### Application release check — NO-GO (outside this completed patch)

| Check | Result |
| --- | --- |
| Approved Phase 1b spec/phase acceptance | PASS: reproducible import/race fixes and measured gates |
| Entire verifier MVP plan complete | FAIL: Phases 2/3 pending, not authorized |
| Local backend build/types/lint/tests/coverage/security/diff | PASS |
| Native critical-flow E2E / Windows runtime | FAIL: not run in this scope |
| Known CRITICAL findings in reviewed change | PASS: zero; not a full live security audit |
| Migration/rollback | PASS for patch: no schema/data migration; revert code/lock for rollback; live restoration untested |
| Hosted monitoring/alerts and release operations | FAIL: outside public-repo scope, not validated |
| Docs and local handoff | PASS |

No release, push or deployment was performed. Backend remediation readiness
does not override these application-release blockers.
