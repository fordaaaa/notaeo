# Jev and Laya: evaluation candidates

Research checked 2026-10-08. These models are not installed or integrated.

[TypeSafe Jev](https://docs.typesafe.ai/introduction) takes unstructured state
and returns typed choices, scores and probabilities. It does not generate
free-form explanations. Its maker currently advertises input pricing of
US$0.042 per million tokens; an inexpensive API is still a paid service.
Source: [TypeSafe's announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

[Laya](https://github.com/NandhaKishorM/laya) is an independent open decision
model with Apache-2.0 licensing, available checkpoints and CPU/GPU inference.
It supports choices, scores and yes/no decisions without generated text. It
is not Jev's released weights. Open weights remove a model-provider fee, but
inference still consumes hardware, memory and operator time. The project's
published timings and accuracy are claims from its own benchmark conditions;
they are not measurements on Notaeo course material.

Potential uses to evaluate: subject tagging, relevance scoring after lexical
retrieval, or matching passages to a selected revision topic. These are research
ideas, not shipped features. A correctly typed decision can still be wrong;
confidence needs checking against held-out examples. Do not use either model
to fabricate explanations, readiness percentages or grades.

Before adoption, freeze a public/synthetic course fixture set with relevant,
irrelevant, ambiguous and long-document examples. Compare against the existing
lexical ranking, measure false positives, retrieval quality, latency and memory,
and choose an abstention threshold from held-out data. Do not send real student
material or purchase inference for this experiment without an explicit task.

Keep the current no-AI path available. No model is downloaded into the desktop
or mobile apps, and the no-local-LLM decision remains unchanged. If a future
decision model helps, choose its deployment separately from optional text AI.
