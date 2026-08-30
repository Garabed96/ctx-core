# OMP Runtime Adapter

Implement the core capability names with OMP's specialized tools. Read a mounted tool's `xd://` documentation before its first use. Prefer the specialized tool over shell equivalents.

## `AskOne`

Use `ask` with one question, 2–5 concise options, and `recommended` set. Put tradeoffs in option descriptions. Do not call it for repository or artifact facts available through tools.

## `ObsidianArtifactStore`

Use the `obsidian-war-room` MCP tools through their `xd://mcp__obsidian_war_room_*` routes. Use vault search/get operations for discovery, create/patch/property operations for content, rename operations for adaptive folder promotion, Canvas operations for visual review, and binary-file operations for attachments. Activate a known inactive Obsidian tool through the catalog when needed.

Resolve the vault and PRD root from explicit user/project context or an existing related PRD. Never scan unrelated personal notes. PRD creates its canonical artifact; Lean patches only an existing encompassing PRD. If the connector cannot reach the intended vault, report the missing capability and stop any operation whose durable PRD write is required; never create a filesystem fallback.

## `PrdCheckpoint`

Read `references/prd-checkpoint.md`. Resolve the exact canonical note through `ObsidianArtifactStore`, then perform one compare-and-patch operation whose precondition includes `expected_revision`. Prefer a connector operation that updates the full checkpoint transaction atomically. Otherwise use the live Obsidian CLI's in-process `app.vault.process` primitive; independent best-effort patches do not satisfy this capability.

Apply only the validated lifecycle transition, advance the note's existing revision convention, then re-read the frontmatter, owning gate, and `Current checkpoint` through the connector. Return those observed fields as the attestation. Zero matches, revision drift, partial writes, unavailable atomic mutation, or failed re-read stop the caller before source mutation, merge, advancement, or yield.

## `InspectSurface`

Use `xd://browser` for web behavior: open once, observe structure first, interact, and use screenshots only for appearance or durable evidence. Use the applicable simulator/device skill and tool for native surfaces. Use `hub` for long-running services. Exercise terminal and backend surfaces through their actual runtime rather than inferring behavior from source.

## `CreateWorktree`

Require explicit human authorization first. Use `ctx_workflow` with `create_worktree`; run `post_setup_worktree` only when project setup is required, then `open_worktree` only when the user wants a separate session. Return the exact branch and path. Do not create park files or inject delayed commands.

## `TeardownWorktree`

On an explicit cleanup request, use `ctx_workflow` with `kill_worktree`. Preserve its refusal for the primary worktree, dirty or unmerged state, and ambiguous targets unless the user deliberately authorizes the exact override supported by the runtime. Use `hub` to stop only a verified managed process.
