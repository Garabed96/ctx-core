# Claude Code Runtime Adapter

Implement the core capability names with Claude Code's current tools. Tool availability is runtime evidence; do not invent a connector or silently substitute a filesystem copy.

## `AskOne`

Use `AskUserQuestion` with one question, 2–5 concise options, and the recommended option marked. Put tradeoffs in option descriptions. If the tool is unavailable, ask one plain-text question and wait.

## `ObsidianArtifactStore`

Use the configured Obsidian MCP connector when available. Prefer its native search, get, create, patch, rename, Canvas, and attachment operations so Obsidian preserves links and metadata. The `obsidian` CLI is an acceptable adapter when it targets the intended live vault.

Resolve the vault and PRD root from explicit user/project context or an existing related PRD. Never scan unrelated personal notes. PRD creates its canonical artifact; Lean patches only an existing encompassing PRD. If neither an Obsidian connector nor a working CLI can reach the intended vault, report the missing capability and stop any operation whose durable PRD write is required.

## `PrdCheckpoint`

Read `references/prd-checkpoint.md`. Resolve the canonical local vault root and the absolute installed plugin root, then invoke Python with `<plugin-root>/scripts/prd_checkpoint.py --vault-root <root>` and one JSON transition request on stdin. Name the exact PRD `path`, `gate`, `expected_revision`, observed evidence, blockers, decision, next action, and timestamp. Fill `repository` with the output of `<plugin-root>/scripts/repo_fingerprint.py <repository-root>`; `record-merge` records the PR and merge commit pointer instead.

Use `activate` or `assert-active` before a PRD-owned implementation slice. Write material progress before unrelated work or handoff; use `assert-merge` and `record-merge` around a merge. Use `--validate` for read-only structure checks and `--migrate` for revision-safe legacy migration. Never patch lifecycle fields through the Obsidian connector.

The command validates the PRD and linked plans, locks the note, checks its expected revision and legal transition, atomically replaces it, then re-reads a content-hash attestation. Reconcile a refused checkpoint before advancing or claiming success. There are no tool or stop hooks: reads, unrelated sessions, and recovery remain available. The agent must invoke checkpoints; a repository fingerprint cannot judge product relevance or verify evidence.

## `InspectSurface`

Use the strongest runtime-native surface available: browser automation for web UI, simulator/device tooling for native UI, direct CLI interaction for terminal products, and focused service calls for backend behavior. Reuse an authenticated user browser only when the task requires that session. Capture screenshots only for visual claims or durable QA evidence.

## `CreateWorktree`

First establish explicit human authorization. Then inspect the repository root, current branch, configured base branch, and existing worktrees with Git. Choose a non-conflicting branch/path, run `git worktree add`, perform only project-required setup, and return the exact branch and path. Do not park conversation context or inject delayed terminal input.

## `TeardownWorktree`

Resolve the named target from outside that worktree when possible. Refuse the primary worktree, dirty state, unmerged branch, or ambiguous target unless the user explicitly overrides that exact guard. Stop target services only when their identity is verified. Remove the worktree, then delete its branch only when merged or explicitly authorized.
