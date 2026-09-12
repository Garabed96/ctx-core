---
name: ctx-lean
description: Execute a settled outcome when the user explicitly requests CTX Lean or continues a named PRD implementation plan.
---

# CTX Lean

Use this workflow only when requested, including explicit continuation of a named PRD plan. Ordinary implementation, refactoring, debugging, and UI polish do not automatically enter Lean. Product ambiguity alone does not activate CTX PRD; discuss the missing decision without creating workflow artifacts unless requested.

Preserve the user's authorization: analysis and review stay read-only; build and fix requests authorize the requested changes. Infer routine choices from existing evidence and ask only when the answer materially changes scope, risk, or outcome.

## Standalone work

Hold the goal, boundaries, observable acceptance, and smallest complete change in session context. Inspect relevant existing patterns, implement the authorized outcome, and verify the affected behavior. Do not search for an encompassing PRD or create a plan, checkpoint, QA note, or handoff artifact for standalone work.

Use references only when they resolve a concrete need:

- [Debugging](references/debugging.md) for an unresolved failure.
- [Testing](references/testing.md) for changed contracts or requested TDD.
- [Review Feedback](references/review-feedback.md) for evaluating review suggestions.

The primary owns implementation, integration, and verification. For a substantial delegated change, prefer one implementer for the complete bounded outcome, including related files. Keep small corrections in the primary; another worker needs substantial remaining work or a genuinely independent outcome. Workers do not delegate or own PRD state. Follow the configured runtime and project policy for model selection and tool restrictions.

For frontend data architecture, use `ctx-frontend` when relevant. Visual guidance remains in the independently installed Impeccable skill and the project's existing PRODUCT.md/DESIGN.md; pass relevant guidance in a worker brief rather than requiring workers to reload a design workflow.

## Explicit PRD-owned work

When the user explicitly identifies the owning PRD or continues its active plan, read that PRD's exact path, revision, gate, checkpoint, and linked plan. Before lifecycle work, read `references/continuity-execution.md`, `references/prd-checkpoint.md`, `references/runtime-interface.md`, and `references/runtime.md`.

Use `PrdCheckpoint` to activate or assert the named gate before implementation. A refused assertion requires reconciliation; inspection and recovery remain available. Implement the linked plan's current outcome and obtain the named verifier's evidence.

Checkpoint material changes in verified evidence, blockers, decisions, or gate state before handoff or yield. Intermediate edits and unchanged reruns do not require another checkpoint. Preserve human acceptance requirements; automated results do not pass a human-verifier gate.

Pause, resume, retry, and merge use the existing lifecycle transitions. Require `assert-merge` before merging and `record-merge` afterward. Never patch lifecycle fields directly or refresh a fingerprint to conceal stale evidence.

Completion means the requested outcome has fresh supporting evidence and any owning PRD checkpoint has been saved and attested. State any remaining verification limits explicitly.
