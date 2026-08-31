#!/usr/bin/env python3
"""On-disk arming-state record for the PRD source-mutation and yield guards.

OMP arms these guards in an in-memory per-session binding: reading
``skill://ctx-prd`` requires a first successful ``ctx_prd_lifecycle`` call,
and every later successful call refreshes that binding's gate/revision until
the extension's own session ends. A Claude Code hook is a fresh, memoryless
process on every invocation, so there is no session object to hold that
binding. ``prd_checkpoint.py`` persists the same fields here on every
successful transition or guard call, keyed by the repository working
directory it was invoked from; the packaged Claude Code hook scripts read it
back to decide whether a guard applies at all before ever shelling out to
``prd_checkpoint.py --guard``.

Deliberate deviation from OMP: because this record outlives any one process
or session, it must also be actively cleared on transitions after which no
further ``activate`` can plausibly re-arm it soon (a completed PRD, or a
paused gate) — otherwise a finished or indefinitely parked PRD would
permanently block bash/edit tools in that repository, even for later,
unrelated work. OMP has no equivalent failure mode; its binding simply
disappears with the session. See ``prd_checkpoint.py``'s ``_settle_arming``
for exactly which transitions clear it and why ``record-merge`` does not.

All functions fail closed to "no state" on any unexpected error — a missing,
unreadable, or malformed record must never crash a caller. Callers that
persist a record (``arm``) are responsible for deciding whether a failure
there should also fail the surrounding command; this module never raises
except from ``arm``/``disarm`` themselves, which callers should wrap.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {"vault_root", "path", "gate", "expected_revision"}


def state_dir() -> Path:
    """Resolve the directory arming records live in.

    ``CTX_ARM_STATE_DIR`` overrides the default for tests and sandboxes.
    Otherwise this sits beside the existing per-note checkpoint lock
    directory under the system temp root: both are ephemeral, host-local
    runtime state that must never be written into the durable Obsidian
    vault, and reusing that precedent needs no new convention.
    """
    override = os.environ.get("CTX_ARM_STATE_DIR")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / "ctx-core-prd-checkpoints" / "arming"


def _key(repository_root: Path) -> str:
    return hashlib.sha256(str(Path(repository_root).resolve()).encode("utf-8")).hexdigest()


def _record_path(repository_root: Path, directory: Path | None = None) -> Path:
    directory = directory if directory is not None else state_dir()
    return directory / f"{_key(repository_root)}.json"


def arm(
    repository_root: Path,
    *,
    vault_root: Path,
    path: str,
    gate: str,
    revision: str,
) -> None:
    """Persist (or refresh) the arming record for one repository."""
    directory = state_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = {
        "schema": 1,
        "repository_root": str(Path(repository_root).resolve()),
        "vault_root": str(Path(vault_root).resolve()),
        "path": path,
        "gate": gate,
        "expected_revision": revision,
    }
    target = _record_path(repository_root, directory)
    descriptor, temporary_name = tempfile.mkstemp(dir=directory, prefix=".arming-", suffix=".json")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, sort_keys=True)
        os.chmod(temporary_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary_name, target)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def disarm(repository_root: Path) -> None:
    """Clear the arming record for one repository. A no-op when unarmed."""
    try:
        _record_path(repository_root).unlink()
    except FileNotFoundError:
        pass


def read(repository_root: Path) -> dict[str, Any] | None:
    """Return the arming record for one repository, or ``None`` when unarmed.

    Never raises: any missing file, unreadable file, or structurally
    malformed record is treated as "no arming state" so callers fail open.
    """
    try:
        raw = _record_path(repository_root).read_text(encoding="utf-8")
        record = json.loads(raw)
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or not REQUIRED_FIELDS.issubset(record):
        return None
    return record
