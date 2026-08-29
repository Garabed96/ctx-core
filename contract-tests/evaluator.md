# CTX Routing Contract Evaluator

Evaluate only; do not execute a workflow or mutate anything. Read the composed `ctx-prd` and `ctx-lean` skills and their references before classifying cases.

For each case return its `id` and one `actual` object with exactly these fields:

- `route`: `ctx-prd` or `ctx-lean`
- `authorization`:
  - `artifact-only` — may create/update the requested product artifact but not implement source changes;
  - `execute-after-approval` — source execution begins only after explicit PRD approval;
  - `execute-now` — the requested implementation, handoff, or approved-gate action is currently authorized;
  - `analysis-only` — inspect, test, and report only; no source mutation or durable workflow artifact.
- `durable_state`: `prd`, `qa-campaign`, `git-handoff`, or `none`
- `mode`: `interview`, `artifact`, `gate`, `implementation`, `debugging`, `testing`, `review`, `focused-qa`, or `handoff`
- `worktree`: `explicit` only when the prompt itself authorizes creation; otherwise `not-authorized`

Use product ambiguity—not code size—to distinguish PRD from Lean. Entering PRD for unresolved product ambiguity creates or updates its canonical PRD even when implementation is not authorized. An explicit “design and build” request is `execute-after-approval`, not `artifact-only`. Explicit TDD is `testing`, not ordinary implementation. A standalone QA request is Lean with `focused-qa`; a durable QA campaign for an active PRD gate is PRD with `gate`. Never infer worktree authorization from task scope.

Return JSON only. Do not include rationale or fields outside the contract.