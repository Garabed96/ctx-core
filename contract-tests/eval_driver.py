#!/usr/bin/env python3
"""Drive the routing contract eval against a live model, one fresh session per case.

Spawns an isolated read-only `codex exec` per case so answers cannot anchor each
other, collects the classifications, and scores them via check.py --results.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULT_FIELDS = {"route", "authorization", "durable_state", "mode", "worktree"}
RUNTIMES = ("codex",)

PROMPT_TEMPLATE = """{evaluator}

Classify exactly ONE case. Read the composed skills exactly as a session would \
receive them: {skills_dir}/ctx-prd/SKILL.md, {skills_dir}/ctx-lean/SKILL.md, and \
every file in their references/ directories. Route from that composed text, not \
from prior knowledge. Do not read contract-tests/cases.json or anything else \
under contract-tests/ — it contains the answer key.

Treat the following as the user's opening message to a fresh session with these \
skills installed:

<case-prompt>
{case_prompt}
</case-prompt>

Respond with ONLY the JSON `actual` object, no id, no fences, no rationale:
{{"route": ..., "authorization": ..., "durable_state": ..., "mode": ..., "worktree": ...}}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", default="codex", choices=RUNTIMES)
    parser.add_argument("--model", help="Model override passed to `codex exec -m`.")
    parser.add_argument("--jobs", type=int, default=4, help="Concurrent cases (default 4).")
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        metavar="ID",
        help="Run only this case id (repeatable). Skips scoring.",
    )
    parser.add_argument(
        "--results-out",
        type=Path,
        help="Where to write the results JSON (default: temp file, path printed).",
    )
    parser.add_argument(
        "--timeout", type=int, default=600, help="Per-case timeout in seconds."
    )
    return parser.parse_args()


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def run_case(case: dict, args: argparse.Namespace, evaluator: str, workdir: Path) -> dict:
    skills_dir = f"dist/{args.runtime}/ctx/skills"
    prompt = PROMPT_TEMPLATE.format(
        evaluator=evaluator, skills_dir=skills_dir, case_prompt=case["prompt"]
    )
    out_file = workdir / f"{case['id']}.txt"
    command = ["codex", "exec", "-s", "read-only", "--color", "never", "-o", str(out_file)]
    if args.model:
        command += ["-m", args.model]
    command.append("-")
    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=REPO,
        timeout=args.timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{case['id']}: codex exec exited {completed.returncode}: "
            f"{(completed.stderr or completed.stdout)[-300:]}"
        )
    actual = extract_json(out_file.read_text())
    if set(actual) != RESULT_FIELDS:
        raise ValueError(f"{case['id']}: fields drifted from contract: {sorted(actual)}")
    return {"id": case["id"], "actual": actual}


def main() -> int:
    args = parse_args()
    evaluator = (REPO / "contract-tests" / "evaluator.md").read_text()
    cases = json.loads((REPO / "contract-tests" / "cases.json").read_text())
    stripped = [{"id": c["id"], "prompt": c["prompt"]} for c in cases]
    if args.cases:
        unknown = set(args.cases) - {c["id"] for c in stripped}
        if unknown:
            sys.exit(f"unknown case ids: {sorted(unknown)}")
        stripped = [c for c in stripped if c["id"] in args.cases]

    results: list[dict] = []
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ctx-eval-") as tmp:
        workdir = Path(tmp)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = {
                pool.submit(run_case, case, args, evaluator, workdir): case["id"]
                for case in stripped
            }
            for future in concurrent.futures.as_completed(futures):
                case_id = futures[future]
                try:
                    results.append(future.result())
                    print(f"done: {case_id}", file=sys.stderr)
                except Exception as error:  # noqa: BLE001 - report and continue
                    failures.append(f"{case_id}: {error}")
                    print(f"FAILED: {case_id}: {error}", file=sys.stderr)

    results.sort(key=lambda r: r["id"])
    results_out = args.results_out or Path(
        tempfile.mkstemp(prefix=f"ctx-eval-{args.runtime}-", suffix=".json")[1]
    )
    results_out.write_text(json.dumps(results, indent=1) + "\n")
    print(f"results: {results_out}")

    if failures:
        print(f"{len(failures)} case(s) failed to produce a classification", file=sys.stderr)
        return 1
    if args.cases:
        print("partial run; skipping check.py scoring")
        return 0
    completed = subprocess.run(
        [sys.executable, str(REPO / "contract-tests" / "check.py"), "--results", str(results_out)],
        cwd=REPO,
    )
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
