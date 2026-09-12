# ctx-core

> **Alpha** — Built for active dogfooding. The interface is intentionally small.

A continuity-first Agent Skills plugin for Claude Code, Codex, and OMP.

## Five focused skills

| Skill | Use it when | Invocation |
|---|---|---|
| **`ctx-prd`** | Requesting a PRD or continuing a named PRD gate | Explicit |
| **`ctx-lean`** | Requesting Lean execution or continuing a named PRD implementation plan | Explicit |
| **`ctx-discuss`** | Exploring options and tradeoffs before implementation | Discoverable |
| **`ctx-align`** | Requesting a prompt or skill review | Discoverable |
| **`ctx-frontend`** | Changing frontend data flow, caching, API integration, or mutation state | Discoverable |

Ordinary implementation and UI polish do not automatically enter Lean or PRD. An unresolved product decision can be discussed without creating a PRD. Explicit continuation of an existing PRD retains its checkpoint obligations.

Discuss, Align, and Frontend are self-contained. Frontend covers existing query keys, clients, hooks, validation, loading/error states, and mutations. Visual guidance remains in the independently installed Impeccable skill and the project's PRODUCT.md/DESIGN.md. No design skill is bundled or automatically loaded by CTX Frontend.

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

Invoke it explicitly for a settled outcome or a named PRD implementation plan. Technical complexity and file count alone do not activate it.

Lean holds Goal, Boundaries, Acceptance, and Current slice ephemerally. It creates no separate plan, checkpoint, QA sheet, or handoff.

When the user explicitly continues work owned by a named PRD, Lean reads its revision and active gate before mutation, then uses `PrdCheckpoint` after material changes in execution truth. Parking, resume, and merge use the same explicit lifecycle command; standalone Lean work remains ephemeral.

Its proportional references cover:

- **Debugging** — reproduce, trace, test one hypothesis, fix the source, confirm.
- **Testing** — defend observable contracts; use red–green–refactor when valuable.
- **Review feedback** — verify each suggestion before accepting or rejecting it.

The canonical Obsidian PRD is the only durable continuity artifact. Lean never creates a mini-PRD or Git-local handoff.

## Execution principles

Both workflows share the same contract:

- Main owns intent, architecture, integration, canonical state, and final proof.
- Target one implementer for a complete bounded change. Main handles review, verification, and small corrections; another worker needs substantial remaining work or a genuinely independent outcome.
- Completion claims require fresh, claim-specific evidence.
- UI behavior is verified through the actual surface.
- Bugs are verified through the original reproduction.
- Worktrees are never created automatically.
- The user’s original verb determines whether implementation is authorized.
- PRD lifecycle writes run through the packaged state machine and are structurally validated, revision-checked, atomically replaced, and re-read before execution, advancement, merge, yield, or completion claims.

OMP exposes the state machine as the essential `ctx_prd_lifecycle` tool. Claude Code and Codex include the same `scripts/prd_checkpoint.py` command. Set `CTX_OBSIDIAN_VAULT` or pass `vaultRoot` in OMP; pass `--vault-root` to Python.

Every call names its PRD, gate, and expected revision. There are no tool/stop hooks or session records. Revision checks protect concurrent updates to the same PRD; unrelated sessions cannot block each other. Agents explicitly save material progress and verify the returned attestation. Fingerprints identify the snapshot behind evidence; they cannot identify its author or prove that product scope and UI/UX goals match the code. That requires agent judgment, tests, and actual surface evidence.

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

Lean and PRD are explicit-only: Codex uses `allow_implicit_invocation: false`; Claude Code and OMP use `disable-model-invocation: true`. The remaining skills have narrow automatic discovery. Request workflows explicitly:

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

It explored broad development orchestration. `ctx-core` keeps the useful continuity discipline behind explicit PRD/Lean interfaces, with focused discussion, prompt review, and frontend data guidance.

## Status

**v0.4.1 — Alpha**

### v0.4.1

- Made Lean and PRD explicit-only using each runtime's native invocation policy; preserved the PRD state machine and existing document format.
- Absorbed Discuss, Align, and a narrow Frontend data-architecture skill. These load no lifecycle references or design workflow.
- Reduced standalone Lean guidance and removed automatic PRD discovery and escalation.
- Target one implementation worker per complete bounded change; the primary owns verification and small corrections.
- When migrating, remove or disable standalone Discuss, Align, and broad Frontend copies so their old triggers do not remain active. Keep Impeccable installed separately.


### v0.4.0

- Removed automatic tool/turn blocking, session arming, and the redundant `--guard` / `guard.*` API. Use `activate` / `assert-active`, material write checkpoints, and `assert-merge` / `record-merge` instead. PRD format and existing notes are unchanged.
- Shared one fingerprint implementation across runtimes. Composition checks ignore generated Python bytecode.
- Previously installed plugins keep their old hooks until the updated package is installed and the runtime restarted.

### v0.3.1

- Canonicalized deterministic `<initiative>/PRD/` and `<initiative>/Planning/` paths.
- Added exact PRD and gate structure validation plus linked-plan backlink, ordering, and ownership checks.
- Made parallel lanes model-agnostic while requiring `impeccable` for applicable UI work.
- Added checkpoint blockers without discarding accepted contextual bullets.
- Added revision-safe v0.3.0 migration that preserves decisions, evidence, amendments, and unknown history while refusing fabricated plans or product content.

## License

Personal use. No license granted.
