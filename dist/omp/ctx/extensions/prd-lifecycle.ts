import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
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

type LifecycleEvent = keyof typeof transitions;

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

async function repositoryFingerprint(repositoryRoot: string, signal?: AbortSignal) {
  const result = await runProcess(
    process.env.CTX_PYTHON ?? "python3",
    [path.join(path.dirname(command), "repo_fingerprint.py"), repositoryRoot],
    undefined,
    signal,
  );
  if (result.code !== 0) throw new Error(result.stderr.trim() || "Repository fingerprint failed");
  return result.stdout.trim();
}

async function invokeCheckpoint(
  vaultRoot: string,
  request: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<{ ok: true; result: CommandResult } | { ok: false; error: CommandResult }> {
  const args = [command, "--vault-root", vaultRoot];
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

export default function prdLifecycle(pi: ExtensionAPI) {
  const z = pi.zod;
  const runtime = pi as unknown as {
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
  const parameters = z.object({
    schemaVersion: z.literal(1),
    vaultRoot: z.string().min(1).optional(),
    path: z.string().min(1),
    expectedRevision: z.string().regex(/^r[1-9]\d*$/),
    gate: z.string().regex(/^[A-Za-z][A-Za-z0-9_-]*$/),
    event: z.enum(Object.keys(transitions) as [LifecycleEvent, ...LifecycleEvent[]]),
    verified: z.string().min(1),
    blockers: z.string().min(1),
    decision: z.string().min(1),
    nextAction: z.string().min(1),
    occurredAt: z.string().min(1),
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
      const transition = transitions[params.event as LifecycleEvent];
      const required = ["verified", "blockers", "decision", "nextAction", "occurredAt"];
      const missing = required.filter((field) => typeof params[field] !== "string" || !params[field].trim());
      if (missing.length) {
        return output({
          ok: false,
          code: "invalid_request",
          message: `Lifecycle transitions require ${missing.join(", ")}.`,
        });
      }
      const repositoryRoot = path.resolve(ctx.cwd);
      let repository: string;
      try {
        repository = await repositoryFingerprint(repositoryRoot, signal);
      } catch (error) {
        return output({ ok: false, code: "repository_fingerprint_failed", message: String(error) });
      }

      const request = {
        path: params.path,
        expected_revision: params.expectedRevision,
        gate: params.gate,
        repository,
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
      const invoked = await invokeCheckpoint(vaultRoot, request, signal);
      return output(invoked.ok ? { ok: true, ...invoked.result } : { ok: false, ...invoked.error });
    },
  });
}
