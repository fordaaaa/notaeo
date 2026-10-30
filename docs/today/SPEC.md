# Today and coursework — bounded implementation

Students should start with work they can act on: overdue assignments, today's
deadlines, upcoming work and undated tasks. Opening linked material should lead
to the existing source reader or Exam coach. A class groups coursework; a
notebook stores material. These remain distinct entities.

This milestone uses the existing authenticated assignment/class APIs rather
than the future-only dashboard calendar. Clients classify dates using the
device's current calendar/time zone; overdue means an unfinished timed deadline
earlier than now, today means a remaining deadline on the device's current day.
Completed work leaves the active lists and remains available in coursework.
Undated work never gets an invented deadline.

Acceptance:

- Missing, foreign and malformed notebook links are rejected with the same404
  before assignment writes. Valid owned links and explicit unlinking work.
- Signed-in Today loads real work/classes/material, with separate loading,
  failure/retry and empty/setup states. A student can add a task, mark it done
  and open its linked material; refresh/relaunch preserves those changes.
- Account changes clear loaded data and late responses cannot repopulate it.
  Writes bind to the original account and duplicate taps do not duplicate work.
- Notebook library remains accessible; creating a notebook does not create a
  second class. Linked notebooks can open Sources or Exam coach deliberately.
- macOS and mobile share the core journey. Label any intermediate desktop-only
  implementation honestly; do not claim parity until both are verified.

Out of this bounded milestone: new SQL/schema, reminders, external calendar
sync, LMS OAuth, citations, AI providers, guest-cloud migration, website and
Windows changes. Existing no-AI workflows and guest local notebooks remain.

Implementation order: prove/fix notebook-link ownership at the API boundary;
add native types/transport and account-bound state with failing tests; connect
macOS Today/task controls; add mobile parity and interaction checks; run each
repository's required gates, obtain independent review and commit logical units.
No push or deployment is part of the work.
