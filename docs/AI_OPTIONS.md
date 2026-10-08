# Optional AI

Owner direction, 2026-10-08: Notaeo helps students organise sources and revise
without relying on AI. Personal AI keys, provider selection, key storage and
direct provider adapters are removed. Settings shows service availability only.

The public local backend has no inference handler by default. Sources, local
search, selected-site discovery, reading, flashcards, guides, mind maps, basic
exam practice, recorded attempts and exports work without AI. Optional coach
requests fall back to source-based practice or the saved reference answer when
the service is unavailable or the response cannot be grounded. AI-only chat
and rewrite endpoints report unavailability rather than invent an answer.

## One service, owned by the operator

An application may inject one `AIService` through its own app state. It receives
the authenticated user's identity and a bounded prompt; model selection and
service credentials belong to the private server. Public clients receive only
authenticated `/api/ai/status` metadata: `enabled` and an optional model name.
The compatibility hosted-status route is retained. Neither exposes credentials.

The private server's existing OpenCode bridge remains the optional engine.
No new paid integration, account registration, model download or inference is
activated by this change. Its existing enable flag is off by default. Provider
free offers can change; a $0 budget does not create a guaranteed AI allowance.
Usage accounting and free hosted quotas still need implementation in the
private server before they can be advertised.

Legacy account key records are logically dropped when the updated store opens
its database. User accounts, notebooks, sources and study records are retained.
This migration does not claim forensic erasure of SQLite pages or old backups.
The JSON import skips retired AI settings.

## Quality and model research

Mocked tests validate grounding references, ownership, fallbacks and request
handling. They do not establish real explanation accuracy or student usefulness.
Native desktop apps expose optional AI in Exam coach; a general chat screen
is still pending. Read [decision-model research](DECISION_MODELS.md) for Jev
and Laya; neither is installed or integrated.
