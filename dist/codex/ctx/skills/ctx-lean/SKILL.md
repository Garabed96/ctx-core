---
name: ctx-lean
description: Executes a settled technical outcome through the smallest complete vertical slice with bounded context and evidence. Use for implementation, bugs, refactors, review feedback, focused QA, or verification when product behavior and acceptance are already decided; escalate unresolved product decisions to ctx-prd.
---

# CTX Lean

Hold a context-restraint contract while completing settled work. Lean is not a lightweight planning ceremony; it investigates and executes when authorized.

## Route

Use Lean when the desired outcome is settled, regardless of code size. Technical uncertainty, architectural depth, or a difficult bug does not require a PRD.

Escalate to `ctx-prd` only when progress requires an unresolved consequential product decision about user behavior, scope, visual direction, safety, or staged acceptance.

Preserve the original verb:

- “Build,” “fix,” “change,” or equivalent authorizes execution.
- “Analyze,” “explain,” “review,” or “plan” authorizes only that result.

## 1. Align silently

Inspect the prompt and available sources for intent, observable success, constraints, and current truth. Ask only when one missing technical answer blocks safe execution or a destructive choice requires authorization. Resolve ordinary choices from repository evidence and established patterns.

Hold this ephemeral slice in session state:

```text
Goal: <one settled outcome>
Boundaries: <in scope / out of scope / preserve>
Acceptance: <observable proof>
Current slice: <smallest complete vertical change>
```

Resolve whether an existing canonical PRD encompasses the work. Prefer explicit project context and already-linked artifacts; never scan unrelated notes. When exactly one PRD owns the work, read its exact path, revision, current gate, checkpoint, and that gate's single linked plan. Verify the plan links back to the PRD and keeps Outcome, Reuse decisions, Implementation slice, Parallel execution contract, Verification, and Non-goals in canonical order.

Do not create a standalone plan, checkpoint, or handoff artifact. PRD-owned execution uses the already-linked gate plan; standalone Lean work remains ephemeral.

## 2. Apply five checks

Before mutation, verify:

1. **Requirement covered** — the slice satisfies the actual request.
2. **Smallest complete slice** — removing more would make it incomplete.
3. **Safety preserved** — named invariants and existing contracts remain intact.
4. **Proof executable** — the acceptance can be observed now.
5. **No speculative machinery** — every added seam, option, and abstraction is required by current behavior.

Correct the slice silently when a check fails. Ask only if correction changes the user's intended outcome.

## 3. Enter the appropriate evidence mode

- Bug or unexpected behavior: read [Debugging](references/debugging.md) before proposing implementation.
- New or changed observable contract, or an explicit TDD request: read [Testing](references/testing.md).
- Review feedback: read [Review Feedback](references/review-feedback.md) before accepting any suggestion.

These are proportional references, not additional workflows.

## 4. Execute and prove

Before mutation, read `references/continuity-execution.md`, `references/prd-checkpoint.md`, `references/runtime-interface.md`, and `references/runtime.md`.

When a canonical PRD owns the work, invoke `PrdCheckpoint` with `assert-active` at the exact revision before source mutation. Drift, an inactive gate, a missing or invalid linked plan, or an unavailable durable write stops PRD-owned execution; runtime guards refuse the edit until reconciled.

Implement the current slice through the existing source-of-truth path. Follow the linked plan's ownership contract without turning it into runtime-specific orchestration: lanes name responsibilities, interfaces, and disjoint files, never a provider or model. When an independent UI lane applies, it uses the `impeccable` skill. Migrate affected callers and remove obsolete paths; do not add compatibility shims unless the product contract requires them.

Run the strongest focused proof for the changed surface. For focused QA, exercise the actual requested flows and report evidence directly; Lean creates no separate durable QA note unless the user explicitly requests one.

After every material change in execution truth, invoke `PrdCheckpoint` with `update`, `block`, `resume`, `retry`, `fail`, or `pass` as appropriate before unrelated work or yield. Record only current status, verified evidence, the active decision, one next action, and the deterministic repository fingerprint; never add an implementation journal or duplicate the task plan.

Finish applicable cleanup only after the behavior is proven: focused contract tests, affected source-of-truth documentation, and obsolete scaffold removal. Do not create post-hoc checkpoint documents.

Before merging PRD-owned work, require `assert-merge`; after merging, require `record-merge`. Standalone Lean work has no PRD merge barrier.

Completion criterion: the requested observable outcome is proven, affected callsites are reconciled, every owning-PRD checkpoint is attested at its returned revision, and every completion claim is bounded by fresh evidence.

## 5. Preserve PRD continuity

The encompassing Obsidian PRD is the only durable continuity artifact. Parking invokes `PrdCheckpoint` with `pause`, preserving its current gate and replacing its checkpoint with verified evidence, the pause decision, and one next action. Resume reads that PRD first, verifies recorded repository and runtime state, then invokes `resume` for blocked/paused work or `retry` for a failed gate.

Standalone Lean work with no encompassing PRD remains ephemeral. Escalate to `ctx-prd` only for unresolved consequential product decisions; never create a mini-PRD or a separate handoff merely to persist Lean state.