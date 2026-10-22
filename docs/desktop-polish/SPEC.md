# Desktop launch, identity and feedback

Status: authorized by the owner's request to test, rate, fix and retest the app.
The interview and repeated approval prompts were waived earlier. Desktop first;
this iteration is macOS, with Windows parity tracked separately.

## Problem and evidence

The owner reports that the logo and sounds need work, and requests a centered,
windowed launch with a better loading screen. Code inspection confirms that
macOS has a default window size but no explicit launch placement, startup uses
the AI activity indicator for ordinary backend startup, and native Settings has
no sound controls. The former browser sound implementation was removed with
the website. Student adoption and subjective preference remain assumptions.

## Users and not-for

Students opening the installed app to collect course sources and revise for an
exam. The maintainer needs repeatable synthetic functional checks and honest
review evidence. Not for website visitors or a new media/editor product.

## Hypothesis

We believe predictable launch placement, a recognizable identity and restrained
feedback will make the installed study workflow easier to understand. We will
know when the technical acceptance checks pass; preference and repeat use are
TBD — needs validation via owner trials with the rebuilt app.

## Success metrics

| Metric | Target | Measurement |
| --- | --- | --- |
| Launch | Main window opens centered, sized to the visible screen, in normal windowed mode | Geometry and native window checks; actual GUI trial separately recorded |
| Placement stability | Settings, reopening and subsequent updates do not recenter a moved window | Native lifecycle tests |
| Loading | Offline startup identity and truthful status; no fake progress or minimum delay | Native tests and build; reduced-motion static sample |
| Sound | Soft brief cue, Settings preview and persistent mute; no automatic audio in tests | PCM/policy tests and explicit owner listening trial |
| Identity | Original reproducible mark, legible at small icon sizes, reused at startup | Generated assets and visual inspection |
| Functional review | Actual commands/results and provenance accompany provisional ratings | OpenCode test evidence and coordinator verification |
| Usefulness/preference | TBD — needs validation via owner course-material trial | No model rating presented as student validation |

## Scope

MVP: one native launch-placement policy, a non-AI startup presentation honoring
reduced motion, an original app mark, an offline cozy success cue with Settings
controls, an independent test/review/fix/retest record, and a separate optional
AI feature plan. Preserve account/data ownership, Settings, offline study and
the existing optional managed-AI boundary.

Out of scope: website, mobile, paid services, personal keys, local LLMs, automatic
AI requests, provider changes, hosted deployment, migrations, notifications and
calendar integration. No claim of Windows runtime verification from macOS.

## Delivery milestones

| Outcome | Status |
| --- | --- |
| Independent functional baseline and verified findings | Complete;68 backend cases passed, model findings checked against actual source |
| Predictable native launch and understandable startup | Complete locally;87 native tests, signed build and independent approval; relaunch/fullscreen owner trial pending |
| Original identity and controllable cozy feedback | Complete locally;12 new native cases, generated/packaged icon consistency, silent test playback; listening preference pending |
| Reviewed candidate, remaining trial checklist and AI roadmap | Complete locally; independent reviews/retest, roadmap and owner trial saved; broader native coverage and public release gates remain open |

## Open questions and risks

Sound pleasantness and final visual preference are TBD — needs validation via
owner listening/visual trials. Windows packaging/runtime remains TBD — needs
validation on Windows. AI model quality and sustainable allowances remain
TBD — needs validation via synthetic evidence evals and operator capacity.

| Risk | Likelihood × impact | Mitigation |
| --- | --- | --- |
| Review invents a defect or personal-use evidence | Plausible × misleading fixes | Verify every finding against code and actual tool output |
| Window placement overrides user interaction | Plausible × disruptive | Apply once to the main launch window only |
| Audio is intrusive | Plausible × poor study experience | Brief low-level cue, persistent control, explicit preview, no startup loop |
| Motion suggests AI or invented progress | Plausible × misleading | Separate startup folio from AI orbs and use real lifecycle state |

Validation status: problem assumption with owner feedback, users concrete,
technical metrics defined and preference/outcome metrics TBD. Next: grounded
plan and implementation under the existing authorization.
