#!/usr/bin/env python3
"""Black-box contract tests for the deterministic PRD checkpoint command."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMMAND = REPO / "core" / "scripts" / "prd_checkpoint.py"

PRD = """---
title: Example — PRD
type: ctx-prd
status: approved
revision: r1
current_gate: null
branch: feat/example
worktree: /tmp/example
approved_by: Garo
approved_at: 2026-08-31T09:00:00Z
created: 2026-08-31
updated: 2026-08-31
---

# Example — PRD

## Outcome
An observable result.

## Boundaries
- **In:** First and second behavior.
- **Out:** Unrelated behavior.
- **Preserve:** Existing contracts.

## Decisions
| Decision | Rationale |
|---|---|
| Use the existing seam. | Avoid duplicate behavior. |

## Current checkpoint
- Gate: null
- Status: pending
- Verified: none
- Blockers: none
- Decision: none
- Next: Activate G1
- Repository: feat/example

## Gates
### G1 — First vertical slice
- **Proves:** First behavior works.
- **Feature list:**
  - Complete the first user-visible behavior.
- **Implementation plan:** [[Example Initiative/Planning/example-g1-first-vertical-slice|G1 plan]]
- **Verifier:** automated — focused contract command
- **Status:** pending
- **Evidence:** none

### G2 — Second vertical slice
- **Proves:** Second behavior works.
- **Feature list:**
  - Complete the second user-visible behavior.
- **Implementation plan:** [[Example Initiative/Planning/example-g2-second-vertical-slice|G2 plan]]
- **Verifier:** human — product owner
- **Status:** pending
- **Evidence:** none

## Approval
- [x] Approved for execution

## Evidence
- None.

## Amendments
- None.
"""


def plan(gate: str, prd_path: str) -> str:
    return f"""---
title: Example {gate} plan
type: implementation-plan
status: planned
gate: {gate}
prd: "[[{prd_path}|Example PRD]]"
---

# Example {gate} plan

## Outcome
The gate behavior works.

## Reuse decisions
- Reuse the existing seam.

## Implementation slice
1. Implement the gate behavior.

## Parallel execution contract
- **Backend/contracts/architecture owner:** Main owns contracts and architecture.
- **Independent UI or specialist lane:** Not applicable
- **Shared integration owner:** Main integrates the gate.
- **File ownership and no-overlap constraints:** One owner changes the fixture.
- **Final integration and verification pass:** Main runs the focused contract.

## Verification
- Run the focused contract.

## Non-goals
- Unrelated behavior.
"""

def set_gate_status(document: str, gate: str, status: str) -> str:
    pattern = re.compile(
        rf"(?ms)(^### {re.escape(gate)}\b.*?^- \*\*Status:\*\*)\s*\w+"
    )
    updated, count = pattern.subn(rf"\1 {status}", document, count=1)
    if count != 1:
        raise AssertionError(f"gate not found: {gate}")
    return updated


def set_checkpoint(document: str, updates: dict[str, str]) -> str:
    start = document.index("## Current checkpoint")
    end = document.index("\n## Gates", start)
    section = document[start:end]
    for field, value in updates.items():
        section, count = re.subn(
            rf"(?m)^- {re.escape(field)}:\s*.*$",
            f"- {field}: {value}",
            section,
            count=1,
        )
        if count != 1:
            raise AssertionError(f"checkpoint field not found: {field}")
    return document[:start] + section + document[end:]



class CheckpointCommandTest(unittest.TestCase):
    @staticmethod
    def ensure_plans(vault: Path) -> None:
        prd_path = "Example Initiative/PRD/example.md"
        for gate, filename in (
            ("G1", "example-g1-first-vertical-slice.md"),
            ("G2", "example-g2-second-vertical-slice.md"),
        ):
            target = vault / "Example Initiative" / "Planning" / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(plan(gate, prd_path), encoding="utf-8")

    def invoke(self, vault: Path, request: dict[str, object]) -> subprocess.CompletedProcess[str]:
        self.ensure_plans(vault)
        return subprocess.run(
            [sys.executable, str(COMMAND), "--vault-root", str(vault)],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            check=False,
        )
    def guard(
        self,
        vault: Path,
        action: str,
        request: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        self.ensure_plans(vault)
        return subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--vault-root",
                str(vault),
                "--guard",
                action,
            ],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            check=False,
        )


    def test_activate_updates_gate_and_checkpoint_in_one_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            note.write_text(PRD, encoding="utf-8")

            completed = self.invoke(
                vault,
                {
                    "path": str(path),
                    "expected_revision": "r1",
                    "gate": "G1",
                    "transition": "activate",
                    "verified": "Approval recorded for Gate 1 execution.",
                    "blockers": "none",
                    "decision": "unchanged",
                    "next_action": "Implement the G1 vertical slice.",
                    "repository": "branch feat/example",
                    "occurred_at": "2026-08-31T10:00:00Z",
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(
                result,
                {
                    "attestation": result["attestation"],
                    "current_gate": "G1",
                    "gate_status": "active",
                    "lifecycle_status": "active",
                    "path": str(path),
                    "revision": "r2",
                    "transition": "activate",
                },
            )

            updated = note.read_text(encoding="utf-8")
            self.assertIn("status: active", updated)
            self.assertIn("revision: r2", updated)
            self.assertIn("current_gate: G1", updated)
            self.assertIn("updated: 2026-08-31", updated)
            self.assertIn("### G1 — First vertical slice", updated)
            self.assertIn("- **Status:** active", updated)
            self.assertIn("### G2 — Second vertical slice", updated)
            self.assertIn("- **Status:** pending", updated)
            self.assertIn(
                "## Current checkpoint\n"
                "- Gate: G1\n"
                "- Status: active\n"
                "- Verified: Approval recorded for Gate 1 execution.\n"
                "- Blockers: none\n"
                "- Decision: unchanged\n"
                "- Next: Implement the G1 vertical slice.\n"
                "- Repository: branch feat/example",
                updated,
            )


    def test_assert_active_attests_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            active = (
                PRD.replace("status: approved", "status: active")
                .replace("revision: r1", "revision: r7")
                .replace("current_gate: null", "current_gate: G1")
            )
            active = set_gate_status(active, "G1", "active")
            active = set_checkpoint(
                active,
                {
                    "Gate": "G1",
                    "Status": "active",
                    "Verified": "Approval recorded.",
                    "Blockers": "none",
                    "Decision": "unchanged",
                    "Next": "Continue G1.",
                    "Repository": "branch feat/example",
                },
            )
            note.write_text(active, encoding="utf-8")

            completed = self.invoke(
                vault,
                {
                    "path": str(path),
                    "expected_revision": "r7",
                    "gate": "G1",
                    "transition": "assert-active",
                    "verified": "Gate G1 is active.",
                    "blockers": "none",
                    "decision": "unchanged",
                    "next_action": "Continue G1.",
                    "repository": "branch feat/example",
                    "occurred_at": "2026-08-31T10:05:00Z",
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["revision"], "r7")
            self.assertEqual(result["gate_status"], "active")
            self.assertEqual(result["transition"], "assert-active")
            self.assertEqual(note.read_text(encoding="utf-8"), active)


    def test_pass_requires_accepted_named_verifier_and_advances_only_current_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            active = (
                PRD.replace("status: approved", "status: active")
                .replace("revision: r1", "revision: r2")
                .replace("current_gate: null", "current_gate: G1")
            )
            active = set_gate_status(active, "G1", "active")
            active = set_checkpoint(
                active,
                {
                    "Gate": "G1",
                    "Status": "active",
                    "Verified": "Approval recorded.",
                    "Blockers": "none",
                    "Decision": "unchanged",
                    "Next": "Verify G1.",
                    "Repository": "branch feat/example",
                },
            )
            note.write_text(active, encoding="utf-8")

            completed = self.invoke(
                vault,
                {
                    "path": str(path),
                    "expected_revision": "r2",
                    "gate": "G1",
                    "transition": "pass",
                    "verified": "Focused contract command passed: evidence://run-123.",
                    "blockers": "none",
                    "decision": "unchanged",
                    "next_action": "Activate G2.",
                    "repository": "branch feat/example commit abc123",
                    "occurred_at": "2026-08-31T10:10:00Z",
                    "verification": {
                        "kind": "automated",
                        "identity": "focused contract command",
                        "status": "accepted",
                    },
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["revision"], "r3")
            self.assertEqual(result["gate_status"], "passed")
            self.assertEqual(result["lifecycle_status"], "active")

            updated = note.read_text(encoding="utf-8")
            self.assertIn("revision: r3", updated)
            self.assertIn("current_gate: G1", updated)
            self.assertIn("- **Status:** passed", updated)
            self.assertIn(
                "- **Evidence:** Focused contract command passed: evidence://run-123.",
                updated,
            )
            self.assertIn("### G2 — Second vertical slice", updated)
            self.assertIn("- **Status:** pending", updated)
            self.assertIn(
                "## Current checkpoint\n"
                "- Gate: G1\n"
                "- Status: passed\n"
                "- Verified: Focused contract command passed: evidence://run-123.\n"
                "- Blockers: none",
                updated,
            )


    def test_failed_gate_can_retry_and_paused_gate_can_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            active = (
                PRD.replace("status: approved", "status: active")
                .replace("revision: r1", "revision: r2")
                .replace("current_gate: null", "current_gate: G1")
            )
            active = set_gate_status(active, "G1", "active")
            active = set_checkpoint(
                active,
                {
                    "Gate": "G1",
                    "Status": "active",
                    "Verified": "Approval recorded.",
                    "Blockers": "none",
                    "Decision": "unchanged",
                    "Next": "Continue G1.",
                    "Repository": "branch feat/example",
                },
            )
            note.write_text(active, encoding="utf-8")

            def transition(
                name: str,
                revision: str,
                verified: str,
                *,
                verification_status: str | None = None,
            ) -> dict[str, str]:
                request: dict[str, object] = {
                    "path": str(path),
                    "expected_revision": revision,
                    "gate": "G1",
                    "transition": name,
                    "verified": verified,
                    "blockers": verified if name in {"block", "fail"} else "none",
                    "decision": "unchanged",
                    "next_action": f"Continue after {name}.",
                    "repository": "branch feat/example",
                    "occurred_at": "2026-08-31T10:20:00Z",
                }
                if verification_status:
                    request["verification"] = {
                        "kind": "automated",
                        "identity": "focused contract command",
                        "status": verification_status,
                    }
                completed = self.invoke(vault, request)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            blocked = transition("block", "r2", "Dependency unavailable.")
            self.assertEqual(
                (blocked["revision"], blocked["gate_status"], blocked["lifecycle_status"]),
                ("r3", "blocked", "blocked"),
            )

            resumed = transition("resume", "r3", "Dependency restored.")
            self.assertEqual(
                (resumed["revision"], resumed["gate_status"], resumed["lifecycle_status"]),
                ("r4", "active", "active"),
            )

            failed = transition(
                "fail",
                "r4",
                "Focused contract command failed: evidence://run-124.",
                verification_status="rejected",
            )
            self.assertEqual(
                (failed["revision"], failed["gate_status"], failed["lifecycle_status"]),
                ("r5", "failed", "blocked"),
            )

            retried = transition("retry", "r5", "Failure remediated.")
            self.assertEqual(
                (retried["revision"], retried["gate_status"], retried["lifecycle_status"]),
                ("r6", "active", "active"),
            )

            paused = transition("pause", "r6", "Session parked with current evidence.")
            self.assertEqual(
                (paused["revision"], paused["gate_status"], paused["lifecycle_status"]),
                ("r7", "active", "paused"),
            )

            resumed_after_pause = transition("resume", "r7", "Repository state reverified.")
            self.assertEqual(
                (
                    resumed_after_pause["revision"],
                    resumed_after_pause["gate_status"],
                    resumed_after_pause["lifecycle_status"],
                ),
                ("r8", "active", "active"),
            )


    def test_activate_refuses_gate_when_predecessor_has_not_passed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            note.write_text(PRD, encoding="utf-8")

            completed = self.invoke(
                vault,
                {
                    "path": str(path),
                    "expected_revision": "r1",
                    "gate": "G2",
                    "transition": "activate",
                    "verified": "Approval recorded.",
                    "blockers": "none",
                    "decision": "unchanged",
                    "next_action": "Implement G2.",
                    "repository": "branch feat/example",
                    "occurred_at": "2026-08-31T10:30:00Z",
                },
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stderr)
            self.assertEqual(error["code"], "illegal_transition")
            self.assertEqual(note.read_text(encoding="utf-8"), PRD)


    def test_merge_requires_same_revision_assertion_before_recording(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            complete = (
                PRD.replace("status: approved", "status: complete")
                .replace("revision: r1", "revision: r5")
                .replace("current_gate: null", "current_gate: G2")
            )
            complete = set_gate_status(complete, "G1", "passed")
            complete = set_gate_status(complete, "G2", "passed")
            complete = set_checkpoint(
                complete,
                {
                    "Gate": "G2",
                    "Status": "passed",
                    "Verified": "Human verifier accepted G2.",
                    "Blockers": "none",
                    "Decision": "unchanged",
                    "Next": "Assert merge readiness.",
                    "Repository": "branch feat/example commit abc123",
                },
            )
            note.write_text(complete, encoding="utf-8")

            assertion_request = {
                "path": str(path),
                "expected_revision": "r5",
                "gate": "G2",
                "transition": "assert-merge",
                "verified": "All gates passed and repository commit abc123 is current.",
                "blockers": "none",
                "decision": "unchanged",
                "next_action": "Merge the approved branch.",
                "repository": "branch feat/example commit abc123",
                "occurred_at": "2026-08-31T10:40:00Z",
            }
            asserted = self.invoke(vault, assertion_request)
            self.assertEqual(asserted.returncode, 0, asserted.stderr)
            assertion = json.loads(asserted.stdout)
            self.assertEqual(assertion["revision"], "r5")
            self.assertIn("merge_assertion", assertion)
            self.assertEqual(note.read_text(encoding="utf-8"), complete)

            record_request = {
                **assertion_request,
                "transition": "record-merge",
                "verified": "PR #42 merged at def456.",
                "blockers": "none",
                "next_action": "Close the completed PRD.",
                "repository": "PR #42 merge def456",
                "merge_assertion": assertion["merge_assertion"],
            }
            recorded = self.invoke(vault, record_request)
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            result = json.loads(recorded.stdout)
            self.assertEqual(result["revision"], "r6")
            self.assertEqual(result["lifecycle_status"], "complete")
            self.assertIn("- Repository: PR #42 merge def456", note.read_text(encoding="utf-8"))


    def test_amend_replaces_one_decision_and_gate_contract_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            paused = (
                PRD.replace("status: approved", "status: paused")
                .replace("revision: r1", "revision: r9")
                .replace("current_gate: null", "current_gate: G1")
                .replace(
                    "| Use the existing seam. | Avoid duplicate behavior. |",
                    "| Use suggestions | Matches the current flow. |",
                )
            )
            paused = set_gate_status(paused, "G1", "active")
            paused = set_checkpoint(
                paused,
                {
                    "Gate": "G1",
                    "Status": "paused",
                    "Verified": "Existing verification.",
                    "Blockers": "none",
                    "Decision": "Use suggestions",
                    "Next": "Amend G1.",
                    "Repository": "branch feat/example",
                },
            )
            note.write_text(paused, encoding="utf-8")

            completed = self.invoke(
                vault,
                {
                    "path": str(path),
                    "expected_revision": "r9",
                    "gate": "G1",
                    "transition": "amend",
                    "verified": "Garo approved the amended G1 contract.",
                    "blockers": "none",
                    "decision": "Use explicit confirmation",
                    "next_action": "Activate amended G1.",
                    "repository": "branch feat/example",
                    "occurred_at": "2026-08-31T10:50:00Z",
                    "amendment": {
                        "approved_by": "Garo",
                        "decision_from": "Use suggestions",
                        "decision_to": "Use explicit confirmation",
                        "decision_rationale": "Prevents implicit creation.",
                        "gate_proves": "Confirmation creates exactly one campaign.",
                        "verifier_kind": "human",
                        "verifier_identity": "product owner",
                        "rationale": "The approved behavior now requires explicit confirmation.",
                    },
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(
                (result["revision"], result["gate_status"], result["lifecycle_status"]),
                ("r10", "pending", "approved"),
            )
            updated = note.read_text(encoding="utf-8")
            self.assertIn("| Use explicit confirmation | Prevents implicit creation. |", updated)
            self.assertNotIn("| Use suggestions |", updated)
            self.assertIn(
                "- **Proves:** Confirmation creates exactly one campaign.",
                updated,
            )
            self.assertIn("- **Verifier:** human — product owner", updated)
            self.assertIn("- **Status:** pending", updated)
            self.assertIn("- **Evidence:** none", updated)
            self.assertIn("2026-08-31 — G1 changed Use suggestions → Use explicit confirmation because The approved behavior now requires explicit confirmation.", updated)


    def test_human_gate_rejects_automated_acceptance_and_completes_on_human_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            active = (
                PRD.replace("status: approved", "status: active")
                .replace("revision: r1", "revision: r4")
                .replace("current_gate: null", "current_gate: G2")
            )
            active = set_gate_status(active, "G1", "passed")
            active = set_gate_status(active, "G2", "active")
            active = set_checkpoint(
                active,
                {
                    "Gate": "G2",
                    "Status": "active",
                    "Verified": "G1 accepted.",
                    "Blockers": "none",
                    "Decision": "unchanged",
                    "Next": "Verify G2.",
                    "Repository": "branch feat/example commit abc123",
                },
            )
            note.write_text(active, encoding="utf-8")
            request: dict[str, object] = {
                "path": str(path),
                "expected_revision": "r4",
                "gate": "G2",
                "transition": "pass",
                "verified": "Product owner accepted G2.",
                "blockers": "none",
                "decision": "unchanged",
                "next_action": "Assert merge readiness.",
                "repository": "branch feat/example commit abc123",
                "occurred_at": "2026-08-31T11:00:00Z",
                "verification": {
                    "kind": "automated",
                    "identity": "focused contract command",
                    "status": "accepted",
                },
            }

            refused = self.invoke(vault, request)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(json.loads(refused.stderr)["code"], "verification_mismatch")
            self.assertEqual(note.read_text(encoding="utf-8"), active)

            request["verification"] = {
                "kind": "human",
                "identity": "product owner",
                "status": "accepted",
            }
            passed = self.invoke(vault, request)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            result = json.loads(passed.stdout)
            self.assertEqual(
                (result["revision"], result["gate_status"], result["lifecycle_status"]),
                ("r5", "passed", "complete"),
            )


    def test_concurrent_transitions_commit_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            note.write_text(PRD, encoding="utf-8")
            request = {
                "path": str(path),
                "expected_revision": "r1",
                "gate": "G1",
                "transition": "activate",
                "verified": "Approval recorded.",
                "blockers": "none",
                "decision": "unchanged",
                "next_action": "Implement G1.",
                "repository": "branch feat/example",
                "occurred_at": "2026-08-31T11:10:00Z",
            }

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(
                    executor.map(lambda _: self.invoke(vault, request), range(2))
                )

            self.assertEqual(
                sorted(result.returncode == 0 for result in results),
                [False, True],
            )
            refusal = next(result for result in results if result.returncode != 0)
            self.assertEqual(json.loads(refusal.stderr)["code"], "revision_conflict")
            updated = note.read_text(encoding="utf-8")
            self.assertIn("revision: r2", updated)
            self.assertEqual(updated.count("- Status: active"), 1)
            self.assertEqual(updated.count("- **Status:** active"), 1)


    def test_yield_guard_refuses_stale_repository_until_checkpoint_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            active = (
                PRD.replace("status: approved", "status: active")
                .replace("revision: r1", "revision: r2")
                .replace("current_gate: null", "current_gate: G1")
            )
            active = set_gate_status(active, "G1", "active")
            active = set_checkpoint(
                active,
                {
                    "Gate": "G1",
                    "Status": "active",
                    "Verified": "Approval recorded.",
                    "Blockers": "none",
                    "Decision": "unchanged",
                    "Next": "Implement G1.",
                    "Repository": "repo-v1",
                },
            )
            note.write_text(active, encoding="utf-8")
            guard_request = {
                "path": str(path),
                "expected_revision": "r2",
                "gate": "G1",
                "repository": "repo-v2",
            }

            mutation = self.guard(vault, "source-mutation", guard_request)
            self.assertEqual(mutation.returncode, 0, mutation.stderr)

            stale_yield = self.guard(vault, "yield", guard_request)
            self.assertNotEqual(stale_yield.returncode, 0)
            self.assertEqual(json.loads(stale_yield.stderr)["code"], "stale_checkpoint")

            updated = self.invoke(
                vault,
                {
                    **guard_request,
                    "transition": "update",
                    "verified": "Repository fingerprint repo-v2 captured.",
                    "blockers": "none",
                    "decision": "unchanged",
                    "next_action": "Continue G1.",
                    "occurred_at": "2026-08-31T11:20:00Z",
                },
            )
            self.assertEqual(updated.returncode, 0, updated.stderr)

            fresh_yield = self.guard(
                vault,
                "yield",
                {**guard_request, "expected_revision": "r3"},
            )
            self.assertEqual(fresh_yield.returncode, 0, fresh_yield.stderr)
            result = json.loads(fresh_yield.stdout)
            self.assertEqual(result["action"], "yield")
            self.assertEqual(result["revision"], "r3")


    def test_terminal_guards_accept_complete_prd_after_repository_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            complete = (
                PRD.replace("status: approved", "status: complete")
                .replace("revision: r1", "revision: r5")
                .replace("current_gate: null", "current_gate: G2")
            )
            complete = set_gate_status(complete, "G1", "passed")
            complete = set_gate_status(complete, "G2", "passed")
            complete = set_checkpoint(
                complete,
                {
                    "Gate": "G2",
                    "Status": "passed",
                    "Verified": "All gates accepted.",
                    "Blockers": "none",
                    "Decision": "complete",
                    "Next": "Record or observe merge.",
                    "Repository": "PR #42 merge def456",
                },
            )
            note.write_text(complete, encoding="utf-8")
            request = {
                "path": str(path),
                "expected_revision": "r5",
                "gate": "G2",
                "repository": "git:changed-after-pass",
            }

            yielded = self.guard(vault, "yield", request)
            self.assertEqual(yielded.returncode, 0, yielded.stderr)
            completion = self.guard(vault, "completion", request)
            self.assertEqual(completion.returncode, 0, completion.stderr)

    def test_paused_current_gate_cannot_be_stranded_by_amending_future_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            paused = (
                PRD.replace("status: approved", "status: paused")
                .replace("revision: r1", "revision: r9")
                .replace("current_gate: null", "current_gate: G1")
            )
            paused = set_gate_status(paused, "G1", "active")
            paused = set_checkpoint(
                paused,
                {
                    "Gate": "G1",
                    "Status": "paused",
                    "Verified": "Existing verification.",
                    "Blockers": "none",
                    "Decision": "Use the existing seam.",
                    "Next": "Resume G1.",
                    "Repository": "branch feat/example",
                },
            )
            note.write_text(paused, encoding="utf-8")
            request = {
                "path": str(path),
                "expected_revision": "r9",
                "gate": "G2",
                "transition": "amend",
                "verified": "Future amendment proposed.",
                "blockers": "none",
                "decision": "Use another seam.",
                "next_action": "Resume G1.",
                "repository": "branch feat/example",
                "occurred_at": "2026-08-31T11:30:00Z",
                "amendment": {
                    "approved_by": "Garo",
                    "decision_from": "Use the existing seam.",
                    "decision_to": "Use another seam.",
                    "decision_rationale": "New evidence.",
                    "gate_proves": "Second behavior still works.",
                    "verifier_kind": "human",
                    "verifier_identity": "product owner",
                    "rationale": "Future scope changed.",
                },
            }

            refused = self.invoke(vault, request)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(json.loads(refused.stderr)["code"], "illegal_transition")
            self.assertEqual(note.read_text(encoding="utf-8"), paused)

    def test_amendment_preserves_literal_backslashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            approved = PRD.replace(
                "| Use the existing seam. | Avoid duplicate behavior. |",
                r"| Use C:\temp | Existing Windows path. |",
            )
            note.write_text(approved, encoding="utf-8")
            request = {
                "path": str(path),
                "expected_revision": "r1",
                "gate": "G1",
                "transition": "amend",
                "verified": "Amendment approved.",
                "blockers": "none",
                "decision": r"Use C:\new",
                "next_action": "Activate G1.",
                "repository": "branch feat/example",
                "occurred_at": "2026-08-31T11:35:00Z",
                "amendment": {
                    "approved_by": "Garo",
                    "decision_from": r"Use C:\temp",
                    "decision_to": r"Use C:\new",
                    "decision_rationale": r"Preserve C:\new literally.",
                    "gate_proves": "First behavior works.",
                    "verifier_kind": "automated",
                    "verifier_identity": "focused contract command",
                    "rationale": "The approved path changed.",
                },
            }

            completed = self.invoke(vault, request)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            updated = note.read_text(encoding="utf-8")
            self.assertIn(
                r"| Use C:\new | Preserve C:\new literally. |",
                updated,
            )
            self.assertIn(
                "G1 changed " + r"Use C:\temp → Use C:\new" + " because",
                updated,
            )

    def test_transition_ignores_gate_like_heading_outside_gates_section(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            path = Path("Example Initiative/PRD/example.md")
            note = vault / path
            note.parent.mkdir(parents=True)
            document = PRD.replace(
                "## Amendments\n- None.",
                "## Amendments\n### Rejected\n- Status: rejected",
            )
            note.write_text(document, encoding="utf-8")

            completed = self.invoke(
                vault,
                {
                    "path": str(path),
                    "expected_revision": "r1",
                    "gate": "G1",
                    "transition": "activate",
                    "verified": "Approval recorded.",
                    "blockers": "none",
                    "decision": "unchanged",
                    "next_action": "Implement G1.",
                    "repository": "branch feat/example",
                    "occurred_at": "2026-08-31T11:40:00Z",
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["revision"], "r2")

if __name__ == "__main__":
    unittest.main()
