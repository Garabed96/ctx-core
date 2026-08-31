import { afterEach, describe, expect, test } from "bun:test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import prdLifecycle from "../adapters/omp/extensions/prd-lifecycle.ts";

const PRD = `---
title: Example — PRD
type: ctx-prd
status: approved
revision: r1
current_gate: null
branch: feat/example
worktree: /tmp/example
approved_by: Garo
approved_at: 2026-08-31T09:00:00Z
created: 2026-08-31
updated: 2026-08-31
---

# Example — PRD

## Outcome
An observable result.

## Boundaries
- **In:** First behavior.
- **Out:** Unrelated behavior.
- **Preserve:** Existing contracts.

## Decisions
| Decision | Rationale |
|---|---|
| Reuse the existing seam. | Avoid duplication. |

## Current checkpoint
- Gate: null
- Status: pending
- Verified: none
- Blockers: none
- Decision: none
- Next: Activate G1
- Repository: none

## Gates
### G1 — First vertical slice
- **Proves:** First behavior works.
- **Feature list:**
  - Complete the first user-visible behavior.
- **Implementation plan:** [[Example Initiative/Planning/example-g1-first-vertical-slice|G1 plan]]
- **Verifier:** automated — focused contract command
- **Status:** pending
- **Evidence:** none

## Approval
- [x] Approved for execution

## Evidence
- None.

## Amendments
- None.
`;

const PLAN = `---
title: Example G1 plan
type: implementation-plan
status: planned
gate: G1
prd: \"[[Example Initiative/PRD/example.md|Example PRD]]\"
---

# Example G1 plan

## Outcome
The gate behavior works.

## Reuse decisions
- Reuse the existing seam.

## Implementation slice
1. Implement the gate behavior.

## Parallel execution contract
- **Backend/contracts/architecture owner:** Main owns contracts and architecture.
- **Independent UI or specialist lane:** Not applicable
- **Shared integration owner:** Main integrates the gate.
- **File ownership and no-overlap constraints:** One owner changes each file.
- **Final integration and verification pass:** Main runs the focused contract.

## Verification
- Run the focused contract.

## Non-goals
- Unrelated behavior.
`;

const temporaryPaths: string[] = [];
afterEach(async () => {
  await Promise.all(temporaryPaths.splice(0).map((item) => rm(item, { recursive: true, force: true })));
});

function fakeSchema(kind = "scalar"): any {
  const schema: any = {
    kind,
    min: () => schema,
    optional: () => schema,
    regex: () => schema,
    strict: () => schema,
  };
  return schema;
}

function loadExtension() {
  const handlers = new Map<string, Function>();
  let tool: any;
  prdLifecycle({
    zod: {
      enum: () => fakeSchema(),
      literal: () => fakeSchema(),
      object: () => fakeSchema("object"),
      string: () => fakeSchema(),
      union: () => fakeSchema("union"),
    },
    on(event: string, handler: Function) {
      handlers.set(event, handler);
    },
    registerTool(value: any) {
      tool = value;
    },
  } as any);
  return { handlers, tool };
}

function context(sessionId: string) {
  return {
    cwd: path.resolve(import.meta.dir, ".."),
    sessionManager: { getSessionId: () => sessionId },
  };
}

describe("OMP PRD lifecycle controller", () => {
  test("registers an object-rooted tool schema", () => {
    const { tool } = loadExtension();
    expect(tool.parameters.kind).toBe("object");
  });

  test("activates through the checkpoint command and guards source mutation", async () => {
    const vault = await mkdtemp(path.join(tmpdir(), "ctx-core-omp-lifecycle-"));
    temporaryPaths.push(vault);
    const relative = "Example Initiative/PRD/example.md";
    await Bun.write(path.join(vault, relative), PRD);
    await Bun.write(
      path.join(vault, "Example Initiative/Planning/example-g1-first-vertical-slice.md"),
      PLAN,
    );
    const { handlers, tool } = loadExtension();
    const ctx = context("active-session");

    const activated = await tool.execute(
      "call-1",
      {
        schemaVersion: 1,
        event: "gate.activate",
        vaultRoot: vault,
        path: relative,
        expectedRevision: "r1",
        gate: "G1",
        verified: "Approval recorded.",
        blockers: "none",
        decision: "unchanged",
        nextAction: "Implement G1.",
        occurredAt: "2026-08-31T12:00:00Z",
      },
      undefined,
      undefined,
      ctx,
    );

    expect(activated.details.ok, JSON.stringify(activated.details)).toBe(true);
    expect(activated.details.revision).toBe("r2");
    const mutationGuard = await handlers.get("tool_call")?.(
      { toolName: "edit", input: {}, toolCallId: "edit-1" },
      ctx,
    );
    expect(mutationGuard).toBeUndefined();
    const stopGuard = await handlers.get("session_stop")?.({}, ctx);
    expect(stopGuard).toBeUndefined();
  });

  test("blocks PRD-owned source mutation before gate attestation", async () => {
    const { handlers } = loadExtension();
    const ctx = context("unattested-session");
    handlers.get("tool_result")?.(
      {
        toolName: "read",
        input: { path: "skill://ctx-prd" },
        isError: false,
      },
      ctx,
    );

    const guard = await handlers.get("tool_call")?.(
      { toolName: "edit", input: {}, toolCallId: "edit-2" },
      ctx,
    );
    expect(guard).toEqual({
      block: true,
      reason: "PRD-owned source mutation requires ctx_prd_lifecycle gate.activate or gate.assert-active first.",
    });
  });
  test("fails closed on every bash call before gate attestation", async () => {
    const { handlers } = loadExtension();
    const ctx = context("unattested-bash-session");
    handlers.get("tool_result")?.(
      {
        toolName: "read",
        input: { path: "skill://ctx-prd" },
        isError: false,
      },
      ctx,
    );

    for (const command of [
      "git status --short",
      "echo x > src/app.ts",
      "cat > src/app.ts",
      "printf x >> src/app.ts",
      "tee src/app.ts",
      "python3 -c \"open('src/app.ts', 'w').write('x')\"",
    ]) {
      const guard = await handlers.get("tool_call")?.(
        { toolName: "bash", input: { command }, toolCallId: command },
        ctx,
      );
      expect(guard?.block).toBe(true);
    }
  });

  test("rejects every missing transition field before checkpoint invocation", async () => {
    const { tool } = loadExtension();
    const ctx = context("invalid-transition-session");
    const result = await tool.execute(
      "call-invalid",
      {
        schemaVersion: 1,
        event: "gate.activate",
        vaultRoot: "/does/not/exist",
        path: "Example Initiative/PRD/example.md",
        expectedRevision: "r1",
        gate: "G1",
        blockers: "none",
      },
      undefined,
      undefined,
      ctx,
    );

    expect(result.details).toEqual({
      ok: false,
      code: "invalid_request",
      message: "Lifecycle transitions require verified, decision, nextAction, occurredAt.",
    });
  });
});
