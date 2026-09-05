# OMP Runtime Adapter

Implement the core capability names with OMP's specialized tools. Read a mounted tool's `xd://` documentation before its first use. Prefer the specialized tool over shell equivalents.

## `AskOne`

Use `ask` with one question, 2–5 concise options, and `recommended` set. Put tradeoffs in option descriptions. Do not call it for repository or artifact facts available through tools.

## `ObsidianArtifactStore`

Use the mounted Obsidian MCP tools through their `xd://mcp__obsidian_*` routes. Use `vault_get_document_map` before targeted reads or patches, vault read/write operations for artifacts, rename operations for adaptive folder promotion, and Canvas or attachment operations when available. The connector may be backed by Obsidian Local REST API; lifecycle fields still cross `PrdCheckpoint`, never independent MCP patches.

Resolve the vault and PRD root from explicit user/project context or an existing related PRD. Never scan unrelated personal notes. PRD creates its canonical artifact; Lean patches only an existing encompassing PRD. If the connector cannot reach the intended vault, report the missing capability and stop any operation whose durable PRD write is required; never create a filesystem fallback.

## `PrdCheckpoint`

Read `references/prd-checkpoint.md`. Invoke the essential `ctx_prd_lifecycle` tool for every lifecycle event. Set `CTX_OBSIDIAN_VAULT` to the canonical local vault root or pass `vaultRoot`; every transition passes the vault-relative PRD path, exact `expectedRevision` (mapped to `expected_revision`), and non-empty `verified`, `blockers`, `decision`, `nextAction`, and `occurredAt` fields. The adapter obtains the repository fingerprint from the shared Python command, calls the packaged state machine, and returns the re-read content-hash attestation.

Use `gate.activate` or `gate.assert-active` before PRD-owned source mutation; `verifier.accepted` or `verifier.rejected` for named verifier results; `gate.block`, `gate.resume`, `gate.retry`, `gate.update`, or `workflow.pause` for execution truth; and `merge.assert` followed by `merge.record` for merge truth. Never patch PRD lifecycle fields through Obsidian MCP.

Resolve the absolute installed plugin root, then use `<plugin-root>/scripts/prd_checkpoint.py --validate` and `--migrate` for protocol maintenance. Validation is read-only; migration requires the exact revision and timestamp and performs one atomic PRD replacement.

The extension only registers the lifecycle tool. It does not intercept tools, block turns, or store session bindings. Every call explicitly identifies its PRD and revision. Reconcile a refused checkpoint before advancing or claiming success; reads and recovery remain available. The agent must checkpoint material progress before unrelated work or handoff and judge whether changed code invalidates the recorded evidence.

## `InspectSurface`

Use `xd://browser` for web behavior: open once, observe structure first, interact, and use screenshots only for appearance or durable evidence. Use the applicable simulator/device skill and tool for native surfaces. Use `hub` for long-running services. Exercise terminal and backend surfaces through their actual runtime rather than inferring behavior from source.

## `CreateWorktree`

Require explicit human authorization first. Use `ctx_workflow` with `create_worktree`; run `post_setup_worktree` only when project setup is required, then `open_worktree` only when the user wants a separate session. Return the exact branch and path. Do not create park files or inject delayed commands.

## `TeardownWorktree`

On an explicit cleanup request, use `ctx_workflow` with `kill_worktree`. Preserve its refusal for the primary worktree, dirty or unmerged state, and ambiguous targets unless the user deliberately authorizes the exact override supported by the runtime. Use `hub` to stop only a verified managed process.
