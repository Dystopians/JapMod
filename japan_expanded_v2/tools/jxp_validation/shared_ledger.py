"""Validate the canonical JXP cross-agent development ledger."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from .core import CheckResult, ValidationContext


LEDGER_RELATIVE = Path("dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md")
COMPANION_DIRECTORY = "japan_expanded_v2_map"
ALLOWED_TODO_STATUSES = {"OPEN", "IN_PROGRESS", "BLOCKED", "DONE", "DEFERRED"}
REQUIRED_TODO_IDS = {f"JXP-{number:03d}" for number in range(1, 18)}
REQUIRED_HEADINGS = (
    "# JXP Shared Development Ledger",
    "## Read This First",
    "## Current Snapshot",
    "## Source Of Truth",
    "## Non-Negotiable Rules",
    "## Architecture Snapshot",
    "## Active TODO",
    "## Known Risks",
    "## Validation Matrix",
    "## Handoff Protocol",
    "## Update Journal",
    "## Historical Report Index",
)
REQUIRED_TOKENS = (
    "PENDING_USER_APPROVAL",
    "main_compatibility_contract.json",
    "BASELINE_LOCK.txt",
    "num_of_cities = 25/30",
    "STATIC_PASS",
    "RUNTIME_PASS",
    "validate_jxp_mod.ps1",
    "validate_all.ps1",
    "jxp_map_compat_shimabara_belt",
    "jxp_map_compat_ikko_heartland",
    "jxp_map_compat_setouchi",
    "jxp_map_compat_wokou_waters",
    "`1021`",
    "`4943`",
)


def _read_utf8(path: Path, result: CheckResult, code: str) -> str | None:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        result.add(code, f"could not read {path}: {exc}", path.as_posix())
        return None
    if path.suffix.casefold() == ".md" and payload.startswith(b"\xef\xbb\xbf"):
        result.add(
            "ledger.unexpected_bom",
            "Markdown coordination files must be ordinary UTF-8 without BOM",
            path.as_posix(),
        )
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        result.add(code, f"file is not valid UTF-8: {exc}", path.as_posix())
        return None


def _descriptor_version(path: Path, result: CheckResult, label: str) -> str | None:
    text = _read_utf8(path, result, "ledger.descriptor_read")
    if text is None:
        return None
    match = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        result.add(
            "ledger.descriptor_version_missing",
            f"{label} descriptor has no version field",
            path.as_posix(),
        )
        return None
    return match.group(1)


def _snapshot_value(text: str, label: str) -> str | None:
    match = re.search(
        rf"^- {re.escape(label)}: `([^`]+)`(?:.*)$",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _check_agent_pointer(
    path: Path,
    required_pointer: str,
    result: CheckResult,
) -> None:
    text = _read_utf8(path, result, "ledger.agent_entry_read")
    if text is None:
        return
    if required_pointer not in text:
        result.add(
            "ledger.agent_entry_pointer",
            f"agent entry must point to {required_pointer}",
            path.as_posix(),
        )
    if "Do not launch EU4" not in text:
        result.add(
            "ledger.agent_entry_runtime_rule",
            "agent entry must preserve the no-launch-without-permission rule",
            path.as_posix(),
        )


def check_shared_development_ledger(context: ValidationContext) -> CheckResult:
    result = CheckResult("Shared development ledger")
    ledger_path = context.mod_root / LEDGER_RELATIVE
    if not ledger_path.is_file():
        result.add(
            "ledger.missing",
            "canonical shared development ledger is missing",
            LEDGER_RELATIVE.as_posix(),
        )
        result.summary = "canonical ledger missing"
        return result

    text = _read_utf8(ledger_path, result, "ledger.read")
    if text is None:
        result.summary = "canonical ledger unreadable"
        return result

    lines = set(text.splitlines())
    for heading in REQUIRED_HEADINGS:
        if heading not in lines:
            result.add(
                "ledger.heading_missing",
                f"required heading is missing: {heading}",
                LEDGER_RELATIVE.as_posix(),
            )

    for token in REQUIRED_TOKENS:
        if token not in text:
            result.add(
                "ledger.contract_token_missing",
                f"required coordination token is missing: {token}",
                LEDGER_RELATIVE.as_posix(),
            )

    main_version = _snapshot_value(text, "Main Mod version")
    map_version = _snapshot_value(text, "Companion Map version")
    pinned_game = _snapshot_value(text, "Pinned game")
    runtime_status = _snapshot_value(text, "Runtime acceptance")
    snapshot_fields = {
        "Main Mod version": main_version,
        "Companion Map version": map_version,
        "Pinned game": pinned_game,
        "Runtime acceptance": runtime_status,
    }
    for label, value in snapshot_fields.items():
        if value is None:
            result.add(
                "ledger.snapshot_field_missing",
                f"Current Snapshot has no machine-readable {label} field",
                LEDGER_RELATIVE.as_posix(),
            )

    main_inner = context.mod_root / "descriptor.mod"
    main_outer = context.mod_root.parent / f"{context.mod_root.name}.mod"
    companion_root = context.mod_root.parent / COMPANION_DIRECTORY
    map_inner = companion_root / "descriptor.mod"
    map_outer = context.mod_root.parent / f"{COMPANION_DIRECTORY}.mod"
    descriptor_versions = {
        "main inner": _descriptor_version(main_inner, result, "main inner"),
        "main outer": _descriptor_version(main_outer, result, "main outer"),
        "map inner": _descriptor_version(map_inner, result, "map inner"),
        "map outer": _descriptor_version(map_outer, result, "map outer"),
    }
    for label in ("main inner", "main outer"):
        version = descriptor_versions[label]
        if main_version is not None and version is not None and version != main_version:
            result.add(
                "ledger.main_version_drift",
                f"{label} version {version!r} does not match ledger {main_version!r}",
                LEDGER_RELATIVE.as_posix(),
            )
    for label in ("map inner", "map outer"):
        version = descriptor_versions[label]
        if map_version is not None and version is not None and version != map_version:
            result.add(
                "ledger.map_version_drift",
                f"{label} version {version!r} does not match ledger {map_version!r}",
                LEDGER_RELATIVE.as_posix(),
            )

    if pinned_game != "EU4 v1.37.5.0 Inca (491d)":
        result.add(
            "ledger.game_version_drift",
            f"pinned game is {pinned_game!r}; expected 'EU4 v1.37.5.0 Inca (491d)'",
            LEDGER_RELATIVE.as_posix(),
        )
    if runtime_status != "PENDING_USER_APPROVAL":
        result.add(
            "ledger.runtime_status",
            "runtime acceptance may change only after an explicitly approved current-version run",
            LEDGER_RELATIVE.as_posix(),
        )

    _check_agent_pointer(
        context.mod_root / "AGENTS.md",
        "dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md",
        result,
    )
    _check_agent_pointer(
        companion_root / "AGENTS.md",
        "../japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md",
        result,
    )

    contract_path = (
        companion_root
        / "tools"
        / "jxp_map_validation"
        / "main_compatibility_contract.json"
    )
    if not contract_path.is_file():
        result.add(
            "ledger.compatibility_contract_missing",
            "companion main compatibility contract is missing",
            contract_path.as_posix(),
        )

    todo_pattern = re.compile(
        r"^\|\s*(JXP-\d{3})\s*\|\s*(P[0-3])\s*\|\s*([A-Z_]+)\s*\|"
        r"\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$",
        re.MULTILINE,
    )
    todo_rows = todo_pattern.findall(text)
    todo_ids = [row[0] for row in todo_rows]
    for todo_id, count in Counter(todo_ids).items():
        if count != 1:
            result.add(
                "ledger.todo_duplicate",
                f"TODO id {todo_id} occurs {count} times in the active table",
                LEDGER_RELATIVE.as_posix(),
            )
    for missing_id in sorted(REQUIRED_TODO_IDS.difference(todo_ids)):
        result.add(
            "ledger.todo_missing",
            f"stable TODO id is missing from the active table: {missing_id}",
            LEDGER_RELATIVE.as_posix(),
        )
    for todo_id, _priority, status, owner, _scope, _task, evidence in todo_rows:
        if status not in ALLOWED_TODO_STATUSES:
            result.add(
                "ledger.todo_status",
                f"{todo_id} uses unsupported status {status!r}",
                LEDGER_RELATIVE.as_posix(),
            )
        if status == "IN_PROGRESS" and owner == "UNCLAIMED":
            result.add(
                "ledger.todo_unowned",
                f"{todo_id} is IN_PROGRESS but has no owner",
                LEDGER_RELATIVE.as_posix(),
            )
        if status == "DONE" and ("PENDING" in evidence or "待" in evidence):
            result.add(
                "ledger.todo_done_without_evidence",
                f"{todo_id} is DONE but its evidence is still pending",
                LEDGER_RELATIVE.as_posix(),
            )

    indexed_files = 0
    log_roots = (context.mod_root / "dev_logs", companion_root / "dev_logs")
    for log_root in log_roots:
        if not log_root.is_dir():
            result.add(
                "ledger.log_directory_missing",
                "required development log directory is missing",
                log_root.as_posix(),
            )
            continue
        for report in sorted(log_root.iterdir(), key=lambda path: path.name.casefold()):
            if not report.is_file() or report.resolve() == ledger_path.resolve():
                continue
            indexed_files += 1
            if f"`{report.name}`" not in text:
                result.add(
                    "ledger.report_unindexed",
                    f"development report is not listed in Historical Report Index: {report.name}",
                    report.as_posix(),
                )

    result.metrics.update(
        {
            "schema": _snapshot_value(text, "Ledger schema"),
            "todo_rows": len(todo_rows),
            "indexed_reports": indexed_files,
            "main_version": main_version,
            "map_version": map_version,
            "runtime_acceptance": runtime_status,
        }
    )
    result.summary = (
        f"versions {main_version or '<missing>'}/{map_version or '<missing>'}; "
        f"{len(todo_rows)} stable TODOs; {indexed_files} historical reports indexed"
    )
    return result
