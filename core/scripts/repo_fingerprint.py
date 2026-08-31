#!/usr/bin/env python3
"""Print the deterministic git/worktree repository fingerprint for one path.

Mirrors OMP's ``repositoryFingerprint`` byte-for-byte: ``git:<HEAD>:worktree:
<sha256 of the tracked diff against HEAD, followed by every untracked file's
path and bytes in sorted order>``. Both sides of the ``PrdCheckpoint`` yield
guard must agree exactly on this value for a given repository state:

- the model runs this command to fill the ``repository`` field before every
  transition that carries current execution truth (see
  ``references/prd-checkpoint.md``);
- the packaged Claude Code ``Stop`` hook calls ``fingerprint()`` directly to
  compare the live repository against ``Current checkpoint`` before letting
  the turn end.

A prose-only, freeform fingerprint (a branch name, a loose description)
cannot be verified this way, which is why the Claude Code adapter requires
this exact command rather than leaving the format to model judgment.
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

    Raises on any git failure (not a repository, git unavailable, unreadable
    file): callers that must fail open on infrastructure trouble should
    catch broadly around this call rather than treat it as a guard refusal.
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
