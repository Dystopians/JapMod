"""Build and audit a local JXP-safe clone of the Chinese supplementary mod."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
from types import ModuleType
from uuid import uuid4

from .core import CheckResult


JAPANESE_HISTORY_TAGS = frozenset(
    "AKM AKT AMA ANU ASA ASK CBA CSK DTE HJO HSK HTK IKE IMG ISK ITO "
    "KKC KNO KTB MAE MRI ODA OGS OTM OUC RFR RYU SBA SHN SMZ SOO STK "
    "TKD TKG TKI TTI UES UTN YMN".split()
)
COMPAT_DIRECTORY_NAME = "jxp_chinese_sup_compat"
COMPAT_DESCRIPTOR_NAME = "jxp_chinese_sup_compat.mod"
COMPAT_DISPLAY_NAME = "Chinese Language Supplementary Mod for 1.37 - JXP Compatibility"
PINNED_LAUNCHER_SUPPORTED_VERSION = "v1.37.5.0"
EXPECTED_PROVINCE_COLLISIONS = 48
EXPECTED_PATCH_COLLISIONS = 73
EXPECTED_WAR_COLLISIONS = 4
NATIONAL_IDEA_REGISTRY_PATH = "common/ideas/00_country_ideas.txt"
JAPANESE_CULTURE_REGISTRY_PATH = "common/cultures/00_cultures.txt"
PATCHABLE_GAMEPLAY_ROOTS = ("common", "decisions", "events", "history", "missions")
TAG_RE = re.compile(r'^\s*([A-Z0-9]{3})\s*=\s*"([^"]+)"', re.MULTILINE)
DYNAMIC_TOKEN_HOTFIX_PATH = Path(
    "localisation/zz_jxp_chinese_dynamic_token_hotfix_l_english.yml"
)
DYNAMIC_TOKEN_HOTFIX_VALUES = (
    ("vaisyas_influence_modifier", 0, "[Country.GetVaishyasName]\u5f71\u54cd\u529b"),
    ("vaisyas_loyalty_modifier", 1, "[Country.GetVaishyasName]\u5fe0\u8bda\u5747\u8861\u70b9"),
    ("vaisyas_non_muslim_influence_modifier", 0, "[Country.GetVaishyasName]\u5f71\u54cd\u529b"),
    ("vaisyas_non_muslim_loyalty_modifier", 1, "[Country.GetVaishyasName]\u5fe0\u8bda\u5747\u8861\u70b9"),
    ("vaisyas_privilege_slots", 0, "[Country.GetVaishyasName]\u6700\u5927\u7279\u6743\u6570"),
)
DEFAULT_LOCALISATION_ENCODER = (
    Path(__file__).resolve().parents[3]
    / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py"
)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_identity(root: Path, excluded: frozenset[str] = frozenset()) -> dict[str, object]:
    digest = sha256()
    files = 0
    total_bytes = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        payload_hash = _file_sha256(path)
        size = path.stat().st_size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(payload_hash.encode("ascii"))
        digest.update(b"\n")
        files += 1
        total_bytes += size
    return {"files": files, "bytes": total_bytes, "sha256": digest.hexdigest()}


def _load_encoder(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_jxp_gameplay_encoder", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load gameplay encoder: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("decode_gameplay_bytes", "encode_gameplay_text"):
        if not callable(getattr(module, name, None)):
            raise ValueError(f"gameplay encoder lacks {name}: {path}")
    return module


def _load_localisation_encoder(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_jxp_localisation_encoder", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load localisation encoder: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "escape_text", None)):
        raise ValueError(f"localisation encoder lacks escape_text: {path}")
    return module


def _dynamic_token_hotfix_source() -> str:
    lines = ["l_english:"]
    lines.extend(
        f' {key}:{version} "{value}"'
        for key, version, value in DYNAMIC_TOKEN_HOTFIX_VALUES
    )
    return "\n".join(lines) + "\n"


def _dynamic_token_hotfix_payload(encoder: ModuleType) -> bytes:
    return encoder.escape_text(_dynamic_token_hotfix_source()).encode("utf-8-sig")


def _country_paths(game_root: Path) -> dict[str, Path]:
    registrations: dict[str, Path] = {}
    for path in sorted((game_root / "common" / "country_tags").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        for tag, raw in TAG_RE.findall(text):
            if tag in JAPANESE_HISTORY_TAGS:
                relative = Path("common") / Path(raw.replace("/", os.sep))
                if tag in registrations and registrations[tag] != relative:
                    raise ValueError(f"duplicate country registration for {tag}")
                registrations[tag] = relative
    missing = sorted(JAPANESE_HISTORY_TAGS - registrations.keys())
    if missing:
        raise ValueError(f"missing Japanese country registrations: {missing}")
    return registrations


def _history_paths(root: Path) -> dict[str, Path]:
    histories: dict[str, Path] = {}
    directory = root / "history" / "countries"
    for path in sorted(directory.glob("*.txt")):
        tag = path.name[:3]
        if tag not in JAPANESE_HISTORY_TAGS:
            continue
        if tag in histories:
            raise ValueError(f"duplicate Japanese history file for {tag}")
        histories[tag] = path.relative_to(root)
    missing = sorted(JAPANESE_HISTORY_TAGS - histories.keys())
    if missing:
        raise ValueError(f"supplement lacks Japanese histories: {missing}")
    return histories


def _patchable_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for directory in PATCHABLE_GAMEPLAY_ROOTS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            files[path.relative_to(root).as_posix()] = path
    return files


def _patch_sources(
    source: Path, main_mod: Path, map_mod: Path
) -> dict[str, Path]:
    source_files = _patchable_files(source)
    main_files = _patchable_files(main_mod)
    map_files = _patchable_files(map_mod)
    patches = {
        relative: main_files[relative]
        for relative in sorted(source_files.keys() & main_files.keys())
    }
    # The companion owns same-path Japanese province history when both JXP
    # components are enabled, so it is the final authoritative byte source.
    for relative in sorted(source_files.keys() & map_files.keys()):
        patches[relative] = map_files[relative]

    source_provinces = {
        path.name for path in (source / "history" / "provinces").glob("*.txt")
    }
    map_provinces = {
        path.name for path in (map_mod / "history" / "provinces").glob("*.txt")
    }
    collisions = sorted(source_provinces & map_provinces)
    if len(collisions) != EXPECTED_PROVINCE_COLLISIONS:
        raise ValueError(
            "Chinese/JXP province collision count drifted: "
            f"expected {EXPECTED_PROVINCE_COLLISIONS}, found {len(collisions)}"
        )
    map_collision_paths = {f"history/provinces/{name}" for name in collisions}
    if not map_collision_paths <= patches.keys():
        raise ValueError("not every Chinese/map province collision is patched")
    war_collisions = {
        relative for relative in patches if relative.startswith("history/wars/")
    }
    if len(war_collisions) != EXPECTED_WAR_COLLISIONS:
        raise ValueError(
            "Chinese/JXP war collision count drifted: "
            f"expected {EXPECTED_WAR_COLLISIONS}, found {len(war_collisions)}"
        )
    if patches.get(NATIONAL_IDEA_REGISTRY_PATH) != main_files.get(
        NATIONAL_IDEA_REGISTRY_PATH
    ):
        raise ValueError(
            "Chinese/JXP national-idea registry collision is not pinned to "
            f"the main Mod: {NATIONAL_IDEA_REGISTRY_PATH}"
        )
    if patches.get(JAPANESE_CULTURE_REGISTRY_PATH) != main_files.get(
        JAPANESE_CULTURE_REGISTRY_PATH
    ):
        raise ValueError(
            "Chinese/JXP Japanese-culture registry collision is not pinned to "
            f"the main Mod: {JAPANESE_CULTURE_REGISTRY_PATH}"
        )
    if len(patches) != EXPECTED_PATCH_COLLISIONS:
        raise ValueError(f"compatibility patch count drifted: {len(patches)}")
    for relative, path in patches.items():
        if not (source / Path(relative)).is_file() or not path.is_file():
            raise ValueError(f"compatibility patch source is missing: {relative}")
    return dict(sorted(patches.items()))


def _canonicalize(path: Path, encoder: ModuleType) -> bool:
    original = path.read_bytes()
    readable = encoder.decode_gameplay_bytes(original)
    canonical = encoder.encode_gameplay_text(readable)
    path.write_bytes(canonical)
    return canonical != original


def _descriptor_text(inner: bool, target: Path, version: str) -> str:
    fields = [
        f'name="{COMPAT_DISPLAY_NAME}"',
        f'version="{version}-jxp1"',
        'picture="thumbnail.png"',
        'tags={\n\t"Translation"\n}',
        'dependencies={\n\t"Chinese Language Mod for 1.37"\n}',
        f'supported_version="{PINNED_LAUNCHER_SUPPORTED_VERSION}"',
    ]
    if not inner:
        fields.append(f'path="{target.as_posix()}"')
    return "\n".join(fields) + "\n"


def build_compat_clone(
    source: Path,
    target: Path,
    outer_descriptor: Path,
    main_mod: Path,
    map_mod: Path,
    game_root: Path,
    encoder_script: Path,
    localisation_encoder_script: Path | None = None,
) -> dict[str, object]:
    """Atomically clone, patch, and canonicalize the supplementary translation."""

    source = source.resolve()
    target = target.resolve()
    outer_descriptor = outer_descriptor.resolve()
    main_mod = main_mod.resolve()
    map_mod = map_mod.resolve()
    game_root = game_root.resolve()
    encoder_script = encoder_script.resolve()
    localisation_encoder_script = (
        localisation_encoder_script or DEFAULT_LOCALISATION_ENCODER
    ).resolve()
    if target.name != COMPAT_DIRECTORY_NAME:
        raise ValueError(f"unsafe compatibility target: {target}")
    if outer_descriptor.parent != target.parent or outer_descriptor.name != COMPAT_DESCRIPTOR_NAME:
        raise ValueError(f"outer descriptor must sit beside the compatibility clone: {outer_descriptor}")
    if not source.is_dir() or source == target:
        raise ValueError(f"invalid supplementary source: {source}")
    if not main_mod.is_dir() or not map_mod.is_dir() or not game_root.is_dir():
        raise ValueError("main mod, map mod, or game root is missing")

    source_identity_before = _tree_identity(source)
    patches = _patch_sources(source, main_mod, map_mod)
    histories = _history_paths(source)
    countries = _country_paths(game_root)
    encoder = _load_encoder(encoder_script)
    localisation_encoder = _load_localisation_encoder(localisation_encoder_script)
    staging = target.parent / f".{target.name}.staging-{uuid4().hex}"
    backup_root = target.parent / "_jxp_backups"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_backup: Path | None = None
    outer_backup: Path | None = None
    try:
        shutil.copytree(source, staging)
        for relative, authoritative in patches.items():
            destination = staging / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(authoritative, destination)

        changed_histories = sum(
            _canonicalize(staging / relative, encoder)
            for relative in histories.values()
        )
        changed_countries = sum(
            _canonicalize(staging / relative, encoder)
            for relative in countries.values()
        )
        hotfix_path = staging / DYNAMIC_TOKEN_HOTFIX_PATH
        hotfix_path.parent.mkdir(parents=True, exist_ok=True)
        hotfix_payload = _dynamic_token_hotfix_payload(localisation_encoder)
        hotfix_path.write_bytes(hotfix_payload)
        source_descriptor = source / "descriptor.mod"
        source_text = source_descriptor.read_text(encoding="utf-8-sig")
        version_match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', source_text)
        version = version_match.group(1) if version_match else "unknown"
        (staging / "descriptor.mod").write_text(
            _descriptor_text(True, target, version), encoding="utf-8", newline=""
        )
        payload_identity = _tree_identity(
            staging, frozenset({".jxp_compat_manifest.json"})
        )
        manifest = {
            "schema": "jxp_chinese_supplementary_compat/v1",
            "source": str(source),
            "source_identity": source_identity_before,
            "payload_identity": payload_identity,
            "patch_count": len(patches),
            "patched_paths": {
                relative: _file_sha256(authoritative)
                for relative, authoritative in patches.items()
            },
            "canonical_history_files": len(histories),
            "canonical_country_files": len(countries),
            "history_files_rewritten": changed_histories,
            "country_files_rewritten": changed_countries,
            "dynamic_token_hotfix": {
                "path": DYNAMIC_TOKEN_HOTFIX_PATH.as_posix(),
                "keys": [key for key, _version, _value in DYNAMIC_TOKEN_HOTFIX_VALUES],
                "sha256": sha256(hotfix_payload).hexdigest(),
            },
        }
        (staging / ".jxp_compat_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="",
        )

        backup_root.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target_backup = backup_root / f"{target.name}_before_rebuild_{timestamp}"
            target.rename(target_backup)
        staging.rename(target)
        outer_payload = _descriptor_text(False, target, version).encode("utf-8")
        if outer_descriptor.exists():
            outer_backup = backup_root / f"{outer_descriptor.name}.before_rebuild_{timestamp}"
            shutil.copy2(outer_descriptor, outer_backup)
        temporary_outer = outer_descriptor.with_name(
            f".{outer_descriptor.name}.tmp-{uuid4().hex}"
        )
        temporary_outer.write_bytes(outer_payload)
        os.replace(temporary_outer, outer_descriptor)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if target_backup is not None and target_backup.exists() and not target.exists():
            target_backup.rename(target)
        raise

    source_identity_after = _tree_identity(source)
    if source_identity_after != source_identity_before:
        raise ValueError("Workshop source changed while the compatibility clone was built")
    result = audit_compat_clone(
        source,
        target,
        outer_descriptor,
        main_mod,
        map_mod,
        game_root,
        encoder_script,
        localisation_encoder_script,
    )
    if result.issues:
        raise ValueError(result.summary + ": " + "; ".join(i.message for i in result.issues))
    return {
        "target": str(target),
        "outer_descriptor": str(outer_descriptor),
        "target_backup": str(target_backup) if target_backup else None,
        "outer_backup": str(outer_backup) if outer_backup else None,
        "source_identity": source_identity_before,
        "payload_identity": result.metrics["payload_identity"],
        "patch_count": len(patches),
        "canonical_history_files": len(histories),
        "canonical_country_files": len(countries),
        "history_files_rewritten": changed_histories,
        "country_files_rewritten": changed_countries,
        "dynamic_token_hotfix_keys": len(DYNAMIC_TOKEN_HOTFIX_VALUES),
        "audit": result.to_dict(),
    }


def audit_compat_clone(
    source: Path,
    target: Path,
    outer_descriptor: Path,
    main_mod: Path,
    map_mod: Path,
    game_root: Path,
    encoder_script: Path,
    localisation_encoder_script: Path | None = None,
) -> CheckResult:
    result = CheckResult("JXP Chinese supplementary compatibility clone")
    try:
        source = source.resolve()
        target = target.resolve()
        patches = _patch_sources(source, main_mod.resolve(), map_mod.resolve())
        histories = _history_paths(target)
        countries = _country_paths(game_root.resolve())
        encoder = _load_encoder(encoder_script.resolve())
        localisation_encoder = _load_localisation_encoder(
            (localisation_encoder_script or DEFAULT_LOCALISATION_ENCODER).resolve()
        )
        expected_hotfix = _dynamic_token_hotfix_payload(localisation_encoder)
        manifest = json.loads(
            (target / ".jxp_compat_manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        result.add("chinese_compat.read", str(exc), str(target))
        result.summary = "compatibility clone could not be audited"
        return result

    for relative, authoritative in patches.items():
        deployed = target / Path(relative)
        if not deployed.is_file() or deployed.read_bytes() != authoritative.read_bytes():
            result.add(
                "chinese_compat.patch_drift",
                "compatibility clone differs from the authoritative JXP bytes",
                relative,
            )
    noncanonical: list[str] = []
    for relative in (*histories.values(), *countries.values()):
        path = target / relative
        try:
            payload = path.read_bytes()
            canonical = encoder.encode_gameplay_text(
                encoder.decode_gameplay_bytes(payload)
            )
        except (OSError, UnicodeError, ValueError) as exc:
            result.add("chinese_compat.name_decode", str(exc), relative.as_posix())
            continue
        if payload != canonical:
            noncanonical.append(relative.as_posix())
    if noncanonical:
        result.add(
            "chinese_compat.name_noncanonical",
            f"noncanonical Japanese gameplay-name bytes remain: {noncanonical[:8]}",
            str(target),
        )

    hotfix_path = target / DYNAMIC_TOKEN_HOTFIX_PATH
    if not hotfix_path.is_file() or hotfix_path.read_bytes() != expected_hotfix:
        result.add(
            "chinese_compat.dynamic_token_hotfix",
            "the five Vaishya localisation keys do not preserve the ASCII GetVaishyasName token",
            DYNAMIC_TOKEN_HOTFIX_PATH.as_posix(),
        )
    expected_hotfix_manifest = {
        "path": DYNAMIC_TOKEN_HOTFIX_PATH.as_posix(),
        "keys": [key for key, _version, _value in DYNAMIC_TOKEN_HOTFIX_VALUES],
        "sha256": sha256(expected_hotfix).hexdigest(),
    }
    if manifest.get("dynamic_token_hotfix") != expected_hotfix_manifest:
        result.add(
            "chinese_compat.dynamic_token_manifest",
            "dynamic-token hotfix metadata differs from the sealed payload contract",
            str(target / ".jxp_compat_manifest.json"),
        )

    descriptor_text = (target / "descriptor.mod").read_text(encoding="utf-8-sig")
    outer_text = outer_descriptor.read_text(encoding="utf-8-sig")
    if "remote_file_id" in descriptor_text or "remote_file_id" in outer_text:
        result.add(
            "chinese_compat.remote_identity",
            "local compatibility descriptors must not impersonate the Workshop item",
            str(outer_descriptor),
        )
    if f'path="{target.as_posix()}"' not in outer_text:
        result.add(
            "chinese_compat.outer_path",
            "outer descriptor does not point at the compatibility clone",
            str(outer_descriptor),
        )
    source_identity = _tree_identity(source)
    if manifest.get("source_identity") != source_identity:
        result.add(
            "chinese_compat.source_drift",
            "Workshop source changed after the compatibility clone was built",
            str(source),
        )
    payload_identity = _tree_identity(
        target, frozenset({".jxp_compat_manifest.json"})
    )
    if manifest.get("payload_identity") != payload_identity:
        result.add(
            "chinese_compat.payload_drift",
            "compatibility payload differs from its sealed manifest",
            str(target),
        )

    result.metrics.update(
        {
            "patches": len(patches),
            "history_name_files": len(histories),
            "country_name_files": len(countries),
            "payload_identity": payload_identity,
            "source_identity": source_identity,
            "dynamic_token_hotfix_keys": len(DYNAMIC_TOKEN_HOTFIX_VALUES),
        }
    )
    result.summary = (
        f"{len(patches)} order-independent conflict patches; "
        f"{len(histories)} history and {len(countries)} country-name files canonical; "
        f"{len(DYNAMIC_TOKEN_HOTFIX_VALUES)} dynamic-token keys repaired; "
        f"{len(result.issues)} issue(s)"
    )
    return result
