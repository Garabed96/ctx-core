# Runtime Interface

The core names capabilities; the installed runtime adapter supplies their implementation. Read `references/runtime.md` before crossing one of these seams.

| Capability | Contract |
|---|---|
| `AskOne` | Present one consequential decision with 2–5 distinct options and one recommendation. Do not ask for facts available from tools or existing artifacts. |
| `ObsidianArtifactStore` | Find, read, create, rename, and patch canonical Obsidian Markdown, Canvas, and attachment artifacts while preserving links. PRD work creates and owns its canonical artifact; Lean may patch only an existing encompassing PRD. If unavailable, stop any operation whose durable PRD write is required; no filesystem fallback becomes canonical. |
| `PrdCheckpoint` | Validate the canonical PRD hierarchy and every linked plan, then invoke the packaged compare-and-swap state machine for one legal lifecycle event, atomically replace lifecycle truth, and re-read a content-hash attestation. Missing-plan, source-mutation, repository-fingerprint, gate-order, verifier, yield, completion, and merge guards fail closed. The packaged command also provides deterministic read-only validation and revision-safe migration. Callers never patch PRD lifecycle state directly. |
| `InspectSurface` | Exercise the actual changed surface and capture behaviorally relevant evidence. Browser, simulator, device, CLI, and service implementations may differ. |
| `CreateWorktree` | Create and open an isolated branch/worktree only after explicit human authorization. Return branch and worktree path. |
| `TeardownWorktree` | Remove only an explicitly named managed worktree after safety checks. Refuse the main worktree, ambiguity, dirty state, or unmerged work unless the human deliberately overrides the specific condition. |

Adapters must preserve these contracts. They may not weaken authorization, artifact authority, or destructive-operation guards to match a convenient tool.