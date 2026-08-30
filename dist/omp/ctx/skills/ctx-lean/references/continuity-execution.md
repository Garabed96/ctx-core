# Continuity Execution

Read this reference before mutation, delegation, gate advancement, or a completion claim.

## Preserve authorization

Honor the user's original verb.

- “Build,” “fix,” “change,” or equivalent authorizes the requested mutation.
- “Analyze,” “explain,” “review,” “design,” or “write a PRD” does not authorize implementation.
- A destructive operation needs explicit authorization for that operation.
- Do not ask again when the current request already supplies the required authorization.

## Main-first ownership

Main owns intent, architectural judgment, continuity, integration, artifact state, and final verification.

Delegate only when a bounded lane is genuinely independent and its result reduces uncertainty or elapsed work. At most two workers may participate in an ordinary run:

- one read-only scout for missing evidence;
- one implementation worker for a self-contained, non-overlapping slice.

Main defines each lane's inputs, owned files or evidence, output contract, and stop condition before dispatch. Workers do not redefine scope, approve gates, update canonical PRD state, or make completion claims for Main. Main verifies their output before use.

## Execution loop

1. Inspect the narrowest evidence that can change the decision.
2. Select the smallest complete vertical slice.
3. Make the source-of-truth change; migrate affected callers and remove obsolete paths.
4. Exercise the changed behavior through the strongest available surface.
5. When a canonical PRD owns the work, call `PrdCheckpoint` for the resulting material truth before unrelated work or yield.
6. Claim only what the observed proof establishes.

## Claim-specific proof

| Claim | Required proof |
|---|---|
| Bug fixed | The original reproduction no longer triggers after the source fix. |
| Test passes | Fresh output from the exact focused test command. |
| Build or typecheck passes | Fresh output from that exact command. |
| UI behavior works | Interaction with the actual surface; visual claims also require visual inspection. |
| Feature contract works | The changed observable contract exercised through a focused test or smoke scenario. |
| Delegated work is complete | Main inspects the delivered changes and runs the relevant proof. |
| PRD gate passes | The named verifier's required evidence exists and the canonical PRD links it. |

Partial evidence supports only a partial claim. Evidence becomes stale after a relevant mutation.

## PRD checkpoint and merge barrier

PRD-owned execution crosses one lifecycle seam: `PrdCheckpoint` in `references/prd-checkpoint.md`. Read the canonical revision before mutation; callers never patch lifecycle fields or gate evidence directly.

- Source mutation requires an attested active gate at the expected revision.
- Material blocker, resolution, evidence, verifier, pause, and failure changes require a write checkpoint before unrelated work or yield.
- A merge requires `assert-merge` against a passed gate and matching repository evidence.
- A completed merge requires `record-merge` before the branch or gate is called closed.
- Revision drift, a partial write, or an unavailable canonical store fails closed.

Standalone Lean work has no PRD checkpoint or merge barrier.

## Worktrees

Never create a worktree automatically. Explicit authorization exists only when the user asks for one or accepts a specific worktree proposal. If authorization is absent, use `AskOne`; if declined, continue in the current tree.

When already in a suitable branch or worktree, continue there without another worktree question. Record branch/worktree metadata only when the active workflow persists state.

Teardown is a separate destructive operation. Run `TeardownWorktree` only on an explicit cleanup request and preserve every runtime safety refusal unless the user deliberately overrides that exact condition.

## Resume and continuity

Resume PRD-owned work from the canonical Obsidian lifecycle state and current checkpoint, then verify recorded branch/worktree and runtime claims against current evidence.

When Lean work is encompassed by an existing PRD:

1. resolve that PRD from explicit project context or existing links;
2. capture its exact revision, current gate, and checkpoint;
3. call `assert-active` before mutation;
4. call the appropriate write transition after each material change in execution truth;
5. on park, call `pause` while preserving `current_gate`;
6. on resume, verify repository/runtime claims before calling `resume`.

If several PRDs could own the work and the choice changes durable state, call `AskOne`. Never create a compact PRD or separate handoff for Lean work. Standalone Lean work with no encompassing PRD reconstructs from the prompt, repository, and runtime evidence.