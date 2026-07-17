"""Validate the canonical JXP cross-agent development ledger."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from .core import CheckResult, ValidationContext


LEDGER_RELATIVE = Path("dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md")
COMPANION_DIRECTORY = "japan_expanded_v2_map"
ALLOWED_TODO_STATUSES = {"OPEN", "IN_PROGRESS", "BLOCKED", "DONE", "DEFERRED"}
REQUIRED_TODO_IDS = {f"JXP-{number:03d}" for number in range(1, 24)}
REQUIRED_EXTERNAL_EVIDENCE_IDS = {
    "EXT-R5-SAVE-001",
    "EXT-R5-ZIP-001",
    "EXT-R5-ZIP-002",
    "EXT-R5-ZIP-003",
    "EXT-R5-PROV-001",
    "EXT-R5-HASH-001",
    "EXT-R5-ID-001",
}
EXPECTED_LEDGER_SCHEMA = "2"
EXPECTED_R5_SIZE = "36371037"
EXPECTED_R5_SHA256 = "9f6dd96a60c7b9f583c22f87e7da2f5c659e2edc14723483a077b7afd73a8bef"
EXPECTED_EXTERNAL_EVIDENCE = {
    "EXT-R5-SAVE-001": (
        "36371037",
        EXPECTED_R5_SHA256,
        "ADMITTED_STATIC_INPUT",
    ),
    "EXT-R5-ZIP-001": (
        "47308072",
        "64f11ace4f049b799b1c9d5cf0fa64d0a75abf485d90c0dbc0814fc71107485d",
        "STRICT_VALIDATED",
    ),
    "EXT-R5-ZIP-002": (
        "47373265",
        "c05c1b9ee8d1aab31e02b472ae2c8f897cdfa08e07b33b75367eac1b3984ae3d",
        "STRICT_VALIDATED",
    ),
    "EXT-R5-ZIP-003": (
        "48071664",
        "cdbcfd3a7abe5653bc8c44a377912511c6ec864587d0a504aec21c949f6b6ae4",
        "STRICT_VALIDATED",
    ),
    "EXT-R5-PROV-001": (
        "2326",
        "03dd5ed8504e7d70a33153010cf8a411a66c9fa3bfb23294a4dd94567f0939da",
        "STRICT_VALIDATED",
    ),
    "EXT-R5-HASH-001": (
        "368",
        "9b1018eebdbf15b6f9101971191d43c6dfae686ca0d92ba30ebf451e1dfafa34",
        "STRICT_VALIDATED",
    ),
    "EXT-R5-ID-001": (
        "2292",
        "bc0dcbece19d32d85f9f50ecff08350de6b7a9024a044a2d30a1a8f44c85759d",
        "STRICT_VALIDATED",
    ),
}
ALLOWED_HOST_PORTABILITY = {"REVIEW_REQUIRED", "READY", "RUNTIME_VALIDATED"}
ALLOWED_R5_FIXTURE_STATUSES = {
    "MISSING",
    "FOUND_ESCROWED_NOT_ADMITTED",
    "ADMITTED_STATIC_INPUT",
    "ADMITTED",
    "RUNTIME_PASS",
}
ALLOWED_MATRIX_BLOCKER_STATES = {
    "R5_AND_R13_REVIEW_PENDING",
    "NONE",
}
ALLOWED_NEXT_STEPS = {
    "PORTABILITY_SLICE",
    "STATIC_GATES",
    "PREFLIGHT",
    "AWAITING_COMMIT_AUTHORIZATION",
    "AWAITING_LAUNCH_PERMISSION",
    "PROBE",
    "RUNTIME_SCENARIOS",
    "R13_CLOSURE",
    "RELEASE_COMPLETE",
    "STATIC_RECLOSURE_THEN_SINGLE_AUTHORIZED_LAUNCH",
}
ALLOWED_RUNTIME_STATUSES = {
    "PENDING_USER_APPROVAL",
    "AUTHORIZED_NOT_STARTED",
}
REQUIRED_HEADINGS = (
    "# JXP Shared Development Ledger",
    "## Read This First",
    "## Current Snapshot",
    "## Live Execution State",
    "## Source Of Truth",
    "## Non-Negotiable Rules",
    "## Architecture Snapshot",
    "## Active TODO",
    "## Active TODO Runtime Closure Map",
    "## Known Risks",
    "## External Evidence Registry",
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
    "ADMITTED_STATIC_INPUT",
    "C:\\JXP_Acceptance",
    "C:\\JXP_R5_Escrow\\20260713_original_machine",
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


def _section(text: str, start: str, end: str) -> str:
    start_marker = f"{start}\n"
    end_marker = f"{end}\n"
    start_index = text.find(start_marker)
    end_index = text.find(end_marker, start_index + len(start_marker))
    if start_index < 0 or end_index < 0:
        return ""
    return text[start_index + len(start_marker) : end_index]


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
    text = text.replace("\r\n", "\n").replace("\r", "\n")

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

    ledger_schema = _snapshot_value(text, "Ledger schema")
    last_updated = _snapshot_value(text, "Last updated")
    main_version = _snapshot_value(text, "Main Mod version")
    map_version = _snapshot_value(text, "Companion Map version")
    pinned_game = _snapshot_value(text, "Pinned game")
    runtime_status = _snapshot_value(text, "Runtime acceptance")
    runtime_candidate = _snapshot_value(text, "Runtime candidate")
    runtime_matrix_sha256 = _snapshot_value(text, "Runtime matrix SHA-256")
    host_portability = _snapshot_value(text, "Host portability")
    r5_fixture_status = _snapshot_value(text, "R5 fixture status")
    matrix_blockers = _snapshot_value(text, "Runtime matrix blockers")
    next_executable_step = _snapshot_value(text, "Next executable step")
    current_host_helper = _snapshot_value(text, "Current-host acceptance helper")
    snapshot_fields = {
        "Ledger schema": ledger_schema,
        "Last updated": last_updated,
        "Main Mod version": main_version,
        "Companion Map version": map_version,
        "Pinned game": pinned_game,
        "Runtime acceptance": runtime_status,
        "Runtime candidate": runtime_candidate,
        "Runtime matrix SHA-256": runtime_matrix_sha256,
        "Host portability": host_portability,
        "R5 fixture status": r5_fixture_status,
        "Runtime matrix blockers": matrix_blockers,
        "Next executable step": next_executable_step,
        "Current-host acceptance helper": current_host_helper,
    }
    for label, value in snapshot_fields.items():
        if value is None:
            result.add(
                "ledger.snapshot_field_missing",
                f"Current Snapshot has no machine-readable {label} field",
                LEDGER_RELATIVE.as_posix(),
            )

    if ledger_schema != EXPECTED_LEDGER_SCHEMA:
        result.add(
            "ledger.schema_drift",
            f"ledger schema is {ledger_schema!r}; expected {EXPECTED_LEDGER_SCHEMA!r}",
            LEDGER_RELATIVE.as_posix(),
        )
    if last_updated is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_updated):
        result.add(
            "ledger.last_updated_format",
            f"Last updated must be an ISO date, got {last_updated!r}",
            LEDGER_RELATIVE.as_posix(),
        )
    if runtime_candidate is not None and not re.fullmatch(
        r"[0-9a-f]{40}", runtime_candidate
    ):
        result.add(
            "ledger.runtime_candidate_format",
            "Runtime candidate must be one lowercase 40-character Git object id",
            LEDGER_RELATIVE.as_posix(),
        )
    matrix_path = (
        context.mod_root
        / "tools"
        / "jxp_runtime_acceptance"
        / "runtime_scenarios.json"
    )
    if runtime_matrix_sha256 is not None and not re.fullmatch(
        r"[0-9a-f]{64}", runtime_matrix_sha256
    ):
        result.add(
            "ledger.runtime_matrix_hash_format",
            "Runtime matrix SHA-256 must be one lowercase 64-character digest",
            LEDGER_RELATIVE.as_posix(),
        )
    elif not matrix_path.is_file():
        result.add(
            "ledger.runtime_matrix_missing",
            "runtime matrix referenced by the ledger is missing",
            matrix_path.as_posix(),
        )
    elif sha256(matrix_path.read_bytes()).hexdigest() != runtime_matrix_sha256:
        result.add(
            "ledger.runtime_matrix_hash_drift",
            "Runtime matrix SHA-256 does not match runtime_scenarios.json",
            matrix_path.as_posix(),
        )
    if host_portability is not None and host_portability not in ALLOWED_HOST_PORTABILITY:
        result.add(
            "ledger.host_portability_status",
            f"unsupported host portability status {host_portability!r}",
            LEDGER_RELATIVE.as_posix(),
        )
    if r5_fixture_status is not None and r5_fixture_status not in ALLOWED_R5_FIXTURE_STATUSES:
        result.add(
            "ledger.r5_fixture_status",
            f"unsupported R5 fixture status {r5_fixture_status!r}",
            LEDGER_RELATIVE.as_posix(),
        )
    if matrix_blockers is not None and matrix_blockers not in ALLOWED_MATRIX_BLOCKER_STATES:
        result.add(
            "ledger.matrix_blocker_status",
            f"unsupported runtime matrix blocker state {matrix_blockers!r}",
            LEDGER_RELATIVE.as_posix(),
        )
    if next_executable_step is not None and next_executable_step not in ALLOWED_NEXT_STEPS:
        result.add(
            "ledger.next_step_status",
            f"unsupported next executable step {next_executable_step!r}",
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
    if runtime_status not in ALLOWED_RUNTIME_STATUSES:
        result.add(
            "ledger.runtime_status",
            f"unsupported runtime acceptance status {runtime_status!r}",
            LEDGER_RELATIVE.as_posix(),
        )
    elif runtime_status == "AUTHORIZED_NOT_STARTED" and not re.search(
        r"Launch authorization:\s*`EXPLICIT_SINGLE_LAUNCH_AUTHORIZED_\d{4}-\d{2}-\d{2}`",
        text,
    ):
        result.add(
            "ledger.runtime_authorization_missing",
            "AUTHORIZED_NOT_STARTED requires a dated explicit single-launch authorization",
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

    active_todo_ids = {
        todo_id
        for todo_id, _priority, status, _owner, _scope, _task, _evidence in todo_rows
        if status in {"OPEN", "IN_PROGRESS", "BLOCKED"}
    }
    expected_runtime_phases: dict[str, set[str]] = {}
    if matrix_path.is_file():
        try:
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            result.add(
                "ledger.runtime_matrix_parse",
                f"could not parse runtime matrix for TODO closure mapping: {exc}",
                matrix_path.as_posix(),
            )
        else:
            scenarios = matrix.get("scenarios") if isinstance(matrix, dict) else None
            if not isinstance(scenarios, list):
                result.add(
                    "ledger.runtime_matrix_scenarios",
                    "runtime matrix has no scenarios list for TODO closure mapping",
                    matrix_path.as_posix(),
                )
            else:
                for scenario in scenarios:
                    if not isinstance(scenario, dict):
                        continue
                    scenario_id = scenario.get("id")
                    scenario_todos = scenario.get("todos")
                    if not isinstance(scenario_id, str) or not re.fullmatch(
                        r"R(?:[1-9]|1[0-3])", scenario_id
                    ):
                        continue
                    if not isinstance(scenario_todos, list):
                        continue
                    for todo_id in scenario_todos:
                        if isinstance(todo_id, str) and todo_id in active_todo_ids:
                            expected_runtime_phases.setdefault(todo_id, set()).add(
                                scenario_id
                            )

    closure_section = _section(
        text,
        "## Active TODO Runtime Closure Map",
        "## Known Risks",
    )
    closure_rows: dict[str, set[str]] = {}
    for line in closure_section.splitlines():
        if not re.match(r"^\|\s*JXP-\d{3}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            result.add(
                "ledger.runtime_closure_row",
                f"runtime closure row has {len(cells)} columns instead of 4",
                LEDGER_RELATIVE.as_posix(),
            )
            continue
        todo_id = cells[0]
        phases = set(re.findall(r"\bR(?:[1-9]|1[0-3])\b", cells[2]))
        if todo_id in closure_rows:
            result.add(
                "ledger.runtime_closure_duplicate",
                f"runtime closure map repeats {todo_id}",
                LEDGER_RELATIVE.as_posix(),
            )
            continue
        closure_rows[todo_id] = phases

    for todo_id in sorted(active_todo_ids):
        if todo_id not in closure_rows:
            result.add(
                "ledger.runtime_closure_missing",
                f"active TODO is missing from runtime closure map: {todo_id}",
                LEDGER_RELATIVE.as_posix(),
            )
            continue
        expected = expected_runtime_phases.get(todo_id, set())
        if closure_rows[todo_id] != expected:
            result.add(
                "ledger.runtime_closure_phase_drift",
                f"{todo_id} closure phases {sorted(closure_rows[todo_id])} "
                f"do not match matrix {sorted(expected)}",
                LEDGER_RELATIVE.as_posix(),
            )
    for todo_id in sorted(set(closure_rows).difference(active_todo_ids)):
        result.add(
            "ledger.runtime_closure_stale",
            f"runtime closure map contains non-active TODO: {todo_id}",
            LEDGER_RELATIVE.as_posix(),
        )

    external_rows: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        if not line.startswith("| `EXT-R5-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            result.add(
                "ledger.external_evidence_row",
                f"external evidence row has {len(cells)} columns instead of 7",
                LEDGER_RELATIVE.as_posix(),
            )
            continue
        evidence_id = cells[0].strip("`")
        size = cells[4].replace(",", "")
        digest = cells[5].strip("`").casefold()
        state = cells[6].strip("`")
        external_rows.append((evidence_id, size, digest, state))
    external_evidence_ids = [row[0] for row in external_rows]
    for evidence_id, count in Counter(external_evidence_ids).items():
        if count != 1:
            result.add(
                "ledger.external_evidence_duplicate",
                f"external evidence id {evidence_id} occurs {count} times",
                LEDGER_RELATIVE.as_posix(),
            )
    for missing_id in sorted(
        REQUIRED_EXTERNAL_EVIDENCE_IDS.difference(external_evidence_ids)
    ):
        result.add(
            "ledger.external_evidence_missing",
            f"required external evidence entry is missing: {missing_id}",
            LEDGER_RELATIVE.as_posix(),
        )
    for evidence_id, size, digest, state in external_rows:
        expected = EXPECTED_EXTERNAL_EVIDENCE.get(evidence_id)
        if expected is None:
            continue
        if (size, digest, state) != expected:
            result.add(
                "ledger.external_evidence_identity_drift",
                f"{evidence_id} size/hash/state disagrees with the admitted registry",
                LEDGER_RELATIVE.as_posix(),
            )

    r5_source_size = _snapshot_value(text, "R5 source size")
    r5_source_sha256 = _snapshot_value(text, "R5 source SHA-256")
    if r5_source_size != EXPECTED_R5_SIZE:
        result.add(
            "ledger.r5_size_drift",
            f"R5 source size is {r5_source_size!r}; expected {EXPECTED_R5_SIZE}",
            LEDGER_RELATIVE.as_posix(),
        )
    if r5_source_sha256 != EXPECTED_R5_SHA256:
        result.add(
            "ledger.r5_hash_drift",
            "R5 source SHA-256 does not match the escrowed original-machine save",
            LEDGER_RELATIVE.as_posix(),
        )

    journal = _section(text, "## Update Journal", "## Historical Report Index")
    journal_entries = re.findall(
        r"^### (\d{4}-\d{2}-\d{2}) - ([A-Z0-9][A-Z0-9-]*) - ",
        journal,
        re.MULTILINE,
    )
    journal_dates = [date for date, _entry_id in journal_entries]
    journal_ids = [entry_id for _date, entry_id in journal_entries]
    if not journal_entries:
        result.add(
            "ledger.journal_missing",
            "Update Journal has no machine-readable dated entry",
            LEDGER_RELATIVE.as_posix(),
        )
    elif journal_dates != sorted(journal_dates, reverse=True):
        result.add(
            "ledger.journal_order",
            "Update Journal dated entries must remain newest-first",
            LEDGER_RELATIVE.as_posix(),
        )
    if journal_dates and last_updated is not None and journal_dates[0] != last_updated:
        result.add(
            "ledger.journal_snapshot_date",
            "Last updated must match the newest machine-readable journal entry",
            LEDGER_RELATIVE.as_posix(),
        )
    for entry_id, count in Counter(journal_ids).items():
        if count != 1:
            result.add(
                "ledger.journal_duplicate",
                f"Update Journal id {entry_id} occurs {count} times",
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
            "schema": ledger_schema,
            "todo_rows": len(todo_rows),
            "runtime_closure_rows": len(closure_rows),
            "external_evidence_rows": len(external_evidence_ids),
            "journal_entries": len(journal_entries),
            "indexed_reports": indexed_files,
            "main_version": main_version,
            "map_version": map_version,
            "runtime_acceptance": runtime_status,
            "runtime_matrix_sha256": runtime_matrix_sha256,
            "host_portability": host_portability,
            "r5_fixture_status": r5_fixture_status,
            "next_executable_step": next_executable_step,
        }
    )
    result.summary = (
        f"versions {main_version or '<missing>'}/{map_version or '<missing>'}; "
        f"{len(todo_rows)} stable TODOs; {len(closure_rows)} active runtime closure rows; "
        f"{indexed_files} historical reports indexed"
    )
    return result
