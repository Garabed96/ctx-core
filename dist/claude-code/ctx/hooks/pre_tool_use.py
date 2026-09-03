#!/usr/bin/env python3
"""PreToolUse hook: enforce the PRD source-mutation guard once armed.

``hooks.json`` fires this only for ``Edit|Write|MultiEdit|NotebookEdit|Bash``.
It bails out fast (exit 0) whenever this repository has no on-disk arming
record from ``prd_arming`` — standalone and unrelated work pays no more than
one stat call and is otherwise completely unaffected. When armed, it shells
out to the packaged ``prd_checkpoint.py --guard source-mutation`` and blocks
(exit 2) only on that command's genuine refusal. Any unexpected trouble
inside this script itself — malformed hook input, a missing module, a
subprocess that cannot start — fails open (exit 0, warning on stderr)
instead of blocking unrelated work.
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
        print(f"prd-checkpoint pre-tool-use hook: {message}", file=sys.stderr)
    return 0


def main() -> int:
    try:
        import prd_arming
    except Exception as error:  # noqa: BLE001 - never block on our own breakage
        return _fail_open(f"could not load arming state module: {error}")

    try:
        payload = json.load(sys.stdin)
    except Exception as error:  # noqa: BLE001
        return _fail_open(f"could not read hook input: {error}")

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

    checkpoint = SCRIPTS_ROOT / "prd_checkpoint.py"
    if not checkpoint.is_file():
        return _fail_open("packaged prd_checkpoint.py is missing")

    request = {
        "path": record["path"],
        "expected_revision": record["expected_revision"],
        "gate": record["gate"],
        # source-mutation never compares this field against Current
        # checkpoint (see guard_document's "source-mutation" branch in
        # prd_checkpoint.py); a fixed marker keeps this hook a single cheap
        # subprocess call with no git work on the hot path.
        "repository": "claude-code-pre-tool-use",
    }
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(checkpoint),
                "--vault-root",
                record["vault_root"],
                "--guard",
                "source-mutation",
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

    reason = completed.stderr.strip() or completed.stdout.strip() or "PRD source-mutation guard refused"
    try:
        reason = json.loads(reason).get("message", reason)
    except (ValueError, AttributeError):
        pass
    print(
        "PRD source-mutation guard refused: "
        f"{reason}. Run "
        f'"{checkpoint}" --vault-root {record["vault_root"]} with an activate '
        f'or assert-active transition for gate {record["gate"]} of '
        f'{record["path"]} before this edit.',
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
