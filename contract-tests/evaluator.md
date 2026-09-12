# CTX Routing Contract Evaluator

Evaluate only; do not execute a workflow or mutate anything. Inspect the composed skill descriptions and invocation policies. Read only the skill bodies or references needed to classify each case.

For each case return its `id` and one `actual` object with exactly these fields:

- `route`: `ctx-prd`, `ctx-lean`, `ctx-discuss`, `ctx-align`, `ctx-frontend`, or `none` (no CTX skill)
- `authorization`:
  - `artifact-only` — may create/update the requested product artifact but not implement source changes;
  - `execute-after-approval` — source execution begins only after explicit PRD approval;
  - `execute-now` — the requested implementation, PRD checkpoint, or approved-gate action is currently authorized;
  - `analysis-only` — inspect, test, and report only; no source mutation or durable workflow artifact.
- `durable_state`: `prd`, `qa-campaign`, or `none`
- `mode`: `interview`, `artifact`, `gate`, `checkpoint`, `implementation`, `debugging`, `testing`, `review`, `focused-qa`, or `discussion`
- `worktree`: `explicit` only when the prompt itself authorizes creation; otherwise `not-authorized`

Lean and PRD require explicit requests, including continuation of a named PRD gate or plan. Ordinary tasks route to `none`, even when complex. A request to write a PRD is explicit PRD work; an open product discussion is not. Route requests to discuss options to Discuss, requested prompt review to Align, and frontend data/cache architecture to Frontend. A build request can require a clarifying discussion without activating Discuss. Visual-only work does not use Frontend. Implementation authorization exits discussion without activating Lean.

A design-and-build request without a requested PRD authorizes implementation (`execute-now`), but an unresolved material decision can make the immediate mode `discussion`; it does not authorize a durable artifact. For explicit PRD design-and-build, use `execute-after-approval`. Preserve read-only and human-verifier boundaries. Never infer worktree authorization from task scope. A settled fix under an explicitly named PRD plan uses Lean and maintains that PRD; a request to resume the PRD's gated lifecycle uses PRD.

Return JSON only. Do not include rationale or fields outside the contract.
