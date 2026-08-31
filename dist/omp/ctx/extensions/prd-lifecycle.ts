import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

const extensionDirectory = path.dirname(fileURLToPath(import.meta.url));
const composedCommand = path.resolve(extensionDirectory, "../scripts/prd_checkpoint.py");
const sourceCommand = path.resolve(extensionDirectory, "../../../core/scripts/prd_checkpoint.py");
const command = existsSync(composedCommand) ? composedCommand : sourceCommand;

const transitions = {
  "gate.activate": "activate",
  "gate.amend": "amend",
  "gate.assert-active": "assert-active",
  "gate.block": "block",
  "gate.resume": "resume",
  "gate.retry": "retry",
  "gate.update": "update",
  "merge.assert": "assert-merge",
  "merge.record": "record-merge",
  "verifier.accepted": "pass",
  "verifier.rejected": "fail",
  "workflow.pause": "pause",
} as const;

const guards = {
  "guard.completion": "completion",
  "guard.next-gate": "next-gate",
  "guard.source-mutation": "source-mutation",
  "guard.yield": "yield",
} as const;

type LifecycleEvent = keyof typeof transitions | keyof typeof guards;
type Binding = {
  gate: string;
  path: string;
  repositoryRoot: string;
  revision: string;
  vaultRoot: string;
};

type CommandResult = Record<string, unknown>;

function output(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value) }],
    details: value,
  };
}

function runProcess(
  application: string,
  args: string[],
  input?: string,
  signal?: AbortSignal,
): Promise<{ code: number; stderr: string; stdout: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(application, args, {
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
      signal,
      stdio: ["pipe", "pipe", "pipe"],
    });
    const stdout: Buffer[] = [];
    const stderr: Buffer[] = [];
    child.stdout.on("data", (chunk: Buffer) => stdout.push(chunk));
    child.stderr.on("data", (chunk: Buffer) => stderr.push(chunk));
    child.on("error", reject);
    child.on("close", (code) => {
      resolve({
        code: code ?? 1,
        stderr: Buffer.concat(stderr).toString("utf8"),
        stdout: Buffer.concat(stdout).toString("utf8"),
      });
    });
    child.stdin.end(input);
  });
}

async function git(repositoryRoot: string, args: string[], signal?: AbortSignal) {
  const result = await runProcess("git", ["-C", repositoryRoot, ...args], undefined, signal);
  if (result.code !== 0) throw new Error(result.stderr.trim() || `git ${args.join(" ")} failed`);
  return result.stdout;
}

async function repositoryFingerprint(repositoryRoot: string, signal?: AbortSignal) {
  const root = path.resolve(repositoryRoot);
  const head = (await git(root, ["rev-parse", "HEAD"], signal)).trim();
  const diff = await git(root, ["diff", "--binary", "HEAD", "--", "."], signal);
  const untracked = await git(root, ["ls-files", "--others", "--exclude-standard", "-z"], signal);
  const digest = createHash("sha256").update(diff);
  for (const relative of untracked.split("\0").filter(Boolean).sort()) {
    digest.update("\0").update(relative).update("\0");
    digest.update(await readFile(path.join(root, relative)));
  }
  return `git:${head}:worktree:${digest.digest("hex")}`;
}

async function invokeCheckpoint(
  vaultRoot: string,
  request: Record<string, unknown>,
  guard: string | undefined,
  signal?: AbortSignal,
): Promise<{ ok: true; result: CommandResult } | { ok: false; error: CommandResult }> {
  const args = [command, "--vault-root", vaultRoot];
  if (guard) args.push("--guard", guard);
  const completed = await runProcess(
    process.env.CTX_PYTHON ?? "python3",
    args,
    JSON.stringify(request),
    signal,
  );
  const raw = (completed.code === 0 ? completed.stdout : completed.stderr).trim();
  let parsed: CommandResult;
  try {
    parsed = JSON.parse(raw) as CommandResult;
  } catch {
    parsed = { code: "invalid_checkpoint_output", message: raw || "checkpoint command returned no JSON" };
  }
  return completed.code === 0 ? { ok: true, result: parsed } : { ok: false, error: parsed };
}

function isCtxPrdSkill(pathValue: unknown) {
  const value = String(pathValue ?? "");
  return value === "skill://ctx-prd" || value.startsWith("skill://ctx-prd/");
}

function isRepositoryMutation(event: any, cwd: string) {
  if (event.toolName === "edit") return true;
  if (event.toolName === "write") {
    const target = String(event.input?.path ?? "");
    if (target === "xd://resolve") return true;
    if (target.startsWith("xd://ast_edit")) return true;
    if (target.startsWith("xd://lsp")) {
      const content = String(event.input?.content ?? "");
      return /"action"\s*:\s*"(?:rename|rename_file|code_actions)"/.test(content)
        && !/"apply"\s*:\s*false/.test(content);
    }
    if (target.includes("://")) return false;
    const absolute = path.resolve(cwd, target);
    const root = path.resolve(cwd);
    return absolute === root || absolute.startsWith(`${root}${path.sep}`);
  }
  if (event.toolName === "bash") return true;
  return false;
}

export default function prdLifecycle(pi: ExtensionAPI) {
  const z = pi.zod;
  const bindings = new Map<string, Binding>();
  const prdRequired = new Set<string>();
  const runtime = pi as unknown as {
    on: Function;
    registerTool: Function;
  };

  const verification = z.object({
    kind: z.enum(["automated", "human"]),
    identity: z.string().min(1),
    status: z.enum(["accepted", "rejected"]),
  }).strict();
  const amendment = z.object({
    approved_by: z.string().min(1),
    decision_from: z.string().min(1),
    decision_to: z.string().min(1),
    decision_rationale: z.string().min(1),
    gate_proves: z.string().min(1),
    verifier_kind: z.enum(["automated", "human"]),
    verifier_identity: z.string().min(1),
    rationale: z.string().min(1),
  }).strict();
  const baseParameters = {
    schemaVersion: z.literal(1),
    vaultRoot: z.string().min(1).optional(),
    path: z.string().min(1),
    expectedRevision: z.string().regex(/^r[1-9]\d*$/),
    gate: z.string().regex(/^[A-Za-z][A-Za-z0-9_-]*$/),
  };
  const parameters = z.object({
    ...baseParameters,
    event: z.enum([
      ...Object.keys(transitions),
      ...Object.keys(guards),
    ] as [LifecycleEvent, ...LifecycleEvent[]]),
    verified: z.string().min(1).optional(),
    blockers: z.string().min(1).optional(),
    decision: z.string().min(1).optional(),
    nextAction: z.string().min(1).optional(),
    occurredAt: z.string().min(1).optional(),
    verification: verification.optional(),
    mergeAssertion: z.string().min(1).optional(),
    amendment: amendment.optional(),
  }).strict();

  runtime.registerTool({
    name: "ctx_prd_lifecycle",
    label: "CTX PRD Lifecycle",
    description: "Apply or attest one revision-safe canonical PRD lifecycle event.",
    parameters,
    strict: true,
    loadMode: "essential",
    async execute(
      _id: string,
      params: any,
      signal: AbortSignal | undefined,
      _update: unknown,
      ctx: any,
    ) {
      const vaultRoot = params.vaultRoot ?? process.env.CTX_OBSIDIAN_VAULT;
      if (!vaultRoot) {
        return output({ ok: false, code: "vault_root_required", message: "Set CTX_OBSIDIAN_VAULT or pass vaultRoot." });
      }
      const guard = guards[params.event as keyof typeof guards];
      const transition = transitions[params.event as keyof typeof transitions];
      if (!guard) {
        const required = ["verified", "blockers", "decision", "nextAction", "occurredAt"];
        const missing = required.filter((field) => typeof params[field] !== "string" || !params[field].trim());
        if (missing.length) {
          return output({
            ok: false,
            code: "invalid_request",
            message: `Lifecycle transitions require ${missing.join(", ")}.`,
          });
        }
      }
      const repositoryRoot = path.resolve(ctx.cwd);
      let repository: string;
      try {
        repository = await repositoryFingerprint(repositoryRoot, signal);
      } catch (error) {
        return output({ ok: false, code: "repository_fingerprint_failed", message: String(error) });
      }

      const common = {
        path: params.path,
        expected_revision: params.expectedRevision,
        gate: params.gate,
        repository,
      };
      const request = guard
        ? common
        : {
            ...common,
            transition,
            verified: params.verified,
            blockers: params.blockers,
            decision: params.decision,
            next_action: params.nextAction,
            occurred_at: params.occurredAt,
            verification: params.verification,
            merge_assertion: params.mergeAssertion,
            amendment: params.amendment,
          };
      const invoked = await invokeCheckpoint(vaultRoot, request, guard, signal);
      if (!invoked.ok) return output({ ok: false, ...invoked.error });

      const result = invoked.result;
      const sessionId = ctx.sessionManager.getSessionId();
      bindings.set(sessionId, {
        gate: String(result.current_gate),
        path: String(result.path),
        repositoryRoot,
        revision: String(result.revision),
        vaultRoot,
      });
      prdRequired.add(sessionId);
      return output({ ok: true, ...result });
    },
  });

  runtime.on("tool_result", (event: any, ctx: any) => {
    if (event.toolName === "read" && !event.isError && isCtxPrdSkill(event.input?.path)) {
      prdRequired.add(ctx.sessionManager.getSessionId());
    }
  });

  runtime.on("tool_call", async (event: any, ctx: any) => {
    if (!isRepositoryMutation(event, ctx.cwd)) return;
    const sessionId = ctx.sessionManager.getSessionId();
    if (!prdRequired.has(sessionId) && !bindings.has(sessionId)) return;
    const binding = bindings.get(sessionId);
    if (!binding) {
      return {
        block: true,
        reason: "PRD-owned source mutation requires ctx_prd_lifecycle gate.activate or gate.assert-active first.",
      };
    }
    const repository = await repositoryFingerprint(binding.repositoryRoot).catch(() => "");
    const guarded = await invokeCheckpoint(
      binding.vaultRoot,
      {
        path: binding.path,
        expected_revision: binding.revision,
        gate: binding.gate,
        repository,
      },
      "source-mutation",
    );
    if (!guarded.ok) {
      return {
        block: true,
        reason: `PRD source-mutation guard refused: ${String(guarded.error.message ?? guarded.error.code)}`,
      };
    }
  });

  runtime.on("session_stop", async (_event: any, ctx: any) => {
    const binding = bindings.get(ctx.sessionManager.getSessionId());
    if (!binding) return;
    const repository = await repositoryFingerprint(binding.repositoryRoot).catch(() => "");
    const guarded = await invokeCheckpoint(
      binding.vaultRoot,
      {
        path: binding.path,
        expected_revision: binding.revision,
        gate: binding.gate,
        repository,
      },
      "yield",
    );
    if (!guarded.ok) {
      return {
        decision: "block" as const,
        reason: `Canonical PRD checkpoint is stale: ${String(guarded.error.message ?? guarded.error.code)}. Call ctx_prd_lifecycle gate.update, gate.block, verifier.accepted, verifier.rejected, or workflow.pause before yielding.`,
      };
    }
  });

  runtime.on("session_shutdown", (_event: unknown, ctx: any) => {
    const sessionId = ctx.sessionManager.getSessionId();
    bindings.delete(sessionId);
    prdRequired.delete(sessionId);
  });
}
