# Review and verification — 2026-10-30

## Backend foundation

OpenCode `opencode/beam-free`, variant `max`, independently reviewed the actual
Classroom, assignment-link and dependency diff and returned **APPROVE**, session
`ses_e742c60e3ffeqX1oxF4e42uTCd`. No paid/native-agent fallback. Calls went through
the rebuilt `cline` MCP server with process-local unrelated-MCP disablement and
a `--pure` executable wrapper; global configuration was not changed.

Committed logical units:

- `13ab139`: import undated Classroom work, preserve local progress on resync,
  continue rejecting malformed non-null deadlines; refresh/recovery coverage.
- `ad6b5d9`: only filelock/setuptools lock updates; installed strict audit0.
- `c8bbe68`: assignment target/notebook ownership before writes, owned relinking
  and unlinking, matching rejection of foreign/missing/malformed notebook links.

Full backend release verifier: build/types/lint/security PASS;686/686 tests,
89.31% combined application coverage, zero security findings. `READY` describes
this local backend gate; external beta is still not approved. Initial ownership
RED5 failures/8 passes; final classes target14 passes. Full gate initially
refused touched-route branch coverage; explicit class-link/foreign-class API
cases resolved the missing coverage without changing thresholds.

## Native candidate

Behaviour RED: five Today tests failed against explicit empty implementations.
GREEN: all five pass. One URLSession transport test checks actual account and
desktop headers, snake-case bodies, list/create/complete and undated decoding.
An initial test used `request.httpBody` directly and crashed; switching to the
existing stream-aware `bodyData` helper fixed the test harness. Final native
suite112/112 passes, no skips. Scope includes local day buckets, disposal/account
guards, duplicate-save suppression, retry and persisted completion.

Signed arm64 app/sidecar build and the canonical real packaged workflow pass.
The runner compiles production Today controller/API types and proves linked
undated create/complete/reload plus cross-account link rejection against a
disposable backend. Owned processes stop and scratch is removed. This is not
full native GUI automation or release signing/notarisation.

Native independent review returned **APPROVE** in standard-agent session
`ses_e73f13f8bffeT2wDylgwjeX4hb`, Beam Free/max. Implementation committed as
`70836a9 feat: add native Today coursework workspace`. An earlier long review failed after9
tool calls with an upstream EPROTO TLS handshake error; it provided no verdict.
Do not count that execution or a successful health response as approval.
The subsequent custom-agent native/mobile review attempts each timed out after
600seconds with session unknown/events0/tool_calls0; neither approved anything.
A combined standard plan-agent retry is recorded at `/tmp/notaeo-today-standard-review.log`.
It failed before any completed step with an upstream EPROTO TLS handshake error,
not a code verdict. The smaller sequential native retry succeeded in
`/tmp/notaeo-native-standard-retry.log`; mobile review remains separate.

## Mobile candidate

Behaviour RED5 failures; initial GREEN5, expanded to7 cases including late reads
and failed-completion retry. Overall196 unit tests pass, typecheck passes and
the actual disposable-backend workflow includes coursework/ownership. All24
phone-browser interface cases pass after explicitly navigating Library where
older tests assumed it was the landing screen. Existing assertions and guest
no-network checks remain. New Today case runs on WebKit/iPhone and Chromium/Pixel.
Both native Hermes bundles export successfully.

Final measured whole-app coverage:
49.64% lines /43.66% branches. Browser checks are not native device validation;
no release build, device SecureStore/restart or live school connection is claimed.
Independent mobile review is pending. The add form was subsequently collapsed
by default to keep saved coursework visible; the final24 UI cases pass.
The standard mobile agent then timed out after600seconds with6 tool calls and
no verdict. The subsequent supplied-source review with tools disabled also
timed out after600seconds, with session unknown/events0/steps0/tool_calls0 and
empty stdout/stderr. Exact result is in `/tmp/notaeo-mobile-text-review.log`.
Native remains approved/committed; mobile source remains uncommitted.

A final mobile regression exposed notebook-library errors being hidden on the
Today tab. Both phone scenarios failed first; the common header now shows the
error and a library retry action, which clears stale errors before reloading.
All24 interface cases pass afterward, as do196 unit tests, types, the real
backend lane and both Hermes exports. This final delta is included in the
failed supplied-source review packet. No code finding or approval was returned.

## Remaining gates

Independent mobile approval before its commit; current native/mobile GUI/device
coverage; mobile dependency/release floors and toolchain; full course creation,
assignment editing, due-review/resume links and course overview. No deployment,
push, real-account write, telemetry, AI service or school credential was added.

Temporary evidence prefixes: `/tmp/notaeo-today-*`,
`/tmp/notaeo-mobile-today-*`, `/tmp/notaeo-beam-long-review.log`,
`/tmp/notaeo-native-final-review.log`, `/tmp/notaeo-mobile-final-review.log`.
