# Runtime Interface

The core names capabilities; the installed runtime adapter supplies their implementation. Read `references/runtime.md` before crossing one of these seams.

| Capability | Contract |
|---|---|
| `AskOne` | Present one consequential decision with 2–5 distinct options and one recommendation. Do not ask for facts available from tools or existing artifacts. |
| `ObsidianArtifactStore` | Find, read, create, rename, and patch canonical Obsidian Markdown, Canvas, and attachment artifacts while preserving links. If unavailable, `ctx-prd` stops; no filesystem fallback becomes canonical. |
| `InspectSurface` | Exercise the actual changed surface and capture behaviorally relevant evidence. Browser, simulator, device, CLI, and service implementations may differ. |
| `CreateWorktree` | Create and open an isolated branch/worktree only after explicit human authorization. Return branch and worktree path. |
| `TeardownWorktree` | Remove only an explicitly named managed worktree after safety checks. Refuse the main worktree, ambiguity, dirty state, or unmerged work unless the human deliberately overrides the specific condition. |
| `ReadGitHandoff` | Resolve the current Git metadata path, read a handoff if present, and accept it only when its Branch field matches the current branch. |
| `WriteGitHandoff` | Resolve `git rev-parse --git-path ctx-core/handoff.md`, create its parent, and write exactly Goal, Verified, Blocked, Next, and Branch. |

Adapters must preserve these contracts. They may not weaken authorization, artifact authority, or destructive-operation guards to match a convenient tool.