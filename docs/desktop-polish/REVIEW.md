# Desktop review loop — 2026-10-22

## Bridge recovery and provenance

All three bridge tools are visible. The model-list health check was misleading:
`freeOnly=true` returns a hard-coded list in the bridge, including the retired
Muse Spark model. Actual CLI diagnostics identified ProviderModelNotFoundError.
The bridge rebuilt successfully and its configured entry point is
`/Users/user/Documents/GitHub/cline/dist/index.js`. A current CLI catalog lists
`opencode/nemotron-3-ultra-free`, with zero input/output/cache prices; this
iteration uses that OpenCode model explicitly. No paid/native fallback.
The first broad launch-plan worker timed out after 180s/22 tool calls; it made
no tracked edits. The replacement bounded plan review approved the plan.

## Independent functional baseline

OpenCode session `ses_e9b189c9effeR0z4iQp8jc70go` executed:

```sh
cd backend
env -u VIRTUAL_ENV uv run pytest tests/coach tests/api/test_api_study.py tests/search/test_search_page.py tests/ai/test_ai_grounding.py -q
```

Actual result: **68 passed, seven external dependency warnings, 8.47s**.
The coordinator exported the session and verified ten tool calls, the actual
command and its output. Tests use synthetic fixtures; no real inference or GUI
trial occurred. The model's provisional scores were usefulness 8/coherence 8/
polish 7/trust 8 out of 10, based on code and this test sample. These are not
security certification, student research or a claim that the model personally
uses the app. UI pleasantness remains an owner trial.

## Findings verified before changes

| Observation | Coordinator decision |
| --- | --- |
| No native notebook deletion affordance | Confirmed backlog gap; do not add destructive UI as a drive-by polish change |
| Reader find-in-page | Possible improvement, not a demonstrated correctness defect; model cited a nonexistent SourcesView.swift path (view is in MainView.swift) |
| Answer drafts leak across sessions | Rejected: actual key is session.id + task.id; deleting drafts on navigation would regress intentional draft preservation |
| Main launch has default size but no explicit placement | Confirmed; this iteration adds main-only placement and lifecycle tests |
| Startup uses NativeAIActivity for ordinary local initialization | Confirmed; replace with folio identity and truthful startup status |
| Native sound is missing | Confirmed; browser implementation is historical, native Settings has no current sound controls |

The bounded plan review approved. Its generator-existence concern was already
resolved by reading the generator; signed packaging remains a separate command
from unsigned XCTest. Its actionable AI-plan request is addressed by binary
fixture/contract/native/hosted gates in AI_PLAN.md; no arbitrary latency target.

## Free projects checked for reusable assets

| Candidate | Verified source | Decision this iteration |
| --- | --- | --- |
| Microsoft Fluent System Icons | [MIT license](https://github.com/microsoft/fluentui-system-icons/blob/main/LICENSE) | Suitable future Windows control icons with notices; keep original Notaeo identity |
| Google Material Design Icons | [Apache2 license](https://github.com/google/material-design-icons/blob/master/LICENSE) | Alternative control icon family, not an additional mixed set |
| KDE Ocean Sound Theme | [Source/project files](https://github.com/KDE/ocean-sound-theme), [intended cue usage](https://raw.githubusercontent.com/KDE/ocean-sound-theme/master/README.md) | Useful sound-design reference; individual asset license must be checked before copying, no files imported |

No external icon/sound/framework is bundled by this pass. Original code-native
assets keep the app offline and its MIT attribution boundary simple; native
platform controls remain in place. GitHub availability alone is not treated as
permission to copy project logos or every media asset.

## Implementation and retest

- `f1bc878`: native main-window launch placement and folio startup, preserving
  Settings and later user moves. Phase 1 native 87/87 and signed build passed.
- `ef795a6`: original matching app icon and quiet opt-in completion feedback.
  WAV/policy/export acceptance tests were RED for missing helpers; the icon
  consistency test was RED for the previous asset. Final native 94/94 pass.
  New helper line coverage 171/176 (97.16%); ResearchApp 215/254 (84.65%).
- An actual test-host main-window check verifies current-screen bounds,
  centering, windowed style and disabled restoration. Its isolated host has no
  restored account/sidecar. This does not test fullscreen relaunch or all monitors.
- OpenCode retested all 12 new cases itself:7 presentation + 5 feedback, zero
  failures. `/tmp/notaeo-opencode-native-retest-final.log` was checked by the
  coordinator. No physical audio, real AI or user data was used.
- The full backend verifier also passed 670 tests, 88.93% combined coverage,
  types/lint/security0. Its four-file diff was the snapshot at that earlier
  measurement, not the final native feature diff. No backend source changed.
- Both final signed arm64 sidecar/Release builds and signature checks pass.
  Original generated icon and reduced-motion startup preview were inspected.

The first Phase 1 reviewer called the spinner fake (but it is gated by actual
backend startup), described an internal view as public, and speculated about a
centering flash/headless-screen placement without a reproducible failure.
Those claims were rejected with source/lifecycle evidence. An independent
Big Pickle review subsequently approved the actual code with zero findings.
A broad Phase 2 reviewer timed out without a verdict; bounded GLM reviews of
the audio helper/tests and UI/generator/AI plan both APPROVE with zero findings.
Model outputs are checked, not automatically converted into fixes.

The retester held polish at7/10: correctness tests cannot establish visual or
sound preference. Usefulness8/coherence 8/trust 8 remain provisional baseline
ratings, not updated student validation or production security signoff.

Native coverage limitations are material: all-app 1119/6871 lines (16.29%),
MainView 0/1055 and SettingsView 10/274. Existing API/logic tests do not exercise
those legacy UI flows. xccov provides no Swift branch percentage here. The
requested global native coverage gate and critical native-flow E2E are not met;
do not present this as a full production release. Windows build/runtime,
physical listening preference and fullscreen/multi-monitor relaunch remain
pending. No production deployment or private-server change occurred.

## Owner trial

Open the rebuilt local macOS app and use a disposable course account. Quit and
relaunch normally and after fullscreen, move between monitors, then resize and
open Settings without losing the main window's position. Under Settings → Sound,
preview the chime, opt in, save an export, cancel another export, then mute and
export again. There should be one cue only for a successful opted-in save, no
startup sound and no cue for cancellation. Separately try source import → local
search → exam-coach answer/reference/self-rating → export. Record concrete
friction before choosing the next feature. Native dialogs and real listening
are not replaced by the automated results above.
