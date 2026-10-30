# Student shipping goals — 2026-10-30

Audience: high school, college and university students, initially in Canada.
Release decision: **not ready for external beta**. Passing local checks establishes
a foundation; native mobile distribution, live school connections and the
deployed service still have gaps. This document tracks outcomes, not estimates.

## Goals and acceptance

| Goal | Acceptance | Current evidence / next action |
| --- | --- | --- |
| G1. Prove the existing core | Registration/login, import/read/search, revision, ownership, logout and Markdown export work on disposable data | Backend, mobile API/browser harness and packaged macOS checks pass; device GUI/restart testing remains open |
| G2. Make a connected student workspace | Today links upcoming, overdue and undated work to the right course, material and study session; user timezone and account isolation are tested | Local macOS/mobile Today task foundation has create/complete/reopen/material navigation; ownership fix committed. Client review is pending; course creation/editing and due-review/resume remain open. See `today/REVIEW.md` |
| G3. Connect the student's school safely | Browser consent, student read-only access, one-use state/PKCE, explicit course choice, bounded pagination, accurate dated/undated work, repeat import and disconnect | Existing Classroom sync now preserves undated assignments locally. OAuth safety/native completion/course selection remain pending in `lms/PLAN.md`; no live school connection is certified |
| G4. Turn selected work into useful portable notes | Select supported files; preserve original extracted text, provenance and page references; inspect/search/export Markdown. Optional AI produces a reviewable derived note with source links and a clear unavailable/failure state | Local PDF/DOCX/TXT/MD ingestion and Markdown ZIP exports exist. Mobile native upload/export parity and permission-aware LMS attachment import remain gaps. No new AI provider or automatic background transmission |
| G5. Verify the installed and hosted release | Supported iOS/Android release builds, native login/SecureStore/restart checks, authenticated HTTPS workflows, deployed readiness, backup/restore and monitoring evidence | macOS ad-hoc build/workflow passes. Mobile JS bundles export. Tailscale/API liveness works; deployed readiness returns 404. No deployment performed |

G2 is the next visible client milestone; G3's safe connection foundation can
proceed independently. Preserve the existing class/notebook distinction. Do not
build more disconnected dashboard cards or equate a backend endpoint with a
complete student workflow. Each implementation needs meaningful failing tests,
the required broader checks and independent review before committing.

## Fresh verification

All checks below ran on 2026-10-30 with synthetic local data except the explicitly
read-only infrastructure probes. No real schoolwork or production account was
created or imported.

| Check | Result | Practical limit |
| --- | --- | --- |
| Backend `uv run pytest`, baseline | 670 passed; 7 dependency deprecation warnings | Local fixtures, not a deployed integration test |
| Final full backend verifier | READY: build/types/lint pass; 677/677 tests; 89.17% combined application coverage; security zero findings | Local backend gate only; broader product release remains blocked |
| Mobile `npm run typecheck` | Pass | Static types |
| Mobile unit tests | 189 passed, 33 files | Native interaction coverage remains limited |
| Mobile `npm run test:backend` | 1 real API workflow passed | Disposable SQLite; in-memory mock SecureStore |
| Mobile `npm run e2e` | 22 passed across iPhone WebKit and Pixel Chromium profiles | Browser harness, not iOS/Android native GUI |
| iOS and Android Expo export | Both Hermes bundles exported | Not release binaries; current Xcode 26.3 is below the mobile handoff's documented native build requirement |
| Native macOS XCTest | 106 passed, zero failures/skips | State/transport tests, not full GUI automation |
| Native iPhone launch | Expo Go 57 renders the current guest notebook screen on iPhone 17 Pro / iOS 26.3 | Launch/render only; native authenticated GUI, keyboard and SecureStore restart journeys remain unverified |
| macOS packaged workflow and signed arm64 app build, baseline | Pass, including upload, read/search, revision, maps/export, ownership and revocation; cleanup passed | Ad-hoc signature, not notarisation or App Store readiness |
| Final macOS build/workflow with updated dependencies | Pass, including owned-process/scratch cleanup | Confirms the final local candidate, not a deployed client |
| Mobile dependency audit | 12 entries: 4 high, 3 moderate, 5 low, zero critical | Needs dependency/reachability triage; do not accept npm's suggested Expo 51 downgrade |
| Tailscale | Running, no reported health errors; `homelab` answered in 33ms | Reachability, not application or backup readiness |
| Deployed HTTPS API | `/api/health` 200; `/api/auth/me` 401 without login | No production credential or write used |
| Deployed readiness | `/api/ready` 404 via HTTPS and directly on server loopback | Runbook expects 200/503: deployment/version mismatch must be reconciled |
| Removed browser pages | `/` and `/docs` 404 | Expected API-only boundary; no website was rebuilt |

Mobile initially could not start Vitest because local `node_modules` lacked a
Rolldown module. `npm ci --ignore-scripts` restored the locked install, after
which all lanes above passed; no mobile tracked file changed. The live research
container was running since October 24; its port 8000 is published on all host
interfaces. Host firewall/public ingress was not verified; do not infer public
exposure or change network configuration from this observation.

## School coverage in Canada

There is no single college/university platform. Examples verified against
official school pages on 2026-10-30, not market-share measurements:

| Platform | Example | Integration status |
| --- | --- | --- |
| Google Classroom | Existing code in this repo; intended student connector | Incomplete, not live-tested |
| D2L Brightspace | [Algonquin College](https://www.algonquincollege.com/brightspace/) | Planned; actual target tenant, app registration and permissions needed |
| Canvas / Quercus | [University of Toronto](https://teaching.utoronto.ca/student-support/) | Future connector; school access/registration must be established |
| Blackboard Ultra / Learn@Seneca | [Seneca Polytechnic](https://employees.senecapolytechnic.ca/spaces/238/itas/wiki/view/15289/learn-seneca) | Future connector; no API access established |
| Moodle / eClass | [York University](https://www.yorku.ca/laps/eso/teaching-research/eclass/) | Future connector; no API access established |

Implement one working authorised connector at a time. Manual import remains the
useful cross-school path. School login does not by itself establish permission
to register an API client or download every attachment. Existing provider
research and the first Google milestone remain in `lms/{SPEC,PLAN,PROVIDERS}.md`.

## Positioning and first student trial

Draft positioning: "Your coursework, organised. Your next study session, ready."
Describe the supported client/version accurately: collect readings and notes,
find source passages, practise and keep Markdown exports. Explain optional AI
as a deliberate enhancement. Avoid promising automatic school sync, reminders,
APA/MLA bibliographies or AI extraction before those workflows are implemented
and evaluated.

Use one high school and one college/university coursework scenario with
synthetic or student-authorised material. Observe whether the student can sign
in, add a course and source, identify the next task, find evidence, complete a
study session and export usable notes without assistance. Record completion,
errors and points of confusion. No student trial, adoption figure or time saved
is claimed yet.

## Correctness change and gate follow-up

Classroom previously treated `parse_due(...) is None` as a reason to discard
coursework. The route now accepts missing/null `dueDate` while continuing to
skip a malformed non-null date. Existing storage already supports nullable
deadlines; no schema, token, scope or OAuth changes were made. A removed remote
deadline clears the local date on repeat sync while preserving record identity,
completion and notebook linkage. Regression tests first produced 3 failures /
22 passes, then 25 passes after the route fix. Three additional refresh/recovery
cases cover successful expired-token refresh, reconnect after rejection and
temporary upstream failure without imported records or a false sync timestamp.
The targeted module suite now has 28 passes and route coverage is 89% combined.

The first full release verifier refused readiness despite 674 passing tests:
the touched Classroom route did not meet its coverage floor, and the current
dependency audit reported 18 advisories across filelock 4.1.1 and setuptools
84.0.0. The refresh/recovery tests address real route branches rather than
lowering the floor. A bounded lockfile refresh upgrades only filelock to 4.2.4
and setuptools to 84.2.1. The subsequent strict installed audit reports no known
vulnerabilities; this audit does not cover the deployed container or mobile.
[Filelock release](https://pypi.org/project/filelock/4.2.1/) and
[setuptools advisory](https://github.com/advisories/GHSA-xmj3-9gf7-h52w).

The native launch initially failed because Metro listened on IPv6 localhost but
advertised a 127.0.0.1 bundle URL. Restarting this session's Metro with
`EXPO_PACKAGER_PROXY_URL=http://localhost:8085` resolved it; no app configuration
or machine-wide developer-directory change was made. Screenshot evidence is
`/tmp/notaeo-shipping-iphone-20261030.png`. JS exports, launch checks and browser
profiles still do not certify mobile release readiness. Windows was not rerun:
the current shell has neither dotnet nor a Windows runtime.

## Bridge execution

All model calls in this continuation explicitly request `opencode/beam-free`
with variant `max`; current catalog metadata confirms zero input/output/cache
prices. The configured bridge timed out without events. Rebuilding `cline`
passed; `node dist/index.js` starts and client configuration points there.
A fresh instance of that same MCP bridge answered `BRIDGE_OK` when unrelated
OpenCode MCP connections were disabled by an environment override for that
process. Global settings were not edited; this is a successful isolation result,
not proof of which connection caused the timeout. A subsequent investigation
failed after tool activity with an upstream TLS error; review results must be
reported separately and never assumed from a successful health check.
