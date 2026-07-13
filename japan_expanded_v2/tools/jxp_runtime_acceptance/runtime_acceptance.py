#!/usr/bin/env python3
"""Prepare JXP runtime evidence without launching or configuring EU4.

The CLI deliberately has no launch command and never writes launcher-v2.sqlite
or dlc_load.json.  It installs content-addressed ordinary-directory snapshots,
records a before-session baseline, and collects explicitly generated evidence.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable, Sequence
import uuid
import zipfile


PINNED_LEGACY_REVISION = "8a5962628014e696bda764bcad10bfd3faee188e"
DEFAULT_GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
DEFAULT_USER_DATA = (
    Path.home() / "Documents" / "Paradox Interactive" / "Europa Universalis IV"
)
PROCESS_NAMES = frozenset(
    {
        "eu4.exe",
        "dowser.exe",
        "paradox launcher.exe",
        "bootstrapper-v2.exe",
    }
)
RUNTIME_DIRECTORIES = {
    "main": (
        "common",
        "decisions",
        "events",
        "gfx",
        "history",
        "interface",
        "localisation",
        "missions",
    ),
    "map": (
        "common",
        "decisions",
        "events",
        "gfx",
        "history",
        "interface",
        "localisation",
        "map",
        "missions",
    ),
}
RUNTIME_ROOT_FILES = ("descriptor.mod", "thumbnail.png")
BLOCKER_PATTERNS = {
    "parsing": re.compile(r"Parsing Errors", re.IGNORECASE),
    "unknown_trigger": re.compile(r"Unknown trigger(?: type)?", re.IGNORECASE),
    "unknown_effect": re.compile(r"Unknown effect(?: type)?", re.IGNORECASE),
    "unknown_modifier": re.compile(r"Unknown modifier", re.IGNORECASE),
    "unknown_reform": re.compile(r"Unknown .*reform", re.IGNORECASE),
    "unknown_event": re.compile(r"Unknown .*event", re.IGNORECASE),
    "mission_collision": re.compile(r"mission\.cpp:353", re.IGNORECASE),
    "idea_overflow": re.compile(r"national_idea8", re.IGNORECASE),
    "jxp_error_reference": re.compile(
        r"(?:japan_expanded_v2|\bjxp[_-]).*(?:error|invalid|unknown|failed|not found|duplicate)|"
        r"(?:error|invalid|unknown|failed|not found|duplicate).*(?:japan_expanded_v2|\bjxp[_-])",
        re.IGNORECASE,
    ),
    "map_initialization": re.compile(
        r"(?:map|province|adjacency|strait).*(?:error|invalid|failed)",
        re.IGNORECASE,
    ),
}


class AcceptanceError(RuntimeError):
    """A safe-precondition or evidence-contract failure."""


@dataclass(frozen=True, slots=True)
class Component:
    key: str
    source: Path
    outer_descriptor: Path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _require_ordinary_directory(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise AcceptanceError(f"{label} is not a directory: {resolved}")
    if _is_link_or_junction(path):
        raise AcceptanceError(f"{label} must be an ordinary directory: {path}")
    return resolved


def _descriptor_value(path: Path, key: str) -> str:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"]+)"', text)
    if not match:
        raise AcceptanceError(f"{path} has no quoted {key}")
    return match.group(1)


def _runtime_files(component: Component) -> tuple[Path, ...]:
    if not component.source.is_dir() or _is_link_or_junction(component.source):
        raise AcceptanceError(
            f"{component.key} source must be an ordinary directory: {component.source}"
        )
    if (
        not component.outer_descriptor.is_file()
        or _is_link_or_junction(component.outer_descriptor)
    ):
        raise AcceptanceError(
            f"{component.key} outer descriptor must be an ordinary file: "
            f"{component.outer_descriptor}"
        )
    inner_version = _descriptor_value(component.source / "descriptor.mod", "version")
    outer_version = _descriptor_value(component.outer_descriptor, "version")
    if inner_version != outer_version:
        raise AcceptanceError(
            f"{component.key} descriptor versions disagree: "
            f"inner {inner_version}, outer {outer_version}"
        )
    required_directories = RUNTIME_DIRECTORIES[component.key]
    files: list[Path] = []
    for directory_name in required_directories:
        directory = component.source / directory_name
        if not directory.is_dir():
            raise AcceptanceError(
                f"{component.key} runtime directory is missing: {directory}"
            )
        if _is_link_or_junction(directory):
            raise AcceptanceError(f"runtime source cannot be a link: {directory}")
        for path in sorted(directory.rglob("*")):
            if path.is_dir():
                if _is_link_or_junction(path):
                    raise AcceptanceError(f"runtime source cannot be a link: {path}")
                continue
            if _is_link_or_junction(path):
                raise AcceptanceError(f"runtime source cannot be a link: {path}")
            files.append(path)
    for filename in RUNTIME_ROOT_FILES:
        path = component.source / filename
        if not path.is_file():
            raise AcceptanceError(f"{component.key} runtime file is missing: {path}")
        files.append(path)
    return tuple(sorted(set(files)))


def _manifest(component: Component) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for path in _runtime_files(component):
        records.append(
            {
                "path": path.relative_to(component.source).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return tuple(records)


def _snapshot_fingerprint(
    component: Component,
    manifest: Iterable[dict[str, object]],
    source_revision: str,
) -> str:
    digest = sha256()
    digest.update(component.key.encode("ascii"))
    digest.update(b"\0")
    digest.update(source_revision.encode("utf-8"))
    for record in manifest:
        digest.update(b"\0")
        digest.update(str(record["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
    return digest.hexdigest()


def _sanitize_label(label: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    if not sanitized:
        raise AcceptanceError("deployment label must contain a letter or digit")
    return sanitized[:32]


def _running_eu4_processes() -> tuple[str, ...]:
    if os.name != "nt":
        return ()
    try:
        completed = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AcceptanceError(f"cannot verify EU4/launcher process state: {exc}") from exc
    active = {
        row[0].strip().lower()
        for row in csv.reader(completed.stdout.splitlines())
        if row
    }
    return tuple(sorted(active & PROCESS_NAMES))


def _assert_processes_stopped() -> None:
    active = _running_eu4_processes()
    if active:
        raise AcceptanceError(
            "EU4/launcher processes must be stopped before this write: "
            + ", ".join(active)
        )


def _git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        raise AcceptanceError(f"git {' '.join(args)} failed: {exc}") from exc
    return completed.stdout.strip()


def _current_revision(repo: Path) -> str:
    revision = _git(repo, "rev-parse", "HEAD")
    dirty = bool(_git(repo, "status", "--short"))
    return f"{revision}{'+dirty' if dirty else ''}"


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            relative = PurePosixPath(member.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise AcceptanceError(f"unsafe git archive member: {member.filename}")
            target = destination.joinpath(*relative.parts)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def _revision_components(
    repo: Path, revision: str, temporary_root: Path
) -> tuple[tuple[Component, ...], str]:
    resolved = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    archive = temporary_root / "source.zip"
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "archive",
                "--format=zip",
                f"--output={archive}",
                resolved,
                "japan_expanded_v2",
                "japan_expanded_v2.mod",
            ],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AcceptanceError(f"git archive failed for {resolved}: {exc}") from exc
    _safe_extract_zip(archive, temporary_root / "checkout")
    checkout = temporary_root / "checkout"
    return (
        (
            Component(
                "main",
                checkout / "japan_expanded_v2",
                checkout / "japan_expanded_v2.mod",
            ),
        ),
        resolved,
    )


def _current_components(repo: Path, main_only: bool) -> tuple[Component, ...]:
    components = [
        Component(
            "main", repo / "japan_expanded_v2", repo / "japan_expanded_v2.mod"
        )
    ]
    if not main_only:
        components.append(
            Component(
                "map",
                repo / "japan_expanded_v2_map",
                repo / "japan_expanded_v2_map.mod",
            )
        )
    return tuple(components)


def _build_outer_descriptor(
    component: Component,
    display_name: str,
    folder_name: str,
    dependency_name: str | None,
) -> str:
    version = _descriptor_value(component.source / "descriptor.mod", "version")
    supported = _descriptor_value(
        component.source / "descriptor.mod", "supported_version"
    )
    tag = "Map" if component.key == "map" else "Gameplay"
    lines = [
        f'name="{display_name}"',
        f'version="{version}"',
        'picture="thumbnail.png"',
    ]
    if dependency_name:
        lines.extend(("dependencies={", f'\t"{dependency_name}"', "}"))
    lines.extend(
        (
            "tags={",
            f'\t"{tag}"',
            "}",
            f'supported_version="{supported}"',
            f'path="mod/{folder_name}"',
        )
    )
    return "\n".join(lines) + "\n"


def _verify_installed_manifest(
    target: Path, manifest: Iterable[dict[str, object]]
) -> None:
    for record in manifest:
        path = target / str(record["path"])
        if not path.is_file() or _sha256_file(path) != record["sha256"]:
            raise AcceptanceError(f"installed snapshot verification failed: {path}")


def _deploy_component(
    component: Component,
    mod_dir: Path,
    label: str,
    source_revision: str,
    dependency_name: str | None,
) -> dict[str, object]:
    manifest = _manifest(component)
    fingerprint = _snapshot_fingerprint(component, manifest, source_revision)
    short = fingerprint[:12]
    folder_name = f"jxp-acceptance-{label}-{component.key}-{short}"
    descriptor_name = f"{folder_name}.mod"
    display_name = f"JXP Acceptance {label} {component.key} [{short}]"
    target = mod_dir / folder_name
    marker = target / ".jxp_acceptance_snapshot.json"
    if target.exists():
        if _is_link_or_junction(target) or not marker.is_file():
            raise AcceptanceError(f"refusing unowned or linked target: {target}")
        _verify_installed_manifest(target, manifest)
    else:
        stage = mod_dir / f".jxp-stage-{uuid.uuid4().hex}"
        stage.mkdir()
        try:
            for record in manifest:
                relative = Path(str(record["path"]))
                source = component.source / relative
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            _verify_installed_manifest(stage, manifest)
            (stage / ".jxp_acceptance_snapshot.json").write_text(
                _json_dump(
                    {
                        "schema": 1,
                        "component": component.key,
                        "label": label,
                        "source_revision": source_revision,
                        "fingerprint": fingerprint,
                        "manifest": manifest,
                    }
                ),
                encoding="utf-8",
            )
            stage.rename(target)
        except Exception:
            if stage.exists() and _is_relative_to(stage, mod_dir):
                shutil.rmtree(stage)
            raise
    descriptor_text = _build_outer_descriptor(
        component, display_name, folder_name, dependency_name
    )
    descriptor = mod_dir / descriptor_name
    if descriptor.exists():
        if (
            _is_link_or_junction(descriptor)
            or not descriptor.is_file()
            or descriptor.read_text(encoding="utf-8-sig") != descriptor_text
        ):
            raise AcceptanceError(f"refusing unrelated descriptor target: {descriptor}")
    else:
        descriptor_temp = mod_dir / f".{descriptor_name}.{uuid.uuid4().hex}.tmp"
        descriptor_temp.write_text(descriptor_text, encoding="utf-8")
        os.replace(descriptor_temp, descriptor)
    return {
        "component": component.key,
        "display_name": display_name,
        "version": _descriptor_value(component.source / "descriptor.mod", "version"),
        "source_revision": source_revision,
        "fingerprint": fingerprint,
        "payload": str(target),
        "descriptor": str(descriptor),
        "files": len(manifest),
    }


def deploy(
    repo: Path,
    user_data: Path,
    label: str,
    revision: str | None,
    main_only: bool,
) -> dict[str, object]:
    _assert_processes_stopped()
    repo = _require_ordinary_directory(repo, "repository")
    user_data = _require_ordinary_directory(user_data, "EU4 user-data root")
    mod_dir = user_data / "mod"
    mod_dir.mkdir(exist_ok=True)
    mod_dir = _require_ordinary_directory(mod_dir, "EU4 user mod directory")
    if _is_relative_to(repo, DEFAULT_GAME_ROOT) or _is_relative_to(mod_dir, repo):
        raise AcceptanceError("repository and deployment targets are not safely separated")
    if _is_relative_to(mod_dir, DEFAULT_GAME_ROOT):
        raise AcceptanceError("deployment target must not be inside the EU4 installation")
    safe_label = _sanitize_label(label)
    with tempfile.TemporaryDirectory(prefix="jxp-acceptance-archive-") as temporary:
        if revision:
            if not main_only:
                raise AcceptanceError("git revision deployment is main-only")
            components, source_revision = _revision_components(
                repo, revision, Path(temporary)
            )
        else:
            components = _current_components(repo, main_only)
            source_revision = _current_revision(repo)
        installed: list[dict[str, object]] = []
        main_display_name: str | None = None
        for component in components:
            record = _deploy_component(
                component,
                mod_dir,
                safe_label,
                source_revision,
                main_display_name if component.key == "map" else None,
            )
            installed.append(record)
            if component.key == "main":
                main_display_name = str(record["display_name"])
    return {
        "status": "deployed_not_enabled",
        "installed": installed,
        "launcher_configuration_modified": False,
        "game_started": False,
        "instruction": (
            "Use the launcher UI to create an isolated playset. Exclude Graphical "
            "Map Improvements and every unrelated mod."
        ),
    }


def _load_pin_manifest(repo: Path) -> dict[str, object]:
    path = (
        repo
        / "japan_expanded_v2"
        / "tools"
        / "jxp_validation"
        / "vanilla_1_37_5_manifest.json"
    )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceError(f"cannot read pinned vanilla manifest: {exc}") from exc


def _enabled_mods(user_data: Path) -> tuple[str, ...]:
    path = user_data / "dlc_load.json"
    if not path.is_file():
        return ()
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return tuple(str(item) for item in value.get("enabled_mods", ()))
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        raise AcceptanceError(f"cannot read dlc_load.json: {exc}") from exc


def _dlc_load(user_data: Path) -> dict[str, object]:
    path = user_data / "dlc_load.json"
    if not path.is_file():
        raise AcceptanceError(f"dlc_load.json is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceError(f"cannot read dlc_load.json: {exc}") from exc
    if not isinstance(value, dict):
        raise AcceptanceError("dlc_load.json must contain an object")
    return value


def preflight(repo: Path, game_root: Path, user_data: Path) -> dict[str, object]:
    repo = _require_ordinary_directory(repo, "repository")
    game_root = _require_ordinary_directory(game_root, "EU4 game root")
    user_data = _require_ordinary_directory(user_data, "EU4 user-data root")
    if _is_relative_to(repo, game_root):
        raise AcceptanceError("repository must not live inside the EU4 installation")
    manifest = _load_pin_manifest(repo)
    pin_records: list[dict[str, object]] = []
    for group in ("files", "generic_files", "mandate_files"):
        for record in manifest.get(group, []):
            relative = Path(str(record["path"]))
            source = game_root / relative
            actual = _sha256_file(source) if source.is_file() else None
            expected = str(record["sha256"]).lower()
            pin_records.append(
                {
                    "path": relative.as_posix(),
                    "expected": expected,
                    "actual": actual,
                    "matched": actual == expected,
                }
            )
    enabled = _enabled_mods(user_data)
    conflicts = tuple(
        item for item in enabled if "ugc_253263609.mod" in item.lower()
    )
    source_versions = {
        "main": _descriptor_value(repo / "japan_expanded_v2" / "descriptor.mod", "version"),
        "map": _descriptor_value(repo / "japan_expanded_v2_map" / "descriptor.mod", "version"),
    }
    processes = _running_eu4_processes()
    return {
        "ready_for_safe_deploy": all(item["matched"] for item in pin_records)
        and not processes,
        "pinned_game": manifest.get("eu4_display_version"),
        "pinned_files": pin_records,
        "source_versions": source_versions,
        "running_processes": processes,
        "enabled_mods_read_only": enabled,
        "map_conflicts": conflicts,
        "warnings": [
            "Current enabled mods are not changed by this tool.",
            *(
                [
                    "Graphical Map Improvements is enabled in the daily playset; "
                    "exclude it from every JXP map acceptance run."
                ]
                if conflicts
                else []
            ),
        ],
        "launcher_configuration_modified": False,
        "game_started": False,
    }


def _scenario_matrix_path() -> Path:
    return Path(__file__).with_name("runtime_scenarios.json")


def _scenario(scenario_id: str) -> dict[str, object]:
    matrix = json.loads(_scenario_matrix_path().read_text(encoding="utf-8"))
    for scenario in matrix["scenarios"]:
        if scenario["id"] == scenario_id:
            return scenario
    raise AcceptanceError(f"unknown runtime scenario: {scenario_id}")


def _file_record(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": str(path),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": _sha256_file(path),
    }


def before_session(
    user_data: Path,
    scenario_id: str,
    evidence_root: Path | None,
    descriptors: Sequence[Path],
) -> dict[str, object]:
    _assert_processes_stopped()
    user_data = _require_ordinary_directory(user_data, "EU4 user-data root")
    scenario = _scenario(scenario_id)
    root = (evidence_root or user_data / "jxp_runtime_evidence").expanduser().resolve()
    if not _is_relative_to(root, user_data):
        raise AcceptanceError("evidence root must remain inside EU4 user data")
    if root.exists() and _is_link_or_junction(root):
        raise AcceptanceError("evidence root must be an ordinary directory")
    descriptor_records = []
    expected_enabled: set[str] = set()
    for raw in descriptors:
        path = raw.expanduser().resolve()
        if not _is_relative_to(path, user_data / "mod") or not path.is_file():
            raise AcceptanceError(f"descriptor is not an installed user mod: {path}")
        descriptor_records.append(_file_record(path))
        expected_enabled.add(f"mod/{path.name}")
    if not descriptor_records:
        raise AcceptanceError("before-session requires at least one installed descriptor")
    dlc_config = _dlc_load(user_data)
    actual_enabled = {str(item) for item in dlc_config.get("enabled_mods", ())}
    if actual_enabled != expected_enabled:
        raise AcceptanceError(
            "active playset is not isolated to the supplied descriptors; "
            f"expected {sorted(expected_enabled)}, found {sorted(actual_enabled)}"
        )
    root.mkdir(parents=True, exist_ok=True)
    now = _utc_now()
    session = root / (
        f"{now.strftime('%Y%m%dT%H%M%SZ')}_{scenario_id.lower()}_{uuid.uuid4().hex[:8]}"
    )
    session.mkdir()
    before_logs = session / "before" / "logs"
    before_logs.mkdir(parents=True)
    copied_logs: list[dict[str, object]] = []
    logs = user_data / "logs"
    if logs.is_dir():
        for source in sorted(logs.glob("*.log")):
            destination = before_logs / source.name
            shutil.copy2(source, destination)
            copied_logs.append(_file_record(destination))
    watched = []
    for relative in ("dlc_load.json", "launcher-v2.sqlite"):
        path = user_data / relative
        if path.is_file():
            watched.append(_file_record(path))
    record = {
        "schema": 1,
        "scenario": scenario,
        "started_at": now.isoformat(),
        "started_at_ns": int(now.timestamp() * 1_000_000_000),
        "user_data": str(user_data),
        "evidence_root": str(root),
        "descriptors": descriptor_records,
        "dlc_load": dlc_config,
        "configuration_baseline": watched,
        "before_logs": copied_logs,
        "game_started_by_tool": False,
    }
    (session / "session.json").write_text(_json_dump(record), encoding="utf-8")
    return {"session": str(session), "scenario": scenario_id, "game_started": False}


def _copy_artifact(source: Path, destination_root: Path) -> dict[str, object]:
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source.name
    if destination.exists():
        destination = destination_root / f"{source.stem}-{_sha256_file(source)[:8]}{source.suffix}"
    shutil.copy2(source, destination)
    return _file_record(destination)


def _scan_logs(paths: Iterable[Path]) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as exc:
            raise AcceptanceError(f"cannot scan {path}: {exc}") from exc
        for number, line in enumerate(lines, 1):
            for code, pattern in BLOCKER_PATTERNS.items():
                if pattern.search(line):
                    matches.append(
                        {
                            "code": code,
                            "file": path.name,
                            "line": number,
                            "text": line[:500],
                        }
                    )
                    if len(matches) >= 500:
                        return matches
    return matches


def collect(
    session: Path, artifacts: Sequence[Path]
) -> tuple[dict[str, object], bool]:
    _assert_processes_stopped()
    session = _require_ordinary_directory(session, "evidence session")
    session_file = session / "session.json"
    if not session_file.is_file():
        raise AcceptanceError(f"session.json is missing from {session}")
    record = json.loads(session_file.read_text(encoding="utf-8"))
    user_data = Path(record["user_data"]).resolve()
    evidence_root = Path(record["evidence_root"]).resolve()
    if not _is_relative_to(evidence_root, user_data) or not _is_relative_to(
        session, evidence_root
    ):
        raise AcceptanceError("session is outside its recorded user-data evidence root")
    started_at_ns = int(record["started_at_ns"])
    after = session / "after"
    log_root = after / "logs"
    copied_logs: list[dict[str, object]] = []
    log_paths: list[Path] = []
    logs = user_data / "logs"
    if logs.is_dir():
        for source in sorted(logs.glob("*.log")):
            item = _copy_artifact(source, log_root)
            copied_logs.append(item)
            log_paths.append(Path(str(item["path"])))
    copied_artifacts: list[dict[str, object]] = []
    automatic_roots = (
        (user_data / "Screenshots", "screenshots", "*"),
        (user_data / "save games", "saves", "JXP_ACC_*.eu4"),
    )
    for source_root, category, pattern in automatic_roots:
        if not source_root.is_dir():
            continue
        for source in sorted(source_root.glob(pattern)):
            if source.is_file() and source.stat().st_mtime_ns >= started_at_ns:
                copied_artifacts.append(
                    _copy_artifact(source, after / category)
                )
    for raw in artifacts:
        source = raw.expanduser().resolve()
        if not source.is_file() or not _is_relative_to(source, user_data):
            raise AcceptanceError(f"artifact must be a user-data file: {source}")
        copied_artifacts.append(_copy_artifact(source, after / "explicit"))
    blockers = _scan_logs(log_paths)
    copied_log_names = {Path(str(item["path"])).name for item in copied_logs}
    missing_logs = sorted({"error.log", "game.log"} - copied_log_names)
    stale_logs = sorted(
        Path(str(item["path"])).name
        for item in copied_logs
        if int(item["mtime_ns"]) < started_at_ns
    )
    passed_log_scan = not blockers and not missing_logs and not stale_logs
    result = {
        "schema": 1,
        "collected_at": _utc_now().isoformat(),
        "scenario_id": record["scenario"]["id"],
        "logs": copied_logs,
        "artifacts": copied_artifacts,
        "blockers": blockers,
        "missing_required_logs": missing_logs,
        "stale_logs": stale_logs,
        "passed_log_scan": passed_log_scan,
        "claim_limit": (
            "Collection proves only the supplied scenario and artifacts; manual UI "
            "checks remain required by runtime_scenarios.json."
        ),
    }
    (session / "collection.json").write_text(_json_dump(result), encoding="utf-8")
    return result, passed_log_scan


def _common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--user-data", type=Path, default=DEFAULT_USER_DATA)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and collect JXP runtime acceptance without launching EU4"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight")
    _common_paths(preflight_parser)
    preflight_parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)

    deploy_parser = subparsers.add_parser("deploy")
    _common_paths(deploy_parser)
    deploy_parser.add_argument("--label", default="current")
    deploy_parser.add_argument("--revision")
    deploy_parser.add_argument("--main-only", action="store_true")

    before_parser = subparsers.add_parser("before-session")
    before_parser.add_argument("scenario")
    before_parser.add_argument("--user-data", type=Path, default=DEFAULT_USER_DATA)
    before_parser.add_argument("--evidence-root", type=Path)
    before_parser.add_argument("--descriptor", type=Path, action="append", default=[])

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("session", type=Path)
    collect_parser.add_argument("--artifact", type=Path, action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "preflight":
            result = preflight(args.repo, args.game_root, args.user_data)
            success = bool(result["ready_for_safe_deploy"])
        elif args.command == "deploy":
            result = deploy(
                args.repo,
                args.user_data,
                args.label,
                args.revision,
                args.main_only,
            )
            success = True
        elif args.command == "before-session":
            result = before_session(
                args.user_data,
                args.scenario,
                args.evidence_root,
                args.descriptor,
            )
            success = True
        else:
            result, success = collect(args.session, args.artifact)
    except (AcceptanceError, OSError, json.JSONDecodeError) as exc:
        print(_json_dump({"ok": False, "error": str(exc)}), end="", file=sys.stderr)
        return 2
    print(_json_dump({"ok": success, **result}), end="")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
