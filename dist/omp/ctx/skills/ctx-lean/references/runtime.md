# OMP Runtime Adapter

Implement the core capability names with OMP's specialized tools. Read a mounted tool's `xd://` documentation before its first use. Prefer the specialized tool over shell equivalents.

## `AskOne`

Use `ask` with one question, 2–5 concise options, and `recommended` set. Put tradeoffs in option descriptions. Do not call it for repository or artifact facts available through tools.

## `ObsidianArtifactStore`

Use the `obsidian-war-room` MCP tools through their `xd://mcp__obsidian_war_room_*` routes. Use vault search/get operations for discovery, create/patch/property operations for content, rename operations for adaptive folder promotion, Canvas operations for visual review, and binary-file operations for attachments. Activate a known inactive Obsidian tool through the catalog when needed.

Resolve the vault and PRD root from explicit user/project context or an existing related PRD. Never scan unrelated personal notes. If the connector cannot reach the intended vault, report the missing capability and stop PRD work; never create a local fallback PRD.

## `InspectSurface`

Use `xd://browser` for web behavior: open once, observe structure first, interact, and use screenshots only for appearance or durable evidence. Use the applicable simulator/device skill and tool for native surfaces. Use `hub` for long-running services. Exercise terminal and backend surfaces through their actual runtime rather than inferring behavior from source.

## `CreateWorktree`

Require explicit human authorization first. Use `ctx_workflow` with `create_worktree`; run `post_setup_worktree` only when project setup is required, then `open_worktree` only when the user wants a separate session. Return the exact branch and path. Do not create park files or inject delayed commands.

## `TeardownWorktree`

On an explicit cleanup request, use `ctx_workflow` with `kill_worktree`. Preserve its refusal for the primary worktree, dirty or unmerged state, and ambiguous targets unless the user deliberately authorizes the exact override supported by the runtime. Use `hub` to stop only a verified managed process.

## Git-local handoff

Use one Git command to resolve `git rev-parse --git-path ctx-core/handoff.md`, then `read` or `write` the resolved path. Create only its parent directory. Compare the embedded Branch with `git branch --show-current` before using it.