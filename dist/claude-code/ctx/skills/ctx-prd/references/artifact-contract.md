# PRD Artifact Contract

Obsidian is canonical. The default root is `CTX PRDs/`; honor an explicitly configured project root instead.

## Adaptive layout

Start with a flat note when no durable sibling artifact is expected:

```text
CTX PRDs/<Feature> — PRD.md
```

Use a folder when the effort has QA campaigns, Canvas reviews, attachments, or other durable evidence:

```text
CTX PRDs/<Feature>/
  <Feature> — PRD.md
  <Feature> — <Campaign> QA.md
  <Feature> — <Decision> Review.canvas
  Attachments/
```

If a flat PRD later gains siblings, use `ObsidianArtifactStore` to move it into the folder while preserving links. Never use generic filenames such as `PRD.md` or `QA.md`.

## Minimal frontmatter

```yaml
---
title: <Feature> — PRD
type: ctx-prd
status: draft
revision: r1
current_gate: null
branch: null
worktree: null
approved_by: null
approved_at: null
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

PRD status is one of `draft`, `approved`, `active`, `paused`, `blocked`, `complete`, or `abandoned`. Gate status is one of `pending`, `active`, `passed`, `failed`, or `blocked`.

Keep frontmatter factual and queryable. `paused` means intentionally deprioritized with a resumable checkpoint; `blocked` means an external prerequisite prevents progress. Do not encode implementation tasks, worker state, or duplicated evidence there.

## One-page core

Use only the sections that carry a current decision:

```markdown
# <Feature> — PRD

## Outcome
<Observable user or product result.>

## Boundaries
- In: <included behavior>
- Out: <explicit non-goal>
- Preserve: <invariant>

## Decisions
| Decision | Rationale |
|---|---|
| ... | ... |


## Current checkpoint
- Gate: null
- Status: pending
- Verified: none
- Decision: none
- Next: <one concrete action>
- Repository: none

## Gates
### G1 — <observable vertical slice>
- Proves: <one-sentence acceptance>
- Verifier: automated | human — <identity or role>
- Status: pending
- Evidence: none

## Approval
- [ ] Approved for execution

## Amendments
- None.
```

Keep the core readable in five minutes. Put research, exhaustive edge cases, implementation details, screenshots, and scenario matrices behind links.

## Approval and lifecycle writes

An explicit chat approval or checked approval box is sufficient. On approval:

- check the box;
- set `approved_by` and `approved_at`;
- set `status: approved` when implementation is not authorized;
- set `status: active` and activate G1 when implementation is authorized.

After every gate attempt and material Lean change inside this PRD, call `PrdCheckpoint` as defined in `references/prd-checkpoint.md`. Replace `Current checkpoint` with fresh gate status, verified evidence, the active decision, one concrete next action, and current repository pointer. Parking preserves `current_gate`; resuming requires repository and runtime verification. The PRD is stale until the revision-safe checkpoint succeeds and is re-read.

## Canvas

Canvas is presentation only. Create a descriptively named Canvas when visual comparison, images, Factory references, or human visual approval materially improves a gate. Keep one-sentence choices and links in Canvas; Markdown remains canonical and Canvas never owns lifecycle state.

## Amendments

Replace stale current text, then append one concise entry for a material approved change:

```text
YYYY-MM-DD — G<N> changed <old> → <new> because <reason/evidence>.
```

Do not log implementation churn. Reopen only evidence invalidated by the amendment.

## Completion

Mark `status: complete` only when every gate is passed by its named verifier and all PRD evidence links resolve.