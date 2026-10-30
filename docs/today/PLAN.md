# Today task foundation

This implements the first connected task journey within the broader student
workspace direction. It is not the complete course/planner/writing milestone.

1. Prove assignment notebook-link ownership before exposing links. RED5 failures
   reproduced foreign/missing links and validation before target ownership.
   Check the target first and use the existing notebook ownership helper before
   create/update. Preserve owned relinking and explicit unlinking. The backend
   changes are committed in `c8bbe68`; full gate686/686,89.31%combined, security0.
2. Native types, request transport, local-day grouping and account-bound
   controller. Five behaviour tests failed against stubs, then passed after
   implementation; one transport test exercises real URLSession headers/bodies.
   Today is the landing/sidebar destination, with add/complete/reopen and linked
   Sources/Exam coach navigation. Existing courses can be selected; course
   creation and general assignment editing are follow-up scope.
3. Compile the same controller/API types into the packaged native workflow.
   Create a linked undated task, complete it, reload through a fresh controller,
   and prove another account cannot read or create a link to its material.
   Full native suite112/112 and signed arm64 packaged workflow pass locally.
4. Mobile account landing offers Today/Library; guests retain the existing
   local notebook path. Use the same APIs, device-local day boundaries and
   explicit validated local date/time input. Keep coursework visible ahead of
   the optional add form. Controller tests cover writes, retry, disposal and
   late account results. Phone-profile interface checks cover invalid dates,
   material selection, saved completion across navigation and source opening.
   Real-backend lane includes task creation/completion and ownership.
5. Review client patches with OpenCode Beam Free at max, run required tests and
   bundle/build checks and commit each logical implementation only after an
   actual approval. Record model errors honestly. No push/deployment.

Still open after this bounded foundation: native/mobile course creation,
assignment editing, due review/resume navigation, a complete course overview,
native device GUI/restart/SecureStore checks, native release tooling and mobile
dependency/coverage release gaps. School OAuth and material extraction remain
separate goals. Neither local test fixtures nor browser profiles establish a
live school connection or mobile store readiness.
