#!/usr/bin/env python3
"""Validate composed CTX plugins and optional model-routing results."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RUNTIMES = {
    "claude-code": ".claude-plugin",
    "codex": ".codex-plugin",
    "omp": ".omp-plugin",
}
CATALOGS = {
    "claude-code": ".claude-plugin/marketplace.json",
    "codex": ".agents/plugins/marketplace.json",
    "omp": ".omp-plugin/marketplace.json",
}
EXPECTED_SKILLS = {"ctx-prd", "ctx-lean"}
EXPECTED_REFERENCES = {
    "ctx-prd": {
        "artifact-contract.md",
        "continuity-execution.md",
        "product-interview.md",
        "prd-checkpoint.md",
        "qa-evidence.md",
        "runtime-interface.md",
        "runtime.md",
    },
    "ctx-lean": {
        "continuity-execution.md",
        "debugging.md",
        "prd-checkpoint.md",
        "review-feedback.md",
        "runtime-interface.md",
        "runtime.md",
        "testing.md",
    },
}
RESULT_FIELDS = {"route", "authorization", "durable_state", "mode", "worktree"}
REFERENCE_PATTERN = re.compile(r"references/[a-z0-9-]+\.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CTX composition contract checks.")
    parser.add_argument(
        "--results",
        type=Path,
        help="Optional JSON results produced from contract-tests/evaluator.md.",
    )
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frontmatter(markdown: str) -> dict[str, str]:
    require(markdown.startswith("---\n"), "SKILL.md is missing frontmatter")
    end = markdown.find("\n---\n", 4)
    require(end != -1, "SKILL.md frontmatter is not closed")
    parsed: dict[str, str] = {}
    for line in markdown[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            parsed[key.strip()] = value.strip()
    return parsed


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def compose(repo: Path, runtime: str, target: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "installer" / "compose.py"),
            "--runtime",
            runtime,
            "--output",
            str(target),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    require(completed.returncode == 0, completed.stderr or completed.stdout)
    require(
        Path(completed.stdout.strip()).resolve() == target.resolve(),
        "composer reported the wrong target",
    )


def validate_composition(repo: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="ctx-core-contract-") as temporary:
        temp = Path(temporary)
        for runtime, manifest_dir in RUNTIMES.items():
            first = temp / f"{runtime}-first" / "ctx"
            second = temp / f"{runtime}-second" / "ctx"
            compose(repo, runtime, first)
            compose(repo, runtime, second)
            require(tree_digest(first) == tree_digest(second), f"{runtime} composition is not deterministic")

            distribution = repo / "dist" / runtime / "ctx"
            require(distribution.is_dir(), f"{runtime} distribution is missing")
            require(
                tree_digest(distribution) == tree_digest(first),
                f"{runtime} committed distribution is stale",
            )

            catalog = json.loads((repo / CATALOGS[runtime]).read_text())
            entries = catalog.get("plugins", [])
            require(len(entries) == 1 and entries[0].get("name") == "ctx", f"{runtime} catalog drifted")
            source = entries[0].get("source")
            source_path = source.get("path") if isinstance(source, dict) else source
            require(source_path == f"./dist/{runtime}/ctx", f"{runtime} catalog source drifted")

            manifest = json.loads((first / manifest_dir / "plugin.json").read_text())
            require(manifest["name"] == "ctx", f"{runtime} plugin name drifted")
            require(bool(manifest.get("version")), f"{runtime} plugin version is missing")

            checkpoint_command = first / "scripts" / "prd_checkpoint.py"
            require(
                checkpoint_command.is_file(),
                f"{runtime} checkpoint command is missing",
            )
            require(
                checkpoint_command.stat().st_mode & 0o111 != 0,
                f"{runtime} checkpoint command is not executable",
            )
            require(
                (first / "scripts" / "prd_document.py").is_file(),
                f"{runtime} canonical document validator is missing",
            )
            if runtime == "omp":
                require(
                    (first / "extensions" / "prd-lifecycle.ts").is_file(),
                    "omp lifecycle extension is missing",
                )
                require(
                    (first / "package.json").is_file(),
                    "omp local package manifest is missing",
                )
                package = json.loads((first / "package.json").read_text())
                require(package["name"] == "ctx", "omp local package name drifted")
                require(
                    package["version"] == manifest["version"],
                    "omp local package version drifted",
                )
                require(
                    package.get("omp", {}).get("extensions")
                    == ["./extensions/prd-lifecycle.ts"],
                    "omp local package omits lifecycle extension",
                )

            skills_root = first / "skills"
            skills = {item.name for item in skills_root.iterdir() if item.is_dir()}
            require(skills == EXPECTED_SKILLS, f"{runtime} exposes unexpected skills: {sorted(skills)}")

            for skill_name in sorted(EXPECTED_SKILLS):
                skill_root = skills_root / skill_name
                skill_text = (skill_root / "SKILL.md").read_text()
                metadata = frontmatter(skill_text)
                require(metadata.get("name") == skill_name, f"{skill_name} frontmatter name drifted")
                require(bool(metadata.get("description")), f"{skill_name} description is missing")

                references_root = skill_root / "references"
                references = {item.name for item in references_root.iterdir() if item.is_file()}
                require(
                    references == EXPECTED_REFERENCES[skill_name],
                    f"{runtime}/{skill_name} reference set drifted: {sorted(references)}",
                )

                for source in [skill_root / "SKILL.md", *references_root.glob("*.md")]:
                    text = source.read_text()
                    for reference in REFERENCE_PATTERN.findall(text):
                        require(
                            (skill_root / reference).is_file(),
                            f"{runtime}/{skill_name} has unresolved reference {reference}",
                        )


def validate_checkpoint_contract(repo: Path) -> None:
    checkpoint = (repo / "core" / "references" / "prd-checkpoint.md").read_text()
    transitions = {
        "assert-active",
        "activate",
        "update",
        "block",
        "amend",
        "resume",
        "retry",
        "pass",
        "fail",
        "pause",
        "assert-merge",
        "record-merge",
    }
    for transition in transitions:
        require(f"`{transition}`" in checkpoint, f"checkpoint transition is missing: {transition}")

    runtime_interface = (repo / "core" / "references" / "runtime-interface.md").read_text()
    continuity = (repo / "core" / "references" / "continuity-execution.md").read_text()
    require("`PrdCheckpoint`" in runtime_interface, "runtime interface omits PrdCheckpoint")
    require("## PRD checkpoint and merge barrier" in continuity, "merge barrier contract is missing")

    artifact = (
        repo / "core" / "skills" / "ctx-prd" / "references" / "artifact-contract.md"
    ).read_text()
    for field in (
        "revision: r1",
        "- Gate:",
        "- Status:",
        "- Verified:",
        "- Blockers:",
        "- Decision:",
        "- Next:",
        "- Repository:",
        "- **Feature list:**",
        "- **Implementation plan:**",
    ):
        require(field in artifact, f"canonical PRD field is missing: {field}")
    for section in (
        "## Outcome",
        "## Boundaries",
        "## Decisions",
        "## Current checkpoint",
        "## Gates",
        "## Approval",
        "## Evidence",
        "## Amendments",
    ):
        require(section in artifact, f"canonical PRD section is missing: {section}")

    for skill_name in EXPECTED_SKILLS:
        skill = (repo / "core" / "skills" / skill_name / "SKILL.md").read_text()
        require("`PrdCheckpoint`" in skill, f"{skill_name} does not cross PrdCheckpoint")
        require(
            "references/prd-checkpoint.md" in skill,
            f"{skill_name} does not load the checkpoint contract",
        )

    for runtime in RUNTIMES:
        adapter = (repo / "adapters" / runtime / "runtime.md").read_text()
        require("## `PrdCheckpoint`" in adapter, f"{runtime} adapter omits PrdCheckpoint")
        require("expected_revision" in adapter, f"{runtime} adapter omits revision checking")
        require("re-read" in adapter, f"{runtime} adapter omits checkpoint attestation")
        require(
            "scripts/prd_checkpoint.py" in adapter or "ctx_prd_lifecycle" in adapter,
            f"{runtime} adapter omits the executable checkpoint seam",
        )

    omp_extension = (
        repo / "adapters" / "omp" / "extensions" / "prd-lifecycle.ts"
    ).read_text()
    for contract in (
        "ctx_prd_lifecycle",
        'runtime.on("tool_call"',
        'runtime.on("session_stop"',
        '"source-mutation"',
        '"yield"',
    ):
        require(contract in omp_extension, f"omp enforcement omits: {contract}")

def validate_checkpoint_behavior(repo: Path) -> None:
    commands = (
        [sys.executable, str(repo / "contract-tests" / "test_prd_checkpoint.py")],
        [sys.executable, str(repo / "contract-tests" / "test_prd_protocol.py")],
        ["bun", "test", "./contract-tests/prd_lifecycle.test.ts"],
    )
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        require(
            completed.returncode == 0,
            completed.stderr or completed.stdout,
        )


def validate_cases(repo: Path, results_path: Path | None) -> int:
    cases = json.loads((repo / "contract-tests" / "cases.json").read_text())
    ids = [case["id"] for case in cases]
    require(len(ids) == len(set(ids)), "contract case ids must be unique")
    for case in cases:
        require(set(case["expected"]) == RESULT_FIELDS, f"{case['id']} expected fields drifted")

    if results_path is None:
        return len(cases)

    results = json.loads(results_path.read_text())
    actual_by_id = {result["id"]: result["actual"] for result in results}
    require(set(actual_by_id) == set(ids), "model results have missing or extra case ids")

    failures: list[str] = []
    for case in cases:
        actual = actual_by_id[case["id"]]
        if actual != case["expected"]:
            failures.append(
                f"{case['id']}: expected {case['expected']}, received {actual}"
            )
    require(not failures, "\n".join(failures))
    return len(cases)


def main() -> None:
    args = parse_args()
    repo = Path(__file__).resolve().parents[1]
    try:
        validate_composition(repo)
        validate_checkpoint_contract(repo)
        validate_checkpoint_behavior(repo)
        case_count = validate_cases(repo, args.results)
    except (AssertionError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    suffix = " with model results" if args.results else " (model results not supplied)"
    print(f"PASS: {len(RUNTIMES)} runtime compositions; {case_count} routing cases{suffix}")


if __name__ == "__main__":
    main()
