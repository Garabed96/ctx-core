#!/usr/bin/env python3
"""Black-box validation and migration tests for the canonical v0.3.1 PRD protocol."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMMAND = REPO / "core" / "scripts" / "prd_checkpoint.py"
PRD_PATH = Path("Initiative Alpha/PRD/example.md")
G1_PLAN_PATH = Path("Initiative Alpha/Planning/example-g1-first-slice.md")
G2_PLAN_PATH = Path("Initiative Alpha/Planning/example-g2-second-slice.md")


def plan(gate: str, prd_path: Path, *, ui: bool = True) -> str:
    lane = (
        "UI owns presentation and must use the impeccable skill."
        if ui
        else "Not applicable"
    )
    return f"""---
title: Example {gate} plan
type: implementation-plan
status: planned
gate: {gate}
prd: "[[{prd_path.as_posix()}|Example PRD]]"
---

# Example {gate} plan

## Outcome
The gate outcome is implemented.

## Reuse decisions
- Reuse the existing service boundary.

## Gate-specific contract
- Preserve the existing public API.

## Implementation slice
1. Implement the observable gate behavior.

## Parallel execution contract
- **Backend/contracts/architecture owner:** Main owns contracts and architecture.
- **Independent UI or specialist lane:** {lane}
- **Shared integration owner:** Main integrates every lane.
- **File ownership and no-overlap constraints:** Each lane owns disjoint files.
- **Final integration and verification pass:** Main runs one final behavioral verification pass.

## Verification
- Exercise the observable gate behavior.

## Non-goals
- Unrelated product behavior.
"""


CANONICAL_PRD = f"""---
title: Example — PRD
type: ctx-prd
status: approved
revision: r1
current_gate: null
branch: feat/example
worktree: /tmp/example
approved_by: Product owner
approved_at: 2026-08-31T09:00:00Z
created: 2026-08-31
updated: 2026-08-31
---

# Example — PRD

## Outcome
An observable user result.

## Boundaries
- **In:** The requested behavior.
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
- Next: Activate G1.
- Repository: git:example

## Gates

### G1 — First slice
- **Proves:** First user-visible behavior works.
- **Feature list:**
  - Complete the first user-visible behavior.
- **Implementation plan:** [[{G1_PLAN_PATH.as_posix()}|G1 implementation plan]]
- **Verifier:** automated — focused contract command
- **Status:** pending
- **Evidence:** none

### G2 — Second slice
- **Proves:** Second user-visible behavior works.
- **Feature list:**
  - Complete the second user-visible behavior.
- **Implementation plan:** [[{G2_PLAN_PATH.as_posix()}|G2 implementation plan]]
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


LEGACY_PRD = f"""---
title: Example — PRD
type: ctx-prd
status: approved
revision: r1
current_gate: G1
branch: feat/example
worktree: /tmp/example
approved_by: Product owner
approved_at: 2026-08-31T09:00:00Z
created: 2026-08-31
updated: 2026-08-31
---

# Example — PRD

## Outcome
An observable user result.

## Current checkpoint
- Gate: G1
- Status: pending
- Verified: Existing verification remains.
- Decision: Existing decision remains.
- Next: Prepare G1.
- Repository: git:example

## Gates
### G1 — First slice
- Proves: First user-visible behavior works.
- Feature list:
  - Complete the first user-visible behavior.
- Verifier: automated — focused contract command
- Status: pending
- Evidence: Existing gate evidence remains.

## Boundaries
- **In:** The requested behavior.
- **Out:** Unrelated behavior.
- **Preserve:** Existing contracts.

## Decisions
| Decision | Rationale |
|---|---|
| Existing decision remains. | Existing rationale remains. |

## Approval
- [x] Approved for execution

## Amendments
- 2026-08-30 — Existing amendment remains exactly as accepted.
"""


class ProtocolCommandTest(unittest.TestCase):
    def invoke(
        self,
        vault: Path,
        request: dict[str, object],
        *args: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(COMMAND), "--vault-root", str(vault), *args],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            check=False,
        )

    def arrange(
        self,
        vault: Path,
        prd: str = CANONICAL_PRD,
        *,
        include_g1: bool = True,
        include_g2: bool = True,
    ) -> Path:
        note = vault / PRD_PATH
        note.parent.mkdir(parents=True)
        note.write_text(prd, encoding="utf-8")
        if include_g1:
            target = vault / G1_PLAN_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(plan("G1", PRD_PATH), encoding="utf-8")
        if include_g2:
            target = vault / G2_PLAN_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(plan("G2", PRD_PATH, ui=False), encoding="utf-8")
        return note

    def assert_error(
        self,
        result: subprocess.CompletedProcess[str],
        code: str,
        *messages: str,
    ) -> dict[str, object]:
        self.assertNotEqual(result.returncode, 0, result.stdout)
        error = json.loads(result.stderr)
        self.assertEqual(error["code"], code)
        for message in messages:
            self.assertIn(message, error["message"])
        return error

    def test_validates_canonical_prd_and_linked_plans(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault)
            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["revision"], "r1")
            self.assertEqual(payload["gates"], ["G1", "G2"])
            self.assertEqual(payload["plans"], [G1_PLAN_PATH.as_posix(), G2_PLAN_PATH.as_posix()])

    def test_rejects_misordered_prd_sections_with_document_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            malformed = CANONICAL_PRD.replace(
                "## Outcome\nAn observable user result.\n\n## Boundaries",
                "## Boundaries",
            ).replace(
                "- **Preserve:** Existing contracts.\n\n## Decisions",
                "- **Preserve:** Existing contracts.\n\n## Outcome\nAn observable user result.\n\n## Decisions",
            )
            self.arrange(vault, malformed)

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_prd", PRD_PATH.as_posix(), "Outcome", "Boundaries")

    def test_rejects_malformed_feature_list_and_obsolete_gate_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            malformed = CANONICAL_PRD.replace(
                "- **Feature list:**\n  - Complete the first user-visible behavior.",
                "- Feature list: Complete the first user-visible behavior.",
                1,
            )
            self.arrange(vault, malformed)

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_prd", "G1", "Feature list")

    def test_rejects_missing_plan_and_reports_expected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault, include_g1=False)

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "missing_plan", "G1", G1_PLAN_PATH.as_posix())

    def test_rejects_plan_without_backlink_or_required_section_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault)
            target = vault / G1_PLAN_PATH
            malformed = plan("G1", PRD_PATH).replace(
                f'prd: "[[{PRD_PATH.as_posix()}|Example PRD]]"',
                'prd: "[[Initiative Alpha/PRD/other.md|Other PRD]]"',
            ).replace(
                "## Parallel execution contract",
                "## Verification\n- Premature verification.\n\n## Parallel execution contract",
            )
            target.write_text(malformed, encoding="utf-8")

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_plan", G1_PLAN_PATH.as_posix(), PRD_PATH.as_posix())

    def test_rejects_model_specific_ui_lane_and_requires_impeccable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault)
            target = vault / G1_PLAN_PATH
            malformed = plan("G1", PRD_PATH).replace(
                "UI owns presentation and must use the impeccable skill.",
                "Run claude -p --model opus for presentation work.",
            )
            target.write_text(malformed, encoding="utf-8")

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_plan", G1_PLAN_PATH.as_posix(), "model-agnostic")

    def test_activation_refuses_when_linked_plan_becomes_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault, include_g1=False)
            request = {
                "path": PRD_PATH.as_posix(),
                "expected_revision": "r1",
                "gate": "G1",
                "transition": "activate",
                "verified": "Approval recorded.",
                "blockers": "none",
                "decision": "unchanged",
                "next_action": "Implement G1.",
                "repository": "git:example",
                "occurred_at": "2026-08-31T10:00:00Z",
            }

            result = self.invoke(vault, request)
            self.assert_error(result, "missing_plan", "G1", G1_PLAN_PATH.as_posix())

    def test_checkpoint_requires_blockers_and_preserves_additional_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            contextual = CANONICAL_PRD.replace(
                "- Repository: git:example",
                "- Repository: git:example\n- Product context: Preserve this accepted context.",
            )
            note = self.arrange(vault, contextual)
            request = {
                "path": PRD_PATH.as_posix(),
                "expected_revision": "r1",
                "gate": "G1",
                "transition": "activate",
                "verified": "Approval recorded.",
                "blockers": "none",
                "decision": "unchanged",
                "next_action": "Implement G1.",
                "repository": "git:changed",
                "occurred_at": "2026-08-31T10:00:00Z",
            }

            result = self.invoke(vault, request)
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = note.read_text(encoding="utf-8")
            self.assertIn("- Blockers: none", updated)
            self.assertIn("- Product context: Preserve this accepted context.", updated)

    def test_migrates_legacy_shape_without_inventing_historical_truth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            note = self.arrange(vault, LEGACY_PRD, include_g2=False)
            before_amendment = "- 2026-08-30 — Existing amendment remains exactly as accepted."
            result = self.invoke(
                vault,
                {
                    "path": PRD_PATH.as_posix(),
                    "expected_revision": "r1",
                    "occurred_at": "2026-08-31T10:00:00Z",
                },
                "--migrate",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["revision"], "r2")
            updated = note.read_text(encoding="utf-8")
            self.assertIn("current_gate: G1", updated)
            self.assertIn("- **Status:** pending", updated)
            self.assertIn("- **Evidence:** Existing gate evidence remains.", updated)
            self.assertIn(before_amendment, updated)
            self.assertIn(
                f"- **Implementation plan:** [[{G1_PLAN_PATH.as_posix().removesuffix('.md')}|G1 — First slice]]",
                updated,
            )
            self.assertIn("- Blockers: none", updated)

            validation = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assertEqual(validation.returncode, 0, validation.stderr)

    def test_migration_retains_unknown_sections_as_noncanonical_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            legacy = (
                LEGACY_PRD.replace(
                    "## Approval",
                    "## Historical notes\nDo not discard this old context.\n\n## Approval",
                )
                .replace(
                    "- Evidence: Existing gate evidence remains.",
                    "- Evidence: Existing gate evidence remains.\nLegacy gate context also remains.",
                )
            )
            note = self.arrange(vault, legacy, include_g2=False)

            result = self.invoke(
                vault,
                {
                    "path": PRD_PATH.as_posix(),
                    "expected_revision": "r1",
                    "occurred_at": "2026-08-31T10:00:00Z",
                },
                "--migrate",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            updated = note.read_text(encoding="utf-8")
            self.assertIn("### Retained historical content", updated)
            self.assertIn("    ## Historical notes", updated)
            self.assertIn("    Do not discard this old context.", updated)
            self.assertIn("    Legacy gate context also remains.", updated)
            top_level = [
                line.removeprefix("## ")
                for line in updated.splitlines()
                if line.startswith("## ")
            ]
            self.assertEqual(top_level, list((
                "Outcome",
                "Boundaries",
                "Decisions",
                "Current checkpoint",
                "Gates",
                "Approval",
                "Evidence",
                "Amendments",
            )))

    def test_obsolete_v030_shape_does_not_pass_canonical_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault, LEGACY_PRD, include_g2=False)

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_prd", PRD_PATH.as_posix(), "top-level sections")

    def test_migration_fails_actionably_when_expected_plan_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault, LEGACY_PRD, include_g1=False, include_g2=False)

            result = self.invoke(
                vault,
                {
                    "path": PRD_PATH.as_posix(),
                    "expected_revision": "r1",
                    "occurred_at": "2026-08-31T10:00:00Z",
                },
                "--migrate",
            )
            self.assert_error(result, "missing_plan", "G1", G1_PLAN_PATH.as_posix(), "create the plan")

    def test_migration_defaults_absent_decision_and_preserves_multiline_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            legacy = LEGACY_PRD.replace(
                "- Decision: Existing decision remains.\n",
                "",
            ).replace(
                "- Evidence: Existing gate evidence remains.",
                "- Evidence: Existing gate evidence remains.\n"
                "  - Browser trace remains attached.\n"
                "  - Contract log remains attached.",
            )
            note = self.arrange(vault, legacy, include_g2=False)

            result = self.invoke(
                vault,
                {
                    "path": PRD_PATH.as_posix(),
                    "expected_revision": "r1",
                    "occurred_at": "2026-08-31T10:00:00Z",
                },
                "--migrate",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            updated = note.read_text(encoding="utf-8")
            self.assertIn("- Decision: none", updated)
            self.assertIn(
                "- **Evidence:** Existing gate evidence remains.\n"
                "  - Browser trace remains attached.\n"
                "  - Contract log remains attached.",
                updated,
            )
            self.assertNotIn("    - Browser trace remains attached.", updated)

    def test_rejects_noncontiguous_or_misordered_gate_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            first = CANONICAL_PRD.index("### G1")
            second = CANONICAL_PRD.index("### G2")
            approval = CANONICAL_PRD.index("## Approval")
            misordered = (
                CANONICAL_PRD[:first]
                + CANONICAL_PRD[second:approval]
                + CANONICAL_PRD[first:second]
                + CANONICAL_PRD[approval:]
            )
            self.arrange(vault, misordered)

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_prd", "G1", "G2", "exact numeric order")

    def test_requires_updated_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            malformed = CANONICAL_PRD.replace("updated: 2026-08-31\n", "")
            self.arrange(vault, malformed)

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_prd", "updated")

    def test_resolves_unique_shortest_path_wikilinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            shortened = CANONICAL_PRD.replace(
                G1_PLAN_PATH.as_posix(),
                G1_PLAN_PATH.stem,
            ).replace(
                G2_PLAN_PATH.as_posix(),
                G2_PLAN_PATH.stem,
            )
            self.arrange(vault, shortened)
            for target in (vault / G1_PLAN_PATH, vault / G2_PLAN_PATH):
                target.write_text(
                    target.read_text(encoding="utf-8").replace(
                        PRD_PATH.as_posix(),
                        PRD_PATH.stem,
                    ),
                    encoding="utf-8",
                )

            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_model_instructions_anywhere_and_duplicate_parallel_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            self.arrange(vault)
            target = vault / G1_PLAN_PATH
            model_specific = target.read_text(encoding="utf-8").replace(
                "The gate outcome is implemented.",
                "Run claude -p --model opus before implementing the outcome.",
            )
            target.write_text(model_specific, encoding="utf-8")
            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_plan", "model-agnostic")

            duplicated = plan("G1", PRD_PATH).replace(
                "Each lane owns disjoint files.",
                "Main integrates every lane.",
            )
            target.write_text(duplicated, encoding="utf-8")
            result = self.invoke(vault, {"path": PRD_PATH.as_posix()}, "--validate")
            self.assert_error(result, "invalid_plan", "distinct responsibilities")

    def test_versioned_slug_uses_full_slug_as_plan_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = Path(temporary)
            versioned_prd = Path("Initiative Alpha/PRD/v2-redesign.md")
            versioned_plan = Path(
                "Initiative Alpha/Planning/v2-redesign-g1-first-slice.md"
            )
            g2_start = CANONICAL_PRD.index("### G2")
            approval = CANONICAL_PRD.index("## Approval")
            document = CANONICAL_PRD[:g2_start] + CANONICAL_PRD[approval:]
            document = document.replace(PRD_PATH.as_posix(), versioned_prd.as_posix())
            document = document.replace(G1_PLAN_PATH.as_posix(), versioned_plan.as_posix())
            note = vault / versioned_prd
            note.parent.mkdir(parents=True)
            note.write_text(document, encoding="utf-8")
            target = vault / versioned_plan
            target.parent.mkdir(parents=True)
            target.write_text(plan("G1", versioned_prd), encoding="utf-8")

            result = self.invoke(
                vault,
                {"path": versioned_prd.as_posix()},
                "--validate",
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
