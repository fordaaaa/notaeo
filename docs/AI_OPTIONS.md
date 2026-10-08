# AI options and current limitations

Checked 2026-10-08. Notaeo's current budget is $0 for hosted AI. The native
exam coach can generate source-linked practice and explanations using a
user's own provider key in Settings. Reading, search, basic practice and
exports remain useful without one. Keys are never returned by the settings
API; the local SQLite database stores configured keys, so protect the app's
data directory and its backups.

The native desktop apps currently expose AI through Exam coach; they do not
yet have a general chat screen. Backend chat APIs are not a shipped native
chat experience. Provider response handling and grounding have mocked
regression tests; real answer quality and usefulness still need evaluation.

## Free provider access

For an adult evaluating BYOK, Groq is already supported. Its current
[free-plan limits](https://console.groq.com/docs/rate-limits) for GPT-OSS 20B
include 200,000 tokens/day and 8,000 tokens/minute across an organization.
Requests can hit token limits before the request count is exhausted. Exact
account limits and availability can change. Read its
[services agreement](https://console.groq.com/docs/legal/services-agreement)
and [data controls](https://console.groq.com/docs/your-data); provider accounts
require adult eligibility. Do not assume a student's uploaded content stays
on their device after they deliberately request an AI feature.

[OpenRouter](https://openrouter.ai/docs/api_reference/limits) also has free
model variants with account-wide request caps and provider-specific data
policies. Fallbacks can choose another same-provider model when one fails;
availability is not guaranteed. BYOK costs and provider quotas are the user's.

[Gemini's API terms](https://ai.google.dev/gemini-api/terms) prohibit applications
directed towards, or likely accessed by, people under 18. Unpaid content can
be used to improve Google products and reviewed by humans, with regional
exceptions. Although its adapter remains available, do not choose it as the
default for a school-age rollout. Provider eligibility needs to be settled
before enabling hosted AI for minors; no age policy or provider account is
created by this document.

## Hosted allowance

Storage quotas, free hosted AI credits, provider billing, usage counters and
startup-credit applications belong to the separate private server project.
There is no bundled cloud-storage allowance or guaranteed hosted AI credit
in this app. A provider's free tier is shared capacity, not an unlimited
per-student entitlement. A paid fallback must never be used to make a free
hosted offer appear unlimited. Local flows remain independent of hosted plans.
