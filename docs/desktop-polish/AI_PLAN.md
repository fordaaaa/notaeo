# Optional AI for the exam coach

Planning only. No provider, account, key, model, hosted setting or allowance is
changed by this iteration. Source search, reading, basic practice, revision and
exports continue to work when AI is unavailable. Student usefulness and real
inference quality are unvalidated; the OpenCode product rating is not evidence
of either. Do not confuse coding workers with the app's managed AI service.

## Existing foundation to reuse

The public app already has authenticated AI availability, optional coach practice
and explanations, source evidence, model provenance and basic fallbacks. Native
Settings is availability-only. Personal keys/provider selectors and local LLMs
remain excluded. General native conversation UI remains future work.

The private server owns hosted service configuration, credentials, upstream
routing and future allowances. Its snapshot must be checked for coach/retrieval
contract parity before enabling a hosted client. Never run a blind public-repo
sync or assume that local sidecar tests prove hosted behavior.

## First capability: understand an answer from course evidence

Proposed student task: after answering a revision question, ask why the reference
answer follows from the course material, open its cited page, then retry the
question. Build on the existing coach explanation flow before adding an empty
general chat tab. A future reader action can explain the current passage using
the same evidence and ownership rules.

Requirements:

- A deliberate action initiates each request. Identify what source evidence is
  sent; no automatic external transfer on app startup, reading or notebook open.
- Return source/page references that actually belong to the active notebook.
  Unsupported claims must not be labeled source-grounded. If evidence is
  missing, say so and offer local search/the source passage.
- Keep basic reference answers and practice accessible during provider outages.
  Show whether an explanation came from basic material or the managed service.
- Allow cancellation/retry without a late answer replacing another question,
  notebook or account. Use bounded request/context sizes and existing ownership.
- Show only truthful activity states. AI orbs indicate a pending request, with
  elapsed time/cancel when implemented; do not invent progress percentages,
  provider events or a transcript of private model reasoning.
- A failed request must not expose upstream URLs, credentials or internal errors.

## Sequence and acceptance gates

| Phase | Outcome | Binary go/no-go evidence |
| --- | --- | --- |
| A — baseline evaluation | Know when current explanations help or fail | A versioned synthetic course fixture and expected source/page evidence exist; supported, absent, contradictory and irrelevant questions have reviewed expected outcomes |
| B — contract and failure handling | One trustworthy explanation interaction | Tests reject foreign/missing citations, preserve a basic answer on unavailable/invalid AI, and prevent stale account/question responses; no key/provider input is restored |
| C — native trial | Student can assess and act on an explanation | On a disposable account, explain → open cited page → retry works; disabled/offline, cancel, retry, expired session and notebook switch are demonstrated |
| D — hosted readiness | Optional service has an explicit operating boundary | Hosted parity, context/privacy disclosures, bounded concurrency, durable allowances/accounting and abuse policy are verified before external invitations |

Use unit tests for evidence/selection logic and API integration tests with a
fake injected service. Real-provider evaluation is separate, opt-in and uses
public/synthetic course material. Mock success must never be reported as an
actual model quality benchmark. Performance targets, acceptable citation/answer
scores and operating capacity are TBD — needs validation via baseline fixture
measurement and owner trials, rather than invented benchmark thresholds.

## Later candidates, after the first loop works

1. Source-grounded hint before revealing an answer, followed by a cited
   explanation. Preserve the student's written attempt; no automatic grading.
2. Practice variation on topics explicitly marked Revise again. Require valid
   source links and the current time budget; retain basic practice fallback.
3. A question box scoped to the selected notebook, using the proven explanation
   contract. General agent actions, scheduling and unsupervised edits stay out.

## Budget, evaluation and open questions

The budget remains $0. A free upstream tier does not establish a dependable
entitlement or permit an unlimited public service. No free usage amount or
funding requirement is invented here. Operator capacity, terms, retention and
availability need validation before choosing/enabling an upstream service.

Which explanation actually helped a learner, what was unsupported, and whether
the cited passage was useful are trial questions. Store no new telemetry or
student data without an explicit design and consent decision. Numeric quality
and latency goals remain TBD — needs validation via the fixture baseline and
owner review. Do not introduce exam-readiness/mastery scores or AI grading
until their meaning and evaluation are established.

Next implementation candidate: Phase A evaluation fixtures and contract review,
followed by a bounded Phase B plan grounded in the existing API/client code.
