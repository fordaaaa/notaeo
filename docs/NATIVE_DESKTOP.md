# Native desktop migration

Owner choice, 2026-10-05: rebuild with native controls throughout. macOS uses
SwiftUI; Windows uses WinForms. Owner update, 2026-10-07: the website and
browser app are removed completely. Desktop packages contain no web assets.
Mobile Settings/style work lives separately in `research-mobile`.

The first migration delivered account login, notebooks, source import/reading,
exam goals, selected revision sessions, written answers, self-ratings, saved
history, and optional AI explanations. Settings belong to the platform app,
including account and provider configuration. Later native slices added study
workspace tools, mind maps and public-web discovery; see HANDOFF.md for current
feature and verification status.

macOS also has native notebook search with source-type filters, optional
related-term matching, result counts, pagination and cited-page opening in
the source reader. Search results stay available when reading a source and
returning to Search; changing notebooks clears the search state. Cmd+F opens
and focuses Search. Windows now has its own native search controls.

`GET /api/notebooks/{id}/search/page` returns a typed page containing `hits`,
`query`, `total`, `limit`, `offset`, `has_more`, `took_ms` and `related`. It
shares the existing search engine, filters and account ownership checks.
The legacy `/search` endpoint retains its list response and timing/total
headers. Neither endpoint requires AI configuration.

Both clients own a bundled Python API process, bound to `127.0.0.1` on an
ephemeral port. The sidecar always serves APIs only.
`X-Notaeo-Desktop-Token` carries the random launch token;
account Bearer authentication remains mandatory on data routes. Browser
cookie and query-token exchange are removed. User data stays outside the app:
Application Support on macOS, AppData on Windows, under `research/data`.

Build macOS with `sh scripts/build_macos_app.sh`. It packages the Python
sidecar and SwiftUI app and verifies the ad-hoc signature. Build Windows with
`scripts/build_windows_app.ps1` on Windows; its publish folder includes the
.NET runtime and the Python sidecar. Cross-compilation on macOS can verify
Windows code and portable tests, but cannot verify native Windows controls
or produce the Windows Python sidecar.

No release, installer, signing identity, App Store submission, deployment or
database migration is part of this change. See `HANDOFF.md` for completed
checks and the remaining platform verification.
