#!/usr/bin/env python3
"""Prepare JXP runtime evidence without launching EU4.

The CLI deliberately has no launch command and never writes launcher-v2.sqlite.
It installs content-addressed ordinary-directory snapshots, configures only the
isolated acceptance root's dlc_load.json, records a before-session baseline,
and collects explicitly generated evidence.
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
import stat
import subprocess
import sys
import tempfile
from typing import Iterable, Sequence
import uuid
import zipfile


PINNED_LEGACY_REVISION = "8a5962628014e696bda764bcad10bfd3faee188e"
PINNED_PRE_IDENTITY_REVISION = "6e461e2e47a839a77b2e376ce61ceb317d393320"
PINNED_PROTOCOL_FILES = {
    "eu4.exe": "9ad3efe1af169f40ee577f9dae5debbc87af6fb8b5450fb345ebf110dc4d771a",
    "userdir.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}
DEFAULT_GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
DEFAULT_USER_DATA = (
    Path.home() / "Documents" / "Paradox Interactive" / "Europa Universalis IV"
)
DEFAULT_ACCEPTANCE_USER_DATA = Path.home() / "Documents" / "JXP_Acceptance"
RUN_FIXTURE_ROOT = Path(__file__).with_name("run_fixtures")
SNAPSHOT_MARKER_SCHEMA = 1
SESSION_SCHEMA = 3
COLLECTION_SCHEMA = 3
DLC_CONFIG_PATHS = {
    "Mandate of Heaven": "dlc/dlc066_mandate_of_heaven/dlc066.dlc",
}
PROCESS_NAMES = frozenset(
    {
        "eu4.exe",
        "dowser.exe",
        "paradox launcher.exe",
        "bootstrapper-v2.exe",
    }
)
FRESHNESS_CLOCK_SKEW_NS = 2_000_000_000
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
DEVELOPMENT_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".idea",
        ".vscode",
        "__pycache__",
        "preview",
        "previews",
        "source",
        "sources",
    }
)
DEVELOPMENT_DIRECTORY_PREFIXES = ("backup",)
DEVELOPMENT_FILE_SUFFIXES = frozenset(
    {".cs", ".kra", ".md", ".ps1", ".psd", ".py", ".pyc", ".pyo", ".xcf"}
)
BLOCKER_PATTERNS = {
    "parsing": re.compile(r"Parsing Errors", re.IGNORECASE),
    "unknown_trigger": re.compile(r"Unknown trigger(?: type)?", re.IGNORECASE),
    "unknown_effect": re.compile(r"Unknown effect(?: type)?", re.IGNORECASE),
    "unknown_modifier": re.compile(r"Unknown modifier", re.IGNORECASE),
    "unknown_reform": re.compile(r"Unknown .*reform", re.IGNORECASE),
    "unknown_event": re.compile(r"Unknown .*event", re.IGNORECASE),
    "unknown_object": re.compile(
        r"\bUnknown (?:country(?: tag)?|tag|object|idea(?: group)?|mission|decision|"
        r"government|religion|culture|province|sprite|interface|DLC|war goal|casus belli)\b",
        re.IGNORECASE,
    ),
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
    if is_junction and is_junction():
        return True
    if os.name == "nt":
        try:
            attributes = getattr(os.lstat(path), "st_file_attributes", 0)
        except OSError:
            return False
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return bool(attributes & reparse)
    return False


def _is_development_runtime_path(relative: Path) -> bool:
    """Return whether a whitelisted tree member is development-only material."""
    directory_parts = tuple(part.lower() for part in relative.parts[:-1])
    if any(
        part in DEVELOPMENT_DIRECTORY_NAMES
        or part.startswith(DEVELOPMENT_DIRECTORY_PREFIXES)
        for part in directory_parts
    ):
        return True
    return relative.suffix.lower() in DEVELOPMENT_FILE_SUFFIXES


def _require_ordinary_directory(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise AcceptanceError(f"{label} is not a directory: {resolved}")
    if _is_link_or_junction(path):
        raise AcceptanceError(f"{label} must be an ordinary directory: {path}")
    return resolved


def _require_isolated_user_data(path: Path) -> Path:
    resolved = _require_ordinary_directory(path, "EU4 acceptance user-data root")
    if resolved == DEFAULT_USER_DATA.resolve():
        raise AcceptanceError(
            "runtime acceptance must not use the daily EU4 user-data root"
        )
    if not str(resolved).isascii() or re.search(r'[\s"]', str(resolved)):
        raise AcceptanceError(
            "EU4 acceptance user-data path must be ASCII and contain no whitespace "
            "or quote; the pinned executable's option parser can truncate ambiguous "
            "userdir values"
        )
    return resolved


def _require_canonical_fixture_user_data(path: Path) -> Path:
    """Restrict root-level console fixtures to the audited acceptance userdir."""
    resolved = _require_isolated_user_data(path)
    canonical = DEFAULT_ACCEPTANCE_USER_DATA.expanduser().resolve()
    daily = DEFAULT_USER_DATA.expanduser().resolve()
    if resolved != canonical:
        raise AcceptanceError(
            "run fixtures may be installed only in the canonical acceptance "
            f"user-data root: {canonical}"
        )
    if _is_relative_to(resolved, daily) or _is_relative_to(daily, resolved):
        raise AcceptanceError(
            "run-fixture root must not contain or be contained by daily user data"
        )
    if (
        resolved.name.lower().startswith("jxp-acceptance-")
        or os.path.lexists(resolved / ".jxp_acceptance_snapshot.json")
        or os.path.lexists(resolved / "descriptor.mod")
    ):
        raise AcceptanceError(
            "run-fixture root resembles a mod payload rather than a user-data root"
        )
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
            if _is_development_runtime_path(path.relative_to(component.source)):
                continue
            files.append(path)
    for filename in RUNTIME_ROOT_FILES:
        path = component.source / filename
        if not path.is_file() or _is_link_or_junction(path):
            raise AcceptanceError(
                f"{component.key} runtime file must be an ordinary file: {path}"
            )
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


def _normalized_manifest_record(record: object) -> tuple[str, int, str]:
    """Validate one marker record without allowing Windows path escape."""
    if not isinstance(record, dict) or set(record) != {"path", "bytes", "sha256"}:
        raise AcceptanceError("acceptance snapshot manifest record schema disagrees")
    raw_path = record["path"]
    size = record["bytes"]
    digest = record["sha256"]
    if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
        raise AcceptanceError(f"unsafe snapshot manifest path: {raw_path!r}")
    relative = PurePosixPath(raw_path)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or raw_path != relative.as_posix()
        or relative.name == ".jxp_acceptance_snapshot.json"
        or any(":" in part for part in relative.parts)
        or _is_development_runtime_path(Path(*relative.parts))
    ):
        raise AcceptanceError(f"unsafe snapshot manifest path: {raw_path!r}")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise AcceptanceError(f"invalid snapshot manifest byte count: {size!r}")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise AcceptanceError(f"invalid snapshot manifest hash: {digest!r}")
    return relative.as_posix(), size, digest


def _snapshot_fingerprint_for_records(
    component_key: str,
    manifest: Iterable[dict[str, object]],
    source_revision: str,
) -> str:
    digest = sha256()
    digest.update(component_key.encode("ascii"))
    digest.update(b"\0")
    digest.update(source_revision.encode("utf-8"))
    for record in manifest:
        normalized, _, record_digest = _normalized_manifest_record(record)
        relative = PurePosixPath(normalized)
        allowed_roots = set(RUNTIME_DIRECTORIES[component_key])
        if not (
            normalized in RUNTIME_ROOT_FILES
            or (len(relative.parts) > 1 and relative.parts[0] in allowed_roots)
        ):
            raise AcceptanceError(
                f"snapshot manifest path is outside the {component_key} runtime whitelist: "
                f"{normalized}"
            )
        digest.update(b"\0")
        digest.update(normalized.encode("utf-8"))
        digest.update(b"\0")
        digest.update(record_digest.encode("ascii"))
    return digest.hexdigest()


def _snapshot_fingerprint(
    component: Component,
    manifest: Iterable[dict[str, object]],
    source_revision: str,
) -> str:
    return _snapshot_fingerprint_for_records(
        component.key, manifest, source_revision
    )


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
            raw_name = member.filename
            normalized_name = (
                raw_name[:-1]
                if member.is_dir() and raw_name.endswith("/")
                else raw_name
            )
            relative = PurePosixPath(normalized_name)
            if (
                not normalized_name
                or "\\" in normalized_name
                or relative.is_absolute()
                or ".." in relative.parts
                or normalized_name != relative.as_posix()
                or any(":" in part for part in relative.parts)
            ):
                raise AcceptanceError(f"unsafe git archive member: {member.filename}")
            target = destination.joinpath(*relative.parts)
            if not _is_relative_to(target, destination):
                raise AcceptanceError(f"git archive member escaped target: {member.filename}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def _revision_components(
    repo: Path, revision: str, temporary_root: Path, main_only: bool
) -> tuple[tuple[Component, ...], str]:
    resolved = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    archive = temporary_root / "source.zip"
    archive_paths = ["japan_expanded_v2", "japan_expanded_v2.mod"]
    if not main_only:
        archive_paths.extend(["japan_expanded_v2_map", "japan_expanded_v2_map.mod"])
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
                *archive_paths,
            ],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AcceptanceError(f"git archive failed for {resolved}: {exc}") from exc
    _safe_extract_zip(archive, temporary_root / "checkout")
    checkout = temporary_root / "checkout"
    components = [
        Component(
            "main",
            checkout / "japan_expanded_v2",
            checkout / "japan_expanded_v2.mod",
        )
    ]
    if not main_only:
        components.append(
            Component(
                "map",
                checkout / "japan_expanded_v2_map",
                checkout / "japan_expanded_v2_map.mod",
            )
        )
    return (
        tuple(components),
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
    expected: dict[str, dict[str, object]] = {}
    for record in manifest:
        normalized, expected_size, expected_digest = _normalized_manifest_record(record)
        relative = PurePosixPath(normalized)
        if normalized in expected:
            raise AcceptanceError(f"duplicate snapshot manifest path: {normalized}")
        expected[normalized] = record
        path = target.joinpath(*relative.parts)
        if not _is_relative_to(path, target):
            raise AcceptanceError(f"snapshot manifest path escaped target: {normalized}")
        if (
            not path.is_file()
            or _is_link_or_junction(path)
            or path.stat().st_size != expected_size
            or _sha256_file(path) != expected_digest
        ):
            raise AcceptanceError(f"installed snapshot verification failed: {path}")

    actual: set[str] = set()
    for path in sorted(target.rglob("*")):
        if _is_link_or_junction(path):
            raise AcceptanceError(f"installed snapshot cannot contain a link: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(target).as_posix()
        if relative == ".jxp_acceptance_snapshot.json":
            continue
        actual.add(relative)
    unexpected = sorted(actual - set(expected))
    missing = sorted(set(expected) - actual)
    if unexpected or missing:
        raise AcceptanceError(
            "installed snapshot file set disagrees with its manifest; "
            f"unexpected={unexpected[:10]}, missing={missing[:10]}"
        )


def _snapshot_marker_value(
    component: Component,
    label: str,
    source_revision: str,
    fingerprint: str,
    manifest: Iterable[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": SNAPSHOT_MARKER_SCHEMA,
        "component": component.key,
        "label": label,
        "source_revision": source_revision,
        "fingerprint": fingerprint,
        "manifest": list(manifest),
    }


def _verify_snapshot_marker(
    marker: Path, expected: dict[str, object]
) -> None:
    try:
        actual = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceError(f"cannot read acceptance snapshot marker {marker}: {exc}") from exc
    if actual != expected:
        raise AcceptanceError(f"acceptance snapshot marker metadata disagrees: {marker}")


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
    marker_value = _snapshot_marker_value(
        component, label, source_revision, fingerprint, manifest
    )
    if target.exists():
        if _is_link_or_junction(target) or not marker.is_file():
            raise AcceptanceError(f"refusing unowned or linked target: {target}")
        _verify_snapshot_marker(marker, marker_value)
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
                _json_dump(marker_value), encoding="utf-8"
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
    user_data = _require_isolated_user_data(user_data)
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
            components, source_revision = _revision_components(
                repo, revision, Path(temporary), main_only
            )
        else:
            components = _current_components(repo, main_only)
            source_revision = _current_revision(repo)
        if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
            raise AcceptanceError(
                "deployment requires a clean committed source revision; "
                f"found {source_revision!r}"
            )
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
            "Run configure-playset for the intended scenario and these exact "
            "descriptors. After explicit startup permission, prove the pinned "
            "EU4 userdir protocol; never use the daily Launcher configuration."
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
    for key in ("enabled_mods", "disabled_dlcs"):
        items = value.get(key)
        if (
            not isinstance(items, list)
            or not all(isinstance(item, str) and item for item in items)
            or len(items) != len(set(items))
        ):
            raise AcceptanceError(f"dlc_load.json {key} must be a unique string list")
    return value


def _descriptor_dependencies(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(r"(?ms)^\s*dependencies\s*=\s*\{(.*?)^\s*\}", text)
    if not match:
        return ()
    return tuple(re.findall(r'"([^"]+)"', match.group(1)))


def _installed_snapshot_record(descriptor: Path, user_data: Path) -> dict[str, object]:
    """Verify and describe one immutable acceptance snapshot selected for a run."""
    mod_dir = (user_data / "mod").resolve()
    descriptor = descriptor.expanduser().resolve()
    if not _is_relative_to(descriptor, mod_dir) or not descriptor.is_file():
        raise AcceptanceError(f"descriptor is not an installed user mod: {descriptor}")
    if _is_link_or_junction(descriptor):
        raise AcceptanceError(f"acceptance descriptor cannot be a link: {descriptor}")

    relative_payload = PurePosixPath(_descriptor_value(descriptor, "path"))
    if (
        relative_payload.is_absolute()
        or ".." in relative_payload.parts
        or len(relative_payload.parts) != 2
        or relative_payload.parts[0].lower() != "mod"
    ):
        raise AcceptanceError(
            f"acceptance descriptor has an unsafe or noncanonical path: {descriptor}"
        )
    payload = user_data.joinpath(*relative_payload.parts).resolve()
    if (
        not _is_relative_to(payload, mod_dir)
        or not payload.is_dir()
        or _is_link_or_junction(payload)
    ):
        raise AcceptanceError(f"acceptance payload is not an ordinary mod directory: {payload}")

    marker = payload / ".jxp_acceptance_snapshot.json"
    try:
        marker_value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceError(f"cannot read acceptance snapshot marker {marker}: {exc}") from exc
    required_marker_keys = {
        "schema",
        "component",
        "label",
        "source_revision",
        "fingerprint",
        "manifest",
    }
    if not isinstance(marker_value, dict) or set(marker_value) != required_marker_keys:
        raise AcceptanceError(f"acceptance snapshot marker schema disagrees: {marker}")
    component = marker_value["component"]
    label = marker_value["label"]
    source_revision = marker_value["source_revision"]
    fingerprint = marker_value["fingerprint"]
    manifest = marker_value["manifest"]
    if not isinstance(component, str) or component not in RUNTIME_DIRECTORIES:
        raise AcceptanceError(f"unknown acceptance snapshot component: {component}")
    if not isinstance(label, str) or _sanitize_label(label) != label:
        raise AcceptanceError(f"invalid acceptance snapshot label: {label!r}")
    if marker_value["schema"] != SNAPSHOT_MARKER_SCHEMA or not isinstance(manifest, list):
        raise AcceptanceError(f"acceptance snapshot marker contents disagree: {marker}")
    if not isinstance(source_revision, str) or not re.fullmatch(
        r"[0-9a-f]{40}", source_revision
    ):
        raise AcceptanceError(
            f"runtime evidence requires a clean committed source revision: {source_revision!r}"
        )
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise AcceptanceError(f"invalid acceptance snapshot fingerprint: {fingerprint!r}")
    recomputed = _snapshot_fingerprint_for_records(component, manifest, source_revision)
    if fingerprint != recomputed:
        raise AcceptanceError(f"acceptance snapshot fingerprint disagrees: {payload}")
    short = fingerprint[:12]
    expected_folder = f"jxp-acceptance-{label}-{component}-{short}"
    if payload.name != expected_folder or descriptor.name != f"{expected_folder}.mod":
        raise AcceptanceError(
            "acceptance snapshot path does not match its marker identity: "
            f"{descriptor}"
        )
    _verify_installed_manifest(payload, manifest)

    inner = payload / "descriptor.mod"
    inner_version = _descriptor_value(inner, "version")
    outer_version = _descriptor_value(descriptor, "version")
    if inner_version != outer_version:
        raise AcceptanceError(
            f"installed descriptor versions disagree: inner {inner_version}, outer {outer_version}"
        )
    dependencies = _descriptor_dependencies(descriptor)
    if component == "main" and dependencies:
        raise AcceptanceError("main acceptance descriptor must have no dependencies")
    if component == "map" and len(dependencies) != 1:
        raise AcceptanceError("map acceptance descriptor must have exactly one dependency")
    display_name = f"JXP Acceptance {label} {component} [{short}]"
    expected_descriptor = _build_outer_descriptor(
        Component(component, payload, descriptor),
        display_name,
        expected_folder,
        dependencies[0] if dependencies else None,
    )
    if descriptor.read_text(encoding="utf-8-sig") != expected_descriptor:
        raise AcceptanceError(f"acceptance outer descriptor contents disagree: {descriptor}")
    return {
        "component": component,
        "display_name": display_name,
        "version": outer_version,
        "source_revision": source_revision,
        "fingerprint": fingerprint,
        "files": len(manifest),
        "payload": str(payload),
        "payload_marker": _file_record(marker),
        "descriptor": _file_record(descriptor),
        "dependencies": list(dependencies),
    }


def _scenario_session_contract(
    scenario: dict[str, object], phase: str | None
) -> tuple[dict[str, object], str | None]:
    phases = scenario.get("session_phases")
    if phases:
        if not isinstance(phases, dict) or not phase or phase not in phases:
            choices = sorted(phases) if isinstance(phases, dict) else []
            raise AcceptanceError(
                f"{scenario['id']} requires --phase chosen from {choices}"
            )
        contract = phases[phase]
        if not isinstance(contract, dict):
            raise AcceptanceError(f"invalid session phase contract: {scenario['id']} {phase}")
        return contract, phase
    if phase:
        raise AcceptanceError(f"{scenario['id']} does not define session phases")
    contract = scenario.get("session_contract", {})
    if not isinstance(contract, dict):
        raise AcceptanceError(f"invalid session contract: {scenario['id']}")
    return contract, None


def _verify_session_snapshot_contract(
    scenario: dict[str, object],
    phase: str | None,
    snapshots: Sequence[dict[str, object]],
    candidate_revision: str,
) -> str | None:
    contract, selected_phase = _scenario_session_contract(scenario, phase)
    by_component: dict[str, dict[str, object]] = {}
    for snapshot in snapshots:
        component = str(snapshot["component"])
        if component in by_component:
            raise AcceptanceError(f"duplicate acceptance component in playset: {component}")
        by_component[component] = snapshot
    required = set(str(item) for item in contract.get("required_components", ()))
    if required and set(by_component) != required:
        raise AcceptanceError(
            f"{scenario['id']} snapshot components disagree; "
            f"expected {sorted(required)}, found {sorted(by_component)}"
        )
    versions = contract.get("required_versions", {})
    if not isinstance(versions, dict):
        raise AcceptanceError(f"invalid required_versions contract: {scenario['id']}")
    for component, expected in versions.items():
        actual = by_component.get(str(component), {}).get("version")
        if actual != expected:
            raise AcceptanceError(
                f"{scenario['id']} {component} version disagrees; "
                f"expected {expected}, found {actual}"
            )
    revisions = contract.get("required_source_revisions", {})
    if not isinstance(revisions, dict):
        raise AcceptanceError(
            f"invalid required_source_revisions contract: {scenario['id']}"
        )
    unknown_revision_components = set(str(item) for item in revisions) - set(
        by_component
    )
    if unknown_revision_components:
        raise AcceptanceError(
            f"{scenario['id']} revision contract names absent components: "
            f"{sorted(unknown_revision_components)}"
        )
    for component, snapshot in by_component.items():
        expected = revisions.get(component, candidate_revision)
        actual = snapshot.get("source_revision")
        if actual != expected:
            raise AcceptanceError(
                f"{scenario['id']} {component} source revision disagrees; "
                f"expected {expected}, found {actual}"
            )
    if "main" in by_component and by_component["main"]["dependencies"]:
        raise AcceptanceError("main acceptance descriptor must have no dependencies")
    if "map" in by_component:
        main_name = by_component.get("main", {}).get("display_name")
        if by_component["map"]["dependencies"] != [main_name]:
            raise AcceptanceError(
                "map acceptance descriptor must depend on the exact selected main snapshot"
            )
    return selected_phase


def _required_disabled_dlcs(
    scenario: dict[str, object], phase: str | None
) -> tuple[str, ...]:
    contract, _ = _scenario_session_contract(scenario, phase)
    required = contract.get("required_runtime_dlc", {})
    if not isinstance(required, dict):
        raise AcceptanceError(f"invalid required_runtime_dlc contract: {scenario['id']}")
    disabled: list[str] = []
    for name, state in required.items():
        path = DLC_CONFIG_PATHS.get(str(name))
        if not path:
            raise AcceptanceError(f"no pinned dlc_load path for required DLC: {name}")
        normalized_state = str(state).casefold()
        if normalized_state == "disabled":
            disabled.append(path)
        elif normalized_state != "enabled":
            raise AcceptanceError(
                f"invalid runtime DLC state for {name}: {state!r}"
            )
    return tuple(sorted(disabled))


def _verified_session_snapshots(
    user_data: Path, descriptors: Sequence[Path]
) -> list[dict[str, object]]:
    records = [
        _installed_snapshot_record(raw.expanduser().resolve(), user_data)
        for raw in descriptors
    ]
    if not records:
        raise AcceptanceError("scenario configuration requires at least one descriptor")
    return records


def configure_playset(
    user_data: Path,
    scenario_id: str,
    phase: str | None,
    descriptors: Sequence[Path],
    candidate_revision: str | None = None,
) -> dict[str, object]:
    """Atomically configure only an isolated acceptance root for one scenario."""
    _assert_processes_stopped()
    user_data = _require_isolated_user_data(user_data)
    scenario = _scenario(scenario_id)
    if scenario_id == "R13":
        raise AcceptanceError("R13 is release closure and has no runtime playset")
    candidate_revision = candidate_revision or _current_candidate_revision()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_revision):
        raise AcceptanceError(
            f"invalid current candidate revision: {candidate_revision!r}"
        )
    snapshots = _verified_session_snapshots(user_data, descriptors)
    selected_phase = _verify_session_snapshot_contract(
        scenario, phase, snapshots, candidate_revision
    )
    ordered = sorted(
        snapshots,
        key=lambda item: ({"main": 0, "map": 1}.get(str(item["component"]), 99)),
    )
    config = {
        "enabled_mods": [
            f"mod/{Path(str(item['descriptor']['path'])).name}" for item in ordered
        ],
        "disabled_dlcs": list(_required_disabled_dlcs(scenario, selected_phase)),
    }
    target = user_data / "dlc_load.json"
    previous = None
    if target.exists():
        if not target.is_file() or _is_link_or_junction(target):
            raise AcceptanceError(f"refusing non-ordinary dlc_load target: {target}")
        _dlc_load(user_data)
        previous = _file_record(target)
    temporary = user_data / f".dlc_load.{uuid.uuid4().hex}.tmp"
    try:
        temporary.write_text(_json_dump(config), encoding="utf-8")
        if json.loads(temporary.read_text(encoding="utf-8")) != config:
            raise AcceptanceError("isolated dlc_load write verification failed")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "scenario": scenario_id,
        "phase": selected_phase,
        "user_data": str(user_data),
        "candidate_revision": candidate_revision,
        "configuration": config,
        "previous_dlc_load": previous,
        "dlc_load": _file_record(target),
        "snapshots": [
            {
                key: item[key]
                for key in (
                    "component",
                    "version",
                    "source_revision",
                    "fingerprint",
                    "display_name",
                )
            }
            for item in ordered
        ],
        "daily_launcher_configuration_modified": False,
        "game_started": False,
    }


def preflight(repo: Path, game_root: Path, user_data: Path) -> dict[str, object]:
    repo = _require_ordinary_directory(repo, "repository")
    game_root = _require_ordinary_directory(game_root, "EU4 game root")
    user_data = _require_ordinary_directory(user_data, "EU4 user-data root")
    if _is_relative_to(repo, game_root):
        raise AcceptanceError("repository must not live inside the EU4 installation")
    manifest = _load_pin_manifest(repo)
    pin_records: list[dict[str, object]] = []
    for relative_value, expected in PINNED_PROTOCOL_FILES.items():
        relative = Path(relative_value)
        source = game_root / relative
        actual = _sha256_file(source) if source.is_file() else None
        pin_records.append(
            {
                "path": relative.as_posix(),
                "expected": expected,
                "actual": actual,
                "matched": actual == expected,
            }
        )
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


def _scenario_matrix() -> dict[str, object]:
    value = json.loads(_scenario_matrix_path().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AcceptanceError("runtime scenario matrix must contain an object")
    return value


def _current_candidate_revision() -> str:
    value = _scenario_matrix().get("current_candidate_revision")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise AcceptanceError(
            "runtime matrix has no pinned 40-character current candidate revision"
        )
    return value


def _scenario(scenario_id: str) -> dict[str, object]:
    matrix = _scenario_matrix()
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


def _required_configuration_records(root: Path) -> list[dict[str, object]]:
    records = []
    for relative in ("dlc_load.json", "launcher-v2.sqlite"):
        path = root / relative
        if not path.is_file() or _is_link_or_junction(path):
            raise AcceptanceError(f"required ordinary configuration file is missing: {path}")
        records.append(_file_record(path))
    return records


def _verified_run_fixture_records() -> list[dict[str, object]]:
    manifest_path = RUN_FIXTURE_ROOT / "manifest.json"
    if not manifest_path.is_file() or _is_link_or_junction(manifest_path):
        raise AcceptanceError(f"run-fixture manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema", "claim_limit", "files"}
        or manifest["schema"] != 1
        or not isinstance(manifest["claim_limit"], str)
        or not isinstance(manifest["files"], list)
        or not manifest["files"]
    ):
        raise AcceptanceError("run-fixture manifest schema disagrees with this helper")
    records: list[dict[str, object]] = []
    names: set[str] = set()
    for item in manifest["files"]:
        if not isinstance(item, dict) or set(item) != {
            "name",
            "scenario",
            "purpose",
            "bytes",
            "sha256",
        }:
            raise AcceptanceError("run-fixture manifest entry is malformed")
        name = item["name"]
        scenario = item["scenario"]
        purpose = item["purpose"]
        expected_bytes = item["bytes"]
        expected_digest = item["sha256"]
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"JXP_ACC_R(?:4|6|8|10)_[A-Za-z0-9_]+\.txt", name)
            or name in names
            or not isinstance(scenario, str)
            or scenario not in {"R4", "R6", "R8", "R10"}
            or not isinstance(purpose, str)
            or not purpose
            or isinstance(expected_bytes, bool)
            or not isinstance(expected_bytes, int)
            or expected_bytes <= 0
            or not isinstance(expected_digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_digest)
        ):
            raise AcceptanceError("run-fixture manifest entry has invalid fields")
        source = (RUN_FIXTURE_ROOT / name).resolve()
        if (
            source.parent != RUN_FIXTURE_ROOT.resolve()
            or not source.is_file()
            or _is_link_or_junction(source)
        ):
            raise AcceptanceError(f"run fixture is missing or not ordinary: {source}")
        payload = source.read_bytes()
        try:
            payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AcceptanceError(f"run fixture is not UTF-8: {source}: {exc}") from exc
        if payload.startswith(b"\xef\xbb\xbf"):
            raise AcceptanceError(f"run fixture must not contain a UTF-8 BOM: {source}")
        actual = _file_record(source)
        if (
            actual["bytes"] != expected_bytes
            or actual["sha256"] != expected_digest
        ):
            raise AcceptanceError(f"run fixture disagrees with its manifest: {source}")
        names.add(name)
        records.append(
            {
                **item,
                "source": str(source),
                "claim_limit": manifest["claim_limit"],
            }
        )
    return records


def install_run_fixtures(user_data: Path) -> dict[str, object]:
    """Install immutable non-release console setup effects into safe userdir."""
    _assert_processes_stopped()
    user_data = _require_canonical_fixture_user_data(user_data)
    fixtures = _verified_run_fixture_records()
    plan: list[tuple[dict[str, object], Path, bool]] = []
    for fixture in fixtures:
        source = Path(str(fixture["source"]))
        destination = user_data / str(fixture["name"])
        reused = False
        if os.path.lexists(destination):
            if not destination.is_file() or _is_link_or_junction(destination):
                raise AcceptanceError(
                    f"refusing non-ordinary run-fixture target: {destination}"
                )
            if (
                destination.stat().st_size != fixture["bytes"]
                or _sha256_file(destination) != fixture["sha256"]
            ):
                raise AcceptanceError(
                    f"refusing to overwrite different run fixture: {destination}"
                )
            reused = True
        plan.append((fixture, destination, reused))

    staged: dict[Path, Path] = {}
    committed: list[tuple[dict[str, object], Path]] = []
    try:
        for fixture, destination, reused in plan:
            if reused:
                continue
            source = Path(str(fixture["source"]))
            temporary = user_data / f".{destination.name}.{uuid.uuid4().hex}.tmp"
            staged[destination] = temporary
            shutil.copy2(source, temporary)
            if (
                temporary.stat().st_size != fixture["bytes"]
                or _sha256_file(temporary) != fixture["sha256"]
            ):
                raise AcceptanceError(
                    f"run-fixture copy verification failed: {destination}"
                )

        for fixture, destination, reused in plan:
            if reused:
                continue
            temporary = staged[destination]
            try:
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise AcceptanceError(
                    f"run-fixture target appeared during commit: {destination}"
                ) from exc
            committed.append((fixture, destination))
            temporary.unlink()

        installed: list[dict[str, object]] = []
        for fixture, destination, reused in plan:
            installed.append(
                {
                    "name": fixture["name"],
                    "scenario": fixture["scenario"],
                    "purpose": fixture["purpose"],
                    "claim_limit": fixture["claim_limit"],
                    "reused": reused,
                    **_file_record(destination),
                }
            )
    except Exception:
        for fixture, destination in reversed(committed):
            if (
                destination.is_file()
                and not _is_link_or_junction(destination)
                and destination.stat().st_size == fixture["bytes"]
                and _sha256_file(destination) == fixture["sha256"]
            ):
                destination.unlink()
        raise
    finally:
        for temporary in staged.values():
            if os.path.lexists(temporary):
                temporary.unlink()
    return {
        "status": "debug_fixture_setup_installed",
        "user_data": str(user_data),
        "installed": installed,
        "daily_launcher_configuration_modified": False,
        "game_started": False,
    }


def before_session(
    user_data: Path,
    scenario_id: str,
    phase: str | None,
    evidence_root: Path | None,
    descriptors: Sequence[Path],
    candidate_revision: str | None = None,
    daily_user_data: Path | None = None,
) -> dict[str, object]:
    _assert_processes_stopped()
    user_data = _require_isolated_user_data(user_data)
    daily_user_data = _require_ordinary_directory(
        daily_user_data or DEFAULT_USER_DATA, "daily EU4 user-data root"
    )
    if daily_user_data == user_data:
        raise AcceptanceError("daily and acceptance user-data roots must be distinct")
    scenario = _scenario(scenario_id)
    if scenario_id == "R13":
        raise AcceptanceError("R13 is release closure and cannot create a game session")
    candidate_revision = candidate_revision or _current_candidate_revision()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_revision):
        raise AcceptanceError(
            f"invalid current candidate revision: {candidate_revision!r}"
        )
    root = (evidence_root or user_data / "jxp_runtime_evidence").expanduser().resolve()
    if not _is_relative_to(root, user_data):
        raise AcceptanceError("evidence root must remain inside EU4 user data")
    if root.exists() and _is_link_or_junction(root):
        raise AcceptanceError("evidence root must be an ordinary directory")
    snapshot_records = _verified_session_snapshots(user_data, descriptors)
    expected_enabled = {
        f"mod/{Path(str(item['descriptor']['path'])).name}"
        for item in snapshot_records
    }
    selected_phase = _verify_session_snapshot_contract(
        scenario, phase, snapshot_records, candidate_revision
    )
    dlc_config = _dlc_load(user_data)
    actual_enabled = {str(item) for item in dlc_config.get("enabled_mods", ())}
    if actual_enabled != expected_enabled:
        raise AcceptanceError(
            "active playset is not isolated to the supplied descriptors; "
            f"expected {sorted(expected_enabled)}, found {sorted(actual_enabled)}"
        )
    expected_disabled = set(_required_disabled_dlcs(scenario, selected_phase))
    actual_disabled = {str(item) for item in dlc_config["disabled_dlcs"]}
    if actual_disabled != expected_disabled:
        raise AcceptanceError(
            "isolated DLC mask disagrees with the scenario contract; "
            f"expected {sorted(expected_disabled)}, found {sorted(actual_disabled)}"
        )
    root.mkdir(parents=True, exist_ok=True)
    now = _utc_now()
    phase_suffix = f"_{selected_phase}" if selected_phase else ""
    session = root / (
        f"{now.strftime('%Y%m%dT%H%M%SZ')}_{scenario_id.lower()}"
        f"{phase_suffix}_{uuid.uuid4().hex[:8]}"
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
    daily_watched = _required_configuration_records(daily_user_data)
    record = {
        "schema": SESSION_SCHEMA,
        "scenario": scenario,
        "phase": selected_phase,
        "candidate_revision": candidate_revision,
        "started_at": now.isoformat(),
        "started_at_ns": int(now.timestamp() * 1_000_000_000),
        "user_data": str(user_data),
        "daily_user_data": str(daily_user_data),
        "evidence_root": str(root),
        "snapshots": snapshot_records,
        "dlc_load": dlc_config,
        "configuration_baseline": watched,
        "daily_configuration_baseline": daily_watched,
        "before_logs": copied_logs,
        "game_started_by_tool": False,
    }
    (session / "session.json").write_text(_json_dump(record), encoding="utf-8")
    return {
        "session": str(session),
        "scenario": scenario_id,
        "phase": selected_phase,
        "game_started": False,
    }


def _copy_artifact(source: Path, destination_root: Path) -> dict[str, object]:
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source.name
    if destination.exists():
        source_digest = _sha256_file(source)
        if _sha256_file(destination) == source_digest:
            return _file_record(destination)
        destination = (
            destination_root / f"{source.stem}-{source_digest[:12]}{source.suffix}"
        )
        if destination.exists():
            if _sha256_file(destination) == source_digest:
                return _file_record(destination)
            raise AcceptanceError(f"artifact destination collision: {destination}")
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


def _runtime_dlc_checks(
    scenario: dict[str, object], phase: str | None, log_paths: Iterable[Path]
) -> list[dict[str, object]]:
    contract, _ = _scenario_session_contract(scenario, phase)
    required = contract.get("required_runtime_dlc", {})
    if not isinstance(required, dict):
        raise AcceptanceError(f"invalid required_runtime_dlc contract: {scenario['id']}")
    game_logs = [path for path in log_paths if path.name.lower() == "game.log"]
    text_value = "\n".join(
        path.read_text(encoding="utf-8-sig", errors="replace") for path in game_logs
    )
    checks = []
    for name, expected_state in required.items():
        pattern = re.compile(
            rf"Setting up DLC\s+{re.escape(str(name))}\s*:\s*"
            r"(Enabled|Disabled)\b",
            re.IGNORECASE,
        )
        observed = pattern.findall(text_value)
        checks.append(
            {
                "dlc": str(name),
                "expected": str(expected_state),
                "observed": observed,
                "matched": bool(observed)
                and all(
                    state.casefold() == str(expected_state).casefold()
                    for state in observed
                ),
            }
        )
    return checks


def _artifact_requirement_checks(
    scenario: dict[str, object],
    phase: str | None,
    artifacts: Sequence[dict[str, object]],
    started_at_ns: int,
) -> list[dict[str, object]]:
    contract, _ = _scenario_session_contract(scenario, phase)
    unique_artifacts: dict[tuple[str, int], dict[str, object]] = {}
    for item in artifacts:
        if int(item["mtime_ns"]) >= started_at_ns - FRESHNESS_CLOCK_SKEW_NS:
            unique_artifacts[(str(item["sha256"]), int(item["bytes"]))] = item
    suffixes = [
        Path(str(item["path"])).suffix.lower()
        for item in unique_artifacts.values()
    ]
    actual = {
        "screenshots": sum(
            suffix in {".bmp", ".jpeg", ".jpg", ".png", ".tga"}
            for suffix in suffixes
        ),
        "saves": sum(suffix == ".eu4" for suffix in suffixes),
    }
    requirements = {
        "screenshots": int(contract.get("minimum_screenshots", 0)),
        "saves": int(contract.get("minimum_saves", 0)),
    }
    return [
        {
            "kind": kind,
            "minimum": minimum,
            "actual": actual[kind],
            "matched": actual[kind] >= minimum,
        }
        for kind, minimum in requirements.items()
    ]


def _validate_session_record(record: object) -> dict[str, object]:
    required_keys = {
        "schema",
        "scenario",
        "phase",
        "candidate_revision",
        "started_at",
        "started_at_ns",
        "user_data",
        "daily_user_data",
        "evidence_root",
        "snapshots",
        "dlc_load",
        "configuration_baseline",
        "daily_configuration_baseline",
        "before_logs",
        "game_started_by_tool",
    }
    if not isinstance(record, dict) or set(record) != required_keys:
        raise AcceptanceError("session.json schema disagrees with this helper")
    if record["schema"] != SESSION_SCHEMA:
        raise AcceptanceError(
            f"unsupported session schema: {record['schema']!r}; expected {SESSION_SCHEMA}"
        )
    scenario = record["scenario"]
    if (
        not isinstance(scenario, dict)
        or not isinstance(scenario.get("id"), str)
        or scenario.get("id") == "R13"
        or scenario != _scenario(str(scenario.get("id")))
    ):
        raise AcceptanceError("session scenario is missing, stale, or not runnable")
    candidate_revision = record["candidate_revision"]
    if (
        not isinstance(candidate_revision, str)
        or not re.fullmatch(r"[0-9a-f]{40}", candidate_revision)
        or candidate_revision != _current_candidate_revision()
    ):
        raise AcceptanceError("session candidate revision is stale or invalid")
    snapshots = record["snapshots"]
    if not isinstance(snapshots, list) or not snapshots or not all(
        isinstance(item, dict) for item in snapshots
    ):
        raise AcceptanceError("session must record at least one verified snapshot")
    phase = record["phase"]
    if phase is not None and not isinstance(phase, str):
        raise AcceptanceError("session phase must be a string or null")
    selected_phase = _verify_session_snapshot_contract(
        scenario, phase, snapshots, candidate_revision
    )
    if selected_phase != phase:
        raise AcceptanceError("session phase no longer matches its scenario contract")
    if (
        not isinstance(record["started_at"], str)
        or isinstance(record["started_at_ns"], bool)
        or not isinstance(record["started_at_ns"], int)
        or not isinstance(record["user_data"], str)
        or not isinstance(record["daily_user_data"], str)
        or not isinstance(record["evidence_root"], str)
        or not isinstance(record["dlc_load"], dict)
        or not isinstance(record["configuration_baseline"], list)
        or not isinstance(record["daily_configuration_baseline"], list)
        or not isinstance(record["before_logs"], list)
        or record["game_started_by_tool"] is not False
    ):
        raise AcceptanceError("session.json contains invalid field types")
    return record


def _daily_configuration_checks(
    daily_user_data: Path, baseline: object
) -> list[dict[str, object]]:
    expected_paths = {
        name: (daily_user_data / name).resolve()
        for name in ("dlc_load.json", "launcher-v2.sqlite")
    }
    if not isinstance(baseline, list) or len(baseline) != len(expected_paths):
        raise AcceptanceError(
            "daily configuration baseline must contain exactly the two guarded files"
        )
    records: dict[str, dict[str, object]] = {}
    for item in baseline:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "bytes",
            "mtime_ns",
            "sha256",
        }:
            raise AcceptanceError("daily configuration baseline record is malformed")
        path_value = item["path"]
        bytes_value = item["bytes"]
        mtime_value = item["mtime_ns"]
        digest_value = item["sha256"]
        if (
            not isinstance(path_value, str)
            or isinstance(bytes_value, bool)
            or not isinstance(bytes_value, int)
            or bytes_value < 0
            or isinstance(mtime_value, bool)
            or not isinstance(mtime_value, int)
            or not isinstance(digest_value, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest_value)
        ):
            raise AcceptanceError("daily configuration baseline has invalid fields")
        recorded_path = Path(path_value).expanduser().resolve()
        name = recorded_path.name
        if name not in expected_paths or recorded_path != expected_paths[name]:
            raise AcceptanceError(
                "daily configuration baseline points outside its recorded root"
            )
        if name in records:
            raise AcceptanceError(
                f"daily configuration baseline repeats guarded file: {name}"
            )
        records[name] = item
    if set(records) != set(expected_paths):
        raise AcceptanceError("daily configuration baseline is incomplete")

    checks: list[dict[str, object]] = []
    for name, path in expected_paths.items():
        before = records[name]
        if not path.is_file() or _is_link_or_junction(path):
            after = None
            matched = False
            error = f"guarded daily configuration file is missing or not ordinary: {path}"
        else:
            after = _file_record(path)
            matched = all(
                after[key] == before[key] for key in ("bytes", "sha256")
            )
            error = None if matched else "size or SHA-256 changed during the session"
        checks.append(
            {
                "name": name,
                "path": str(path),
                "before": before,
                "after": after,
                "matched": matched,
                "error": error,
            }
        )
    return checks


def collect(
    session: Path, artifacts: Sequence[Path]
) -> tuple[dict[str, object], bool]:
    _assert_processes_stopped()
    session = _require_ordinary_directory(session, "evidence session")
    session_file = session / "session.json"
    if not session_file.is_file():
        raise AcceptanceError(f"session.json is missing from {session}")
    record = _validate_session_record(
        json.loads(session_file.read_text(encoding="utf-8"))
    )
    user_data = _require_isolated_user_data(Path(str(record["user_data"])))
    daily_user_data = _require_ordinary_directory(
        Path(str(record["daily_user_data"])), "daily EU4 user-data root"
    )
    if daily_user_data == user_data:
        raise AcceptanceError("daily and acceptance user-data roots must be distinct")
    evidence_root = Path(record["evidence_root"]).resolve()
    if not _is_relative_to(evidence_root, user_data) or not _is_relative_to(
        session, evidence_root
    ):
        raise AcceptanceError("session is outside its recorded user-data evidence root")
    started_at_ns = int(record["started_at_ns"])
    before_logs_by_name = {
        Path(str(item["path"])).name.lower(): item
        for item in record["before_logs"]
    }
    after = session / "after"
    log_root = after / "logs"
    copied_logs: list[dict[str, object]] = []
    fresh_log_paths: list[Path] = []
    logs = user_data / "logs"
    if logs.is_dir():
        for source in sorted(logs.glob("*.log")):
            item = _copy_artifact(source, log_root)
            copied_logs.append(item)
            baseline = before_logs_by_name.get(source.name.lower())
            changed = baseline is None or any(
                item[key] != baseline[key] for key in ("mtime_ns", "sha256", "bytes")
            )
            if (
                changed
                and int(item["mtime_ns"])
                >= started_at_ns - FRESHNESS_CLOCK_SKEW_NS
            ):
                fresh_log_paths.append(Path(str(item["path"])))
    copied_artifacts: list[dict[str, object]] = []
    automatic_roots = (
        (user_data / "Screenshots", "screenshots", "*"),
        (user_data / "save games", "saves", "JXP_ACC_*.eu4"),
    )
    for source_root, category, pattern in automatic_roots:
        if not source_root.is_dir():
            continue
        for source in sorted(source_root.glob(pattern)):
            if (
                source.is_file()
                and source.stat().st_mtime_ns
                >= started_at_ns - FRESHNESS_CLOCK_SKEW_NS
            ):
                copied_artifacts.append(
                    _copy_artifact(source, after / category)
                )
    for raw in artifacts:
        source = raw.expanduser().resolve()
        if not source.is_file() or not _is_relative_to(source, user_data):
            raise AcceptanceError(f"artifact must be a user-data file: {source}")
        copied_artifacts.append(_copy_artifact(source, after / "explicit"))
    blockers = _scan_logs(fresh_log_paths)
    copied_log_names = {Path(str(item["path"])).name.lower() for item in copied_logs}
    missing_logs = sorted({"error.log", "game.log"} - copied_log_names)
    fresh_log_names = {path.name.lower() for path in fresh_log_paths}
    stale_logs = sorted(
        name
        for name in {"error.log", "game.log"} & copied_log_names
        if name not in fresh_log_names
    )
    passed_log_scan = not blockers and not missing_logs and not stale_logs

    snapshot_checks: list[dict[str, object]] = []
    for expected in record["snapshots"]:
        descriptor = Path(str(expected["descriptor"]["path"]))
        try:
            actual = _installed_snapshot_record(descriptor, user_data)
            matched = all(
                actual[key] == expected[key]
                for key in (
                    "component",
                    "display_name",
                    "version",
                    "source_revision",
                    "fingerprint",
                    "files",
                    "payload",
                    "dependencies",
                )
            ) and all(
                actual[file_key]["sha256"] == expected[file_key]["sha256"]
                and actual[file_key]["bytes"] == expected[file_key]["bytes"]
                for file_key in ("payload_marker", "descriptor")
            )
            error = None
        except AcceptanceError as exc:
            matched = False
            error = str(exc)
        snapshot_checks.append(
            {
                "component": expected.get("component"),
                "fingerprint": expected.get("fingerprint"),
                "matched": matched,
                "error": error,
            }
        )

    after_dlc = _dlc_load(user_data)
    expected_enabled = {
        f"mod/{Path(str(item['descriptor']['path'])).name}"
        for item in record["snapshots"]
    }
    actual_enabled = {str(item) for item in after_dlc.get("enabled_mods", ())}
    expected_disabled = {
        str(item) for item in record["dlc_load"].get("disabled_dlcs", ())
    }
    actual_disabled = {str(item) for item in after_dlc.get("disabled_dlcs", ())}
    isolated_configuration_stable = after_dlc == record["dlc_load"]
    playset_stable = isolated_configuration_stable
    daily_configuration_checks = _daily_configuration_checks(
        daily_user_data, record["daily_configuration_baseline"]
    )
    daily_configuration_stable = all(
        item["matched"] for item in daily_configuration_checks
    )
    dlc_checks = _runtime_dlc_checks(
        record["scenario"], record.get("phase"), fresh_log_paths
    )
    artifact_checks = _artifact_requirement_checks(
        record["scenario"],
        record.get("phase"),
        copied_artifacts,
        started_at_ns,
    )
    passed_collection_gate = (
        passed_log_scan
        and all(item["matched"] for item in snapshot_checks)
        and playset_stable
        and daily_configuration_stable
        and all(item["matched"] for item in dlc_checks)
        and all(item["matched"] for item in artifact_checks)
    )
    configuration_after = []
    for relative in ("dlc_load.json", "launcher-v2.sqlite"):
        path = user_data / relative
        if path.is_file():
            configuration_after.append(_file_record(path))
    result = {
        "schema": COLLECTION_SCHEMA,
        "collected_at": _utc_now().isoformat(),
        "scenario_id": record["scenario"]["id"],
        "logs": copied_logs,
        "artifacts": copied_artifacts,
        "blockers": blockers,
        "missing_required_logs": missing_logs,
        "stale_logs": stale_logs,
        "passed_log_scan": passed_log_scan,
        "snapshot_checks": snapshot_checks,
        "playset_stable": playset_stable,
        "isolated_configuration_stable": isolated_configuration_stable,
        "expected_enabled_mods": sorted(expected_enabled),
        "actual_enabled_mods": sorted(actual_enabled),
        "expected_disabled_dlcs": sorted(expected_disabled),
        "actual_disabled_dlcs": sorted(actual_disabled),
        "daily_user_data": str(daily_user_data),
        "daily_configuration_checks": daily_configuration_checks,
        "daily_configuration_stable": daily_configuration_stable,
        "runtime_dlc_checks": dlc_checks,
        "artifact_requirement_checks": artifact_checks,
        "configuration_after": configuration_after,
        "passed_collection_gate": passed_collection_gate,
        "claim_limit": (
            "Collection proves only the supplied scenario and artifacts; manual UI "
            "checks remain required by runtime_scenarios.json."
        ),
    }
    (session / "collection.json").write_text(_json_dump(result), encoding="utf-8")
    return result, passed_collection_gate


def _common_paths(
    parser: argparse.ArgumentParser, user_data_default: Path
) -> None:
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--user-data", type=Path, default=user_data_default)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and collect JXP runtime acceptance without launching EU4"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight")
    _common_paths(preflight_parser, DEFAULT_USER_DATA)
    preflight_parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)

    deploy_parser = subparsers.add_parser("deploy")
    _common_paths(deploy_parser, DEFAULT_ACCEPTANCE_USER_DATA)
    deploy_parser.add_argument("--label", default="current")
    deploy_parser.add_argument("--revision")
    deploy_parser.add_argument("--main-only", action="store_true")

    configure_parser = subparsers.add_parser("configure-playset")
    configure_parser.add_argument("scenario")
    configure_parser.add_argument("--phase")
    configure_parser.add_argument(
        "--user-data", type=Path, default=DEFAULT_ACCEPTANCE_USER_DATA
    )
    configure_parser.add_argument(
        "--descriptor", type=Path, action="append", default=[]
    )

    fixture_parser = subparsers.add_parser("install-fixtures")
    fixture_parser.add_argument(
        "--user-data", type=Path, default=DEFAULT_ACCEPTANCE_USER_DATA
    )

    before_parser = subparsers.add_parser("before-session")
    before_parser.add_argument("scenario")
    before_parser.add_argument("--phase")
    before_parser.add_argument(
        "--user-data", type=Path, default=DEFAULT_ACCEPTANCE_USER_DATA
    )
    before_parser.add_argument(
        "--daily-user-data", type=Path, default=DEFAULT_USER_DATA
    )
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
        elif args.command == "configure-playset":
            result = configure_playset(
                args.user_data,
                args.scenario,
                args.phase,
                args.descriptor,
            )
            success = True
        elif args.command == "install-fixtures":
            result = install_run_fixtures(args.user_data)
            success = True
        elif args.command == "before-session":
            result = before_session(
                args.user_data,
                args.scenario,
                args.phase,
                args.evidence_root,
                args.descriptor,
                daily_user_data=args.daily_user_data,
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
