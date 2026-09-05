#!/usr/bin/env python3
"""Fingerprint HEAD, tracked changes and untracked files for checkpoint evidence.

A mismatch invalidates the previous snapshot; it does not identify the author
or determine whether a product claim changed. All runtime adapters use this
command so their evidence uses the same bytes and ordering.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def _git(root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def fingerprint(root: Path) -> str:
    """Return the deterministic fingerprint for the repository at ``root``.

    Raises on Git or file errors rather than returning unverifiable evidence.
    """
    root = Path(root).resolve()
    head = _git(root, "rev-parse", "HEAD").decode("utf-8", "strict").strip()
    diff = _git(root, "diff", "--binary", "HEAD", "--", ".")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    digest = hashlib.sha256(diff)
    paths = sorted(item for item in untracked.split(b"\0") if item)
    for relative in paths:
        digest.update(b"\0")
        digest.update(relative)
        digest.update(b"\0")
        digest.update((root / relative.decode("utf-8", "surrogateescape")).read_bytes())
    return f"git:{head}:worktree:{digest.hexdigest()}"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: repo_fingerprint.py <repository-root>", file=sys.stderr)
        return 2
    try:
        print(fingerprint(Path(sys.argv[1])))
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode("utf-8", "replace").strip() if error.stderr else str(error)
        print(f"repo_fingerprint.py: {message}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"repo_fingerprint.py: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
