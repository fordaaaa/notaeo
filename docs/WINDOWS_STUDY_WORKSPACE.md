# Windows study workspace

Status: approved by independent OpenCode spec review, 2026-10-06.

Bring the Windows native workspace up to the macOS study feature baseline:
find course passages, organize material, explore a cited course map, and see
clear activity feedback. Keep the installed WinForms interface and the useful
no-key flow. Existing macOS features and backend ranking remain the reference.

## Search

- Add a Search tab and Ctrl+F to focus its query field.
- Submit a topic/question or literal quoted phrase. Match the existing 500
  character limit and source-type/related-term choices.
- Use authenticated `GET /api/notebooks/{id}/search/page`, preserving query
  characters and decoding total, offset, limit, has_more and related metadata.
- Show readable snippets, titles and page references with previous/next
  pagination. Empty/error/cancel/retry states must be explicit.
- Opening a result selects Sources and scrolls its reader to the cited page.
  The reader must keep page boundaries and support sources with chunks only.
- Retain submitted search state within a notebook. Notebook/account changes,
  clearing and cancellation invalidate pending results. A late response may
  not replace newer results, restart a spinner, or reopen an old source.

## Source ordering

- A visible choice offers newest, oldest, natural name and file type.
- Remember this choice locally in a separate non-secret preferences file;
  never rewrite the DPAPI account file to persist appearance or sorting.
- Date order compares parsed UTC instants, including offsets/fractions.
  Invalid/missing dates sort last in either direction. Show added dates.
- Natural names put Lecture 2 before Lecture 10; equal keys use stable IDs.
  File type orders by kind, then natural name and ID.
- Sorting preserves the selected source and must not trigger duplicate reads.

## Mind map

- Add a native Mind map tab backed by the existing authenticated `/mindmap`
  and `/mindmap/export` routes. Decode stable IDs, children, source_id and pages.
- Display a connected notebook/source/concept tree, zoom (60–160%), scrolling,
  collapse/expand and an accessible native outline alternative. Concepts are
  extracted key terms; do not imply AI inference or semantic relationships.
- Use a portable layout model for node/connector positions and scaled bounds.
  Source text is capped/wrapped in the graph, with full text available in the
  outline/tooltips. All sources remain reachable; never silently truncate.
- Every concept/source action opens its actual source and cited page in the
  Sources tab. The visual canvas must have keyboard/accessible equivalents.
- Refresh/error/no-source/cancel states are visible. Leaving or rebinding a
  notebook invalidates pending work. Export saves Markdown through the native
  dialog with a sanitized server filename and authenticated headers only.
  Cancellation/navigation must prevent stale dialogs and writes.

## Thinking orbs

- A lightweight native control draws soft teal/blue/lilac orbs for real pending
  search/map/optional-AI work; labels describe the actual operation.
- Settings has a local three-second preview and a persistent Reduce Motion
  preference that works while logged out. Neither creates an AI request.
- Either app Reduce Motion or Windows' animations preference stops decorative
  movement. Hidden/disposed controls stop their timers. Prefer 30 fps or less,
  no accumulating GDI resources, no sound, and readable accessible labels.
- Motion/sample math lives in portable code and is tested for bounds,
  periodicity and static reduced-motion output.

## Boundaries and verification

- Accounts and the per-launch desktop token remain mandatory on data calls;
  AI keys stay optional. Keep existing 401 expiry semantics and foreign 404s.
- Reuse current backend routes, models and search ranking. Add no service,
  provider, dependency, database migration, browser renderer or local LLM.
- First write meaningful failing tests for transport/citations/cancellation,
  natural/date sorting, motion samples and graph layout/scaled bounds.
- Run targeted and full portable Windows tests, Release compilation and
  self-contained win-x64 publication using the existing .NET 10 SDK. Verify
  the macOS build required by AGENTS.md. Backend changes, if actually needed,
  require the full backend suite; no changes solely to claim backend activity.
- Independently review the spec before implementation and the final code
  before committing. Commit one logical feature at a time with conventional
  single-line messages. Update the handoff with exact results and limitations.
- macOS can compile Windows targets and exercise portable logic. Actual
  WinForms accessibility/layout, Windows animation preference, real DPAPI and
  the Windows-packaged Python sidecar require Windows verification. Do not
  report those checks as performed from macOS.

## Implementation ownership

1. OpenCode contract worker: API/DTOs and meaningful transport regressions for
   search and maps. Preserve existing API methods and session expiry behavior.
2. Once contracts compile, independent OpenCode workers own the Search screen
   with portable request state and the Mind map screen with portable layout.
   They edit separate files; root owns test-project membership and MainForm.
3. Root integrates navigation/cited reader, source ordering/preferences,
   orb control and Settings. Review each worker result and intervene when
   integration or native lifecycle behavior needs correction.
4. Root runs broader checks, obtains independent code review, and creates
   separate feature commits. No release, installer or publishing in this pass.
