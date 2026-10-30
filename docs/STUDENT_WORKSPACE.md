# Notaeo student workspace — direction update, 2026-10-22

Implementation update, 2026-10-30: a local Today task foundation now connects
assignment creation/completion and linked material/study in macOS and mobile.
The backend ownership prerequisites are committed; client candidates await
independent approval. [Current evidence and scope](today/REVIEW.md). The original
gap assessment below records the October22 state; the complete course/planner,
writing/reminder and due-review/resume directions are still unfinished.

Owner feedback: both mobile and macOS feel bare bones. The intended direction
is engaging study informed by Gizmo, within a workspace that connects planning,
alerts, citations and paper writing. This expands the earlier exam-coach-only
positioning. It does not change account ownership, optional AI, native apps,
the $0 budget, or the private hosted boundary.

This is a product direction and proposed delivery sequence, not an implemented
redesign or evidence of product-market fit. The recent reliability fixes remain
useful, but do not establish that either app is compelling or complete.

## Product promise

**Your coursework, connected.**

Notaeo is a student workspace that connects course material, study sessions,
deadlines and cited writing. A student should be able to move from what is due
to the relevant material and actual work, without reconstructing the context
across unrelated tools.

Gizmo's documented sequence is import → practice → deeper explanation, with
progress and social features. The useful reference here is a clear learning
loop, not a requirement to copy its assets, subscriptions, multiplayer, XP or
every import type. [Official Gizmo overview](https://help.gizmo.ai/en/articles/14472668-how-does-gizmo-work).
"Notion oriented" means organized pages and connected coursework in this
proposal; it is not authorization to build an arbitrary database/formula/plugin
platform before the student workflows work.

## What the actual apps are missing

The native macOS main window is organized around selecting a notebook and then
choosing Sources, Search, Discover, Site index, Mind map or Exam coach. There
is no Today, assignment planner or writing surface in that shell. Mobile starts
with a plain notebook list and places notes among seven study tabs. A new
student sees containers and tools rather than their course workload.

The backend already contains useful foundations; existence is not completeness:

| Capability | Grounded implementation | Actual gap |
| --- | --- | --- |
| Dashboard | `backend/api/dashboard.py:18` | No main native client home consumes it; future-only date buckets are not an overdue task list |
| Classes and assignments | `backend/api/classes.py:29,63,80,84` | No desktop/mobile assignment workflow; linking and ownership must be verified before exposure |
| Calendar | `backend/api/classes.py:112`, `backend/core/dashboard.py:66` | UTC/server-time buckets, horizon limits, undated/overdue handling and completed-work display need a deliberate client contract |
| Due review across notebooks | `backend/api/review.py:18` | No direct daily-study destination from the main native shell |
| Notes with source references | `backend/api/notes.py:32,74` | Mobile buries editing under Study; macOS exposes no notes editor; chunk references are not formatted bibliographies |
| Outlines and exports | `backend/api/outlines.py:53`, `backend/core/export.py` | Not a connected paper-writing workspace; source metadata, citation insertion and paper export remain work |
| Practice | `backend/core/study.py`, `backend/api/coach.py` | Existing basic practice needs a stronger interaction, a clear next session and demonstrated question quality |
| Device reminders | No existing native reminder scheduler found | New feature: permission, scheduling, editing/cancellation and honest delivery behavior |

Do not repeat the earlier mistake of counting endpoints, test passes or visual
effects as a finished product. Do not describe the existing note references as
APA/MLA support or the calendar as notification delivery.

## Connected experience

| Destination | What the student does |
| --- | --- |
| Today | See due and overdue work, review due material, resume an unfinished session or document |
| Courses | Open a course overview with its assignments, linked material, writing and practice |
| Planner | Add/edit/check off assignments, see an agenda/week, plan study time and configure reminders |
| Study | Start a focused practice session, attempt before revealing, revisit mistakes, inspect source evidence |
| Writing | Work from an outline and sources to a saved draft with citations and an exportable reference list |

Example acceptance story: an essay due Friday appears on Today. Opening it
shows the associated course material and the student's draft. They collect a
passage, cite it in their own writing, and return to the assignment. A Biology
exam remains visible alongside it, with due review and a revision session they
can resume. Completing work updates the same planner, rather than a disconnected
checklist. Reminder delivery is a distinct capability to implement and validate.

These are proposed capabilities, not assertions that the current apps support
this whole journey. Both clients share concepts, not identical screen density:
desktop gets source-and-document space; mobile prioritizes quick capture,
agenda, reading and focused study while retaining access to writing.

## First visible milestone: Today and a course workspace

Build this before another isolated polish pass:

1. Replace the signed-in notebook-list landing experience with Today: unfinished
   and overdue assignments, next deadlines, due reviews and resume actions.
   Provide an honest first-run setup that adds real course material/work.
2. Add a course/material overview connecting existing assignments, notebooks and
   study sessions. A class and notebook are distinct existing entities: a class
   groups scheduled work; a notebook holds material; an assignment can link to
   a notebook. Do not silently rename or duplicate them. Initially expose only
   proven links; preserve unlinked material in the library. A general direct
   class–notebook relationship is an explicit design question, not an existing
   field.
3. Let students add/edit/complete a dated or undated assignment and open its
   linked material. Today and an agenda show the same persisted records after
   relaunch. Use existing APIs first; narrowly fix demonstrated contract gaps.
4. Make due review and existing exam-coach sessions directly reachable. Surface
   actual saved activity, not invented mastery, fake example deadlines or empty
   "coming soon" destinations masquerading as finished features.

Implement the shared contract first, then macOS and mobile sequentially. A
milestone is not complete until both clients expose the agreed core journey;
desktop-only completion must be labeled as such. No website or Windows scope.

Risks to investigate before coding: the dashboard/calendar currently query
assignments from the current moment forward and therefore cannot alone power
overdue work; days are bucketed using server/UTC dates; assignment notebook links
need cross-owner rejection tests at create/update; list endpoints may need bounds
as accounts grow. These are specific investigation targets, not claims of fixes.

## Following milestones

1. **Better daily study:** focused question presentation, clear attempts and
   completion, missed-topic review, supported question formats and visible source
   links. Manual cards and basic practice stay useful without AI. Evaluate
   question quality with actual course fixtures; self-rating is not grading.
2. **Writing and citations:** promote documents out of the study-tool menu;
   connect source reader, outline, saved draft and citation insertion. Source
   metadata must be reviewable. Formatted references need a separate metadata/
   formatting design; never invent authors, dates, pages or bibliographic fields.
3. **Planning and alerts:** agenda/week planning and explicit opt-in local
   reminders linked to real deadlines. Update/cancel reminders on edits and
   completion. Time zones, permission denial, offline edits and closed-app
   behavior need device tests. Push, external calendar sync and automatic
   cross-device delivery are separate scope, not promises of a local scheduler.

Writing, alerts and study are part of the intended product; this sequence is an
implementation boundary, not removal of those requirements. Optional managed AI
can help explain a passage or vary practice after its evidence/fallback contract
is proven. No personal provider keys, local LLMs, unlimited free AI entitlement,
automatic paper generation or private model-reasoning display is introduced.

## Evidence, metrics and open questions

The owner's repeated bare-bones assessment is direct product feedback. The
navigation and missing client connections above were inspected in the repos.
Independent OpenCode critique agreed on the disconnected workspace problem.
Its claim that nearly everything already exists was rejected: paper writing,
bibliographic metadata, notification delivery and stronger study interactions
remain substantial work. It also suggested overdue data from endpoints that
currently exclude it; do not implement that assumption.

Initial segment: students managing several courses with both exams and written
assignments; education level and device mix are TBD — needs validation via owner
course-material trial and student interviews. Broader demand is an assumption.

Technical acceptance for the first milestone: a student can create work, see it
in Today/agenda, open its material, perform/resume study, mark work complete and
recover the same state after relaunch; a second account cannot read/link it.
An empty account gets actionable setup. Error/loading/empty states are distinct.
Dates near midnight and a missed deadline remain understandable on both clients.

Outcome metrics: time to a first useful study/work session, unaided completion
of the essay-and-exam scenario, and return use of Today. Targets are **TBD —
needs validation via timed owner trials and student observation**. Do not add
telemetry or claim that an agent's usefulness rating proves student adoption.

Open decisions that can change scope: direct class/material grouping; date-only
versus timed assignments and user time zone; paper export/citation style priorities;
reminder delivery expectations; offline versus cross-device consistency. Resolve
these in the bounded implementation SPEC/PLAN, using explicit TBDs where needed.

Validation status: owner problem observed; initial segment concrete but untested;
technical acceptance defined; outcome metric targets TBD. This replaces the next
feature priority, not the pending security/device/release gates.
