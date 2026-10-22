# Native workflow review — 2026-10-22

Local milestone complete; not a production-release approval. Requirements and
scope are in SPEC.md and PLAN.md. No student usability trial was conducted.

## Defect and implementation

The macOS paste flow automatically sent `force: true` after a duplicate warning.
Commit `476277a` replaces that retry with an explicit native copy/cancel decision.
The controller holds the submitted snapshot, invalidates consent on account or
notebook changes, and suppresses stale results. Draft text is cleared only when
it still matches the completed submission. Confirmation consumes approval before
the dialog's dismissal callback runs. Twelve tests cover these state boundaries,
network/malformed-response errors, Unicode, large input and overlapping work.

The new dedicated lane compiles production Swift client/state/controller sources
and calls the actual packaged Python backend. It checks desktop-token and account
authentication, registration/login/logout/revocation, Unicode notebooks, paste
and TXT upload, source text/chunks, filtered lexical search, duplicate source
counts before/after consent, revision goals, basic practice/explanation/finish,
disabled-AI fallback, mind maps and exports. A real SQLite header and saved ZIP
integrity are checked. A second account receives 404 for foreign data.

The shell owns the backend and Swift check, creates private scratch directories,
passes clean child environments with explicit data paths and disables AI. The
Swift check uses ephemeral HTTP sessions, in-memory credentials and temporary
preferences. Test feedback stays silent. Cleanup stops only owned children before
removing scratch data; inability to stop one fails and retains its data.

## Red, green and independent review

| Check | Actual result / local evidence |
| --- | --- |
| Consent RED | Missing state/transport contracts fail; `/tmp/notaeo-paste-red.log` |
| Native full suite | 106/106 pass, including 12 consent tests; `/tmp/notaeo-paste-full-green.log` |
| Consent controller coverage | 82/83 executable lines, 98.80%; `/tmp/notaeo-paste-coverage.json` |
| Signed app build after consent fix | PASS; `/tmp/notaeo-paste-build.log` |
| Packaged fixture RED | Missing preparation fails; `/tmp/notaeo-packaged-workflow-red.log` |
| Initial interruption regression | Failed: a synthetic child survived wrapper termination; coordinator-preserved observation in `/tmp/notaeo-packaged-workflow-interrupt-red.log` |
| Final canonical build + workflow | Exit 0; signed arm64 sidecar/Release app, workflow and cleanup PASS; `/tmp/notaeo-packaged-workflow-canonical.log` |
| Final supervisor fault checks | Four scenarios pass: missing executable, exit before readiness, invalid readiness URL, interrupted startup; `/tmp/notaeo-packaged-workflow-negative.log` |
| Independent OpenCode execution | Packaged workflow exit 0; 12/12 consent tests pass; `/tmp/notaeo-opencode-{packaged,paste}-retest.log` |
| New Python driver | Ruff all checks pass; Pyright 0 errors/0 warnings |
| Shell syntax / whitespace | `sh -n scripts/test_macos_workflows.sh` and `git diff --check` pass |
| Scoped secret/TODO scan | No credential or TODO finding; sole URL match is the synthetic invalid loopback fixture |

The first lifecycle design passed a static review but failed the coordinator's
interruption test. Its verified synthetic sleep process was stopped and its
identified scratch directory removed. The implementation was redesigned so the
shell directly owns both children. The final four fault cases passed after that
redesign; the initial static approval is not used as approval of the final code.

Free bridge model `opencode/glm-5.3-flash-free`, `xhigh`, was explicitly selected
after checking the actual CLI catalog and zero prices. The bridge's static
free-only list is insufficient for CLI health. No paid/native worker fallback.
One broad coding worker timed out after 360 seconds with no edits; the coordinator
implemented and used bounded independent reviews/retests instead.

| Independent session | Result |
| --- | --- |
| `ses_e9aceb00dffehE1LtuCByG3UAT` | Consent controller/tests and UI diff: APPROVE, zero findings |
| `ses_e9abcd1faffeLeYQDCd9c9NhLO` | Final shell supervisor, Swift workflow and fault driver: APPROVE, zero confirmed findings |
| `ses_e9ab9349cffeQHT2siFks0Ovaz` | Actually reran packaged workflow and 12 native tests, both exit 0 |

Final implementation review counts: CRITICAL 0, HIGH 0, MEDIUM 0, LOW 0;
verdict APPROVE for this bounded change. The review noted the 64 KB startup-log
read limit as a possible false-failure under pathological log spam, not an app
security defect. It made no GUI, listening or personal-use claim.

## Repeat and try manually

From the repository root:

```bash
sh scripts/test_macos_workflows.sh
# Only when the packaged sidecar is already built:
sh scripts/test_macos_workflows.sh --no-build
cd backend
env -u VIRTUAL_ENV uv run python ../macos/WorkflowChecks/check_runner_failures.py
```

The canonical command requires the local Xcode path used by the existing build
script and builds the signed app first. `DEVELOPER_DIR` may explicitly override
that path. `--backend PATH` exists for the fault fixtures; it does not change the
installed app's backend. No missing-fixture case skips the lane.

For a manual check, open the rebuilt `macos/build/Build/Products/Release/Notaeo.app`,
sign in and paste the same course text twice. The second paste must show the
duplicate decision without adding a source. Cancel keeps the count unchanged;
Save a copy adds one. Try changing the draft and notebook/account around an
in-flight request. Then complete a basic revision session and export a notebook.

## Remaining release gaps

- These are native-client/API integration checks, not GUI dialog-click E2E.
  Physical monitor/window restoration, actual dialog interaction and sound
  preference need owner trials. No audio was played by automation.
- Native whole-app line coverage is 1201/7008 (17.14%), despite the controller's
  98.80%. Swift branch coverage is unavailable here. The requested whole-native
  80% floor is not met; this is not a production-ready certification.
- Backend source is unchanged. The prior 670-case verifier with 88.93% combined
  coverage remains prior evidence, not a newly executed full backend gate.
- Windows/mobile, real remote discovery/inference, provider costs and hosted
  deployment are outside this lane. No user data, provider settings, private
  server code, website or dependencies were changed.
- Local `/tmp` logs are disposable evidence. Committed tests and run commands
  provide reproducibility; the ad-hoc-signed app is not notarized.

Brig's `research-native-macos` source index was refreshed: 26 native source files
(2 indexed, 24 unchanged). The unrelated `.serena/project.yml` edit is preserved.
