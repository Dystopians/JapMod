#!/usr/bin/env python3
"""Prepare JXP runtime evidence without launching EU4.

The CLI deliberately has no launch command and never writes launcher-v2.sqlite.
It installs content-addressed ordinary-directory snapshots, configures only the
isolated acceptance root's dlc_load.json, records a before-session baseline,
and collects explicitly generated evidence.
"""

from __future__ import annotations

import argparse
import base64
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha1, sha256
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import threading
from typing import Iterable, Sequence
import uuid
import zipfile
import zlib

try:
    from .oracle_contract import OracleContractError, verify_runtime_oracle
except ImportError:  # Direct-script CLI execution.
    from oracle_contract import OracleContractError, verify_runtime_oracle


PINNED_LEGACY_REVISION = "8a5962628014e696bda764bcad10bfd3faee188e"
PINNED_PRE_IDENTITY_REVISION = "6e461e2e47a839a77b2e376ce61ceb317d393320"
PINNED_PROTOCOL_FILES = {
    "eu4.exe": "9ad3efe1af169f40ee577f9dae5debbc87af6fb8b5450fb345ebf110dc4d771a",
    "userdir.txt": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "launcher-settings.json": "71bc763b5df4d9fc04dbc48655449f847bf4442d65fb195e5111739c08c5d572",
}
PINNED_PROTOCOL_PATHS = ("eu4.exe", "userdir.txt", "launcher-settings.json")
PIN_MANIFEST_RELATIVE_PATH = PurePosixPath(
    "japan_expanded_v2/tools/jxp_validation/vanilla_1_37_5_manifest.json"
)
PIN_MANIFEST_SHA256 = (
    "1abc720a6ee8e930f60d644a49aa6c2c231c05dac559cb4c465d6d391a05f2a9"
)
PINNED_GAMEPLAY_GROUPS = (
    (
        "files",
        (
            (
                "missions/Japanese_Missions.txt",
                "67b3f0abb6276fb11f2688c2f7269eb9086e0afd7a2d778e6bc4bf856c028fd5",
            ),
            (
                "missions/DOM_Japanese_Missions.txt",
                "55917ac903b47ba943ed8e0256bdd19af7bec65443e2f72a633e3d4cded98525",
            ),
        ),
    ),
    (
        "generic_files",
        (
            (
                "missions/00_Generic_missions.txt",
                "550119394756c142eca5b83a527820cdff878a87968a29f2e5de38cd06e9dd3d",
            ),
            (
                "missions/01_Generic_European_Missions.txt",
                "71f32cabf7713d5f27223c95c185c7ca0961cd02544e3408d4836ec4dd7ba184",
            ),
            (
                "missions/Asian_Missions.txt",
                "d8a2d8f46f7bd0d7f01d13b5e8f66ea8e30325d7eadaad94f58518516d4b228e",
            ),
        ),
    ),
    (
        "mandate_files",
        (
            (
                "common/cb_types/00_cb_types.txt",
                "c9b76e64963a9b8e20eb9c4729d400ee13cd71f7818e80d247b134cc831033d9",
            ),
            (
                "common/wargoal_types/00_wargoal_types.txt",
                "ec45a5a221b762a326fab4f29099e39b6461665072d53fa398ac466f38617600",
            ),
            (
                "common/imperial_reforms/01_china.txt",
                "e7a3f1e8065b8d8e02c9dabea403525b994f9cfd844e5b14e05b57a24137759c",
            ),
            (
                "events/ChineseEmpire.txt",
                "7bb14aaa99b89fbca230272bc7d7c4ed1e7dbe1468b3d198a6bf25170de680a9",
            ),
        ),
    ),
)
HELPER_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
RUN_FIXTURE_ROOT = Path(__file__).with_name("run_fixtures")
SNAPSHOT_MARKER_SCHEMA = 1
SESSION_SCHEMA = 4
COLLECTION_SCHEMA = 4
RECEIPT_SCHEMA = 4
EVIDENCE_MANIFEST_SCHEMA = 4
ACTIVE_SESSION_NAME = ".active_session.json"
CONFIGURE_RECEIPT_NAME = ".jxp_configure_receipt.json"
SESSION_SEAL_NAME = "session.seal.json"
COLLECTION_NAME = "collection.json"
COLLECTION_SEAL_NAME = "collection.seal.json"
CLOSURE_NAME = "closure.json"
CLOSURE_SEAL_NAME = "closure.seal.json"
PROCESS_OBSERVATION_NAME = "process_observation.json"
EVIDENCE_MANIFEST_NAME = "evidence_manifest.json"
EXPECTED_GAME_VERSION_LOG = "Game Version: EU4 v1.37.5.0 Inca"
ISOLATED_CONFIGURATION_PATHS = (
    "dlc_load.json",
    "launcher-v2.sqlite",
    ".launcher-cache",
)
DAILY_CRITICAL_VFS_PATHS = (
    "dlc_load.json",
    "launcher-v2.sqlite",
    "settings.txt",
    "pdx_settings.txt",
    "gameplaysettings.txt",
    ".launcher-cache",
    "cache",
    "logs",
    "save games",
    "Screenshots",
)
DAILY_VFS_COVERAGE = ("*", *DAILY_CRITICAL_VFS_PATHS)
ACCEPTANCE_RUNTIME_OUTPUT_PATHS = (
    "settings.txt",
    "pdx_settings.txt",
    "gameplaysettings.txt",
    "logs",
)
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
MIN_SCREENSHOT_DIMENSION = 64
MAX_SCREENSHOT_PIXELS = 100_000_000
MAX_DECODED_IMAGE_BYTES = 512 * 1024 * 1024
MAX_SCREENSHOT_FILE_BYTES = 640 * 1024 * 1024
MIN_EU4_SAVE_BYTES = 32 * 1024
MIN_EU4_META_BYTES = 512
MIN_EU4_GAMESTATE_BYTES = 256 * 1024
MAX_EU4_STRUCTURE_PREFIX_BYTES = 32 * 1024 * 1024
MAX_EU4_SAVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_EU4_ZIP_MEMBERS = 32
MAX_EU4_ZIP_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_EU4_ZIP_RATIO = 1000
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


KF_FLAG_DONT_VERIFY = 0x00004000


def _known_documents_root() -> Path:
    """Return the OS Documents known folder without trusting Windows env vars.

    The non-Windows branch is intentionally small and patchable for unit tests;
    production runtime acceptance is Windows-only and uses the Shell Known Folder
    API so USERPROFILE, HOME, and HOMEDRIVE/HOMEPATH cannot redirect the guard.
    """
    if os.name != "nt":
        return (Path.home() / "Documents").resolve()

    try:
        import ctypes
        from ctypes import wintypes

        class Guid(ctypes.Structure):
            _fields_ = (
                ("data1", ctypes.c_ulong),
                ("data2", ctypes.c_ushort),
                ("data3", ctypes.c_ushort),
                ("data4", ctypes.c_ubyte * 8),
            )

        folder_id_documents = Guid(
            0xFDD39AD0,
            0x238F,
            0x46AF,
            (ctypes.c_ubyte * 8)(
                0xAD,
                0xB4,
                0x6C,
                0x85,
                0x48,
                0x03,
                0x69,
                0xC7,
            ),
        )
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        get_known_folder = shell32.SHGetKnownFolderPath
        get_known_folder.argtypes = (
            ctypes.POINTER(Guid),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_void_p),
        )
        get_known_folder.restype = ctypes.c_long
        free_memory = ole32.CoTaskMemFree
        free_memory.argtypes = (ctypes.c_void_p,)
        free_memory.restype = None
        pointer = ctypes.c_void_p()
        # The Shell resolves the registered current Documents location without
        # consulting caller-controlled USERPROFILE/HOME variables.  Do not use
        # KF_FLAG_DEFAULT_PATH here: that would silently ignore a legitimate
        # Known Folder redirection.  DONT_VERIFY leaves the ordinary-directory
        # and reparse-chain checks to each production operation boundary.
        known_folder_flags = KF_FLAG_DONT_VERIFY
        result = get_known_folder(
            ctypes.byref(folder_id_documents),
            known_folder_flags,
            None,
            ctypes.byref(pointer),
        )
        if result != 0 or not pointer.value:
            raise OSError(
                "SHGetKnownFolderPath(FOLDERID_Documents) failed with HRESULT "
                f"0x{result & 0xFFFFFFFF:08x}"
            )
        try:
            value = ctypes.wstring_at(pointer.value)
        finally:
            free_memory(pointer)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise AcceptanceError(f"cannot resolve the Windows Documents known folder: {exc}") from exc
    if not value:
        raise AcceptanceError("Windows Documents known folder resolved to an empty path")
    return Path(value).resolve()


@lru_cache(maxsize=1)
def _known_profile_root() -> Path:
    """Return the current Windows profile without trusting USERPROFILE/HOME."""

    if os.name != "nt":
        return Path.home().resolve()
    try:
        import ctypes
        from ctypes import wintypes

        class Guid(ctypes.Structure):
            _fields_ = (
                ("data1", ctypes.c_ulong),
                ("data2", ctypes.c_ushort),
                ("data3", ctypes.c_ushort),
                ("data4", ctypes.c_ubyte * 8),
            )

        folder_id_profile = Guid(
            0x5E6C858F,
            0x0E22,
            0x4760,
            (ctypes.c_ubyte * 8)(
                0x9A,
                0xFE,
                0xEA,
                0x33,
                0x17,
                0xB6,
                0x71,
                0x73,
            ),
        )
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        get_known_folder = shell32.SHGetKnownFolderPath
        get_known_folder.argtypes = (
            ctypes.POINTER(Guid),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_void_p),
        )
        get_known_folder.restype = ctypes.c_long
        free_memory = ole32.CoTaskMemFree
        free_memory.argtypes = (ctypes.c_void_p,)
        free_memory.restype = None
        pointer = ctypes.c_void_p()
        result = get_known_folder(
            ctypes.byref(folder_id_profile),
            KF_FLAG_DONT_VERIFY,
            None,
            ctypes.byref(pointer),
        )
        if result != 0 or not pointer.value:
            raise OSError(
                "SHGetKnownFolderPath(FOLDERID_Profile) failed with HRESULT "
                f"0x{result & 0xFFFFFFFF:08x}"
            )
        try:
            value = ctypes.wstring_at(pointer.value)
        finally:
            free_memory(pointer)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise AcceptanceError(
            f"cannot resolve the Windows profile known folder: {exc}"
        ) from exc
    if not value:
        raise AcceptanceError("Windows profile known folder resolved to an empty path")
    return Path(value).resolve()


DOCUMENTS_ROOT = _known_documents_root()
DEFAULT_USER_DATA = (
    DOCUMENTS_ROOT / "Paradox Interactive" / "Europa Universalis IV"
)
DEFAULT_ACCEPTANCE_USER_DATA = DOCUMENTS_ROOT / "JXP_Acceptance"


@dataclass(frozen=True, slots=True)
class Component:
    key: str
    source: Path
    outer_descriptor: Path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceError(f"{label} must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcceptanceError(f"{label} is not an ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AcceptanceError(f"{label} must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _json_dump(value: object, *, sort_keys: bool = True) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=sort_keys) + "\n"


def _strict_json_loads(text: str, label: str) -> object:
    """Parse JSON while rejecting duplicate object keys at every depth."""

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key {key!r}")
            value[key] = item
        return value

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            ),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise AcceptanceError(f"cannot parse {label}: {exc}") from exc


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _object_sha256(value: object) -> str:
    return sha256(_canonical_json_bytes(value)).hexdigest()


def _json_exact_equal(left: object, right: object) -> bool:
    """Compare JSON values without Python's bool/int equality coercion."""

    return _canonical_json_bytes(left) == _canonical_json_bytes(right)


def _read_json_object(
    path: Path, label: str, *, max_bytes: int | None = None
) -> dict[str, object]:
    if not path.is_file() or _is_link_or_junction(path):
        raise AcceptanceError(f"{label} must be an ordinary file: {path}")
    try:
        before = path.stat()
        if max_bytes is not None and (
            isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or max_bytes <= 0
            or before.st_size > max_bytes
        ):
            raise AcceptanceError(f"{label} exceeds its read limit: {path}")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if any(
                getattr(opened, key) != getattr(before, key)
                for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
            ):
                raise AcceptanceError(f"{label} changed before reading: {path}")
            raw = stream.read(max_bytes + 1 if max_bytes is not None else -1)
            opened_after = os.fstat(stream.fileno())
        after = path.stat()
        if (
            max_bytes is not None
            and len(raw) > max_bytes
            or any(
                getattr(opened_after, key) != getattr(opened, key)
                or getattr(after, key) != getattr(before, key)
                for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
            )
        ):
            raise AcceptanceError(f"{label} changed or exceeded its limit: {path}")
        value = _strict_json_loads(raw.decode("utf-8-sig", errors="strict"), label)
    except (OSError, UnicodeError) as exc:
        raise AcceptanceError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label} must contain a JSON object: {path}")
    return value


def _atomic_write_json(
    path: Path, value: object, *, sort_keys: bool = True
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        temporary.write_text(_json_dump(value, sort_keys=sort_keys), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            temporary.unlink()


def _exclusive_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = _require_ordinary_directory(path.parent, "exclusive JSON parent")
    path = parent / path.name
    temporary = parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    payload = _json_dump(value).encode("utf-8")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
    )
    committed = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # A hard-link commit is atomic and no-clobber on the same volume.  A
        # failed write never exposes a partial final JSON file.
        os.link(temporary, path)
        committed = True
        if (
            not path.is_file()
            or _is_link_or_junction(path)
            or path.stat().st_size != len(payload)
            or _sha256_file(path) != sha256(payload).hexdigest()
        ):
            raise AcceptanceError(f"exclusive JSON commit verification failed: {path}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if committed and os.path.lexists(path) and os.path.lexists(temporary):
            try:
                final_stat = path.stat()
                temporary_stat = temporary.stat()
                same_file = (
                    final_stat.st_dev == temporary_stat.st_dev
                    and final_stat.st_ino == temporary_stat.st_ino
                )
            except OSError:
                same_file = False
            if same_file and (
                path.stat().st_size != len(payload)
                or _sha256_file(path) != sha256(payload).hexdigest()
            ):
                path.unlink()
        if os.path.lexists(temporary):
            temporary.unlink()


def _sealed_value(payload: dict[str, object], field: str) -> dict[str, object]:
    if field in payload:
        raise AcceptanceError(f"seal field already exists: {field}")
    return {**payload, field: _object_sha256(payload)}


def _verify_self_seal(
    value: object,
    field: str,
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label} must contain an object")
    digest = value.get(field)
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise AcceptanceError(f"{label} has no valid {field}")
    payload = {key: item for key, item in value.items() if key != field}
    if _object_sha256(payload) != digest:
        raise AcceptanceError(f"{label} self-seal disagrees")
    return value


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
    supplied = Path(os.path.abspath(os.path.expanduser(str(path))))
    # Checking only the leaf misses an ancestor junction such as
    # Documents\alias\evidence.  Walk the supplied chain (not the resolved one)
    # so every redirection boundary is visible and fails closed.
    for candidate in reversed((supplied, *supplied.parents)):
        if os.path.lexists(candidate) and _is_link_or_junction(candidate):
            raise AcceptanceError(
                f"{label} cannot traverse a link or junction: {candidate}"
            )
    return resolved


def _require_canonical_repo(repo: Path) -> Path:
    """Accept only the real Git top-level containing this helper."""
    helper_root = _require_ordinary_directory(HELPER_REPO_ROOT, "helper repository")
    supplied = Path(os.path.abspath(os.path.expanduser(str(repo))))
    candidate = _require_ordinary_directory(repo, "repository")
    if supplied != candidate or candidate != helper_root:
        raise AcceptanceError(
            "runtime acceptance accepts only the helper's own checkout: "
            f"{helper_root}"
        )
    reported = _git(candidate, "rev-parse", "--show-toplevel")
    if not reported:
        raise AcceptanceError("git returned no repository top-level")
    git_top_level = Path(reported).resolve()
    if git_top_level != helper_root or _is_link_or_junction(git_top_level):
        raise AcceptanceError(
            "helper path is not the real Git top-level of its own checkout: "
            f"helper {helper_root}, git {git_top_level}"
        )
    return helper_root


def _require_canonical_game_root(game_root: Path) -> Path:
    """Accept only the fixed, ordinary EU4 1.37.5 installation location."""
    canonical = DEFAULT_GAME_ROOT.resolve()
    supplied = Path(os.path.abspath(os.path.expanduser(str(game_root))))
    resolved = _require_ordinary_directory(game_root, "EU4 game root")
    if supplied != resolved or resolved != canonical:
        raise AcceptanceError(
            "runtime acceptance is pinned to the canonical EU4 installation root: "
            f"{canonical}"
        )
    if _is_link_or_junction(DEFAULT_GAME_ROOT):
        raise AcceptanceError(
            f"canonical EU4 game root cannot be a link or junction: {DEFAULT_GAME_ROOT}"
        )
    return resolved


def _require_canonical_runtime_roots(
    repo: Path, game_root: Path
) -> tuple[Path, Path]:
    """Verify the two immutable authorities used by every runtime operation."""
    return _require_canonical_repo(repo), _require_canonical_game_root(game_root)


def _safe_pin_relative_path(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise AcceptanceError(f"{label} must be a non-empty POSIX relative path")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or value != relative.as_posix()
        or relative.as_posix() in {"", "."}
        or ".." in relative.parts
        or any(not part or ":" in part for part in relative.parts)
    ):
        raise AcceptanceError(f"{label} is not a canonical safe relative path: {value!r}")
    return relative


def _pin_path_under_root(root: Path, relative: PurePosixPath, label: str) -> Path:
    source = root
    for part in relative.parts:
        source = source / part
        if os.path.lexists(source) and _is_link_or_junction(source):
            raise AcceptanceError(f"{label} cannot traverse a link or junction: {source}")
    if not _is_relative_to(source, root):
        raise AcceptanceError(f"{label} escaped its canonical root: {source}")
    return source


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


def _require_canonical_acceptance_user_data(path: Path) -> Path:
    resolved = _require_isolated_user_data(path)
    canonical = DEFAULT_ACCEPTANCE_USER_DATA.expanduser().resolve()
    if resolved != canonical:
        raise AcceptanceError(
            "runtime acceptance production writes are restricted to the canonical "
            f"user-data root: {canonical}"
        )
    return resolved


def _require_disjoint_roots(first: Path, second: Path, labels: str) -> None:
    if first == second or _is_relative_to(first, second) or _is_relative_to(second, first):
        raise AcceptanceError(f"{labels} must be distinct and must not contain one another")


def _launcher_daily_user_data(game_root: Path) -> Path:
    game_root = _require_canonical_game_root(game_root)
    settings_path = game_root / "launcher-settings.json"
    expected = PINNED_PROTOCOL_FILES["launcher-settings.json"]
    if (
        not settings_path.is_file()
        or _is_link_or_junction(settings_path)
        or _sha256_file(settings_path) != expected
    ):
        raise AcceptanceError(
            "cannot derive daily user data from the pinned launcher-settings.json"
        )
    settings = _read_json_object(settings_path, "launcher settings")
    raw = settings.get("gameDataPath")
    if not isinstance(raw, str) or not raw:
        raise AcceptanceError("launcher settings have no gameDataPath")
    marker = "%USER_DOCUMENTS%"
    if raw == marker:
        derived = DOCUMENTS_ROOT
    elif raw.startswith(marker + "/") or raw.startswith(marker + "\\"):
        relative = raw[len(marker) + 1 :].replace("\\", "/")
        parts = PurePosixPath(relative)
        if parts.is_absolute() or ".." in parts.parts or any(":" in part for part in parts.parts):
            raise AcceptanceError(f"unsafe launcher gameDataPath: {raw!r}")
        derived = DOCUMENTS_ROOT.joinpath(*parts.parts)
    else:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            raise AcceptanceError(f"unsupported launcher gameDataPath: {raw!r}")
        derived = candidate
    resolved = derived.resolve()
    expected_daily = DEFAULT_USER_DATA.expanduser().resolve()
    if resolved != expected_daily:
        raise AcceptanceError(
            "pinned launcher gameDataPath disagrees with the canonical daily root; "
            f"derived {resolved}, expected {expected_daily}"
        )
    return _require_ordinary_directory(resolved, "canonical daily EU4 user-data root")


def _require_canonical_daily_user_data(path: Path, game_root: Path) -> Path:
    resolved = _require_ordinary_directory(path, "daily EU4 user-data root")
    expected = _launcher_daily_user_data(game_root)
    if resolved != expected:
        raise AcceptanceError(
            "daily configuration guard must target the launcher-derived canonical "
            f"EU4 user-data root: {expected}"
        )
    return resolved


def _require_canonical_fixture_user_data(path: Path) -> Path:
    """Restrict root-level console fixtures to the audited acceptance userdir."""
    resolved = _require_canonical_acceptance_user_data(path)
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


def _require_canonical_evidence_root(
    user_data: Path,
    value: Path | None,
    *,
    create: bool,
) -> Path:
    """Reserve one evidence tree disjoint from mod/config/runtime surfaces."""

    expected = user_data / "jxp_runtime_evidence"
    raw = (value or expected).expanduser()
    supplied = Path(os.path.abspath(os.path.expanduser(str(raw))))
    if supplied != expected:
        raise AcceptanceError(
            "runtime evidence is restricted to the canonical reserved root: "
            f"{expected}"
        )
    if create:
        raw.mkdir(parents=True, exist_ok=True)
    resolved = _require_ordinary_directory(raw, "runtime evidence root")
    if resolved != expected:
        raise AcceptanceError("runtime evidence root does not resolve canonically")
    return resolved


def _active_session_path(user_data: Path) -> Path:
    return user_data / ACTIVE_SESSION_NAME


def _assert_no_active_session(user_data: Path, action: str) -> None:
    active = _active_session_path(user_data)
    if os.path.lexists(active):
        raise AcceptanceError(
            f"cannot {action} while an acceptance session is active: {active}; "
            "collect it or run abort-session explicitly"
        )


def _read_active_session(user_data: Path) -> dict[str, object]:
    active = _active_session_path(user_data)
    value = _read_json_object(active, "active-session lock")
    required = {
        "schema",
        "state",
        "nonce",
        "session",
        "session_sha256",
        "created_at",
    }
    if set(value) != required or value.get("schema") != SESSION_SCHEMA:
        raise AcceptanceError("active-session lock schema disagrees")
    if value.get("state") != "active":
        raise AcceptanceError("active-session lock is incomplete")
    if not isinstance(value.get("nonce"), str) or not re.fullmatch(
        r"[0-9a-f]{64}", str(value.get("nonce"))
    ):
        raise AcceptanceError("active-session lock nonce is invalid")
    if not isinstance(value.get("session"), str) or not isinstance(
        value.get("session_sha256"), str
    ):
        raise AcceptanceError("active-session lock identity is invalid")
    return value


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


def _expected_eu4_argv(game_root: Path, user_data: Path) -> list[str]:
    executable = (game_root / "eu4.exe").resolve()
    return [str(executable), f"-userdir={user_data}"]


def _windows_command_line_argv(command_line: str) -> list[str]:
    if os.name != "nt":
        raise AcceptanceError("EU4 process observation requires Windows")
    try:
        import ctypes
        from ctypes import wintypes

        argc = ctypes.c_int()
        command_line_to_argv = ctypes.windll.shell32.CommandLineToArgvW
        command_line_to_argv.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        command_line_to_argv.restype = ctypes.POINTER(wintypes.LPWSTR)
        pointer = command_line_to_argv(command_line, ctypes.byref(argc))
        if not pointer:
            raise OSError("CommandLineToArgvW returned null")
        try:
            return [pointer[index] for index in range(argc.value)]
        finally:
            ctypes.windll.kernel32.LocalFree(pointer)
    except (AttributeError, OSError, ValueError) as exc:
        raise AcceptanceError(f"cannot parse observed Windows command line: {exc}") from exc


def _eu4_process_details() -> list[dict[str, object]]:
    if os.name != "nt":
        return []
    script = (
        "$ErrorActionPreference='Stop'; "
        "$p=Get-CimInstance Win32_Process -Filter \"Name='eu4.exe'\" | "
        "Select-Object ProcessId,ExecutablePath,CommandLine,"
        "@{Name='CreationDate';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}}; "
        "@($p) | ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
        value = _strict_json_loads(
            completed.stdout or "[]", "EU4 process observation"
        )
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        raise AcceptanceError(f"cannot observe EU4 process command line: {exc}") from exc
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise AcceptanceError("EU4 process observation returned malformed data")
    return value


def _trusted_git_path() -> Path:
    path = Path(os.path.abspath(str(_R13_TRUSTED_GIT)))
    if (
        path.resolve() != path
        or not path.is_file()
        or _is_link_or_junction(path)
        or _sha256_file(path) != _R13_TRUSTED_GIT_SHA256
    ):
        raise AcceptanceError(f"trusted Git executable is unavailable: {path}")
    cursor = path
    while cursor != cursor.parent:
        if _is_link_or_junction(cursor):
            raise AcceptanceError(f"trusted Git path traverses reparse data: {cursor}")
        cursor = cursor.parent
    return path


def _git_bytes(
    repo: Path, *args: str, input_bytes: bytes | None = None
) -> bytes:
    system_paths = _windows_system_paths()
    profile = _require_ordinary_directory(_known_profile_root(), "Windows profile")
    windows = Path(system_paths["windows"])
    system = Path(system_paths["system"])
    git = _trusted_git_path()
    environment = {
        "SystemRoot": str(windows),
        "WINDIR": str(windows),
        "SYSTEMDRIVE": windows.drive,
        "COMSPEC": str(system_paths["cmd"]),
        "PATH": os.pathsep.join((str(git.parent), str(system))),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "HOME": str(profile),
        "USERPROFILE": str(profile),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "NUL" if os.name == "nt" else "/dev/null",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "LC_ALL": "C",
    }
    try:
        completed = subprocess.run(
            [
                str(git),
                "--no-replace-objects",
                "--literal-pathspecs",
                "-C",
                str(repo),
                *args,
            ],
            check=True,
            capture_output=True,
            text=False,
            env=environment,
            input=input_bytes,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AcceptanceError(f"git {' '.join(args)} failed: {exc}") from exc
    if not isinstance(completed.stdout, bytes):
        raise AcceptanceError("trusted Git returned non-bytes output")
    return completed.stdout


def _git(repo: Path, *args: str) -> str:
    try:
        return _git_bytes(repo, *args).decode("utf-8", errors="strict").strip()
    except UnicodeError as exc:
        raise AcceptanceError(f"git {' '.join(args)} returned non-UTF-8 data") from exc


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


@lru_cache(maxsize=16)
def _git_snapshot_manifest_records(
    component_key: str, source_revision: str
) -> tuple[tuple[str, int, str], ...]:
    """Derive the runtime manifest from the claimed immutable Git object.

    Installed marker metadata is intentionally not an authority.  Rebuilding
    the whitelist from ``git archive`` binds every accepted byte to the exact
    commit claimed by the snapshot.
    """
    if component_key not in RUNTIME_DIRECTORIES:
        raise AcceptanceError(f"unknown snapshot component: {component_key!r}")
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise AcceptanceError(f"invalid snapshot Git revision: {source_revision!r}")
    repo = _require_canonical_repo(HELPER_REPO_ROOT)
    with tempfile.TemporaryDirectory(prefix="jxp-snapshot-proof-") as temporary:
        components, resolved_revision = _revision_components(
            repo,
            source_revision,
            Path(temporary),
            main_only=component_key == "main",
        )
        if resolved_revision != source_revision:
            raise AcceptanceError(
                "snapshot revision must be the exact full Git commit id; "
                f"resolved {resolved_revision}, claimed {source_revision}"
            )
        selected = [item for item in components if item.key == component_key]
        if len(selected) != 1:
            raise AcceptanceError(
                f"Git revision has no unique {component_key} runtime component"
            )
        return tuple(
            (str(item["path"]), int(item["bytes"]), str(item["sha256"]))
            for item in _manifest(selected[0])
        )


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
        actual = _strict_json_loads(
            marker.read_text(encoding="utf-8"), "acceptance snapshot marker"
        )
    except OSError as exc:
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
    repo, game_root = _require_canonical_runtime_roots(repo, DEFAULT_GAME_ROOT)
    _verified_twelve_pins(repo, game_root)
    user_data = _require_canonical_acceptance_user_data(user_data)
    _assert_no_active_session(user_data, "deploy snapshots")
    mod_dir = user_data / "mod"
    mod_dir.mkdir(exist_ok=True)
    mod_dir = _require_ordinary_directory(mod_dir, "EU4 user mod directory")
    if _is_relative_to(repo, game_root) or _is_relative_to(mod_dir, repo):
        raise AcceptanceError("repository and deployment targets are not safely separated")
    if _is_relative_to(mod_dir, game_root):
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
    repo = _require_canonical_repo(repo)
    relative = _safe_pin_relative_path(
        PIN_MANIFEST_RELATIVE_PATH.as_posix(), "pinned vanilla manifest path"
    )
    path = _pin_path_under_root(repo, relative, "pinned vanilla manifest")
    if not path.is_file() or _is_link_or_junction(path):
        raise AcceptanceError(f"pinned vanilla manifest must be an ordinary file: {path}")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AcceptanceError(f"cannot read pinned vanilla manifest: {exc}") from exc
    actual_manifest_sha256 = sha256(payload).hexdigest()
    if actual_manifest_sha256 != PIN_MANIFEST_SHA256:
        raise AcceptanceError(
            "pinned vanilla manifest SHA-256 disagrees; "
            f"expected {PIN_MANIFEST_SHA256}, found {actual_manifest_sha256}"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AcceptanceError(f"pinned vanilla manifest is not UTF-8: {exc}") from exc
    value = _strict_json_loads(text, "pinned vanilla manifest")
    required_keys = {
        "schema",
        "eu4_raw_version",
        "eu4_display_version",
        *(group for group, _ in PINNED_GAMEPLAY_GROUPS),
    }
    if not isinstance(value, dict) or set(value) != required_keys:
        raise AcceptanceError("pinned vanilla manifest top-level schema disagrees")
    if (
        type(value["schema"]) is not int
        or value["schema"] != 1
        or value["eu4_raw_version"] != "v1.37.5.0"
        or value["eu4_display_version"] != "EU4 v1.37.5.0 Inca (491d)"
    ):
        raise AcceptanceError("pinned vanilla manifest version identity disagrees")
    for group, expected_entries in PINNED_GAMEPLAY_GROUPS:
        entries = value[group]
        if not isinstance(entries, list) or len(entries) != len(expected_entries):
            raise AcceptanceError(f"pinned vanilla manifest {group} cardinality disagrees")
        for index, (entry, (expected_path, expected_sha256)) in enumerate(
            zip(entries, expected_entries, strict=True)
        ):
            if not isinstance(entry, dict) or set(entry) != {
                "path",
                "sha256",
                "purpose",
            }:
                raise AcceptanceError(
                    f"pinned vanilla manifest {group}[{index}] schema disagrees"
                )
            relative_entry = _safe_pin_relative_path(
                entry["path"], f"pinned vanilla manifest {group}[{index}].path"
            )
            if (
                relative_entry.as_posix() != expected_path
                or entry["sha256"] != expected_sha256
                or not isinstance(entry["purpose"], str)
                or not entry["purpose"].strip()
            ):
                raise AcceptanceError(
                    f"pinned vanilla manifest {group}[{index}] identity disagrees"
                )
    return value


def _enabled_mods(user_data: Path) -> tuple[str, ...]:
    path = user_data / "dlc_load.json"
    if not path.is_file():
        return ()
    value = _dlc_load(user_data)
    return tuple(str(item) for item in value["enabled_mods"])


def _dlc_load(user_data: Path) -> dict[str, object]:
    path = user_data / "dlc_load.json"
    if not path.is_file():
        raise AcceptanceError(f"dlc_load.json is missing: {path}")
    try:
        value = _strict_json_loads(
            path.read_text(encoding="utf-8-sig"), "dlc_load.json"
        )
    except OSError as exc:
        raise AcceptanceError(f"cannot read dlc_load.json: {exc}") from exc
    if not isinstance(value, dict):
        raise AcceptanceError("dlc_load.json must contain an object")
    if list(value) != ["enabled_mods", "disabled_dlcs"]:
        raise AcceptanceError(
            "dlc_load.json must contain exactly enabled_mods then disabled_dlcs"
        )
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
        marker_value = _strict_json_loads(
            marker.read_text(encoding="utf-8"), "acceptance snapshot marker"
        )
    except OSError as exc:
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
    normalized_manifest = tuple(
        _normalized_manifest_record(item) for item in manifest
    )
    if len({item[0] for item in normalized_manifest}) != len(normalized_manifest):
        raise AcceptanceError(f"acceptance snapshot marker repeats a path: {marker}")
    committed_manifest = _git_snapshot_manifest_records(component, source_revision)
    if normalized_manifest != committed_manifest:
        raise AcceptanceError(
            "acceptance snapshot manifest is not the exact runtime whitelist "
            f"derived from Git commit {source_revision}: {payload}"
        )
    committed_records = [
        {"path": path, "bytes": size, "sha256": digest}
        for path, size, digest in committed_manifest
    ]
    recomputed = _snapshot_fingerprint_for_records(
        component, committed_records, source_revision
    )
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
    if str(scenario.get("id", "")).upper() == "PROBE":
        if phase not in {None, "default"}:
            raise AcceptanceError("PROBE phase is canonically named 'default'")
        contract = scenario.get("session_contract", scenario.get("contract", {}))
        if not isinstance(contract, dict):
            raise AcceptanceError("invalid PROBE session contract")
        return contract, "default"
    if phase:
        raise AcceptanceError(f"{scenario['id']} does not define session phases")
    contract = scenario.get("session_contract", scenario.get("contract", {}))
    if not isinstance(contract, dict):
        raise AcceptanceError(f"invalid session contract: {scenario['id']}")
    return contract, None


def _scenario_contract_identity(
    scenario: dict[str, object], phase: str | None
) -> tuple[dict[str, object], str]:
    contract, selected_phase = _scenario_session_contract(scenario, phase)
    identity: dict[str, object] = {
        "scenario_id": scenario["id"],
        "phase": selected_phase,
        "scenario": scenario,
        "session_contract": contract,
    }
    return identity, _object_sha256(identity)


EVIDENCE_ARTIFACT_KINDS = frozenset(
    {
        "screenshot",
        "screenshot_set",
        "assertion_manifest",
        "conditional_static_gate_output",
        "evidence_index",
        "save",
        "external_save",
        "log",
        "log_excerpt",
        "hash_manifest",
        "checklist",
        "observer_notes",
        "process_observation",
        "settings",
        "static_gate_output",
        "text",
        "provenance",
        "vfs_inventory",
        "ledger_entry",
    }
)


def _raw_required_artifacts(
    contract: dict[str, object],
) -> dict[str, dict[str, object]]:
    raw = contract.get("required_artifacts")
    if not isinstance(raw, list) or not raw:
        raise AcceptanceError("schema-2 contract requires non-empty required_artifacts")
    roles: dict[str, dict[str, object]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise AcceptanceError("required_artifacts entry schema disagrees")
        role = item.get("role")
        kind = item.get("kind")
        if (
            not isinstance(role, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_]{1,95}", role)
            or role in roles
            or not isinstance(kind, str)
            or kind not in EVIDENCE_ARTIFACT_KINDS
        ):
            raise AcceptanceError(f"invalid or duplicate required artifact: {item!r}")
        supports = item.get("supports_assertion_ids")
        if (
            not isinstance(supports, list)
            or not supports
            or len(supports) != len(set(supports))
            or not all(
                isinstance(assertion_id, str)
                and re.fullmatch(r"[a-z0-9][a-z0-9_]{2,95}", assertion_id)
                for assertion_id in supports
            )
            or item.get("distinct") is not True
        ):
            raise AcceptanceError(
                "every required artifact must declare a non-empty unique "
                f"supports_assertion_ids list and distinct=true: {item!r}"
            )
        if kind == "screenshot_set":
            min_items = item.get("min_items")
            if (
                set(item)
                != {
                    "role",
                    "kind",
                    "supports_assertion_ids",
                    "distinct",
                    "min_items",
                    "case_ids",
                }
                or isinstance(min_items, bool)
                or not isinstance(min_items, int)
                or min_items < 1
            ):
                raise AcceptanceError(
                    f"screenshot_set requires exact case binding and min_items >= 1: {item!r}"
                )
            case_ids = item.get("case_ids")
            if (
                not isinstance(case_ids, list)
                or len(case_ids) != min_items
                or len(case_ids) != len(set(case_ids))
                or not all(
                    isinstance(case_id, str)
                    and re.fullmatch(r"[a-z0-9][a-z0-9_]{1,95}", case_id)
                    for case_id in case_ids
                )
            ):
                raise AcceptanceError(
                    f"screenshot_set case_ids must uniquely cover min_items: {item!r}"
                )
        elif set(item) != {
            "role",
            "kind",
            "supports_assertion_ids",
            "distinct",
        }:
            raise AcceptanceError(
                f"only screenshot_set may declare min_items: {item!r}"
            )
        roles[role] = dict(item)
    return roles


def _raw_required_artifact_roles(contract: dict[str, object]) -> dict[str, str]:
    return {
        role: str(spec["kind"])
        for role, spec in _raw_required_artifacts(contract).items()
    }


def _scenario_phase_exists(scenario: dict[str, object], phase: str | None) -> str | None:
    if (
        phase == "default"
        and str(scenario.get("id", "")).upper() != "PROBE"
        and not scenario.get("session_phases")
    ):
        return None
    _, selected = _scenario_session_contract(scenario, phase)
    return selected


def _verified_runtime_oracle(
    scenario: dict[str, object],
    artifact_specs: dict[str, dict[str, object]],
    assertion_ids: Sequence[str],
    *,
    repo: Path | None = None,
    game_root: Path | None = None,
    verify_sources: bool,
) -> dict[str, object]:
    """Translate the independent oracle validator into acceptance failures."""

    canonical_repo = repo or Path(__file__).resolve().parents[3]
    canonical_game = game_root or DEFAULT_GAME_ROOT
    try:
        return verify_runtime_oracle(
            scenario,
            artifact_specs,
            assertion_ids,
            canonical_repo,
            canonical_game,
            verify_sources=verify_sources,
        )
    except (OracleContractError, OSError) as exc:
        raise AcceptanceError(f"R12 runtime oracle contract failed: {exc}") from exc


def _normalized_evidence_contract(
    scenario: dict[str, object], phase: str | None
) -> dict[str, object]:
    is_closure = str(scenario.get("id", "")).upper() == "R13"
    if is_closure:
        if phase not in {None, "closure"} or scenario.get("runnable") is not False:
            raise AcceptanceError("R13 is the one non-runnable closure contract")
        contract = scenario.get("closure_contract")
        if not isinstance(contract, dict):
            raise AcceptanceError("R13 has no closure_contract object")
        selected_phase = "closure"
    else:
        contract, selected_phase = _scenario_session_contract(scenario, phase)
    matrix = _scenario_matrix()
    if matrix.get("schema") != 2:
        raise AcceptanceError("schema-4 sessions require runtime matrix schema 2")
    expected_parent_compatibility = {
        "collection_schema": COLLECTION_SCHEMA,
        "same_matrix_sha256": True,
        "same_current_candidate_revision": True,
        "same_game_pins": True,
        "same_canonical_roots": True,
        "ready_for_lead_review": True,
    }
    if (
        matrix.get("parent_collection_compatibility_requirements")
        != expected_parent_compatibility
    ):
        raise AcceptanceError(
            "runtime matrix parent-collection compatibility contract disagrees"
        )

    acceptance = scenario.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        raise AcceptanceError(f"{scenario['id']} has no structured acceptance assertions")
    acceptance_by_id: dict[str, str] = {}
    for item in acceptance:
        if not isinstance(item, dict) or set(item) != {"id", "text"}:
            raise AcceptanceError(f"{scenario['id']} acceptance schema disagrees")
        assertion_id = item.get("id")
        text_value = item.get("text")
        if (
            not isinstance(assertion_id, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_]{2,95}", assertion_id)
            or assertion_id in acceptance_by_id
            or not isinstance(text_value, str)
            or not text_value.strip()
        ):
            raise AcceptanceError(f"invalid or duplicate acceptance assertion: {item!r}")
        acceptance_by_id[assertion_id] = text_value

    assertion_ids = contract.get("assertion_ids")
    if (
        not isinstance(assertion_ids, list)
        or not assertion_ids
        or not all(isinstance(item, str) for item in assertion_ids)
        or len(assertion_ids) != len(set(assertion_ids))
        or not set(assertion_ids).issubset(acceptance_by_id)
    ):
        raise AcceptanceError(
            f"{scenario['id']} {selected_phase} assertion_ids do not close over acceptance"
        )

    all_referenced: set[str] = set()
    phase_contracts = scenario.get("session_phases")
    if is_closure:
        candidates = (contract,)
    elif isinstance(phase_contracts, dict) and phase_contracts:
        candidates = phase_contracts.values()
    else:
        candidates = (scenario.get("session_contract"),)
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(
            candidate.get("assertion_ids"), list
        ):
            raise AcceptanceError(f"{scenario['id']} has an invalid assertion contract")
        all_referenced.update(str(item) for item in candidate["assertion_ids"])
    if all_referenced != set(acceptance_by_id):
        raise AcceptanceError(
            f"{scenario['id']} phase assertion union disagrees with acceptance ids"
        )

    artifact_specs = _raw_required_artifacts(contract)
    artifact_roles = {
        role: str(spec["kind"]) for role, spec in artifact_specs.items()
    }
    supported_assertions: set[str] = set()
    for role, spec in artifact_specs.items():
        supports = set(str(item) for item in spec["supports_assertion_ids"])
        if not supports.issubset(assertion_ids):
            raise AcceptanceError(
                f"artifact role {role} claims assertions outside its session contract"
            )
        supported_assertions.update(supports)
    if supported_assertions != set(assertion_ids):
        raise AcceptanceError(
            "required artifact supports_assertion_ids union must cover every "
            "session assertion exactly within the phase"
        )

    raw_blockers = scenario.get("blockers", [])
    if not isinstance(raw_blockers, list):
        raise AcceptanceError(f"{scenario['id']} blockers must be a list")
    blocker_ids: set[str] = set()
    blockers: list[dict[str, object]] = []
    blocker_keys = {
        "id",
        "type",
        "status",
        "blocks_assertion_ids",
        "prevents_ready_for_lead_review",
        "resolution_requirement",
    }
    for item in raw_blockers:
        if not isinstance(item, dict) or set(item) != blocker_keys:
            raise AcceptanceError(
                f"{scenario['id']} blocker schema disagrees: {item!r}"
            )
        blocker_id = item.get("id")
        blocker_type = item.get("type")
        status_value = item.get("status")
        blocked_ids = item.get("blocks_assertion_ids")
        resolution = item.get("resolution_requirement")
        if (
            not isinstance(blocker_id, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_]{2,95}", blocker_id)
            or blocker_id in blocker_ids
            or not isinstance(blocker_type, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_]{2,95}", blocker_type)
            or status_value not in {"PENDING", "BLOCKED"}
            or not isinstance(blocked_ids, list)
            or not blocked_ids
            or len(blocked_ids) != len(set(blocked_ids))
            or not all(isinstance(value, str) for value in blocked_ids)
            or not set(blocked_ids).issubset(acceptance_by_id)
            or item.get("prevents_ready_for_lead_review") is not True
            or not isinstance(resolution, str)
            or not resolution.strip()
        ):
            raise AcceptanceError(
                f"{scenario['id']} blocker identity/status/references disagree: {item!r}"
            )
        blocker_ids.add(blocker_id)
        if set(blocked_ids) & set(assertion_ids):
            blockers.append(dict(item))
    prefix = contract.get("artifact_prefix")
    if is_closure:
        if prefix is not None:
            raise AcceptanceError("R13 closure must not declare a runtime artifact prefix")
        minimum_screenshots = 0
        minimum_saves = 0
    else:
        if not isinstance(prefix, str) or not re.fullmatch(r"JXP_ACC_[A-Z0-9_]+_", prefix):
            raise AcceptanceError(f"invalid artifact_prefix: {prefix!r}")
        for count_key in ("minimum_screenshots", "minimum_saves"):
            value = contract.get(count_key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AcceptanceError(f"invalid {count_key}: {value!r}")
        minimum_screenshots = int(contract["minimum_screenshots"])
        minimum_saves = int(contract["minimum_saves"])
    expected_screenshots = sum(
        int(spec.get("min_items", 1))
        for spec in artifact_specs.values()
        if spec["kind"] in {"screenshot", "screenshot_set"}
    )
    expected_saves = sum(
        1 for spec in artifact_specs.values() if spec["kind"] == "save"
    )
    if minimum_screenshots != expected_screenshots:
        raise AcceptanceError(
            "minimum_screenshots must equal screenshot singles plus all "
            f"screenshot_set min_items; expected {expected_screenshots}"
        )
    if minimum_saves != expected_saves:
        raise AcceptanceError(
            f"minimum_saves must equal required save roles; expected {expected_saves}"
        )

    raw_parents = contract.get("required_parent_collections", [])
    if not isinstance(raw_parents, list):
        raise AcceptanceError("required_parent_collections must be a list")
    parents: list[dict[str, object]] = []
    parent_roles: dict[str, dict[str, object]] = {}
    for item in raw_parents:
        if not isinstance(item, dict) or set(item) != {"role", "scenario", "phase"}:
            raise AcceptanceError("required_parent_collections entry schema disagrees")
        role = item.get("role")
        parent_scenario_id = item.get("scenario")
        parent_phase = item.get("phase")
        if (
            not isinstance(role, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_]{1,95}", role)
            or role in parent_roles
            or not isinstance(parent_scenario_id, str)
            or not isinstance(parent_phase, str)
        ):
            raise AcceptanceError(f"invalid parent collection requirement: {item!r}")
        target = _scenario(parent_scenario_id)
        normalized_parent_phase = _scenario_phase_exists(target, parent_phase)
        normalized = {
            "role": role,
            "scenario": target["id"],
            "phase": normalized_parent_phase,
        }
        parents.append(normalized)
        parent_roles[role] = normalized

    raw_inputs = contract.get("required_input_saves", [])
    if not isinstance(raw_inputs, list):
        raise AcceptanceError("required_input_saves must be a list")
    inputs: list[dict[str, object]] = []
    input_roles: set[str] = set()
    for item in raw_inputs:
        if not isinstance(item, dict) or not isinstance(item.get("role"), str):
            raise AcceptanceError("required_input_saves entry schema disagrees")
        role = str(item["role"])
        if (
            not re.fullmatch(r"[a-z0-9][a-z0-9_]{1,95}", role)
            or role in input_roles
        ):
            raise AcceptanceError(f"invalid or duplicate input-save role: {role!r}")
        input_roles.add(role)
        if item.get("source") == "external_original":
            if set(item) != {
                "role",
                "source",
                "provenance_role",
                "hash_role",
                "required_provenance_fields",
            }:
                raise AcceptanceError("external input-save schema disagrees")
            provenance_role = item.get("provenance_role")
            hash_role = item.get("hash_role")
            provenance_fields = item.get("required_provenance_fields")
            if (
                artifact_roles.get(role) != "external_save"
                or artifact_roles.get(str(provenance_role)) != "provenance"
                or artifact_roles.get(str(hash_role)) != "hash_manifest"
                or not isinstance(provenance_fields, list)
                or not provenance_fields
                or len(provenance_fields) != len(set(provenance_fields))
                or not all(
                    isinstance(field, str)
                    and re.fullmatch(r"[a-z][a-z0-9_]{1,95}", field)
                    for field in provenance_fields
                )
            ):
                raise AcceptanceError("external input-save evidence role closure disagrees")
            inputs.append(dict(item))
            continue
        if set(item) != {"role", "parent_collection_role", "parent_artifact_role"}:
            raise AcceptanceError("parent input-save schema disagrees")
        parent_role = item.get("parent_collection_role")
        parent_artifact_role = item.get("parent_artifact_role")
        if not isinstance(parent_role, str) or parent_role not in parent_roles:
            raise AcceptanceError("input save references an absent parent collection role")
        parent_requirement = parent_roles[parent_role]
        target_scenario = _scenario(str(parent_requirement["scenario"]))
        target_contract, _ = _scenario_session_contract(
            target_scenario, str(parent_requirement["phase"])
        )
        target_roles = _raw_required_artifact_roles(target_contract)
        if target_roles.get(str(parent_artifact_role)) not in {"save", "external_save"}:
            raise AcceptanceError("input save references a non-save parent artifact role")
        inputs.append(dict(item))

    raw_fixtures = contract.get("required_fixture_uses", [])
    if not isinstance(raw_fixtures, list):
        raise AcceptanceError("required_fixture_uses must be a list")
    fixtures: list[dict[str, object]] = []
    fixture_names: set[str] = set()
    for item in raw_fixtures:
        required_fixture_keys = {
            "name",
            "console_screenshot_role",
            "before_save_role",
            "after_save_role",
        }
        if not isinstance(item, dict) or set(item) != required_fixture_keys:
            raise AcceptanceError("required_fixture_uses entry schema disagrees")
        name = item.get("name")
        console_role = item.get("console_screenshot_role")
        before_role = item.get("before_save_role")
        after_role = item.get("after_save_role")
        if (
            not isinstance(name, str)
            or name in fixture_names
            or artifact_roles.get(str(console_role)) not in {"screenshot", "screenshot_set"}
            or artifact_roles.get(str(before_role)) != "save"
            or artifact_roles.get(str(after_role)) != "save"
            or before_role == after_role
        ):
            raise AcceptanceError(f"fixture-use role closure disagrees: {item!r}")
        _run_fixture_record(name)
        fixture_names.add(name)
        fixtures.append(dict(item))

    if set(parent_roles) & set(artifact_roles):
        raise AcceptanceError("parent and artifact role namespaces overlap")
    non_external_inputs = {
        str(item["role"]) for item in inputs if item.get("source") != "external_original"
    }
    if non_external_inputs & (set(parent_roles) | set(artifact_roles)):
        raise AcceptanceError("input role namespace unexpectedly overlaps another role")

    runtime_oracle: dict[str, object] | None = None
    if str(scenario["id"]).upper() == "R12":
        runtime_oracle = _verified_runtime_oracle(
            scenario,
            artifact_specs,
            [str(item) for item in assertion_ids],
            verify_sources=False,
        )
    elif any(
        key in scenario for key in ("exact_oracle", "typed_case_schema", "typed_cases")
    ):
        raise AcceptanceError("only R12 may declare a runtime oracle contract")

    return {
        "scenario_id": scenario["id"],
        "phase": selected_phase,
        "prefix": prefix,
        "minimum_screenshots": minimum_screenshots,
        "minimum_saves": minimum_saves,
        "runnable": not is_closure,
        "assertions": [
            {"id": assertion_id, "text": acceptance_by_id[assertion_id]}
            for assertion_id in assertion_ids
        ],
        "artifact_roles": artifact_roles,
        "artifact_specs": artifact_specs,
        "parents": parents,
        "inputs": inputs,
        "fixtures": fixtures,
        "blockers": blockers,
        "runtime_oracle": runtime_oracle,
    }


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
    if set(by_component) != required:
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
    user_data: Path, descriptors: Sequence[Path], *, allow_empty: bool = False
) -> list[dict[str, object]]:
    records = [
        _installed_snapshot_record(raw.expanduser().resolve(), user_data)
        for raw in descriptors
    ]
    if not records and not allow_empty:
        raise AcceptanceError("scenario configuration requires at least one descriptor")
    return records


def _configure_receipt_path(user_data: Path) -> Path:
    return user_data / CONFIGURE_RECEIPT_NAME


def _canonical_snapshot_order(
    snapshots: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    return sorted(
        snapshots,
        key=lambda item: ({"main": 0, "map": 1}.get(str(item["component"]), 99)),
    )


def _expected_dlc_configuration(
    scenario: dict[str, object],
    phase: str | None,
    snapshots: Sequence[dict[str, object]],
) -> dict[str, object]:
    ordered = _canonical_snapshot_order(snapshots)
    return {
        "enabled_mods": [
            f"mod/{Path(str(item['descriptor']['path'])).name}" for item in ordered
        ],
        "disabled_dlcs": list(_required_disabled_dlcs(scenario, phase)),
    }


def _write_configure_receipt(
    user_data: Path,
    scenario: dict[str, object],
    phase: str | None,
    candidate_revision: str,
    snapshots: Sequence[dict[str, object]],
    configuration: dict[str, object],
) -> dict[str, object]:
    _, contract_sha256 = _scenario_contract_identity(scenario, phase)
    payload: dict[str, object] = {
        "schema": RECEIPT_SCHEMA,
        "nonce": secrets.token_hex(32),
        "created_at": _utc_now().isoformat(),
        "scenario_id": scenario["id"],
        "phase": phase,
        "candidate_revision": candidate_revision,
        "contract_sha256": contract_sha256,
        "user_data": str(user_data),
        "configuration": configuration,
        "snapshots": list(_canonical_snapshot_order(snapshots)),
        "dlc_load_state": _path_state(user_data / "dlc_load.json", hash_files=True),
    }
    receipt = _sealed_value(payload, "receipt_sha256")
    target = _configure_receipt_path(user_data)
    if os.path.lexists(target) and (
        not target.is_file() or _is_link_or_junction(target)
    ):
        raise AcceptanceError(f"configure receipt target is not ordinary: {target}")
    _atomic_write_json(target, receipt)
    return receipt


def _verified_configure_receipt(
    user_data: Path,
    scenario: dict[str, object],
    phase: str | None,
    candidate_revision: str,
    snapshots: Sequence[dict[str, object]],
    configuration: dict[str, object],
) -> dict[str, object]:
    target = _configure_receipt_path(user_data)
    receipt = _verify_self_seal(
        _read_json_object(target, "configure receipt"),
        "receipt_sha256",
        "configure receipt",
    )
    required = {
        "schema",
        "nonce",
        "created_at",
        "scenario_id",
        "phase",
        "candidate_revision",
        "contract_sha256",
        "user_data",
        "configuration",
        "snapshots",
        "dlc_load_state",
        "receipt_sha256",
    }
    if set(receipt) != required or receipt.get("schema") != RECEIPT_SCHEMA:
        raise AcceptanceError("configure receipt schema disagrees")
    _, contract_sha256 = _scenario_contract_identity(scenario, phase)
    expected = {
        "scenario_id": scenario["id"],
        "phase": phase,
        "candidate_revision": candidate_revision,
        "contract_sha256": contract_sha256,
        "user_data": str(user_data),
        "configuration": configuration,
        "snapshots": list(_canonical_snapshot_order(snapshots)),
        "dlc_load_state": _path_state(user_data / "dlc_load.json", hash_files=True),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise AcceptanceError(f"configure receipt {key} disagrees")
    return receipt


def configure_playset(
    user_data: Path,
    scenario_id: str,
    phase: str | None,
    descriptors: Sequence[Path],
    candidate_revision: str | None = None,
) -> dict[str, object]:
    """Atomically configure only an isolated acceptance root for one scenario."""
    _assert_processes_stopped()
    user_data = _require_canonical_acceptance_user_data(user_data)
    _assert_no_active_session(user_data, "configure the playset")
    scenario = _scenario(scenario_id)
    if str(scenario["id"]).upper() == "R13":
        raise AcceptanceError("R13 is release closure and has no runtime playset")
    candidate_revision = candidate_revision or _current_candidate_revision()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_revision):
        raise AcceptanceError(
            f"invalid current candidate revision: {candidate_revision!r}"
        )
    contract, _ = _scenario_session_contract(scenario, phase)
    required_components = contract.get("required_components", ())
    if not isinstance(required_components, list):
        raise AcceptanceError("required_components must be a list")
    snapshots = _verified_session_snapshots(
        user_data, descriptors, allow_empty=not required_components
    )
    selected_phase = _verify_session_snapshot_contract(
        scenario, phase, snapshots, candidate_revision
    )
    ordered = _canonical_snapshot_order(snapshots)
    config = _expected_dlc_configuration(
        scenario, selected_phase, ordered
    )
    target = user_data / "dlc_load.json"
    previous = None
    if os.path.lexists(target):
        if not target.is_file() or _is_link_or_junction(target):
            raise AcceptanceError(f"refusing non-ordinary dlc_load target: {target}")
        _dlc_load(user_data)
        previous = _path_state(target, hash_files=True)
    _atomic_write_json(target, config, sort_keys=False)
    if _dlc_load(user_data) != config:
        raise AcceptanceError("isolated dlc_load write verification failed")
    receipt = _write_configure_receipt(
        user_data,
        scenario,
        selected_phase,
        candidate_revision,
        ordered,
        config,
    )
    return {
        "scenario": scenario["id"],
        "phase": selected_phase,
        "user_data": str(user_data),
        "candidate_revision": candidate_revision,
        "configuration": config,
        "previous_dlc_load": previous,
        "dlc_load": _path_state(target, hash_files=True),
        "configure_receipt": {
            "path": str(_configure_receipt_path(user_data)),
            "receipt_sha256": receipt["receipt_sha256"],
            "nonce": receipt["nonce"],
        },
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


def _twelve_pin_records(repo: Path, game_root: Path) -> list[dict[str, object]]:
    """Return the exact three protocol plus nine gameplay pins for EU4 1.37.5."""
    repo, game_root = _require_canonical_runtime_roots(repo, game_root)
    manifest = _load_pin_manifest(repo)
    if tuple(PINNED_PROTOCOL_FILES) != PINNED_PROTOCOL_PATHS:
        raise AcceptanceError("pinned protocol path set or order disagrees")
    pin_records: list[dict[str, object]] = []
    for relative_value in PINNED_PROTOCOL_PATHS:
        expected = PINNED_PROTOCOL_FILES[relative_value]
        relative = _safe_pin_relative_path(relative_value, "protocol pin path")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise AcceptanceError(f"protocol pin hash is invalid: {relative_value}")
        source = _pin_path_under_root(game_root, relative, "protocol pin")
        actual = _sha256_file(source) if source.is_file() else None
        pin_records.append(
            {
                "path": relative.as_posix(),
                "expected": expected,
                "actual": actual,
                "matched": actual == expected,
            }
        )
    for group, expected_entries in PINNED_GAMEPLAY_GROUPS:
        entries = manifest[group]
        if not isinstance(entries, list):
            raise AcceptanceError(f"pinned gameplay group is malformed: {group}")
        for record, (expected_path, expected) in zip(
            entries, expected_entries, strict=True
        ):
            if not isinstance(record, dict):
                raise AcceptanceError(f"pinned gameplay record is malformed: {group}")
            relative = _safe_pin_relative_path(record["path"], "gameplay pin path")
            if relative.as_posix() != expected_path or record["sha256"] != expected:
                raise AcceptanceError(f"pinned gameplay identity disagrees: {expected_path}")
            source = _pin_path_under_root(game_root, relative, "gameplay pin")
            actual = _sha256_file(source) if source.is_file() else None
            pin_records.append(
                {
                    "path": relative.as_posix(),
                    "expected": expected,
                    "actual": actual,
                    "matched": actual == expected,
                }
            )
    paths = [str(item["path"]) for item in pin_records]
    expected_paths = [
        *PINNED_PROTOCOL_PATHS,
        *(
            relative
            for _, entries in PINNED_GAMEPLAY_GROUPS
            for relative, _ in entries
        ),
    ]
    if paths != expected_paths or len(paths) != 12 or len(paths) != len(set(paths)):
        raise AcceptanceError(
            "pinned runtime protocol must contain the exact 12 ordered unique paths"
        )
    return pin_records


def _verified_twelve_pins(repo: Path, game_root: Path) -> list[dict[str, object]]:
    records = _twelve_pin_records(repo, game_root)
    mismatches = [str(item["path"]) for item in records if not item["matched"]]
    if mismatches:
        raise AcceptanceError(
            "pinned EU4 protocol/gameplay files disagree: " + ", ".join(mismatches)
        )
    return records


def preflight(repo: Path, game_root: Path, user_data: Path) -> dict[str, object]:
    repo, game_root = _require_canonical_runtime_roots(repo, game_root)
    user_data = _require_canonical_daily_user_data(user_data, game_root)
    if _is_relative_to(repo, game_root):
        raise AcceptanceError("repository must not live inside the EU4 installation")
    pin_records = _twelve_pin_records(repo, game_root)
    manifest = _load_pin_manifest(repo)
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
    value = _strict_json_loads(
        _scenario_matrix_path().read_text(encoding="utf-8"),
        "runtime scenario matrix",
    )
    if (
        not isinstance(value, dict)
        or value.get("schema") not in {1, 2}
        or not isinstance(value.get("scenarios"), list)
    ):
        raise AcceptanceError("runtime scenario matrix must contain an object")
    return value


def _scenario_matrix_sha256() -> str:
    path = _scenario_matrix_path()
    _scenario_matrix()
    return _sha256_file(path)


def _current_candidate_revision() -> str:
    value = _scenario_matrix().get("current_candidate_revision")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise AcceptanceError(
            "runtime matrix has no pinned 40-character current candidate revision"
        )
    return value


def _scenario(scenario_id: str) -> dict[str, object]:
    matrix = _scenario_matrix()
    normalized_id = scenario_id.upper()
    if normalized_id == "PROBE":
        for key in ("PROBE", "probe", "protocol_probe"):
            raw = matrix.get(key)
            if isinstance(raw, dict):
                scenario = dict(raw)
                scenario.setdefault("id", "PROBE")
                if scenario.get("id") != "PROBE":
                    raise AcceptanceError("top-level PROBE scenario has a conflicting id")
                return scenario
    for scenario in matrix["scenarios"]:
        if not isinstance(scenario, dict) or not isinstance(scenario.get("id"), str):
            raise AcceptanceError("runtime scenario matrix contains a malformed scenario")
        if str(scenario["id"]).upper() == normalized_id:
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


def _sampled_content_sha256(path: Path) -> str:
    """Hash bounded content windows for large daily files plus their exact size."""
    size = path.stat().st_size
    window = 64 * 1024
    offsets = sorted({0, max(0, size // 2 - window // 2), max(0, size - window)})
    digest = sha256()
    digest.update(str(size).encode("ascii"))
    with path.open("rb") as stream:
        for offset in offsets:
            stream.seek(offset)
            payload = stream.read(window)
            digest.update(b"\0")
            digest.update(str(offset).encode("ascii"))
            digest.update(b"\0")
            digest.update(payload)
    return digest.hexdigest()


def _path_state(
    path: Path,
    *,
    hash_files: bool,
    sample_large_files: bool = False,
) -> dict[str, object]:
    """Record exact presence/type state without following any reparse point."""
    absolute = path.expanduser().absolute()
    if not os.path.lexists(absolute):
        return {"path": str(absolute), "kind": "absent"}
    if _is_link_or_junction(absolute):
        raise AcceptanceError(f"guarded VFS path cannot be a link: {absolute}")
    if absolute.is_file():
        record: dict[str, object] = {
            "path": str(absolute),
            "kind": "file",
            "bytes": absolute.stat().st_size,
            "mtime_ns": absolute.stat().st_mtime_ns,
        }
        if hash_files:
            if sample_large_files and record["bytes"] > 4 * 1024 * 1024:
                record["content_hash_mode"] = "sampled-three-64KiB-windows"
                record["content_sha256"] = _sampled_content_sha256(absolute)
            else:
                record["content_hash_mode"] = "full"
                record["sha256"] = _sha256_file(absolute)
        return record
    if not absolute.is_dir():
        raise AcceptanceError(f"guarded VFS path is not ordinary: {absolute}")
    entries: list[dict[str, object]] = []
    for child in sorted(absolute.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if _is_link_or_junction(child):
            raise AcceptanceError(f"guarded VFS tree cannot contain a link: {child}")
        relative = child.relative_to(absolute).as_posix()
        child_stat = child.stat()
        if child.is_dir():
            entries.append(
                {
                    "path": relative,
                    "kind": "directory",
                    "mtime_ns": child_stat.st_mtime_ns,
                }
            )
        elif child.is_file():
            entry: dict[str, object] = {
                "path": relative,
                "kind": "file",
                "bytes": child_stat.st_size,
                "mtime_ns": child_stat.st_mtime_ns,
            }
            if hash_files:
                if sample_large_files and entry["bytes"] > 4 * 1024 * 1024:
                    entry["content_hash_mode"] = "sampled-three-64KiB-windows"
                    entry["content_sha256"] = _sampled_content_sha256(child)
                else:
                    entry["content_hash_mode"] = "full"
                    entry["sha256"] = _sha256_file(child)
            entries.append(entry)
        else:
            raise AcceptanceError(f"guarded VFS tree member is not ordinary: {child}")
    return {
        "path": str(absolute),
        "kind": "directory",
        "mtime_ns": absolute.stat().st_mtime_ns,
        "entries": entries,
    }


def _isolated_configuration_inventory(user_data: Path) -> list[dict[str, object]]:
    return [
        _path_state(user_data / relative, hash_files=True)
        for relative in ISOLATED_CONFIGURATION_PATHS
    ]


def _daily_vfs_inventory(daily_user_data: Path) -> list[dict[str, object]]:
    daily_user_data = _require_ordinary_directory(
        daily_user_data, "daily EU4 user-data root"
    )
    inventory: list[dict[str, object]] = []
    seen: set[str] = set()
    critical_names = {relative.casefold() for relative in DAILY_CRITICAL_VFS_PATHS}
    for path in sorted(
        daily_user_data.iterdir(), key=lambda item: item.name.casefold()
    ):
        seen.add(path.name.casefold())
        # The installed-mod tree is large and is not a normal engine-output
        # surface. Record its complete recursive path/type/size/mtime topology,
        # while content-hashing every other daily top-level tree.
        inventory.append(
            _path_state(
                path,
                hash_files=path.name.casefold() != "mod",
                # Configuration files such as launcher-v2.sqlite must retain a
                # full-content digest even when larger than the sampling
                # threshold. Large files inside ordinary output directories
                # remain bounded, but their exact size and mtime are sealed.
                sample_large_files=not (
                    path.is_file() and path.name.casefold() in critical_names
                ),
            )
        )
    for relative in DAILY_CRITICAL_VFS_PATHS:
        if relative.casefold() not in seen:
            critical_path = daily_user_data / relative
            inventory.append(
                _path_state(
                    critical_path,
                    hash_files=True,
                    sample_large_files=not critical_path.is_file(),
                )
            )
    return inventory


def _acceptance_runtime_output_inventory(user_data: Path) -> list[dict[str, object]]:
    return [
        _path_state(user_data / relative, hash_files=True, sample_large_files=True)
        for relative in ACCEPTANCE_RUNTIME_OUTPUT_PATHS
    ]


def _artifact_source_roots(user_data: Path) -> tuple[Path, ...]:
    roots = (
        user_data,
        user_data / "Screenshots",
        user_data / "save games",
    )
    for root in roots:
        if not os.path.lexists(root):
            continue
        if not root.is_dir() or _is_link_or_junction(root):
            raise AcceptanceError(
                f"artifact source root must be an ordinary directory: {root}"
            )
    return roots


def _artifact_inventory(user_data: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    roots = _artifact_source_roots(user_data)
    candidates: set[Path] = set()
    for root in roots[1:]:
        if root.is_dir():
            for path in root.iterdir():
                if _is_link_or_junction(path):
                    raise AcceptanceError(f"artifact source cannot be a link: {path}")
                if path.is_file():
                    candidates.add(path)
    candidates.update(
        path
        for path in user_data.iterdir()
        if path.is_file() and path.name.startswith("JXP_ACC_")
    )
    for path in sorted(candidates, key=lambda item: str(item).casefold()):
        if _is_link_or_junction(path):
            raise AcceptanceError(f"artifact source cannot be a link: {path}")
        records.append(_file_record(path.resolve()))
    return records


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
    manifest = _strict_json_loads(
        manifest_path.read_text(encoding="utf-8"), "run-fixture manifest"
    )
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


def _run_fixture_record(name: str) -> dict[str, object]:
    for record in _verified_run_fixture_records():
        if record["name"] == name:
            return record
    raise AcceptanceError(f"unknown verified run fixture: {name}")


def _validated_image_dimensions(width: int, height: int, path: Path) -> None:
    if (
        width < MIN_SCREENSHOT_DIMENSION
        or height < MIN_SCREENSHOT_DIMENSION
        or width * height > MAX_SCREENSHOT_PIXELS
    ):
        raise AcceptanceError(
            f"screenshot dimensions are implausible for runtime evidence: "
            f"{width}x{height}: {path}"
        )


def _force_decode_windows_raster(
    path: Path, expected_width: int, expected_height: int
) -> str:
    """Force GDI+ to decode every JPEG/BMP pixel in a subprocess."""

    if os.name != "nt":
        raise AcceptanceError(
            f"full JPEG/BMP decoding requires the pinned Windows runtime: {path}"
        )
    script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$stream = [System.IO.File]::Open(
    $env:JXP_IMAGE_PATH,
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::Read
)
try {
    $image = [System.Drawing.Image]::FromStream($stream, $true, $true)
    try {
        $bitmap = [System.Drawing.Bitmap]::new($image)
        try {
            $rect = [System.Drawing.Rectangle]::new(0, 0, $bitmap.Width, $bitmap.Height)
            $data = $bitmap.LockBits(
                $rect,
                [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
                [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
            )
            try {
                $count = [Math]::Abs($data.Stride) * $data.Height
                $bytes = New-Object byte[] $count
                [System.Runtime.InteropServices.Marshal]::Copy(
                    $data.Scan0, $bytes, 0, $count
                )
                $sha = [System.Security.Cryptography.SHA256]::Create()
                try {
                    $digest = $sha.ComputeHash($bytes)
                    $hash = -join ($digest | ForEach-Object { $_.ToString('x2') })
                } finally {
                    $sha.Dispose()
                }
            } finally {
                $bitmap.UnlockBits($data)
            }
            [pscustomobject]@{
                width = $bitmap.Width
                height = $bitmap.Height
                decoded_sha256 = $hash
            } | ConvertTo-Json -Compress
        } finally {
            $bitmap.Dispose()
        }
    } finally {
        $image.Dispose()
    }
} finally {
    $stream.Dispose()
}
"""
    environment = dict(os.environ)
    environment["JXP_IMAGE_PATH"] = str(path)
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=30,
            env=environment,
            creationflags=creation_flags,
        )
        value = _strict_json_loads(completed.stdout.strip(), "decoded raster result")
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise AcceptanceError(f"raster decoder rejected {path}: {exc}") from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"width", "height", "decoded_sha256"}
        or value.get("width") != expected_width
        or value.get("height") != expected_height
        or not isinstance(value.get("decoded_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", value["decoded_sha256"])
    ):
        raise AcceptanceError(f"decoded raster dimensions/digest disagree: {path}")
    return str(value["decoded_sha256"])


def _validate_jpeg_payload(payload: bytes, path: Path) -> tuple[int, int]:
    if len(payload) < 128 or payload[:2] != b"\xff\xd8":
        raise AcceptanceError(f"JPEG artifact has an invalid SOI/header: {path}")
    position = 2
    width = height = 0
    saw_sof = False
    saw_sos = False
    quantization_tables: set[int] = set()
    huffman_tables: set[tuple[int, int]] = set()
    frame_components: dict[int, int] = {}
    entropy_bytes = 0
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while position < len(payload):
        if payload[position] != 0xFF:
            raise AcceptanceError(f"JPEG marker stream is malformed: {path}")
        marker_start = position
        while position < len(payload) and payload[position] == 0xFF:
            position += 1
        if position >= len(payload):
            raise AcceptanceError(f"JPEG marker is truncated: {path}")
        marker = payload[position]
        position += 1
        if marker == 0xD9:
            if position != len(payload):
                raise AcceptanceError(f"JPEG artifact has trailing bytes: {path}")
            if (
                not saw_sof
                or not saw_sos
                or not quantization_tables
                or not huffman_tables
                or entropy_bytes < 8
            ):
                raise AcceptanceError(f"JPEG lacks a decoded frame/scan payload: {path}")
            _validated_image_dimensions(width, height, path)
            return width, height
        if marker in {0x00, 0xD8} or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            raise AcceptanceError(f"unexpected JPEG marker outside scan: {path}")
        if position + 2 > len(payload):
            raise AcceptanceError(f"JPEG segment length is truncated: {path}")
        segment_length = struct.unpack(">H", payload[position : position + 2])[0]
        if segment_length < 2:
            raise AcceptanceError(f"JPEG segment length is invalid: {path}")
        segment_end = position + segment_length
        if segment_end > len(payload):
            raise AcceptanceError(f"JPEG segment body is truncated: {path}")
        segment = payload[position + 2 : segment_end]
        if marker == 0xDB:
            cursor = 0
            while cursor < len(segment):
                specification = segment[cursor]
                cursor += 1
                precision = specification >> 4
                table_id = specification & 0x0F
                table_bytes = 64 * (precision + 1)
                if (
                    precision not in {0, 1}
                    or table_id > 3
                    or cursor + table_bytes > len(segment)
                ):
                    raise AcceptanceError(f"JPEG DQT segment is invalid: {path}")
                quantization_tables.add(table_id)
                cursor += table_bytes
            if cursor != len(segment):
                raise AcceptanceError(f"JPEG DQT length disagrees: {path}")
        elif marker == 0xC4:
            cursor = 0
            while cursor < len(segment):
                if cursor + 17 > len(segment):
                    raise AcceptanceError(f"JPEG DHT segment is truncated: {path}")
                specification = segment[cursor]
                table_class = specification >> 4
                table_id = specification & 0x0F
                counts = segment[cursor + 1 : cursor + 17]
                symbol_count = sum(counts)
                cursor += 17
                if (
                    table_class not in {0, 1}
                    or table_id > 3
                    or symbol_count < 1
                    or symbol_count > 256
                    or cursor + symbol_count > len(segment)
                ):
                    raise AcceptanceError(f"JPEG DHT segment is invalid: {path}")
                huffman_tables.add((table_class, table_id))
                cursor += symbol_count
            if cursor != len(segment):
                raise AcceptanceError(f"JPEG DHT length disagrees: {path}")
        if marker in sof_markers:
            if saw_sof or len(segment) < 6 or segment[0] not in {8, 12}:
                raise AcceptanceError(f"JPEG SOF segment is invalid: {path}")
            height, width = struct.unpack(">HH", segment[1:5])
            components = segment[5]
            if components < 1 or len(segment) != 6 + 3 * components:
                raise AcceptanceError(f"JPEG SOF component table is invalid: {path}")
            for offset in range(6, len(segment), 3):
                component_id, sampling, table_id = segment[offset : offset + 3]
                horizontal = sampling >> 4
                vertical = sampling & 0x0F
                if (
                    component_id in frame_components
                    or horizontal not in {1, 2, 3, 4}
                    or vertical not in {1, 2, 3, 4}
                    or table_id > 3
                ):
                    raise AcceptanceError(
                        f"JPEG SOF component definition is invalid: {path}"
                    )
                frame_components[component_id] = table_id
            saw_sof = True
        position = segment_end
        if marker != 0xDA:
            continue
        if not saw_sof or len(segment) < 6:
            raise AcceptanceError(f"JPEG SOS appears before a valid frame: {path}")
        scan_components = segment[0]
        if (
            scan_components < 1
            or len(segment) != 4 + 2 * scan_components
            or scan_components > len(frame_components)
        ):
            raise AcceptanceError(f"JPEG SOS component table is invalid: {path}")
        seen_scan_components: set[int] = set()
        spectral_start = segment[-3]
        spectral_end = segment[-2]
        approximation = segment[-1]
        if spectral_start > spectral_end or spectral_end > 63 or approximation > 0xDD:
            raise AcceptanceError(f"JPEG SOS spectral selection is invalid: {path}")
        for offset in range(1, 1 + 2 * scan_components, 2):
            component_id = segment[offset]
            selectors = segment[offset + 1]
            dc_table = selectors >> 4
            ac_table = selectors & 0x0F
            if (
                component_id not in frame_components
                or component_id in seen_scan_components
                or dc_table > 3
                or ac_table > 3
                or frame_components[component_id] not in quantization_tables
                or (spectral_start == 0 and (0, dc_table) not in huffman_tables)
                or (spectral_end > 0 and (1, ac_table) not in huffman_tables)
            ):
                raise AcceptanceError(f"JPEG SOS table selection is invalid: {path}")
            seen_scan_components.add(component_id)
        saw_sos = True
        while position < len(payload):
            if payload[position] != 0xFF:
                entropy_bytes += 1
                position += 1
                continue
            next_position = position + 1
            while next_position < len(payload) and payload[next_position] == 0xFF:
                next_position += 1
            if next_position >= len(payload):
                raise AcceptanceError(f"JPEG entropy stream is truncated: {path}")
            scan_marker = payload[next_position]
            if scan_marker == 0x00:
                entropy_bytes += 1
                position = next_position + 1
                continue
            if 0xD0 <= scan_marker <= 0xD7:
                position = next_position + 1
                continue
            # Re-enter the outer marker parser for EOI or a progressive scan.
            position = marker_start = position
            break
    raise AcceptanceError(f"JPEG artifact has no terminal EOI marker: {path}")


def _validate_image_artifact(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    size = path.stat().st_size
    if size <= 0 or size > MAX_SCREENSHOT_FILE_BYTES:
        raise AcceptanceError(f"screenshot file size is unsafe: {path}")
    with path.open("rb") as stream:
        head = stream.read(64)
        if suffix in {".jpg", ".jpeg"}:
            width, height = _validate_jpeg_payload(path.read_bytes(), path)
            decoded_sha256 = _force_decode_windows_raster(path, width, height)
            return {
                "format": "jpeg",
                "width": width,
                "height": height,
                "decoded_sha256": decoded_sha256,
            }
    if suffix == ".png":
        payload = path.read_bytes()
        if len(payload) < 45 or payload[:8] != b"\x89PNG\r\n\x1a\n":
            raise AcceptanceError(f"PNG artifact has an invalid signature: {path}")
        offset = 8
        chunks: list[bytes] = []
        width = height = 0
        bit_depth = color_type = 0
        idat_payloads: list[bytes] = []
        saw_idat = False
        idat_closed = False
        saw_plte = False
        palette_entries = 0
        while offset < len(payload):
            if offset + 12 > len(payload):
                raise AcceptanceError(f"PNG artifact has a truncated chunk: {path}")
            length = struct.unpack(">I", payload[offset : offset + 4])[0]
            chunk_type = payload[offset + 4 : offset + 8]
            if (
                len(chunk_type) != 4
                or not all(
                    ord("A") <= value <= ord("Z")
                    or ord("a") <= value <= ord("z")
                    for value in chunk_type
                )
                or ord("a") <= chunk_type[2] <= ord("z")
            ):
                raise AcceptanceError(f"PNG chunk type is invalid: {path}")
            data_start = offset + 8
            data_end = data_start + length
            crc_end = data_end + 4
            if crc_end > len(payload):
                raise AcceptanceError(f"PNG artifact has a truncated chunk body: {path}")
            expected_crc = struct.unpack(">I", payload[data_end:crc_end])[0]
            actual_crc = zlib.crc32(chunk_type + payload[data_start:data_end]) & 0xFFFFFFFF
            if actual_crc != expected_crc:
                raise AcceptanceError(f"PNG artifact has a bad chunk CRC: {path}")
            chunks.append(chunk_type)
            if len(chunks) == 1:
                if chunk_type != b"IHDR" or length != 13:
                    raise AcceptanceError(f"PNG artifact does not start with IHDR: {path}")
                (
                    width,
                    height,
                    bit_depth,
                    color_type,
                    compression_method,
                    filter_method,
                    interlace_method,
                ) = struct.unpack(">IIBBBBB", payload[data_start:data_end])
                valid_depths = {
                    0: {1, 2, 4, 8, 16},
                    2: {8, 16},
                    3: {1, 2, 4, 8},
                    4: {8, 16},
                    6: {8, 16},
                }
                if (
                    bit_depth not in valid_depths.get(color_type, set())
                    or compression_method != 0
                    or filter_method != 0
                    or interlace_method != 0
                ):
                    raise AcceptanceError(
                        f"PNG IHDR uses unsupported or invalid screenshot encoding: {path}"
                    )
                _validated_image_dimensions(width, height, path)
            elif chunk_type == b"PLTE":
                if (
                    saw_plte
                    or saw_idat
                    or color_type in {0, 4}
                    or length < 3
                    or length > 768
                    or length % 3
                ):
                    raise AcceptanceError(f"PNG palette chunk is invalid: {path}")
                palette_entries = length // 3
                if color_type == 3 and palette_entries > 1 << bit_depth:
                    raise AcceptanceError(f"PNG indexed palette is oversized: {path}")
                saw_plte = True
            elif chunk_type == b"IDAT":
                if idat_closed:
                    raise AcceptanceError(f"PNG IDAT chunks are not consecutive: {path}")
                saw_idat = True
                idat_payloads.append(payload[data_start:data_end])
            elif chunk_type == b"IHDR":
                raise AcceptanceError(f"PNG contains a duplicate IHDR: {path}")
            elif chunk_type not in {b"IEND"} and 65 <= chunk_type[0] <= 90:
                raise AcceptanceError(f"PNG contains an unknown critical chunk: {path}")
            elif saw_idat and chunk_type != b"IEND":
                idat_closed = True
            offset = crc_end
            if chunk_type == b"IEND":
                if length != 0 or offset != len(payload):
                    raise AcceptanceError(f"PNG artifact has an invalid IEND/trailing data: {path}")
                break
        if not chunks or chunks[-1] != b"IEND" or b"IDAT" not in chunks:
            raise AcceptanceError(f"PNG artifact lacks IDAT or IEND: {path}")
        if not any(idat_payloads) or (color_type == 3 and not saw_plte):
            raise AcceptanceError(f"PNG image data/palette contract is incomplete: {path}")
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
        row_bytes = (width * channels * bit_depth + 7) // 8
        expected_decoded = (row_bytes + 1) * height
        if expected_decoded > MAX_DECODED_IMAGE_BYTES:
            raise AcceptanceError(f"PNG decoded payload is unreasonably large: {path}")
        inflater = zlib.decompressobj()
        try:
            decoded = inflater.decompress(
                b"".join(idat_payloads), expected_decoded + 1
            )
            if inflater.unconsumed_tail or len(decoded) > expected_decoded:
                raise AcceptanceError(f"PNG IDAT expands beyond IHDR dimensions: {path}")
            decoded += inflater.flush(expected_decoded + 1 - len(decoded))
        except zlib.error as exc:
            raise AcceptanceError(f"PNG IDAT stream cannot be decoded: {path}: {exc}") from exc
        if (
            not inflater.eof
            or inflater.unused_data
            or len(decoded) != expected_decoded
            or any(decoded[row * (row_bytes + 1)] > 4 for row in range(height))
        ):
            raise AcceptanceError(f"PNG decoded scanline structure is invalid: {path}")
        if color_type != 3:
            # Every filter byte and the exact decompressed raster size were
            # already checked.  PNG filters are total over byte rows, so an
            # additional Python byte-by-byte reconstruction would add no
            # validity signal for truecolour/grayscale screenshots.
            return {
                "format": "png",
                "width": width,
                "height": height,
                "decoded_sha256": sha256(decoded).hexdigest(),
            }
        bytes_per_pixel = max(1, (channels * bit_depth + 7) // 8)
        previous = bytearray(row_bytes)
        decoded_digest = sha256()
        for row_index in range(height):
            start = row_index * (row_bytes + 1)
            filter_type = decoded[start]
            raw_row = decoded[start + 1 : start + 1 + row_bytes]
            reconstructed = bytearray(row_bytes)
            for index, raw_value in enumerate(raw_row):
                left = reconstructed[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                above = previous[index]
                upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                if filter_type == 0:
                    predictor = 0
                elif filter_type == 1:
                    predictor = left
                elif filter_type == 2:
                    predictor = above
                elif filter_type == 3:
                    predictor = (left + above) // 2
                else:
                    estimate = left + above - upper_left
                    distances = (
                        abs(estimate - left),
                        abs(estimate - above),
                        abs(estimate - upper_left),
                    )
                    predictor = (left, above, upper_left)[distances.index(min(distances))]
                reconstructed[index] = (raw_value + predictor) & 0xFF
            if color_type == 3:
                indices: list[int] = []
                if bit_depth == 8:
                    indices = list(reconstructed[:width])
                else:
                    mask = (1 << bit_depth) - 1
                    for pixel in range(width):
                        bit_offset = pixel * bit_depth
                        byte_value = reconstructed[bit_offset // 8]
                        shift = 8 - bit_depth - (bit_offset % 8)
                        indices.append((byte_value >> shift) & mask)
                if any(index >= palette_entries for index in indices):
                    raise AcceptanceError(f"PNG pixel references an absent palette entry: {path}")
            decoded_digest.update(reconstructed)
            previous = reconstructed
        return {
            "format": "png",
            "width": width,
            "height": height,
            "decoded_sha256": decoded_digest.hexdigest(),
        }
    if suffix == ".bmp":
        payload = path.read_bytes()
        if len(payload) < 54 or payload[:2] != b"BM":
            raise AcceptanceError(f"BMP artifact has an invalid header: {path}")
        declared_size = struct.unpack("<I", payload[2:6])[0]
        pixel_offset = struct.unpack("<I", payload[10:14])[0]
        dib_size = struct.unpack("<I", payload[14:18])[0]
        if dib_size < 40 or 14 + dib_size > size:
            raise AcceptanceError(f"BMP DIB header is invalid: {path}")
        width, height = struct.unpack("<ii", payload[18:26])
        planes, bits_per_pixel = struct.unpack("<HH", payload[26:30])
        compression = struct.unpack("<I", payload[30:34])[0]
        declared_image_size = struct.unpack("<I", payload[34:38])[0]
        colors_used = struct.unpack("<I", payload[46:50])[0]
        absolute_height = abs(height)
        if (
            declared_size != size
            or pixel_offset < 14 + dib_size
            or pixel_offset >= size
            or width <= 0
            or height == 0
            or planes != 1
            or bits_per_pixel not in {1, 4, 8, 16, 24, 32}
            or compression not in {0, 3}
            or (compression == 3 and bits_per_pixel not in {16, 32})
            or (compression == 0 and bits_per_pixel not in {1, 4, 8, 16, 24, 32})
        ):
            raise AcceptanceError(f"BMP artifact metadata is invalid: {path}")
        _validated_image_dimensions(width, absolute_height, path)
        palette_entries = 0
        if bits_per_pixel <= 8:
            maximum_palette = 1 << bits_per_pixel
            palette_entries = colors_used or maximum_palette
            palette_end = 14 + dib_size + palette_entries * 4
            if (
                palette_entries < 1
                or palette_entries > maximum_palette
                or palette_end > pixel_offset
            ):
                raise AcceptanceError(f"BMP indexed palette is missing or invalid: {path}")
        elif colors_used and 14 + dib_size + colors_used * 4 > pixel_offset:
            raise AcceptanceError(f"BMP optional palette is truncated: {path}")
        if compression == 3 and dib_size == 40 and pixel_offset < 14 + dib_size + 12:
            raise AcceptanceError(f"BMP bitfield masks are missing: {path}")
        row_stride = ((width * bits_per_pixel + 31) // 32) * 4
        pixel_bytes = row_stride * absolute_height
        if (
            pixel_offset + pixel_bytes > size
            or (declared_image_size not in {0, pixel_bytes})
        ):
            raise AcceptanceError(f"BMP artifact pixel array is truncated: {path}")
        if bits_per_pixel <= 8:
            for row in range(absolute_height):
                row_data = payload[
                    pixel_offset + row * row_stride : pixel_offset + (row + 1) * row_stride
                ]
                if bits_per_pixel == 8:
                    indices = row_data[:width]
                else:
                    mask = (1 << bits_per_pixel) - 1
                    indices = bytes(
                        (row_data[(pixel * bits_per_pixel) // 8]
                         >> (8 - bits_per_pixel - ((pixel * bits_per_pixel) % 8)))
                        & mask
                        for pixel in range(width)
                    )
                if any(index >= palette_entries for index in indices):
                    raise AcceptanceError(
                        f"BMP pixel references an absent palette entry: {path}"
                    )
        decoded_sha256 = _force_decode_windows_raster(path, width, absolute_height)
        return {
            "format": "bmp",
            "width": width,
            "height": absolute_height,
            "decoded_sha256": decoded_sha256,
        }
    if suffix == ".tga":
        payload = path.read_bytes()
        if len(payload) < 18:
            raise AcceptanceError(f"TGA artifact is truncated: {path}")
        id_length = payload[0]
        color_map_type = payload[1]
        image_type = payload[2]
        width, height = struct.unpack("<HH", payload[12:16])
        bits_per_pixel = payload[16]
        descriptor = payload[17]
        grayscale = image_type in {3, 11}
        rle = image_type in {10, 11}
        if (
            color_map_type != 0
            or image_type not in {2, 3, 10, 11}
            or bits_per_pixel not in ({8, 16} if grayscale else {16, 24, 32})
            or descriptor & 0xC0
            or (bits_per_pixel == 16 and descriptor & 0x0F not in {0, 1, 8})
            or (bits_per_pixel in {24, 8} and descriptor & 0x0F)
            or (bits_per_pixel == 32 and descriptor & 0x0F not in {0, 8})
        ):
            raise AcceptanceError(f"TGA artifact metadata is invalid: {path}")
        _validated_image_dimensions(width, height, path)
        bytes_per_pixel = (bits_per_pixel + 7) // 8
        total_pixels = width * height
        cursor = 18 + id_length
        if cursor > len(payload):
            raise AcceptanceError(f"TGA image ID is truncated: {path}")
        decoded_pixels = 0
        decoded_digest = sha256()
        if rle:
            while decoded_pixels < total_pixels:
                if cursor >= len(payload):
                    raise AcceptanceError(f"TGA RLE packet stream is truncated: {path}")
                packet = payload[cursor]
                cursor += 1
                count = (packet & 0x7F) + 1
                if decoded_pixels + count > total_pixels:
                    raise AcceptanceError(f"TGA RLE packet exceeds pixel count: {path}")
                if packet & 0x80:
                    end = cursor + bytes_per_pixel
                    if end > len(payload):
                        raise AcceptanceError(f"TGA RLE pixel is truncated: {path}")
                    pixel = payload[cursor:end]
                    decoded_digest.update(pixel * count)
                    cursor = end
                else:
                    end = cursor + count * bytes_per_pixel
                    if end > len(payload):
                        raise AcceptanceError(f"TGA raw packet is truncated: {path}")
                    decoded_digest.update(payload[cursor:end])
                    cursor = end
                decoded_pixels += count
        else:
            end = cursor + total_pixels * bytes_per_pixel
            if end > len(payload):
                raise AcceptanceError(f"TGA artifact pixel array is truncated: {path}")
            decoded_digest.update(payload[cursor:end])
            decoded_pixels = total_pixels
            cursor = end
        if decoded_pixels != total_pixels:
            raise AcceptanceError(f"TGA decoded pixel count disagrees: {path}")
        trailing = len(payload) - cursor
        if trailing:
            if (
                trailing < 26
                or payload[-18:] != b"TRUEVISION-XFILE.\x00"
            ):
                raise AcceptanceError(f"TGA artifact has invalid trailing data: {path}")
            extension_offset, developer_offset = struct.unpack("<II", payload[-26:-18])
            for offset_value in (extension_offset, developer_offset):
                if offset_value and not (cursor <= offset_value < len(payload) - 26):
                    raise AcceptanceError(f"TGA footer offset is invalid: {path}")
        return {
            "format": "tga",
            "width": width,
            "height": height,
            "decoded_sha256": decoded_digest.hexdigest(),
        }
    raise AcceptanceError(f"unsupported screenshot format: {path}")


def _scan_clausewitz_stream(
    stream: object,
    expected_size: int,
    label: str,
) -> dict[str, object]:
    prefix = bytearray()
    observed = 0
    depth = 0
    maximum_depth = 0
    lines = 0
    quoted = False
    escaped = False
    comment = False
    negative_depth = False
    histogram = [0] * 256
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        if len(prefix) < MAX_EU4_STRUCTURE_PREFIX_BYTES:
            prefix.extend(
                chunk[: MAX_EU4_STRUCTURE_PREFIX_BYTES - len(prefix)]
            )
        observed += len(chunk)
        for value in chunk:
            histogram[value] += 1
            if comment:
                if value in {10, 13}:
                    comment = False
                    if value == 10:
                        lines += 1
                continue
            if quoted:
                if escaped:
                    escaped = False
                elif value == 92:
                    escaped = True
                elif value == 34:
                    quoted = False
                continue
            if value == 35:
                comment = True
            elif value == 34:
                quoted = True
            elif value == 123:
                depth += 1
                maximum_depth = max(maximum_depth, depth)
            elif value == 125:
                depth -= 1
                negative_depth = negative_depth or depth < 0
            elif value == 10:
                lines += 1
    if observed != expected_size:
        raise AcceptanceError(f"{label} size changed while being decoded")
    return {
        "prefix": bytes(prefix),
        "bytes": observed,
        "depth": depth,
        "maximum_depth": maximum_depth,
        "lines": lines,
        "quoted": quoted,
        "escaped": escaped,
        "negative_depth": negative_depth,
        "unique_bytes": sum(bool(count) for count in histogram),
        "largest_byte_count": max(histogram),
    }


def _validate_clausewitz_text_scan(
    scan: dict[str, object], kind: str, path: Path
) -> None:
    prefix = scan["prefix"]
    if (
        not isinstance(prefix, bytes)
        or not prefix.startswith(b"EU4txt\n")
        or scan["depth"] != 0
        or scan["quoted"] is True
        or scan["escaped"] is True
        or scan["negative_depth"] is True
        or int(scan["maximum_depth"]) < 1
        or int(scan["lines"]) < (100 if kind in {"full", "gamestate"} else 10)
    ):
        raise AcceptanceError(f"EU4 {kind} text structure is malformed: {path}")
    if kind in {"full", "meta"}:
        version_pattern = re.compile(
            rb"(?ms)^savegame_version=\{\s*"
            rb"first=\d+\s+second=\d+\s+third=\d+\s+forth=\d+\s+"
            rb'name="[^"\r\n]+"\s*\}'
        )
        if (
            not re.search(rb"(?m)^date=\d{1,4}\.\d{1,2}\.\d{1,2}\r?$", prefix)
            or not re.search(rb'(?m)^player="[A-Z0-9-]{3}"\r?$', prefix)
            or not version_pattern.search(prefix)
        ):
            raise AcceptanceError(
                f"EU4 {kind} text lacks canonical date/player/version fields: {path}"
            )
    elif kind == "gamestate":
        if (
            not re.search(
                rb'(?ms)^players_countries=\{.*?"Player".*?"[A-Z0-9-]{3}".*?\}',
                prefix,
            )
            or not re.search(rb"(?m)^gameplaysettings=\{", prefix)
            or not re.search(rb"(?m)^countries=\{", prefix)
        ):
            raise AcceptanceError(
                f"EU4 gamestate text lacks canonical campaign structures: {path}"
            )
    elif kind == "ai" and not re.search(rb"(?m)^ai=\{", prefix):
        raise AcceptanceError(f"EU4 AI text lacks its top-level object: {path}")


def _validate_clausewitz_binary_scan(
    scan: dict[str, object], kind: str, path: Path
) -> None:
    prefix = scan["prefix"]
    size = int(scan["bytes"])
    if (
        not isinstance(prefix, bytes)
        or not prefix.startswith(b"EU4bin")
        or int(scan["unique_bytes"]) < 16
        or int(scan["largest_byte_count"]) > size * 9 // 10
        or prefix.count(b"\x01\x00") < 2
        or prefix.count(b"\x0f\x00") < 2
    ):
        raise AcceptanceError(f"EU4 {kind} binary token stream is implausible: {path}")
    if kind == "gamestate" and not re.search(
        rb"\x01\x00\x03\x00\x0f\x00\x06\x00Player"
        rb"\x0f\x00\x03\x00[A-Z0-9-]{3}",
        prefix[:256],
    ):
        raise AcceptanceError(f"EU4 binary gamestate lacks player framing: {path}")
    if kind == "meta" and b".eu4" not in prefix:
        raise AcceptanceError(f"EU4 binary meta lacks a save filename: {path}")


def _validate_eu4_save(path: Path) -> dict[str, object]:
    if path.suffix.lower() != ".eu4":
        raise AcceptanceError(f"EU4 save artifact must use .eu4: {path}")
    file_size = path.stat().st_size
    if file_size < MIN_EU4_SAVE_BYTES or file_size > MAX_EU4_SAVE_BYTES:
        raise AcceptanceError(f"EU4 save size is implausible: {path}")
    stat_before = path.stat()
    with path.open("rb") as stream:
        prefix = stream.read(6)
    if prefix == b"EU4txt":
        with path.open("rb") as stream:
            scan = _scan_clausewitz_stream(stream, file_size, "EU4 text save")
        _validate_clausewitz_text_scan(scan, "full", path)
        stat_after = path.stat()
        if any(
            getattr(stat_before, key) != getattr(stat_after, key)
            for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        ):
            raise AcceptanceError(f"EU4 text save changed while reading: {path}")
        return {
            "format": "eu4text",
            "lines": scan["lines"],
            "maximum_depth": scan["maximum_depth"],
        }
    if not zipfile.is_zipfile(path):
        raise AcceptanceError(
            f"EU4 save must be EU4txt or a ZIP containing meta and gamestate: {path}"
        )
    try:
        archive_context = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise AcceptanceError(f"EU4 save ZIP cannot be opened: {path}: {exc}") from exc
    with archive_context as archive:
        members = archive.infolist()
        if not members or len(members) > MAX_EU4_ZIP_MEMBERS:
            raise AcceptanceError(f"EU4 save archive member count is unsafe: {path}")
        names: set[str] = set()
        total_uncompressed = 0
        for member in members:
            raw_name = member.filename
            relative = PurePosixPath(raw_name)
            mode = (member.external_attr >> 16) & 0xF000
            if (
                not raw_name
                or "\\" in raw_name
                or relative.is_absolute()
                or ".." in relative.parts
                or raw_name != relative.as_posix()
                or any(":" in part for part in relative.parts)
                or mode == stat.S_IFLNK
                or bool(member.flag_bits & 0x1)
                or raw_name in names
            ):
                raise AcceptanceError(f"unsafe EU4 save archive entry: {raw_name!r}")
            if member.is_dir():
                raise AcceptanceError(f"EU4 save archive contains a directory: {raw_name!r}")
            total_uncompressed += member.file_size
            if (
                member.file_size > MAX_EU4_SAVE_BYTES
                or total_uncompressed > MAX_EU4_ZIP_TOTAL_BYTES
                or (
                    member.file_size > 0
                    and (
                        member.compress_size == 0
                        or member.file_size
                        > member.compress_size * MAX_EU4_ZIP_RATIO
                    )
                )
            ):
                raise AcceptanceError(f"EU4 save archive expansion is unsafe: {raw_name!r}")
            names.add(raw_name)
        required = {"meta", "gamestate"}
        if not required.issubset(names):
            raise AcceptanceError(f"EU4 save lacks meta or gamestate: {path}")
        if not names.issubset({"meta", "gamestate", "ai"}):
            raise AcceptanceError(f"EU4 save contains unknown archive members: {path}")
        entry_headers: dict[str, str] = {}
        entry_structures: dict[str, dict[str, object]] = {}
        required_minimums = {
            "meta": MIN_EU4_META_BYTES,
            "gamestate": MIN_EU4_GAMESTATE_BYTES,
            "ai": 16 * 1024,
        }
        for member in members:
            if member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                raise AcceptanceError(
                    f"EU4 save archive compression is unsupported: {member.filename!r}"
                )
            if member.file_size < required_minimums.get(member.filename, 1):
                raise AcceptanceError(
                    f"EU4 save {member.filename} entry is implausibly small: {path}"
                )
            try:
                with archive.open(member) as stream:
                    scan = _scan_clausewitz_stream(
                        stream,
                        member.file_size,
                        f"EU4 save archive entry {member.filename}",
                    )
            except (OSError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
                raise AcceptanceError(
                    f"EU4 save archive member fails decompression/CRC: "
                    f"{member.filename!r}: {exc}"
                ) from exc
            entry_prefix = scan["prefix"][:6]
            if entry_prefix not in {b"EU4bin", b"EU4txt"}:
                raise AcceptanceError(
                    f"EU4 save {member.filename} entry has an invalid engine payload: {path}"
                )
            if entry_prefix == b"EU4txt":
                _validate_clausewitz_text_scan(scan, member.filename, path)
            else:
                _validate_clausewitz_binary_scan(scan, member.filename, path)
            entry_headers[member.filename] = entry_prefix.decode("ascii")
            entry_structures[member.filename] = {
                "bytes": member.file_size,
                "unique_bytes": scan["unique_bytes"],
            }
    stat_after = path.stat()
    if any(
        getattr(stat_before, key) != getattr(stat_after, key)
        for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    ):
        raise AcceptanceError(f"EU4 save ZIP changed while reading: {path}")
    return {
        "format": "eu4zip",
        "entry_headers": entry_headers,
        "entry_structures": entry_structures,
    }


def _validate_text_artifact(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    if not payload:
        raise AcceptanceError(f"text evidence artifact is empty: {path}")
    try:
        payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AcceptanceError(f"text evidence is not UTF-8: {path}: {exc}") from exc
    return {"format": "utf8-text"}


def _validate_artifact_format(path: Path, kind: str) -> dict[str, object]:
    normalized = kind.casefold()
    if normalized in {"screenshot", "screenshot_set", "image"}:
        return _validate_image_artifact(path)
    if normalized in {"save", "external_save", "eu4_save", "eu4-save"}:
        return _validate_eu4_save(path)
    if normalized in {
        "text",
        "notes",
        "note",
        "log_excerpt",
        "hash_manifest",
        "checklist",
        "observer_notes",
        "provenance",
    }:
        return _validate_text_artifact(path)
    raise AcceptanceError(f"unsupported evidence artifact kind: {kind!r}")


def _canonical_artifact_prefix(scenario_id: str, phase: str | None) -> str:
    scenario_token = re.sub(r"[^A-Z0-9]+", "_", scenario_id.upper()).strip("_")
    prefix = f"JXP_ACC_{scenario_token}_"
    if phase:
        phase_token = re.sub(r"[^A-Z0-9]+", "_", phase.upper()).strip("_")
        prefix += f"{phase_token}_"
    return prefix


def _resolve_evidence_source(
    raw: str,
    user_data: Path,
    prefix: str,
) -> Path:
    roots = _artifact_source_roots(user_data)
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = user_data / candidate
    source = candidate.resolve()
    allowed_parents = {root.resolve() for root in roots}
    if source.parent not in allowed_parents:
        raise AcceptanceError(
            "evidence artifacts must be direct files in the acceptance root, "
            f"Screenshots, or save games: {source}"
        )
    if not source.name.startswith(prefix):
        raise AcceptanceError(
            f"evidence artifact must use canonical prefix {prefix!r}: {source.name}"
        )
    if not source.is_file() or _is_link_or_junction(source):
        raise AcceptanceError(f"evidence artifact must be an ordinary file: {source}")
    return source


def _parse_role_paths(values: Sequence[str], option: str) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise AcceptanceError(f"{option} must use ROLE=PATH: {value!r}")
        role, raw_path = value.split("=", 1)
        role = role.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", role):
            raise AcceptanceError(f"invalid {option} role: {role!r}")
        if role in parsed or not raw_path.strip():
            raise AcceptanceError(f"duplicate or empty {option} role: {role!r}")
        parsed[role] = Path(raw_path.strip()).expanduser()
    return parsed


def _seal_input_saves(
    session: Path,
    values: Sequence[str],
) -> list[dict[str, object]]:
    parsed = _parse_role_paths(values, "--input-save")
    destination_root = session / "before" / "inputs"
    records: list[dict[str, object]] = []
    digests: set[str] = set()
    for role, raw_path in sorted(parsed.items()):
        source = raw_path.resolve()
        if not source.is_file() or _is_link_or_junction(source):
            raise AcceptanceError(f"input save must be an ordinary file: {source}")
        validation = _validate_eu4_save(source)
        digest = _sha256_file(source)
        if digest in digests:
            raise AcceptanceError("input save roles must reference distinct save bytes")
        digests.add(digest)
        destination_root.mkdir(parents=True, exist_ok=True)
        destination = destination_root / f"{role}.eu4"
        if os.path.lexists(destination):
            raise AcceptanceError(f"sealed input destination already exists: {destination}")
        shutil.copy2(source, destination)
        if _sha256_file(destination) != digest:
            raise AcceptanceError(f"sealed input copy verification failed: {role}")
        records.append(
            {
                "role": role,
                "source_path": str(source),
                "sealed_path": str(destination),
                "validation": validation,
                **_file_record(destination),
            }
        )
    return records


def _oracle_contract_summary(value: dict[str, object]) -> dict[str, object]:
    return {
        key: item
        for key, item in value.items()
        if key not in {"case_contracts", "source_pins", "sources_verified"}
    }


def _verify_oracle_snapshot_sources(
    oracle: dict[str, object],
    snapshots: Sequence[dict[str, object]],
) -> None:
    source_pins = oracle.get("source_pins")
    if not isinstance(source_pins, dict):
        raise AcceptanceError("R12 oracle has no source-pin map")
    snapshots_by_component = {
        str(item["component"]): item for item in snapshots
    }
    for component in ("main", "map"):
        snapshot = snapshots_by_component.get(component)
        if snapshot is None:
            raise AcceptanceError(
                f"R12 oracle cannot bind an absent {component} runtime snapshot"
            )
        committed = {
            path: digest
            for path, _size, digest in _git_snapshot_manifest_records(
                component, str(snapshot["source_revision"])
            )
        }
        for key, expected_digest in source_pins.items():
            prefix = f"{component}:"
            if not str(key).startswith(prefix):
                continue
            relative = str(key)[len(prefix) :]
            runtime_member = (
                relative in RUNTIME_ROOT_FILES
                or PurePosixPath(relative).parts[0]
                in RUNTIME_DIRECTORIES[component]
            )
            if runtime_member and relative not in committed:
                raise AcceptanceError(
                    f"R12 oracle runtime source is absent from the deployed "
                    f"Git snapshot: {key}"
                )
            if runtime_member and committed[relative] != expected_digest:
                raise AcceptanceError(
                    f"R12 oracle {key} disagrees with the deployed Git snapshot"
                )


def _seal_runtime_oracle(
    session: Path,
    scenario: dict[str, object],
    normalized: dict[str, object],
    repo: Path,
    game_root: Path,
    snapshots: Sequence[dict[str, object]],
) -> dict[str, object] | None:
    if normalized.get("runtime_oracle") is None:
        return None
    verified = _verified_runtime_oracle(
        scenario,
        normalized["artifact_specs"],
        [str(item["id"]) for item in normalized["assertions"]],
        repo=repo,
        game_root=game_root,
        verify_sources=True,
    )
    if _oracle_contract_summary(verified) != _oracle_contract_summary(
        normalized["runtime_oracle"]
    ):
        raise AcceptanceError("R12 oracle changed between normalization and source proof")
    _verify_oracle_snapshot_sources(verified, snapshots)
    source = Path(str(verified["path"]))
    copied = _copy_artifact(source, session / "before" / "oracle")
    if copied["sha256"] != verified["sha256"]:
        raise AcceptanceError("sealed R12 oracle copy SHA-256 disagrees")
    return {
        "contract": _oracle_contract_summary(verified),
        "source_path": str(source),
        "sealed_path": copied["path"],
        "bytes": copied["bytes"],
        "mtime_ns": copied["mtime_ns"],
        "sha256": copied["sha256"],
    }


def _verify_sealed_runtime_oracle(
    stored: object,
    session: Path,
    scenario: dict[str, object],
    normalized: dict[str, object],
    repo: Path,
    game_root: Path,
    snapshots: Sequence[dict[str, object]],
) -> dict[str, object] | None:
    if normalized.get("runtime_oracle") is None:
        if stored is not None:
            raise AcceptanceError("non-R12 session unexpectedly seals an oracle")
        return None
    required = {
        "contract",
        "source_path",
        "sealed_path",
        "bytes",
        "mtime_ns",
        "sha256",
    }
    if not isinstance(stored, dict) or set(stored) != required:
        raise AcceptanceError("sealed R12 oracle record schema disagrees")
    verified = _verified_runtime_oracle(
        scenario,
        normalized["artifact_specs"],
        [str(item["id"]) for item in normalized["assertions"]],
        repo=repo,
        game_root=game_root,
        verify_sources=True,
    )
    _verify_oracle_snapshot_sources(verified, snapshots)
    sealed = Path(str(stored["sealed_path"]))
    expected_root = session / "before" / "oracle"
    if (
        sealed.parent != expected_root
        or sealed.name != Path(str(verified["path"])).name
        or not sealed.is_file()
        or _is_link_or_junction(sealed)
        or str(stored["source_path"]) != str(verified["path"])
        or stored["contract"] != _oracle_contract_summary(verified)
    ):
        raise AcceptanceError("sealed R12 oracle path/contract identity disagrees")
    actual = _file_record(sealed)
    if (
        any(actual[key] != stored[key] for key in ("bytes", "mtime_ns", "sha256"))
        or stored["sha256"] != verified["sha256"]
    ):
        raise AcceptanceError("sealed R12 oracle bytes changed or disagree")
    return dict(stored)


_COLLECTION_SCHEMA4_KEYS = frozenset(
    {
        "schema",
        "status",
        "collected_at",
        "scenario_id",
        "phase",
        "candidate_revision",
        "session_id",
        "session_path",
        "session_sha256",
        "contract_sha256",
        "matrix_sha256",
        "permission_reference",
        "repo",
        "game_root",
        "user_data",
        "daily_user_data",
        "expected_argv",
        "process_observation",
        "game_pins_before",
        "game_pins_after",
        "pins_stable",
        "launcher_daily_root_matched",
        "snapshots",
        "snapshot_checks",
        "snapshot_contract_stable",
        "dlc_load_before",
        "dlc_load_after",
        "configure_receipt",
        "configure_receipt_stable",
        "isolated_configuration_before",
        "isolated_configuration_after",
        "isolated_configuration_stable",
        "daily_vfs_coverage",
        "daily_vfs_hash_policy",
        "daily_vfs_before",
        "daily_vfs_after",
        "daily_vfs_stable",
        "daily_vfs_guard_artifact",
        "isolated_vfs_inventory_artifact",
        "runtime_output_before",
        "runtime_output_after",
        "fresh_settings_outputs",
        "logs",
        "fresh_log_paths",
        "missing_required_logs",
        "game_version_log_matched",
        "log_blockers",
        "passed_log_scan",
        "required_fixture_records",
        "fixtures_stable",
        "fixture_uses",
        "runtime_oracle",
        "runtime_oracle_evidence",
        "runtime_oracle_evidence_sha256",
        "sealed_inputs",
        "external_input_evidence_checks",
        "parents",
        "artifact_roles",
        "appendix_artifacts",
        "artifact_requirement_checks",
        "runtime_dlc_checks",
        "assertions",
        "matrix_blockers",
        "automated_check_results",
        "automated_checks_passed",
        "manual_assertions_complete",
        "manual_assertions_passed",
        "ready_for_lead_review",
        "scenario_pass_claimed",
        "claim_limit",
    }
)

_PARENT_AUTOMATED_CHECK_IDS = frozenset(
    {
        "twelve_pins_stable",
        "launcher_daily_root_canonical",
        "fresh_logs_clean",
        "snapshot_contract_stable",
        "isolated_configuration_stable",
        "daily_vfs_stable",
        "required_fixtures_stable",
        "artifact_minimums_met",
        "runtime_dlc_contract_met",
        "external_input_provenance_bound",
        "runtime_oracle_stable",
        "runtime_oracle_evidence_bound",
    }
)

_PARENT_DEPENDENCY_RECORD_KEYS = frozenset(
    {
        "role",
        "collection_path",
        "collection_sha256",
        "collection_seal_path",
        "collection_seal_sha256",
        "collection_status",
        "ready_for_lead_review",
        "automated_checks_passed",
        "manual_assertions_complete",
        "manual_assertions_passed",
        "scenario_id",
        "phase",
        "candidate_revision",
        "session_id",
        "session_path",
        "session_sha256",
        "session_seal_path",
        "session_seal_sha256",
        "contract_sha256",
        "artifact_roles",
        "artifact_roles_sha256",
        "assertions",
        "assertions_sha256",
        "snapshots",
        "snapshots_sha256",
        "sealed_inputs",
        "sealed_inputs_sha256",
        "parent_dependencies",
        "parent_dependencies_sha256",
        "fixture_uses",
        "fixture_uses_sha256",
        "required_fixture_records",
        "required_fixture_records_sha256",
        "runtime_oracle_evidence_sha256",
        "compatibility",
    }
)


def _all_parent_checks_matched(value: object, *, allow_empty: bool) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(item, dict) and item.get("matched") is True for item in value)
    )


def _verify_parent_collection_artifact_roles(
    collection: dict[str, object],
    session: Path,
    session_record: dict[str, object],
    session_sha256: str,
) -> None:
    artifact_roles = collection.get("artifact_roles")
    if not isinstance(artifact_roles, dict) or not artifact_roles:
        raise AcceptanceError("parent collection artifact_roles are missing or malformed")
    normalized = _normalized_evidence_contract(
        session_record["scenario"], session_record["phase"]
    )
    if set(artifact_roles) != set(normalized["artifact_roles"]):
        raise AcceptanceError("parent collection artifact role set disagrees with its contract")

    after_root = _require_ordinary_directory(
        session / "after", "parent collection after directory"
    )
    used_paths: set[str] = set()
    used_hashes: set[str] = set()
    verified_observation: dict[str, object] | None = None
    base_record_keys = {
        "role",
        "kind",
        "source_path",
        "validation",
        "path",
        "bytes",
        "mtime_ns",
        "sha256",
        "supports_assertion_ids",
        "distinct",
    }
    for role, raw_records in artifact_roles.items():
        if not isinstance(role, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9_]{1,95}", role
        ):
            raise AcceptanceError(f"parent collection artifact role is invalid: {role!r}")
        records = _dependency_artifact_records(raw_records)
        spec = normalized["artifact_specs"][role]
        expected_kind = normalized["artifact_roles"][role]
        minimum = int(spec.get("min_items", 1))
        if len(records) < minimum or (expected_kind != "screenshot_set" and len(records) != 1):
            raise AcceptanceError(f"parent collection artifact role count disagrees: {role}")
        expected_cases = set(str(item) for item in spec.get("case_ids", []))
        actual_cases: set[str] = set()
        for item in records:
            allowed_keys = base_record_keys | ({"case_id"} if "case_id" in item else set())
            if set(item) != allowed_keys:
                raise AcceptanceError(
                    f"parent collection artifact record schema disagrees: {role}"
                )
            kind = item.get("kind")
            path_value = item.get("path")
            if (
                item.get("role") != role
                or kind != expected_kind
                or item.get("distinct") is not True
                or item.get("supports_assertion_ids")
                != spec["supports_assertion_ids"]
                or not isinstance(path_value, str)
                or not path_value
                or isinstance(item.get("bytes"), bool)
                or not isinstance(item.get("bytes"), int)
                or int(item["bytes"]) <= 0
                or isinstance(item.get("mtime_ns"), bool)
                or not isinstance(item.get("mtime_ns"), int)
                or not isinstance(item.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", str(item["sha256"]))
                or not isinstance(item.get("source_path"), str)
                or not isinstance(item.get("validation"), dict)
            ):
                raise AcceptanceError(
                    f"parent collection artifact record fields disagree: {role}"
                )
            raw_path = Path(path_value).expanduser()
            artifact_path = raw_path.resolve()
            if (
                not raw_path.is_absolute()
                or str(artifact_path) != path_value
                or artifact_path == after_root
                or not _is_relative_to(artifact_path, after_root)
                or not artifact_path.is_file()
            ):
                raise AcceptanceError(
                    f"parent artifact must be a canonical file inside session after: {role}"
                )
            cursor = artifact_path
            while True:
                if _is_link_or_junction(cursor):
                    raise AcceptanceError(
                        f"parent artifact path traverses a link or junction: {artifact_path}"
                    )
                if cursor == after_root:
                    break
                cursor = cursor.parent
                if cursor == cursor.parent and cursor != after_root:
                    raise AcceptanceError(
                        f"parent artifact path escapes session after: {artifact_path}"
                    )
            if artifact_path.stat().st_nlink != 1:
                raise AcceptanceError(
                    f"parent artifact must not be a hard-linked replay: {artifact_path}"
                )
            actual = _file_record(artifact_path)
            if any(
                actual[key] != item.get(key) for key in ("bytes", "sha256")
            ):
                raise AcceptanceError(f"parent artifact bytes/hash changed: {artifact_path}")
            canonical_path = str(artifact_path)
            digest = str(item["sha256"])
            if canonical_path in used_paths or digest in used_hashes:
                raise AcceptanceError(
                    f"parent artifact path or bytes are replayed across roles: {role}"
                )
            used_paths.add(canonical_path)
            used_hashes.add(digest)

            validation = item["validation"]
            if kind in {"screenshot", "screenshot_set", "save", "external_save"}:
                if validation != _validate_artifact_format(artifact_path, str(kind)):
                    raise AcceptanceError(
                        f"parent artifact format attestation disagrees: {artifact_path}"
                    )
            elif kind == "log":
                _validate_text_artifact(artifact_path)
                if validation != {
                    "format": "fresh-engine-log",
                    "name": Path(str(item["source_path"])).name.lower(),
                }:
                    raise AcceptanceError(
                        f"parent log format attestation disagrees: {artifact_path}"
                    )
            elif kind == "settings":
                _validate_text_artifact(artifact_path)
                if validation != {"format": "engine-settings-output"}:
                    raise AcceptanceError(
                        f"parent settings format attestation disagrees: {artifact_path}"
                    )
            elif kind == "process_observation":
                if verified_observation is None:
                    verified_observation = _verified_process_observation(
                        session, session_record, session_sha256
                    )
                copied_observation = _verify_self_seal(
                    _read_json_object(artifact_path, "parent process observation artifact"),
                    "observation_sha256",
                    "parent process observation artifact",
                )
                if copied_observation != verified_observation or validation != {
                    "format": "sealed-process-observation",
                    "observation_sha256": verified_observation["observation_sha256"],
                    "matched": True,
                }:
                    raise AcceptanceError(
                        "parent process-observation artifact identity disagrees"
                    )
            elif kind == "vfs_inventory":
                inventory = _read_json_object(
                    artifact_path, "parent VFS inventory artifact"
                )
                if (
                    inventory.get("schema") != COLLECTION_SCHEMA
                    or inventory.get("session_id") != session_record["session_id"]
                    or inventory.get("session_sha256") != session_sha256
                    or validation != {"format": "generated-json"}
                ):
                    raise AcceptanceError(
                        f"parent VFS inventory identity disagrees: {artifact_path}"
                    )
            elif (
                kind == "checklist"
                and session_record["scenario"]["id"] == "R12"
            ):
                if validation != _validate_r12_typed_checklist(
                    artifact_path, role, normalized
                ):
                    raise AcceptanceError(
                        f"parent R12 typed checklist attestation disagrees: {role}"
                    )
            else:
                if validation != _validate_text_artifact(artifact_path):
                    raise AcceptanceError(
                        f"parent text artifact format attestation disagrees: {artifact_path}"
                    )
            case_id = item.get("case_id")
            if case_id is not None:
                if not isinstance(case_id, str) or not case_id or case_id in actual_cases:
                    raise AcceptanceError(f"parent screenshot case id is invalid: {role}")
                actual_cases.add(case_id)
        if actual_cases != expected_cases:
            raise AcceptanceError(f"parent screenshot case coverage disagrees: {role}")


def _verify_ready_parent_collection_invariants(
    collection: dict[str, object],
    session: Path,
    session_record: dict[str, object],
    session_sha256: str,
) -> None:
    if set(collection) != _COLLECTION_SCHEMA4_KEYS:
        raise AcceptanceError("parent collection schema-4 key set disagrees")
    if (
        collection.get("schema") != COLLECTION_SCHEMA
        or collection.get("status") != "READY_FOR_LEAD_REVIEW"
        or collection.get("ready_for_lead_review") is not True
        or collection.get("automated_checks_passed") is not True
        or collection.get("manual_assertions_complete") is not True
        or collection.get("manual_assertions_passed") is not True
        or collection.get("scenario_pass_claimed") is not False
        or collection.get("matrix_blockers") != []
    ):
        raise AcceptanceError("parent collection review-ready invariants disagree")
    _aware_datetime(collection.get("collected_at"), "parent collected_at")
    if (
        not isinstance(collection.get("scenario_id"), str)
        or not isinstance(collection.get("session_id"), str)
        or not re.fullmatch(r"[0-9a-f]{32}", str(collection["session_id"]))
        or not isinstance(collection.get("candidate_revision"), str)
        or not re.fullmatch(r"[0-9a-f]{40}", str(collection["candidate_revision"]))
        or not isinstance(collection.get("contract_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(collection["contract_sha256"]))
        or not isinstance(collection.get("matrix_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(collection["matrix_sha256"]))
        or not isinstance(collection.get("claim_limit"), str)
        or not str(collection["claim_limit"]).strip()
    ):
        raise AcceptanceError("parent collection identity fields are invalid")

    cross_identity = {
        "scenario_id": session_record["scenario"]["id"],
        "phase": session_record["phase"],
        "candidate_revision": session_record["candidate_revision"],
        "session_id": session_record["session_id"],
        "session_path": str(session),
        "session_sha256": session_sha256,
        "contract_sha256": session_record["contract_sha256"],
        "matrix_sha256": session_record["matrix_sha256"],
        "permission_reference": session_record["permission_reference"],
        "repo": session_record["repo"],
        "game_root": session_record["game_root"],
        "user_data": session_record["user_data"],
        "daily_user_data": session_record["daily_user_data"],
        "expected_argv": session_record["expected_argv"],
        "game_pins_before": session_record["game_pins"],
        "snapshots": session_record["snapshots"],
        "dlc_load_before": session_record["dlc_load"],
        "configure_receipt": session_record["configure_receipt"],
        "isolated_configuration_before": session_record[
            "isolated_configuration_baseline"
        ],
        "daily_vfs_coverage": session_record["daily_vfs_coverage"],
        "daily_vfs_hash_policy": session_record["daily_vfs_hash_policy"],
        "daily_vfs_before": session_record["daily_vfs_baseline"],
        "runtime_output_before": session_record["runtime_output_baseline"],
        "required_fixture_records": session_record["required_fixture_records"],
        "runtime_oracle": session_record["runtime_oracle"],
        "sealed_inputs": session_record["sealed_inputs"],
        "parents": session_record["parents"],
    }
    if any(collection.get(key) != value for key, value in cross_identity.items()):
        raise AcceptanceError("parent collection and immutable session identity disagree")
    observation = _verified_process_observation(
        session, session_record, session_sha256
    )
    if collection.get("process_observation") != observation:
        raise AcceptanceError("parent collection process observation disagrees")

    automated_expectations = {
        "twelve_pins_stable": (
            collection.get("pins_stable") is True
            and collection.get("game_pins_before") == collection.get("game_pins_after")
            and isinstance(collection.get("game_pins_after"), list)
            and len(collection["game_pins_after"]) == 12
            and all(
                isinstance(item, dict) and item.get("matched") is True
                for item in collection["game_pins_after"]
            )
        ),
        "launcher_daily_root_canonical": collection.get(
            "launcher_daily_root_matched"
        )
        is True,
        "fresh_logs_clean": (
            collection.get("passed_log_scan") is True
            and collection.get("missing_required_logs") == []
            and collection.get("log_blockers") == []
            and collection.get("game_version_log_matched") is True
        ),
        "snapshot_contract_stable": (
            collection.get("snapshot_contract_stable") is True
            and _all_parent_checks_matched(
                collection.get("snapshot_checks"), allow_empty=False
            )
        ),
        "isolated_configuration_stable": (
            collection.get("isolated_configuration_stable") is True
            and collection.get("configure_receipt_stable") is True
            and collection.get("dlc_load_before") == collection.get("dlc_load_after")
        ),
        "daily_vfs_stable": (
            collection.get("daily_vfs_stable") is True
            and collection.get("daily_vfs_before") == collection.get("daily_vfs_after")
        ),
        "required_fixtures_stable": (
            collection.get("fixtures_stable") is True
            and _all_parent_checks_matched(
                collection.get("fixture_uses"), allow_empty=True
            )
        ),
        "artifact_minimums_met": _all_parent_checks_matched(
            collection.get("artifact_requirement_checks"), allow_empty=False
        ),
        "runtime_dlc_contract_met": _all_parent_checks_matched(
            collection.get("runtime_dlc_checks"), allow_empty=True
        ),
        "external_input_provenance_bound": _all_parent_checks_matched(
            collection.get("external_input_evidence_checks"), allow_empty=True
        ),
        "runtime_oracle_stable": collection.get("runtime_oracle")
        == session_record["runtime_oracle"],
        "runtime_oracle_evidence_bound": (
            isinstance(collection.get("runtime_oracle_evidence"), list)
            and collection.get("runtime_oracle_evidence_sha256")
            == _object_sha256(collection["runtime_oracle_evidence"])
            and (
                (
                    session_record["runtime_oracle"] is None
                    and collection["runtime_oracle_evidence"] == []
                )
                or (
                    session_record["runtime_oracle"] is not None
                    and len(collection["runtime_oracle_evidence"]) == 282
                )
            )
        ),
    }
    raw_automated = collection.get("automated_check_results")
    if not isinstance(raw_automated, list) or len(raw_automated) != len(
        _PARENT_AUTOMATED_CHECK_IDS
    ):
        raise AcceptanceError("parent collection automated check list is malformed")
    automated_by_id: dict[str, object] = {}
    for item in raw_automated:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "matched"}
            or not isinstance(item.get("id"), str)
            or item["id"] in automated_by_id
        ):
            raise AcceptanceError("parent collection automated check entry is malformed")
        automated_by_id[str(item["id"])] = item.get("matched")
    if set(automated_by_id) != _PARENT_AUTOMATED_CHECK_IDS or any(
        automated_by_id[check_id] is not True or not automated_expectations[check_id]
        for check_id in _PARENT_AUTOMATED_CHECK_IDS
    ):
        raise AcceptanceError("parent collection automated check invariants disagree")

    normalized = _normalized_evidence_contract(
        session_record["scenario"], session_record["phase"]
    )
    verified_oracle = _verify_sealed_runtime_oracle(
        session_record["runtime_oracle"],
        session,
        session_record["scenario"],
        normalized,
        Path(str(session_record["repo"])),
        Path(str(session_record["game_root"])),
        session_record["snapshots"],
    )
    if collection.get("runtime_oracle") != verified_oracle:
        raise AcceptanceError("parent R12 runtime oracle seal disagrees")
    assertions = collection.get("assertions")
    if not isinstance(assertions, list) or len(assertions) != len(
        normalized["assertions"]
    ):
        raise AcceptanceError("parent collection assertion list is malformed")
    assertions_by_id: dict[str, dict[str, object]] = {}
    for item in assertions:
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "id",
                "text",
                "status",
                "note",
                "attestor",
                "attested_at",
                "artifact_roles",
                "matrix_blocker_ids",
            }
            or not isinstance(item.get("id"), str)
            or item["id"] in assertions_by_id
            or item.get("status") != "PASS"
            or not isinstance(item.get("note"), str)
            or not str(item["note"]).strip()
            or not isinstance(item.get("attestor"), str)
            or not str(item["attestor"]).strip()
            or item.get("matrix_blocker_ids") != []
            or not isinstance(item.get("artifact_roles"), list)
            or not item["artifact_roles"]
            or len(item["artifact_roles"]) != len(set(item["artifact_roles"]))
        ):
            raise AcceptanceError("parent collection assertion invariant disagrees")
        _aware_datetime(item.get("attested_at"), "parent assertion attested_at")
        assertions_by_id[str(item["id"])] = item
    expected_assertions = {str(item["id"]): item for item in normalized["assertions"]}
    if set(assertions_by_id) != set(expected_assertions):
        raise AcceptanceError("parent collection assertion ids disagree with its contract")
    for assertion_id, item in assertions_by_id.items():
        expected_roles = [
            role
            for role, spec in normalized["artifact_specs"].items()
            if assertion_id in spec["supports_assertion_ids"]
        ]
        if (
            item.get("text") != expected_assertions[assertion_id]["text"]
            or item["artifact_roles"] != expected_roles
        ):
            raise AcceptanceError(
                f"parent collection assertion evidence mapping disagrees: {assertion_id}"
            )
    _verify_parent_collection_artifact_roles(
        collection, session, session_record, session_sha256
    )
    parent_role_records = {
        str(role): value if isinstance(value, list) else [value]
        for role, value in collection["artifact_roles"].items()
    }
    expected_oracle_evidence = _runtime_oracle_evidence_index(
        normalized, parent_role_records
    )
    if (
        collection.get("runtime_oracle_evidence") != expected_oracle_evidence
        or collection.get("runtime_oracle_evidence_sha256")
        != _object_sha256(expected_oracle_evidence)
    ):
        raise AcceptanceError("parent R12 oracle-to-artifact evidence index disagrees")


def _verified_collection_file(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    raw_path = path.expanduser()
    if raw_path.is_dir():
        session = _require_ordinary_directory(raw_path, "parent collection session")
        collection_path = session / COLLECTION_NAME
    else:
        if _is_link_or_junction(raw_path):
            raise AcceptanceError(f"parent collection path must be ordinary: {raw_path}")
        collection_path = raw_path.resolve()
        if collection_path.name != COLLECTION_NAME:
            raise AcceptanceError(
                f"parent collection must be named {COLLECTION_NAME}: {collection_path}"
            )
        session = _require_ordinary_directory(
            collection_path.parent, "parent collection session"
        )
    if collection_path.parent != session or collection_path.name != COLLECTION_NAME:
        raise AcceptanceError("parent collection path is outside its session directory")
    collection = _read_json_object(collection_path, "parent collection")
    if set(collection) != _COLLECTION_SCHEMA4_KEYS:
        raise AcceptanceError("parent collection schema-4 key set disagrees")
    seal_path = collection_path.with_name(COLLECTION_SEAL_NAME)
    seal = _read_json_object(seal_path, "parent collection seal")
    required = {
        "schema",
        "collection_path",
        "collection_sha256",
        "session_sha256",
        "sealed_at",
    }
    if set(seal) != required or seal.get("schema") != COLLECTION_SCHEMA:
        raise AcceptanceError("parent collection seal schema disagrees")
    _aware_datetime(seal.get("sealed_at"), "parent collection sealed_at")
    actual_digest = _sha256_file(collection_path)
    session_seal, session_sha256 = _verified_session_seal(session)
    session_record = _validate_session_record(
        _read_json_object(_session_file(session), "parent session record")
    )
    if (
        seal.get("collection_path") != str(collection_path)
        or seal.get("collection_sha256") != actual_digest
        or seal.get("session_sha256") != session_sha256
        or collection.get("session_path") != str(session)
        or collection.get("session_sha256") != session_sha256
        or collection.get("session_id") != session_seal.get("session_id")
        or collection.get("session_id") != session_record.get("session_id")
    ):
        raise AcceptanceError("parent collection/session seal identity or hash disagrees")
    _verify_ready_parent_collection_invariants(
        collection, session, session_record, session_sha256
    )
    return collection, seal


def _parent_dependency_record(role: str, path: Path) -> dict[str, object]:
    collection, seal = _verified_collection_file(path)
    collection_path = Path(str(seal["collection_path"]))
    session = Path(str(collection["session_path"]))
    collection_seal_path = collection_path.with_name(COLLECTION_SEAL_NAME)
    session_seal_path = _session_seal_file(session)
    artifact_roles = collection["artifact_roles"]
    assertions = collection["assertions"]
    snapshots = collection["snapshots"]
    sealed_inputs = collection["sealed_inputs"]
    parent_dependencies = collection["parents"]
    fixture_uses = collection["fixture_uses"]
    required_fixture_records = collection["required_fixture_records"]
    return {
        "role": role,
        "collection_path": str(collection_path),
        "collection_sha256": seal["collection_sha256"],
        "collection_seal_path": str(collection_seal_path),
        "collection_seal_sha256": _sha256_file(collection_seal_path),
        "collection_status": collection["status"],
        "ready_for_lead_review": collection["ready_for_lead_review"],
        "automated_checks_passed": collection["automated_checks_passed"],
        "manual_assertions_complete": collection["manual_assertions_complete"],
        "manual_assertions_passed": collection["manual_assertions_passed"],
        "scenario_id": collection["scenario_id"],
        "phase": collection["phase"],
        "candidate_revision": collection["candidate_revision"],
        "session_id": collection["session_id"],
        "session_path": str(session),
        "session_sha256": collection["session_sha256"],
        "session_seal_path": str(session_seal_path),
        "session_seal_sha256": _sha256_file(session_seal_path),
        "contract_sha256": collection["contract_sha256"],
        "artifact_roles": artifact_roles,
        "artifact_roles_sha256": _object_sha256(artifact_roles),
        "assertions": assertions,
        "assertions_sha256": _object_sha256(assertions),
        "snapshots": snapshots,
        "snapshots_sha256": _object_sha256(snapshots),
        "sealed_inputs": sealed_inputs,
        "sealed_inputs_sha256": _object_sha256(sealed_inputs),
        "parent_dependencies": parent_dependencies,
        "parent_dependencies_sha256": _object_sha256(parent_dependencies),
        "fixture_uses": fixture_uses,
        "fixture_uses_sha256": _object_sha256(fixture_uses),
        "required_fixture_records": required_fixture_records,
        "required_fixture_records_sha256": _object_sha256(required_fixture_records),
        "runtime_oracle_evidence_sha256": collection[
            "runtime_oracle_evidence_sha256"
        ],
        "compatibility": {
            "matrix_sha256": collection["matrix_sha256"],
            "candidate_revision": collection["candidate_revision"],
            "game_pins": collection["game_pins_after"],
            "repo": collection["repo"],
            "game_root": collection["game_root"],
            "user_data": collection["user_data"],
            "daily_user_data": collection["daily_user_data"],
        },
    }


def _seal_parent_collections(values: Sequence[str]) -> list[dict[str, object]]:
    parsed = _parse_role_paths(values, "--parent-collection")
    records: list[dict[str, object]] = []
    digests: set[str] = set()
    session_digests: set[str] = set()
    for role, raw_path in sorted(parsed.items()):
        record = _parent_dependency_record(role, raw_path)
        digest = str(record["collection_sha256"])
        session_digest = str(record["session_sha256"])
        if digest in digests or session_digest in session_digests:
            raise AcceptanceError(
                "parent roles must reference distinct collections and sessions"
            )
        digests.add(digest)
        session_digests.add(session_digest)
        records.append(record)
    return records


def install_run_fixtures(user_data: Path) -> dict[str, object]:
    """Install immutable non-release console setup effects into safe userdir."""
    _assert_processes_stopped()
    user_data = _require_canonical_fixture_user_data(user_data)
    _assert_no_active_session(user_data, "install run fixtures")
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


def _session_file(session: Path) -> Path:
    return session / "session.json"


def _session_seal_file(session: Path) -> Path:
    return session / SESSION_SEAL_NAME


def _write_session_and_seal(
    session: Path,
    record: dict[str, object],
) -> tuple[str, dict[str, object]]:
    session_path = _session_file(session)
    _exclusive_write_json(session_path, record)
    session_sha256 = _sha256_file(session_path)
    seal = {
        "schema": SESSION_SCHEMA,
        "session_path": str(session_path),
        "session_sha256": session_sha256,
        "session_id": record["session_id"],
        "active_nonce": record["active_nonce"],
        "sealed_at": _utc_now().isoformat(),
    }
    _exclusive_write_json(_session_seal_file(session), seal)
    return session_sha256, seal


def _verified_session_seal(session: Path) -> tuple[dict[str, object], str]:
    session_path = _session_file(session)
    seal = _read_json_object(_session_seal_file(session), "session seal")
    required = {
        "schema",
        "session_path",
        "session_sha256",
        "session_id",
        "active_nonce",
        "sealed_at",
    }
    if set(seal) != required or seal.get("schema") != SESSION_SCHEMA:
        raise AcceptanceError("session seal schema disagrees")
    digest = _sha256_file(session_path)
    record = _read_json_object(session_path, "sealed session record")
    if (
        seal.get("session_path") != str(session_path)
        or seal.get("session_sha256") != digest
        or seal.get("session_id") != record.get("session_id")
        or seal.get("active_nonce") != record.get("active_nonce")
    ):
        raise AcceptanceError("session.json disagrees with its immutable session seal")
    _aware_datetime(seal.get("sealed_at"), "session seal sealed_at")
    return seal, digest


def _create_active_placeholder(user_data: Path, nonce: str) -> None:
    active = _active_session_path(user_data)
    placeholder = {
        "schema": SESSION_SCHEMA,
        "state": "creating",
        "nonce": nonce,
        "session": None,
        "session_sha256": None,
        "created_at": _utc_now().isoformat(),
    }
    try:
        _exclusive_write_json(active, placeholder)
    except FileExistsError as exc:
        raise AcceptanceError(
            f"another acceptance session is already active: {active}"
        ) from exc


def _activate_session(
    user_data: Path,
    nonce: str,
    session: Path,
    session_sha256: str,
) -> None:
    active = _active_session_path(user_data)
    current = _read_json_object(active, "active-session placeholder")
    if current.get("state") != "creating" or current.get("nonce") != nonce:
        raise AcceptanceError("active-session placeholder identity changed")
    value = {
        "schema": SESSION_SCHEMA,
        "state": "active",
        "nonce": nonce,
        "session": str(session),
        "session_sha256": session_sha256,
        "created_at": current.get("created_at"),
    }
    _atomic_write_json(active, value)


def _remove_active_if_nonce(user_data: Path, nonce: str) -> None:
    active = _active_session_path(user_data)
    if not os.path.lexists(active):
        return
    try:
        value = _read_json_object(active, "active-session lock")
    except AcceptanceError:
        return
    if value.get("nonce") == nonce:
        _retire_active_lock_value(user_data, value, "failed session creation")


def _retire_active_lock_value(
    user_data: Path,
    expected: dict[str, object],
    label: str,
) -> None:
    """Move an exact nonce-bound lock aside before deleting it.

    A raw check-then-unlink can delete a replacement lock.  Renaming first and
    validating the moved inode/value makes replacement races fail closed and
    recoverable.
    """
    active = _active_session_path(user_data)
    if not active.is_file() or _is_link_or_junction(active):
        raise AcceptanceError(f"{label} active-session lock is not ordinary")
    stat_before = active.stat()
    observed = _read_json_object(active, f"{label} active-session lock")
    stat_after_read = active.stat()
    identity_keys = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if observed != expected or any(
        getattr(stat_before, key) != getattr(stat_after_read, key)
        for key in identity_keys
    ):
        raise AcceptanceError(f"{label} active-session lock changed before retirement")
    tombstone = user_data / (
        f".active-session-retired-{expected.get('nonce', 'unknown')}-"
        f"{uuid.uuid4().hex}.json"
    )
    if os.path.lexists(tombstone):
        raise AcceptanceError(f"active-session tombstone unexpectedly exists: {tombstone}")
    os.rename(active, tombstone)
    try:
        moved = _read_json_object(tombstone, f"{label} retired active-session lock")
        moved_stat = tombstone.stat()
        if moved != expected or any(
            getattr(stat_before, key) != getattr(moved_stat, key)
            for key in ("st_dev", "st_ino", "st_size")
        ):
            if not os.path.lexists(active):
                os.rename(tombstone, active)
            raise AcceptanceError(
                f"{label} active-session lock was replaced during retirement"
            )
        tombstone.unlink()
    except Exception:
        if os.path.lexists(tombstone) and not os.path.lexists(active):
            os.rename(tombstone, active)
        raise


def _required_fixture_records_for_contract(
    scenario: dict[str, object],
    phase: str | None,
    user_data: Path,
) -> list[dict[str, object]]:
    normalized = _normalized_evidence_contract(scenario, phase)
    records: list[dict[str, object]] = []
    for requirement in normalized["fixtures"]:
        name = str(requirement["name"])
        source_record = _run_fixture_record(name)
        if source_record["scenario"] != scenario["id"]:
            raise AcceptanceError(
                f"run fixture {name} is not declared for {scenario['id']}"
            )
        installed = user_data / name
        if not installed.is_file() or _is_link_or_junction(installed):
            raise AcceptanceError(f"required run fixture is not installed: {installed}")
        actual = _file_record(installed)
        if (
            actual["bytes"] != source_record["bytes"]
            or actual["sha256"] != source_record["sha256"]
        ):
            raise AcceptanceError(f"installed run fixture hash disagrees: {installed}")
        records.append(
            {
                **requirement,
                "claim_limit": source_record["claim_limit"],
                "purpose": source_record["purpose"],
                **actual,
            }
        )
    return records


def _build_evidence_manifest_template(
    scenario: dict[str, object],
    phase: str | None,
    session_sha256: str,
    contract_sha256: str,
    fixture_records: Sequence[dict[str, object]],
) -> dict[str, object]:
    normalized = _normalized_evidence_contract(scenario, phase)
    artifacts: list[dict[str, object]] = []
    for role, kind in normalized["artifact_roles"].items():
        spec = normalized["artifact_specs"][role]
        if kind == "log":
            source = "automatic_log"
        elif kind == "settings":
            source = "automatic_settings"
        elif kind == "external_save":
            source = "sealed_input"
        elif kind == "process_observation":
            source = "process_observation"
        elif kind == "vfs_inventory" and "daily_vfs" in role:
            source = "daily_vfs_inventory"
        elif kind == "vfs_inventory" and "isolated_vfs" in role:
            source = "isolated_vfs_inventory"
        else:
            source = "operator_file"
        artifacts.append(
            {
                "role": role,
                "kind": kind,
                "source": source,
                **(
                    {
                        "min_items": spec["min_items"],
                        **(
                            {
                                "cases": {
                                    case_id: "" for case_id in spec["case_ids"]
                                }
                            }
                            if "case_ids" in spec
                            else {"paths": []}
                        ),
                    }
                    if kind == "screenshot_set"
                    else {"paths": []}
                ),
            }
        )
    return {
        "schema": EVIDENCE_MANIFEST_SCHEMA,
        "scenario_id": scenario["id"],
        "phase": normalized["phase"],
        "session_sha256": session_sha256,
        "contract_sha256": contract_sha256,
        "artifacts": artifacts,
        "assertions": [
            {
                "id": item["id"],
                "status": "PENDING",
                "note": "",
                "attestor": "",
                "attested_at": "",
                "artifact_roles": [],
            }
            for item in normalized["assertions"]
        ],
        "fixture_uses": [
            {
                "name": item["name"],
                "console_screenshot_role": item["console_screenshot_role"],
                "before_save_role": item["before_save_role"],
                "after_save_role": item["after_save_role"],
                "note": "",
            }
            for item in fixture_records
        ],
    }


def _dependency_artifact_records(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or not value or not all(
        isinstance(item, dict) for item in value
    ):
        raise AcceptanceError("parent artifact role has no sealed evidence records")
    return value


def _validate_dependency_closure(
    scenario: dict[str, object],
    phase: str | None,
    sealed_inputs: Sequence[dict[str, object]],
    parents: Sequence[dict[str, object]],
    expected_parent_compatibility: dict[str, object],
) -> None:
    normalized = _normalized_evidence_contract(scenario, phase)
    if not all(
        isinstance(item, dict) and set(item) == _PARENT_DEPENDENCY_RECORD_KEYS
        for item in parents
    ):
        raise AcceptanceError("sealed parent dependency record schema disagrees")
    parent_by_role = {str(item.get("role")): item for item in parents}
    expected_parent_roles = {str(item["role"]) for item in normalized["parents"]}
    if set(parent_by_role) != expected_parent_roles or len(parent_by_role) != len(parents):
        raise AcceptanceError(
            "--parent-collection roles do not exactly match the scenario contract"
        )
    for requirement in normalized["parents"]:
        actual = parent_by_role[str(requirement["role"])]
        sealed_hash_pairs = (
            ("artifact_roles", "artifact_roles_sha256"),
            ("assertions", "assertions_sha256"),
            ("snapshots", "snapshots_sha256"),
            ("sealed_inputs", "sealed_inputs_sha256"),
            ("parent_dependencies", "parent_dependencies_sha256"),
            ("fixture_uses", "fixture_uses_sha256"),
            ("required_fixture_records", "required_fixture_records_sha256"),
        )
        if (
            actual.get("scenario_id") != requirement["scenario"]
            or actual.get("phase") != requirement["phase"]
            or actual.get("collection_status") != "READY_FOR_LEAD_REVIEW"
            or actual.get("ready_for_lead_review") is not True
            or actual.get("automated_checks_passed") is not True
            or actual.get("manual_assertions_complete") is not True
            or actual.get("manual_assertions_passed") is not True
            or any(
                actual.get(digest_key) != _object_sha256(actual.get(value_key))
                for value_key, digest_key in sealed_hash_pairs
            )
            or not isinstance(actual.get("artifact_roles"), dict)
            or any(
                not isinstance(actual.get(key), list)
                for key in (
                    "assertions",
                    "snapshots",
                    "sealed_inputs",
                    "parent_dependencies",
                    "fixture_uses",
                    "required_fixture_records",
                )
            )
            or not isinstance(actual.get("runtime_oracle_evidence_sha256"), str)
            or not re.fullmatch(
                r"[0-9a-f]{64}",
                str(actual.get("runtime_oracle_evidence_sha256")),
            )
        ):
            raise AcceptanceError(
                f"parent collection identity disagrees for {requirement['role']}"
            )
        if actual.get("compatibility") != expected_parent_compatibility:
            raise AcceptanceError(
                f"parent collection compatibility disagrees for {requirement['role']}"
            )

    input_by_role = {str(item.get("role")): item for item in sealed_inputs}
    expected_input_roles = {str(item["role"]) for item in normalized["inputs"]}
    if set(input_by_role) != expected_input_roles or len(input_by_role) != len(sealed_inputs):
        raise AcceptanceError("--input-save roles do not exactly match the contract")
    for requirement in normalized["inputs"]:
        role = str(requirement["role"])
        actual = input_by_role[role]
        if requirement.get("source") == "external_original":
            continue
        parent = parent_by_role[str(requirement["parent_collection_role"])]
        artifact_roles = parent.get("artifact_roles")
        if not isinstance(artifact_roles, dict):
            raise AcceptanceError("parent collection artifact_roles are malformed")
        parent_records = _dependency_artifact_records(
            artifact_roles.get(str(requirement["parent_artifact_role"]))
        )
        save_records = [item for item in parent_records if item.get("kind") in {"save", "external_save"}]
        if len(save_records) != 1 or save_records[0].get("sha256") != actual.get("sha256"):
            raise AcceptanceError(
                f"sealed input {role} does not match its exact parent artifact"
            )


def before_session(
    user_data: Path,
    scenario_id: str,
    phase: str | None,
    evidence_root: Path | None,
    descriptors: Sequence[Path],
    candidate_revision: str | None = None,
    daily_user_data: Path | None = None,
    repo: Path | None = None,
    game_root: Path | None = None,
    permission_reference: str | None = None,
    input_saves: Sequence[str] = (),
    parent_collections: Sequence[str] = (),
) -> dict[str, object]:
    _assert_processes_stopped()
    repo, game_root = _require_canonical_runtime_roots(
        repo or HELPER_REPO_ROOT,
        game_root or DEFAULT_GAME_ROOT,
    )
    game_pins = _verified_twelve_pins(repo, game_root)
    user_data = _require_canonical_acceptance_user_data(user_data)
    daily_user_data = _require_canonical_daily_user_data(
        daily_user_data or DEFAULT_USER_DATA, game_root
    )
    _require_disjoint_roots(
        user_data, daily_user_data, "acceptance and daily user-data roots"
    )
    scenario = _scenario(scenario_id)
    if str(scenario["id"]).upper() == "R13":
        raise AcceptanceError("R13 is release closure and cannot create a game session")
    if not isinstance(permission_reference, str) or not permission_reference.strip():
        raise AcceptanceError(
            "before-session requires a non-empty --permission-reference for the "
            "user's explicit visible-start authorization"
        )
    permission_reference = permission_reference.strip()
    if len(permission_reference) > 2000:
        raise AcceptanceError("permission reference is unreasonably long")
    candidate_revision = candidate_revision or _current_candidate_revision()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_revision):
        raise AcceptanceError(
            f"invalid current candidate revision: {candidate_revision!r}"
        )
    root = _require_canonical_evidence_root(
        user_data, evidence_root, create=True
    )
    _assert_no_active_session(user_data, "start another session")
    active_nonce = secrets.token_hex(32)
    _create_active_placeholder(user_data, active_nonce)
    session: Path | None = None
    try:
        contract, _ = _scenario_session_contract(scenario, phase)
        required_components = contract.get("required_components", ())
        if not isinstance(required_components, list):
            raise AcceptanceError("required_components must be a list")
        snapshot_records = _verified_session_snapshots(
            user_data, descriptors, allow_empty=not required_components
        )
        selected_phase = _verify_session_snapshot_contract(
            scenario, phase, snapshot_records, candidate_revision
        )
        ordered_snapshots = _canonical_snapshot_order(snapshot_records)
        expected_config = _expected_dlc_configuration(
            scenario, selected_phase, ordered_snapshots
        )
        dlc_config = _dlc_load(user_data)
        if dlc_config != expected_config:
            raise AcceptanceError(
                "active playset/DLC lists do not exactly match canonical component "
                "order and scenario contract"
            )
        configure_receipt = _verified_configure_receipt(
            user_data,
            scenario,
            selected_phase,
            candidate_revision,
            ordered_snapshots,
            expected_config,
        )
        contract_identity, contract_sha256 = _scenario_contract_identity(
            scenario, selected_phase
        )
        now = _utc_now()
        phase_suffix = f"_{selected_phase}" if selected_phase else ""
        session = root / (
            f"{now.strftime('%Y%m%dT%H%M%SZ')}_{str(scenario['id']).lower()}"
            f"{phase_suffix}_{uuid.uuid4().hex[:8]}"
        )
        session.mkdir()
        before_logs = session / "before" / "logs"
        before_logs.mkdir(parents=True)
        copied_logs: list[dict[str, object]] = []
        logs = user_data / "logs"
        if os.path.lexists(logs):
            if not logs.is_dir() or _is_link_or_junction(logs):
                raise AcceptanceError(f"acceptance logs root is not ordinary: {logs}")
            for source in sorted(logs.glob("*.log")):
                if not source.is_file() or _is_link_or_junction(source):
                    raise AcceptanceError(f"acceptance log is not ordinary: {source}")
                destination = before_logs / source.name
                shutil.copy2(source, destination)
                copied_logs.append(
                    {"source_path": str(source.resolve()), **_file_record(destination)}
                )
        normalized = _normalized_evidence_contract(scenario, selected_phase)
        runtime_oracle = _seal_runtime_oracle(
            session, scenario, normalized, repo, game_root, ordered_snapshots
        )
        sealed_inputs = _seal_input_saves(session, input_saves)
        parents = _seal_parent_collections(parent_collections)
        expected_parent_compatibility = {
            "matrix_sha256": _scenario_matrix_sha256(),
            "candidate_revision": candidate_revision,
            "game_pins": game_pins,
            "repo": str(repo),
            "game_root": str(game_root),
            "user_data": str(user_data),
            "daily_user_data": str(daily_user_data),
        }
        _validate_dependency_closure(
            scenario,
            selected_phase,
            sealed_inputs,
            parents,
            expected_parent_compatibility,
        )
        fixture_records = _required_fixture_records_for_contract(
            scenario, selected_phase, user_data
        )
        isolated_baseline = _isolated_configuration_inventory(user_data)
        daily_baseline = _daily_vfs_inventory(daily_user_data)
        runtime_output_baseline = _acceptance_runtime_output_inventory(user_data)
        artifact_baseline = _artifact_inventory(user_data)
        session_id = uuid.uuid4().hex
        record = {
            "schema": SESSION_SCHEMA,
            "session_id": session_id,
            "active_nonce": active_nonce,
            "scenario": scenario,
            "phase": selected_phase,
            "contract_identity": contract_identity,
            "contract_sha256": contract_sha256,
            "matrix_sha256": expected_parent_compatibility["matrix_sha256"],
            "candidate_revision": candidate_revision,
            "started_at": now.isoformat(),
            "started_at_ns": int(now.timestamp() * 1_000_000_000),
            "repo": str(repo),
            "game_root": str(game_root),
            "game_pins": game_pins,
            "expected_argv": _expected_eu4_argv(game_root, user_data),
            "permission_reference": permission_reference,
            "user_data": str(user_data),
            "daily_user_data": str(daily_user_data),
            "evidence_root": str(root),
            "snapshots": ordered_snapshots,
            "dlc_load": dlc_config,
            "configure_receipt": configure_receipt,
            "isolated_configuration_baseline": isolated_baseline,
            "daily_vfs_baseline": daily_baseline,
            "daily_vfs_coverage": list(DAILY_VFS_COVERAGE),
            "daily_vfs_hash_policy": (
                "all top-level entries recursively inventoried; full SHA-256 through "
                "4 MiB and for every critical top-level configuration file; three "
                "bounded 64-KiB windows plus exact path/type/size/mtime for other "
                "larger files; the daily mod tree uses complete metadata topology"
            ),
            "runtime_output_baseline": runtime_output_baseline,
            "artifact_inventory": artifact_baseline,
            "required_fixture_records": fixture_records,
            "runtime_oracle": runtime_oracle,
            "sealed_inputs": sealed_inputs,
            "parents": parents,
            "before_logs": copied_logs,
            "game_started_by_tool": False,
        }
        session_sha256, _ = _write_session_and_seal(session, record)
        manifest = _build_evidence_manifest_template(
            scenario,
            selected_phase,
            session_sha256,
            contract_sha256,
            fixture_records,
        )
        _exclusive_write_json(session / EVIDENCE_MANIFEST_NAME, manifest)
        _activate_session(user_data, active_nonce, session, session_sha256)
        return {
            "session": str(session),
            "scenario": scenario["id"],
            "phase": selected_phase,
            "session_sha256": session_sha256,
            "contract_sha256": contract_sha256,
            "evidence_manifest": str(session / EVIDENCE_MANIFEST_NAME),
            "expected_argv": record["expected_argv"],
            "game_started": False,
        }
    except Exception:
        _remove_active_if_nonce(user_data, active_nonce)
        if session is not None and session.exists() and _is_relative_to(session, root):
            shutil.rmtree(session)
        raise


def _copy_artifact(
    source: Path, destination_root: Path, *, max_bytes: int | None = None
) -> dict[str, object]:
    source = source.expanduser().absolute()
    if not source.is_file() or _is_link_or_junction(source):
        raise AcceptanceError(f"artifact source must be an ordinary file: {source}")
    destination_root.mkdir(parents=True, exist_ok=True)
    destination_root = _require_ordinary_directory(
        destination_root, "artifact destination directory"
    )
    source_before = source.stat()
    if max_bytes is not None and (
        isinstance(max_bytes, bool)
        or not isinstance(max_bytes, int)
        or max_bytes < 0
        or source_before.st_size > max_bytes
    ):
        raise AcceptanceError(f"artifact source exceeds copy limit: {source}")
    temporary = destination_root / f".jxp-copy-{uuid.uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    digest = sha256()
    copied_bytes = 0
    try:
        with source.open("rb") as input_stream, os.fdopen(
            descriptor, "wb"
        ) as output_stream:
            descriptor = -1
            opened = os.fstat(input_stream.fileno())
            if any(
                getattr(opened, key) != getattr(source_before, key)
                for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
            ):
                raise AcceptanceError(f"artifact source changed before copy: {source}")
            while True:
                chunk = input_stream.read(1024 * 1024)
                if not chunk:
                    break
                if max_bytes is not None and copied_bytes + len(chunk) > max_bytes:
                    raise AcceptanceError(f"artifact source grew beyond copy limit: {source}")
                output_stream.write(chunk)
                digest.update(chunk)
                copied_bytes += len(chunk)
            output_stream.flush()
            os.fsync(output_stream.fileno())
            opened_after = os.fstat(input_stream.fileno())
            if any(
                getattr(opened_after, key) != getattr(opened, key)
                for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
            ):
                raise AcceptanceError(f"artifact source changed during copy: {source}")
        source_after = source.stat()
        source_digest = digest.hexdigest()
        if (
            _is_link_or_junction(source)
            or copied_bytes != source_before.st_size
            or any(
                getattr(source_after, key) != getattr(source_before, key)
                for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
            )
            or _sha256_file(source) != source_digest
            or _sha256_file(temporary) != source_digest
        ):
            raise AcceptanceError(f"artifact source/copy identity changed: {source}")
        os.utime(
            temporary,
            ns=(source_before.st_atime_ns, source_before.st_mtime_ns),
        )
        destination = destination_root / source.name

        def existing_matches(path: Path) -> bool:
            return (
                path.is_file()
                and not _is_link_or_junction(path)
                and path.stat().st_size == copied_bytes
                and _sha256_file(path) == source_digest
            )

        if os.path.lexists(destination):
            if existing_matches(destination):
                return _file_record(destination)
            destination = (
                destination_root
                / f"{source.stem}-{source_digest[:12]}{source.suffix}"
            )
            if os.path.lexists(destination):
                if existing_matches(destination):
                    return _file_record(destination)
                raise AcceptanceError(f"artifact destination collision: {destination}")
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            if not existing_matches(destination):
                raise AcceptanceError(
                    f"artifact destination raced with another file: {destination}"
                ) from exc
        if not existing_matches(destination):
            raise AcceptanceError(f"artifact committed copy verification failed: {destination}")
        return _file_record(destination)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if os.path.lexists(temporary):
            temporary.unlink()


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
        "session_id",
        "active_nonce",
        "scenario",
        "phase",
        "contract_identity",
        "contract_sha256",
        "matrix_sha256",
        "candidate_revision",
        "started_at",
        "started_at_ns",
        "repo",
        "game_root",
        "game_pins",
        "expected_argv",
        "permission_reference",
        "user_data",
        "daily_user_data",
        "evidence_root",
        "snapshots",
        "dlc_load",
        "configure_receipt",
        "isolated_configuration_baseline",
        "daily_vfs_baseline",
        "daily_vfs_coverage",
        "daily_vfs_hash_policy",
        "runtime_output_baseline",
        "artifact_inventory",
        "required_fixture_records",
        "runtime_oracle",
        "sealed_inputs",
        "parents",
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
        or str(scenario.get("id")).upper() == "R13"
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
    if not isinstance(snapshots, list) or not all(
        isinstance(item, dict) for item in snapshots
    ):
        raise AcceptanceError("session snapshots are malformed")
    phase = record["phase"]
    if phase is not None and not isinstance(phase, str):
        raise AcceptanceError("session phase must be a string or null")
    selected_phase = _verify_session_snapshot_contract(
        scenario, phase, snapshots, candidate_revision
    )
    if selected_phase != phase:
        raise AcceptanceError("session phase no longer matches its scenario contract")
    contract_identity, contract_sha256 = _scenario_contract_identity(scenario, phase)
    if (
        record["contract_identity"] != contract_identity
        or record["contract_sha256"] != contract_sha256
    ):
        raise AcceptanceError("session evidence contract is stale or has changed")
    normalized = _normalized_evidence_contract(scenario, phase)
    stored_oracle = record["runtime_oracle"]
    if normalized.get("runtime_oracle") is None:
        if stored_oracle is not None:
            raise AcceptanceError("non-R12 session unexpectedly contains an oracle")
    elif (
        not isinstance(stored_oracle, dict)
        or set(stored_oracle)
        != {
            "contract",
            "source_path",
            "sealed_path",
            "bytes",
            "mtime_ns",
            "sha256",
        }
        or stored_oracle.get("contract")
        != _oracle_contract_summary(normalized["runtime_oracle"])
        or not isinstance(stored_oracle.get("source_path"), str)
        or not isinstance(stored_oracle.get("sealed_path"), str)
        or isinstance(stored_oracle.get("bytes"), bool)
        or not isinstance(stored_oracle.get("bytes"), int)
        or isinstance(stored_oracle.get("mtime_ns"), bool)
        or not isinstance(stored_oracle.get("mtime_ns"), int)
        or not isinstance(stored_oracle.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(stored_oracle["sha256"]))
    ):
        raise AcceptanceError("sealed R12 oracle session record disagrees")
    if record["matrix_sha256"] != _scenario_matrix_sha256():
        raise AcceptanceError("session runtime matrix hash is stale or invalid")
    if (
        not isinstance(record["session_id"], str)
        or not re.fullmatch(r"[0-9a-f]{32}", record["session_id"])
        or not isinstance(record["active_nonce"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", record["active_nonce"])
        or not isinstance(record["contract_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", record["contract_sha256"])
        or not isinstance(record["matrix_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", record["matrix_sha256"])
    ):
        raise AcceptanceError("session identity fields are invalid")
    if (
        not isinstance(record["started_at"], str)
        or isinstance(record["started_at_ns"], bool)
        or not isinstance(record["started_at_ns"], int)
        or not isinstance(record["user_data"], str)
        or not isinstance(record["daily_user_data"], str)
        or not isinstance(record["evidence_root"], str)
        or not isinstance(record["repo"], str)
        or not isinstance(record["game_root"], str)
        or not isinstance(record["game_pins"], list)
        or len(record["game_pins"]) != 12
        or not isinstance(record["expected_argv"], list)
        or len(record["expected_argv"]) != 2
        or not all(isinstance(item, str) for item in record["expected_argv"])
        or not isinstance(record["permission_reference"], str)
        or not record["permission_reference"].strip()
        or not isinstance(record["dlc_load"], dict)
        or not isinstance(record["configure_receipt"], dict)
        or not isinstance(record["isolated_configuration_baseline"], list)
        or not isinstance(record["daily_vfs_baseline"], list)
        or record["daily_vfs_coverage"] != list(DAILY_VFS_COVERAGE)
        or not isinstance(record["daily_vfs_hash_policy"], str)
        or not isinstance(record["runtime_output_baseline"], list)
        or not isinstance(record["artifact_inventory"], list)
        or not isinstance(record["required_fixture_records"], list)
        or (
            record["runtime_oracle"] is not None
            and not isinstance(record["runtime_oracle"], dict)
        )
        or not isinstance(record["sealed_inputs"], list)
        or not isinstance(record["parents"], list)
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


def _active_session_matches(
    user_data: Path,
    session: Path,
    session_sha256: str,
    active_nonce: str,
) -> dict[str, object]:
    active = _read_active_session(user_data)
    if (
        Path(str(active["session"])).resolve() != session.resolve()
        or active.get("session_sha256") != session_sha256
        or active.get("nonce") != active_nonce
    ):
        raise AcceptanceError("active-session lock does not identify this session")
    return active


def _require_recorded_session_location(
    session: Path,
    record: dict[str, object],
) -> tuple[Path, Path]:
    """Bind a session to one direct child of its canonical safe evidence root."""

    user_data = _require_canonical_acceptance_user_data(
        Path(str(record["user_data"]))
    )
    evidence_root = _require_canonical_evidence_root(
        user_data, Path(str(record["evidence_root"])), create=False
    )
    if (
        not _is_relative_to(evidence_root, user_data)
        or session.parent != evidence_root
        or not _is_relative_to(session, evidence_root)
    ):
        raise AcceptanceError(
            "session must be a direct child of its recorded canonical evidence root"
        )
    return user_data, evidence_root


def _release_active_session(
    user_data: Path,
    session: Path,
    session_sha256: str,
    active_nonce: str,
    label: str,
) -> None:
    active_path = _active_session_path(user_data)
    if not os.path.lexists(active_path):
        return
    active = _active_session_matches(
        user_data, session, session_sha256, active_nonce
    )
    _retire_active_lock_value(user_data, active, label)


def observe_process(session: Path) -> dict[str, object]:
    """Observe, but never start or mutate, the one pinned EU4 process."""
    session = _require_ordinary_directory(session, "evidence session")
    seal, session_sha256 = _verified_session_seal(session)
    record = _validate_session_record(
        _read_json_object(_session_file(session), "session record")
    )
    user_data, _ = _require_recorded_session_location(session, record)
    _active_session_matches(
        user_data, session, session_sha256, str(record["active_nonce"])
    )
    active_processes = set(_running_eu4_processes())
    if active_processes != {"eu4.exe"}:
        raise AcceptanceError(
            "observe-process requires eu4.exe to be the only EU4/Launcher-family "
            f"process; found {sorted(active_processes)}"
        )
    processes = _eu4_process_details()
    if len(processes) != 1:
        raise AcceptanceError(
            f"observe-process requires exactly one eu4.exe process; found {len(processes)}"
        )
    process = processes[0]
    executable_value = process.get("ExecutablePath")
    command_line = process.get("CommandLine")
    creation_date = process.get("CreationDate")
    pid = process.get("ProcessId")
    if (
        isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        or not isinstance(executable_value, str)
        or not executable_value
        or not isinstance(command_line, str)
        or not command_line
        or not isinstance(creation_date, str)
        or not creation_date
    ):
        raise AcceptanceError("observed EU4 process lacks PID/path/command line")
    started_at = _aware_datetime(record["started_at"], "session started_at")
    creation_at = _aware_datetime(creation_date, "EU4 process CreationDate")
    observed_at = _utc_now()
    skew_seconds = FRESHNESS_CLOCK_SKEW_NS / 1_000_000_000
    if creation_at.timestamp() < started_at.timestamp() - skew_seconds:
        raise AcceptanceError("observed EU4 process predates this acceptance session")
    if creation_at.timestamp() > observed_at.timestamp() + skew_seconds:
        raise AcceptanceError("observed EU4 process CreationDate is in the future")
    expected_argv = record["expected_argv"]
    expected_executable = Path(str(expected_argv[0])).resolve()
    executable = Path(executable_value).resolve()
    argv = _windows_command_line_argv(command_line)
    if executable != expected_executable:
        raise AcceptanceError(
            f"observed EU4 executable disagrees; expected {expected_executable}, found {executable}"
        )
    if len(argv) != 2 or Path(argv[0]).resolve() != expected_executable:
        raise AcceptanceError(f"observed EU4 argv is not the unique expected pair: {argv!r}")
    expected_option = str(expected_argv[1])
    if (
        argv[1] != expected_option
        or not argv[1].startswith("-userdir=")
        or sum(argument.startswith("-userdir=") for argument in argv[1:]) != 1
    ):
        raise AcceptanceError(
            "observed command line must contain the exact lower-case, non-repeated "
            f"userdir option {expected_option!r} and no other argument"
        )
    payload: dict[str, object] = {
        "schema": SESSION_SCHEMA,
        "session_id": record["session_id"],
        "session_sha256": session_sha256,
        "observed_at": observed_at.isoformat(),
        "pid": pid,
        "executable_path": str(executable),
        "command_line": command_line,
        "creation_date": creation_date,
        "argv": argv,
        "expected_argv": expected_argv,
        "matched": True,
        "process_mutated_or_started_by_tool": False,
    }
    observation = _sealed_value(payload, "observation_sha256")
    target = session / PROCESS_OBSERVATION_NAME
    try:
        _exclusive_write_json(target, observation)
    except FileExistsError as exc:
        raise AcceptanceError(f"process observation already exists: {target}") from exc
    return observation


def _verified_process_observation(
    session: Path,
    record: dict[str, object],
    session_sha256: str,
) -> dict[str, object]:
    value = _verify_self_seal(
        _read_json_object(session / PROCESS_OBSERVATION_NAME, "process observation"),
        "observation_sha256",
        "process observation",
    )
    required = {
        "schema",
        "session_id",
        "session_sha256",
        "observed_at",
        "pid",
        "executable_path",
        "command_line",
        "creation_date",
        "argv",
        "expected_argv",
        "matched",
        "process_mutated_or_started_by_tool",
        "observation_sha256",
    }
    if (
        set(value) != required
        or value.get("schema") != SESSION_SCHEMA
        or value.get("session_id") != record["session_id"]
        or value.get("session_sha256") != session_sha256
        or value.get("expected_argv") != record["expected_argv"]
        or value.get("argv") != record["expected_argv"]
        or value.get("matched") is not True
        or value.get("process_mutated_or_started_by_tool") is not False
    ):
        raise AcceptanceError("process observation identity or exact argv disagrees")
    expected_executable = Path(str(record["expected_argv"][0])).resolve()
    if Path(str(value["executable_path"])).resolve() != expected_executable:
        raise AcceptanceError("process observation executable path disagrees")
    started_at = _aware_datetime(record["started_at"], "session started_at")
    creation_at = _aware_datetime(value["creation_date"], "process creation_date")
    observed_at = _aware_datetime(value["observed_at"], "process observed_at")
    skew_seconds = FRESHNESS_CLOCK_SKEW_NS / 1_000_000_000
    if (
        creation_at.timestamp() < started_at.timestamp() - skew_seconds
        or creation_at.timestamp() > observed_at.timestamp() + skew_seconds
    ):
        raise AcceptanceError("process observation timestamps disagree with the session")
    return value


def abort_session(session: Path, reason: str) -> dict[str, object]:
    _assert_processes_stopped()
    if not isinstance(reason, str) or not reason.strip():
        raise AcceptanceError("abort-session requires a non-empty --reason")
    session = _require_ordinary_directory(session, "evidence session")
    if os.path.lexists(session / COLLECTION_NAME) or os.path.lexists(
        session / COLLECTION_SEAL_NAME
    ):
        raise AcceptanceError("a collected/finalized session cannot be aborted")
    _, session_sha256 = _verified_session_seal(session)
    record = _validate_session_record(
        _read_json_object(_session_file(session), "session record")
    )
    user_data, _ = _require_recorded_session_location(session, record)
    payload = {
        "schema": SESSION_SCHEMA,
        "session_id": record["session_id"],
        "session_sha256": session_sha256,
        "aborted_at": _utc_now().isoformat(),
        "reason": reason.strip(),
        "game_started_by_tool": False,
    }
    value = _sealed_value(payload, "abort_sha256")
    target = session / "abort.json"
    if not os.path.lexists(target):
        _exclusive_write_json(target, value)
    else:
        existing = _verify_self_seal(
            _read_json_object(target, "abort record"),
            "abort_sha256",
            "abort record",
        )
        expected_keys = set(value)
        if (
            set(existing) != expected_keys
            or existing.get("schema") != SESSION_SCHEMA
            or existing.get("session_id") != record["session_id"]
            or existing.get("session_sha256") != session_sha256
            or existing.get("reason") != reason.strip()
            or existing.get("game_started_by_tool") is not False
        ):
            raise AcceptanceError("existing abort record does not match this request")
        _aware_datetime(existing.get("aborted_at"), "abort aborted_at")
        value = existing
    _release_active_session(
        user_data,
        session,
        session_sha256,
        str(record["active_nonce"]),
        "abort-session",
    )
    return {"status": "aborted", "session": str(session), **value}


def _artifact_baseline_by_path(record: dict[str, object]) -> dict[str, dict[str, object]]:
    baseline = record.get("artifact_inventory")
    if not isinstance(baseline, list):
        raise AcceptanceError("session artifact inventory is malformed")
    by_path: dict[str, dict[str, object]] = {}
    for item in baseline:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise AcceptanceError("session artifact inventory entry is malformed")
        normalized = str(Path(str(item["path"])).resolve())
        if normalized in by_path:
            raise AcceptanceError("session artifact inventory repeats a path")
        by_path[normalized] = item
    return by_path


def _require_new_or_changed_artifact(
    source: Path,
    baseline_by_path: dict[str, dict[str, object]],
) -> None:
    before = baseline_by_path.get(str(source.resolve()))
    if before is None:
        return
    if (
        before.get("bytes") == source.stat().st_size
        and before.get("sha256") == _sha256_file(source)
    ):
        raise AcceptanceError(
            f"evidence artifact existed unchanged before this session: {source}"
        )


def _copy_role_artifact(
    source: Path,
    destination_root: Path,
    role: str,
    kind: str,
    validation: dict[str, object],
) -> dict[str, object]:
    copied = _copy_artifact(source, destination_root / role)
    copied_validation = _validate_artifact_format(Path(str(copied["path"])), kind)
    if copied_validation != validation:
        raise AcceptanceError(
            f"copied artifact validation changed while binding role {role}"
        )
    return {
        "role": role,
        "kind": kind,
        "source_path": str(source.resolve()),
        "validation": copied_validation,
        **copied,
    }


def _validate_r12_typed_checklist(
    path: Path,
    role: str,
    normalized: dict[str, object],
) -> dict[str, object]:
    oracle = normalized.get("runtime_oracle")
    if not isinstance(oracle, dict) or not isinstance(
        oracle.get("case_contracts"), dict
    ):
        raise AcceptanceError("R12 typed checklist has no verified oracle context")
    expected_cases = {
        case_id: contract
        for case_id, contract in oracle["case_contracts"].items()
        if any(
            isinstance(binding, dict) and binding.get("role") == role
            for binding in contract.get("evidence_bindings", [])
        )
    }
    if not expected_cases:
        raise AcceptanceError(f"R12 checklist role has no typed cases: {role}")
    value = _read_json_object(path, f"R12 typed checklist {role}")
    if (
        set(value)
        != {"schema", "scenario_id", "role", "oracle_pack_sha256", "cases"}
        or value.get("schema") != "jxp_runtime_typed_case_evidence/v1"
        or value.get("scenario_id") != "R12"
        or value.get("role") != role
        or value.get("oracle_pack_sha256") != oracle.get("sha256")
        or not isinstance(value.get("cases"), dict)
        or set(value["cases"]) != set(expected_cases)
    ):
        raise AcceptanceError(f"R12 typed checklist identity/case set disagrees: {role}")
    for case_id, contract in expected_cases.items():
        item = value["cases"][case_id]
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "status",
                "note",
                "attestor",
                "attested_at",
                "oracle_pointer",
                "oracle_object_sha256",
                "observed",
            }
            or item.get("status") != "PASS"
            or not isinstance(item.get("note"), str)
            or not str(item["note"]).strip()
            or not isinstance(item.get("attestor"), str)
            or not str(item["attestor"]).strip()
            or item.get("oracle_pointer") != contract.get("pointer")
            or item.get("oracle_object_sha256")
            != contract.get("oracle_object_sha256")
            or not isinstance(item.get("observed"), dict)
            or not item["observed"]
        ):
            raise AcceptanceError(
                f"R12 typed checklist terminal attestation disagrees: {case_id}"
            )
        timestamp = item.get("attested_at")
        if not isinstance(timestamp, str):
            raise AcceptanceError(f"R12 typed checklist timestamp is missing: {case_id}")
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AcceptanceError(
                f"R12 typed checklist timestamp is invalid: {case_id}"
            ) from exc
        if (
            parsed.tzinfo is None
            or parsed.utcoffset() is None
            or parsed.utcoffset().total_seconds() != 0
        ):
            raise AcceptanceError(
                f"R12 typed checklist timestamp must be UTC: {case_id}"
            )
    return {
        "format": "r12-typed-case-checklist",
        "role": role,
        "case_count": len(expected_cases),
        "case_ids_sha256": _object_sha256(sorted(expected_cases)),
        "oracle_pack_sha256": oracle["sha256"],
    }


def _copy_process_observation_artifact(
    source: Path,
    destination_root: Path,
    role: str,
    observation: dict[str, object],
) -> dict[str, object]:
    """Bind the sealed process observation without widening generic formats."""

    copied = _copy_artifact(source, destination_root / role)
    copied_path = Path(str(copied["path"]))
    copied_observation = _verify_self_seal(
        _read_json_object(copied_path, "copied process observation"),
        "observation_sha256",
        "copied process observation",
    )
    if copied_observation != observation:
        raise AcceptanceError(
            f"copied process observation changed while binding role {role}"
        )
    return {
        "role": role,
        "kind": "process_observation",
        "source_path": str(source.resolve()),
        "validation": {
            "format": "sealed-process-observation",
            "observation_sha256": observation["observation_sha256"],
            "matched": True,
        },
        **copied,
    }


def _synthetic_evidence_file(
    path: Path,
    value: object,
    role: str,
    kind: str,
) -> dict[str, object]:
    if os.path.lexists(path):
        if not path.is_file() or _is_link_or_junction(path):
            raise AcceptanceError(f"generated evidence path is not ordinary: {path}")
        try:
            existing = _strict_json_loads(
                path.read_text(encoding="utf-8-sig"),
                "existing generated evidence",
            )
        except OSError as exc:
            raise AcceptanceError(
                f"cannot verify existing generated evidence {path}: {exc}"
            ) from exc
        if existing != value:
            raise AcceptanceError(
                f"existing generated evidence disagrees with this collection: {path}"
            )
    else:
        _exclusive_write_json(path, value)
    return {
        "role": role,
        "kind": kind,
        "source_path": str(path),
        "validation": {"format": "generated-json"},
        **_file_record(path),
    }


def _validate_evidence_manifest(
    manifest_path: Path,
    session: Path,
    record: dict[str, object],
    session_sha256: str,
    normalized: dict[str, object],
    automatic_roles: dict[str, list[dict[str, object]]],
    fixture_records: Sequence[dict[str, object]],
    artifacts: Sequence[Path],
) -> tuple[
    dict[str, list[dict[str, object]]],
    list[dict[str, object]],
    bool,
    bool,
    list[dict[str, object]],
    list[dict[str, object]],
]:
    canonical_manifest = (session / EVIDENCE_MANIFEST_NAME).resolve()
    if manifest_path.expanduser().resolve() != canonical_manifest:
        raise AcceptanceError(
            f"collect must use the session's canonical evidence manifest: {canonical_manifest}"
        )
    manifest = _read_json_object(canonical_manifest, "evidence manifest")
    required_top = {
        "schema",
        "scenario_id",
        "phase",
        "session_sha256",
        "contract_sha256",
        "artifacts",
        "assertions",
        "fixture_uses",
    }
    if (
        set(manifest) != required_top
        or manifest.get("schema") != EVIDENCE_MANIFEST_SCHEMA
        or manifest.get("scenario_id") != record["scenario"]["id"]
        or manifest.get("phase") != record["phase"]
        or manifest.get("session_sha256") != session_sha256
        or manifest.get("contract_sha256") != record["contract_sha256"]
    ):
        raise AcceptanceError("evidence manifest identity/schema disagrees")

    raw_artifacts = manifest.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise AcceptanceError("evidence manifest artifacts must be a list")
    entries: dict[str, dict[str, object]] = {}
    for item in raw_artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("role"), str):
            raise AcceptanceError("evidence manifest artifact entry is malformed")
        role = str(item["role"])
        if role in entries:
            raise AcceptanceError(f"evidence manifest repeats artifact role: {role}")
        entries[role] = item
    if set(entries) != set(normalized["artifact_roles"]):
        raise AcceptanceError("evidence manifest artifact roles disagree with matrix")

    baseline = _artifact_baseline_by_path(record)
    prefix = str(normalized["prefix"])
    after_root = session / "after" / "artifacts"
    role_records: dict[str, list[dict[str, object]]] = {}
    used_paths: set[str] = set()
    used_hashes: set[str] = set()
    for role, kind in normalized["artifact_roles"].items():
        item = entries[role]
        spec = normalized["artifact_specs"][role]
        expected_source = (
            "automatic_log"
            if kind == "log"
            else "automatic_settings"
            if kind == "settings"
            else "sealed_input"
            if kind == "external_save"
            else "process_observation"
            if kind == "process_observation"
            else "daily_vfs_inventory"
            if kind == "vfs_inventory" and "daily_vfs" in role
            else "isolated_vfs_inventory"
            if kind == "vfs_inventory" and "isolated_vfs" in role
            else "operator_file"
        )
        has_cases = kind == "screenshot_set" and "case_ids" in spec
        required_keys = {"role", "kind", "source"}
        if has_cases:
            required_keys.update({"min_items", "cases"})
        else:
            required_keys.add("paths")
            if kind == "screenshot_set":
                required_keys.add("min_items")
        if (
            set(item) != required_keys
            or item.get("kind") != kind
            or item.get("source") != expected_source
            or (
                not has_cases
                and (
                    not isinstance(item.get("paths"), list)
                    or not all(isinstance(path, str) for path in item["paths"])
                )
            )
            or (
                has_cases
                and (
                    not isinstance(item.get("cases"), dict)
                    or set(item["cases"]) != set(spec["case_ids"])
                    or not all(isinstance(path, str) for path in item["cases"].values())
                )
            )
            or (
                kind == "screenshot_set"
                and item.get("min_items") != spec.get("min_items")
            )
        ):
            raise AcceptanceError(f"evidence manifest role schema disagrees: {role}")
        if expected_source != "operator_file":
            supplied = list(item["cases"].values()) if has_cases else item["paths"]
            if supplied:
                raise AcceptanceError(f"automatic evidence role must not supply paths: {role}")
            records_for_role = list(automatic_roles.get(role, ()))
        else:
            minimum = int(spec.get("min_items", 1))
            if has_cases:
                path_cases = list(item["cases"].items())
            else:
                path_cases = [(None, path) for path in item["paths"]]
            if len(path_cases) < minimum or any(not path for _, path in path_cases):
                raise AcceptanceError(
                    f"evidence role {role} requires at least {minimum} path(s)"
                )
            if kind != "screenshot_set" and len(path_cases) != 1:
                raise AcceptanceError(f"evidence role {role} requires exactly one path")
            records_for_role = []
            for case_id, raw_path in path_cases:
                source = _resolve_evidence_source(raw_path, Path(str(record["user_data"])), prefix)
                _require_new_or_changed_artifact(source, baseline)
                validation = _validate_artifact_format(source, kind)
                evidence_record = _copy_role_artifact(
                    source, after_root, role, kind, validation
                )
                if (
                    record["scenario"]["id"] == "R12"
                    and kind == "checklist"
                ):
                    source_typed_validation = _validate_r12_typed_checklist(
                        source, role, normalized
                    )
                    copied_typed_validation = _validate_r12_typed_checklist(
                        Path(str(evidence_record["path"])), role, normalized
                    )
                    if copied_typed_validation != source_typed_validation:
                        raise AcceptanceError(
                            f"R12 typed checklist changed while copying: {role}"
                        )
                    evidence_record["validation"] = copied_typed_validation
                if case_id is not None:
                    evidence_record["case_id"] = case_id
                records_for_role.append(evidence_record)
        minimum = int(spec.get("min_items", 1))
        if len(records_for_role) < minimum:
            raise AcceptanceError(
                f"required evidence role {role} has {len(records_for_role)} item(s), needs {minimum}"
            )
        if kind != "screenshot_set" and len(records_for_role) != 1:
            raise AcceptanceError(f"required evidence role {role} is not unique")
        for evidence in records_for_role:
            evidence["supports_assertion_ids"] = list(
                spec["supports_assertion_ids"]
            )
            evidence["distinct"] = True
            evidence_path = str(Path(str(evidence["path"])).resolve())
            digest = str(evidence["sha256"])
            if evidence_path in used_paths or digest in used_hashes:
                raise AcceptanceError(
                    f"one path or SHA-256 cannot satisfy more than one evidence role: {role}"
                )
            used_paths.add(evidence_path)
            used_hashes.add(digest)
        role_records[role] = records_for_role

    appendix: list[dict[str, object]] = []
    for raw_path in artifacts:
        source = _resolve_evidence_source(str(raw_path), Path(str(record["user_data"])), prefix)
        _require_new_or_changed_artifact(source, baseline)
        suffix = source.suffix.lower()
        if suffix in {".png", ".bmp", ".jpg", ".jpeg", ".tga"}:
            kind = "screenshot"
        elif suffix == ".eu4":
            kind = "save"
        else:
            kind = "text"
        validation = _validate_artifact_format(source, kind)
        item = _copy_role_artifact(source, session / "after" / "appendix", "appendix", kind, validation)
        evidence_path = str(Path(str(item["path"])).resolve())
        digest = str(item["sha256"])
        if evidence_path in used_paths or digest in used_hashes:
            raise AcceptanceError("appendix artifact duplicates a required role path/hash")
        used_paths.add(evidence_path)
        used_hashes.add(digest)
        appendix.append(item)

    raw_assertions = manifest.get("assertions")
    if not isinstance(raw_assertions, list):
        raise AcceptanceError("evidence manifest assertions must be a list")
    assertion_by_id: dict[str, dict[str, object]] = {}
    for item in raw_assertions:
        if not isinstance(item, dict) or set(item) != {
            "id",
            "status",
            "note",
            "attestor",
            "attested_at",
            "artifact_roles",
        }:
            raise AcceptanceError("evidence assertion entry schema disagrees")
        assertion_id = item.get("id")
        if not isinstance(assertion_id, str) or assertion_id in assertion_by_id:
            raise AcceptanceError("evidence assertion id is invalid or duplicated")
        assertion_by_id[assertion_id] = item
    expected_assertions = {str(item["id"]) for item in normalized["assertions"]}
    if set(assertion_by_id) != expected_assertions:
        raise AcceptanceError("evidence assertion ids disagree with matrix")
    assertion_results: list[dict[str, object]] = []
    manual_complete = True
    manual_passed = True
    blocker_ids_by_assertion: dict[str, list[str]] = {}
    for blocker in normalized["blockers"]:
        for assertion_id in blocker["blocks_assertion_ids"]:
            if assertion_id in expected_assertions:
                blocker_ids_by_assertion.setdefault(str(assertion_id), []).append(
                    str(blocker["id"])
                )
    for requirement in normalized["assertions"]:
        item = assertion_by_id[str(requirement["id"])]
        status = item.get("status")
        note = item.get("note")
        attestor = item.get("attestor")
        attested_at = item.get("attested_at")
        mapped_roles = item.get("artifact_roles")
        expected_mapped_roles = [
            role
            for role, spec in normalized["artifact_specs"].items()
            if str(requirement["id"]) in spec["supports_assertion_ids"]
        ]
        valid_attested_at = False
        if isinstance(attested_at, str) and attested_at.strip():
            try:
                parsed_attested_at = datetime.fromisoformat(
                    attested_at.strip().replace("Z", "+00:00")
                )
                valid_attested_at = parsed_attested_at.tzinfo is not None
            except ValueError:
                valid_attested_at = False
        if (
            status not in {"PASS", "FAIL", "BLOCKED"}
            or not isinstance(note, str)
            or not note.strip()
            or not isinstance(attestor, str)
            or not attestor.strip()
            or not valid_attested_at
            or not isinstance(mapped_roles, list)
            or mapped_roles != expected_mapped_roles
            or not set(mapped_roles).issubset(role_records)
        ):
            manual_complete = False
        if status != "PASS":
            manual_passed = False
        active_blocker_ids = blocker_ids_by_assertion.get(
            str(requirement["id"]), []
        )
        if active_blocker_ids and status != "BLOCKED":
            raise AcceptanceError(
                f"assertion {requirement['id']} must remain BLOCKED while matrix "
                f"blocker(s) are unresolved: {active_blocker_ids}"
            )
        assertion_results.append(
            {
                "id": requirement["id"],
                "text": requirement["text"],
                "status": status,
                "note": note,
                "attestor": attestor,
                "attested_at": attested_at,
                "artifact_roles": mapped_roles,
                "matrix_blocker_ids": active_blocker_ids,
            }
        )
    if not manual_complete:
        raise AcceptanceError(
            "every assertion must have a terminal status, non-empty note, named "
            "attestor, timezone-aware attested_at, and mapping to collected evidence roles"
        )

    raw_fixture_uses = manifest.get("fixture_uses")
    if not isinstance(raw_fixture_uses, list):
        raise AcceptanceError("evidence manifest fixture_uses must be a list")
    fixture_by_name: dict[str, dict[str, object]] = {}
    for item in raw_fixture_uses:
        if not isinstance(item, dict) or set(item) != {
            "name",
            "console_screenshot_role",
            "before_save_role",
            "after_save_role",
            "note",
        }:
            raise AcceptanceError("fixture-use manifest schema disagrees")
        name = item.get("name")
        if not isinstance(name, str) or name in fixture_by_name:
            raise AcceptanceError("fixture-use name is invalid or duplicated")
        fixture_by_name[name] = item
    expected_fixture_names = {str(item["name"]) for item in fixture_records}
    if set(fixture_by_name) != expected_fixture_names:
        raise AcceptanceError("fixture-use manifest names disagree with contract")
    fixture_results: list[dict[str, object]] = []
    for baseline_fixture in fixture_records:
        name = str(baseline_fixture["name"])
        item = fixture_by_name[name]
        if not isinstance(item.get("note"), str) or not str(item["note"]).strip():
            raise AcceptanceError(f"fixture use requires a non-empty note: {name}")
        for key in (
            "console_screenshot_role",
            "before_save_role",
            "after_save_role",
        ):
            if item.get(key) != baseline_fixture.get(key):
                raise AcceptanceError(f"fixture use {name} {key} disagrees")
        before_records = role_records[str(item["before_save_role"])]
        after_records = role_records[str(item["after_save_role"])]
        if len(before_records) != 1 or len(after_records) != 1:
            raise AcceptanceError(f"fixture use {name} save roles are not unique")
        if before_records[0]["sha256"] == after_records[0]["sha256"]:
            raise AcceptanceError(f"fixture use {name} before/after saves are identical")
        fixture_results.append(
            {
                **item,
                "fixture_sha256": baseline_fixture["sha256"],
                "claim_limit": baseline_fixture["claim_limit"],
                "matched": True,
            }
        )
    return (
        role_records,
        assertion_results,
        manual_complete,
        manual_passed,
        fixture_results,
        appendix,
    )


def _populated_provenance_value(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _external_input_evidence_checks(
    normalized: dict[str, object],
    record: dict[str, object],
    role_records: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    sealed_by_role = {
        str(item.get("role")): item
        for item in record["sealed_inputs"]
        if isinstance(item, dict)
    }
    results: list[dict[str, object]] = []
    for requirement in normalized["inputs"]:
        if requirement.get("source") != "external_original":
            continue
        input_role = str(requirement["role"])
        provenance_role = str(requirement["provenance_role"])
        hash_role = str(requirement["hash_role"])
        sealed = sealed_by_role.get(input_role)
        input_evidence = role_records.get(input_role, [])
        provenance_evidence = role_records.get(provenance_role, [])
        hash_evidence = role_records.get(hash_role, [])
        if (
            sealed is None
            or len(input_evidence) != 1
            or len(provenance_evidence) != 1
            or len(hash_evidence) != 1
            or input_evidence[0].get("sha256") != sealed.get("sha256")
        ):
            raise AcceptanceError(
                f"external input evidence roles do not bind the sealed save: {input_role}"
            )
        provenance_path = Path(str(provenance_evidence[0]["path"]))
        provenance = _read_json_object(
            provenance_path, f"external provenance for {input_role}"
        )
        required_fields = set(str(item) for item in requirement["required_provenance_fields"])
        missing_fields = sorted(required_fields - set(provenance))
        empty_fields = sorted(
            field
            for field in required_fields & set(provenance)
            if not _populated_provenance_value(provenance[field])
        )
        if missing_fields or empty_fields:
            raise AcceptanceError(
                f"external provenance {input_role} missing={missing_fields}, "
                f"empty={empty_fields}"
            )
        expected_bytes = int(sealed["bytes"])
        expected_sha256 = str(sealed["sha256"])
        if (
            isinstance(provenance.get("size_bytes"), bool)
            or provenance.get("size_bytes") != expected_bytes
            or provenance.get("sha256") != expected_sha256
            or provenance.get("original_filename")
            != Path(str(sealed["source_path"])).name
            or provenance.get("unaltered_bytes_attestation") is not True
        ):
            raise AcceptanceError(
                f"external provenance identity/hash/attestation disagrees: {input_role}"
            )
        acquired_at = provenance.get("acquired_at_utc")
        try:
            acquired_datetime = datetime.fromisoformat(
                str(acquired_at).replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise AcceptanceError(
                f"external provenance acquired_at_utc is invalid: {input_role}"
            ) from exc
        if (
            acquired_datetime.tzinfo is None
            or acquired_datetime.utcoffset() is None
            or acquired_datetime.utcoffset().total_seconds() != 0
        ):
            raise AcceptanceError(
                f"external provenance acquired_at_utc must be UTC: {input_role}"
            )
        hash_path = Path(str(hash_evidence[0]["path"]))
        hash_text = hash_path.read_text(encoding="utf-8-sig")
        if expected_sha256 not in hash_text or not re.search(
            rf"(?<!\d){expected_bytes}(?!\d)", hash_text
        ):
            raise AcceptanceError(
                f"external hash manifest lacks the exact size and SHA-256: {input_role}"
            )
        results.append(
            {
                "role": input_role,
                "bytes": expected_bytes,
                "sha256": expected_sha256,
                "provenance_role": provenance_role,
                "provenance_sha256": provenance_evidence[0]["sha256"],
                "hash_role": hash_role,
                "hash_manifest_sha256": hash_evidence[0]["sha256"],
                "required_provenance_fields": list(
                    requirement["required_provenance_fields"]
                ),
                "matched": True,
            }
        )
    return results


def _runtime_oracle_evidence_index(
    normalized: dict[str, object],
    role_records: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    oracle = normalized.get("runtime_oracle")
    if oracle is None:
        return []
    if not isinstance(oracle, dict) or not isinstance(
        oracle.get("case_contracts"), dict
    ):
        raise AcceptanceError("R12 oracle evidence index lacks case contracts")
    result: list[dict[str, object]] = []
    for case_id, contract in oracle["case_contracts"].items():
        bound_artifacts: list[dict[str, object]] = []
        for binding in contract["evidence_bindings"]:
            role = str(binding["role"])
            candidates = role_records.get(role, [])
            evidence_case_id = binding.get("case_id")
            if evidence_case_id is not None:
                candidates = [
                    item
                    for item in candidates
                    if item.get("case_id") == evidence_case_id
                ]
            if len(candidates) != 1:
                raise AcceptanceError(
                    f"R12 typed case does not resolve to one sealed artifact: "
                    f"{case_id} {role} {evidence_case_id}"
                )
            artifact = candidates[0]
            bound_artifacts.append(
                {
                    "role": role,
                    "case_id": evidence_case_id,
                    "artifact_path": artifact["path"],
                    "artifact_sha256": artifact["sha256"],
                }
            )
        result.append(
            {
                "case_id": case_id,
                "type": contract["type"],
                "assertion_ids": contract["assertion_ids"],
                "oracle_pointer": contract["pointer"],
                "oracle_object_sha256": contract["oracle_object_sha256"],
                "artifacts": bound_artifacts,
            }
        )
    if len(result) != 282:
        raise AcceptanceError("R12 oracle evidence index must contain 282 cases")
    return result


def _collect_schema4(
    session: Path,
    artifacts: Sequence[Path],
    evidence_manifest: Path,
) -> tuple[dict[str, object], bool]:
    _assert_processes_stopped()
    session = _require_ordinary_directory(session, "evidence session")
    collection_path = session / COLLECTION_NAME
    collection_seal_path = session / COLLECTION_SEAL_NAME
    if (
        os.path.lexists(collection_path)
        or os.path.lexists(collection_seal_path)
        or os.path.lexists(session / "abort.json")
    ):
        raise AcceptanceError("session is already collected, sealed, or aborted")
    _, session_sha256 = _verified_session_seal(session)
    record = _validate_session_record(
        _read_json_object(_session_file(session), "session record")
    )
    user_data, _ = _require_recorded_session_location(session, record)
    repo, game_root = _require_canonical_runtime_roots(
        Path(str(record["repo"])), Path(str(record["game_root"]))
    )
    daily_user_data = _require_canonical_daily_user_data(
        Path(str(record["daily_user_data"])), game_root
    )
    _require_disjoint_roots(
        user_data, daily_user_data, "acceptance and daily user-data roots"
    )
    _active_session_matches(
        user_data, session, session_sha256, str(record["active_nonce"])
    )
    observation = _verified_process_observation(session, record, session_sha256)
    if record["expected_argv"] != _expected_eu4_argv(game_root, user_data):
        raise AcceptanceError("recorded expected argv is no longer canonical")
    normalized = _normalized_evidence_contract(record["scenario"], record["phase"])
    runtime_oracle_after = _verify_sealed_runtime_oracle(
        record["runtime_oracle"],
        session,
        record["scenario"],
        normalized,
        repo,
        game_root,
        record["snapshots"],
    )
    runtime_oracle_stable = runtime_oracle_after == record["runtime_oracle"]

    pin_records_after = _twelve_pin_records(repo, game_root)
    pins_stable = (
        pin_records_after == record["game_pins"]
        and all(bool(item["matched"]) for item in pin_records_after)
    )
    launcher_daily_matches = False
    if pins_stable:
        launcher_daily_matches = _launcher_daily_user_data(game_root) == daily_user_data

    started_at_ns = int(record["started_at_ns"])
    before_logs_by_name = {
        Path(str(item["path"])).name.lower(): item
        for item in record["before_logs"]
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    after = session / "after"
    log_root = after / "logs"
    copied_logs: list[dict[str, object]] = []
    fresh_log_paths: list[Path] = []
    fresh_log_records: dict[str, dict[str, object]] = {}
    logs = user_data / "logs"
    if os.path.lexists(logs):
        if not logs.is_dir() or _is_link_or_junction(logs):
            raise AcceptanceError(f"acceptance logs root is not ordinary: {logs}")
        for source in sorted(logs.glob("*.log")):
            if not source.is_file() or _is_link_or_junction(source):
                raise AcceptanceError(f"acceptance log is not ordinary: {source}")
            copied = _copy_artifact(source, log_root)
            item = {"source_path": str(source.resolve()), **copied}
            copied_logs.append(item)
            baseline = before_logs_by_name.get(source.name.lower())
            changed = baseline is None or any(
                item[key] != baseline.get(key)
                for key in ("mtime_ns", "sha256", "bytes")
            )
            if changed and int(item["mtime_ns"]) >= started_at_ns - FRESHNESS_CLOCK_SKEW_NS:
                copied_path = Path(str(item["path"]))
                fresh_log_paths.append(copied_path)
                fresh_log_records[source.name.lower()] = item
    missing_logs = sorted({"error.log", "game.log"} - set(fresh_log_records))
    blockers = _scan_logs(fresh_log_paths)
    game_log_path = next(
        (path for path in fresh_log_paths if path.name.lower() == "game.log"), None
    )
    game_version_matched = False
    if game_log_path is not None:
        game_text = game_log_path.read_text(encoding="utf-8-sig", errors="replace")
        version_lines = [
            line.strip()
            for line in game_text.splitlines()
            if line.strip().startswith("Game Version:")
        ]
        game_version_matched = bool(version_lines) and set(version_lines) == {
            EXPECTED_GAME_VERSION_LOG
        }
    passed_log_scan = not blockers and not missing_logs and game_version_matched

    snapshot_checks: list[dict[str, object]] = []
    actual_snapshots: list[dict[str, object]] = []
    for expected in record["snapshots"]:
        descriptor = Path(str(expected["descriptor"]["path"]))
        try:
            actual = _installed_snapshot_record(descriptor, user_data)
            actual_snapshots.append(actual)
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
        except (AcceptanceError, OSError, json.JSONDecodeError) as exc:
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
    snapshot_contract_stable = all(item["matched"] for item in snapshot_checks)

    expected_config = _expected_dlc_configuration(
        record["scenario"], record["phase"], record["snapshots"]
    )
    after_dlc = _dlc_load(user_data)
    exact_dlc_semantics = after_dlc == expected_config == record["dlc_load"]
    receipt_stable = False
    if snapshot_contract_stable:
        try:
            verified_receipt = _verified_configure_receipt(
                user_data,
                record["scenario"],
                record["phase"],
                str(record["candidate_revision"]),
                actual_snapshots,
                expected_config,
            )
            receipt_stable = verified_receipt == record["configure_receipt"]
        except AcceptanceError:
            receipt_stable = False
    isolated_after = _isolated_configuration_inventory(user_data)
    isolated_configuration_stable = (
        isolated_after == record["isolated_configuration_baseline"]
        and exact_dlc_semantics
        and receipt_stable
    )
    daily_after = _daily_vfs_inventory(daily_user_data)
    daily_vfs_stable = daily_after == record["daily_vfs_baseline"]
    runtime_output_after = _acceptance_runtime_output_inventory(user_data)

    runtime_baseline_by_path = {
        str(item.get("path")): item
        for item in record["runtime_output_baseline"]
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    fresh_settings_records: list[dict[str, object]] = []
    for item in runtime_output_after:
        path_value = item.get("path")
        if (
            not isinstance(path_value, str)
            or Path(path_value).name not in {
                "settings.txt",
                "pdx_settings.txt",
                "gameplaysettings.txt",
            }
            or item.get("kind") != "file"
            or isinstance(item.get("mtime_ns"), bool)
            or not isinstance(item.get("mtime_ns"), int)
            or int(item["mtime_ns"])
            < started_at_ns - FRESHNESS_CLOCK_SKEW_NS
            or item == runtime_baseline_by_path.get(path_value)
        ):
            continue
        source = Path(path_value)
        if not source.is_file() or _is_link_or_junction(source):
            raise AcceptanceError(f"runtime settings output is not ordinary: {source}")
        fresh_settings_records.append(
            {
                "source_path": str(source.resolve()),
                "validation": {"format": "engine-settings-output"},
                **_copy_artifact(source, after / "settings"),
            }
        )

    daily_guard_value = {
        "schema": COLLECTION_SCHEMA,
        "session_id": record["session_id"],
        "session_sha256": session_sha256,
        "coverage": record["daily_vfs_coverage"],
        "hash_policy": record["daily_vfs_hash_policy"],
        "before": record["daily_vfs_baseline"],
        "after": daily_after,
        "matched": daily_vfs_stable,
    }
    daily_guard_record = _synthetic_evidence_file(
        after / "system" / "daily_vfs_guard.json",
        daily_guard_value,
        "daily_vfs_inventory",
        "vfs_inventory",
    )
    isolated_guard_value = {
        "schema": COLLECTION_SCHEMA,
        "session_id": record["session_id"],
        "session_sha256": session_sha256,
        "configuration_before": record["isolated_configuration_baseline"],
        "configuration_after": isolated_after,
        "configuration_matched": isolated_configuration_stable,
        "runtime_outputs_before": record["runtime_output_baseline"],
        "runtime_outputs_after": runtime_output_after,
        "artifact_sources_before": record["artifact_inventory"],
        "artifact_sources_after": _artifact_inventory(user_data),
    }
    isolated_guard_record = _synthetic_evidence_file(
        after / "system" / "isolated_vfs_inventory.json",
        isolated_guard_value,
        "isolated_vfs_inventory",
        "vfs_inventory",
    )

    fixture_records_after = _required_fixture_records_for_contract(
        record["scenario"], record["phase"], user_data
    )
    fixtures_stable = fixture_records_after == record["required_fixture_records"]

    sealed_inputs_after: list[dict[str, object]] = []
    for stored in record["sealed_inputs"]:
        if not isinstance(stored, dict) or not isinstance(stored.get("role"), str):
            raise AcceptanceError("sealed input record is malformed")
        role = str(stored["role"])
        sealed_path = Path(str(stored.get("sealed_path", ""))).resolve()
        expected_root = (session / "before" / "inputs").resolve()
        if (
            sealed_path.parent != expected_root
            or sealed_path.name != f"{role}.eu4"
            or not sealed_path.is_file()
            or _is_link_or_junction(sealed_path)
        ):
            raise AcceptanceError(f"sealed input path is invalid: {role}")
        validation = _validate_eu4_save(sealed_path)
        actual = _file_record(sealed_path)
        if any(actual.get(key) != stored.get(key) for key in ("path", "bytes", "sha256")):
            raise AcceptanceError(f"sealed input bytes changed after before-session: {role}")
        if validation != stored.get("validation"):
            raise AcceptanceError(f"sealed input validation changed: {role}")
        sealed_inputs_after.append(dict(stored))

    parents_after: list[dict[str, object]] = []
    for stored in record["parents"]:
        if (
            not isinstance(stored, dict)
            or set(stored) != _PARENT_DEPENDENCY_RECORD_KEYS
            or not isinstance(stored.get("role"), str)
        ):
            raise AcceptanceError("parent collection record is malformed")
        actual = _parent_dependency_record(
            str(stored["role"]),
            Path(str(stored.get("collection_path", "")))
        )
        if actual != stored:
            raise AcceptanceError(
                f"parent collection identity or contents changed: {stored['role']}"
            )
        parents_after.append(actual)
    _validate_dependency_closure(
        record["scenario"],
        record["phase"],
        sealed_inputs_after,
        parents_after,
        {
            "matrix_sha256": record["matrix_sha256"],
            "candidate_revision": record["candidate_revision"],
            "game_pins": record["game_pins"],
            "repo": str(repo),
            "game_root": str(game_root),
            "user_data": str(user_data),
            "daily_user_data": str(daily_user_data),
        },
    )

    automatic_roles: dict[str, list[dict[str, object]]] = {}
    input_by_role = {str(item["role"]): item for item in sealed_inputs_after}
    for role, kind_value in normalized["artifact_roles"].items():
        kind = str(kind_value)
        records_for_role: list[dict[str, object]] = []
        if kind == "log":
            if role.endswith("error_log"):
                log_name = "error.log"
            elif role.endswith("game_log"):
                log_name = "game.log"
            else:
                raise AcceptanceError(
                    f"automatic log role does not identify error.log or game.log: {role}"
                )
            source_record = fresh_log_records.get(log_name)
            if source_record is not None:
                records_for_role.append(
                    {
                        "role": role,
                        "kind": kind,
                        "validation": {"format": "fresh-engine-log", "name": log_name},
                        **source_record,
                    }
                )
        elif kind == "settings":
            if fresh_settings_records:
                preferred = next(
                    (
                        item
                        for item in fresh_settings_records
                        if Path(str(item["source_path"])).name == "settings.txt"
                    ),
                    fresh_settings_records[0],
                )
                records_for_role.append({"role": role, "kind": kind, **preferred})
        elif kind == "external_save":
            sealed = input_by_role.get(role)
            if sealed is not None:
                sealed_path = Path(str(sealed["sealed_path"]))
                records_for_role.append(
                    _copy_role_artifact(
                        sealed_path,
                        after / "artifacts",
                        role,
                        kind,
                        dict(sealed["validation"]),
                    )
                )
        elif kind == "process_observation":
            observation_path = session / PROCESS_OBSERVATION_NAME
            records_for_role.append(
                _copy_process_observation_artifact(
                    observation_path,
                    after / "artifacts",
                    role,
                    observation,
                )
            )
        elif kind == "vfs_inventory" and "daily_vfs" in role:
            records_for_role.append({**daily_guard_record, "role": role, "kind": kind})
        elif kind == "vfs_inventory" and "isolated_vfs" in role:
            records_for_role.append(
                {**isolated_guard_record, "role": role, "kind": kind}
            )
        if records_for_role:
            automatic_roles[role] = records_for_role

    (
        role_records,
        assertion_results,
        manual_assertions_complete,
        manual_assertions_passed,
        fixture_use_results,
        appendix,
    ) = _validate_evidence_manifest(
        evidence_manifest,
        session,
        record,
        session_sha256,
        normalized,
        automatic_roles,
        fixture_records_after,
        artifacts,
    )
    runtime_oracle_evidence = _runtime_oracle_evidence_index(
        normalized, role_records
    )
    runtime_oracle_evidence_sha256 = _object_sha256(runtime_oracle_evidence)
    external_input_checks = _external_input_evidence_checks(
        normalized, record, role_records
    )
    flattened_role_artifacts = [
        item for records_for_role in role_records.values() for item in records_for_role
    ]
    artifact_checks = _artifact_requirement_checks(
        record["scenario"],
        record["phase"],
        flattened_role_artifacts,
        started_at_ns,
    )
    runtime_dlc_checks = _runtime_dlc_checks(
        record["scenario"], record["phase"], fresh_log_paths
    )

    automated_check_results = [
        {"id": "twelve_pins_stable", "matched": pins_stable},
        {
            "id": "launcher_daily_root_canonical",
            "matched": launcher_daily_matches,
        },
        {"id": "fresh_logs_clean", "matched": passed_log_scan},
        {
            "id": "snapshot_contract_stable",
            "matched": snapshot_contract_stable,
        },
        {
            "id": "isolated_configuration_stable",
            "matched": isolated_configuration_stable,
        },
        {"id": "daily_vfs_stable", "matched": daily_vfs_stable},
        {"id": "required_fixtures_stable", "matched": fixtures_stable},
        {
            "id": "artifact_minimums_met",
            "matched": all(bool(item["matched"]) for item in artifact_checks),
        },
        {
            "id": "runtime_dlc_contract_met",
            "matched": all(bool(item["matched"]) for item in runtime_dlc_checks),
        },
        {
            "id": "external_input_provenance_bound",
            "matched": all(bool(item["matched"]) for item in external_input_checks),
        },
        {
            "id": "runtime_oracle_stable",
            "matched": runtime_oracle_stable,
        },
        {
            "id": "runtime_oracle_evidence_bound",
            "matched": (
                (record["runtime_oracle"] is None and not runtime_oracle_evidence)
                or (
                    record["runtime_oracle"] is not None
                    and len(runtime_oracle_evidence) == 282
                )
            ),
        },
    ]
    automated_checks_passed = all(
        bool(item["matched"]) for item in automated_check_results
    )
    ready_for_lead_review = (
        automated_checks_passed
        and manual_assertions_complete
        and manual_assertions_passed
        and not normalized["blockers"]
    )
    if ready_for_lead_review:
        collection_status = "READY_FOR_LEAD_REVIEW"
    elif normalized["blockers"]:
        collection_status = "MATRIX_CONTRACT_BLOCKED"
    elif not automated_checks_passed:
        collection_status = "AUTOMATED_CHECK_FAILED"
    elif any(item.get("status") == "FAIL" for item in assertion_results):
        collection_status = "MANUAL_ASSERTION_FAILED"
    else:
        collection_status = "MANUAL_ASSERTION_BLOCKED"

    artifact_roles_for_collection: dict[str, object] = {}
    for role, records_for_role in role_records.items():
        artifact_roles_for_collection[role] = (
            records_for_role
            if len(records_for_role) != 1
            else records_for_role[0]
        )
    result: dict[str, object] = {
        "schema": COLLECTION_SCHEMA,
        "status": collection_status,
        "collected_at": _utc_now().isoformat(),
        "scenario_id": record["scenario"]["id"],
        "phase": record["phase"],
        "candidate_revision": record["candidate_revision"],
        "session_id": record["session_id"],
        "session_path": str(session),
        "session_sha256": session_sha256,
        "contract_sha256": record["contract_sha256"],
        "matrix_sha256": record["matrix_sha256"],
        "permission_reference": record["permission_reference"],
        "repo": str(repo),
        "game_root": str(game_root),
        "user_data": str(user_data),
        "daily_user_data": str(daily_user_data),
        "expected_argv": record["expected_argv"],
        "process_observation": observation,
        "game_pins_before": record["game_pins"],
        "game_pins_after": pin_records_after,
        "pins_stable": pins_stable,
        "launcher_daily_root_matched": launcher_daily_matches,
        "snapshots": record["snapshots"],
        "snapshot_checks": snapshot_checks,
        "snapshot_contract_stable": snapshot_contract_stable,
        "dlc_load_before": record["dlc_load"],
        "dlc_load_after": after_dlc,
        "configure_receipt": record["configure_receipt"],
        "configure_receipt_stable": receipt_stable,
        "isolated_configuration_before": record[
            "isolated_configuration_baseline"
        ],
        "isolated_configuration_after": isolated_after,
        "isolated_configuration_stable": isolated_configuration_stable,
        "daily_vfs_coverage": record["daily_vfs_coverage"],
        "daily_vfs_hash_policy": record["daily_vfs_hash_policy"],
        "daily_vfs_before": record["daily_vfs_baseline"],
        "daily_vfs_after": daily_after,
        "daily_vfs_stable": daily_vfs_stable,
        "daily_vfs_guard_artifact": daily_guard_record,
        "isolated_vfs_inventory_artifact": isolated_guard_record,
        "runtime_output_before": record["runtime_output_baseline"],
        "runtime_output_after": runtime_output_after,
        "fresh_settings_outputs": fresh_settings_records,
        "logs": copied_logs,
        "fresh_log_paths": [str(path) for path in fresh_log_paths],
        "missing_required_logs": missing_logs,
        "game_version_log_matched": game_version_matched,
        "log_blockers": blockers,
        "passed_log_scan": passed_log_scan,
        "required_fixture_records": fixture_records_after,
        "fixtures_stable": fixtures_stable,
        "fixture_uses": fixture_use_results,
        "runtime_oracle": runtime_oracle_after,
        "runtime_oracle_evidence": runtime_oracle_evidence,
        "runtime_oracle_evidence_sha256": runtime_oracle_evidence_sha256,
        "sealed_inputs": sealed_inputs_after,
        "external_input_evidence_checks": external_input_checks,
        "parents": parents_after,
        "artifact_roles": artifact_roles_for_collection,
        "appendix_artifacts": appendix,
        "artifact_requirement_checks": artifact_checks,
        "runtime_dlc_checks": runtime_dlc_checks,
        "assertions": assertion_results,
        "matrix_blockers": normalized["blockers"],
        "automated_check_results": automated_check_results,
        "automated_checks_passed": automated_checks_passed,
        "manual_assertions_complete": manual_assertions_complete,
        "manual_assertions_passed": manual_assertions_passed,
        "ready_for_lead_review": ready_for_lead_review,
        "scenario_pass_claimed": False,
        "claim_limit": (
            "A sealed collection is an immutable evidence bundle. Even READY status "
            "does not itself update the canonical ledger or claim scenario passage."
        ),
    }
    _assert_processes_stopped()
    _active_session_matches(
        user_data, session, session_sha256, str(record["active_nonce"])
    )
    wrote_collection = False
    try:
        _exclusive_write_json(collection_path, result)
        wrote_collection = True
        collection_sha256 = _sha256_file(collection_path)
        collection_seal = {
            "schema": COLLECTION_SCHEMA,
            "collection_path": str(collection_path),
            "collection_sha256": collection_sha256,
            "session_sha256": session_sha256,
            "sealed_at": _utc_now().isoformat(),
        }
        _exclusive_write_json(collection_seal_path, collection_seal)
    except Exception:
        if wrote_collection and not os.path.lexists(collection_seal_path):
            collection_path.unlink(missing_ok=True)
        raise
    _active_session_matches(
        user_data, session, session_sha256, str(record["active_nonce"])
    )
    _release_active_session(
        user_data,
        session,
        session_sha256,
        str(record["active_nonce"]),
        "collect",
    )
    return result, ready_for_lead_review


def _verified_terminal_collection(
    session: Path,
) -> tuple[dict[str, object], bool, dict[str, object], str]:
    _, session_sha256 = _verified_session_seal(session)
    record = _validate_session_record(
        _read_json_object(_session_file(session), "session record")
    )
    collection_path = session / COLLECTION_NAME
    seal_path = session / COLLECTION_SEAL_NAME
    collection = _read_json_object(collection_path, "terminal collection")
    seal = _read_json_object(seal_path, "terminal collection seal")
    required_seal = {
        "schema",
        "collection_path",
        "collection_sha256",
        "session_sha256",
        "sealed_at",
    }
    ready = collection.get("ready_for_lead_review")
    status_value = collection.get("status")
    valid_statuses = {
        "READY_FOR_LEAD_REVIEW",
        "MATRIX_CONTRACT_BLOCKED",
        "AUTOMATED_CHECK_FAILED",
        "MANUAL_ASSERTION_FAILED",
        "MANUAL_ASSERTION_BLOCKED",
    }
    if (
        set(seal) != required_seal
        or seal.get("schema") != COLLECTION_SCHEMA
        or seal.get("collection_path") != str(collection_path)
        or seal.get("collection_sha256") != _sha256_file(collection_path)
        or seal.get("session_sha256") != session_sha256
        or collection.get("schema") != COLLECTION_SCHEMA
        or collection.get("session_sha256") != session_sha256
        or collection.get("session_path") != str(session)
        or not isinstance(ready, bool)
        or status_value not in valid_statuses
        or (ready is True) != (status_value == "READY_FOR_LEAD_REVIEW")
    ):
        raise AcceptanceError("terminal collection identity/status/seal disagrees")
    _aware_datetime(seal.get("sealed_at"), "collection seal sealed_at")
    return collection, ready, record, session_sha256


def _cleanup_unsealed_collection_outputs(session: Path) -> None:
    session = _require_ordinary_directory(session, "evidence session")
    for name in (COLLECTION_SEAL_NAME, COLLECTION_NAME):
        path = session / name
        if not os.path.lexists(path):
            continue
        if not path.is_file() or _is_link_or_junction(path) or path.parent != session:
            raise AcceptanceError(f"partial collection output is not ordinary: {path}")
        path.unlink()
    after = session / "after"
    if os.path.lexists(after):
        if (
            not after.is_dir()
            or _is_link_or_junction(after)
            or after.absolute().parent != session.absolute()
            or after.resolve().parent != session.resolve()
        ):
            raise AcceptanceError(f"partial collection after tree is unsafe: {after}")
        shutil.rmtree(after)


def _validated_collection_session_identity(
    session: Path,
    *,
    require_active: bool,
) -> tuple[dict[str, object], str, Path]:
    """Authenticate the immutable safe-root session before any recovery write."""

    _, session_sha256 = _verified_session_seal(session)
    record = _validate_session_record(
        _read_json_object(_session_file(session), "session record")
    )
    user_data, _ = _require_recorded_session_location(session, record)
    if require_active:
        _active_session_matches(
            user_data,
            session,
            session_sha256,
            str(record["active_nonce"]),
        )
    return record, session_sha256, user_data


def collect(
    session: Path,
    artifacts: Sequence[Path],
    evidence_manifest: Path,
) -> tuple[dict[str, object], bool]:
    session = _require_ordinary_directory(session, "evidence session")
    pre_record, pre_session_sha256, pre_user_data = (
        _validated_collection_session_identity(session, require_active=False)
    )
    collection_exists = os.path.lexists(session / COLLECTION_NAME)
    seal_exists = os.path.lexists(session / COLLECTION_SEAL_NAME)
    if collection_exists and seal_exists:
        collection, ready, record, session_sha256 = _verified_terminal_collection(
            session
        )
        if record != pre_record or session_sha256 != pre_session_sha256:
            raise AcceptanceError("terminal collection session identity changed")
        _release_active_session(
            pre_user_data,
            session,
            session_sha256,
            str(record["active_nonce"]),
            "collect recovery",
        )
        return collection, ready
    if collection_exists or seal_exists:
        _validated_collection_session_identity(session, require_active=True)
        _cleanup_unsealed_collection_outputs(session)
    try:
        return _collect_schema4(session, artifacts, evidence_manifest)
    except Exception:
        if os.path.lexists(session / COLLECTION_NAME) and os.path.lexists(
            session / COLLECTION_SEAL_NAME
        ):
            collection, ready, record, session_sha256 = _verified_terminal_collection(
                session
            )
            if record != pre_record or session_sha256 != pre_session_sha256:
                raise AcceptanceError("recovered collection session identity changed")
            _release_active_session(
                pre_user_data,
                session,
                session_sha256,
                str(record["active_nonce"]),
                "collect recovery",
            )
            return collection, ready
        _validated_collection_session_identity(session, require_active=True)
        _cleanup_unsealed_collection_outputs(session)
        raise


_CLOSURE_KEYS = frozenset(
    {
        "schema",
        "scenario_id",
        "phase",
        "status",
        "ready_for_lead_review",
        "automated_check_results",
        "automated_checks_passed",
        "manual_assertions_complete",
        "manual_assertions_passed",
        "scenario_pass_claimed",
        "closed_at",
        "candidate_revision",
        "toolchain_revision",
        "matrix_sha256",
        "contract_identity",
        "contract_sha256",
        "repo",
        "game_root",
        "user_data",
        "daily_user_data",
        "output_root",
        "game_pins",
        "daily_configuration_final",
        "daily_vfs_final",
        "daily_vfs_final_sha256",
        "parents",
        "parent_lineage_sha256",
        "artifact_roles",
        "artifact_roles_sha256",
        "assertion_manifest",
        "assertion_manifest_sha256",
        "assertions",
        "matrix_blockers",
        "claim_limit",
        "game_session_created",
        "active_lock_created",
        "game_started",
    }
)

_CLOSURE_SEAL_KEYS = frozenset(
    {
        "schema",
        "closure_path",
        "closure_sha256",
        "parent_lineage_sha256",
        "artifact_roles_sha256",
        "assertion_manifest_sha256",
        "matrix_sha256",
        "candidate_revision",
        "toolchain_revision",
        "sealed_at",
    }
)

_CLOSURE_ARTIFACT_RECORD_KEYS = frozenset(
    {
        "role",
        "kind",
        "source_path",
        "validation",
        "path",
        "bytes",
        "mtime_ns",
        "sha256",
        "supports_assertion_ids",
        "distinct",
    }
)

_CLOSURE_ASSERTION_RECORD_KEYS = frozenset(
    {"source_path", "validation", "path", "bytes", "mtime_ns", "sha256"}
)


def _closure_contract_identity(scenario: dict[str, object]) -> dict[str, object]:
    contract = scenario.get("closure_contract")
    if not isinstance(contract, dict):
        raise AcceptanceError("R13 has no closure contract")
    return {
        "scenario_id": "R13",
        "phase": "closure",
        "scenario": scenario,
        "closure_contract": contract,
    }


def _closure_output_root(user_data: Path, value: Path | None) -> Path:
    candidate = value or Path("jxp_release_closure")
    candidate = candidate.expanduser()
    if not candidate.is_absolute():
        candidate = user_data / candidate
    absolute = Path(os.path.abspath(str(candidate)))
    if (
        absolute.parent != user_data
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", absolute.name)
    ):
        raise AcceptanceError(
            "closure output root must be one ordinary direct child of the "
            "canonical acceptance root"
        )
    if os.path.lexists(absolute):
        if (
            not absolute.is_dir()
            or _is_link_or_junction(absolute)
            or absolute.resolve() != absolute
        ):
            raise AcceptanceError(
                f"closure output root must be an ordinary canonical directory: {absolute}"
            )
    return absolute


def _closure_source_file(
    path: Path, label: str, max_bytes: int = 32 * 1024 * 1024
) -> Path:
    raw = path.expanduser()
    absolute = Path(os.path.abspath(str(raw)))
    resolved = absolute.resolve()
    if (
        absolute != resolved
        or not resolved.is_file()
        or _is_link_or_junction(absolute)
        or resolved.stat().st_nlink != 1
        or resolved.stat().st_size <= 0
        or resolved.stat().st_size > max_bytes
    ):
        raise AcceptanceError(f"{label} must be one ordinary canonical file: {path}")
    cursor = absolute
    while cursor != cursor.parent:
        if _is_link_or_junction(cursor):
            raise AcceptanceError(f"{label} traverses a link or junction: {cursor}")
        cursor = cursor.parent
    return resolved


_R13_GATE_CHECK_IDS = {
    "r13_main_static_gate_output": (
        "main_validator",
        "main_checks",
        "core_unit_tests",
    ),
    "r13_combined_static_gate_output": (
        "map_validator",
        "history_validator",
        "content_validator",
        "compatibility_validator",
        "asset_validator",
        "runtime_oracle_check",
        "main_validator",
    ),
    "r13_mandate_vanilla_manifest_output": (
        "vanilla_manifest_hash",
        "mandate_cb",
        "mandate_wargoal",
        "mandate_reforms",
        "chinese_empire_events",
    ),
    "r13_ideas_shape_and_mutation_output": (
        "idea_shape",
        "idea_mutation_suite",
    ),
    "r13_ledger_validation_output": (
        "ledger_schema",
        "ledger_index",
        "ledger_tests",
    ),
    "r13_skill_validation_output_if_changed": (
        "repo_skill_validation",
        "installed_skill_validation",
        "skill_mirror_hash",
    ),
}

_R13_GATE_TIMEOUT_SECONDS = 900
_R13_GATE_MAX_TRANSCRIPT_BYTES = 1 * 1024 * 1024
_R13_GATE_MAX_TOTAL_TRANSCRIPT_BYTES = 4 * 1024 * 1024
_R13_CLOSURE_MAX_INPUT_BYTES = 8 * 1024 * 1024
_R13_CLOSURE_MAX_BYTES = 32 * 1024 * 1024
_R13_TRUSTED_GIT = Path(r"F:\Git\mingw64\bin\git.exe")
_R13_TRUSTED_GIT_SHA256 = (
    "d117eb75c7541372ed43a8e6bbb70230a846daff47946107a87e7c52b4c6581d"
)
_R13_GIT_TOOLCHAIN_PATHS = (
    "japan_expanded_v2/tools",
    "japan_expanded_v2/AGENTS.md",
    "japan_expanded_v2_map/tools",
    "japan_expanded_v2_map/AGENTS.md",
    "skills/eu4-modding",
    "japan_expanded_v2/dev_logs",
    "japan_expanded_v2_map/dev_logs",
    "japan_expanded_v2.mod",
    "japan_expanded_v2_map.mod",
    ".gitattributes",
)


@lru_cache(maxsize=1)
def _windows_system_paths() -> dict[str, Path]:
    """Resolve Windows and System32 through WinAPI, never caller environment."""

    if os.name != "nt":
        windows = Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve()
        system = windows / "System32"
    else:
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            def directory(function_name: str) -> Path:
                function = getattr(kernel32, function_name)
                function.argtypes = (ctypes.c_wchar_p, ctypes.c_uint)
                function.restype = ctypes.c_uint
                buffer = ctypes.create_unicode_buffer(32768)
                length = function(buffer, len(buffer))
                if length == 0 or length >= len(buffer):
                    raise OSError(
                        f"{function_name} failed with Win32 error "
                        f"{ctypes.get_last_error()}"
                    )
                return Path(buffer.value)

            windows = directory("GetWindowsDirectoryW")
            system = directory("GetSystemDirectoryW")
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise AcceptanceError(
                f"cannot resolve trusted Windows system directories: {exc}"
            ) from exc
    windows = _require_ordinary_directory(windows, "Windows directory")
    system = _require_ordinary_directory(system, "Windows system directory")
    powershell_directory = _require_ordinary_directory(
        system / "WindowsPowerShell" / "v1.0", "Windows PowerShell directory"
    )
    return {
        "windows": windows,
        "system": system,
        "powershell": powershell_directory / "powershell.exe",
        "cmd": system / "cmd.exe",
        "powershell_modules": powershell_directory / "Modules",
    }


def _r13_toolchain_file_record(
    path: Path, label: str, *, allow_empty: bool = False
) -> dict[str, object]:
    absolute = Path(os.path.abspath(str(path.expanduser())))
    resolved = absolute.resolve()
    if absolute != resolved or not resolved.is_file() or _is_link_or_junction(absolute):
        raise AcceptanceError(f"{label} must be an ordinary canonical file: {path}")
    cursor = absolute
    while cursor != cursor.parent:
        if _is_link_or_junction(cursor):
            raise AcceptanceError(f"{label} traverses a link or junction: {cursor}")
        cursor = cursor.parent
    before = resolved.stat()
    if before.st_size < 0 or before.st_size == 0 and not allow_empty:
        raise AcceptanceError(f"{label} is empty: {resolved}")
    digest = _sha256_file(resolved)
    after = resolved.stat()
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
    ):
        raise AcceptanceError(f"{label} changed while it was hashed: {resolved}")
    return {
        "kind": "file",
        "path": str(resolved),
        "bytes": after.st_size,
        "sha256": digest,
    }


def _r13_toolchain_tree_record(root: Path, label: str) -> dict[str, object]:
    root = _require_ordinary_directory(root, label)
    records: list[dict[str, object]] = []
    total_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if _is_link_or_junction(path):
            raise AcceptanceError(f"{label} contains a link or junction: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise AcceptanceError(f"{label} contains a non-ordinary entry: {path}")
        before = path.stat()
        digest = _sha256_file(path)
        after = path.stat()
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ino != after.st_ino
        ):
            raise AcceptanceError(f"{label} changed while it was hashed: {path}")
        total_bytes += after.st_size
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": after.st_size,
                "sha256": digest,
            }
        )
    if not records:
        raise AcceptanceError(f"{label} contains no files")
    return {
        "kind": "tree",
        "path": str(root),
        "file_count": len(records),
        "bytes": total_bytes,
        "sha256": _object_sha256(records),
    }


def _r13_git_blob_hashes(path: Path, label: str) -> tuple[int, str, str]:
    before = path.stat()
    if not path.is_file() or _is_link_or_junction(path) or before.st_nlink != 1:
        raise AcceptanceError(f"{label} contains a non-ordinary file: {path}")
    git_digest = sha1()
    content_digest = sha256()
    git_digest.update(f"blob {before.st_size}\0".encode("ascii"))
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if any(
            getattr(opened, key) != getattr(before, key)
            for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        ):
            raise AcceptanceError(f"{label} changed before hashing: {path}")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            git_digest.update(chunk)
            content_digest.update(chunk)
        opened_after = os.fstat(stream.fileno())
    after = path.stat()
    if any(
        getattr(opened_after, key) != getattr(opened, key)
        or getattr(after, key) != getattr(before, key)
        for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    ):
        raise AcceptanceError(f"{label} changed while hashing: {path}")
    return after.st_size, git_digest.hexdigest(), content_digest.hexdigest()


def _r13_git_expected_manifest(
    repo: Path, relative: str, label: str
) -> tuple[str, list[dict[str, object]]]:
    revision = _git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise AcceptanceError("R13 toolchain Git HEAD is not a SHA-1 commit")
    if _git(repo, "rev-parse", "--show-object-format") != "sha1":
        raise AcceptanceError("R13 toolchain requires a SHA-1 Git object store")
    raw = _git_bytes(
        repo,
        "ls-tree",
        "-r",
        "-l",
        "-z",
        "--full-tree",
        revision,
        "--",
        relative,
    )
    records: list[dict[str, object]] = []
    pattern = re.compile(
        rb"^(?P<mode>[0-9]{6}) (?P<kind>[^ ]+) (?P<oid>[0-9a-f]{40}) +"
        rb"(?P<size>[0-9]+)\t(?P<path>.+)$"
    )
    for raw_entry in raw.split(b"\0"):
        if not raw_entry:
            continue
        match = pattern.fullmatch(raw_entry)
        if (
            match is None
            or match.group("kind") != b"blob"
            or match.group("mode") not in {b"100644", b"100755"}
        ):
            raise AcceptanceError(f"{label} has an unsupported Git tree entry")
        try:
            path_text = match.group("path").decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise AcceptanceError(f"{label} has a non-UTF-8 Git path") from exc
        if "\\" in path_text or PurePosixPath(path_text).is_absolute():
            raise AcceptanceError(f"{label} has an unsafe Git path: {path_text}")
        records.append(
            {
                "path": path_text,
                "mode": match.group("mode").decode("ascii"),
                "bytes": int(match.group("size")),
                "git_blob": match.group("oid").decode("ascii"),
            }
        )
    if not records:
        raise AcceptanceError(f"{label} has no Git-tracked files: {relative}")
    records.sort(key=lambda item: str(item["path"]))
    if len({str(item["path"]).casefold() for item in records}) != len(records):
        raise AcceptanceError(f"{label} has case-colliding Git paths")
    batch_input = "".join(f"{item['git_blob']}\n" for item in records).encode("ascii")
    batch = _git_bytes(repo, "cat-file", "--batch", input_bytes=batch_input)
    cursor = 0
    for item in records:
        header_end = batch.find(b"\n", cursor)
        if header_end < 0:
            raise AcceptanceError(f"{label} Git blob batch is truncated")
        header = batch[cursor:header_end].split()
        if (
            len(header) != 3
            or header[0].decode("ascii", errors="strict") != item["git_blob"]
            or header[1] != b"blob"
            or not header[2].isdigit()
        ):
            raise AcceptanceError(f"{label} Git blob batch header disagrees")
        size = int(header[2])
        start = header_end + 1
        end = start + size
        if end >= len(batch) or batch[end : end + 1] != b"\n":
            raise AcceptanceError(f"{label} Git blob batch body is truncated")
        content = batch[start:end]
        if size != item["bytes"]:
            raise AcceptanceError(f"{label} Git blob size disagrees")
        item["sha256"] = sha256(content).hexdigest()
        cursor = end + 1
    if cursor != len(batch):
        raise AcceptanceError(f"{label} Git blob batch has trailing data")
    return revision, records


def _r13_git_tree_record(
    repo: Path, relative: str, label: str
) -> dict[str, object]:
    """Require a live subtree/file to be byte-exact to the complete HEAD tree."""

    relative_path = PurePosixPath(relative)
    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or not relative_path.parts
    ):
        raise AcceptanceError(f"{label} Git path is unsafe: {relative}")
    target = repo.joinpath(*relative_path.parts)
    if target.is_dir():
        target = _require_ordinary_directory(target, label)
        live_paths: list[Path] = []
        stack = [target]
        while stack:
            directory = stack.pop()
            for path in directory.iterdir():
                if _is_link_or_junction(path):
                    raise AcceptanceError(
                        f"{label} contains a link or junction: {path}"
                    )
                if path.is_dir():
                    stack.append(path)
                elif path.is_file():
                    live_paths.append(path)
                else:
                    raise AcceptanceError(
                        f"{label} contains a non-ordinary entry: {path}"
                    )
    elif target.is_file() and not _is_link_or_junction(target):
        live_paths = [target]
    else:
        raise AcceptanceError(f"{label} is missing: {target}")

    revision, expected = _r13_git_expected_manifest(repo, relative, label)
    expected_core = [
        {
            "path": item["path"],
            "bytes": item["bytes"],
            "git_blob": item["git_blob"],
            "sha256": item["sha256"],
        }
        for item in expected
    ]
    live: list[dict[str, object]] = []
    for path in live_paths:
        size, blob, digest = _r13_git_blob_hashes(path, label)
        live.append(
            {
                "path": path.relative_to(repo).as_posix(),
                "bytes": size,
                "git_blob": blob,
                "sha256": digest,
            }
        )
    live.sort(key=lambda item: str(item["path"]))
    if not _json_exact_equal(live, expected_core):
        raise AcceptanceError(
            f"{label} differs from Git HEAD or contains untracked/ignored files"
        )
    return {
        "kind": "git_tree",
        "path": str(target),
        "git_path": relative,
        "revision": revision,
        "file_count": len(expected),
        "bytes": sum(int(item["bytes"]) for item in expected),
        "sha256": _object_sha256(expected),
    }


def _r13_python_dependency_sites() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    """Resolve required packages only from fixed interpreter/profile locations."""

    profile = _require_ordinary_directory(_known_profile_root(), "Windows profile")
    candidates = (
        Path(sys.prefix).resolve() / "Lib" / "site-packages",
        profile
        / "AppData"
        / "Roaming"
        / "Python"
        / f"Python{sys.version_info.major}{sys.version_info.minor}"
        / "site-packages",
    )
    required = (
        ("numpy", "numpy"),
        ("pillow", "PIL"),
        ("pyyaml", "yaml"),
    )
    distributions: dict[str, tuple[Path, importlib.metadata.Distribution]] = {}
    ordinary_candidates: list[Path] = []
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        site = _require_ordinary_directory(candidate, "R13 Python package site")
        ordinary_candidates.append(site)
        for distribution in importlib.metadata.distributions(path=[str(site)]):
            name = str(distribution.metadata.get("Name", "")).casefold()
            distributions.setdefault(name, (site, distribution))
    records: list[dict[str, str]] = []
    used_sites: list[Path] = []
    for distribution_name, package_name in required:
        selected = distributions.get(distribution_name)
        if selected is None:
            raise AcceptanceError(
                f"R13 gate dependency is unavailable: {distribution_name}"
            )
        site, distribution = selected
        package_root = (site / package_name).resolve()
        if (
            not package_root.is_dir()
            or not _is_relative_to(package_root, site)
            or _is_link_or_junction(package_root)
        ):
            raise AcceptanceError(
                f"R13 gate dependency entry path is unsafe: {package_root}"
            )
        if site not in used_sites:
            used_sites.append(site)
        records.append(
            {
                "distribution": str(distribution.metadata["Name"]),
                "version": distribution.version,
                "site": str(site),
                "entry_path": str(package_root),
            }
        )
    ordered_sites = tuple(
        site for site in ordinary_candidates if site in set(used_sites)
    )
    return ordered_sites, records


def _r13_python_distribution_manifest(
    site: Path, distribution_name: str
) -> tuple[importlib.metadata.Distribution, list[dict[str, object]]]:
    selected = None
    for distribution in importlib.metadata.distributions(path=[str(site)]):
        if str(distribution.metadata.get("Name", "")).casefold() == distribution_name.casefold():
            selected = distribution
            break
    if selected is None or selected.files is None:
        raise AcceptanceError(
            f"R13 Python distribution manifest is unavailable: {distribution_name}"
        )
    records: list[dict[str, object]] = []
    scripts = (site.parent / "Scripts").resolve()
    for relative in sorted(selected.files, key=lambda item: str(item).casefold()):
        path = Path(selected.locate_file(relative)).resolve()
        if path.is_file() and _is_relative_to(path, scripts):
            # Console entry points are not part of the isolated import site.
            continue
        if not path.is_file() or not _is_relative_to(path, site):
            raise AcceptanceError(
                f"R13 Python distribution contains an unsafe file: {path}"
            )
        file_record = _r13_toolchain_file_record(
            path,
            f"R13 {distribution_name} distribution file",
            allow_empty=True,
        )
        records.append(
            {
                "path": path.relative_to(site).as_posix(),
                "bytes": file_record["bytes"],
                "sha256": file_record["sha256"],
            }
        )
    records.sort(key=lambda item: str(item["path"]))
    if not records or len({str(item["path"]) for item in records}) != len(records):
        raise AcceptanceError(f"R13 Python distribution is empty: {distribution_name}")
    return selected, records


def _r13_python_distribution_record(
    site: Path, distribution_name: str
) -> dict[str, object]:
    selected, records = _r13_python_distribution_manifest(site, distribution_name)
    return {
        "kind": "distribution",
        "path": f"{site}::{distribution_name}",
        "distribution": str(selected.metadata["Name"]),
        "version": selected.version,
        "file_count": len(records),
        "bytes": sum(int(item["bytes"]) for item in records),
        "sha256": _object_sha256(records),
    }


def _r13_plain_tree_manifest(root: Path, label: str) -> list[dict[str, object]]:
    root = _require_ordinary_directory(root, label)
    records: list[dict[str, object]] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        for path in directory.iterdir():
            if _is_link_or_junction(path):
                raise AcceptanceError(f"{label} contains a link or junction: {path}")
            if path.is_dir():
                stack.append(path)
                continue
            if not path.is_file() or path.stat().st_nlink != 1:
                raise AcceptanceError(f"{label} contains a non-ordinary file: {path}")
            record = _r13_toolchain_file_record(path, label, allow_empty=True)
            records.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": record["bytes"],
                    "sha256": record["sha256"],
                }
            )
    records.sort(key=lambda item: str(item["path"]))
    return records


def _r13_gate_runtime_paths(context: dict[str, object]) -> dict[str, Path]:
    temporary = Path(str(context["user_data"])).resolve() / ".jxp_r13_gate_temp"
    return {
        "root": temporary,
        "dependency_site": temporary / "python_packages",
        "pycache": temporary / "pycache",
        "python_wrapper": temporary / "r13-python.ps1",
    }


def _r13_expected_isolated_dependency_manifest(
    dependencies: Sequence[dict[str, str]],
) -> list[dict[str, object]]:
    expected: list[dict[str, object]] = []
    seen: set[str] = set()
    for dependency in dependencies:
        _selected, manifest = _r13_python_distribution_manifest(
            Path(dependency["site"]), dependency["distribution"]
        )
        for record in manifest:
            key = str(record["path"]).casefold()
            if key in seen:
                raise AcceptanceError(
                    f"R13 dependency files collide: {record['path']}"
                )
            seen.add(key)
            expected.append(record)
    expected.sort(key=lambda item: str(item["path"]))
    return expected


def _r13_python_wrapper_payload(context: dict[str, object]) -> bytes:
    paths = _r13_gate_runtime_paths(context)
    python = Path(sys.executable).resolve()
    runner = Path(__file__).with_name("r13_python_runner.py").resolve()
    return (
        "$ErrorActionPreference = 'Stop'\r\n"
        f"& '{python}' -I -S -B -X 'pycache_prefix={paths['pycache']}' "
        f"'{runner}' @args\r\n"
    ).encode("utf-8")


def _r13_prepare_gate_python_runtime(context: dict[str, object]) -> None:
    paths = _r13_gate_runtime_paths(context)
    root = _require_ordinary_directory(paths["root"], "R13 gate temp root")
    for key in ("dependency_site", "pycache"):
        path = paths[key]
        if os.path.lexists(path):
            raise AcceptanceError(f"R13 gate Python path already exists: {path}")
        path.mkdir()
        if _require_ordinary_directory(path, f"R13 gate Python {key}").parent != root:
            raise AcceptanceError(f"R13 gate Python {key} escaped the temp root")

    dependency_site = paths["dependency_site"]
    source_sites, dependencies = _r13_python_dependency_sites()
    selected_sites = {str(item["distribution"]): Path(item["site"]) for item in dependencies}
    expected: list[dict[str, object]] = []
    seen: set[str] = set()
    for dependency in dependencies:
        name = str(dependency["distribution"])
        site = selected_sites[name]
        _selected, manifest = _r13_python_distribution_manifest(site, name)
        for record in manifest:
            relative = PurePosixPath(str(record["path"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise AcceptanceError(f"R13 dependency path is unsafe: {relative}")
            key = relative.as_posix().casefold()
            if key in seen:
                raise AcceptanceError(f"R13 dependency files collide: {relative}")
            seen.add(key)
            source = site.joinpath(*relative.parts)
            destination_parent = dependency_site.joinpath(*relative.parts[:-1])
            copied = _copy_artifact(source, destination_parent)
            if (
                Path(str(copied["path"])).name != relative.name
                or not _json_exact_equal(copied["bytes"], record["bytes"])
                or copied["sha256"] != record["sha256"]
            ):
                raise AcceptanceError(f"R13 isolated dependency copy changed: {relative}")
            expected.append(record)
    if not source_sites or not _json_exact_equal(
        _r13_plain_tree_manifest(dependency_site, "R13 isolated dependency site"),
        sorted(expected, key=lambda item: str(item["path"])),
    ):
        raise AcceptanceError("R13 isolated dependency site disagrees with distributions")

    wrapper = paths["python_wrapper"]
    payload = _r13_python_wrapper_payload(context)
    descriptor = os.open(wrapper, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if _sha256_file(wrapper) != sha256(payload).hexdigest():
        raise AcceptanceError("R13 Python wrapper changed while it was created")


def _r13_filtered_tree_record(
    root: Path,
    label: str,
    *,
    excluded_top_level: frozenset[str] = frozenset(),
    exclude_bytecode: bool = False,
    require_single_link: bool = True,
) -> dict[str, object]:
    root = _require_ordinary_directory(root, label)
    records: list[dict[str, object]] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        for path in directory.iterdir():
            relative = path.relative_to(root)
            if _is_link_or_junction(path):
                raise AcceptanceError(f"{label} contains a link or junction: {path}")
            if relative.parts[0].casefold() in excluded_top_level:
                continue
            if exclude_bytecode and (
                "__pycache__" in {part.casefold() for part in relative.parts}
                or path.suffix.casefold() in {".pyc", ".pyo"}
            ):
                continue
            if path.is_dir():
                stack.append(path)
                continue
            if (
                not path.is_file()
                or require_single_link
                and path.stat().st_nlink != 1
            ):
                raise AcceptanceError(f"{label} contains a non-ordinary file: {path}")
            record = _r13_toolchain_file_record(path, label, allow_empty=True)
            records.append(
                {
                    "path": relative.as_posix(),
                    "bytes": record["bytes"],
                    "sha256": record["sha256"],
                }
            )
    records.sort(key=lambda item: str(item["path"]))
    if not records:
        raise AcceptanceError(f"{label} contains no approved files")
    return {
        "kind": "tree",
        "path": str(root),
        "file_count": len(records),
        "bytes": sum(int(item["bytes"]) for item in records),
        "sha256": _object_sha256(records),
    }


def _r13_external_platform_record() -> dict[str, object]:
    return {
        "os_name": os.name,
        "machine": platform.machine(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "cache_tag": sys.implementation.cache_tag,
        "pointer_bits": struct.calcsize("P") * 8,
        "base_prefix": str(Path(sys.base_prefix).resolve()),
    }


def _r13_external_toolchain_records(
    context: dict[str, object], dependencies: Sequence[dict[str, str]]
) -> list[dict[str, object]]:
    system_paths = _windows_system_paths()
    profile = _require_ordinary_directory(_known_profile_root(), "Windows profile")
    codex_home = _require_ordinary_directory(profile / ".codex", "Codex home")
    python_root = _require_ordinary_directory(
        Path(sys.base_prefix), "R13 Python base prefix"
    )
    records: list[dict[str, object]] = [
        _r13_filtered_tree_record(
            python_root,
            "R13 Python base runtime",
            excluded_top_level=frozenset({"lib", "dlls", "scripts"}),
            exclude_bytecode=True,
        ),
        _r13_filtered_tree_record(
            python_root / "Lib",
            "R13 Python standard library",
            excluded_top_level=frozenset({"site-packages"}),
            exclude_bytecode=True,
        ),
        _r13_filtered_tree_record(
            python_root / "DLLs", "R13 Python extension library", exclude_bytecode=True
        ),
        _r13_toolchain_file_record(
            _trusted_git_path(), "R13 trusted Git executable"
        ),
        _r13_toolchain_file_record(
            Path(system_paths["powershell"]), "R13 Windows PowerShell"
        ),
        _r13_toolchain_file_record(Path(system_paths["cmd"]), "R13 command processor"),
        _r13_filtered_tree_record(
            Path(system_paths["powershell_modules"]),
            "R13 Windows PowerShell modules",
            require_single_link=False,
        ),
        _r13_toolchain_file_record(
            codex_home
            / "skills"
            / ".system"
            / "skill-creator"
            / "scripts"
            / "quick_validate.py",
            "R13 skill quick validator",
        ),
    ]
    zip_path = python_root / f"python{sys.version_info.major}{sys.version_info.minor}.zip"
    if os.path.lexists(zip_path):
        raise AcceptanceError(f"R13 unapproved Python zip import root exists: {zip_path}")
    records.append({"kind": "absent", "path": str(zip_path)})
    records.extend(
        _r13_python_distribution_record(
            Path(dependency["site"]), dependency["distribution"]
        )
        for dependency in dependencies
    )
    records.sort(key=lambda item: str(item["path"]).casefold())
    return records


def _r13_external_toolchain_baseline(
    context: dict[str, object], dependencies: Sequence[dict[str, str]]
) -> dict[str, object]:
    baseline_path = Path(__file__).with_name(
        "r13_external_toolchain_baseline.json"
    ).resolve()
    baseline = _read_json_object(baseline_path, "R13 external toolchain baseline")
    if set(baseline) != {"schema", "platform", "records"} or baseline.get(
        "schema"
    ) != "jxp_r13_external_toolchain_baseline/v1":
        raise AcceptanceError("R13 external toolchain baseline schema disagrees")
    platform_record = _r13_external_platform_record()
    records = _r13_external_toolchain_records(context, dependencies)
    if (
        not _json_exact_equal(baseline.get("platform"), platform_record)
        or not _json_exact_equal(baseline.get("records"), records)
    ):
        raise AcceptanceError("R13 external toolchain differs from approved baseline")
    return {
        "path": str(baseline_path),
        "platform": platform_record,
        "record_count": len(records),
        "records_sha256": _object_sha256(records),
        "baseline_sha256": _sha256_file(baseline_path),
    }


def _r13_gate_toolchain_guard(context: dict[str, object]) -> dict[str, object]:
    """Bind repository inputs to HEAD and external inputs to a reviewed baseline."""

    repo = _require_ordinary_directory(Path(str(context["repo"])), "R13 repository")
    toolchain_revision = context.get("toolchain_revision")
    if (
        not isinstance(toolchain_revision, str)
        or not re.fullmatch(r"[0-9a-f]{40}", toolchain_revision)
        or _r13_current_toolchain_revision(repo) != toolchain_revision
    ):
        raise AcceptanceError("R13 toolchain revision is stale or invalid")
    profile = _require_ordinary_directory(_known_profile_root(), "Windows profile")
    codex_home = _require_ordinary_directory(profile / ".codex", "Codex home")
    git_records = [
        _r13_git_tree_record(repo, relative, f"R13 Git toolchain {relative}")
        for relative in _R13_GIT_TOOLCHAIN_PATHS
    ]
    if any(item["revision"] != toolchain_revision for item in git_records):
        raise AcceptanceError("R13 Git toolchain revision changed during inspection")

    _dependency_sites, dependencies = _r13_python_dependency_sites()
    external = _r13_external_toolchain_baseline(context, dependencies)
    runtime_paths = _r13_gate_runtime_paths(context)
    isolated_manifest = _r13_plain_tree_manifest(
        runtime_paths["dependency_site"], "R13 isolated dependency site"
    )
    expected_isolated = _r13_expected_isolated_dependency_manifest(dependencies)
    if not _json_exact_equal(isolated_manifest, expected_isolated):
        raise AcceptanceError(
            "R13 isolated dependency site differs from approved distributions"
        )
    pycache_root = _require_ordinary_directory(
        runtime_paths["pycache"], "R13 isolated pycache root"
    )
    if any(pycache_root.iterdir()):
        raise AcceptanceError("R13 isolated pycache root must remain empty")
    wrapper = _r13_toolchain_file_record(
        runtime_paths["python_wrapper"], "R13 isolated Python wrapper"
    )
    expected_wrapper = _r13_python_wrapper_payload(context)
    if (
        wrapper["bytes"] != len(expected_wrapper)
        or wrapper["sha256"] != sha256(expected_wrapper).hexdigest()
    ):
        raise AcceptanceError("R13 isolated Python wrapper differs from policy")
    repo_skill = _r13_plain_tree_manifest(
        repo / "skills" / "eu4-modding", "repository EU4 skill"
    )
    installed_skill_root = codex_home / "skills" / "eu4-modding"
    installed_skill = _r13_plain_tree_manifest(
        installed_skill_root, "installed EU4 skill"
    )
    if not _json_exact_equal(repo_skill, installed_skill):
        raise AcceptanceError(
            "installed EU4 skill differs from the Git-verified repository skill"
        )
    skill_git = next(
        item for item in git_records if item["git_path"] == "skills/eu4-modding"
    )
    body = {
        "schema": "jxp_r13_gate_toolchain/v2",
        "toolchain_revision": toolchain_revision,
        "git_head": {
            "paths": list(_R13_GIT_TOOLCHAIN_PATHS),
            "file_count": sum(int(item["file_count"]) for item in git_records),
            "bytes": sum(int(item["bytes"]) for item in git_records),
            "records_sha256": _object_sha256(git_records),
        },
        "external_baseline": external,
        "dependencies": dependencies,
        "isolated_dependency_site": {
            "path": str(runtime_paths["dependency_site"]),
            "file_count": len(isolated_manifest),
            "bytes": sum(int(item["bytes"]) for item in isolated_manifest),
            "sha256": _object_sha256(isolated_manifest),
        },
        "python_wrapper": wrapper,
        "python_import_policy": {
            "isolated": True,
            "no_site": True,
            "safe_path": True,
            "dont_write_bytecode": True,
            "stdlib_before_repo_and_dependencies": True,
            "skill_scripts_are_not_import_roots": True,
            "allowed_skill_script": (
                "skills/eu4-modding/scripts/check_mission_series_overlap.py"
            ),
        },
        "installed_skill": {
            "path": str(installed_skill_root.resolve()),
            "source_revision": toolchain_revision,
            "git_tree_sha256": skill_git["sha256"],
            "file_count": len(installed_skill),
            "bytes": sum(int(item["bytes"]) for item in installed_skill),
            "sha256": _object_sha256(installed_skill),
        },
    }
    return {**body, "toolchain_sha256": _object_sha256(body)}


def _r13_current_toolchain_revision(repo: Path) -> str:
    revision = _git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise AcceptanceError("R13 toolchain Git HEAD is not a full commit id")
    return revision


def _r13_gate_environment(
    context: dict[str, object], _python_path: str
) -> dict[str, str]:
    system_paths = _windows_system_paths()
    windows = system_paths["windows"]
    system = system_paths["system"]
    powershell = Path(system_paths["powershell"])
    cmd = Path(system_paths["cmd"])
    for path, label in ((powershell, "PowerShell"), (cmd, "command processor")):
        _r13_toolchain_file_record(path, f"trusted Windows {label}")
    modules = _require_ordinary_directory(
        system_paths["powershell_modules"], "Windows PowerShell modules"
    )
    repo = Path(str(context["repo"])).resolve()
    runtime_paths = _r13_gate_runtime_paths(context)
    gate_temp = runtime_paths["root"]
    profile = _require_ordinary_directory(_known_profile_root(), "Windows profile")
    quick_validate = (
        profile
        / ".codex"
        / "skills"
        / ".system"
        / "skill-creator"
        / "scripts"
        / "quick_validate.py"
    ).resolve()
    return {
        "SystemRoot": str(windows),
        "WINDIR": str(windows),
        "SYSTEMDRIVE": windows.drive,
        "COMSPEC": str(cmd),
        "PATH": os.pathsep.join((str(powershell.parent), str(system))),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "PSModulePath": str(modules),
        "TEMP": str(gate_temp),
        "TMP": str(gate_temp),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "PYTHONPYCACHEPREFIX": str(runtime_paths["pycache"]),
        "JXP_R13_MAIN_TOOLS": str(repo / "japan_expanded_v2" / "tools"),
        "JXP_R13_MAP_TOOLS": str(repo / "japan_expanded_v2_map" / "tools"),
        "JXP_R13_DEPENDENCY_SITE": str(runtime_paths["dependency_site"]),
        "JXP_R13_PYCACHE_ROOT": str(runtime_paths["pycache"]),
        "JXP_R13_QUICK_VALIDATE": str(quick_validate),
        "JXP_R13_MISSION_OVERLAP_SCRIPT": str(
            repo
            / "skills"
            / "eu4-modding"
            / "scripts"
            / "check_mission_series_overlap.py"
        ),
    }


def _r13_gate_receipt_summary(role: str) -> str:
    checks = _R13_GATE_CHECK_IDS.get(role)
    if checks is None:
        raise AcceptanceError(f"unknown R13 static gate role: {role}")
    return "PASS: close-release live verification: " + ", ".join(checks)


def _r13_static_gate_specs(
    context: dict[str, object],
) -> dict[str, dict[str, object]]:
    """Return the only commands allowed to satisfy the six R13 gate roles."""

    repo = Path(str(context["repo"])).resolve()
    game_root = Path(str(context["game_root"])).resolve()
    main_mod = repo / "japan_expanded_v2"
    map_mod = repo / "japan_expanded_v2_map"
    tests = main_mod / "tools" / "jxp_validation" / "tests"
    python = str(Path(sys.executable).resolve())
    runtime_paths = _r13_gate_runtime_paths(context)
    python_wrapper = str(runtime_paths["python_wrapper"])
    runner = str(Path(__file__).with_name("r13_python_runner.py").resolve())
    python_prefix = [
        python,
        "-I",
        "-S",
        "-B",
        "-X",
        f"pycache_prefix={runtime_paths['pycache']}",
        runner,
    ]
    powershell = str(_windows_system_paths()["powershell"])
    main_command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo / "skills" / "eu4-modding" / "scripts" / "validate_jxp_mod.ps1"),
        "-ModPath",
        str(main_mod),
        "-GameRoot",
        str(game_root),
        "-PythonPath",
        python_wrapper,
    ]
    combined_command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(map_mod / "tools" / "validate_all.ps1"),
        "-GameRoot",
        str(game_root),
        "-MainMod",
        str(main_mod),
        "-PythonPath",
        python_wrapper,
        "-PowerShellPath",
        powershell,
    ]
    base_environment = _r13_gate_environment(context, "")
    test_environment = _r13_gate_environment(context, str(main_mod / "tools"))
    codex_home = (_known_profile_root() / ".codex").resolve()
    quick_validate = (
        codex_home
        / "skills"
        / ".system"
        / "skill-creator"
        / "scripts"
        / "quick_validate.py"
    ).resolve()
    repo_skill = (repo / "skills" / "eu4-modding").resolve()
    installed_skill = (codex_home / "skills" / "eu4-modding").resolve()
    return {
        "r13_main_static_gate_output": {
            "commands": [main_command],
            "cwd": str(repo),
            "environment": base_environment,
            "required_markers": [[
                "PASS: all 26 checks passed.",
                "Ran 221 tests",
                "OK: JXP general, release, topology, asset, and unit validation passed.",
            ]],
        },
        "r13_combined_static_gate_output": {
            "commands": [combined_command],
            "cwd": str(repo),
            "environment": base_environment,
            "required_markers": [[
                "PASS: companion and dependency static validation completed.",
                "No EU4 process was started; runtime acceptance remains a separate approved step.",
            ]],
        },
        "r13_mandate_vanilla_manifest_output": {
            "commands": [[
                *python_prefix,
                "-m",
                "unittest",
                "-v",
                "jxp_validation.tests.test_mandate",
            ]],
            "cwd": str(main_mod),
            "environment": test_environment,
            "required_markers": [[
                "test_live_mandate_contract_is_closed",
                "test_rejects_vanilla_cb_without_shogunate_exclusion",
                "test_rejects_vanilla_wargoal_without_take_mandate",
                "Ran 11 tests",
                "OK",
            ]],
        },
        "r13_ideas_shape_and_mutation_output": {
            "commands": [[
                *python_prefix,
                "-m",
                "unittest",
                "-v",
                "jxp_validation.tests.test_ideas",
                "jxp_validation.tests.test_daimyo_coverage",
            ]],
            "cwd": str(main_mod),
            "environment": test_environment,
            "required_markers": [[
                "test_live_mod_audits_more_than_the_seven_route_groups",
                "test_live_68_tag_matrix_is_closed",
                "Ran 15 tests",
                "OK",
            ]],
        },
        "r13_ledger_validation_output": {
            "commands": [[
                *python_prefix,
                "-m",
                "unittest",
                "-v",
                "jxp_validation.tests.test_validation.SharedLedgerTests",
            ]],
            "cwd": str(main_mod),
            "environment": test_environment,
            "required_markers": [[
                "test_live_shared_ledger_is_consistent",
                "test_shared_ledger_rejects_descriptor_version_drift",
                "test_shared_ledger_rejects_unindexed_report",
                "Ran 3 tests",
                "OK",
            ]],
        },
        "r13_skill_validation_output_if_changed": {
            "commands": [
                [*python_prefix, str(quick_validate), str(repo_skill)],
                [*python_prefix, str(quick_validate), str(installed_skill)],
            ],
            "cwd": str(repo),
            "environment": base_environment,
            "required_markers": [["Skill is valid!"], ["Skill is valid!"]],
            "repo_skill": str(repo_skill),
            "installed_skill": str(installed_skill),
        },
    }


def _r13_gate_receipt_expectation(
    role: str, context: dict[str, object]
) -> dict[str, object]:
    spec = _r13_static_gate_specs(context).get(role)
    if spec is None:
        raise AcceptanceError(f"unknown R13 static gate role: {role}")
    commands = spec.get("commands")
    if not isinstance(commands, list) or not commands:
        raise AcceptanceError(f"R13 static gate command contract is malformed: {role}")
    return {
        "commands": commands,
        "exit_codes": [0 for _ in commands],
        "checks": [
            {"id": check_id, "status": "PASS"}
            for check_id in _R13_GATE_CHECK_IDS[role]
        ],
        "transcript": _r13_gate_receipt_summary(role),
    }


def _r13_skill_tree_manifest(root: Path, label: str) -> list[dict[str, object]]:
    records = _r13_plain_tree_manifest(root, label)
    if not records:
        raise AcceptanceError(f"{label} contains no files")
    return records


def _r13_live_runtime_payload_guard(
    context: dict[str, object],
) -> list[dict[str, object]]:
    repo = Path(str(context["repo"])).resolve()
    revision = str(context["candidate_revision"])
    result: list[dict[str, object]] = []
    for component in _current_components(repo, main_only=False):
        live_manifest = _manifest(component)
        live_records = tuple(
            _normalized_manifest_record(record) for record in live_manifest
        )
        committed_records = _git_snapshot_manifest_records(component.key, revision)
        if not _json_exact_equal(live_records, committed_records):
            raise AcceptanceError(
                f"R13 live {component.key} runtime payload differs from candidate Git bytes"
            )
        result.append(
            {
                "component": component.key,
                "version": _descriptor_value(
                    component.source / "descriptor.mod", "version"
                ),
                "source_revision": revision,
                "fingerprint": _snapshot_fingerprint(
                    component, live_manifest, revision
                ),
            }
        )
    return result


def _run_r13_bounded_process(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str],
    max_output_bytes: int,
) -> subprocess.CompletedProcess[bytes]:
    """Drain both pipes concurrently and kill before output can grow unbounded."""

    if (
        isinstance(max_output_bytes, bool)
        or not isinstance(max_output_bytes, int)
        or max_output_bytes <= 0
    ):
        raise AcceptanceError("R13 static gate output budget is exhausted")
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=env,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
        )
    except OSError as exc:
        raise AcceptanceError(f"cannot start R13 static gate: {exc}") from exc
    if process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise AcceptanceError("R13 static gate pipes were not created")

    lock = threading.Lock()
    overflow = threading.Event()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    reader_errors: list[BaseException] = []

    def drain(name: str, stream: object) -> None:
        try:
            while True:
                chunk = stream.read(64 * 1024)  # type: ignore[attr-defined]
                if not chunk:
                    break
                if not isinstance(chunk, bytes):
                    raise TypeError("process pipe returned non-bytes data")
                with lock:
                    captured = len(buffers["stdout"]) + len(buffers["stderr"])
                    remaining = max_output_bytes - captured
                    if remaining > 0:
                        buffers[name].extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        overflow.set()
                if overflow.is_set():
                    try:
                        process.kill()
                    except OSError:
                        pass
        except BaseException as exc:  # Propagate reader failures on the main thread.
            reader_errors.append(exc)
            try:
                process.kill()
            except OSError:
                pass
        finally:
            try:
                stream.close()  # type: ignore[attr-defined]
            except OSError:
                pass

    readers = [
        threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
    ]
    for reader in readers:
        reader.start()
    timed_out = False
    termination_failed = False
    try:
        returncode = process.wait(timeout=_R13_GATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            process.kill()
        except OSError:
            pass
        try:
            returncode = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            termination_failed = True
            returncode = -1
            for stream in (process.stdout, process.stderr):
                try:
                    stream.close()
                except OSError:
                    pass
    finally:
        for reader in readers:
            reader.join(timeout=30)
    if any(reader.is_alive() for reader in readers):
        raise AcceptanceError("R13 static gate output readers did not stop")
    if termination_failed:
        raise AcceptanceError("R13 static gate could not be terminated after timeout")
    if timed_out:
        raise AcceptanceError("R13 static gate timed out")
    if reader_errors:
        raise AcceptanceError(
            f"R13 static gate output read failed: {reader_errors[0]}"
        ) from reader_errors[0]
    if overflow.is_set():
        raise AcceptanceError(
            "R13 static gate exceeded its streaming output budget: "
            f"> {max_output_bytes}"
        )
    return subprocess.CompletedProcess(
        list(command),
        returncode,
        bytes(buffers["stdout"]),
        bytes(buffers["stderr"]),
    )


def _execute_r13_static_gate_verifications(
    context: dict[str, object],
    expected_payload: Sequence[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Run every R13 static gate now; user-authored JSON is never sufficient."""

    _assert_processes_stopped()
    payload_guard = _r13_live_runtime_payload_guard(context)
    if not _json_exact_equal(payload_guard, list(expected_payload)):
        raise AcceptanceError("R13 parent payload differs from live candidate Git payload")
    specs = _r13_static_gate_specs(context)
    if set(specs) != set(_R13_GATE_CHECK_IDS):
        raise AcceptanceError("R13 static gate command registry is incomplete")
    toolchain_guard = _r13_gate_toolchain_guard(context)
    total_transcript_bytes = 0
    results: dict[str, dict[str, object]] = {}
    for role, spec in specs.items():
        cwd = _require_ordinary_directory(Path(str(spec["cwd"])), f"R13 gate cwd {role}")
        commands = spec.get("commands")
        markers = spec.get("required_markers")
        environment_overrides = spec.get("environment")
        if (
            not isinstance(commands, list)
            or not commands
            or not isinstance(markers, list)
            or len(markers) != len(commands)
            or not isinstance(environment_overrides, dict)
        ):
            raise AcceptanceError(f"R13 static gate specification is malformed: {role}")
        marker_proofs: list[dict[str, object]] = []
        executions: list[dict[str, object]] = []
        for command, command_markers in zip(commands, markers, strict=True):
            if (
                not isinstance(command, list)
                or not command
                or not all(isinstance(item, str) and item for item in command)
                or not isinstance(command_markers, list)
                or not command_markers
                or not all(isinstance(item, str) and item for item in command_markers)
            ):
                raise AcceptanceError(f"R13 static gate argv/markers are malformed: {role}")
            if any(Path(item).name.casefold() in PROCESS_NAMES for item in command):
                raise AcceptanceError(f"R13 static gate command attempts a game launch: {role}")
            if any(
                item.casefold().startswith("-userdir")
                or item.casefold() == "-skipmainmodvalidation"
                for item in command
            ):
                raise AcceptanceError(f"R13 static gate argv is unsafe or incomplete: {role}")
            if not all(
                isinstance(key, str)
                and key
                and isinstance(value, str)
                for key, value in environment_overrides.items()
            ):
                raise AcceptanceError(f"R13 static gate environment is malformed: {role}")
            environment = dict(environment_overrides)
            if not _json_exact_equal(
                _r13_gate_toolchain_guard(context), toolchain_guard
            ):
                raise AcceptanceError(f"R13 gate toolchain changed before execution: {role}")
            executable = _r13_toolchain_file_record(
                Path(command[0]), f"R13 gate executable {role}"
            )
            started_at = _utc_now().isoformat()
            try:
                completed = _run_r13_bounded_process(
                    command,
                    cwd=cwd,
                    env=environment,
                    max_output_bytes=min(
                        _R13_GATE_MAX_TRANSCRIPT_BYTES,
                        _R13_GATE_MAX_TOTAL_TRANSCRIPT_BYTES
                        - total_transcript_bytes,
                    ),
                )
            finally:
                _assert_processes_stopped()
            if not _json_exact_equal(
                _r13_gate_toolchain_guard(context), toolchain_guard
            ):
                raise AcceptanceError(f"R13 gate toolchain changed during execution: {role}")
            if not _json_exact_equal(
                _r13_live_runtime_payload_guard(context), payload_guard
            ):
                raise AcceptanceError(f"R13 static gate changed runtime payload: {role}")
            completed_at = _utc_now().isoformat()
            if (
                isinstance(completed.returncode, bool)
                or not isinstance(completed.returncode, int)
                or completed.stdout is not None
                and not isinstance(completed.stdout, bytes)
                or completed.stderr is not None
                and not isinstance(completed.stderr, bytes)
            ):
                raise AcceptanceError(f"R13 static gate returned malformed process data: {role}")
            stdout = completed.stdout if completed.stdout is not None else b""
            stderr = completed.stderr if completed.stderr is not None else b""
            transcript_bytes = len(stdout) + len(stderr)
            total_transcript_bytes += transcript_bytes
            transcript = (stdout + b"\n" + stderr).decode("utf-8", errors="replace")
            missing = [marker for marker in command_markers if marker not in transcript]
            if (
                completed.returncode != 0
                or transcript_bytes > _R13_GATE_MAX_TRANSCRIPT_BYTES
                or total_transcript_bytes > _R13_GATE_MAX_TOTAL_TRANSCRIPT_BYTES
                or missing
            ):
                raise AcceptanceError(
                    f"R13 live static gate failed: role={role}, "
                    f"exit={completed.returncode}, missing_markers={missing}, "
                    f"transcript_bytes={transcript_bytes}"
                )
            executions.append(
                {
                    "argv": list(command),
                    "cwd": str(cwd),
                    "effective_environment": environment,
                    "effective_environment_sha256": _object_sha256(environment),
                    "executable": executable,
                    "toolchain_guard_sha256_before": toolchain_guard[
                        "toolchain_sha256"
                    ],
                    "toolchain_guard_sha256_after": toolchain_guard[
                        "toolchain_sha256"
                    ],
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "exit_code": completed.returncode,
                    "stdout_b64": base64.b64encode(stdout).decode("ascii"),
                    "stdout_bytes": len(stdout),
                    "stdout_sha256": sha256(stdout).hexdigest(),
                    "stderr_b64": base64.b64encode(stderr).decode("ascii"),
                    "stderr_bytes": len(stderr),
                    "stderr_sha256": sha256(stderr).hexdigest(),
                    "framed_output_sha256": sha256(
                        struct.pack(">Q", len(stdout))
                        + stdout
                        + struct.pack(">Q", len(stderr))
                        + stderr
                    ).hexdigest(),
                }
            )
            marker_proofs.append(
                {
                    "required_markers": list(command_markers),
                    "required_markers_sha256": _object_sha256(list(command_markers)),
                    "matched": True,
                }
            )
        additional_proof: dict[str, object] = {}
        if role == "r13_skill_validation_output_if_changed":
            repo_manifest = _r13_skill_tree_manifest(
                Path(str(spec["repo_skill"])), "repo EU4 skill"
            )
            installed_manifest = _r13_skill_tree_manifest(
                Path(str(spec["installed_skill"])), "installed EU4 skill"
            )
            if not _json_exact_equal(repo_manifest, installed_manifest):
                raise AcceptanceError("repo and installed EU4 skill mirrors disagree")
            skill_guard = toolchain_guard.get("installed_skill")
            if not isinstance(skill_guard, dict):
                raise AcceptanceError("R13 toolchain lacks Git-derived skill proof")
            additional_proof = {
                "skill_mirror_sha256": _object_sha256(repo_manifest),
                "skill_file_count": len(repo_manifest),
                "source_revision": skill_guard.get("source_revision"),
                "git_tree_sha256": skill_guard.get("git_tree_sha256"),
            }
        expectation = _r13_gate_receipt_expectation(role, context)
        results[role] = {
            **expectation,
            "passed": True,
            "execution_mode": "live_close_release",
            "payload_guard": payload_guard,
            "toolchain_guard": toolchain_guard,
            "executions": executions,
            "marker_proofs": marker_proofs,
            "additional_proof": additional_proof,
        }
    return results


def _run_r13_static_gate_verifications(
    context: dict[str, object],
    expected_payload: Sequence[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Run every controlled gate with an isolated, no-clobber temp directory."""

    user_data = _require_ordinary_directory(
        Path(str(context["user_data"])), "R13 gate acceptance root"
    )
    temporary = user_data / ".jxp_r13_gate_temp"
    if os.path.lexists(temporary):
        raise AcceptanceError(f"R13 gate temp path already exists: {temporary}")
    temporary.mkdir()
    try:
        if _require_ordinary_directory(temporary, "R13 gate temp root").parent != user_data:
            raise AcceptanceError("R13 gate temp root escaped the acceptance root")
        _r13_prepare_gate_python_runtime(context)
        return _execute_r13_static_gate_verifications(context, expected_payload)
    finally:
        if os.path.lexists(temporary):
            if (
                temporary.parent != user_data
                or not temporary.is_dir()
                or _is_link_or_junction(temporary)
                or temporary.resolve() != temporary
            ):
                raise AcceptanceError(f"unsafe R13 gate temp path remains: {temporary}")
            shutil.rmtree(temporary)


def _require_utc_timestamp(value: object, label: str) -> None:
    parsed = _aware_datetime(value, label)
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise AcceptanceError(f"{label} must be UTC")


def _r13_parent_map(
    parents: Sequence[dict[str, object]],
    normalized: dict[str, object],
) -> dict[str, dict[str, object]]:
    by_role = {str(item.get("role")): item for item in parents}
    expected = [str(item["role"]) for item in normalized["parents"]]
    if set(by_role) != set(expected) or len(by_role) != len(parents):
        raise AcceptanceError("R13 parent role set is not exact")
    return {role: by_role[role] for role in expected}


def _r13_assertion_result_rows(
    parents: Sequence[dict[str, object]],
    normalized: dict[str, object],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role, parent in _r13_parent_map(parents, normalized).items():
        assertions = parent.get("assertions")
        if (
            not isinstance(assertions, list)
            or not assertions
            or parent.get("assertions_sha256") != _object_sha256(assertions)
        ):
            raise AcceptanceError(f"R13 parent assertions are not sealed: {role}")
        for assertion in assertions:
            if (
                not isinstance(assertion, dict)
                or assertion.get("status") != "PASS"
                or not isinstance(assertion.get("id"), str)
                or not isinstance(assertion.get("artifact_roles"), list)
                or not assertion["artifact_roles"]
            ):
                raise AcceptanceError(f"R13 parent assertion is not PASS: {role}")
            rows.append(
                {
                    "parent_role": role,
                    "scenario_id": parent["scenario_id"],
                    "phase": parent["phase"],
                    "collection_sha256": parent["collection_sha256"],
                    "assertion": assertion,
                    "assertion_sha256": _object_sha256(assertion),
                }
            )
    if len(rows) != 65:
        raise AcceptanceError(
            f"R13 must close exactly 65 PROBE/R1-R12 assertions; found {len(rows)}"
        )
    return rows


def _r13_lineage_rows(
    parents: Sequence[dict[str, object]],
    normalized: dict[str, object],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role, parent in _r13_parent_map(parents, normalized).items():
        rows.append(
            {
                "role": role,
                "scenario_id": parent["scenario_id"],
                "phase": parent["phase"],
                "collection_sha256": parent["collection_sha256"],
                "collection_seal_sha256": parent["collection_seal_sha256"],
                "session_sha256": parent["session_sha256"],
                "session_seal_sha256": parent["session_seal_sha256"],
                "contract_sha256": parent["contract_sha256"],
                "artifact_roles_sha256": parent["artifact_roles_sha256"],
                "assertions_sha256": parent["assertions_sha256"],
                "snapshots_sha256": parent["snapshots_sha256"],
                "sealed_inputs_sha256": parent["sealed_inputs_sha256"],
                "parent_dependencies_sha256": parent[
                    "parent_dependencies_sha256"
                ],
                "fixture_uses_sha256": parent["fixture_uses_sha256"],
                "required_fixture_records_sha256": parent[
                    "required_fixture_records_sha256"
                ],
                "runtime_oracle_evidence_sha256": parent[
                    "runtime_oracle_evidence_sha256"
                ],
            }
        )
    if len(rows) != 16:
        raise AcceptanceError("R13 lineage index must contain sixteen parents")
    return rows


def _r13_current_payload(
    parents: Sequence[dict[str, object]], candidate_revision: str
) -> list[dict[str, object]]:
    identities: dict[str, set[tuple[str, str, str]]] = {}
    for parent in parents:
        snapshots = parent.get("snapshots")
        if (
            not isinstance(snapshots, list)
            or parent.get("snapshots_sha256") != _object_sha256(snapshots)
        ):
            raise AcceptanceError("R13 parent snapshot lineage is not sealed")
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                raise AcceptanceError("R13 parent snapshot is malformed")
            if snapshot.get("source_revision") != candidate_revision:
                continue
            component = snapshot.get("component")
            version = snapshot.get("version")
            fingerprint = snapshot.get("fingerprint")
            if (
                component not in {"main", "map"}
                or not isinstance(version, str)
                or not isinstance(fingerprint, str)
                or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)
            ):
                raise AcceptanceError("R13 current snapshot identity is malformed")
            identities.setdefault(str(component), set()).add(
                (version, candidate_revision, fingerprint)
            )
    if set(identities) != {"main", "map"} or any(
        len(values) != 1 for values in identities.values()
    ):
        raise AcceptanceError(
            "R13 parents must agree on one current main and one current map payload"
        )
    return [
        {
            "component": component,
            "version": next(iter(identities[component]))[0],
            "source_revision": candidate_revision,
            "fingerprint": next(iter(identities[component]))[2],
        }
        for component in ("main", "map")
    ]


def _r13_common_evidence_identity(
    parents: Sequence[dict[str, object]],
    context: dict[str, object],
) -> dict[str, object]:
    payload = _r13_current_payload(parents, str(context["candidate_revision"]))
    return {
        "candidate_revision": context["candidate_revision"],
        "matrix_sha256": context["matrix_sha256"],
        "parent_lineage_sha256": _object_sha256(list(parents)),
        "game_pins_sha256": _object_sha256(context["game_pins"]),
        "tested_payload": payload,
        "tested_payload_sha256": _object_sha256(payload),
    }


def _validated_r13_live_gate_verification(
    role: str,
    context: dict[str, object],
    verification: object,
) -> dict[str, object]:
    expectation = _r13_gate_receipt_expectation(role, context)
    specs = _r13_static_gate_specs(context)
    spec = specs[role]
    required = {
        *expectation,
        "passed",
        "execution_mode",
        "payload_guard",
        "toolchain_guard",
        "executions",
        "marker_proofs",
        "additional_proof",
    }
    if (
        not isinstance(verification, dict)
        or set(verification) != required
        or verification.get("passed") is not True
        or verification.get("execution_mode") != "live_close_release"
        or any(
            not _json_exact_equal(verification.get(key), expected)
            for key, expected in expectation.items()
        )
    ):
        raise AcceptanceError(f"R13 live gate verification schema disagrees: {role}")
    executions = verification.get("executions")
    marker_proofs = verification.get("marker_proofs")
    live_toolchain_guard = _r13_gate_toolchain_guard(context)
    if not _json_exact_equal(
        verification.get("toolchain_guard"), live_toolchain_guard
    ):
        raise AcceptanceError(f"R13 live gate toolchain disagrees: {role}")
    commands = expectation["commands"]
    required_markers = spec["required_markers"]
    execution_keys = {
        "argv",
        "cwd",
        "effective_environment",
        "effective_environment_sha256",
        "executable",
        "toolchain_guard_sha256_before",
        "toolchain_guard_sha256_after",
        "started_at",
        "completed_at",
        "exit_code",
        "stdout_b64",
        "stdout_bytes",
        "stdout_sha256",
        "stderr_b64",
        "stderr_bytes",
        "stderr_sha256",
        "framed_output_sha256",
    }
    if (
        not isinstance(executions, list)
        or len(executions) != len(commands)
        or not isinstance(marker_proofs, list)
        or len(marker_proofs) != len(commands)
    ):
        raise AcceptanceError(f"R13 live gate execution cardinality disagrees: {role}")
    expected_marker_proofs: list[dict[str, object]] = []
    for execution, command, markers in zip(
        executions, commands, required_markers, strict=True
    ):
        if (
            not isinstance(execution, dict)
            or set(execution) != execution_keys
            or not _json_exact_equal(execution.get("argv"), command)
            or execution.get("cwd") != spec["cwd"]
            or not _json_exact_equal(
                execution.get("effective_environment"), spec["environment"]
            )
            or execution.get("effective_environment_sha256")
            != _object_sha256(spec["environment"])
            or not _json_exact_equal(
                execution.get("executable"),
                _r13_toolchain_file_record(
                    Path(command[0]), f"R13 gate executable {role}"
                ),
            )
            or execution.get("toolchain_guard_sha256_before")
            != live_toolchain_guard["toolchain_sha256"]
            or execution.get("toolchain_guard_sha256_after")
            != live_toolchain_guard["toolchain_sha256"]
            or isinstance(execution.get("exit_code"), bool)
            or not isinstance(execution.get("exit_code"), int)
            or execution.get("exit_code") != 0
        ):
            raise AcceptanceError(f"R13 live gate execution identity disagrees: {role}")
        _require_utc_timestamp(execution.get("started_at"), f"R13 gate {role} started_at")
        _require_utc_timestamp(
            execution.get("completed_at"), f"R13 gate {role} completed_at"
        )
        if _aware_datetime(
            execution["completed_at"], f"R13 gate {role} completed_at"
        ) < _aware_datetime(
            execution["started_at"], f"R13 gate {role} started_at"
        ):
            raise AcceptanceError(f"R13 live gate timestamps are reversed: {role}")
        if not isinstance(execution.get("stdout_b64"), str) or not isinstance(
            execution.get("stderr_b64"), str
        ):
            raise AcceptanceError(f"R13 live gate output base64 is not text: {role}")
        try:
            stdout = base64.b64decode(execution["stdout_b64"], validate=True)
            stderr = base64.b64decode(execution["stderr_b64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise AcceptanceError(f"R13 live gate output base64 is invalid: {role}") from exc
        transcript_bytes = len(stdout) + len(stderr)
        transcript = (stdout + b"\n" + stderr).decode("utf-8", errors="replace")
        if (
            transcript_bytes > _R13_GATE_MAX_TRANSCRIPT_BYTES
            or isinstance(execution.get("stdout_bytes"), bool)
            or not isinstance(execution.get("stdout_bytes"), int)
            or isinstance(execution.get("stderr_bytes"), bool)
            or not isinstance(execution.get("stderr_bytes"), int)
            or execution.get("stdout_bytes") != len(stdout)
            or execution.get("stderr_bytes") != len(stderr)
            or execution.get("stdout_sha256") != sha256(stdout).hexdigest()
            or execution.get("stderr_sha256") != sha256(stderr).hexdigest()
            or execution.get("framed_output_sha256")
            != sha256(
                struct.pack(">Q", len(stdout))
                + stdout
                + struct.pack(">Q", len(stderr))
                + stderr
            ).hexdigest()
            or any(marker not in transcript for marker in markers)
        ):
            raise AcceptanceError(f"R13 live gate output proof disagrees: {role}")
        expected_marker_proofs.append(
            {
                "required_markers": list(markers),
                "required_markers_sha256": _object_sha256(list(markers)),
                "matched": True,
            }
        )
    if not _json_exact_equal(marker_proofs, expected_marker_proofs):
        raise AcceptanceError(f"R13 live gate marker proof disagrees: {role}")
    additional_proof = verification.get("additional_proof")
    if not isinstance(additional_proof, dict):
        raise AcceptanceError(f"R13 live gate additional proof is malformed: {role}")
    if role == "r13_skill_validation_output_if_changed":
        if (
            set(additional_proof)
            != {
                "skill_mirror_sha256",
                "skill_file_count",
                "source_revision",
                "git_tree_sha256",
            }
            or not isinstance(additional_proof.get("skill_mirror_sha256"), str)
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(additional_proof["skill_mirror_sha256"])
            )
            or isinstance(additional_proof.get("skill_file_count"), bool)
            or not isinstance(additional_proof.get("skill_file_count"), int)
            or int(additional_proof["skill_file_count"]) <= 0
            or additional_proof.get("source_revision")
            != live_toolchain_guard["installed_skill"]["source_revision"]
            or additional_proof.get("git_tree_sha256")
            != live_toolchain_guard["installed_skill"]["git_tree_sha256"]
            or additional_proof.get("skill_mirror_sha256")
            != live_toolchain_guard["installed_skill"]["sha256"]
            or additional_proof.get("skill_file_count")
            != live_toolchain_guard["installed_skill"]["file_count"]
        ):
            raise AcceptanceError("R13 live EU4 skill proof is malformed")
    elif additional_proof:
        raise AcceptanceError(f"R13 gate has unexpected additional proof: {role}")
    return dict(verification)


def _r13_gate_total_raw_bytes(
    verifications: dict[str, dict[str, object]], label: str
) -> int:
    if set(verifications) != set(_R13_GATE_CHECK_IDS):
        raise AcceptanceError(f"{label} gate role set is not exact")
    total = 0
    for role in _R13_GATE_CHECK_IDS:
        executions = verifications[role].get("executions")
        if not isinstance(executions, list):
            raise AcceptanceError(f"{label} gate executions are malformed: {role}")
        for execution in executions:
            if not isinstance(execution, dict):
                raise AcceptanceError(f"{label} gate execution is malformed: {role}")
            for key in ("stdout_bytes", "stderr_bytes"):
                value = execution.get(key)
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise AcceptanceError(f"{label} gate byte count is malformed: {role}")
                total += value
    if total > _R13_GATE_MAX_TOTAL_TRANSCRIPT_BYTES:
        raise AcceptanceError(
            f"{label} aggregate gate transcript exceeds limit: "
            f"{total} > {_R13_GATE_MAX_TOTAL_TRANSCRIPT_BYTES}"
        )
    return total


def _r13_journal_entry(
    ledger_text: str, entry_id: str
) -> tuple[dict[str, object], str]:
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,95}", entry_id):
        raise AcceptanceError("R13 ledger entry id is invalid")
    # CommonMark recognizes LF, CRLF, and CR as line endings.  Python's
    # splitlines() also treats several control characters and Unicode
    # separators as line breaks, which would let a visually hidden heading or
    # fence become structural to this parser alone.
    if any(
            ord(character) < 0x20 and character not in "\t\r\n"
            or 0x7F <= ord(character) <= 0x9F
            or character in "\u2028\u2029"
            for character in ledger_text
    ):
        raise AcceptanceError(
            "R13 ledger contains a non-CommonMark line separator or control"
        )
    lines = ledger_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    outside: set[int] = set()
    openings: dict[int, tuple[str, int, str]] = {}
    closing_for: dict[int, int] = {}
    active: tuple[int, str, int] | None = None
    opener_pattern = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
    for index, line in enumerate(lines):
        if active is not None:
            opener_index, character, minimum = active
            if re.fullmatch(
                rf" {{0,3}}{re.escape(character)}{{{minimum},}}[ \t]*", line
            ):
                closing_for[opener_index] = index
                active = None
            continue
        match = opener_pattern.fullmatch(line)
        if match is not None:
            marker = match.group(1)
            info = match.group(2)
            if marker[0] == "`" and "`" in info:
                outside.add(index)
                continue
            openings[index] = (marker[0], len(marker), info)
            active = (index, marker[0], len(marker))
            continue
        outside.add(index)
    if active is not None:
        raise AcceptanceError("R13 ledger contains an unclosed Markdown fence")
    if any(
        re.match(r"^ {0,3}<(?:!--|\?|!|/?[A-Za-z])", lines[index])
        for index in outside
    ):
        raise AcceptanceError("R13 ledger cannot contain raw HTML blocks")

    update_headings = [
        index
        for index in sorted(outside)
        if lines[index] == "## Update Journal"
    ]
    if len(update_headings) != 1:
        raise AcceptanceError("R13 ledger must contain one real Update Journal heading")
    journal_start = update_headings[0] + 1
    journal_end = len(lines)
    for index in range(journal_start, len(lines)):
        if index in outside and re.fullmatch(r"##(?:[ \t]+.*)?", lines[index]):
            journal_end = index
            break
    heading_pattern = re.compile(
        r"^### (?P<date>\d{4}-\d{2}-\d{2}) - "
        r"(?P<id>[A-Z0-9][A-Z0-9_-]{2,95}) - (?P<title>\S(?:.*\S)?)$"
    )
    headings: list[tuple[int, re.Match[str]]] = []
    for index in range(journal_start, journal_end):
        if index not in outside or not re.fullmatch(
            r"###(?:[ \t]+.*)?", lines[index]
        ):
            continue
        match = heading_pattern.fullmatch(lines[index])
        if match is None:
            raise AcceptanceError("R13 Update Journal contains a malformed entry heading")
        headings.append((index, match))
    matching = [item for item in headings if item[1].group("id") == entry_id]
    if len(matching) != 1:
        raise AcceptanceError("R13 ledger entry id must identify one real journal heading")
    selected_index, selected = matching[0]
    later = [index for index, _match in headings if index > selected_index]
    section_end = min(later) if later else journal_end
    section = "\n".join(lines[selected_index:section_end]).strip() + "\n"

    blocks: list[str] = []
    for opener_index, (character, length, info) in openings.items():
        if not selected_index < opener_index < section_end:
            continue
        info_tokens = info.strip().split(None, 1)
        target_like = bool(
            info_tokens and info_tokens[0] == "jxp-r13-journal-json"
        )
        if target_like and (
            character != "`"
            or length != 3
            or lines[opener_index] != "```jxp-r13-journal-json"
            or lines[closing_for[opener_index]] != "```"
        ):
            raise AcceptanceError(
                "R13 structured journal JSON must use exact opening and closing fences"
            )
        if (
            character == "`"
            and length == 3
            and lines[opener_index] == "```jxp-r13-journal-json"
            and info == "jxp-r13-journal-json"
        ):
            closer_index = closing_for[opener_index]
            if closer_index >= section_end or lines[closer_index] != "```":
                raise AcceptanceError(
                    "R13 structured journal JSON must use an exact closing fence"
                )
            blocks.append("\n".join(lines[opener_index + 1 : closer_index]) + "\n")
    if len(blocks) != 1:
        raise AcceptanceError(
            "R13 ledger journal entry must contain one real structured JSON block"
        )
    parsed = _strict_json_loads(blocks[0], "R13 ledger journal entry")
    if not isinstance(parsed, dict):
        raise AcceptanceError("R13 ledger journal JSON must be an object")
    updated = _aware_datetime(parsed.get("updated_at"), "R13 journal updated_at")
    if updated.strftime("%Y-%m-%d") != selected.group("date"):
        raise AcceptanceError("R13 journal heading date and updated_at disagree")
    return parsed, section


def _expected_r13_journal_entry(
    entry_id: str,
    updated_at: object,
    parents: Sequence[dict[str, object]],
    normalized: dict[str, object],
    common: dict[str, object],
) -> dict[str, object]:
    _require_utc_timestamp(updated_at, "R13 journal updated_at")
    blockers = [str(item["id"]) for item in normalized["blockers"]]
    if blockers:
        raise AcceptanceError("R13 journal closure cannot be built while blockers remain")
    return {
        "schema": "jxp_r13_journal_entry/v1",
        "scenario_id": "R13",
        "phase": "closure",
        "entry_id": entry_id,
        "closure_status": "READY_FOR_LEAD_REVIEW",
        "ready_for_lead_review": True,
        "runtime_status": "RUNTIME_PASS",
        "candidate_revision": common["candidate_revision"],
        "matrix_sha256": common["matrix_sha256"],
        "parent_lineage_sha256": common["parent_lineage_sha256"],
        "parent_collection_sha256s": [
            str(item["collection_sha256"]) for item in parents
        ],
        "remaining_blocker_ids": [],
        "r13_scenario_pass_claimed": False,
        "r13_game_started": False,
        "continuous_obligations_closed": False,
        "updated_at": updated_at,
    }


def _validate_closure_artifact_format(
    path: Path,
    kind: str,
    role: str,
    daily_configuration: Sequence[dict[str, object]],
    parents: Sequence[dict[str, object]],
    normalized: dict[str, object],
    context: dict[str, object],
    daily_vfs: Sequence[dict[str, object]],
    gate_verifications: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    value = _read_json_object(
        path,
        f"R13 semantic artifact {role}",
        max_bytes=_R13_CLOSURE_MAX_INPUT_BYTES,
    )
    common = _r13_common_evidence_identity(parents, context)
    parent_lineage_sha256 = common["parent_lineage_sha256"]

    if role == "r13_assertion_result_manifest" and kind == "assertion_manifest":
        rows = _r13_assertion_result_rows(parents, normalized)
        required = {
            "schema",
            "status",
            "candidate_revision",
            "matrix_sha256",
            "parent_lineage_sha256",
            "assertion_count",
            "assertions",
            "generated_at",
        }
        if (
            set(value) != required
            or value.get("schema") != "jxp_r13_assertion_results/v1"
            or value.get("status") != "PASS"
            or value.get("candidate_revision") != common["candidate_revision"]
            or value.get("matrix_sha256") != common["matrix_sha256"]
            or value.get("parent_lineage_sha256") != parent_lineage_sha256
            or isinstance(value.get("assertion_count"), bool)
            or not isinstance(value.get("assertion_count"), int)
            or value.get("assertion_count") != len(rows)
            or not _json_exact_equal(value.get("assertions"), rows)
        ):
            raise AcceptanceError("R13 assertion-result manifest semantics disagree")
        _require_utc_timestamp(value.get("generated_at"), "R13 assertion results generated_at")
        return {
            "format": "r13-assertion-results-v1",
            "passed": True,
            "assertion_count": len(rows),
            "assertions_sha256": _object_sha256(rows),
        }

    if role == "r13_evidence_lineage_index" and kind == "evidence_index":
        rows = _r13_lineage_rows(parents, normalized)
        required = {
            "schema",
            "status",
            "candidate_revision",
            "matrix_sha256",
            "parent_lineage_sha256",
            "parent_count",
            "parents",
            "generated_at",
        }
        if (
            set(value) != required
            or value.get("schema") != "jxp_r13_evidence_lineage/v1"
            or value.get("status") != "PASS"
            or value.get("candidate_revision") != common["candidate_revision"]
            or value.get("matrix_sha256") != common["matrix_sha256"]
            or value.get("parent_lineage_sha256") != parent_lineage_sha256
            or isinstance(value.get("parent_count"), bool)
            or not isinstance(value.get("parent_count"), int)
            or value.get("parent_count") != len(rows)
            or not _json_exact_equal(value.get("parents"), rows)
        ):
            raise AcceptanceError("R13 evidence-lineage index semantics disagree")
        _require_utc_timestamp(value.get("generated_at"), "R13 lineage generated_at")
        return {
            "format": "r13-evidence-lineage-v1",
            "passed": True,
            "parent_count": len(rows),
            "lineage_sha256": _object_sha256(rows),
        }

    if role in _R13_GATE_CHECK_IDS and kind in {
        "static_gate_output",
        "conditional_static_gate_output",
    }:
        expectation = _r13_gate_receipt_expectation(role, context)
        required = {
            "schema",
            "role",
            "status",
            "candidate_revision",
            "matrix_sha256",
            "parent_lineage_sha256",
            "game_pins_sha256",
            "tested_payload",
            "tested_payload_sha256",
            "commands",
            "exit_codes",
            "completed_at",
            "checks",
            "transcript",
        }
        if (
            set(value) != required
            or value.get("schema") != "jxp_r13_static_gate_output/v3"
            or value.get("role") != role
            or value.get("status") != "PASS"
            or any(
                not _json_exact_equal(value.get(key), common[key]) for key in common
            )
            or any(
                not _json_exact_equal(value.get(key), expected)
                for key, expected in expectation.items()
            )
            or not isinstance(value.get("exit_codes"), list)
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item != 0
                for item in value.get("exit_codes", [])
            )
        ):
            raise AcceptanceError(f"R13 static gate receipt semantics disagree: {role}")
        _require_utc_timestamp(value.get("completed_at"), f"R13 gate {role} completed_at")
        verification = _validated_r13_live_gate_verification(
            role, context, (gate_verifications or {}).get(role)
        )
        if not _json_exact_equal(
            verification.get("payload_guard"), common["tested_payload"]
        ):
            raise AcceptanceError(
                f"R13 live gate payload differs from parent evidence: {role}"
            )
        return {
            "format": "r13-static-gate-output-v3",
            "passed": True,
            "role": role,
            "execution_mode": "live_close_release",
            "commands_sha256": _object_sha256(expectation["commands"]),
            "checks_sha256": _object_sha256(expectation["checks"]),
            "marker_proofs_sha256": _object_sha256(
                verification["marker_proofs"]
            ),
            "additional_proof": verification["additional_proof"],
            "tested_payload_sha256": common["tested_payload_sha256"],
            "live_verification": verification,
        }

    if role == "r13_daily_configuration_final_hashes" and kind == "hash_manifest":
        required = {
            "schema",
            "status",
            "candidate_revision",
            "matrix_sha256",
            "parent_lineage_sha256",
            "daily_configuration",
            "daily_configuration_sha256",
            "daily_vfs_sha256",
            "recorded_at",
        }
        configuration = list(daily_configuration)
        if (
            set(value) != required
            or value.get("schema") != "jxp_r13_daily_state/v1"
            or value.get("status") != "PASS"
            or value.get("candidate_revision") != common["candidate_revision"]
            or value.get("matrix_sha256") != common["matrix_sha256"]
            or value.get("parent_lineage_sha256") != parent_lineage_sha256
            or not _json_exact_equal(
                value.get("daily_configuration"), configuration
            )
            or value.get("daily_configuration_sha256")
            != _object_sha256(configuration)
            or value.get("daily_vfs_sha256") != _object_sha256(list(daily_vfs))
        ):
            raise AcceptanceError("R13 final daily-state manifest semantics disagree")
        _require_utc_timestamp(value.get("recorded_at"), "R13 daily state recorded_at")
        return {
            "format": "r13-daily-state-v1",
            "passed": True,
            "configuration_sha256": _object_sha256(configuration),
            "daily_vfs_sha256": _object_sha256(list(daily_vfs)),
        }

    if role == "r13_canonical_ledger_update" and kind == "ledger_entry":
        ledger = Path(str(context["repo"])) / "japan_expanded_v2" / "dev_logs" / "JXP_SHARED_DEVELOPMENT_LEDGER.md"
        ledger = _closure_source_file(ledger, "canonical R13 ledger")
        ledger_text = ledger.read_text(encoding="utf-8-sig")
        required = {
            "schema",
            "status",
            "candidate_revision",
            "matrix_sha256",
            "parent_lineage_sha256",
            "ledger_path",
            "ledger_sha256",
            "entry_id",
            "entry_sha256",
            "runtime_status",
            "parent_collection_sha256s",
            "remaining_blocker_ids",
            "updated_at",
        }
        entry_id = value.get("entry_id")
        if not isinstance(entry_id, str):
            raise AcceptanceError("R13 canonical ledger entry id is missing")
        entry, _section = _r13_journal_entry(ledger_text, entry_id)
        expected_entry = _expected_r13_journal_entry(
            entry_id,
            value.get("updated_at"),
            parents,
            normalized,
            common,
        )
        if (
            set(value) != required
            or value.get("schema") != "jxp_r13_ledger_update/v2"
            or value.get("status") != "PASS"
            or value.get("candidate_revision") != common["candidate_revision"]
            or value.get("matrix_sha256") != common["matrix_sha256"]
            or value.get("parent_lineage_sha256") != parent_lineage_sha256
            or value.get("ledger_path") != str(ledger)
            or value.get("ledger_sha256") != _sha256_file(ledger)
            or not _json_exact_equal(entry, expected_entry)
            or value.get("entry_sha256") != _object_sha256(expected_entry)
            or value.get("runtime_status") != expected_entry["runtime_status"]
            or not _json_exact_equal(
                value.get("parent_collection_sha256s"),
                expected_entry["parent_collection_sha256s"],
            )
            or not _json_exact_equal(
                value.get("remaining_blocker_ids"),
                expected_entry["remaining_blocker_ids"],
            )
        ):
            raise AcceptanceError("R13 canonical ledger update semantics disagree")
        _require_utc_timestamp(value.get("updated_at"), "R13 ledger updated_at")
        return {
            "format": "r13-ledger-update-v2",
            "passed": True,
            "ledger_sha256": _sha256_file(ledger),
            "entry_id": entry_id,
            "entry_sha256": _object_sha256(expected_entry),
        }

    raise AcceptanceError(
        f"unsupported or mismatched R13 artifact role/kind: {role!r}/{kind!r}"
    )


def _preflight_r13_closure_inputs(
    values: Sequence[str],
    assertion_manifest: Path,
    normalized: dict[str, object],
) -> dict[str, object]:
    parsed = _parse_role_paths(values, "--artifact")
    expected_roles = normalized.get("artifact_roles")
    if not isinstance(expected_roles, dict) or set(parsed) != set(expected_roles):
        raise AcceptanceError(
            "--artifact roles do not exactly match the ten R13 closure roles"
        )
    paths = {
        str(role): _closure_source_file(
            parsed[str(role)],
            f"R13 artifact {role}",
            _R13_CLOSURE_MAX_INPUT_BYTES,
        )
        for role in expected_roles
    }
    assertion = _closure_source_file(
        assertion_manifest,
        "R13 manual assertion manifest",
        _R13_CLOSURE_MAX_INPUT_BYTES,
    )
    all_paths = [*paths.values(), assertion]
    if len({str(path) for path in all_paths}) != len(all_paths):
        raise AcceptanceError("R13 closure inputs must use eleven distinct paths")
    total = sum(path.stat().st_size for path in all_paths)
    if total > _R13_CLOSURE_MAX_INPUT_BYTES:
        raise AcceptanceError(
            "R13 aggregate closure inputs exceed limit before parsing: "
            f"{total} > {_R13_CLOSURE_MAX_INPUT_BYTES}"
        )
    return {
        "artifacts": {role: _file_record(path) for role, path in paths.items()},
        "assertion": _file_record(assertion),
        "total_bytes": total,
    }


def _closure_artifact_sources(
    values: Sequence[str],
    normalized: dict[str, object],
    daily_configuration: Sequence[dict[str, object]],
    parents: Sequence[dict[str, object]],
    context: dict[str, object],
    daily_vfs: Sequence[dict[str, object]],
    gate_verifications: dict[str, dict[str, object]],
    preflight: dict[str, object],
) -> dict[str, dict[str, object]]:
    parsed = _parse_role_paths(values, "--artifact")
    expected_roles = normalized["artifact_roles"]
    if not isinstance(expected_roles, dict) or set(parsed) != set(expected_roles):
        raise AcceptanceError(
            "--artifact roles do not exactly match the ten R13 closure roles"
        )
    records: dict[str, dict[str, object]] = {}
    paths: set[str] = set()
    digests: set[str] = set()
    for role in expected_roles:
        source = _closure_source_file(
            parsed[str(role)],
            f"R13 artifact {role}",
            _R13_CLOSURE_MAX_INPUT_BYTES,
        )
        kind = str(expected_roles[role])
        spec = normalized["artifact_specs"][role]
        validation = _validate_closure_artifact_format(
            source,
            kind,
            str(role),
            daily_configuration,
            parents,
            normalized,
            context,
            daily_vfs,
            gate_verifications,
        )
        source_record = _file_record(source)
        expected_preflight = preflight.get("artifacts")
        if (
            not isinstance(expected_preflight, dict)
            or not _json_exact_equal(
                source_record, expected_preflight.get(str(role))
            )
        ):
            raise AcceptanceError(f"R13 artifact changed after preflight: {role}")
        record = {
            "role": role,
            "kind": kind,
            "validation": validation,
            "supports_assertion_ids": spec["supports_assertion_ids"],
            "distinct": spec["distinct"],
            **source_record,
        }
        canonical_path = str(record["path"])
        digest = str(record["sha256"])
        if (
            spec.get("distinct") is not True
            or canonical_path in paths
            or digest in digests
        ):
            raise AcceptanceError("R13 artifact roles must bind distinct paths and bytes")
        paths.add(canonical_path)
        digests.add(digest)
        records[str(role)] = record
    return records


def _validate_closure_assertion_manifest(
    path: Path,
    normalized: dict[str, object],
    expected_source: dict[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    source = _closure_source_file(
        path, "R13 manual assertion manifest", _R13_CLOSURE_MAX_INPUT_BYTES
    )
    value = _read_json_object(
        source,
        "R13 manual assertion manifest",
        max_bytes=_R13_CLOSURE_MAX_INPUT_BYTES,
    )
    if (
        set(value) != {"schema", "scenario_id", "phase", "assertions"}
        or value.get("schema") != EVIDENCE_MANIFEST_SCHEMA
        or value.get("scenario_id") != "R13"
        or value.get("phase") != "closure"
        or not isinstance(value.get("assertions"), list)
    ):
        raise AcceptanceError("R13 manual assertion manifest schema disagrees")
    expected_assertions = normalized["assertions"]
    if len(value["assertions"]) != len(expected_assertions):
        raise AcceptanceError("R13 manual assertion manifest must contain six assertions")
    artifact_specs = normalized["artifact_specs"]
    for item, expected in zip(value["assertions"], expected_assertions, strict=True):
        expected_roles = [
            role
            for role, spec in artifact_specs.items()
            if expected["id"] in spec["supports_assertion_ids"]
        ]
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "id",
                "status",
                "note",
                "attestor",
                "attested_at",
                "artifact_roles",
            }
            or item.get("id") != expected["id"]
            or item.get("status") != "PASS"
            or not isinstance(item.get("note"), str)
            or not str(item["note"]).strip()
            or not isinstance(item.get("attestor"), str)
            or not str(item["attestor"]).strip()
            or not _json_exact_equal(item.get("artifact_roles"), expected_roles)
        ):
            raise AcceptanceError(
                f"R13 manual assertion identity/status/binding disagrees: {expected['id']}"
            )
        timestamp = item.get("attested_at")
        if not isinstance(timestamp, str):
            raise AcceptanceError("R13 manual assertion timestamp is missing")
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AcceptanceError(
                f"R13 manual assertion timestamp is invalid: {timestamp!r}"
            ) from exc
        if (
            parsed.tzinfo is None
            or parsed.utcoffset() is None
            or parsed.utcoffset().total_seconds() != 0
        ):
            raise AcceptanceError("R13 manual assertion timestamps must be UTC")
    file_record = _file_record(source)
    if expected_source is not None and not _json_exact_equal(
        file_record, expected_source
    ):
        raise AcceptanceError("R13 assertion manifest changed after preflight")
    return value, {
        "validation": {
            "format": "r13-manual-assertion-manifest",
            "schema": EVIDENCE_MANIFEST_SCHEMA,
            "passed": True,
        },
        **file_record,
    }


def _closure_automated_check_results(
    parents: Sequence[dict[str, object]],
    sources: dict[str, dict[str, object]],
    assertion_value: dict[str, object],
) -> list[dict[str, object]]:
    results = [
        {
            "id": "sixteen_parent_lineages_semantic",
            "matched": len(parents) == 16
            and all(
                isinstance(item, dict)
                and set(item) == _PARENT_DEPENDENCY_RECORD_KEYS
                for item in parents
            ),
        }
    ]
    results.extend(
        {
            "id": f"artifact_semantic:{role}",
            "matched": isinstance(source.get("validation"), dict)
            and source["validation"].get("passed") is True,
        }
        for role, source in sources.items()
    )
    assertions = assertion_value.get("assertions")
    results.append(
        {
            "id": "six_manual_closure_assertions_terminal",
            "matched": isinstance(assertions, list)
            and len(assertions) == 6
            and all(
                isinstance(item, dict) and item.get("status") == "PASS"
                for item in assertions
            ),
        }
    )
    return results


def _r13_closure_input_total_bytes(
    sources: dict[str, dict[str, object]], assertion_source: dict[str, object]
) -> int:
    """Bound all eleven caller-controlled closure inputs as one byte budget."""

    total = 0
    for label, record in (
        *((f"artifact {role}", source) for role, source in sources.items()),
        ("assertion manifest", assertion_source),
    ):
        value = record.get("bytes")
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise AcceptanceError(f"R13 {label} byte count is malformed")
        total += value
        if total > _R13_CLOSURE_MAX_INPUT_BYTES:
            raise AcceptanceError(
                "R13 aggregate closure inputs exceed limit: "
                f"{total} > {_R13_CLOSURE_MAX_INPUT_BYTES}"
            )
    return total


def _r13_closure_tree_total_bytes(root: Path, label: str) -> int:
    """Fail closed on links, non-files, hard links, or an oversized tree."""

    root = _require_ordinary_directory(root, label)
    total = 0
    stack = [root]
    while stack:
        directory = stack.pop()
        for path in directory.iterdir():
            if _is_link_or_junction(path):
                raise AcceptanceError(f"{label} contains a link or junction: {path}")
            if path.is_dir():
                stack.append(path)
                continue
            if not path.is_file() or path.stat().st_nlink != 1:
                raise AcceptanceError(f"{label} contains a non-ordinary file: {path}")
            size = path.stat().st_size
            if size < 0:
                raise AcceptanceError(f"{label} contains an invalid file size: {path}")
            total += size
            if total > _R13_CLOSURE_MAX_BYTES:
                raise AcceptanceError(
                    f"{label} exceeds the whole-tree size limit: "
                    f"{total} > {_R13_CLOSURE_MAX_BYTES}"
                )
    return total


def _copy_closure_inputs(
    staging: Path,
    output_root: Path,
    sources: dict[str, dict[str, object]],
    assertion_source: dict[str, object],
    assertion_value: dict[str, object],
    normalized: dict[str, object],
    daily_configuration: Sequence[dict[str, object]],
    parents: Sequence[dict[str, object]],
    context: dict[str, object],
    daily_vfs: Sequence[dict[str, object]],
    gate_verifications: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    copied_roles: dict[str, dict[str, object]] = {}
    for role, source in sources.items():
        copied = _copy_artifact(
            Path(str(source["path"])),
            staging / "artifacts" / role,
            max_bytes=int(source["bytes"]),
        )
        copied_path = Path(str(copied["path"]))
        copied_validation = _validate_closure_artifact_format(
            copied_path,
            str(source["kind"]),
            role,
            daily_configuration,
            parents,
            normalized,
            context,
            daily_vfs,
            gate_verifications,
        )
        if (
            not _json_exact_equal(copied_validation, source["validation"])
            or not _json_exact_equal(copied["bytes"], source["bytes"])
            or not _json_exact_equal(copied["sha256"], source["sha256"])
        ):
            raise AcceptanceError(f"R13 staged artifact changed while copying: {role}")
        copied_roles[role] = {
            "role": role,
            "kind": source["kind"],
            "source_path": source["path"],
            "validation": copied_validation,
            "path": str(output_root / copied_path.relative_to(staging)),
            "bytes": copied["bytes"],
            "mtime_ns": copied["mtime_ns"],
            "sha256": copied["sha256"],
            "supports_assertion_ids": source["supports_assertion_ids"],
            "distinct": source["distinct"],
        }
    copied_assertion = _copy_artifact(
        Path(str(assertion_source["path"])),
        staging / "assertions",
        max_bytes=int(assertion_source["bytes"]),
    )
    copied_assertion_path = Path(str(copied_assertion["path"]))
    copied_value, copied_source = _validate_closure_assertion_manifest(
        copied_assertion_path, normalized
    )
    if (
        not _json_exact_equal(copied_value, assertion_value)
        or copied_assertion["sha256"] != assertion_source["sha256"]
    ):
        raise AcceptanceError("R13 staged assertion manifest changed while copying")
    assertion_record = {
        "source_path": assertion_source["path"],
        "validation": copied_source["validation"],
        "path": str(output_root / copied_assertion_path.relative_to(staging)),
        "bytes": copied_assertion["bytes"],
        "mtime_ns": copied_assertion["mtime_ns"],
        "sha256": copied_assertion["sha256"],
    }
    return copied_roles, assertion_record


def _verify_closure_artifact_records(
    closure: dict[str, object],
    output_root: Path,
    sources: dict[str, dict[str, object]],
    normalized: dict[str, object],
    daily_configuration: Sequence[dict[str, object]],
    parents: Sequence[dict[str, object]],
    context: dict[str, object],
    daily_vfs: Sequence[dict[str, object]],
    gate_verifications: dict[str, dict[str, object]],
) -> None:
    records = closure.get("artifact_roles")
    if not isinstance(records, dict) or set(records) != set(sources):
        raise AcceptanceError("sealed R13 artifact role set disagrees")
    artifacts_root = _require_ordinary_directory(
        output_root / "artifacts", "sealed R13 artifact root"
    )
    if {path.name for path in artifacts_root.iterdir()} != set(records):
        raise AcceptanceError("sealed R13 artifact directories disagree")
    used_paths: set[str] = set()
    used_hashes: set[str] = set()
    for role, item in records.items():
        source = sources[role]
        if not isinstance(item, dict) or set(item) != _CLOSURE_ARTIFACT_RECORD_KEYS:
            raise AcceptanceError(f"sealed R13 artifact schema disagrees: {role}")
        path = Path(str(item["path"]))
        role_root = _require_ordinary_directory(
            artifacts_root / role, f"sealed R13 artifact role {role}"
        )
        if (
            path.resolve() != path
            or path.parent != role_root
            or not path.is_file()
            or _is_link_or_junction(path)
            or path.stat().st_nlink != 1
            or len(list(role_root.iterdir())) != 1
        ):
            raise AcceptanceError(f"sealed R13 artifact path is not ordinary: {role}")
        actual = _file_record(path)
        if any(
            not _json_exact_equal(actual[key], item[key])
            for key in ("bytes", "mtime_ns", "sha256")
        ):
            raise AcceptanceError(f"sealed R13 artifact bytes/hash changed: {role}")
        if (
            item["role"] != role
            or item["kind"] != source["kind"]
            or item["source_path"] != source["path"]
            or not _json_exact_equal(item["validation"], source["validation"])
            or not _json_exact_equal(
                item["supports_assertion_ids"], source["supports_assertion_ids"]
            )
            or item["distinct"] is not True
            or any(
                not _json_exact_equal(item[key], source[key])
                for key in ("bytes", "mtime_ns", "sha256")
            )
            or not _json_exact_equal(
                item["validation"],
                _validate_closure_artifact_format(
                    path,
                    str(item["kind"]),
                    role,
                    daily_configuration,
                    parents,
                    normalized,
                    context,
                    daily_vfs,
                    gate_verifications,
                ),
            )
        ):
            raise AcceptanceError(f"sealed R13 artifact lineage disagrees: {role}")
        if str(path) in used_paths or str(item["sha256"]) in used_hashes:
            raise AcceptanceError("sealed R13 artifacts replay a path or byte stream")
        used_paths.add(str(path))
        used_hashes.add(str(item["sha256"]))


def _verified_release_closure(
    output_root: Path,
    context: dict[str, object],
    parents: Sequence[dict[str, object]],
    sources: dict[str, dict[str, object]],
    assertion_value: dict[str, object],
    assertion_source: dict[str, object],
    normalized: dict[str, object],
    daily_configuration: Sequence[dict[str, object]],
    daily_vfs: Sequence[dict[str, object]],
    gate_verifications: dict[str, dict[str, object]],
) -> tuple[dict[str, object], bool]:
    output_root = _require_ordinary_directory(output_root, "R13 closure output root")
    _r13_closure_tree_total_bytes(output_root, "R13 closure output")
    expected_entries = {"artifacts", "assertions", CLOSURE_NAME, CLOSURE_SEAL_NAME}
    if {path.name for path in output_root.iterdir()} != expected_entries:
        raise AcceptanceError("R13 closure output root contains unexpected entries")
    closure_path = output_root / CLOSURE_NAME
    seal_path = output_root / CLOSURE_SEAL_NAME
    if any(
        not path.is_file() or _is_link_or_junction(path) or path.stat().st_nlink != 1
        for path in (closure_path, seal_path)
    ):
        raise AcceptanceError("R13 closure and seal must be ordinary files")
    closure = _read_json_object(closure_path, "R13 closure")
    seal = _read_json_object(seal_path, "R13 closure seal")
    if set(closure) != _CLOSURE_KEYS or set(seal) != _CLOSURE_SEAL_KEYS:
        raise AcceptanceError("R13 closure or seal schema disagrees")
    if normalized["blockers"]:
        raise AcceptanceError("sealed R13 closure cannot retain matrix blockers")
    ready = True
    status = "READY_FOR_LEAD_REVIEW"
    automated_results = _closure_automated_check_results(
        parents, sources, assertion_value
    )
    automated_passed = all(item.get("matched") is True for item in automated_results)
    if (
        seal.get("schema") != COLLECTION_SCHEMA
        or seal.get("closure_path") != str(closure_path)
        or seal.get("closure_sha256") != _sha256_file(closure_path)
        or closure.get("schema") != COLLECTION_SCHEMA
        or closure.get("scenario_id") != "R13"
        or closure.get("phase") != "closure"
        or closure.get("status") != status
        or closure.get("ready_for_lead_review") is not ready
        or not _json_exact_equal(
            closure.get("automated_check_results"), automated_results
        )
        or closure.get("automated_checks_passed") is not automated_passed
        or automated_passed is not True
        or closure.get("manual_assertions_complete") is not True
        or closure.get("manual_assertions_passed") is not True
        or closure.get("scenario_pass_claimed") is not False
        or closure.get("matrix_blockers") != []
        or closure.get("game_session_created") is not False
        or closure.get("active_lock_created") is not False
        or closure.get("game_started") is not False
    ):
        raise AcceptanceError("R13 closure status/seal invariants disagree")
    _aware_datetime(closure.get("closed_at"), "R13 closed_at")
    _aware_datetime(seal.get("sealed_at"), "R13 sealed_at")
    if any(
        not _json_exact_equal(closure.get(key), value)
        for key, value in context.items()
    ):
        raise AcceptanceError("R13 closure current roots/revision/contract disagree")
    parent_list = list(parents)
    if (
        not _json_exact_equal(closure.get("parents"), parent_list)
        or closure.get("parent_lineage_sha256") != _object_sha256(parent_list)
        or seal.get("parent_lineage_sha256") != closure["parent_lineage_sha256"]
        or closure.get("artifact_roles_sha256")
        != _object_sha256(closure.get("artifact_roles"))
        or seal.get("artifact_roles_sha256") != closure["artifact_roles_sha256"]
        or seal.get("matrix_sha256") != context["matrix_sha256"]
        or seal.get("candidate_revision") != context["candidate_revision"]
        or seal.get("toolchain_revision") != context["toolchain_revision"]
    ):
        raise AcceptanceError("R13 parent/artifact lineage seals disagree")
    _verify_closure_artifact_records(
        closure,
        output_root,
        sources,
        normalized,
        daily_configuration,
        parents,
        context,
        daily_vfs,
        gate_verifications,
    )
    assertion_record = closure.get("assertion_manifest")
    if (
        not isinstance(assertion_record, dict)
        or set(assertion_record) != _CLOSURE_ASSERTION_RECORD_KEYS
    ):
        raise AcceptanceError("sealed R13 assertion manifest record disagrees")
    assertion_path = Path(str(assertion_record["path"]))
    assertion_root = _require_ordinary_directory(
        output_root / "assertions", "sealed R13 assertion root"
    )
    if (
        assertion_path.resolve() != assertion_path
        or assertion_path.parent != assertion_root
        or not assertion_path.is_file()
        or _is_link_or_junction(assertion_path)
        or assertion_path.stat().st_nlink != 1
        or len(list(assertion_root.iterdir())) != 1
    ):
        raise AcceptanceError("sealed R13 assertion manifest is not ordinary")
    copied_value, copied_source = _validate_closure_assertion_manifest(
        assertion_path, normalized
    )
    actual_assertion = _file_record(assertion_path)
    if (
        not _json_exact_equal(copied_value, assertion_value)
        or not _json_exact_equal(
            closure.get("assertions"), assertion_value["assertions"]
        )
        or assertion_record["source_path"] != assertion_source["path"]
        or not _json_exact_equal(
            assertion_record["validation"], copied_source["validation"]
        )
        or any(
            not _json_exact_equal(assertion_record[key], actual_assertion[key])
            for key in ("bytes", "mtime_ns", "sha256")
        )
        or any(
            not _json_exact_equal(assertion_record[key], assertion_source[key])
            for key in ("bytes", "mtime_ns", "sha256")
        )
        or closure.get("assertion_manifest_sha256") != assertion_record["sha256"]
        or seal.get("assertion_manifest_sha256") != assertion_record["sha256"]
    ):
        raise AcceptanceError("sealed R13 assertion manifest lineage disagrees")
    if (
        not _json_exact_equal(
            closure.get("daily_configuration_final"), list(daily_configuration)
        )
        or not _json_exact_equal(closure.get("daily_vfs_final"), list(daily_vfs))
        or closure.get("daily_vfs_final_sha256") != _object_sha256(list(daily_vfs))
    ):
        raise AcceptanceError("R13 final daily configuration/VFS state is stale")
    return closure, ready


def _sealed_r13_gate_verifications(
    output_root: Path,
) -> dict[str, dict[str, object]]:
    """Recover first-run gate executions for an idempotent sealed replay."""

    output_root = _require_ordinary_directory(
        output_root, "existing R13 closure output root"
    )
    _r13_closure_tree_total_bytes(output_root, "existing R13 closure output")
    closure_path = _closure_source_file(
        output_root / CLOSURE_NAME,
        "existing R13 closure",
        _R13_CLOSURE_MAX_BYTES,
    )
    seal_path = _closure_source_file(
        output_root / CLOSURE_SEAL_NAME,
        "existing R13 closure seal",
        _R13_CLOSURE_MAX_BYTES,
    )
    closure = _read_json_object(closure_path, "existing R13 closure")
    seal = _read_json_object(seal_path, "existing R13 closure seal")
    if (
        seal.get("schema") != COLLECTION_SCHEMA
        or seal.get("closure_path") != str(closure_path)
        or seal.get("closure_sha256") != _sha256_file(closure_path)
        or closure.get("schema") != COLLECTION_SCHEMA
        or closure.get("scenario_id") != "R13"
        or closure.get("phase") != "closure"
    ):
        raise AcceptanceError("existing R13 closure seal is invalid")
    artifact_roles = closure.get("artifact_roles")
    if not isinstance(artifact_roles, dict):
        raise AcceptanceError("existing R13 closure lacks artifact records")
    results: dict[str, dict[str, object]] = {}
    for role in _R13_GATE_CHECK_IDS:
        record = artifact_roles.get(role)
        validation = record.get("validation") if isinstance(record, dict) else None
        verification = (
            validation.get("live_verification")
            if isinstance(validation, dict)
            else None
        )
        if not isinstance(verification, dict):
            raise AcceptanceError(
                f"existing R13 closure lacks live gate execution: {role}"
            )
        results[role] = verification
    return results


def close_release(
    repo: Path,
    game_root: Path,
    daily_user_data: Path,
    user_data: Path,
    parent_collections: Sequence[str],
    artifacts: Sequence[str],
    assertion_manifest: Path,
    output_root: Path | None = None,
) -> tuple[dict[str, object], bool]:
    """Seal the non-runnable R13 release closure without creating a session."""

    _assert_processes_stopped()
    repo, game_root = _require_canonical_runtime_roots(repo, game_root)
    user_data = _require_canonical_acceptance_user_data(user_data)
    daily_user_data = _require_canonical_daily_user_data(daily_user_data, game_root)
    _require_disjoint_roots(user_data, daily_user_data, "acceptance and daily roots")
    _assert_no_active_session(user_data, "close release")
    game_pins = _verified_twelve_pins(repo, game_root)
    candidate_revision = _current_candidate_revision()
    matrix_sha256 = _scenario_matrix_sha256()
    scenario = _scenario("R13")
    normalized = _normalized_evidence_contract(scenario, None)
    if (
        normalized.get("runnable") is not False
        or len(normalized.get("parents", [])) != 16
        or len(normalized.get("artifact_roles", {})) != 10
        or len(normalized.get("assertions", [])) != 6
    ):
        raise AcceptanceError("R13 closure contract cardinalities disagree")
    if normalized.get("blockers"):
        blocker_ids = ", ".join(
            str(item.get("id", "<missing>"))
            for item in normalized["blockers"]
            if isinstance(item, dict)
        )
        raise AcceptanceError(
            "R13 closure is refused while matrix blockers remain; no blocked "
            f"closure is emitted: {blocker_ids}"
        )
    parsed_parents = _parse_role_paths(parent_collections, "--parent-collection")
    expected_parent_roles = {str(item["role"]) for item in normalized["parents"]}
    if set(parsed_parents) != expected_parent_roles:
        raise AcceptanceError(
            "--parent-collection roles do not exactly match the sixteen R13 parents"
        )
    sealed_parents = _seal_parent_collections(parent_collections)
    sealed_by_role = {str(item["role"]): item for item in sealed_parents}
    if set(sealed_by_role) != expected_parent_roles:
        raise AcceptanceError("sealed R13 parent role set changed")
    parents = [
        sealed_by_role[str(requirement["role"])]
        for requirement in normalized["parents"]
    ]
    expected_compatibility = {
        "matrix_sha256": matrix_sha256,
        "candidate_revision": candidate_revision,
        "game_pins": game_pins,
        "repo": str(repo),
        "game_root": str(game_root),
        "user_data": str(user_data),
        "daily_user_data": str(daily_user_data),
    }
    _validate_dependency_closure(
        scenario, None, [], parents, expected_compatibility
    )
    daily_configuration = _required_configuration_records(daily_user_data)
    daily_vfs = _daily_vfs_inventory(daily_user_data)
    output_root = _closure_output_root(user_data, output_root)
    contract_identity = _closure_contract_identity(scenario)
    context: dict[str, object] = {
        "candidate_revision": candidate_revision,
        "toolchain_revision": _r13_current_toolchain_revision(repo),
        "matrix_sha256": matrix_sha256,
        "contract_identity": contract_identity,
        "contract_sha256": _object_sha256(contract_identity),
        "repo": str(repo),
        "game_root": str(game_root),
        "user_data": str(user_data),
        "daily_user_data": str(daily_user_data),
        "output_root": str(output_root),
        "game_pins": game_pins,
    }
    input_preflight = _preflight_r13_closure_inputs(
        artifacts, assertion_manifest, normalized
    )
    expected_payload = _r13_current_payload(parents, candidate_revision)
    fresh_gate_verifications = _run_r13_static_gate_verifications(
        context, expected_payload
    )
    for role in _R13_GATE_CHECK_IDS:
        fresh = _validated_r13_live_gate_verification(
            role, context, fresh_gate_verifications.get(role)
        )
        if not _json_exact_equal(fresh.get("payload_guard"), expected_payload):
            raise AcceptanceError(
                f"fresh R13 replay gate payload disagrees with parents: {role}"
            )
    _r13_gate_total_raw_bytes(fresh_gate_verifications, "fresh R13")
    gate_verifications = (
        _sealed_r13_gate_verifications(output_root)
        if os.path.lexists(output_root)
        else fresh_gate_verifications
    )
    _r13_gate_total_raw_bytes(gate_verifications, "sealed R13")
    sources = _closure_artifact_sources(
        artifacts,
        normalized,
        daily_configuration,
        parents,
        context,
        daily_vfs,
        gate_verifications,
        input_preflight,
    )
    assertion_value, assertion_source = _validate_closure_assertion_manifest(
        assertion_manifest,
        normalized,
        expected_source=input_preflight["assertion"],
    )
    if (
        assertion_source["path"] in {item["path"] for item in sources.values()}
        or assertion_source["sha256"]
        in {item["sha256"] for item in sources.values()}
    ):
        raise AcceptanceError(
            "R13 manual assertion manifest must be distinct from all ten artifacts"
        )
    _r13_closure_input_total_bytes(sources, assertion_source)
    automated_check_results = _closure_automated_check_results(
        parents, sources, assertion_value
    )
    automated_checks_passed = all(
        item.get("matched") is True for item in automated_check_results
    )
    if not automated_checks_passed:
        raise AcceptanceError("R13 semantic automated checks did not all pass")
    if os.path.lexists(output_root):
        return _verified_release_closure(
            output_root,
            context,
            parents,
            sources,
            assertion_value,
            assertion_source,
            normalized,
            daily_configuration,
            daily_vfs,
            gate_verifications,
        )

    staging = user_data / f".{output_root.name}.{uuid.uuid4().hex}.staging"
    staging.mkdir()
    committed = False
    try:
        copied_roles, copied_assertion = _copy_closure_inputs(
            staging,
            output_root,
            sources,
            assertion_source,
            assertion_value,
            normalized,
            daily_configuration,
            parents,
            context,
            daily_vfs,
            gate_verifications,
        )
        ready = True
        closure: dict[str, object] = {
            "schema": COLLECTION_SCHEMA,
            "scenario_id": "R13",
            "phase": "closure",
            "status": "READY_FOR_LEAD_REVIEW",
            "ready_for_lead_review": ready,
            "automated_check_results": automated_check_results,
            "automated_checks_passed": automated_checks_passed,
            "manual_assertions_complete": True,
            "manual_assertions_passed": True,
            "scenario_pass_claimed": False,
            "closed_at": _utc_now().isoformat(),
            **context,
            "daily_configuration_final": daily_configuration,
            "daily_vfs_final": daily_vfs,
            "daily_vfs_final_sha256": _object_sha256(daily_vfs),
            "parents": parents,
            "parent_lineage_sha256": _object_sha256(parents),
            "artifact_roles": copied_roles,
            "artifact_roles_sha256": _object_sha256(copied_roles),
            "assertion_manifest": copied_assertion,
            "assertion_manifest_sha256": copied_assertion["sha256"],
            "assertions": assertion_value["assertions"],
            "matrix_blockers": [],
            "claim_limit": (
                "R13 seals only this finite release evidence slice; it never "
                "launches EU4 or closes continuous maintenance obligations."
            ),
            "game_session_created": False,
            "active_lock_created": False,
            "game_started": False,
        }
        closure_path = staging / CLOSURE_NAME
        closure_payload = _json_dump(closure).encode("utf-8")
        if len(closure_payload) > _R13_CLOSURE_MAX_BYTES:
            raise AcceptanceError(
                "R13 closure exceeds the replay-safe serialized size limit: "
                f"{len(closure_payload)} > {_R13_CLOSURE_MAX_BYTES}"
            )
        _exclusive_write_json(closure_path, closure)
        seal = {
            "schema": COLLECTION_SCHEMA,
            "closure_path": str(output_root / CLOSURE_NAME),
            "closure_sha256": _sha256_file(closure_path),
            "parent_lineage_sha256": closure["parent_lineage_sha256"],
            "artifact_roles_sha256": closure["artifact_roles_sha256"],
            "assertion_manifest_sha256": closure["assertion_manifest_sha256"],
            "matrix_sha256": matrix_sha256,
            "candidate_revision": candidate_revision,
            "toolchain_revision": context["toolchain_revision"],
            "sealed_at": _utc_now().isoformat(),
        }
        _exclusive_write_json(staging / CLOSURE_SEAL_NAME, seal)
        _r13_closure_tree_total_bytes(staging, "staged R13 closure output")
        if os.path.lexists(output_root):
            raise AcceptanceError(f"R13 closure output appeared concurrently: {output_root}")
        os.rename(staging, output_root)
        committed = True
    finally:
        if not committed and os.path.lexists(staging):
            if (
                staging.is_dir()
                and not _is_link_or_junction(staging)
                and staging.parent == user_data
            ):
                shutil.rmtree(staging)
            else:
                raise AcceptanceError(f"unsafe R13 staging path remains: {staging}")
    return _verified_release_closure(
        output_root,
        context,
        parents,
        sources,
        assertion_value,
        assertion_source,
        normalized,
        daily_configuration,
        daily_vfs,
        gate_verifications,
    )


def _common_paths(
    parser: argparse.ArgumentParser, user_data_default: Path
) -> None:
    parser.add_argument("--repo", type=Path, default=HELPER_REPO_ROOT)
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
    before_parser.add_argument(
        "--repo", type=Path, default=HELPER_REPO_ROOT
    )
    before_parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    before_parser.add_argument("--permission-reference", required=True)
    before_parser.add_argument("--evidence-root", type=Path)
    before_parser.add_argument("--descriptor", type=Path, action="append", default=[])
    before_parser.add_argument("--input-save", action="append", default=[])
    before_parser.add_argument("--parent-collection", action="append", default=[])

    observe_parser = subparsers.add_parser("observe-process")
    observe_parser.add_argument("session", type=Path)

    abort_parser = subparsers.add_parser("abort-session")
    abort_parser.add_argument("session", type=Path)
    abort_parser.add_argument("--reason", required=True)

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("session", type=Path)
    collect_parser.add_argument("--artifact", type=Path, action="append", default=[])
    collect_parser.add_argument("--evidence-manifest", type=Path, required=True)

    close_parser = subparsers.add_parser("close-release")
    close_parser.add_argument("--repo", type=Path, default=HELPER_REPO_ROOT)
    close_parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    close_parser.add_argument(
        "--daily-user-data", type=Path, default=DEFAULT_USER_DATA
    )
    close_parser.add_argument(
        "--user-data", type=Path, default=DEFAULT_ACCEPTANCE_USER_DATA
    )
    close_parser.add_argument("--parent-collection", action="append", default=[])
    close_parser.add_argument("--artifact", action="append", default=[])
    close_parser.add_argument("--assertion-manifest", type=Path, required=True)
    close_parser.add_argument("--output-root", type=Path)
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
                repo=args.repo,
                game_root=args.game_root,
                permission_reference=args.permission_reference,
                input_saves=args.input_save,
                parent_collections=args.parent_collection,
            )
            success = True
        elif args.command == "observe-process":
            result = observe_process(args.session)
            success = True
        elif args.command == "abort-session":
            result = abort_session(args.session, args.reason)
            success = True
        elif args.command == "collect":
            result, success = collect(
                args.session, args.artifact, args.evidence_manifest
            )
        else:
            result, success = close_release(
                args.repo,
                args.game_root,
                args.daily_user_data,
                args.user_data,
                args.parent_collection,
                args.artifact,
                args.assertion_manifest,
                args.output_root,
            )
    except (AcceptanceError, OSError, json.JSONDecodeError) as exc:
        print(_json_dump({"ok": False, "error": str(exc)}), end="", file=sys.stderr)
        return 2
    print(_json_dump({"ok": success, **result}), end="")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
