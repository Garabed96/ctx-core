#!/usr/bin/env python3
"""Block repository-write tools when an armed PRD gate refuses mutation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))


def fail_open(message: str) -> int:
    print(f"warning: Codex PRD pre-tool hook: {message}", file=sys.stderr)
    return 0


def main() -> int:
    try:
        import prd_arming

        payload = json.load(sys.stdin)
        repository = Path(payload["cwd"])
        record = prd_arming.read(repository)
        if record is None:
            if prd_arming._record_path(repository).exists():
                return fail_open("arming state is unreadable or malformed")
            return 0
        armed_repository = Path(record["repository_root"])
        if armed_repository.resolve() != repository.resolve():
            return fail_open("arming state belongs to a different repository")

        checkpoint = SCRIPTS_ROOT / "prd_checkpoint.py"
        if not checkpoint.is_file():
            return fail_open("packaged prd_checkpoint.py is missing")
        request = {
            "path": record["path"],
            "expected_revision": record["expected_revision"],
            "gate": record["gate"],
            "repository": str(armed_repository.resolve()),
        }
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
    except Exception as error:  # noqa: BLE001 - hook failures must not block unrelated work
        return fail_open(str(error))

    reason = completed.stderr.strip() or completed.stdout.strip() or "guard refused"
    try:
        reason = json.loads(reason).get("message", reason)
    except (ValueError, AttributeError):
        pass
    if completed.returncode == 0:
        return 0
    if completed.returncode != 3:
        return fail_open(f"checkpoint command failed: {reason}")
    print(f"PRD source-mutation guard refused: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
