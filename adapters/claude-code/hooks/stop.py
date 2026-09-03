#!/usr/bin/env python3
"""Stop hook: enforce the PRD yield guard once armed.

Bails out fast (exit 0) whenever this repository has no on-disk arming
record from ``prd_arming``. When armed, computes the current deterministic
repository fingerprint (see ``repo_fingerprint``) and shells out to the
packaged ``prd_checkpoint.py --guard yield``; blocks (exit 2) only on that
command's genuine refusal (nonterminal work with a stale repository
fingerprint versus ``Current checkpoint``) — a structurally complete PRD
with every gate passed is accepted, matching OMP. Any unexpected trouble
inside this script itself, including a fingerprint that cannot be computed
(no git, not a repository, permission error), fails open (exit 0, warning on
stderr) instead of blocking an unrelated or already-settled turn.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = HOOK_ROOT.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))


def _fail_open(message: str) -> int:
    if message:
        print(f"prd-checkpoint stop hook: {message}", file=sys.stderr)
    return 0


def main() -> int:
    try:
        import prd_arming
        import repo_fingerprint
    except Exception as error:  # noqa: BLE001 - never block on our own breakage
        return _fail_open(f"could not load checkpoint modules: {error}")

    try:
        payload = json.load(sys.stdin)
    except Exception as error:  # noqa: BLE001
        return _fail_open(f"could not read hook input: {error}")

    if isinstance(payload, dict) and payload.get("stop_hook_active"):
        return 0  # Claude Code re-entry after a block; blocking again creates an infinite loop

    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    if not cwd:
        return _fail_open("hook input is missing cwd")

    try:
        record = prd_arming.read(Path(cwd))
    except Exception as error:  # noqa: BLE001 - prd_arming.read should not raise, but never trust that blindly
        return _fail_open(f"could not read arming state: {error}")

    if record is None:
        return 0  # unarmed: no PRD gate has been attested for this repository

    if prd_arming.foreign_session(record, payload.get("session_id")):
        return 0  # armed by another agent session; its own hooks enforce the guard

    try:
        repository = repo_fingerprint.fingerprint(Path(cwd))
    except Exception as error:  # noqa: BLE001 - not a repo, no git, unreadable file, etc.
        return _fail_open(f"could not compute repository fingerprint: {error}")

    checkpoint = SCRIPTS_ROOT / "prd_checkpoint.py"
    if not checkpoint.is_file():
        return _fail_open("packaged prd_checkpoint.py is missing")

    request = {
        "path": record["path"],
        "expected_revision": record["expected_revision"],
        "gate": record["gate"],
        "repository": repository,
    }
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(checkpoint),
                "--vault-root",
                record["vault_root"],
                "--guard",
                "yield",
            ],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as error:  # noqa: BLE001
        return _fail_open(f"could not run prd_checkpoint.py: {error}")

    if completed.returncode == 0:
        return 0

    reason = completed.stderr.strip() or completed.stdout.strip() or "PRD yield guard refused"
    try:
        reason = json.loads(reason).get("message", reason)
    except (ValueError, AttributeError):
        pass
    print(
        f"Canonical PRD checkpoint is stale: {reason}. Run "
        f'"{checkpoint}" --vault-root {record["vault_root"]} with an update, '
        f"block, pass, fail, or pause transition for gate "
        f'{record["gate"]} of {record["path"]} before yielding.',
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
