# PRD Checkpoint

`PrdCheckpoint` is the sole lifecycle seam for work owned by a canonical PRD. It combines revision validation, legal gate transitions, concise evidence writes, and post-write verification behind one interface. Callers never patch lifecycle state directly.

## Interface

Input:

```text
path: exact canonical Obsidian PRD path
expected_revision: revision read by the caller
gate: owning gate identifier
transition: assert-active | activate | amend | update | block | resume | pass | fail | pause | assert-merge | record-merge
verified: concise observed evidence or durable links
decision: current material decision, when one changed
next_action: exactly one concrete next action
repository: branch/worktree or PR/merge pointer, when relevant
```

Result:

```text
path
revision
lifecycle_status
current_gate
gate_status
attestation
```

The revision format remains local to the PRD. The adapter advances it consistently with the existing note and returns the exact new value. Assertions do not advance the revision.

## Transition contract

| Transition | Required current truth | Result |
|---|---|---|
| `assert-active` | named gate is active at `expected_revision` | read-only attestation |
| `activate` | named gate is pending and execution is authorized | gate active; checkpoint created |
| `amend` | named gate is pending, or lifecycle is paused; explicit approval covers the contract change | affected decision and gate replaced; one amendment appended; gate does not activate |
| `update` | named gate is active or blocked | current verified truth replaces stale checkpoint truth |
| `block` | named gate is active | gate blocked with reason and one next action |
| `resume` | named gate is blocked or lifecycle is paused | gate active with blocker resolution evidence |
| `pass` | named gate is active and its named verifier has accepted the required evidence | gate passed; no later gate activates implicitly |
| `fail` | named gate is active | gate failed with evidence and one next action |
| `pause` | named gate is active or blocked | lifecycle paused; gate identity preserved |
| `assert-merge` | named gate is passed and repository evidence matches | read-only merge attestation |
| `record-merge` | `assert-merge` succeeded for the same revision | PR and merge commit recorded; lifecycle remains truthful |

A transition outside this table fails closed. A human-verifier gate cannot `pass` from automated evidence alone.

## Checkpoint transaction

For every call:

1. Read the exact canonical PRD and resolve its revision, lifecycle status, current gate, named verifier, and gate status.
2. Compare `expected_revision` before any write. On mismatch, return the current revision and make no change.
3. Validate authorization, transition, verifier evidence, and repository claims.
4. Patch only frontmatter lifecycle fields, the owning gate's status/evidence, `Current checkpoint`, and one material amendment when the approved contract changed.
5. Advance the revision for a write transition.
6. Re-read the PRD and verify every returned field. A partial or unverifiable write fails closed.

No source mutation, gate advancement, merge, completion claim, or yield may cross this seam while its required checkpoint is missing or stale.

## Current checkpoint

During execution the PRD contains one compact section:

```markdown
## Current checkpoint
- Gate: G2
- Status: active
- Verified: <current observed truth or evidence links>
- Decision: <current material decision or unchanged>
- Next: <one concrete action>
- Repository: <branch/worktree, PR, or merge pointer>
```

Replace stale values; do not append an implementation journal. Detailed scenarios, logs, and screenshots remain in linked evidence artifacts.
