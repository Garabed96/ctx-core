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

describe("OMP explicit PRD checkpoints", () => {
  test("registers the lifecycle tool without tool or session hooks", () => {
    const { handlers, tool } = loadExtension();
    expect(tool.parameters.kind).toBe("object");
    expect(handlers.size).toBe(0);
  });

  test("independent PRDs can recover in one repository while revision and merge checks remain enforced", async () => {
    const vault = await mkdtemp(path.join(tmpdir(), "ctx-core-vault-"));
    const repository = await mkdtemp(path.join(tmpdir(), "ctx-core-repository-"));
    temporaryPaths.push(vault, repository);
    for (const args of [
      ["init", "-q"],
      ["-c", "user.name=Test", "-c", "user.email=test@localhost", "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-qm", "Fixture"],
    ]) {
      expect(Bun.spawnSync(["git", "-C", repository, ...args]).exitCode).toBe(0);
    }
    for (const initiative of ["Example Initiative", "Other Initiative"]) {
      await Bun.write(path.join(vault, initiative, "PRD/example.md"), PRD.replaceAll("Example Initiative", initiative));
      await Bun.write(
        path.join(vault, initiative, "Planning/example-g1-first-vertical-slice.md"),
        PLAN.replaceAll("Example Initiative", initiative),
      );
    }
    const { handlers, tool } = loadExtension();
    // No session/model identity is needed: each call names its PRD and revision.
    const ctx = { cwd: repository };
    const request = {
      schemaVersion: 1,
      vaultRoot: vault,
      path: "Example Initiative/PRD/example.md",
      gate: "G1",
      verified: "Fixture evidence.",
      blockers: "none",
      decision: "unchanged",
      nextAction: "Continue the fixture.",
      occurredAt: "2026-09-05T00:00:00Z",
    };
    const call = async (event: string, expectedRevision: string, fields = {}) =>
      (await tool.execute("call", { ...request, event, expectedRevision, ...fields }, undefined, undefined, ctx)).details;
    const other = { path: "Other Initiative/PRD/example.md" };

    expect((await call("gate.activate", "r1")).revision).toBe("r2");
    expect((await call("gate.activate", "r1", other)).revision).toBe("r2");
    expect((await call("gate.block", "r2", { blockers: "Waiting on evidence." })).revision).toBe("r3");
    expect((await call("gate.assert-active", "r2", other)).ok).toBe(true);
    expect((await call("gate.assert-active", "r3")).ok).toBe(false);
    expect(Bun.spawnSync(["git", "-C", repository, "status", "--short"]).exitCode).toBe(0);
    expect((await call("gate.resume", "r3")).revision).toBe("r4");
    expect((await call("gate.update", "r2")).code).toBe("revision_conflict");
    expect((await call("verifier.accepted", "r4", {
      verification: { kind: "automated", identity: "focused contract command", status: "accepted" },
    })).lifecycle_status).toBe("complete");
    expect((await call("merge.assert", "r5")).ok).toBe(true);
    const note = Bun.file(path.join(vault, request.path));
    const before = await note.text();
    await Bun.write(path.join(repository, "another-agent.txt"), "Unrelated repository work.");
    expect((await call("merge.assert", "r5")).code).toBe("repository_mismatch");
    expect(await note.text()).toBe(before);
    expect(handlers.size).toBe(0);
  });

  test("rejects missing transition fields before checkpoint invocation", async () => {
    const { tool } = loadExtension();
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
      { cwd: "/does/not/exist" },
    );
    expect(result.details).toEqual({
      ok: false,
      code: "invalid_request",
      message: "Lifecycle transitions require verified, decision, nextAction, occurredAt.",
    });
  });
});
