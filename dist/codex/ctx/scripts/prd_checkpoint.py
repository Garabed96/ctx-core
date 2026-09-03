#!/usr/bin/env python3
"""Apply revision-safe lifecycle transitions to a canonical CTX PRD.

The command accepts one JSON request on stdin and emits one JSON attestation on
stdout. It is intentionally independent of product repositories and operates
only on the named note beneath ``--vault-root``.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from prd_document import (
    ProtocolError,
    gate_headings,
    migrate_prd,
    section_span as document_section_span,
    validate_prd,
)
import prd_arming

FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---(?P<tail>\n|\Z)", re.DOTALL)
REVISION = re.compile(r"r(?P<number>[1-9]\d*)\Z")
FIELD_LINE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?P<space>\s*)(?P<value>.*)$")
LIFECYCLE_STATUSES = {
    "draft",
    "approved",
    "active",
    "paused",
    "blocked",
    "complete",
    "abandoned",
}
GATE_STATUSES = {"pending", "active", "passed", "failed", "blocked"}


class CheckpointError(Exception):
    """A typed refusal safe to return to an automated caller."""

    def __init__(self, code: str, message: str, *, current_revision: str | None = None):
        super().__init__(message)
        self.code = code
        self.current_revision = current_revision


def _reject_unexpected_keys(
    value: dict[str, Any],
    allowed: set[str],
    label: str,
) -> None:
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise CheckpointError(
            "invalid_request",
            f"{label} contains unexpected fields: " + ", ".join(unexpected),
        )


def _require_single_line(fields: dict[str, str], label: str) -> None:
    invalid = [key for key, value in fields.items() if "\n" in value or "\r" in value]
    if invalid:
        raise CheckpointError(
            "invalid_request",
            f"{label} fields must be single-line: " + ", ".join(invalid),
        )


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CheckpointError(
            "invalid_request",
            "occurred_at must be an ISO-8601 timestamp",
        ) from error
    if parsed.tzinfo is None:
        raise CheckpointError(
            "invalid_request",
            "occurred_at must include a timezone",
        )

@dataclass(frozen=True)
class Verification:
    kind: str
    identity: str
    status: str

    @classmethod
    def from_json(cls, value: Any) -> "Verification | None":
        if value is None:
            return None
        if not isinstance(value, dict):
            raise CheckpointError("invalid_request", "verification must be a JSON object")
        required = ("kind", "identity", "status")
        _reject_unexpected_keys(value, set(required), "verification")
        missing = [
            key
            for key in required
            if not isinstance(value.get(key), str) or not value[key].strip()
        ]
        if missing:
            raise CheckpointError(
                "invalid_request",
                "verification is missing: " + ", ".join(missing),
            )
        verification = cls(**{key: value[key].strip() for key in required})
        _require_single_line(
            {
                "kind": verification.kind,
                "identity": verification.identity,
                "status": verification.status,
            },
            "verification",
        )
        if verification.kind not in {"automated", "human"}:
            raise CheckpointError(
                "invalid_request",
                "verification.kind must be automated or human",
            )
        if verification.status not in {"accepted", "rejected"}:
            raise CheckpointError(
                "invalid_request",
                "verification.status must be accepted or rejected",
            )
        return verification


@dataclass(frozen=True)
class Amendment:
    approved_by: str
    decision_from: str
    decision_to: str
    decision_rationale: str
    gate_proves: str
    verifier_kind: str
    verifier_identity: str
    rationale: str

    @classmethod
    def from_json(cls, value: Any) -> "Amendment | None":
        if value is None:
            return None
        if not isinstance(value, dict):
            raise CheckpointError("invalid_request", "amendment must be a JSON object")
        required = (
            "approved_by",
            "decision_from",
            "decision_to",
            "decision_rationale",
            "gate_proves",
            "verifier_kind",
            "verifier_identity",
            "rationale",
        )
        _reject_unexpected_keys(value, set(required), "amendment")
        missing = [
            key
            for key in required
            if not isinstance(value.get(key), str) or not value[key].strip()
        ]
        if missing:
            raise CheckpointError(
                "invalid_request",
                "amendment is missing: " + ", ".join(missing),
            )
        amendment = cls(**{key: value[key].strip() for key in required})
        if amendment.verifier_kind not in {"automated", "human"}:
            raise CheckpointError(
                "invalid_request",
                "amendment.verifier_kind must be automated or human",
            )
        if any(
            "|" in field or "\n" in field
            for field in (
                amendment.decision_from,
                amendment.decision_to,
                amendment.decision_rationale,
            )
        ):
            raise CheckpointError(
                "invalid_request",
                "amendment decision fields cannot contain table delimiters or newlines",
            )
        if any(
            "\n" in field
            for field in (
                amendment.approved_by,
                amendment.gate_proves,
                amendment.verifier_identity,
                amendment.rationale,
            )
        ):
            raise CheckpointError(
                "invalid_request",
                "amendment fields cannot contain newlines",
            )
        return amendment


@dataclass(frozen=True)
class Request:
    path: str
    expected_revision: str
    gate: str
    transition: str
    verified: str
    blockers: str
    decision: str
    next_action: str
    repository: str
    occurred_at: str
    verification: Verification | None
    merge_assertion: str | None
    amendment: Amendment | None

    @classmethod
    def from_json(cls, value: Any) -> "Request":
        if not isinstance(value, dict):
            raise CheckpointError("invalid_request", "request must be a JSON object")
        required = (
            "path",
            "expected_revision",
            "gate",
            "transition",
            "verified",
            "blockers",
            "decision",
            "next_action",
            "repository",
            "occurred_at",
        )
        _reject_unexpected_keys(
            value,
            set(required) | {"verification", "merge_assertion", "amendment"},
            "request",
        )
        missing = [key for key in required if not isinstance(value.get(key), str) or not value[key].strip()]
        if missing:
            raise CheckpointError(
                "invalid_request",
                "missing non-empty string fields: " + ", ".join(missing),
            )
        merge_assertion = value.get("merge_assertion")
        if merge_assertion is not None and (
            not isinstance(merge_assertion, str) or not merge_assertion.strip()
        ):
            raise CheckpointError(
                "invalid_request",
                "merge_assertion must be a non-empty string",
            )
        request = cls(
            **{key: value[key].strip() for key in required},
            verification=Verification.from_json(value.get("verification")),
            merge_assertion=merge_assertion.strip() if merge_assertion else None,
            amendment=Amendment.from_json(value.get("amendment")),
        )
        _require_single_line(
            {key: getattr(request, key) for key in required},
            "request",
        )
        if not REVISION.fullmatch(request.expected_revision):
            raise CheckpointError("invalid_request", "expected_revision must match r<N>")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", request.gate):
            raise CheckpointError("invalid_request", "gate must be a stable identifier such as G1")
        _validate_timestamp(request.occurred_at)
        return request


@dataclass(frozen=True)
class GuardRequest:
    path: str
    expected_revision: str
    gate: str
    repository: str

    @classmethod
    def from_json(cls, value: Any) -> "GuardRequest":
        if not isinstance(value, dict):
            raise CheckpointError("invalid_request", "guard request must be a JSON object")
        required = ("path", "expected_revision", "gate", "repository")
        _reject_unexpected_keys(value, set(required), "guard request")
        missing = [
            key
            for key in required
            if not isinstance(value.get(key), str) or not value[key].strip()
        ]
        if missing:
            raise CheckpointError(
                "invalid_request",
                "guard request is missing: " + ", ".join(missing),
            )
        request = cls(**{key: value[key].strip() for key in required})
        _require_single_line(
            {key: getattr(request, key) for key in required},
            "guard request",
        )
        if not REVISION.fullmatch(request.expected_revision):
            raise CheckpointError("invalid_request", "expected_revision must match r<N>")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", request.gate):
            raise CheckpointError("invalid_request", "gate must be a stable identifier such as G1")
        return request


@dataclass(frozen=True)
class Frontmatter:
    values: dict[str, str]

    @classmethod
    def parse(cls, text: str) -> "Frontmatter":
        match = FRONTMATTER.match(text)
        if not match:
            raise CheckpointError("invalid_prd", "canonical PRD requires YAML frontmatter")
        values: dict[str, str] = {}
        for line in match.group("body").splitlines():
            field = FIELD_LINE.match(line)
            if field:
                values[field.group("key")] = field.group("value").strip()
        required = ("type", "status", "revision", "current_gate", "updated")
        missing = [key for key in required if key not in values]
        if missing:
            raise CheckpointError("invalid_prd", "frontmatter is missing: " + ", ".join(missing))
        if _scalar(values["type"]) != "ctx-prd":
            raise CheckpointError("invalid_prd", "note type must be ctx-prd")
        if _scalar(values["status"]) not in LIFECYCLE_STATUSES:
            raise CheckpointError("invalid_prd", "frontmatter contains an invalid status")
        if not REVISION.fullmatch(_scalar(values["revision"]) or ""):
            raise CheckpointError("invalid_prd", "revision must match r<N>")
        return cls(values)

    def scalar(self, key: str) -> str | None:
        return _scalar(self.values.get(key, ""))


def _scalar(value: str) -> str | None:
    value = value.strip()
    if value in {"", "null", "~"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _replace_frontmatter(text: str, updates: dict[str, str]) -> str:
    match = FRONTMATTER.match(text)
    if not match:
        raise CheckpointError("invalid_prd", "canonical PRD requires YAML frontmatter")
    remaining = dict(updates)
    lines: list[str] = []
    for line in match.group("body").splitlines():
        field = FIELD_LINE.match(line)
        if field and field.group("key") in remaining:
            key = field.group("key")
            lines.append(f"{key}: {remaining.pop(key)}")
        else:
            lines.append(line)
    if remaining:
        raise CheckpointError(
            "invalid_prd",
            "frontmatter is missing writable fields: " + ", ".join(sorted(remaining)),
        )
    replacement = "---\n" + "\n".join(lines) + "\n---" + match.group("tail")
    return replacement + text[match.end() :]


def _section_span(text: str, heading: str, _next_heading_prefix: str) -> tuple[int, int]:
    try:
        return document_section_span(text, heading.removeprefix("## ").strip())
    except ProtocolError as error:
        raise CheckpointError(error.code, str(error)) from error


def _gate_span(text: str, gate: str) -> tuple[int, int]:
    try:
        headings = gate_headings(text)
    except ProtocolError as error:
        raise CheckpointError(error.code, str(error)) from error
    for heading in headings:
        match = re.fullmatch(r"(G[1-9]\d*)(?:\s+—\s+.+)?", heading.title)
        if match and match.group(1) == gate:
            return heading.start, heading.end
    raise CheckpointError("unknown_gate", f"gate not found: {gate}")


def _list_field(section: str, field: str) -> str:
    match = re.search(
        rf"^(?P<label>- (?:\*\*)?{re.escape(field)}:(?:\*\*)?)\s*(?P<value>.*)$",
        section,
        re.MULTILINE,
    )
    if not match:
        raise CheckpointError("invalid_prd", f"section is missing field: {field}")
    return match.group("value").strip()


def _replace_list_field(section: str, field: str, value: str) -> str:
    pattern = re.compile(
        rf"^(?P<label>- (?:\*\*)?{re.escape(field)}:(?:\*\*)?)\s*.*$",
        re.MULTILINE,
    )
    if not pattern.search(section):
        raise CheckpointError("invalid_prd", f"section is missing field: {field}")
    return pattern.sub(lambda match: f"{match.group('label')} {value}", section, count=1)


def _revision_after(revision: str) -> str:
    match = REVISION.fullmatch(revision)
    if not match:
        raise CheckpointError("invalid_prd", "revision must match r<N>")
    return f"r{int(match.group('number')) + 1}"


def _replace_checkpoint(text: str, request: Request, status: str) -> str:
    start, end = _section_span(text, "## Current checkpoint", "## ")
    checkpoint = text[start:end]
    updates = {
        "Gate": request.gate,
        "Status": status,
        "Verified": request.verified,
        "Blockers": request.blockers,
        "Decision": request.decision,
        "Next": request.next_action,
        "Repository": request.repository,
    }
    for field, value in updates.items():
        checkpoint = _replace_list_field(checkpoint, field, value)
    return text[:start] + checkpoint + text[end:]


def _gate_statuses(text: str) -> list[tuple[str, str]]:
    statuses: list[tuple[str, str]] = []
    try:
        headings = gate_headings(text)
    except ProtocolError as error:
        raise CheckpointError(error.code, str(error)) from error
    for heading in headings:
        parsed = re.fullmatch(r"(G[1-9]\d*)(?:\s+—\s+.+)?", heading.title)
        if not parsed:
            raise CheckpointError("invalid_prd", f"invalid gate heading: {heading.title}")
        gate = parsed.group(1)
        status = _list_field(text[heading.start:heading.end], "Status")
        if status not in GATE_STATUSES:
            raise CheckpointError(
                "invalid_prd",
                f"gate {gate} contains an invalid status: {status}",
            )
        statuses.append((gate, status))
    if not statuses:
        raise CheckpointError("invalid_prd", "PRD contains no gates")
    return statuses


def _validate_verification(gate_section: str, request: Request) -> None:
    verification = request.verification
    if not verification or verification.status != "accepted":
        raise CheckpointError(
            "verification_required",
            "pass requires an accepted verification attestation",
        )
    verifier = _list_field(gate_section, "Verifier")
    match = re.fullmatch(r"(automated|human)\s+—\s+(.+)", verifier)
    if not match:
        raise CheckpointError(
            "invalid_prd",
            "Verifier must use '<automated|human> — <identity>'",
        )
    expected_kind, expected_identity = match.groups()
    if verification.kind != expected_kind or verification.identity != expected_identity:
        raise CheckpointError(
            "verification_mismatch",
            f"expected {expected_kind} — {expected_identity}",
        )


def _validate_approval(text: str, frontmatter: Frontmatter) -> None:
    if not frontmatter.scalar("approved_by") or not frontmatter.scalar("approved_at"):
        raise CheckpointError("unauthorized", "activation requires approved_by and approved_at")
    if not re.search(r"^- \[[xX]\] Approved for execution\s*$", text, re.MULTILINE):
        raise CheckpointError("unauthorized", "activation requires checked execution approval")


def _activate(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    if frontmatter.scalar("status") not in {"approved", "active"}:
        raise CheckpointError("illegal_transition", "activate requires an approved or active PRD")
    _validate_approval(text, frontmatter)

    gate_start, gate_end = _gate_span(text, request.gate)
    gate_section = text[gate_start:gate_end]
    if _list_field(gate_section, "Status") != "pending":
        raise CheckpointError("illegal_transition", "activate requires a pending gate")
    statuses = _gate_statuses(text)
    target_index = next(
        index for index, (gate, _) in enumerate(statuses) if gate == request.gate
    )
    incomplete_predecessors = [
        gate for gate, status in statuses[:target_index] if status != "passed"
    ]
    if incomplete_predecessors:
        raise CheckpointError(
            "illegal_transition",
            "earlier gates have not passed: " + ", ".join(incomplete_predecessors),
        )

    active_gates = [gate for gate, status in statuses if status == "active"]
    if active_gates:
        raise CheckpointError("illegal_transition", "another gate is already active: " + ", ".join(active_gates))

    gate_section = _replace_list_field(gate_section, "Status", "active")
    text = text[:gate_start] + gate_section + text[gate_end:]

    text = _replace_checkpoint(text, request, "active")

    revision = _revision_after(frontmatter.scalar("revision") or "")
    text = _replace_frontmatter(
        text,
        {
            "status": "active",
            "revision": revision,
            "current_gate": request.gate,
            "updated": request.occurred_at[:10],
        },
    )
    return text, revision, "active"


def _assert_active(
    text: str,
    request: Request,
    frontmatter: Frontmatter,
) -> tuple[str, str, str]:
    if frontmatter.scalar("status") != "active":
        raise CheckpointError("inactive_gate", "assert-active requires an active PRD")
    if frontmatter.scalar("current_gate") != request.gate:
        raise CheckpointError(
            "inactive_gate",
            f"current gate is {frontmatter.scalar('current_gate') or 'null'}, not {request.gate}",
        )
    gate_start, gate_end = _gate_span(text, request.gate)
    gate_status = _list_field(text[gate_start:gate_end], "Status")
    if gate_status != "active":
        raise CheckpointError(
            "inactive_gate",
            f"gate {request.gate} is {gate_status}, not active",
        )
    return text, frontmatter.scalar("revision") or "", gate_status

def _current_gate(
    text: str,
    request: Request,
    frontmatter: Frontmatter,
) -> tuple[int, int, str, str]:
    if frontmatter.scalar("current_gate") != request.gate:
        raise CheckpointError(
            "illegal_transition",
            f"current gate is {frontmatter.scalar('current_gate') or 'null'}, not {request.gate}",
        )
    start, end = _gate_span(text, request.gate)
    section = text[start:end]
    return start, end, section, _list_field(section, "Status")


def _apply_gate_transition(
    text: str,
    request: Request,
    frontmatter: Frontmatter,
    *,
    gate_status: str,
    lifecycle_status: str,
    checkpoint_status: str | None = None,
    replace_evidence: bool = True,
) -> tuple[str, str, str]:
    start, end, section, _ = _current_gate(text, request, frontmatter)
    section = _replace_list_field(section, "Status", gate_status)
    if replace_evidence:
        section = _replace_list_field(section, "Evidence", request.verified)
    text = text[:start] + section + text[end:]
    text = _replace_checkpoint(text, request, checkpoint_status or gate_status)
    revision = _revision_after(frontmatter.scalar("revision") or "")
    text = _replace_frontmatter(
        text,
        {
            "status": lifecycle_status,
            "revision": revision,
            "current_gate": request.gate,
            "updated": request.occurred_at[:10],
        },
    )
    return text, revision, gate_status


def _block(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    _, _, _, gate_status = _current_gate(text, request, frontmatter)
    if frontmatter.scalar("status") != "active" or gate_status != "active":
        raise CheckpointError("illegal_transition", "block requires an active gate")
    return _apply_gate_transition(
        text,
        request,
        frontmatter,
        gate_status="blocked",
        lifecycle_status="blocked",
    )


def _resume(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    _, _, _, gate_status = _current_gate(text, request, frontmatter)
    lifecycle_status = frontmatter.scalar("status")
    resumable = (
        lifecycle_status == "blocked" and gate_status == "blocked"
    ) or (
        lifecycle_status == "paused" and gate_status in {"active", "blocked"}
    )
    if not resumable:
        raise CheckpointError(
            "illegal_transition",
            "resume requires a blocked gate or paused lifecycle",
        )
    return _apply_gate_transition(
        text,
        request,
        frontmatter,
        gate_status="active",
        lifecycle_status="active",
    )


def _fail(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    _, _, section, gate_status = _current_gate(text, request, frontmatter)
    if frontmatter.scalar("status") != "active" or gate_status != "active":
        raise CheckpointError("illegal_transition", "fail requires an active gate")
    if request.verification:
        if request.verification.status != "rejected":
            raise CheckpointError(
                "verification_mismatch",
                "fail requires rejected verification when an attestation is supplied",
            )
        verifier = _list_field(section, "Verifier")
        match = re.fullmatch(r"(automated|human)\s+—\s+(.+)", verifier)
        if not match or (
            request.verification.kind,
            request.verification.identity,
        ) != match.groups():
            raise CheckpointError("verification_mismatch", f"expected {verifier}")
    return _apply_gate_transition(
        text,
        request,
        frontmatter,
        gate_status="failed",
        lifecycle_status="blocked",
    )


def _retry(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    _, _, _, gate_status = _current_gate(text, request, frontmatter)
    if frontmatter.scalar("status") != "blocked" or gate_status != "failed":
        raise CheckpointError("illegal_transition", "retry requires a failed gate")
    return _apply_gate_transition(
        text,
        request,
        frontmatter,
        gate_status="active",
        lifecycle_status="active",
    )


def _pause(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    _, _, _, gate_status = _current_gate(text, request, frontmatter)
    if frontmatter.scalar("status") not in {"active", "blocked"} or gate_status not in {
        "active",
        "blocked",
    }:
        raise CheckpointError(
            "illegal_transition",
            "pause requires an active or blocked gate",
        )
    return _apply_gate_transition(
        text,
        request,
        frontmatter,
        gate_status=gate_status,
        lifecycle_status="paused",
        checkpoint_status="paused",
        replace_evidence=False,
    )


def _update(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    _, _, _, gate_status = _current_gate(text, request, frontmatter)
    lifecycle_status = frontmatter.scalar("status") or ""
    if lifecycle_status not in {"active", "blocked"} or gate_status not in {
        "active",
        "blocked",
    }:
        raise CheckpointError(
            "illegal_transition",
            "update requires an active or blocked gate",
        )
    return _apply_gate_transition(
        text,
        request,
        frontmatter,
        gate_status=gate_status,
        lifecycle_status=lifecycle_status,
    )


def _pass(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    if frontmatter.scalar("status") != "active":
        raise CheckpointError("illegal_transition", "pass requires an active PRD")
    if frontmatter.scalar("current_gate") != request.gate:
        raise CheckpointError("illegal_transition", "pass requires the current gate")
    gate_start, gate_end = _gate_span(text, request.gate)
    gate_section = text[gate_start:gate_end]
    if _list_field(gate_section, "Status") != "active":
        raise CheckpointError("illegal_transition", "pass requires an active gate")
    _validate_verification(gate_section, request)

    gate_section = _replace_list_field(gate_section, "Status", "passed")
    gate_section = _replace_list_field(gate_section, "Evidence", request.verified)
    text = text[:gate_start] + gate_section + text[gate_end:]
    text = _replace_checkpoint(text, request, "passed")

    lifecycle_status = (
        "complete"
        if all(status == "passed" for _, status in _gate_statuses(text))
        else "active"
    )
    revision = _revision_after(frontmatter.scalar("revision") or "")
    text = _replace_frontmatter(
        text,
        {
            "status": lifecycle_status,
            "revision": revision,
            "current_gate": request.gate,
            "updated": request.occurred_at[:10],
        },
    )
    return text, revision, "passed"


def _replace_decision(text: str, amendment: Amendment) -> str:
    pattern = re.compile(
        rf"^\|\s*{re.escape(amendment.decision_from)}\s*\|\s*[^|\n]+\|\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise CheckpointError(
            "amendment_mismatch",
            f"expected exactly one decision row for: {amendment.decision_from}",
        )
    replacement = (
        f"| {amendment.decision_to} | {amendment.decision_rationale} |"
    )
    return pattern.sub(lambda _match: replacement, text, count=1)


def _append_amendment(text: str, request: Request, amendment: Amendment) -> str:
    start, end = _section_span(text, "## Amendments", "## ")
    section = text[start:end].rstrip()
    entry = (
        f"{request.occurred_at[:10]} — {request.gate} changed "
        f"{amendment.decision_from} → {amendment.decision_to} because "
        f"{amendment.rationale}"
    )
    if re.search(r"^- None\.\s*$", section, re.MULTILINE):
        section = re.sub(
            r"^- None\.\s*$",
            lambda _match: f"- {entry}",
            section,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        section += f"\n- {entry}"
    return text[:start] + section + "\n" + text[end:]


def _amend(text: str, request: Request, frontmatter: Frontmatter) -> tuple[str, str, str]:
    amendment = request.amendment
    if not amendment:
        raise CheckpointError("invalid_request", "amend requires amendment details")
    if request.decision != amendment.decision_to:
        raise CheckpointError(
            "amendment_mismatch",
            "request decision must equal amendment.decision_to",
        )
    gate_start, gate_end = _gate_span(text, request.gate)
    gate_section = text[gate_start:gate_end]
    gate_status = _list_field(gate_section, "Status")
    lifecycle_status = frontmatter.scalar("status")
    if lifecycle_status == "paused":
        if frontmatter.scalar("current_gate") != request.gate:
            raise CheckpointError(
                "illegal_transition",
                "a paused lifecycle may amend only its current gate",
            )
        if gate_status not in {"active", "blocked", "failed"}:
            raise CheckpointError(
                "illegal_transition",
                "a paused lifecycle requires an active, blocked, or failed current gate",
            )
    elif lifecycle_status == "approved":
        if gate_status != "pending":
            raise CheckpointError(
                "illegal_transition",
                "an approved lifecycle may amend only a pending gate",
            )
    else:
        raise CheckpointError(
            "illegal_transition",
            "amend requires an approved or paused PRD",
        )

    text = _replace_decision(text, amendment)
    gate_start, gate_end = _gate_span(text, request.gate)
    gate_section = text[gate_start:gate_end]
    gate_section = _replace_list_field(
        gate_section,
        "Proves",
        amendment.gate_proves,
    )
    gate_section = _replace_list_field(
        gate_section,
        "Verifier",
        f"{amendment.verifier_kind} — {amendment.verifier_identity}",
    )
    gate_section = _replace_list_field(gate_section, "Status", "pending")
    gate_section = _replace_list_field(gate_section, "Evidence", "none")
    text = text[:gate_start] + gate_section + text[gate_end:]
    text = _append_amendment(text, request, amendment)
    text = _replace_checkpoint(text, request, "pending")

    revision = _revision_after(frontmatter.scalar("revision") or "")
    text = _replace_frontmatter(
        text,
        {
            "status": "approved",
            "revision": revision,
            "current_gate": request.gate,
            "updated": request.occurred_at[:10],
        },
    )
    return text, revision, "pending"


def _checkpoint_fields(text: str) -> dict[str, str]:
    start, end = _section_span(text, "## Current checkpoint", "## ")
    section = text[start:end]
    return {
        field: _list_field(section, field)
        for field in (
            "Gate",
            "Status",
            "Verified",
            "Blockers",
            "Decision",
            "Next",
            "Repository",
        )
    }


def _merge_assertion(text: str, request: Request) -> str:
    payload = {
        "attestation": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "gate": request.gate,
        "path": request.path,
        "revision": request.expected_revision,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _assert_merge(
    text: str,
    request: Request,
    frontmatter: Frontmatter,
) -> tuple[str, str, str]:
    _, _, _, gate_status = _current_gate(text, request, frontmatter)
    if gate_status != "passed":
        raise CheckpointError("merge_blocked", "assert-merge requires a passed gate")
    checkpoint = _checkpoint_fields(text)
    if checkpoint["Gate"] != request.gate or checkpoint["Status"] != "passed":
        raise CheckpointError(
            "merge_blocked",
            "current checkpoint does not attest the passed gate",
        )
    if checkpoint["Repository"] != request.repository:
        raise CheckpointError(
            "repository_mismatch",
            f"expected repository evidence: {checkpoint['Repository']}",
        )
    return text, frontmatter.scalar("revision") or "", gate_status


def _record_merge(
    text: str,
    request: Request,
    frontmatter: Frontmatter,
) -> tuple[str, str, str]:
    _, _, _, gate_status = _current_gate(text, request, frontmatter)
    if gate_status != "passed":
        raise CheckpointError("merge_blocked", "record-merge requires a passed gate")
    expected_assertion = _merge_assertion(text, request)
    if request.merge_assertion != expected_assertion:
        raise CheckpointError(
            "merge_assertion_required",
            "record-merge requires assert-merge from the same revision",
        )
    text = _replace_checkpoint(text, request, "passed")
    revision = _revision_after(frontmatter.scalar("revision") or "")
    text = _replace_frontmatter(
        text,
        {
            "status": frontmatter.scalar("status") or "",
            "revision": revision,
            "current_gate": request.gate,
            "updated": request.occurred_at[:10],
        },
    )
    return text, revision, gate_status


TRANSITIONS: dict[str, Callable[[str, Request, Frontmatter], tuple[str, str, str]]] = {
    "activate": _activate,
    "amend": _amend,
    "assert-active": _assert_active,
    "assert-merge": _assert_merge,
    "block": _block,
    "fail": _fail,
    "pass": _pass,
    "pause": _pause,
    "record-merge": _record_merge,
    "resume": _resume,
    "retry": _retry,
    "update": _update,
}


def _validate_document(vault_root: Path, relative_path: str, text: str):
    try:
        return validate_prd(vault_root, relative_path, text)
    except ProtocolError as error:
        raise CheckpointError(error.code, str(error)) from error


def transition_document(
    text: str,
    request: Request,
    vault_root: Path,
) -> tuple[str, dict[str, str]]:
    _validate_document(vault_root, request.path, text)
    frontmatter = Frontmatter.parse(text)
    revision = frontmatter.scalar("revision") or ""
    if revision != request.expected_revision:
        raise CheckpointError(
            "revision_conflict",
            f"expected {request.expected_revision}, found {revision}",
            current_revision=revision,
        )
    transition = TRANSITIONS.get(request.transition)
    if not transition:
        raise CheckpointError("invalid_request", f"unsupported transition: {request.transition}")

    updated, new_revision, gate_status = transition(text, request, frontmatter)
    _validate_document(vault_root, request.path, updated)
    lifecycle_status = Frontmatter.parse(updated).scalar("status") or ""
    attestation = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    result = {
        "attestation": attestation,
        "current_gate": request.gate,
        "gate_status": gate_status,
        "lifecycle_status": lifecycle_status,
        "path": request.path,
        "revision": new_revision,
        "transition": request.transition,
    }
    if request.transition == "assert-merge":
        result["merge_assertion"] = _merge_assertion(text, request)
    return updated, result


def guard_document(
    text: str,
    request: GuardRequest,
    action: str,
    vault_root: Path,
) -> dict[str, str]:
    _validate_document(vault_root, request.path, text)
    frontmatter = Frontmatter.parse(text)
    revision = frontmatter.scalar("revision") or ""
    if revision != request.expected_revision:
        raise CheckpointError(
            "revision_conflict",
            f"expected {request.expected_revision}, found {revision}",
            current_revision=revision,
        )
    if frontmatter.scalar("current_gate") != request.gate:
        raise CheckpointError(
            "guard_refused",
            f"current gate is {frontmatter.scalar('current_gate') or 'null'}, not {request.gate}",
        )
    gate_start, gate_end = _gate_span(text, request.gate)
    gate_status = _list_field(text[gate_start:gate_end], "Status")
    lifecycle_status = frontmatter.scalar("status") or ""

    if action == "source-mutation":
        if lifecycle_status != "active" or gate_status != "active":
            raise CheckpointError(
                "guard_refused",
                "source mutation requires an attested active gate",
            )
    else:
        checkpoint = _checkpoint_fields(text)
        if checkpoint["Gate"] != request.gate:
            raise CheckpointError(
                "stale_checkpoint",
                "current checkpoint belongs to a different gate",
            )
        complete = (
            lifecycle_status == "complete"
            and gate_status == "passed"
            and checkpoint["Status"] == "passed"
            and all(status == "passed" for _, status in _gate_statuses(text))
        )
        if action == "completion":
            if not complete:
                raise CheckpointError(
                    "guard_refused",
                    "completion requires every gate to be passed",
                )
        elif action == "yield" and complete:
            pass
        else:
            if checkpoint["Repository"] != request.repository:
                raise CheckpointError(
                    "stale_checkpoint",
                    "repository fingerprint differs from the current checkpoint",
                )
            if action == "next-gate" and (
                gate_status != "passed" or checkpoint["Status"] != "passed"
            ):
                raise CheckpointError(
                    "guard_refused",
                    "next-gate requires a passed current gate",
                )

    return {
        "action": action,
        "attestation": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "current_gate": request.gate,
        "gate_status": gate_status,
        "lifecycle_status": lifecycle_status,
        "path": request.path,
        "revision": revision,
    }


def _resolve_note(vault_root: Path, relative_path: str) -> Path:
    if Path(relative_path).is_absolute():
        raise CheckpointError("invalid_request", "path must be relative to --vault-root")
    root = vault_root.resolve()
    note = (root / relative_path).resolve()
    if not note.is_relative_to(root):
        raise CheckpointError("invalid_request", "path escapes --vault-root")
    if not note.is_file():
        raise CheckpointError("not_found", f"PRD not found: {relative_path}")
    return note


def _atomic_replace(note: Path, content: str) -> None:
    mode = stat.S_IMODE(note.stat().st_mode)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=note.parent,
            prefix=f".{note.name}.",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.chmod(temporary, mode)
        os.replace(temporary, note)
        directory = os.open(note.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _atomic_transition(vault_root: Path, request: Request) -> dict[str, str]:
    note = _resolve_note(vault_root, request.path)
    with _lock_path(note).open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original_stat = note.stat()
        original = note.read_text(encoding="utf-8")
        updated, result = transition_document(original, request, vault_root)
        if updated != original:
            current_stat = note.stat()
            if (
                current_stat.st_ino,
                current_stat.st_mtime_ns,
                current_stat.st_size,
            ) != (
                original_stat.st_ino,
                original_stat.st_mtime_ns,
                original_stat.st_size,
            ):
                raise CheckpointError(
                    "external_write_conflict",
                    "canonical PRD changed outside the checkpoint lock",
                )
            _atomic_replace(note, updated)

        observed = note.read_text(encoding="utf-8")
        observed_hash = hashlib.sha256(observed.encode("utf-8")).hexdigest()
        if observed_hash != result["attestation"]:
            raise CheckpointError("attestation_failed", "post-write PRD attestation failed")
        return result


def _validation_path(value: Any) -> str:
    if not isinstance(value, dict):
        raise CheckpointError("invalid_request", "validation request must be a JSON object")
    _reject_unexpected_keys(value, {"path"}, "validation request")
    path = value.get("path")
    if not isinstance(path, str) or not path.strip():
        raise CheckpointError("invalid_request", "validation request requires path")
    return path.strip()


def _migration_request(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, dict):
        raise CheckpointError("invalid_request", "migration request must be a JSON object")
    required = {"path", "expected_revision", "occurred_at"}
    _reject_unexpected_keys(value, required, "migration request")
    missing = [
        name
        for name in required
        if not isinstance(value.get(name), str) or not value[name].strip()
    ]
    if missing:
        raise CheckpointError(
            "invalid_request",
            "migration request is missing: " + ", ".join(sorted(missing)),
        )
    path = value["path"].strip()
    revision = value["expected_revision"].strip()
    occurred_at = value["occurred_at"].strip()
    _require_single_line(
        {"path": path, "expected_revision": revision, "occurred_at": occurred_at},
        "migration request",
    )
    if not REVISION.fullmatch(revision):
        raise CheckpointError("invalid_request", "expected_revision must match r<N>")
    _validate_timestamp(occurred_at)
    return path, revision, occurred_at


def _atomic_validate(vault_root: Path, relative_path: str) -> dict[str, object]:
    note = _resolve_note(vault_root, relative_path)
    with _lock_path(note).open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        text = note.read_text(encoding="utf-8")
        document = _validate_document(vault_root, relative_path, text)
        return {
            "attestation": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "gates": [gate.gate for gate in document.gates],
            "path": relative_path,
            "plans": [gate.plan_path for gate in document.gates],
            "revision": document.revision,
        }


def _atomic_migrate(
    vault_root: Path,
    relative_path: str,
    expected_revision: str,
    occurred_at: str,
) -> dict[str, object]:
    note = _resolve_note(vault_root, relative_path)
    with _lock_path(note).open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original_stat = note.stat()
        original = note.read_text(encoding="utf-8")
        try:
            updated = migrate_prd(
                vault_root,
                relative_path,
                original,
                expected_revision,
                occurred_at,
            )
        except ProtocolError as error:
            raise CheckpointError(error.code, str(error)) from error
        current_stat = note.stat()
        if (
            current_stat.st_ino,
            current_stat.st_mtime_ns,
            current_stat.st_size,
        ) != (
            original_stat.st_ino,
            original_stat.st_mtime_ns,
            original_stat.st_size,
        ):
            raise CheckpointError(
                "external_write_conflict",
                "canonical PRD changed outside the checkpoint lock",
            )
        _atomic_replace(note, updated)
        observed = note.read_text(encoding="utf-8")
        if observed != updated:
            raise CheckpointError("attestation_failed", "post-write PRD migration attestation failed")
        document = _validate_document(vault_root, relative_path, observed)
        return {
            "attestation": hashlib.sha256(observed.encode("utf-8")).hexdigest(),
            "gates": [gate.gate for gate in document.gates],
            "path": relative_path,
            "plans": [gate.plan_path for gate in document.gates],
            "revision": document.revision,
            "transition": "migrate",
        }


def _lock_path(note: Path) -> Path:
    lock_root = Path(tempfile.gettempdir()) / "ctx-core-prd-checkpoints"
    lock_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_name = hashlib.sha256(str(note).encode("utf-8")).hexdigest() + ".lock"
    return lock_root / lock_name


def _atomic_guard(
    vault_root: Path,
    request: GuardRequest,
    action: str,
) -> dict[str, str]:
    note = _resolve_note(vault_root, request.path)
    with _lock_path(note).open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        return guard_document(note.read_text(encoding="utf-8"), request, action, vault_root)


DISARMING_TRANSITIONS = {"pause"}


def _record_arming(vault_root: Path, result: dict[str, str], session_id: str | None = None) -> None:
    """Refresh the on-disk arming record after a successful call.

    See ``prd_arming`` for why a hook-driven Claude Code runtime needs this
    where OMP holds an in-memory session binding instead. Best-effort: a
    failure here must never fail the surrounding checkpoint command.
    """
    try:
        prd_arming.arm(
            Path.cwd(),
            vault_root=vault_root,
            path=result["path"],
            gate=result["current_gate"],
            revision=result["revision"],
            session_id=session_id,
        )
    except Exception as error:  # noqa: BLE001 - arming is best-effort, never fatal
        print(f"warning: prd_checkpoint arming update failed: {error}", file=sys.stderr)


def _settle_arming(
    vault_root: Path, transition: str, result: dict[str, str], session_id: str | None = None
) -> None:
    """Refresh or clear the on-disk arming record after a successful transition.

    Cleared after ``pause`` and after a ``pass`` that completes every gate.
    Pausing exists to park work for an unknown, possibly cross-session
    interval; leaving the record armed would let a later, unrelated turn in
    the same repository trip the source-mutation guard for a PRD nobody is
    resuming. A completed PRD can never reactivate a gate, so its record
    would otherwise block that repository's bash/edit tools forever. OMP
    has neither failure mode: its binding simply disappears with the
    session, and both cases already fail closed there through PRD state
    alone (lifecycle_status != "active").

    ``record-merge`` deliberately stays armed even though it also leaves no
    gate active: OMP's binding keeps refusing source-mutation for a
    multi-gate PRD between one gate's ``record-merge`` and the next gate's
    ``activate`` (gate_status stays "passed", not "active"), and clearing
    the record here would silently under-enforce that same gap versus OMP.
    Only ``activate`` (or another successful transition) re-arms it, which
    naturally still happens moments later in the ordinary flow.

    Best-effort: never raises.
    """
    settles = transition in DISARMING_TRANSITIONS or (
        transition == "pass" and result.get("lifecycle_status") == "complete"
    )
    if settles:
        try:
            prd_arming.disarm(Path.cwd())
        except Exception as error:  # noqa: BLE001 - arming is best-effort, never fatal
            print(f"warning: prd_checkpoint arming clear failed: {error}", file=sys.stderr)
        return
    _record_arming(vault_root, result, session_id)


def _guard_session_id(explicit: str | None) -> str | None:
    """Guards are read-only checks: keep the record's current owner unless the caller names one."""
    if explicit:
        return explicit
    record = prd_arming.read(Path.cwd())
    return record.get("session_id") if record else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument(
        "--session-id",
        help="Agent session that owns this arming; transitions default to $CLAUDE_CODE_SESSION_ID.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--guard",
        choices=("source-mutation", "yield", "next-gate", "completion"),
    )
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--migrate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        value = json.load(sys.stdin)
        if args.guard:
            result = _atomic_guard(
                args.vault_root,
                GuardRequest.from_json(value),
                args.guard,
            )
            _record_arming(args.vault_root, result, _guard_session_id(args.session_id))
        elif args.validate:
            result = _atomic_validate(args.vault_root, _validation_path(value))
        elif args.migrate:
            path, revision, occurred_at = _migration_request(value)
            result = _atomic_migrate(
                args.vault_root,
                path,
                revision,
                occurred_at,
            )
        else:
            result = _atomic_transition(args.vault_root, Request.from_json(value))
            _settle_arming(
                args.vault_root,
                result["transition"],
                result,
                args.session_id or os.environ.get("CLAUDE_CODE_SESSION_ID") or None,
            )
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        failure = {"code": "invalid_request", "message": str(error)}
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 2
    except CheckpointError as error:
        failure: dict[str, str] = {"code": error.code, "message": str(error)}
        if error.current_revision:
            failure["current_revision"] = error.current_revision
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 3
    except OSError as error:
        print(json.dumps({"code": "storage_error", "message": str(error)}, sort_keys=True), file=sys.stderr)
        return 4

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
