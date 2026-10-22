# Summary

Implement the authorized desktop polish iteration in public research. Preserve
the preexisting `.serena/project.yml` edit and the private server checkout.
No deployment. OpenCode's prescribed Muse model is retired; the bridge works
with catalog-verified zero-cost `opencode/nemotron-3-ultra-free`. Its free-only
listing is a stale constant, not a CLI health test; record the actual CLI check.

Requirements: centered normal main launch window, no later recentering, honest
offline startup distinct from AI, original reproducible identity, a brief cozy
sound with persistent control/preview, evidence-based review iterations and an
optional-AI roadmap. Preference remains unvalidated until the owner tries it.

# Patterns to Mirror

| Category | Existing example | Use |
| --- | --- | --- |
| Native lifecycle | macos/Research/ResearchApp.swift:5,25 | Main actor, one owned sidecar and main Window scene |
| Motion | macos/Research/NativeStyle.swift:38 | Either app or system reduced motion makes samples static |
| Error handling | macos/Research/ResearchApp.swift:78 | Retry only actual backend failures; no fake progress |
| Preferences | macos/Research/SettingsView.swift:14 | Namespaced AppStorage, grouped native Form |
| Data/export | macos/Research/MainView.swift:347 | Success only after atomic save, never after cancellation |
| Tests | macos/ResearchTests/ThinkingOrbTests.swift:4 | Pure deterministic motion/policy samples with XCTest |
| API tests | backend/tests/coach/test_coach.py | Actual API with synthetic temporary storage |
| Assets | scripts/generate_app_icon.swift:1 | Original offline CoreGraphics generator |

No existing native sound playback/asset pattern exists. Windows already uses
CenterScreen, but runtime parity cannot be verified without its toolchain/host.

# Files to Change

| File | Action | Why |
| --- | --- | --- |
| macos/Research/ResearchApp.swift | UPDATE | Main-window launch placement, separate startup identity/status |
| macos/Research/NativePresentation.swift | CREATE | Tested placement, folio mark/motion and quiet PCM/policy/playback helpers |
| macos/Research/SettingsView.swift | UPDATE | Persistent sound control and explicit preview |
| macos/Research/MainView.swift | UPDATE | Play opted-in cue after a successful saved export |
| macos/ResearchTests/NativePresentationTests.swift | CREATE | Visible-frame geometry, once-only application, motion, PCM and audio gating |
| macos/Research.xcodeproj/project.pbxproj | UPDATE | Register production helper and XCTest source |
| scripts/generate_app_icon.swift; AppIcon.appiconset/*.png | UPDATE | Original folio/N identity consistent with the native startup mark |
| docs/desktop-polish/SPEC.md, PLAN.md, REVIEW.md, AI_PLAN.md; HANDOFF.md | CREATE/UPDATE | Acceptance, actual evidence, review filtering, roadmap, continuation |

# Tasks

## Phase 1 — Placement and startup (Medium, estimate 2–4h)

Goal: launch the main app in a centered normal window and show truthful loading.
Riskiest phase first: restoration and lifecycle behavior.

Complete: missing placement/motion helpers and launch-preference hook were RED
in the new acceptance tests. Final native XCTest87/87 passes. NativePresentation
line coverage98/99 (98.99%); ResearchApp 215/254 (84.65%). Xcode's report does not
provide Swift branch coverage; no branch-floor claim is made. Full arm64 sidecar,
Release app build and ad-hoc signature verification pass. Offline reduced-motion
startup render inspected at `/tmp/notaeo-startup-preview.png`. Fresh independent
OpenCode Big Pickle review APPROVE, zero concrete defects; no GUI trial claimed.
Evidence: `/tmp/notaeo-desktop-placement-{red,green,build}.log`,
`-coverage.json`, plus `/tmp/notaeo-desktop-restoration-red.log`.
Learned: SceneBuilder does not support the needed availability if/else, and the
system accessibility motion value is read-only; use documented app restoration
preferences and an isolated AppStorage suite for the render test.

1. Action RED: add/register native tests for visible-frame bounds including
   negative screen origins/small displays, centered target size, one application
   per window and a static reduced-motion folio. Mirror existing XCTest policy
   tests. Run the new class and save failing output before implementation.
2. Action GREEN: add a main-window-only attachment bridge that applies placement
   once, disables restoration for that window, and never moves Settings/user
   changes. Use screen visibleFrame, not an assumed zero-origin screen. Honor
   macOS 14 availability. Set the app's NSQuitAlwaysKeepsWindows preference false
   before restoring windows, and disable restoration on the attached window.
   SwiftUI SceneBuilder cannot express the required availability if/else for
   restorationBehavior; do not raise the OS floor or use private APIs instead.
   Keep user-requested fullscreen available after launch. Test preferences with
   an isolated suite; test hosts must not change the real app's defaults.
3. Action GREEN: replace ordinary-startup AI orbs with a native folio mark and
   real startup copy/indeterminate indicator; reduced motion is static. No
   minimum loading delay, percentages or network assets.
4. Validate: targeted and full native XCTest, signed sidecar/app build, independent
   review. Record limits of tests versus an actual desktop GUI trial.

## Phase 2 — Identity and cozy feedback (Medium, estimate 2–4h)

Goal: recognizable original branding and controllable, quiet completion feedback.
Depends on Phase 1 native helper/registration.

Complete: sound/export helper acceptance tests first failed for missing APIs;
packaged icon consistency failed on the previous book icon. Final 94/94 native
tests pass, including the actual test-host main window and read-only rendered
startup. OpenCode independently reran all 12 new cases:12/12 pass. New helper
line coverage 171/176 (97.16%); ResearchApp remains215/254 (84.65%). Swift branch
coverage is unavailable in xccov. Full native app coverage is1119/6871 (16.29%),
with MainView 0/1055 and SettingsView 10/274; those legacy UI workflows are not
exercised by unit tests. Do not claim the whole native app meets 80% coverage or
that dialogs/export clicks are E2E-tested. The real temporary-file save helper
is tested for success/failure/mute; physical playback is never called by tests.
The rebuilt arm64 sidecar/Release app and ad-hoc signature pass. Generator
output inspected at512px; packaged icon matches the startup mark in a separate
consistency test. Fresh GLM OpenCode helper and UI/generator/AI-plan reviews:
APPROVE, zero unresolved findings. Evidence `/tmp/notaeo-desktop-feedback-*`,
`-icon-red.log`, `-export-feedback-red.log`, `-actual-window.log` and
`/tmp/notaeo-opencode-native-retest-final.log`.
Learned: test the successful write before emitting completion feedback, and
compare compiled icon assets with the native identity to catch stale branding.

1. Action RED: test original offline PCM duration/amplitude, smooth silent edges,
   deterministic output and injected playback gate (muted/test host=no playback,
   preview explicit, opted-in completion plays). No physical audio from tests.
2. Action GREEN: synthesize a brief warm two-note cue in memory; retain playback
   until completion and stop the prior cue to avoid overlap. Add persistent
   native sound preference (default off) and explicit Settings preview. Play only
   after successful export, not startup, cancellation or AI loading.
3. Action GREEN: redraw the established CoreGraphics icon with the same original
   folio/N mark as startup. Generate/inspect small and large sizes. Do not copy
   another project's trademark or import an entire UI framework.
4. Validate: targeted/full native tests, signed build, reviewed diff and policy,
   generated icon inspection, owner listening checklist (pending until tried).

## Phase 3 — Review loop and AI plan (Small, estimate 1–2h)

Goal: actionable evidence and a bounded optional-AI roadmap.

Complete: verified OpenCode baseline 68 cases; independent final12-case native
retest; coordinator full 94-case native and 670-case backend gates. Model ratings
remain provisional (polish 7), unvalidated by human trials. AI_PLAN defines binary
fixture/evidence/fallback/native/hosted acceptance gates without invented usage,
latency or student outcome targets. Independent UI/generator/AI-plan review
APPROVE, zero findings. REVIEW/HANDOFF record filtered model findings, coverage
limitations, license references and owner trial. AGENTS now checks the actual
CLI catalog instead of trusting the static free list; free-model retirement is
explicit. Learned: a successful model-list tool is not proof its recommended
model exists, and passing unit tests is not an increase in perceived polish.

1. Action: record OpenCode's actual68-test baseline and provisional ratings;
   verify findings before accepting them. Reject nonexistent paths and the
   incorrect draft-leak finding (keys already include session and task IDs).
2. Action: fresh OpenCode review/test after changes, fix confirmed defects,
   rerun affected checks, commit each logical feature only after approval.
3. Action: document source-grounded explanations/practice, evaluation fixtures,
   citations/abstention, cancellation and real thinking states. Preserve no-AI
   fallbacks and the private hosted credential/allowance boundary. Targets and
   budget decisions not already established stay TBD with validation methods.
4. Action: record license-checked GitHub candidates, scoped evidence and handoff.

# Validation

```bash
# Root: select installed Xcode locally, never change machine-wide selection.
DEVELOPER_DIR=/Applications/Xcode-26.3.0.app/Contents/Developer xcodebuild -project macos/Research.xcodeproj -scheme Research -configuration Debug -derivedDataPath /tmp/notaeo-desktop-tests -destination 'platform=macOS,arch=arm64' CODE_SIGNING_ALLOWED=NO test
sh scripts/build_macos_app.sh
git diff --check
# Backend regression gate remains available (no backend code planned):
cd backend
env -u VIRTUAL_ENV uv run scripts/verify.py
```

Native code has no configured separate lint/typecheck command; Swift 6 compilation
is the type check. Native coverage and UI trial evidence must be reported
separately from backend coverage; do not substitute Python tests for native UX.
No Windows runtime/build result is claimed on this host.

# Risks and Acceptance checklist

| Risk | Control |
| --- | --- |
| SwiftUI restores an old fullscreen state | Disable restoration at native launch boundary; inspect actual window lifecycle |
| Wrong-screen positioning or repeated movement | VisibleFrame geometry and once-per-main-window attachment tests |
| Model hallucinates tests/bugs/ratings | Verify session tool results and full source before fixes |
| Intrusive or unpleasant sound | Default off, explicit preview, low amplitude, owner listening trial |
| Asset license confusion | Original brand/chime; external projects are documented candidates only |

- [x] Grounded plan reviewed; no repeated owner approval required.
- [x] Phase 1 meaningful RED/GREEN, native checks/build and review.
- [x] Phase 2 meaningful RED/GREEN, asset inspection, native checks/build and review.
- [x] Functional review/retest and AI plan saved.
- [x] Separate feature commits and handoff; public preexisting edit preserved.
