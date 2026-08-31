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

Every initiative uses one deterministic hierarchy:

```text
<initiative>/
  PRD/
    <ticket-or-slug>.md
  Planning/
    <ticket-or-slug>-g1-<gate-slug>.md
    <ticket-or-slug>-g2-<gate-slug>.md
```

The PRD always uses Outcome, Boundaries, Decisions, Current checkpoint, Gates, Approval, Evidence, and Amendments in that order. Every gate contains a concise Feature list and exactly one linked ctx-lean plan. Plans link back and own implementation detail, reuse decisions, lane ownership, and verification.

The PRD owns product decisions, gates, status, verifiers, and evidence links. Detailed implementation belongs to linked plans; test results remain in descriptively named QA campaign notes. Canvas is presentation-only.

A gate is not complete until the canonical PRD records its result and evidence. It cannot activate until its plan resolves, links back, follows the plan contract, and every predecessor passes.

Gate lifecycle changes cross one executable, revision-checked `PrdCheckpoint` state machine. It structurally validates the PRD and plans, legal transitions, verifier identity, gate order, repository fingerprints, and merge assertions; writes atomically; and returns a reread content-hash attestation. The same command provides read-only validation and deterministic migration from older PRDs.

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
- PRD lifecycle writes run through the packaged state machine and are structurally validated, revision-checked, atomically replaced, and re-read before execution, advancement, merge, yield, or completion claims.

OMP exposes the state machine as the essential `ctx_prd_lifecycle` tool. Its extension arms a source-mutation guard when `skill://ctx-prd` is read and blocks session settlement while the repository fingerprint differs from `Current checkpoint`. Set `CTX_OBSIDIAN_VAULT` to the canonical local vault root, or pass `vaultRoot` to the tool. Claude Code and Codex distributions include the same `scripts/prd_checkpoint.py` command and package `PreToolUse`/`Stop` hooks that arm the same guards deterministically once a gate has been attested in the repository.

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

Open `/hooks`, review the CTX hooks, and trust them; Codex does not auto-trust plugin hooks.

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

**v0.3.1 — Alpha**

### v0.3.1

- Canonicalized deterministic `<initiative>/PRD/` and `<initiative>/Planning/` paths.
- Added exact PRD and gate structure validation plus linked-plan backlink, ordering, and ownership checks.
- Made parallel lanes model-agnostic while requiring `impeccable` for applicable UI work.
- Added checkpoint blockers without discarding accepted contextual bullets.
- Added revision-safe v0.3.0 migration that preserves decisions, evidence, amendments, and unknown history while refusing fabricated plans or product content.

## License

Personal use. No license granted.
