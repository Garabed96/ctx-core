# PRD Artifact Contract

Obsidian is canonical. v0.3.1 uses one deterministic hierarchy for every PRD and its ctx-lean gate plans.

## Deterministic paths

```text
<initiative>/
  PRD/
    <ticket-or-slug>.md
  Planning/
    <ticket-or-slug>-g<gate-number>-<gate-slug>.md
```

Use lowercase kebab-case filenames. A leading ticket token with at least two letters, such as `COR-503`, normalizes to `cor503`; other filenames use their complete stem, so `v2-redesign.md` produces the prefix `v2-redesign`. One canonical PRD owns each ticket within an initiative. Every gate has exactly one plan; every plan links back to its PRD. Links may use a unique Obsidian shortest path and omit `.md`, but their resolved vault paths must satisfy this contract.

Supporting QA, Canvas, and attachments may live elsewhere beneath the initiative. They never own lifecycle state.

## PRD frontmatter

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

PRD status is one of `draft`, `approved`, `active`, `paused`, `blocked`, `complete`, or `abandoned`. Gate status is exactly one of `pending`, `active`, `passed`, `failed`, or `blocked`; put explanations in evidence or checkpoint context, never after the status token.

## Canonical PRD

Use these eight top-level sections in this exact order:

```markdown
# <Feature> — PRD

## Outcome
<Observable user or product result.>

## Boundaries
- **In:** <included behavior>
- **Out:** <explicit non-goal>
- **Preserve:** <invariant>

## Decisions
| Decision | Rationale |
|---|---|
| ... | ... |

## Current checkpoint
- Gate: null
- Status: pending
- Verified: none
- Blockers: none
- Decision: none
- Next: <one concrete action>
- Repository: none

## Gates

### G1 — <observable vertical slice>
- **Proves:** <one-sentence acceptance>
- **Feature list:**
  - <one user-visible feature>
  - <one different user-visible feature>
- **Implementation plan:** [[<initiative>/Planning/<ticket-or-slug>-g1-<gate-slug>|G1 implementation plan]]
- **Verifier:** automated — <exact identity>
- **Status:** pending
- **Evidence:** none

## Approval
- [ ] Approved for execution

## Evidence
- None.

## Amendments
- None.
```

Every gate uses the six bold field labels in the shown order. `Feature list` contains one concise user-visible behavior per direct bullet node. It is an overview, not a numbered implementation slice, file list, architecture description, or worker assignment. `Implementation plan` contains exactly one embedded Obsidian link and no prose.

The checkpoint's seven ordered fields are state-machine owned. Additional accepted product context may follow them in the same section; transitions update the owned fields without discarding that context. `Verified` records observed truth, `Blockers` records open impediments or `none`, and `Repository` records the deterministic repository/worktree fingerprint when execution applies.

## Linked ctx-lean plan

Each plan has factual frontmatter and an explicit backlink:

```yaml
---
title: <Ticket> <Gate> — <Plan title>
type: implementation-plan
status: planned
gate: G1
prd: "[[<initiative>/PRD/<ticket-or-slug>|Canonical PRD]]"
---
```

Use these required sections in recognizable order:

```markdown
# <Ticket> <Gate> — <Plan title>

## Outcome
<Technical outcome owned by this gate.>

## Reuse decisions
- <existing seam or component to reuse>

## <Optional gate-specific contract>
<Only gate-specific detail needed before the slice.>

## Implementation slice
1. <smallest complete implementation step>

## Parallel execution contract
- **Backend/contracts/architecture owner:** <owner and contract boundary>
- **Independent UI or specialist lane:** <lane and owned surface, or exactly Not applicable>
- **Shared integration owner:** <one integration owner>
- **File ownership and no-overlap constraints:** <explicit disjoint ownership>
- **Final integration and verification pass:** <one owner and one final pass>

## Verification
- <observable proof>

## Non-goals
- <excluded work>
```

Optional gate-specific sections appear only between **Reuse decisions** and **Implementation slice**. Every field describes a distinct responsibility. The complete plan is runtime- and model-agnostic: name responsibilities, contracts, and files, not a provider, model, CLI, or reasoning effort. When an independent UI lane applies, require the `impeccable` skill; when none applies, use exactly `Not applicable`.

## Approval and lifecycle

An explicit chat approval or checked approval box is sufficient. On approval:

- check the box;
- set `approved_by`, `approved_at`, and `status: approved`;
- activate only the first eligible gate unless the approval explicitly says otherwise.

`PrdCheckpoint` validates the complete PRD and all plans before every transition or guard. Activation additionally requires the target plan to exist, link back, match its deterministic path, and satisfy its section and ownership contracts. Preceding gates must be passed and no other gate may be active.

The PRD owns product scope, decisions, gate state, and evidence. Plans own implementation detail. Amendments replace current accepted text and append one dated rationale without rewriting historical amendment entries.

## Deterministic validation

Validate without mutation:

```sh
printf '%s' '{"path":"<initiative>/PRD/<ticket-or-slug>.md"}' |
  python3 "<plugin-root>/scripts/prd_checkpoint.py" --vault-root "<vault-root>" --validate
```

Validation errors identify the PRD, gate or plan, malformed or misordered field, and expected deterministic path.

## Migration from pre-v0.3.1

Run migration only against the revision just read:

```sh
printf '%s' '{
  "path":"<initiative>/PRD/<ticket-or-slug>.md",
  "expected_revision":"r<N>",
  "occurred_at":"<ISO-8601 timestamp with timezone>"
}' | python3 "<plugin-root>/scripts/prd_checkpoint.py" --vault-root "<vault-root>" --migrate
```

Migration:

- preserves lifecycle status and `current_gate`;
- preserves decisions, gate evidence, global evidence, and historical amendments;
- reorders the eight canonical sections and six gate fields;
- adds `Blockers: none` and `Decision: none` only when the old checkpoint omitted those explicit sentinels;
- derives a missing plan path from the PRD filename, gate number, and gate heading;
- refuses with `missing_plan` and the expected path instead of fabricating plan content;
- refuses when a missing Feature list or remaining observed checkpoint field would require invented product truth;
- retains unknown old top-level sections as indented historical content beneath Amendments;
- advances the revision exactly once and validates the resulting v0.3.1 document.

Migration never leaves two canonical shapes, compatibility aliases, placeholder plans, or deprecated field spellings.

## Canvas and completion

Canvas is presentation only. Markdown remains canonical and Canvas never owns lifecycle state.

Mark `status: complete` only when every gate is passed by its named verifier and all plan and evidence links resolve. In a validated terminal state, yield and completion guards accept repository evolution because the active-work fingerprint is no longer writable; merge truth remains protected by `assert-merge` and `record-merge`.