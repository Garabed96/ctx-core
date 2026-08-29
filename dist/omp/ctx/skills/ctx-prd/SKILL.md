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

If the original request authorized only the PRD, stop after approval. If it authorized implementation, activate Gate 1.

Completion criterion: approval state in the canonical PRD matches the user's actual authorization.

## 4. Execute one gate

Before mutation, read `references/continuity-execution.md`, `references/runtime-interface.md`, and `references/runtime.md`.

For the current gate only:

1. Re-read its observable outcome, constraints, and verifier.
2. Implement the smallest complete vertical slice that can satisfy it.
3. Produce the verifier's required evidence.
4. For an evidence matrix, read [QA Evidence](references/qa-evidence.md), create or update a separate descriptively named QA campaign note, and link it.
5. Update the PRD immediately with gate status, verifier, and concise evidence links.

A gate is not complete until Step 5 is written. Never put scenario results, implementation journals, worker reports, or task checklists in the PRD.

- Automated-verifier PASS advances to the next gate.
- Human-verifier gates stop with evidence ready and wait for explicit acceptance.
- FAIL or BLOCKED remains recorded and does not advance.

Completion criterion: the canonical PRD and linked artifacts state exactly what the named verifier observed before any next-gate work begins.

## 5. Resume or amend

Resume from the Obsidian lifecycle state and current checkpoint, then verify recorded branch/worktree and runtime claims before acting.

When an approved decision changes, pause execution, amend only the affected decision and gate, and append one material amendment with date and rationale. Do not reopen settled gates unless the changed decision invalidates their evidence.

Overall completion requires every gate passed by its named verifier, the PRD marked complete, and every evidence link resolved.