# PRD Checkpoint

`PrdCheckpoint` is the sole lifecycle seam for work owned by a canonical PRD. It combines revision validation, legal gate transitions, concise evidence writes, and post-write verification behind one interface. Callers never patch lifecycle state directly.
The packaged `<plugin-root>/scripts/prd_checkpoint.py` command implements this seam as a locked compare-and-swap state machine. It accepts one JSON request on stdin, mutates one note beneath `--vault-root`, atomically replaces the complete note, and returns a content-hash attestation. Runtime adapters resolve the absolute installed plugin root before calling the command; models never patch lifecycle fields themselves.


## Interface

Input:

```text
path: exact canonical Obsidian PRD path
expected_revision: revision read by the caller
gate: owning gate identifier
transition: assert-active | activate | amend | update | block | resume | retry | pass | fail | pause | assert-merge | record-merge
verified: concise observed evidence or durable links
blockers: current open blockers, or none
decision: current material decision, when one changed
next_action: exactly one concrete next action
repository: deterministic repository fingerprint, or PR/merge pointer for record-merge
verification: named verifier kind, identity, and accepted/rejected status for verifier results
amendment: approved structured decision and gate replacement for amend
merge_assertion: token returned by assert-merge for record-merge
occurred_at: explicit ISO-8601 event timestamp
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
`assert-merge` also returns `merge_assertion`; `record-merge` must present that token against the same revision.

## Deterministic invocation

Lifecycle events, not free-form model judgment, select transitions:

| Event source | Event | Engine action |
|---|---|---|
| Gate controller | approved pending gate begins | `activate` |
| Source-mutation guard | repository edit requested | read-only `source-mutation` guard, equivalent to `assert-active` |
| Verifier runner or explicit human acceptance | named verifier accepts or rejects | `pass` or `fail` |
| Workflow controller | blocker, resolution, retry, or parking | `block`, `resume`, `retry`, or `pause` |
| Session stop guard | main turn attempts to yield | compare the current repository fingerprint with `Current checkpoint` while work is nonterminal; accept a structurally valid complete PRD |
| Merge controller | merge begins or completes | `assert-merge` or `record-merge` |

OMP exposes these events through `ctx_prd_lifecycle`. Reading `ctx-prd` arms the source-mutation guard; every bash call and repository-write tool remains blocked until `gate.activate` or `gate.assert-active` returns an attestation. A stale repository fingerprint blocks nonterminal session settlement until a write transition refreshes the canonical checkpoint. A complete PRD has no writable active gate, so validated terminal yield and completion do not compare the obsolete active-work fingerprint.


The revision format remains local to the PRD. The adapter advances it consistently with the existing note and returns the exact new value. Assertions do not advance the revision.

## Transition contract

| Transition | Required current truth | Result |
|---|---|---|
| `assert-active` | named gate is active at `expected_revision` | read-only attestation |
| `activate` | named gate is pending, every predecessor passed, and its deterministic linked plan resolves, links back, and validates | gate active; checkpoint updated |
| `amend` | named gate is pending while approved, or is the current active/blocked/failed gate while paused; explicit approval covers the contract change | affected decision and gate replaced; one amendment appended; gate does not activate |
| `update` | named gate is active or blocked | current verified truth replaces stale checkpoint truth |
| `block` | named gate is active | gate blocked with reason and one next action |
| `resume` | named gate is blocked or lifecycle is paused | gate active with blocker resolution evidence |
| `pass` | named gate is active and its named verifier has accepted the required evidence | gate passed; no later gate activates implicitly |
| `fail` | named gate is active | gate failed with evidence and one next action |
| `pause` | named gate is active or blocked | lifecycle paused; gate identity preserved |
| `retry` | named gate failed and lifecycle is blocked | failed gate active again with remediation evidence |
| `assert-merge` | named gate is passed and repository evidence matches | read-only merge attestation |
| `record-merge` | `assert-merge` succeeded for the same revision | PR and merge commit recorded; lifecycle remains truthful |

A transition outside this table fails closed. A human-verifier gate cannot `pass` from automated evidence alone.

## Checkpoint transaction

For every call:

1. Read the exact canonical PRD and resolve its revision, lifecycle status, current gate, named verifier, gate status, and linked plan.
2. Structurally validate the PRD section order, gate field order, Feature lists, plan paths/backlinks, plan section order, and parallel ownership contract.
3. Compare `expected_revision` before any write. On mismatch, return the current revision and make no change.
4. Validate authorization, transition, verifier evidence, blockers, gate order, and repository claims.
5. Construct the complete updated note in memory, touching only frontmatter lifecycle fields, the owning gate's status/evidence, the seven state-machine-owned `Current checkpoint` fields, and one approved amendment. Preserve additional accepted checkpoint context.
6. Advance the revision exactly once for a write transition.
7. Atomically replace the note while holding its checkpoint lock.
8. Re-read and structurally validate the PRD, linked plans, returned fields, and content hash. A partial or unverifiable write fails closed.

No source mutation, gate advancement, merge, completion claim, or nonterminal yield may cross this seam while its required checkpoint is missing or stale. A terminal yield still requires a structurally valid complete PRD with every gate passed.

## Current checkpoint

During execution the PRD contains one compact section:

```markdown
## Current checkpoint
- Gate: G2
- Status: active
- Verified: <current observed truth or evidence links>
- Blockers: <open blockers or none>
- Decision: <current material decision or unchanged>
- Next: <one concrete action>
- Repository: <deterministic git/worktree fingerprint, PR, or merge pointer>
```

Replace stale values; do not append an implementation journal. Detailed scenarios, logs, and screenshots remain in linked evidence artifacts.

## Validation and migration

`--validate` accepts `{"path":"<vault-relative PRD>"}` and performs the complete structural check without mutation.

`--migrate` accepts `path`, `expected_revision`, and `occurred_at`. It preserves lifecycle state, decisions, multiline gate evidence, global evidence, and amendments; reorders legacy sections and fields; adds missing `Blockers: none` and `Decision: none` sentinels; derives missing plan paths; retains unknown sections as noncanonical history; and advances the revision once. It refuses rather than inventing a missing Feature list, observed checkpoint truth, or plan. A missing plan error names the deterministic path that must be created.
