# Claude Code Runtime Adapter

Implement the core capability names with Claude Code's current tools. Tool availability is runtime evidence; do not invent a connector or silently substitute a filesystem copy.

## `AskOne`

Use `AskUserQuestion` with one question, 2–5 concise options, and the recommended option marked. Put tradeoffs in option descriptions. If the tool is unavailable, ask one plain-text question and wait.

## `ObsidianArtifactStore`

Use the configured Obsidian MCP connector when available. Prefer its native search, get, create, patch, rename, Canvas, and attachment operations so Obsidian preserves links and metadata. The `obsidian` CLI is an acceptable adapter when it targets the intended live vault.

Resolve the vault and PRD root from explicit user/project context or an existing related PRD. Never scan unrelated personal notes. PRD creates its canonical artifact; Lean patches only an existing encompassing PRD. If neither an Obsidian connector nor a working CLI can reach the intended vault, report the missing capability and stop any operation whose durable PRD write is required.

## `PrdCheckpoint`

Read `references/prd-checkpoint.md`. Resolve the canonical local vault root, then invoke the packaged absolute command `"${CLAUDE_PLUGIN_ROOT}/scripts/prd_checkpoint.py" --vault-root <root>` through Python with one JSON transition request—including current `blockers` or `none`—on stdin. Use its `--guard source-mutation` before PRD-owned repository edits and `--guard yield` before settlement. Use `--validate` for read-only structural validation and `--migrate` for revision-safe v0.3.1 migration. Never patch PRD lifecycle fields through the Obsidian connector.

The command validates the exact PRD hierarchy and all linked plans, holds a per-note lock, checks `expected_revision` and the legal transition, atomically replaces the complete PRD, then re-reads and returns a content-hash attestation. Invalid structure, missing plans, revision drift, illegal transitions, stale repository state, partial writes, or failed re-reads stop source mutation, merge, advancement, or yield.

## `InspectSurface`

Use the strongest runtime-native surface available: browser automation for web UI, simulator/device tooling for native UI, direct CLI interaction for terminal products, and focused service calls for backend behavior. Reuse an authenticated user browser only when the task requires that session. Capture screenshots only for visual claims or durable QA evidence.

## `CreateWorktree`

First establish explicit human authorization. Then inspect the repository root, current branch, configured base branch, and existing worktrees with Git. Choose a non-conflicting branch/path, run `git worktree add`, perform only project-required setup, and return the exact branch and path. Do not park conversation context or inject delayed terminal input.

## `TeardownWorktree`

Resolve the named target from outside that worktree when possible. Refuse the primary worktree, dirty state, unmerged branch, or ambiguous target unless the user explicitly overrides that exact guard. Stop target services only when their identity is verified. Remove the worktree, then delete its branch only when merged or explicitly authorized.
