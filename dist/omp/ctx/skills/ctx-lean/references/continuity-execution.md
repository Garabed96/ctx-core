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
5. Record only workflow state and durable evidence required by the active workflow.
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

## Worktrees

Never create a worktree automatically. Explicit authorization exists only when the user asks for one or accepts a specific worktree proposal. If authorization is absent, use `AskOne`; if declined, continue in the current tree.

When already in a suitable branch or worktree, continue there without another worktree question. Record branch/worktree metadata only when the active workflow persists state.

Teardown is a separate destructive operation. Run `TeardownWorktree` only on an explicit cleanup request and preserve every runtime safety refusal unless the user deliberately overrides that exact condition.

## Resume and handoff

PRD resume reads the canonical Obsidian lifecycle state and then verifies its recorded branch/worktree against current Git state.

Lean reconstructs from the current prompt, repository, and Git state. It persists nothing by default. When the user explicitly requests a handoff, call `WriteGitHandoff` with exactly:

```text
Goal: <one sentence>
Verified: <fresh evidence or “none”>
Blocked: <external blocker or “none”>
Next: <one concrete action>
Branch: <exact branch>
```

On resume, ignore a Git-local handoff whose Branch does not match. After its contents are incorporated, remove it unless the user asks to retain it.