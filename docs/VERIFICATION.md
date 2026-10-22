# Backend verification

`backend/scripts/verify.py` runs the repository's fixed backend release checks
and prints a concise evidence report. It does not deploy the app or establish
that the native clients or a hosted service are ready to release. Review the
dated release checklist below before treating a passing backend run as release
approval.

## Run the gate

From the repository root:

```sh
cd backend
uv run scripts/verify.py
```

The default timeout is 900 seconds per command. Set a different finite,
positive timeout with `--timeout SECONDS`. To run only dependency and source
security checks:

```sh
cd backend
uv run scripts/verify.py --security-only
```

The CLI also provides `--help`; its operational options are `--security-only`
and `--timeout SECONDS`. Check commands
are fixed in the source. Exit status is `0` when the selected check passes, `1`
when evidence fails or is incomplete, and `2` for invalid CLI arguments.
Security-only mode reports `SECURITY: PASS` or `SECURITY: FAIL`; it never reports
overall `READY`.

The full run executes these stages in order:

1. **Build:** `sh backend/scripts/build_macos_sidecar.sh` from the repository
   root. A failed, missing, timed-out, interrupted, or over-output build stops
   the run; later stages are reported as missing/not run.
2. **Types:** Pyright JSON evidence.
3. **Lint:** Ruff JSON evidence.
4. **Tests and coverage:** pytest JUnit XML, then coverage.py JSON.
5. **Security:** strict `pip-audit` JSON plus the source scan.
6. **Diff:** Git change inventory and whitespace checks.

The non-build checks continue after a failure so the report can show the other
available evidence. They still cannot produce `READY` if any mandatory result
fails or is unknown. The advisory audit may require network access to refresh
vulnerability data; an unavailable or incomplete audit fails closed.

## Read the report

The first line starts with `VERIFICATION REPORT` and gives each stage's status,
its measured counts where applicable, and the overall result. `READY` requires
all six stages in order, successful process exit codes, valid evidence, zero
type/lint/security findings, a passing non-empty test suite, coverage floors,
and a known diff count. Any missing value is shown as `unknown`; it is never
treated as zero. A failed report includes numbered, sanitized issues. Raw tool
diagnostics and secret values are not printed.

The test count is passed tests over total tests. Skipped tests are not passes.
Coverage's displayed combined percentage weights covered statements and
branches together. Passing also requires the independent floors below, so the
combined percentage alone is insufficient.

## Coverage scope

The application denominator contains every Python file under `backend/core/`
and `backend/api/`, including files absent from executed test imports. The CLI
checks that all on-disk application modules appear in the coverage JSON. Their
aggregate must meet at least 80% line coverage and 80% branch coverage. Each
touched Python file under `core`, `api`, or `scripts` must meet both floors as
well. Script coverage is collected to measure changed verifier code, but does
not enter the application aggregate. Empty modules with zero statements are
allowed when the application aggregate has measured lines; an entirely
zero-line application cannot pass.

Touched Python paths come from the NUL-delimited Git diff against `HEAD` plus
untracked files. Deleted paths are not treated as touched files requiring
coverage. The diff count includes changed and untracked paths. Unavailable or
malformed Git inventory leaves the relevant counts unknown and blocks
readiness.

## Artifacts and process limits

Each full invocation creates a unique temporary directory under
`backend/build/verification/`. It holds the coverage data, JUnit XML, and
coverage JSON while that run is active; the directory is removed when the run
ends. The parent `build/verification/` directory remains. The verifier does
not write application data or modify source files.

Child stdout and stderr are drained separately under a combined 128 KiB output
limit. Structured evidence is parsed from stdout or the bounded report files;
stderr is not merged into JSON. Timeout, interrupt, malformed encoding, or
excess output makes that command's evidence incomplete. The verifier starts
each child in its own process group and terminates that group on timeout or
output overflow. JUnit and coverage evidence are limited to 8 MiB each; scanned
source files are limited to 2 MiB. The source scan returns rule, path, and line
metadata, not matching source text or credential values. It is a scoped local
check, not a complete security audit.

The subprocess implementation uses POSIX process groups and pipe selection.
The build stage is a macOS sidecar build. Treat this gate as a macOS/POSIX
workflow; it does not verify Windows packaging or runtime behavior. Windows
runtime, DPAPI, packaged sidecar, and installer checks require Windows.

## Safe seeded failures

The CLI integration tests replace the fixed command map with synthetic
executables in temporary directories. These commands do not run the real
build, Git inventory, or dependency audit. From `backend/`, run one test to
exercise a build failure and verify that later stages do not run:

```sh
uv run pytest tests/platform/test_verification_cli.py::test_build_failure_stops_later_stages_and_cannot_report_ready -q
```

To confirm that a command returning success without producing required test
artifacts still fails closed:

```sh
uv run pytest 'tests/platform/test_verification_cli.py::test_success_exit_without_new_artifact_does_not_pass_tests' -q
```

These are intentionally passing regression tests: each asserts that the
synthetic failure results in a nonzero gate result. They are safe examples for
demonstrating failure handling; do not induce failures in the real gate by
changing repository commands or files.

## Release evidence — 2026-10-22

This checklist records the current local evidence. `PASS` is limited to the
named check; `FAIL` blocks the backend gate or release claim; `N/A` means the
check does not apply to this phase. Unverified release prerequisites are marked
`FAIL` rather than passing by omission. A backend pass does not imply deployment or application release
approval.

| Check | Status | Evidence and limit |
| --- | --- | --- |
| macOS sidecar build stage | PASS | The current verifier report records Build: PASS. |
| Pyright and Ruff | PASS | Types: PASS (0); Lint: PASS (0). |
| Backend test suite | PASS | 670/670 tests passed after Phase 2b. |
| Application coverage | PASS | 5,845/6,399 lines (91.34%) and 1,605/1,978 branches (81.14%); combined 88.93%. All 51 core/API Python modules are represented. |
| Source scan | PASS | No source findings in the current run. |
| Dependency audit / overall backend gate | PASS | Fresh strict audit checks 85 packages, zero findings. Certifi alone updated to 2026.10.19; full gate reports READY. |
| Fresh macOS app packaging | PASS | Rebuilt after the certifi update; build exits 0 with arm64 and ad-hoc signature checks. It is not notarized or ready for public distribution. |
| Packaged certificate bundle | PASS | Actual development, sidecar and app PEMs have identical SHA256 and 120 roots, excluding emSign ECC Root CA - G3. Host Python SSLContext loads each file with required certificate and hostname checks; no live sidecar TLS test performed. |
| Windows build and runtime | FAIL | .NET and PowerShell tools are unavailable in the current macOS environment; Windows packaging, controls, DPAPI, installer, and runtime remain unverified and release-blocking. |
| Native app critical-flow and clean-machine checks | FAIL | No current end-to-end runtime evidence is recorded here. |
| Hosted TLS, monitoring, and alerts | FAIL | These hosted operations are outside this repository's access; release evidence is unavailable and no deployment was performed. |
| Data migration and rollback | N/A | This verification change proposes no application data migration. |
| Existing migration recovery | FAIL | No fresh synthetic backup/restore or rollback drill was performed; do not infer migration safety from passing API tests. |
| Notarization and public distribution | FAIL | The macOS app is ad-hoc signed; Developer ID, hardened runtime, notarization, and distribution packaging remain future release work. |
| Verification feature SPEC and plan | PASS | Gate behavior and failure demonstrations exercised by the full suite; documentation/handoff reviewed. Maintainer-effort outcome metrics remain TBD, without a student-validation claim. |
| Scoped dependency security finding | PASS | Phase 2b resolves the reported critical trust-bundle finding; independent scoped code/security reviews approve. This is not a whole-app security sign-off. |

The certifi maintainer describes the affected trust chain in the
[security advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2).
The initial October 22 audit found the affected bundle in certifi 2026.7.22.
The owner separately approved Phase 2b; the updated and rebuilt bundles remove
the affected root. No successful attack or exposed credential was demonstrated,
so no secret rotation is indicated by this finding alone.

The final gate report is `/tmp/notaeo-phase2b-final-gate.log` (exit 0). It reports
10 changed paths: nine intended files plus unrelated `.serena/project.yml`,
which is excluded from our commits. Review copies of audit, coverage, and
bundle evidence are in `backend/build/verification/phase2b-final-audit.json`,
`phase2b-final-coverage.json`, and `phase2b-bundle-check.json` under that same
directory. Initial failed evidence remains in `/tmp/notaeo-phase3-current-gate.log`
and the corresponding `phase3-current-*` JSON files. Normal verifier run
artifacts are ephemeral; these retained copies are evidence snapshots, not
outputs that the verifier leaves behind. The separately approved certifi
remediation is complete in `PLAN.md` Phase 2b. The local milestone is ready to
commit after independent review; public application release remains **NO-GO**
because the native runtime, Windows, migration-recovery and operational checks
above remain unverified. No push or deployment was performed.
