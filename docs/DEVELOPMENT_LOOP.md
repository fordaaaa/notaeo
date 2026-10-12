# Development loop

Owner workflow recorded 2026-10-12. Each feature gets its own loop. Current
SPEC.md and PLAN.md must state the active feature and approval status; archive
completed versions before replacing them. An agent cannot approve its own work
on behalf of the owner.

1. **PRD:** interview the owner once, with all seven questions together. Record
   problem, evidence, users/not-for, hypothesis, metrics, MVP/exclusions,
   milestones, open questions and likelihood × impact risks in SPEC.md.
   Requirements only; no file paths, libraries or implementation tasks.
   Unknowns use `TBD — needs validation via {method}`. Do not invent evidence.
   If the owner waives the interview, record the waiver and assumptions; do not
   repeatedly ask the waived questions or fabricate answers.
2. **Plan:** read the SPEC and inspect real patterns first. Write PLAN.md with
   referenced naming/error/logging/data/tests examples, proposed files, small
   independently testable phases, exact validation commands, risks, dependencies
   and estimates. Put the riskiest phase first. Stop for the owner's explicit
   `yes` or `modify: ...`; generic requests to continue do not bypass this gate.
3. **Approved phase:** implement only the approved phase. Show meaningful RED
   tests before implementation, then GREEN and refactor while tests stay green.
   Test applicable empty/invalid/boundary/error/concurrency/large-data cases;
   unit and integration coverage are mandatory. Critical user flows need E2E.
   Prove at least 80% lines and branches on touched code without suppressing or
   deleting failures. Record every changed file, commands/output, manual trial,
   phase completion and one lesson in the plan. No unrelated refactors.
4. **Fresh review:** give a separate OpenCode reviewer only the SPEC, PLAN and
   diff. It gathers diff/stat and reads every changed file fully, with relevant
   callers/imports/tests. Findings require >80% confidence. High/critical
   findings include file:line, snippet, concrete failure and why guards fail.
   Skip unrelated style preferences. End with severity counts and
   APPROVE/WARNING/BLOCK; no approval with unresolved critical findings.
5. **Security audit:** a separate OpenCode reviewer reports before changes.
   Scan dependencies and source, then review OWASP categories in context.
   Test fixtures, placeholders and public values are not automatically secrets.
   Record severity, file:line, exploit scenario, safe example, rotation decision
   and three highest-risk fixes. Do not print suspected secret values.
6. **Verify:** execute build → types → lint → tests/coverage → security → diff.
   Stop if build fails; verification does not fix code without authorization.
   Report actual outcomes and first 30 relevant type/lint diagnostics. Repeat
   after major implementation changes. The owner's exact final format is:

   `VERIFICATION REPORT — Build: PASS/FAIL, Types: PASS/FAIL (n), Lint: PASS/FAIL (n), Tests: PASS/FAIL (x/y, z%), Security: PASS/FAIL (n), Diff: (n files). Overall: READY / NOT READY. Issues to fix (numbered).`

   Fields must contain real measured counts. A missing/not-run stage cannot
   count as PASS. Represent unknown evidence explicitly and explain it in the
   issues; exact unknown-value convention is pending owner confirmation.
7. **Ship/handoff:** demonstrate every SPEC requirement, complete the plan,
   verify critical flows and security, and check migrations/rollback,
   monitoring/alerts and docs. Record PASS/FAIL and explicit blockers; unresolved
   critical findings mean no-go. Commit logical changes only after independent
   reviewer approval and required green checks. Update SPEC/PLAN/HANDOFF with
   shipped versus pending work, next three actions, open questions and exact
   resume commands. Finishing a local feature does not imply deployment.

## Context and delegation

Run the AGENTS.md OpenCode gate before code work. Use bounded OpenCode workers
at `opencode/muse-spark-1.3-contributor-free`, `xhigh`, with explicit file ownership.
Never silently substitute native agents when the bridge fails. Preserve review
independence by supplying only the review packet, not the worker's narrative.

Use Brig for fresh, compact code indexes/outlines/symbol lookup; verify snippets
and line references before relying on them. Brig's exposed tools store code
indexes, not conversation decisions. SPEC.md, PLAN.md and HANDOFF.md are the
persistent decisions/progress record. Save context before switching phases or
agents: feature, scope, approval, owned files, evidence paths and next action.
Keep raw secrets, user databases and credentials out of indexes and handoffs.

On 2026-10-12 full `research` indexing returned
`UNIQUE constraint failed: symbols.path, symbols.qualname, symbols.kind`.
Backend-only indexing succeeded using path `backend/`, slug `research-backend`;
retrieval must pass `slug`, not just `repo`. Native context remains direct source
inspection until a native index can be verified. Do not claim the full index is
fresh or erase an existing index to mask the failure.

## Safety and scope of checks

Use Python 3.12 via `uv run`; no system python3. No website/npm build exists in
this repository. Use the existing macOS packaging script with its selected
Xcode; Windows runtime and Windows Python packaging require Windows. Mobile
and hosted checks belong to their own repositories and explicitly approved
scope. Never query real user databases to satisfy an integration test. Docs-only
changes run `git diff --check` and consistency checks; do not run app tests solely
for prose or claim the full production verification gate passed.
