"""Structural validation and deterministic migration for canonical ctx-core PRDs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---(?P<tail>\n|\Z)", re.DOTALL)
PRD_SECTIONS = (
    "Outcome",
    "Boundaries",
    "Decisions",
    "Current checkpoint",
    "Gates",
    "Approval",
    "Evidence",
    "Amendments",
)
GATE_FIELDS = (
    "Proves",
    "Feature list",
    "Implementation plan",
    "Verifier",
    "Status",
    "Evidence",
)
CHECKPOINT_FIELDS = (
    "Gate",
    "Status",
    "Verified",
    "Blockers",
    "Decision",
    "Next",
    "Repository",
)
PLAN_SECTIONS = (
    "Outcome",
    "Reuse decisions",
    "Implementation slice",
    "Parallel execution contract",
    "Verification",
    "Non-goals",
)
PARALLEL_FIELDS = (
    "Backend/contracts/architecture owner",
    "Independent UI or specialist lane",
    "Shared integration owner",
    "File ownership and no-overlap constraints",
    "Final integration and verification pass",
)
GATE_STATUSES = {"pending", "active", "passed", "failed", "blocked"}
LIFECYCLE_STATUSES = {
    "draft",
    "approved",
    "active",
    "paused",
    "blocked",
    "complete",
    "abandoned",
}
MODEL_SPECIFIC = re.compile(
    r"(?i)(?:\b(?:opus|sonnet|haiku|codex(?:\s+sol)?|gpt-[a-z0-9_.-]+)\b|claude\s+-p|--model\b)"
)


class ProtocolError(Exception):
    """A structural protocol refusal with a stable machine code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Heading:
    title: str
    start: int
    body_start: int
    end: int


@dataclass(frozen=True)
class GateDocument:
    gate: str
    status: str
    plan_path: str


@dataclass(frozen=True)
class ProtocolDocument:
    revision: str
    gates: tuple[GateDocument, ...]


@dataclass(frozen=True)
class PathContract:
    initiative: PurePosixPath
    prd_path: str
    plan_prefix: str


def _headings(text: str, level: int) -> list[Heading]:
    marker = "#" * level
    found: list[tuple[str, int, int]] = []
    offset = 0
    fenced = False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if re.match(r"^\s*```", stripped):
            fenced = not fenced
        elif not fenced:
            match = re.fullmatch(rf"{re.escape(marker)} (?!#)(.+?)\s*", stripped)
            if match:
                found.append((match.group(1), offset, offset + len(line)))
        offset += len(line)
    return [
        Heading(title, start, body_start, found[index + 1][1] if index + 1 < len(found) else len(text))
        for index, (title, start, body_start) in enumerate(found)
    ]


def _frontmatter_values(text: str, document: str) -> dict[str, str]:
    match = FRONTMATTER.match(text)
    if not match:
        raise ProtocolError("invalid_prd", f"{document}: canonical PRD requires YAML frontmatter")
    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if field:
            value = field.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            values[field.group(1)] = value
    return values


def _path_contract(relative_path: str) -> PathContract:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ProtocolError("invalid_prd", f"{relative_path}: PRD path must be vault-relative")
    if len(path.parts) < 3 or path.parent.name != "PRD" or path.suffix != ".md":
        raise ProtocolError(
            "invalid_prd",
            f"{relative_path}: expected deterministic PRD path <initiative>/PRD/<ticket-or-slug>.md",
        )
    initiative = path.parent.parent
    stem = path.stem.lower()
    ticket = re.match(r"(?P<ticket>[a-z]{2,10}-?\d+)(?:-|$)", stem)
    prefix = ticket.group("ticket").replace("-", "") if ticket else stem
    return PathContract(initiative, path.as_posix(), prefix)


def _section_map(text: str, document: str) -> tuple[list[Heading], dict[str, Heading]]:
    headings = _headings(text, 2)
    titles = [heading.title for heading in headings]
    if titles != list(PRD_SECTIONS):
        raise ProtocolError(
            "invalid_prd",
            f"{document}: top-level sections are {titles}; expected {list(PRD_SECTIONS)} in exact order",
        )
    return headings, {heading.title: heading for heading in headings}


def _section_text(text: str, heading: Heading) -> str:
    return text[heading.start:heading.end]


def section_span(text: str, title: str, document: str = "PRD") -> tuple[int, int]:
    _, sections = _section_map(text, document)
    heading = sections.get(title)
    if not heading:
        raise ProtocolError("invalid_prd", f"{document}: missing section {title}")
    return heading.start, heading.end


def gate_headings(text: str, document: str = "PRD") -> tuple[Heading, ...]:
    _, sections = _section_map(text, document)
    gates = sections["Gates"]
    nested = _headings(_section_text(text, gates), 3)
    return tuple(
        Heading(
            heading.title,
            gates.start + heading.start,
            gates.start + heading.body_start,
            gates.start + heading.end,
        )
        for heading in nested
    )


def _wiki_targets(text: str) -> list[str]:
    targets: list[str] = []
    for match in re.finditer(r"\[\[(.*?)\]\]", text, re.DOTALL):
        inner = re.sub(r"\s+", " ", match.group(1)).strip()
        targets.append(inner.split("|", 1)[0].strip())
    return targets


def _normalize_markdown_path(target: str) -> str:
    normalized = target.split("#", 1)[0].strip().removeprefix("/")
    return normalized if normalized.endswith(".md") else normalized + ".md"


def _resolve_markdown_path(
    vault_root: Path,
    target: str,
    document: str,
) -> str:
    normalized = _normalize_markdown_path(target)
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ProtocolError("invalid_plan", f"{document}: link target escapes the vault: {target}")
    exact = vault_root / path
    if exact.is_file():
        return path.as_posix()
    matches = sorted(
        candidate.relative_to(vault_root).as_posix()
        for candidate in vault_root.rglob(path.name)
        if candidate.is_file()
        and PurePosixPath(candidate.relative_to(vault_root).as_posix()).as_posix().endswith(
            path.as_posix()
        )
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ProtocolError(
            "invalid_plan",
            f"{document}: shortest-path link {target} is ambiguous: {matches}",
        )
    return path.as_posix()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "gate"


def _expected_plan_path(contract: PathContract, gate: str, heading_title: str) -> str:
    number = re.fullmatch(r"G([1-9]\d*)", gate)
    if not number:
        raise ProtocolError("invalid_prd", f"{contract.prd_path}: gate {gate} must use G<positive-number>")
    title = heading_title.split("—", 1)[1].strip() if "—" in heading_title else heading_title.removeprefix(gate).strip()
    filename = f"{contract.plan_prefix}-g{number.group(1)}-{_slug(title)}.md"
    return (contract.initiative / "Planning" / filename).as_posix()


def _validate_plan_path(contract: PathContract, gate: str, plan_path: str) -> None:
    path = PurePosixPath(plan_path)
    number = re.fullmatch(r"G([1-9]\d*)", gate)
    if not number:
        raise ProtocolError("invalid_prd", f"{contract.prd_path}: gate {gate} must use G<positive-number>")
    expected_parent = contract.initiative / "Planning"
    expected_name = re.compile(
        rf"{re.escape(contract.plan_prefix)}-g{number.group(1)}-[a-z0-9]+(?:-[a-z0-9]+)*\.md"
    )
    if path.parent != expected_parent or not expected_name.fullmatch(path.name):
        raise ProtocolError(
            "invalid_prd",
            f"{contract.prd_path}: gate {gate} plan {plan_path} must match "
            f"{expected_parent.as_posix()}/{contract.plan_prefix}-g{number.group(1)}-<gate-slug>.md",
        )


def _canonical_gate_fields(section: str, document: str, gate: str) -> tuple[dict[str, str], list[str]]:
    lines = section.splitlines()
    matches: list[tuple[int, str, str]] = []
    field_pattern = re.compile(
        r"^- \*\*(Proves|Feature list|Implementation plan|Verifier|Status|Evidence):\*\*(?:\s*(.*))?$"
    )
    for index, line in enumerate(lines):
        match = field_pattern.fullmatch(line)
        if match:
            matches.append((index, match.group(1), (match.group(2) or "").strip()))
    names = [name for _, name, _ in matches]
    if names != list(GATE_FIELDS):
        raise ProtocolError(
            "invalid_prd",
            f"{document}: gate {gate} fields are {names}; expected {list(GATE_FIELDS)} in exact order",
        )
    if len(set(names)) != len(names):
        raise ProtocolError("invalid_prd", f"{document}: gate {gate} contains duplicate fields")
    values = {name: value for _, name, value in matches}
    for name in GATE_FIELDS:
        if name != "Feature list" and not values[name]:
            raise ProtocolError("invalid_prd", f"{document}: gate {gate} field {name} must be non-empty")
    feature_index = next(index for index, name, _ in matches if name == "Feature list")
    next_index = next(index for index, name, _ in matches if name == "Implementation plan")
    if values["Feature list"]:
        raise ProtocolError(
            "invalid_prd",
            f"{document}: gate {gate} Feature list must contain indented bullet nodes, not inline text",
        )
    features: list[str] = []
    for line in lines[feature_index + 1:next_index]:
        if not line.strip():
            continue
        bullet = re.fullmatch(r"  - (\S.*)", line)
        if not bullet:
            raise ProtocolError(
                "invalid_prd",
                f"{document}: gate {gate} Feature list requires exactly one concise feature per direct bullet node",
            )
        features.append(bullet.group(1))
    if not features:
        raise ProtocolError("invalid_prd", f"{document}: gate {gate} Feature list must contain at least one bullet")
    implementation_links = _wiki_targets(values["Implementation plan"])
    if len(implementation_links) != 1 or not re.fullmatch(
        r"\[\[[^\]]+\]\]", values["Implementation plan"]
    ):
        raise ProtocolError(
            "invalid_prd",
            f"{document}: gate {gate} Implementation plan must be exactly one embedded Obsidian link",
        )
    return values, features


def _validate_parallel_contract(plan_path: str, section: str) -> None:
    fields: list[tuple[str, str]] = []
    pattern = re.compile(
        r"^- \*\*(Backend/contracts/architecture owner|Independent UI or specialist lane|Shared integration owner|File ownership and no-overlap constraints|Final integration and verification pass):\*\*\s*(\S.*)$"
    )
    for line in section.splitlines():
        match = pattern.fullmatch(line)
        if match:
            fields.append((match.group(1), match.group(2).strip()))
    names = [name for name, _ in fields]
    if names != list(PARALLEL_FIELDS):
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: Parallel execution contract fields are {names}; expected {list(PARALLEL_FIELDS)}",
        )
    normalized = [re.sub(r"\s+", " ", value).strip().casefold() for _, value in fields]
    if len(set(normalized)) != len(normalized):
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: Parallel execution contract fields must describe distinct responsibilities",
        )
    lane = dict(fields)["Independent UI or specialist lane"]
    applicable_ui = lane.casefold() != "not applicable"
    if applicable_ui and "impeccable" not in lane.casefold():
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: applicable UI lanes must require impeccable; use exactly 'Not applicable' when no lane exists",
        )


def _validate_plan(vault_root: Path, plan_path: str, gate: str, prd_path: str) -> None:
    target = vault_root / PurePosixPath(plan_path)
    if not target.is_file():
        raise ProtocolError(
            "missing_plan",
            f"{prd_path}: gate {gate} linked plan is missing at expected deterministic path {plan_path}",
        )
    text = target.read_text(encoding="utf-8")
    if MODEL_SPECIFIC.search(text):
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: implementation plans must remain model-agnostic",
        )
    backlinks = {
        _resolve_markdown_path(vault_root, value, plan_path)
        for value in _wiki_targets(text)
    }
    if prd_path not in backlinks:
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: gate {gate} plan must link back to canonical PRD {prd_path}",
        )
    frontmatter = _frontmatter_values(text, plan_path)
    if frontmatter.get("type") != "implementation-plan" or frontmatter.get("gate") != gate:
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: expected type implementation-plan and gate {gate}",
        )
    headings = _headings(text, 2)
    titles = [heading.title for heading in headings]
    if titles[:2] != ["Outcome", "Reuse decisions"] or "Implementation slice" not in titles:
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: required plan sections must begin Outcome, Reuse decisions and include Implementation slice",
        )
    implementation_index = titles.index("Implementation slice")
    if implementation_index < 2 or titles[implementation_index:] != list(PLAN_SECTIONS[2:]):
        raise ProtocolError(
            "invalid_plan",
            f"{plan_path}: after optional gate-specific sections, expected {list(PLAN_SECTIONS[2:])} in order; found {titles}",
        )
    parallel = headings[titles.index("Parallel execution contract")]
    _validate_parallel_contract(plan_path, _section_text(text, parallel))


def _checkpoint_values(section: str, document: str) -> dict[str, str]:
    fields: list[tuple[str, str]] = []
    for line in section.splitlines():
        match = re.fullmatch(r"^- ([A-Za-z][A-Za-z0-9 /_-]*):\s*(.*)$", line)
        if match and match.group(1) in CHECKPOINT_FIELDS:
            fields.append((match.group(1), match.group(2).strip()))
    names = [name for name, _ in fields]
    if names != list(CHECKPOINT_FIELDS):
        raise ProtocolError(
            "invalid_prd",
            f"{document}: Current checkpoint fields are {names}; expected {list(CHECKPOINT_FIELDS)} in order",
        )
    values = dict(fields)
    empty = [name for name, value in fields if not value]
    if empty:
        raise ProtocolError("invalid_prd", f"{document}: Current checkpoint fields must be non-empty: {empty}")
    return values


def validate_prd(vault_root: Path, relative_path: str, text: str) -> ProtocolDocument:
    contract = _path_contract(relative_path)
    frontmatter = _frontmatter_values(text, relative_path)
    required_frontmatter = ("type", "status", "revision", "current_gate", "updated")
    missing = [name for name in required_frontmatter if name not in frontmatter]
    if missing:
        raise ProtocolError("invalid_prd", f"{relative_path}: frontmatter is missing {missing}")
    if frontmatter["type"] != "ctx-prd":
        raise ProtocolError("invalid_prd", f"{relative_path}: note type must be ctx-prd")
    if frontmatter["status"] not in LIFECYCLE_STATUSES:
        raise ProtocolError("invalid_prd", f"{relative_path}: invalid lifecycle status {frontmatter['status']}")
    if not re.fullmatch(r"r[1-9]\d*", frontmatter["revision"]):
        raise ProtocolError("invalid_prd", f"{relative_path}: revision must match r<N>")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", frontmatter["updated"]):
        raise ProtocolError("invalid_prd", f"{relative_path}: updated must match YYYY-MM-DD")

    _, sections = _section_map(text, relative_path)
    checkpoint = _checkpoint_values(_section_text(text, sections["Current checkpoint"]), relative_path)
    approval = _section_text(text, sections["Approval"])
    if not re.search(r"^- \[[ xX]\] Approved for execution\s*$", approval, re.MULTILINE):
        raise ProtocolError("invalid_prd", f"{relative_path}: Approval must contain the execution checkbox")

    headings = gate_headings(text, relative_path)
    if not headings:
        raise ProtocolError("invalid_prd", f"{relative_path}: Gates contains no gates")
    parsed_headings: list[tuple[Heading, str]] = []
    for heading in headings:
        match = re.fullmatch(r"(G[1-9]\d*)(?:\s+—\s+.+)?", heading.title)
        if not match:
            raise ProtocolError("invalid_prd", f"{relative_path}: invalid gate heading {heading.title}")
        parsed_headings.append((heading, match.group(1)))
    gate_order = [gate for _, gate in parsed_headings]
    expected_order = [f"G{index}" for index in range(1, len(gate_order) + 1)]
    if gate_order != expected_order:
        raise ProtocolError(
            "invalid_prd",
            f"{relative_path}: gates are {gate_order}; expected {expected_order} in exact numeric order",
        )

    gates: list[GateDocument] = []
    seen: set[str] = set()
    for heading, gate in parsed_headings:
        if gate in seen:
            raise ProtocolError("invalid_prd", f"{relative_path}: duplicate gate {gate}")
        seen.add(gate)
        values, _ = _canonical_gate_fields(_section_text(text, heading), relative_path, gate)
        status = values["Status"]
        if status not in GATE_STATUSES:
            raise ProtocolError("invalid_prd", f"{relative_path}: gate {gate} has invalid status {status}")
        target = _resolve_markdown_path(
            vault_root,
            _wiki_targets(values["Implementation plan"])[0],
            relative_path,
        )
        _validate_plan_path(contract, gate, target)
        _validate_plan(vault_root, target, gate, relative_path)
        gates.append(GateDocument(gate, status, target))

    for index, gate in enumerate(gates):
        if gate.status in {"active", "passed"}:
            incomplete = [item.gate for item in gates[:index] if item.status != "passed"]
            if incomplete:
                raise ProtocolError(
                    "invalid_prd",
                    f"{relative_path}: gate {gate.gate} is {gate.status} before preceding verifier passes: {incomplete}",
                )
    active = [gate.gate for gate in gates if gate.status == "active"]
    if len(active) > 1:
        raise ProtocolError("invalid_prd", f"{relative_path}: multiple active gates {active}")
    current_gate = frontmatter["current_gate"]
    if current_gate not in {"", "null", "~"} and current_gate not in seen:
        raise ProtocolError("invalid_prd", f"{relative_path}: current_gate {current_gate} is not defined")
    if frontmatter["status"] == "active":
        current_status = next(
            (gate.status for gate in gates if gate.gate == current_gate),
            None,
        )
        if current_status not in {"active", "passed"}:
            raise ProtocolError(
                "invalid_prd",
                f"{relative_path}: active lifecycle requires the current gate to be active or passed; "
                f"frontmatter={current_gate}, gate_status={current_status}",
            )
    checkpoint_gate = checkpoint["Gate"]
    if current_gate not in {"", "null", "~"} and checkpoint_gate != current_gate:
        raise ProtocolError(
            "invalid_prd",
            f"{relative_path}: Current checkpoint gate {checkpoint_gate} differs from current_gate {current_gate}",
        )
    return ProtocolDocument(frontmatter["revision"], tuple(gates))


def _legacy_field_pattern() -> re.Pattern[str]:
    names = "|".join(re.escape(name) for name in GATE_FIELDS)
    return re.compile(rf"^- (?:\*\*)?({names}):(?:\*\*)?(?:\s*(.*))?$")


def _migrate_checkpoint(section: str, document: str) -> str:
    lines = section.rstrip().splitlines()
    values: dict[str, str] = {}
    extras: list[str] = []
    for line in lines[1:]:
        match = re.fullmatch(r"^- ([A-Za-z][A-Za-z0-9 /_-]*):\s*(.*)$", line)
        if match and match.group(1) in CHECKPOINT_FIELDS:
            values[match.group(1)] = match.group(2).strip()
        else:
            extras.append(line)
    for sentinel in ("Blockers", "Decision"):
        if sentinel not in values:
            values[sentinel] = "none"
    missing = [name for name in CHECKPOINT_FIELDS if not values.get(name)]
    if missing:
        raise ProtocolError(
            "migration_content_required",
            f"{document}: Current checkpoint requires existing values for {missing}; migration will not invent them",
        )
    output = ["## Current checkpoint", ""]
    output.extend(f"- {name}: {values[name]}" for name in CHECKPOINT_FIELDS)
    if any(line.strip() for line in extras):
        output.append("")
        output.extend(extras)
    return "\n".join(output).rstrip()


def _migrate_gates(
    vault_root: Path,
    contract: PathContract,
    section: str,
) -> tuple[str, list[str]]:
    headings = _headings(section, 3)
    if not headings:
        raise ProtocolError("migration_content_required", f"{contract.prd_path}: Gates contains no gates")
    output = ["## Gates", ""]
    retained: list[str] = []
    pattern = _legacy_field_pattern()
    for heading in headings:
        gate_match = re.fullmatch(r"(G[1-9]\d*)(?:\s+—\s+.+)?", heading.title)
        if not gate_match:
            raise ProtocolError("migration_content_required", f"{contract.prd_path}: invalid gate heading {heading.title}")
        gate = gate_match.group(1)
        raw = _section_text(section, heading)
        lines = raw.splitlines()
        matches: list[tuple[int, str, str]] = []
        for index, line in enumerate(lines):
            match = pattern.fullmatch(line)
            if match:
                matches.append((index, match.group(1), (match.group(2) or "").strip()))
        values = {name: value for _, name, value in matches}
        missing = [name for name in ("Proves", "Feature list", "Verifier", "Status", "Evidence") if name not in values]
        if missing:
            raise ProtocolError(
                "migration_content_required",
                f"{contract.prd_path}: gate {gate} is missing {missing}; migration will not invent product behavior or evidence",
            )
        feature_index = next(index for index, name, _ in matches if name == "Feature list")
        later = [index for index, _, _ in matches if index > feature_index]
        feature_end = min(later) if later else len(lines)
        features = [
            match.group(1)
            for line in lines[feature_index + 1:feature_end]
            if (match := re.fullmatch(r"  - (\S.*)", line))
        ]
        if values["Feature list"] or not features:
            raise ProtocolError(
                "migration_content_required",
                f"{contract.prd_path}: gate {gate} Feature list needs existing direct bullets; migration will not invent them",
            )
        consumed = {0, *(index for index, _, _ in matches)}
        consumed.update(range(feature_index + 1, feature_end))
        evidence_index = next(index for index, name, _ in matches if name == "Evidence")
        evidence_continuations = [
            line
            for line in lines[evidence_index + 1:]
            if line.strip() and re.match(r"^\s{2,}\S", line)
        ]
        consumed.update(
            index
            for index in range(evidence_index + 1, len(lines))
            if lines[index] in evidence_continuations
        )
        unknown_lines = [
            line
            for index, line in enumerate(lines)
            if index not in consumed and line.strip()
        ]
        if unknown_lines:
            retained.append(
                f"### {heading.title}\n" + "\n".join(unknown_lines)
            )
        plan_value = values.get("Implementation plan", "")
        links = _wiki_targets(plan_value)
        if links:
            if len(links) != 1:
                raise ProtocolError("migration_content_required", f"{contract.prd_path}: gate {gate} has multiple plan links")
            plan_path = _resolve_markdown_path(vault_root, links[0], contract.prd_path)
        else:
            plan_path = _expected_plan_path(contract, gate, heading.title)
            if not (vault_root / PurePosixPath(plan_path)).is_file():
                raise ProtocolError(
                    "missing_plan",
                    f"{contract.prd_path}: gate {gate} requires {plan_path}; create the plan rather than fabricating implementation content",
                )
            plan_value = f"[[{plan_path.removesuffix('.md')}|{heading.title}]]"
        output.extend(
            [
                f"### {heading.title}",
                f"- **Proves:** {values['Proves']}",
                "- **Feature list:**",
                *[f"  - {feature}" for feature in features],
                f"- **Implementation plan:** {plan_value}",
                f"- **Verifier:** {values['Verifier']}",
                f"- **Status:** {values['Status']}",
                f"- **Evidence:** {values['Evidence']}",
                *evidence_continuations,
                "",
            ]
        )
    return "\n".join(output).rstrip(), retained


def _replace_frontmatter_values(text: str, updates: dict[str, str]) -> str:
    match = FRONTMATTER.match(text)
    if not match:
        raise ProtocolError("invalid_prd", "canonical PRD requires YAML frontmatter")
    remaining = dict(updates)
    lines: list[str] = []
    for line in match.group("body").splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*.*$", line)
        if field and field.group(1) in remaining:
            name = field.group(1)
            lines.append(f"{name}: {remaining.pop(name)}")
        else:
            lines.append(line)
    if remaining:
        raise ProtocolError("migration_content_required", f"frontmatter is missing writable fields {sorted(remaining)}")
    replacement = "---\n" + "\n".join(lines) + "\n---" + match.group("tail")
    return replacement + text[match.end():]


def migrate_prd(
    vault_root: Path,
    relative_path: str,
    text: str,
    expected_revision: str,
    occurred_at: str,
) -> str:
    contract = _path_contract(relative_path)
    frontmatter = _frontmatter_values(text, relative_path)
    revision = frontmatter.get("revision", "")
    if revision != expected_revision:
        raise ProtocolError(
            "revision_conflict",
            f"{relative_path}: expected {expected_revision}, found {revision}",
        )
    match = re.fullmatch(r"r([1-9]\d*)", revision)
    if not match:
        raise ProtocolError("invalid_prd", f"{relative_path}: revision must match r<N>")
    headings = _headings(text, 2)
    by_title: dict[str, Heading] = {}
    for heading in headings:
        if heading.title in by_title:
            raise ProtocolError("migration_content_required", f"{relative_path}: duplicate section {heading.title}")
        by_title[heading.title] = heading
    required = [name for name in PRD_SECTIONS if name != "Evidence"]
    missing = [name for name in required if name not in by_title]
    if missing:
        raise ProtocolError(
            "migration_content_required",
            f"{relative_path}: migration requires existing sections {missing}; content will not be invented",
        )

    gate_retained: list[str] = []
    migrated: dict[str, str] = {}
    for name in PRD_SECTIONS:
        if name == "Evidence" and name not in by_title:
            migrated[name] = "## Evidence\n\n- None."
        elif name == "Current checkpoint":
            migrated[name] = _migrate_checkpoint(_section_text(text, by_title[name]), relative_path)
        elif name == "Gates":
            migrated[name], gate_retained = _migrate_gates(
                vault_root,
                contract,
                _section_text(text, by_title[name]),
            )
        else:
            migrated[name] = _section_text(text, by_title[name]).rstrip()

    unknown = [
        _section_text(text, heading).rstrip()
        for heading in headings
        if heading.title not in PRD_SECTIONS
    ]
    unknown.extend(gate_retained)
    if unknown:
        retained = ["", "### Retained historical content", ""]
        for section in unknown:
            retained.extend("    " + line for line in section.splitlines())
            retained.append("")
        migrated["Amendments"] = migrated["Amendments"].rstrip() + "\n" + "\n".join(retained).rstrip()

    prefix_end = headings[0].start
    prefix = text[:prefix_end].rstrip()
    updated = prefix + "\n\n" + "\n\n".join(migrated[name] for name in PRD_SECTIONS) + "\n"
    updated = _replace_frontmatter_values(
        updated,
        {
            "revision": f"r{int(match.group(1)) + 1}",
            "updated": occurred_at[:10],
        },
    )
    validate_prd(vault_root, relative_path, updated)
    return updated
