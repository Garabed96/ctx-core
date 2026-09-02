#!/usr/bin/env python3
"""Compose the canonical CTX core with one runtime adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

RUNTIMES = {
    "claude-code": ".claude-plugin",
    "codex": ".codex-plugin",
    "omp": ".omp-plugin",
}
SKILLS = ("ctx-prd", "ctx-lean")
SHARED_REFERENCES = (
    "continuity-execution.md",
    "prd-checkpoint.md",
    "runtime-interface.md",
)
BUILD_MARKER = ".ctx-core-build.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose CTX skills for one supported runtime."
    )
    parser.add_argument("--runtime", required=True, choices=sorted(RUNTIMES))
    parser.add_argument(
        "--output",
        type=Path,
        help="Plugin output directory. Defaults to .build/<runtime>/ctx.",
    )
    return parser.parse_args()


def source_digest(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def prepare_output(target: Path, owned_root: Path, runtime: str) -> None:
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        return

    target_resolved = target.resolve()
    owned_resolved = owned_root.resolve()
    marker = target / BUILD_MARKER
    owned_build = target_resolved.is_relative_to(owned_resolved)
    matching_build = marker.is_file() and json.loads(marker.read_text()).get("runtime") == runtime
    if not owned_build and not matching_build:
        raise SystemExit(f"Refusing to replace non-CTX output: {target}")
    shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)


def compose(runtime: str, output: Path | None) -> Path:
    repo = Path(__file__).resolve().parents[1]
    core = repo / "core"
    adapter = repo / "adapters" / runtime / "runtime.md"
    metadata = json.loads((core / "plugin.json").read_text())
    owned_root = repo / ".build"
    target = output.resolve() if output else owned_root / runtime / metadata["name"]

    prepare_output(target, owned_root, runtime)
    target.mkdir(parents=True)

    source_paths = [core / "plugin.json", adapter]
    scripts = core / "scripts"
    shutil.copytree(
        scripts,
        target / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    source_paths.extend(
        path
        for path in scripts.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )

    adapter_root = adapter.parent
    for asset in sorted(adapter_root.iterdir()):
        if asset == adapter:
            continue
        destination = target / asset.name
        if asset.is_dir():
            shutil.copytree(
                asset,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            source_paths.extend(
                path
                for path in asset.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
            )
        else:
            shutil.copy2(asset, destination)
            source_paths.append(asset)
    for skill_name in SKILLS:
        source_skill = core / "skills" / skill_name
        target_skill = target / "skills" / skill_name
        shutil.copytree(source_skill, target_skill)
        references = target_skill / "references"
        references.mkdir(exist_ok=True)

        source_paths.extend(path for path in source_skill.rglob("*") if path.is_file())
        for reference_name in SHARED_REFERENCES:
            source_reference = core / "references" / reference_name
            shutil.copy2(source_reference, references / reference_name)
            source_paths.append(source_reference)
        shutil.copy2(adapter, references / "runtime.md")

    manifest_dir = target / RUNTIMES[runtime]
    manifest_dir.mkdir()
    manifest = {
        "name": metadata["name"],
        "version": metadata["version"],
        "description": metadata["description"],
        "author": metadata["author"],
    }
    if runtime in {"codex", "omp"}:
        manifest["skills"] = "./skills/"
    if runtime == "codex":
        manifest["hooks"] = "./hooks/hooks.json"
        manifest["license"] = metadata["license"]
        manifest["interface"] = {
            "displayName": "CTX Core",
            "shortDescription": "PRD and Lean continuity workflows",
            "developerName": metadata["author"]["name"],
            "category": "Coding",
            "capabilities": ["Interactive", "Write"],
        }
    (manifest_dir / "plugin.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    if runtime == "omp":
        package = {
            "name": metadata["name"],
            "version": metadata["version"],
            "private": True,
            "type": "module",
            "omp": {
                "name": "CTX Core",
                "version": metadata["version"],
                "description": metadata["description"],
                "extensions": ["./extensions/prd-lifecycle.ts"],
            },
        }
        (target / "package.json").write_text(
            json.dumps(package, indent=2, sort_keys=True) + "\n"
        )

    build = {
        "runtime": runtime,
        "skills": list(SKILLS),
        "source_sha256": source_digest(source_paths, repo),
        "version": metadata["version"],
    }
    (target / BUILD_MARKER).write_text(
        json.dumps(build, indent=2, sort_keys=True) + "\n"
    )
    return target


def main() -> None:
    args = parse_args()
    target = compose(args.runtime, args.output)
    print(target)


if __name__ == "__main__":
    main()
