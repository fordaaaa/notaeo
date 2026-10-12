# Proposed v1: production verification gate

Status: draft; interview waived by the owner on 2026-10-12; implementation
not approved. The owner has not tested enough to supply product evidence. This
is the proposed first feature for the requested development loop. Prioritizing
it over account recovery or a student-facing feature is TBD — needs validation
via explicit plan approval.

## Problem

The maintainer needs an ordered, repeatable assessment of whether a change is
ready to release. Existing individual build/test checks do not establish the
requested type, lint, coverage, security and release gates together. The time
lost or incidents caused by this gap are TBD — needs validation via maintainer
observations and release history. Student pain is not inferred from this gap.

## Evidence

- Owner request: “make a loop” and continue development toward production.
- Repository inspection found individual backend/native build and test checks,
  but no configured backend type checker, linter or coverage thresholds.
- Historical passing tests and local packaging do not establish today's gate
  or live production readiness.
- Quotes from students, release incidents and usage metrics are TBD — needs
  validation via maintainer trials and an agreed evidence sample.

Problem impact remains an assumption; the tooling gap is observed.

## Users (+ Not-for)

Notaeo's maintainer and delegated coding/review agents preparing native desktop
changes for release. Other maintainer segments are TBD — needs validation via
owner confirmation. This developer feature does not validate a student segment
or replace student-facing product discovery. Not for end-user study workflows,
public website distribution or automatic production deployment.

## Hypothesis

We believe an ordered verification gate with explicit failure evidence will
help Notaeo maintainers identify release blockers before shipping. We'll know
when deliberately failing or incomplete checks cannot produce a READY result,
and complete passing checks produce an accurate, reproducible report.
The effect on release incidents or maintainer effort is TBD — needs validation
via a baseline and subsequent maintainer trials.

## Success metrics

| Metric | Target | How measured |
| --- | --- | --- |
| False READY result after a failed, missing or incomplete mandatory check | Zero, required by the requested gate | Seeded failure, unavailable-tool and interrupted-run scenarios |
| Report accuracy | All executed checks represented with their actual outcomes | Compare reports to captured check results and independent review |
| New/touched-code coverage | At least 80% lines and 80% branches | Coverage report for the declared approved change; exclusions must be visible |
| Suite coverage | 80%+ requested; denominator TBD — needs validation via scope approval | Full declared suite report; no narrowing to hide uncovered application code |
| Maintainer effort and release regressions | TBD — needs validation via baseline measurements and follow-up trials | Agreed observations before/after use |

## Scope

### MVP — proposed boundary, pending confirmation

- Assess build first, then types, lint, tests with coverage, security and diff.
  A failed build stops execution of subsequent checks.
- Report actual test counts, coverage, errors/warnings and changed-file count;
  preserve unknown/not-run outcomes without inventing numeric evidence.
- Emit the requested verification report and numbered actionable issues.
  A missing mandatory check cannot count as PASS or yield READY.
- Verification and security audit report findings before fixes. Review includes
  confidence, severity counts and a verdict; unresolved critical findings block
  release.
- Support the requested approval boundary, tests-before-implementation, one
  approved phase at a time, independent review and durable handoff.
- Preserve account ownership, no-AI functionality and secret/data privacy.
- First verification scope is proposed as the public backend with separately
  documented native desktop checks. Confirmation is TBD — needs validation via
  explicit plan approval.

### Out of scope

Website restoration, personal AI keys, local models and paid infrastructure are
excluded by existing owner decisions. Automatic implementation approval and
automatic fixes during verification are excluded by this workflow. New study
features, account recovery, hosted/mobile changes and deployment are not part
of this proposed gate MVP unless the owner changes its scope.

## Delivery milestones

| Business outcome | Status |
| --- | --- |
| Maintainer agrees which release boundary and evidence establish readiness | Pending |
| Maintainer can reproduce an honest blocker report for the approved scope | Pending |
| Independent reviewers confirm failure detection and privacy boundaries | Pending |
| A release candidate satisfies all declared requirements and launch checks | Pending |

## Open questions

Which feature and platform come first? Is backend verification sufficient for
this MVP or must native runtime evidence be included? What is the complete suite
coverage denominator? What historical incidents and baseline effort support the
hypothesis? What changes may address existing failures? Who owns operational
monitoring and the hosted release decision? All are TBD — needs validation via
plan approval, baseline measurements or deployment-owner review as applicable.
The waived interview will not be asked again for this loop.

## Risks

| Risk | Likelihood × impact | Mitigation |
| --- | --- | --- |
| Existing failures make a complete gate larger than expected | TBD — needs validation via baseline checks × blocks release | Report baseline before approving remediation; keep it explicit |
| Passing local checks are mistaken for production readiness | TBD — needs validation via maintainer trial × unsafe release | Separate local checks from native runtime and operational evidence |
| Coverage denominator hides untested code | TBD — needs validation via coverage review × misleading confidence | Declare measured scope and inspect omissions |
| Reports expose secrets or real student data | TBD — needs validation via synthetic adversarial tests × privacy breach | Bound scans, redact values, keep tests synthetic |
| Context is stale after interrupted/delegated work | TBD — needs validation via resume trial × incorrect continuation | Record scope, approval, evidence and next action durably |

Validation status: problem assumption; users concrete (maintainer, not a
validated student segment); metrics defined for correctness, outcome metrics TBD.
Suggested next step: plan from this SPEC, then obtain explicit plan approval.
