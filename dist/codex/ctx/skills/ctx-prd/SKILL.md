---
name: ctx-prd
description: Creates and executes a durable gated product decision in Obsidian when user behavior, scope, visual direction, or staged acceptance is unsettled. Use for consequential product ambiguity requiring approval; not for settled technical work, debugging, or ordinary implementation.
---

# CTX PRD

Own one product decision from clarification through verified gates. The canonical interface is one concise Obsidian PRD plus linked evidence artifacts—not a planning stack.

## Route

Use PRD when a consequential product decision is unresolved: what users can do, scope boundaries, visual direction, safety behavior, or staged acceptance. Technical complexity alone does not qualify. If the outcome is settled, stop and use `ctx-lean`.

Preserve the user's original authorization:

- Entering PRD for an unresolved product decision authorizes creating or updating its canonical PRD as workflow state, but never source implementation.
- “Design/write a PRD” authorizes the artifact and approval conversation, not implementation.
- “Design and build/implement” authorizes Gate 1 only after explicit PRD approval.
- Approval never authorizes a later human-verifier gate before that verifier accepts its evidence.

## 1. Align silently

Inspect the prompt and available evidence for intent, observable success, constraints, and current truth. Ask nothing when these are sufficient. Never ask for repository, runtime, or artifact facts available through tools.

When a consequential product choice remains, read [Product Interview](references/product-interview.md). Ask one question at a time until the product contract and meaningful gates are decision-ready.

Completion criterion: every unresolved question can materially change user behavior, scope, a gate, or its verifier; otherwise clarification is complete.

## 2. Create or update the canonical PRD

Read [Artifact Contract](references/artifact-contract.md) and `references/runtime.md`. Resolve `ObsidianArtifactStore`; if unavailable, stop with that missing capability. Do not create a repository or local-file fallback PRD.

Create one one-page core with 1–5 observable vertical gates. Name one verifier per gate:

- automated verifier for objective runtime or contract evidence;
- human verifier for subjective product/visual judgment or irreversible release authority.

Record decisions and rationale, not implementation task lists. Link supporting evidence instead of copying it into the PRD.

Completion criterion: Obsidian contains one canonical, link-valid PRD whose outcome, boundaries, decisions, gates, and approval control can be understood in five minutes.

## 3. Capture approval

Approval may be an explicit statement in chat or the PRD approval checkbox. Record approver, timestamp, and lifecycle status in frontmatter before execution.

If the original request authorized only the PRD, stop after approval. If it authorized implementation, continue to gate execution; Gate 1 activates only through `PrdCheckpoint`.

Completion criterion: approval state in the canonical PRD matches the user's actual authorization.

## 4. Execute one gate

Before mutation, read `references/continuity-execution.md`, `references/prd-checkpoint.md`, `references/runtime-interface.md`, and `references/runtime.md`.

For the current gate only:

1. Re-read its observable outcome, constraints, named verifier, canonical path, and revision.
2. Call `PrdCheckpoint` with `activate`, or `assert-active` when already active. Source mutation waits for its attestation.
3. Implement the smallest complete vertical slice that can satisfy the gate.
4. Produce the named verifier's required evidence.
5. For an evidence matrix, read [QA Evidence](references/qa-evidence.md), create or update a separate descriptively named QA campaign note, and link it.
6. Call `PrdCheckpoint` with the resulting `update`, `block`, `fail`, or `pass` transition and re-read the returned revision.

Checkpoint every material change in execution truth before unrelated work or yield. Record current truth and durable evidence, not scenario results, implementation journals, worker reports, or task checklists.

- Automated-verifier PASS may call `pass` and advance only after the attested write.
- Human-verifier gates stop with evidence ready; call `pass` only after explicit acceptance.
- FAIL or BLOCKED remains recorded and does not advance.

Before merging PRD-owned work, call `assert-merge` at the exact expected revision. After a successful merge, call `record-merge` with the PR and commit pointer. A gate, merge, or completion claim is invalid until its checkpoint succeeds.

Completion criterion: the canonical PRD and linked artifacts state exactly what the named verifier observed, and `PrdCheckpoint` returns the attested revision before any next-gate work begins.

## 5. Resume or amend

Resume from the Obsidian lifecycle state and current checkpoint. Capture its exact revision, then verify recorded branch/worktree and runtime claims before calling `resume` or `assert-active`.

When an approved decision changes, pause active execution, then call `PrdCheckpoint` with `amend` at the exact revision. Replace only the affected decision and gate, append one material amendment with date and rationale, and preserve pending status unless implementation was separately authorized. Do not reopen settled gates unless the change invalidated their evidence.

Overall completion requires every gate passed by its named verifier, the PRD marked complete, and every evidence link resolved.