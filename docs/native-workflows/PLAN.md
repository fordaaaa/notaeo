# Summary

Two authorized phases in public research. Preserve `.serena/project.yml` and
leave private-server/mobile/website untouched. Free OpenCode GLM model verified
in the current CLI catalog; bridge gate passed. No paid/native worker fallback.
Complexity Medium, provisional 4–8h (not claimed elapsed time).

Requirements: no silent forced duplicate import; confirm an immutable paste in
the current account/notebook only; keep useful failure/draft recovery; exercise
the native client with the packaged no-AI backend using disposable data.

# Patterns to Mirror

| Category | Grounded example | Use |
| --- | --- | --- |
| Native state/generation | macos/Research/SearchView.swift:4-35 | MainActor ObservableObject, private-set state, stale-response suppression |
| Duplicate contract | macos/Research/APIClient.swift:249-269; Models.swift:118-128 | saved/duplicateOf/summary, no automatic force |
| UI confirmation | macos/Research/SiteIndexView.swift:236 | Native confirmationDialog |
| Data ownership/errors | macos/Research/AppState.swift:55-75 | Per-request token snapshot and matching unauthorized expiry |
| Tests/mocks | macos/ResearchTests/APIClientTests.swift:146-205 | URLProtocol transport stubs, synthetic payloads |
| Sidecar lifecycle | macos/Research/BackendProcess.swift:35-157 | Owned child, loopback URL validation, bounded startup and stop |
| Actual save feedback | macos/Research/NativePresentation.swift:150 | Atomic write followed by opt-in cue; silent injected test playback |

No existing native packaged-backend integration lane exists. Compile the same
production Swift client/model/state sources into a separate command-line check,
so lightweight native unit tests retain their setup and no new app test-mode
credentials or Xcode target are needed. This remains client/API integration,
not a GUI-click test.

# Files to Change

| File | Action | Why |
| --- | --- | --- |
| macos/Research/SourcePasteController.swift | CREATE | Tested duplicate decision/snapshot/scope logic |
| macos/Research/MainView.swift | UPDATE | Explicit copy/cancel controls and safe draft clearing |
| macos/ResearchTests/SourcePasteControllerTests.swift | CREATE | Duplicate/confirm/cancel/context/failure/concurrency acceptance |
| macos/Research.xcodeproj/project.pbxproj | UPDATE | Phase1 source/test registration only |
| macos/WorkflowChecks/PackagedWorkflow.swift | CREATE | Production Swift client/API/AppState/SQLite workflow and owned temporary sidecar |
| scripts/test_macos_workflows.sh | CREATE | Build packaged app/sidecar and invoke dedicated lane |
| docs/native-workflows/{SPEC,PLAN,REVIEW}.md; HANDOFF.md | CREATE/UPDATE | Current requirements, evidence, review and resume |

DELETE none. Prefer a test-owned Process fixture over production environment
bypass hooks; change production lifecycle only if integration evidence requires
a narrowly reviewed fix. No dependency, database or hosted API changes planned.

# Tasks

## Phase 1 — Explicit duplicate-paste decision

Goal: warning cannot write a second source without a current explicit decision.
Riskiest phase first; provisional 2–4h.

Complete locally. Acceptance tests were RED for absent paste state/transport
contracts. Targeted9/9 first passed; expanded12/12 and full106/106 pass after
Unicode/large snapshot, cancellation, context and overlapping completion cases.
Controller82/83 executable lines (98.80%); all native1201/7008 (17.14%). Swift
branch coverage is unavailable; full native UI coverage remains a release gap.
Signed arm64 sidecar/Release app packaging passes. Independent OpenCode review
APPROVE with zero findings. The coding worker timed out after360s with no edits;
the coordinator took over implementation and kept review independent. Evidence
`/tmp/notaeo-paste-{red,green,full-green,build}.log` and `-coverage.json`.
Learned: approval must consume the snapshot synchronously; dialog dismissal
must not revoke a decision already made or make a second request itself.

1. RED: a duplicate response produces one request and a pending snapshot; no
   force/reload until consent. Confirm replays that exact title/text, cancellation
   produces no request, fresh paste works, errors preserve draft, concurrent
   actions/context changes/cancellation cannot publish stale state or copy under
   another owner. Use protocol/closure fakes, not real audio/network.
2. GREEN: MainActor controller mirrors generation guards; scope includes current
   account and notebook. Clear pending work on context/view change. Confirmation
   UI uses separate presentation state so automatic dialog dismissal cannot
   consume the pending snapshot before the explicit action runs. Do not clear
   newer edited draft text on completion of an older submission.
3. Validate full native XCTest and signed app build, inspect helper coverage and
   independent correctness/security review. Commit one focused fix.

## Phase 2 — Packaged native-client workflow lane

Goal: detect real Swift/HTTP/SQLite contract mismatches with no mocked backend.
Depends on Phase1 commit; provisional 2–4h.

1. RED: dedicated native-client checks fail clearly without their packaged fixture.
   Tests require an actual loopback desktop-token+account session: register,
   wrong/correct login, notebook, paste/read/search, duplicate no-copy then
   explicit-copy counts, basic coach goal/draft/start/answer/finish, export,
   second-owner404 and logout/revocation. Use synthetic course data only.
2. GREEN: test fixture explicitly selects the built packaged executable, binds
   ephemeral loopback and passes a fresh temporary data directory and token.
   Avoid production Keychain/defaults. Await readiness with a deadline; terminate
   only the owned process and prove cleanup. Never fall back to real data.
3. GREEN: a build/run wrapper compiles the production client/model/state sources
   into an isolated CLI check, keeping the normal native unit lane independent. Missing preparation fails, never skip. Fix only failures
   demonstrated by this lane, with a separate RED/targeted regression.
4. Validate both native lanes and signed packaging, independently review/retest,
   document actual coverage and remaining GUI/Windows gaps, commit and hand off.

# Validation

```bash
DEVELOPER_DIR=/Applications/Xcode-26.3.0.app/Contents/Developer xcodebuild -project macos/Research.xcodeproj -scheme Research -configuration Debug -derivedDataPath /tmp/notaeo-native-workflow-unit -destination 'platform=macOS,arch=arm64' CODE_SIGNING_ALLOWED=NO -enableCodeCoverage YES -parallel-testing-enabled NO test
sh scripts/build_macos_app.sh
# Phase2 dedicated lane, after implementation:
sh scripts/test_macos_workflows.sh
git diff --check
```

Swift6 compilation supplies native type checks; no separate native linter is
configured. Report native line coverage separately; xccov has no Swift branch
percentage here. Native whole-app coverage is not yet80%; no release claim.
Backend source unchanged: existing full670-case verifier remains prior evidence;
rerun required backend suite if an actual backend fix becomes necessary.

# Risks / acceptance

| Risk | Control |
| --- | --- |
| Confirmation dismissal races | Snapshot/action/presentation are distinct; test cancellation and delayed completions |
| Task writes already in flight when user changes account | No later automatic force; suppress stale UI; server ownership authoritative |
| Test fixture uses Application Support | Test-owned explicit temp path and child process; no runtime test switches |
| Integration preparation burdens unit tests | Separate CLI lane; no new Xcode target or production test-mode hooks |

- [x] Phase1 RED/GREEN, independent review, native checks/build and commit.
- [ ] Phase2 fixture RED, real packaged workflow and cleanup verified.
- [ ] Independent OpenCode final retest and evidence saved.
- [ ] Feature commits and handoff; unrelated edit preserved.
