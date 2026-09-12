---
name: ctx-frontend
description: Review or change frontend data flow, query caching, API integration, or mutation state. Not for visual styling or layout-only work.
---

# CTX Frontend

Use the project's existing data architecture. Before changing a data path, trace its consumer, query or hook, client, endpoint, validation, response and error shapes, and relevant tests. Inspect persistence and authorization when the change reaches those boundaries.

- Reuse query-key factories, API clients, hooks, schemas, and shared domain logic. Avoid parallel fetch paths or duplicated server state.
- Preserve loading, empty, error, retry, and mutation states. Check cache invalidation and any optimistic update or rollback against the affected consumers.
- Keep calculations and cross-surface behavior in the existing shared package when applicable; preserve authentication, authorization, and validation at trust boundaries.
- Consult official documentation for the installed library version when behavior is uncertain. Do not introduce TanStack Query or another dependency merely because this skill is loaded.
- Verify the changed observable contract with focused checks. Run broader checks only when affected boundaries or failures justify them.

This skill does not start a design, PRD, or delegation workflow. For visual work, use the existing product/design context and relevant Impeccable guidance independently. Do not load design guidance for data-only changes.
