# Authentication audit — 2026-10-08

Scope: repository source review and local regression tests against synthetic
accounts and temporary SQLite databases. OpenCode reviewed the changes
independently. This is not a penetration test of a live deployment or a
certification that the app is secure. No production accounts or databases were
inspected; no deployment or infrastructure settings were changed.

## Account login

The mobile client sends email and password to `POST /api/auth/login`. The
backend looks up the normalized email in SQLite and verifies its stored salted
PBKDF2-HMAC-SHA256 hash. New hashes use 600,000 iterations and a random
16-byte salt. Passwords are not stored as plaintext. A successful check creates
a random bearer session; SQLite stores its SHA-256 digest, not the raw token.
Sessions expire after 30 days. Account routes validate the bearer and notebook
ownership server-side. Mobile stores the bearer in Expo SecureStore where
available, with an in-memory fallback; it does not persist the password.
Hosted credential exchanges require HTTPS. Loopback HTTP is the local
sidecar/development path.

## Findings fixed

| Finding | Change and evidence |
| --- | --- |
| Unknown emails and Google-only rows skipped password hashing | Missing or unusable hashes now do standard KDF work before rejection. Tests observe that work. This reduces a timing shortcut; entire requests are not guaranteed to have identical timing. |
| Stored password envelopes accepted an arbitrary algorithm marker and unbounded iteration counts | Verification requires the expected algorithm, salt/digest sizes and a bounded iteration count. Forged and malformed hashes fail closed. |
| Logout parsed whitespace differently from authentication | Logout revokes the same trimmed token that authentication validated. The revoked bearer fails `/api/auth/me`. |
| Google login linked accounts by matching email, retaining the existing password and sessions | A verified Google subject identifies its own account. Email collisions return 409 without linking, overwriting another subject or issuing a session. Explicit authenticated account linking is not implemented. |
| Account/token responses lacked explicit cache protection | API responses, including handled and unhandled errors, use `Cache-Control: no-store`; privacy regressions check these headers. |
| Mobile accepted duplicate-registration HTTP 200 as login success | Authentication requires a valid backend token and user payload before entering the account UI. Failure details remain visible. |
| Late mobile 401/logout could clear a replacement session | Requests track their token and session generation; revocation only affects the matching current session. Storage mutations are serialized. |
| Mobile bootstrap deleted saved credentials for transport failures | Bootstrap checks `/api/auth/me`. A current 401 revokes the token; network/server failures keep it for a later retry while showing guest mode. |

HTTP integration tests also verify that separate registrations with the same
password receive different salted hashes, raw bearer tokens never occupy the
session-hash column, incorrect passwords mint no session, and logout invalidates
the returned token. The existing suite checks account isolation and throttling.

## Remaining boundaries

The shared in-process authentication buckets are not a distributed rate limiter:
check/record operations can race and inactive dictionary keys have no global
bound. Production needs an outer bounded limiter, a trusted proxy configuration
and deployment-specific load/abuse testing. Password reset, authenticated Google
linking, all-device session revocation and stronger password screening remain
future features. Duplicate registration still differs from successful signup in
status and payload, so the throttle limits enumeration rather than eliminating
it. These features were not added by changing the current login contract.

URL ingestion rejects private targets and validates redirects, but DNS checking
and the HTTP client's DNS resolution are separate; resistance to DNS rebinding
has not been proven. AI remains optional and off by default; any operator-side
process that reads notebook content still needs operating-system isolation in
the deployment. Live TLS, secrets, backups, retention, proxy trust and deployed
release identity were not verified in this audit.

## Verification

Public backend: `uv run pytest` — 477 passed. Mobile: `npm test` — 144 passed;
`npm run typecheck` — clean; `npx playwright test` — 20 passed across iPhone
WebKit and Pixel Chromium browser profiles. The browser checks exercise the
mobile interface against controlled backend responses; they do not replace
native device validation. `sh scripts/build_macos_app.sh` passed, including
arm64 sidecar and signature verification. The iOS simulator is running Expo Go for manual
checks. A compiled Expo 57 iOS build needs Xcode 26.4 or later; this machine
currently has Xcode 26.3.

Password guidance: [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
Authentication guidance: [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
