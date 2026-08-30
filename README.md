# ctx-core

> **Alpha** — Built for active dogfooding. The interface is intentionally small.

A continuity-first Agent Skills plugin for Claude Code, Codex, and OMP.

## Two workflows

| Workflow | Use it when | State |
|---|---|---|
| **`ctx-prd`** | Product behavior, scope, visual direction, safety, or acceptance is unresolved | Canonical Obsidian PRD |
| **`ctx-lean`** | The desired outcome is settled and needs analysis, implementation, debugging, QA, or verification | Ephemeral session state |

> **Unsettled product decision → PRD. Settled outcome → Lean.**

Technical complexity and code size do not decide the workflow.

## `ctx-prd`

`ctx-prd` turns consequential product ambiguity into a durable decision contract, then executes it gate by gate.

It:

1. Inspects existing evidence.
2. Asks one consequential question at a time.
3. Creates a concise canonical PRD in Obsidian.
4. Defines 1–5 observable vertical gates.
5. Names an automated or human verifier for each gate.
6. Waits for explicit approval.
7. Executes and updates one gate at a time.

Obsidian is required for PRD work. There is no repository Markdown fallback.

A small effort may remain one note:

```text
CTX PRDs/
  Action-First Copilot — PRD.md
```

When the effort gains QA, visual review, or attachments, it becomes a folder:

```text
CTX PRDs/
  Action-First Copilot/
    Action-First Copilot — PRD.md
    Action-First Copilot — Mobile QA.md
    Action-First Copilot — Card Review.canvas
    Attachments/
```

The PRD owns decisions, gates, status, verifiers, and evidence links. Detailed test results remain in separate, descriptively named QA campaign notes. Canvas is presentation-only.

A gate is not complete until the canonical PRD records its result and evidence.

Gate lifecycle changes cross one revision-checked `PrdCheckpoint` seam. Source mutation requires an attested active gate; blockers and verifier results replace the current checkpoint immediately; PRD-owned merges require a passed gate at the expected revision and record the resulting PR/commit before closure.

## `ctx-lean`

`ctx-lean` completes settled technical work through the smallest complete vertical slice.

Use it for:

- approved features;
- bugs and unexpected behavior;
- refactors;
- review feedback;
- focused QA;
- TDD requests;
- verification and analysis.

Lean holds Goal, Boundaries, Acceptance, and Current slice ephemerally. It creates no separate plan, checkpoint, QA sheet, or handoff.

When an existing canonical PRD encompasses the work, Lean reads its revision and active gate before mutation, then uses `PrdCheckpoint` after material changes in execution truth. Parking, resume, and merge share the same fail-closed lifecycle seam; standalone Lean work remains ephemeral.

Its proportional references cover:

- **Debugging** — reproduce, trace, test one hypothesis, fix the source, confirm.
- **Testing** — defend observable contracts; use red–green–refactor when valuable.
- **Review feedback** — verify each suggestion before accepting or rejecting it.

The canonical Obsidian PRD is the only durable continuity artifact. Lean never creates a mini-PRD or Git-local handoff.

## Execution principles

Both workflows share the same contract:

- Main owns intent, architecture, integration, canonical state, and final proof.
- At most two bounded workers may participate in an ordinary run.
- Completion claims require fresh, claim-specific evidence.
- UI behavior is verified through the actual surface.
- Bugs are verified through the original reproduction.
- Worktrees are never created automatically.
- The user’s original verb determines whether implementation is authorized.
- PRD lifecycle writes are revision-checked and re-read before execution, advancement, merge, or completion claims.

## Install

Restart the runtime after installation so it reloads its skills.

### Claude Code

```sh
claude plugin marketplace add Garabed96/ctx-core
claude plugin install ctx@ctx-core --scope user
```

### Codex

```sh
codex plugin marketplace add Garabed96/ctx-core --ref main
codex plugin add ctx@ctx-core
```

### OMP

```sh
omp plugin marketplace add Garabed96/ctx-core
omp plugin install ctx@ctx-core --scope user
```

Both skills are model-invoked. Describe the work normally or request one explicitly:

```text
Use ctx-prd to resolve this product decision.
Use ctx-lean to implement this settled behavior.
```

## Architecture

```text
ctx-core/
  core/          # canonical skills and shared contracts
  adapters/      # Claude Code, Codex, and OMP tool mappings
  installer/     # deterministic composition
  contract-tests/
  dist/          # generated installable plugins
```

`core/` is the source of truth. Generated distributions are never edited manually.

Validate all three runtime packages and routing contracts:

```sh
python3 contract-tests/check.py
```

## Lineage

[`ctx-plugin`](https://github.com/Garabed96/ctx-plugin) is the frozen first generation.

It explored broad development orchestration. `ctx-core` keeps the useful continuity discipline behind two smaller interfaces: durable PRD state for product work and bounded Lean state for technical execution.

## Status

**v0.2.1 — Alpha**

## License

Personal use. No license granted.
