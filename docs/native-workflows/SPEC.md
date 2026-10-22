# Native import safety and real backend workflow checks

Authorized continuation of the desktop review/fix/retest loop. No interview or
repeated approval prompt; the owner waived those earlier.

## Problem, evidence and users

Students importing course notes expect a duplicate warning to leave their source
collection unchanged until they choose to save a copy. The current macOS paste
flow immediately retries with force after a duplicate response. The coordinator
and an independent OpenCode review confirmed the unconditional second request.
This is an observed correctness defect, not a reported production incident.

The maintainer also lacks an automated check that the native Swift client can
complete a study session against the actual packaged backend. Existing Swift
API tests mostly stub HTTP; Python API tests do not prove the cross-language
contract. Student adoption/preference remains an assumption. Not for website
visitors, AI-provider selection, or modifying hosted operations.

## Hypothesis and success metrics

We believe explicit duplicate consent and a reproducible native-client/backend
workflow check will prevent accidental copies and reveal contract regressions.

| Metric | Target | Measurement |
| --- | --- | --- |
| Duplicate warning | Exactly one initial request and zero copy until explicit confirmation | Native controller tests and packaged-backend source counts |
| Confirmation | Only the reviewed title/text and original account/notebook scope can be copied | Snapshot, cancellation, context-change and concurrency cases |
| Basic import | A fresh paste saves normally; failures preserve recoverable draft text | Mocked native failure/mutation tests |
| Native/backend compatibility | Register/login, import/read/search, basic revision, export and account isolation work without AI | Dedicated native integration suite against a disposable packaged sidecar |
| Test isolation | No user data/Keychain, physical sound, remote inference or network discovery | Temporary directories, in-memory credentials, loopback only and explicit teardown |
| Learning/retention | TBD — needs validation via owner course-material trials | No automatic grades or inferred exam readiness |

## Scope and milestones

MVP: explicit duplicate-paste decision, context-safe pending work, native tests,
and an isolated packaged-backend integration lane with exact setup/run commands.
The native client integration lane is not a GUI-click test; full dialogs and
physical monitor trials remain separate. No test is silently skipped if setup
is missing; the dedicated lane must fail with an actionable setup message.

Out of scope: new notebook deletion UI, upload-policy redesign, Windows/mobile,
general chat, provider changes, storage allowances, website, deployment and real
account/data operations. No backend behavior change is assumed necessary.

| Business outcome | Status |
| --- | --- |
| Duplicate warning respects the student's choice | Complete locally;12 consent/state cases,106 full native cases, signed build and independent approval |
| Maintainer can reproduce the real native-client study workflow | Pending |
| Reviewed commits, evidence and remaining GUI gaps saved | Pending |

## Open questions and risks

Source import UI preference, physical dialog behavior and Windows runtime are
TBD — needs validation via owner trials on the appropriate host. Native whole-
app coverage remains below the earlier requested release floor; this iteration
must report that honestly rather than shrink the denominator.

| Risk | Likelihood × impact | Mitigation |
| --- | --- | --- |
| Async confirmation applies to changed content/account | Plausible × accidental write | Immutable snapshot, explicit scope/generation guards and stale-response tests |
| Test fixture starts a real-data sidecar | Plausible × privacy/data change | Explicit packaged executable and fresh data path, no default Application Support fallback |
| Integration lane masks failures or hangs | Plausible × false confidence | No skips, bounded startup/requests/teardown and independent retest |
| Client integration described as GUI E2E | Plausible × misleading release claim | Separate actual request/SQLite evidence from dialog-click/physical trials |

Validation status: technical problem observed, users concrete, technical metrics
defined and learning outcomes TBD. Next: grounded implementation and retest.
