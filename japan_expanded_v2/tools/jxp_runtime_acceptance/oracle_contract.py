"""Strict R12 runtime-oracle contract validation.

This module is deliberately standard-library only.  It does not launch EU4,
write files, or trust working-directory discovery.  The caller supplies the
already-canonical repository and game roots.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Mapping, Sequence


ORACLE_ID = "r12-v1"
ORACLE_SCHEMA = "jxp_runtime_oracle_pack/v1"
ORACLE_RELATIVE_PATH = PurePosixPath(
    "japan_expanded_v2_map/tools/jxp_map_validation/generated/"
    "runtime_oracle_pack.json"
)
MATRIX_SEMANTIC_PATH = "main:tools/jxp_runtime_acceptance/runtime_scenarios.json"
MATRIX_SEMANTIC_PROJECTION = "/scenarios[id=R12]/executable_checklist"
# The Toyotomi succession override deliberately moves ODA country history from
# the vanilla root into the main-mod root while keeping the total at 258 pins.
EXPECTED_SOURCE_COUNTS = {"map": 180, "main": 13, "game": 65}
MAX_ORACLE_PACK_BYTES = 32 * 1024 * 1024
EXPECTED_PACK_KEYS = {
    "counts",
    "event_options",
    "history_contract",
    "history_states",
    "origin_profiles",
    "province_rows",
    "runtime_matrix_semantic_pin",
    "runtime_observation_only",
    "schema",
    "source_pins",
    "unification",
}
EXPECTED_COUNTS = {
    "event_options": 37,
    "history_states": 63,
    "origin_missions": 33,
    "origin_profiles": 5,
    "province_rows": 88,
    "unification_rows": 88,
}
EXPECTED_CASE_TYPE_COUNTS = {
    "rendering_row": 88,
    "bookmark_state": 12,
    "history_boundary_state": 45,
    "non_boundary_slider_state": 6,
    "event_option_result": 37,
    "origin_profile": 5,
    "unification_province": 88,
    "annual_lifecycle": 1,
}
EXPECTED_ASSERTION_BY_CASE_TYPE = {
    "rendering_row": "r12_rendering_and_positions",
    "bookmark_state": "r12_history_boundaries",
    "history_boundary_state": "r12_history_boundaries",
    "non_boundary_slider_state": "r12_history_boundaries",
    "event_option_result": "r12_event_semantics",
    "origin_profile": "r12_origin_identity",
    "unification_province": "r12_unification",
    "annual_lifecycle": "r12_long_reload_stability",
}
EXPECTED_ORIGIN_CASE_IDS = {
    "ANK": "r12_origin_ank_warrior_exclusive",
    "KYO": "r12_origin_kyo_court_exclusive",
    "HNM": "r12_origin_hnm_sea_exclusive",
    "DHO": "r12_origin_dho_frontier_exclusive",
    "TGS": "r12_origin_tgs_temple_market_exclusive",
}
EXPECTED_FOCUS_BY_PROVINCE = {
    "1015": "r12_focus_okinawa",
    "4651": "r12_focus_tsushima",
    "4955": "r12_focus_sado",
    "4959": "r12_focus_oki",
    "4969": "r12_focus_iki",
    "4980": "r12_focus_amami",
    "4981": "r12_focus_sakishima",
}
EXPECTED_CASE_SCHEMA = {
    "required_fields": [
        "case_id",
        "type",
        "assertion_ids",
        "evidence_bindings",
        "expected",
    ],
    "allowed_types": list(EXPECTED_CASE_TYPE_COUNTS),
    "assertion_ids_must_be_session_subset": True,
    "evidence_binding_item_forms": [
        {"required_fields": ["role"], "allowed_fields": ["role"]},
        {
            "required_fields": ["role", "case_id"],
            "allowed_fields": ["role", "case_id"],
        },
    ],
    "expected_required_fields": ["oracle_pack", "pointer"],
    "expected_allowed_fields": ["oracle_pack", "pointer"],
    "expected_must_be_non_empty": True,
}
EXPECTED_LIFECYCLE_KEYS = {
    "r12_first_applicable_annual_legacy",
    "r12_mission_repair_guard",
    "r12_post_tag_idea_sync",
    "r12_startup_geography_and_origin_initialization",
    "r12_twelve_month_reload_stability",
    "r12_unification_day_one_refresh",
    "r12_unification_immediate_refresh",
}
REQUIRED_SOURCE_KEYS = {
    "map:tools/jxp_map_validation/build_runtime_oracles.py",
    "map:tools/validate_all.ps1",
    "map:tools/jxp_map_builder/province_plan.json",
    "map:tools/jxp_map_builder/history_plan.json",
    "main:tools/jxp_validation/clausewitz.py",
    "game:interface/eventpictures.gfx",
}


class OracleContractError(ValueError):
    """Raised when the R12 expected-state proof chain is incomplete or stale."""


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object_sha256(value: object) -> str:
    return sha256(_canonical_json_bytes(value)).hexdigest()


def _strict_json_bytes(payload: bytes, label: str) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8-sig"),
            object_pairs_hook=no_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OracleContractError(f"cannot parse {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise OracleContractError(f"{label} must contain an object")
    return value


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
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return False


def _safe_relative(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise OracleContractError(f"{label} is not a POSIX relative path")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or relative.as_posix() != value
        or ".." in relative.parts
        or any(
            not part or ":" in part or part != part.rstrip(" .")
            for part in relative.parts
        )
    ):
        raise OracleContractError(f"{label} is unsafe: {value!r}")
    return relative


def _ordinary_file_under(root: Path, relative: PurePosixPath, label: str) -> Path:
    root = root.resolve()
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if os.path.lexists(candidate) and _is_link_or_junction(candidate):
            raise OracleContractError(f"{label} traverses a link or junction: {candidate}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise OracleContractError(f"{label} is absent or escaped its root: {candidate}") from exc
    if not resolved.is_file() or _is_link_or_junction(resolved):
        raise OracleContractError(f"{label} is not an ordinary file: {resolved}")
    return resolved


def _stable_file_bytes(path: Path, label: str) -> bytes:
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    identity = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if (
        _is_link_or_junction(path)
        or any(getattr(before, key) != getattr(after, key) for key in identity)
        or len(payload) != before.st_size
    ):
        raise OracleContractError(f"{label} changed while being read: {path}")
    return payload


def _stable_file_sha256(path: Path, label: str) -> str:
    before = path.stat()
    digest = sha256()
    observed = 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            observed += len(chunk)
        opened_after = os.fstat(stream.fileno())
    after = path.stat()
    identity = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if (
        _is_link_or_junction(path)
        or any(getattr(opened, key) != getattr(before, key) for key in identity)
        or any(getattr(opened_after, key) != getattr(opened, key) for key in identity)
        or any(getattr(after, key) != getattr(before, key) for key in identity)
        or observed != before.st_size
    ):
        raise OracleContractError(f"{label} changed while being hashed: {path}")
    return digest.hexdigest()


def _json_pointer(value: object, pointer: object) -> object:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise OracleContractError(f"oracle pointer is not absolute: {pointer!r}")
    current = value
    for raw_token in pointer.split("/")[1:]:
        if re.search(r"~(?![01])", raw_token):
            raise OracleContractError(f"oracle pointer has invalid escaping: {pointer}")
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise OracleContractError(f"oracle pointer does not resolve: {pointer}")
        current = current[token]
    return current


def _source_pin_path(
    key: str, repo_root: Path, game_root: Path
) -> tuple[Path, PurePosixPath]:
    if ":" not in key:
        raise OracleContractError(f"source pin lacks a root label: {key!r}")
    label, raw_relative = key.split(":", 1)
    roots = {
        "map": repo_root / "japan_expanded_v2_map",
        "main": repo_root / "japan_expanded_v2",
        "game": game_root,
    }
    if label not in roots:
        raise OracleContractError(f"source pin uses an unknown root: {key!r}")
    return roots[label], _safe_relative(raw_relative, f"source pin {key}")


def _verify_source_pins(
    source_pins: Mapping[str, object], repo_root: Path, game_root: Path
) -> None:
    prefix_counts = Counter(key.split(":", 1)[0] for key in source_pins)
    if dict(prefix_counts) != EXPECTED_SOURCE_COUNTS:
        raise OracleContractError(
            f"oracle source-pin root counts disagree: {dict(prefix_counts)}"
        )
    for key, expected in source_pins.items():
        root, relative = _source_pin_path(key, repo_root, game_root)
        path = _ordinary_file_under(root, relative, f"oracle source pin {key}")
        if _stable_file_sha256(path, f"oracle source pin {key}") != expected:
            raise OracleContractError(f"oracle source pin SHA-256 disagrees: {key}")


def _validate_pack_shape(pack: dict[str, object]) -> None:
    if set(pack) != EXPECTED_PACK_KEYS or pack.get("schema") != ORACLE_SCHEMA:
        raise OracleContractError("runtime oracle pack schema/key set disagrees")
    if pack.get("counts") != EXPECTED_COUNTS:
        raise OracleContractError("runtime oracle pack count contract disagrees")
    expected_maps = {
        "province_rows": 88,
        "history_states": 63,
        "event_options": 37,
        "origin_profiles": 5,
    }
    for key, expected_count in expected_maps.items():
        value = pack.get(key)
        if not isinstance(value, dict) or len(value) != expected_count:
            raise OracleContractError(f"oracle {key} cardinality disagrees")
    unification = pack.get("unification")
    if not isinstance(unification, dict):
        raise OracleContractError("oracle unification object is missing")
    province_rows = unification.get("province_rows")
    lifecycle = unification.get("lifecycle")
    if not isinstance(province_rows, dict) or len(province_rows) != 88:
        raise OracleContractError("oracle unification province rows disagree")
    if not isinstance(lifecycle, dict) or set(lifecycle) != EXPECTED_LIFECYCLE_KEYS:
        raise OracleContractError("oracle lifecycle key coverage disagrees")
    for key, row in pack["province_rows"].items():
        if not isinstance(row, dict) or str(row.get("id")) != key:
            raise OracleContractError(f"province oracle key/id disagrees: {key}")
    for key, row in pack["history_states"].items():
        if not isinstance(row, dict) or row.get("case_id") != key:
            raise OracleContractError(f"history oracle key/case_id disagrees: {key}")
        sealed = row.get("state_sha256")
        payload = {name: value for name, value in row.items() if name != "state_sha256"}
        if sealed != _object_sha256(payload):
            raise OracleContractError(f"history oracle state hash disagrees: {key}")
    for key, row in pack["event_options"].items():
        if (
            not isinstance(row, dict)
            or row.get("option_key") != key
            or row.get("effect_sha256") != _object_sha256(row.get("script"))
        ):
            raise OracleContractError(f"event oracle identity/effect hash disagrees: {key}")
    for key, profile in pack["origin_profiles"].items():
        if not isinstance(profile, dict) or profile.get("representative_tag") != key:
            raise OracleContractError(f"origin oracle key/tag disagrees: {key}")
        missions = profile.get("missions")
        if not isinstance(missions, dict):
            raise OracleContractError(f"origin oracle missions are malformed: {key}")
        for mission_id, mission in missions.items():
            if (
                not isinstance(mission, dict)
                or mission.get("mission_id") != mission_id
                or mission.get("effect_sha256")
                != _object_sha256(mission.get("effect"))
            ):
                raise OracleContractError(
                    f"origin mission identity/effect hash disagrees: {mission_id}"
                )
    for key, row in province_rows.items():
        if not isinstance(row, dict) or str(row.get("province_id")) != key:
            raise OracleContractError(f"unification oracle key/province_id disagrees: {key}")
    for key, row in lifecycle.items():
        if not isinstance(row, dict) or row.get("case_id") != key:
            raise OracleContractError(f"lifecycle oracle key/case_id disagrees: {key}")
    source_effect = unification.get("source_effect")
    if (
        not isinstance(source_effect, dict)
        or source_effect.get("sha256") != _object_sha256(source_effect.get("ast"))
    ):
        raise OracleContractError("unification source-effect hash disagrees")


def _validate_semantic_pin(pack: dict[str, object], scenario: Mapping[str, object]) -> None:
    checklist = scenario.get("executable_checklist")
    expected = {
        "path": MATRIX_SEMANTIC_PATH,
        "projection": MATRIX_SEMANTIC_PROJECTION,
        "sha256": _object_sha256(checklist),
    }
    if not isinstance(checklist, dict) or pack.get("runtime_matrix_semantic_pin") != expected:
        raise OracleContractError("oracle pack R12 executable-checklist semantic pin disagrees")


def _validate_source_pin_manifest(source_pins: object) -> Mapping[str, object]:
    if (
        not isinstance(source_pins, dict)
        or len(source_pins) != sum(EXPECTED_SOURCE_COUNTS.values())
        or list(source_pins) != sorted(source_pins)
        or not REQUIRED_SOURCE_KEYS.issubset(source_pins)
    ):
        raise OracleContractError("oracle source-pin manifest coverage/order disagrees")
    for key, digest in source_pins.items():
        if (
            not isinstance(key, str)
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise OracleContractError(f"oracle source pin is malformed: {key!r}")
        _source_pin_path(key, Path("."), Path("."))
    return source_pins


def _verify_referenced_sources(pack: object, source_pins: Mapping[str, object]) -> None:
    referenced: set[str] = set()

    def walk(value: object, *, semantic_pin: bool = False) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, semantic_pin=semantic_pin or key == "runtime_matrix_semantic_pin")
        elif isinstance(value, list):
            for item in value:
                walk(item, semantic_pin=semantic_pin)
        elif (
            not semantic_pin
            and isinstance(value, str)
            and re.match(r"^(?:game|main|map|repo):", value)
        ):
            referenced.add(value)

    walk(pack)
    missing = referenced - set(source_pins)
    if missing:
        raise OracleContractError(
            f"oracle references sources absent from source_pins: {sorted(missing)[:5]}"
        )


def _validate_case_bindings(
    case: Mapping[str, object],
    artifact_specs: Mapping[str, Mapping[str, object]],
) -> None:
    assertion_ids = case["assertion_ids"]
    bindings = case["evidence_bindings"]
    if not isinstance(bindings, list) or not bindings:
        raise OracleContractError(f"typed case has no evidence bindings: {case['case_id']}")
    identities: set[tuple[str, str | None]] = set()
    saw_non_screenshot = False
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) not in ({"role"}, {"role", "case_id"}):
            raise OracleContractError(f"typed case evidence binding schema disagrees: {binding!r}")
        role = binding.get("role")
        if not isinstance(role, str) or role not in artifact_specs:
            raise OracleContractError(f"typed case names an unknown evidence role: {role!r}")
        spec = artifact_specs[role]
        supports = spec.get("supports_assertion_ids")
        if not isinstance(supports, list) or not set(assertion_ids).issubset(supports):
            raise OracleContractError(f"typed case evidence role does not support its assertion: {role}")
        evidence_case = binding.get("case_id")
        kind = spec.get("kind")
        if evidence_case is None:
            if kind == "screenshot_set":
                raise OracleContractError(f"screenshot-set binding lacks a case id: {role}")
            saw_non_screenshot = True
        elif (
            not isinstance(evidence_case, str)
            or kind != "screenshot_set"
            or evidence_case not in spec.get("case_ids", [])
        ):
            raise OracleContractError(f"typed screenshot evidence case disagrees: {binding!r}")
        identity = (role, evidence_case if isinstance(evidence_case, str) else None)
        if identity in identities:
            raise OracleContractError(f"typed case repeats an evidence binding: {identity}")
        identities.add(identity)
    if not saw_non_screenshot:
        raise OracleContractError(f"typed case lacks checklist/save/log evidence: {case['case_id']}")


def _expected_case_bindings(
    case_type: str, pointer: str, resolved: Mapping[str, object]
) -> list[dict[str, str]]:
    if case_type == "rendering_row":
        bindings = [
            {"role": "r12_ports_straits_positions_checklist"},
            {
                "role": "r12_full_map_rendering_screenshot_set",
                "case_id": "r12_japan_region_full_map",
            },
        ]
        province = pointer.rsplit("/", 1)[-1]
        focus = EXPECTED_FOCUS_BY_PROVINCE.get(province)
        if focus is not None:
            bindings.append(
                {"role": "r12_island_focus_screenshot_set", "case_id": focus}
            )
        return bindings
    if case_type == "bookmark_state":
        case_id = str(resolved["case_id"])
        return [
            {"role": "r12_history_state_checklist"},
            {"role": "r12_bookmark_screenshot_set", "case_id": case_id},
        ]
    if case_type == "history_boundary_state":
        case_id = str(resolved["case_id"])
        return [
            {"role": "r12_history_state_checklist"},
            {"role": "r12_boundary_screenshot_set", "case_id": case_id},
        ]
    if case_type == "non_boundary_slider_state":
        case_id = str(resolved["case_id"])
        return [
            {"role": "r12_history_state_checklist"},
            {"role": "r12_random_slider_screenshot_set", "case_id": case_id},
        ]
    if case_type == "event_option_result":
        case_id = "r12_event_" + str(resolved["option_key"]).replace(".", "_")
        return [
            {"role": "r12_event_option_checklist"},
            {"role": "r12_event_option_screenshot_set", "case_id": case_id},
        ]
    if case_type == "origin_profile":
        tag = str(resolved["representative_tag"])
        return [
            {"role": "r12_origin_identity_checklist"},
            {
                "role": "r12_origin_exclusivity_screenshot_set",
                "case_id": EXPECTED_ORIGIN_CASE_IDS[tag],
            },
            *[
                {
                    "role": "r12_origin_chain_completion_screenshot_set",
                    "case_id": f"r12_{mission}",
                }
                for mission in resolved["missions"]
            ],
        ]
    if case_type == "unification_province":
        return [
            {"role": "r12_unification_88_province_checklist"},
            {"role": "r12_unification_before_save"},
            {"role": "r12_unification_after_save"},
        ]
    if case_type == "annual_lifecycle":
        return [
            {"role": "r12_unification_88_province_checklist"},
            {"role": "r12_unification_before_save"},
            {"role": "r12_unification_after_save"},
            {"role": "r12_post_annual_tick_reload_save"},
            {"role": "r12_annual_timeline"},
            {"role": "r12_error_log"},
            {"role": "r12_game_log"},
        ]
    raise OracleContractError(f"unknown typed-case binding type: {case_type}")


def _validate_typed_cases(
    scenario: Mapping[str, object],
    pack: dict[str, object],
    artifact_specs: Mapping[str, Mapping[str, object]],
    session_assertion_ids: Sequence[str],
) -> tuple[str, str, dict[str, dict[str, object]]]:
    if scenario.get("typed_case_schema") != EXPECTED_CASE_SCHEMA:
        raise OracleContractError("R12 typed-case schema disagrees")
    cases = scenario.get("typed_cases")
    if not isinstance(cases, list) or len(cases) != 282:
        raise OracleContractError("R12 must define exactly 282 typed cases")
    case_ids: set[str] = set()
    pointers: set[str] = set()
    type_counts: Counter[str] = Counter()
    used_roles: set[str] = set()
    used_screenshot_cases: dict[str, set[str]] = {}
    pointers_by_type: dict[str, set[str]] = {
        key: set() for key in EXPECTED_CASE_TYPE_COUNTS
    }
    assertions = set(session_assertion_ids)
    case_contracts: dict[str, dict[str, object]] = {}
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "case_id",
            "type",
            "assertion_ids",
            "evidence_bindings",
            "expected",
        }:
            raise OracleContractError("typed-case field set disagrees")
        case_id = case.get("case_id")
        case_type = case.get("type")
        case_assertions = case.get("assertion_ids")
        expected = case.get("expected")
        if (
            not isinstance(case_id, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_]{2,95}", case_id)
            or case_id in case_ids
            or case_type not in EXPECTED_CASE_TYPE_COUNTS
            or not isinstance(case_assertions, list)
            or not case_assertions
            or len(case_assertions) != len(set(case_assertions))
            or not all(isinstance(item, str) for item in case_assertions)
            or not set(case_assertions).issubset(assertions)
            or not isinstance(expected, dict)
            or set(expected) != {"oracle_pack", "pointer"}
            or expected.get("oracle_pack") != ORACLE_ID
        ):
            raise OracleContractError(f"typed-case identity/assertion/expected schema disagrees: {case_id!r}")
        pointer = expected.get("pointer")
        if not isinstance(pointer, str) or pointer in pointers:
            raise OracleContractError(f"typed-case oracle pointer is invalid or repeated: {pointer!r}")
        resolved = _json_pointer(pack, pointer)
        if not isinstance(resolved, dict) or not resolved:
            raise OracleContractError(f"typed-case oracle is empty or not an object: {pointer}")
        if case_assertions != [EXPECTED_ASSERTION_BY_CASE_TYPE[case_type]]:
            raise OracleContractError(
                f"typed-case assertion mapping disagrees: {case_id}"
            )
        _validate_case_bindings(case, artifact_specs)
        expected_bindings = _expected_case_bindings(case_type, pointer, resolved)
        binding_identity = {
            (str(binding["role"]), binding.get("case_id"))
            for binding in case["evidence_bindings"]
        }
        expected_binding_identity = {
            (str(binding["role"]), binding.get("case_id"))
            for binding in expected_bindings
        }
        if binding_identity != expected_binding_identity:
            raise OracleContractError(
                f"typed-case exact evidence bindings disagree: {case_id}"
            )
        for binding in case["evidence_bindings"]:
            role = binding["role"]
            used_roles.add(role)
            if "case_id" in binding:
                used_screenshot_cases.setdefault(role, set()).add(binding["case_id"])
        case_ids.add(case_id)
        pointers.add(pointer)
        type_counts[case_type] += 1
        pointers_by_type[case_type].add(pointer)
        case_contracts[case_id] = {
            "type": case_type,
            "assertion_ids": list(case_assertions),
            "evidence_bindings": list(case["evidence_bindings"]),
            "pointer": pointer,
            "oracle_object_sha256": _object_sha256(resolved),
        }

    if dict(type_counts) != EXPECTED_CASE_TYPE_COUNTS:
        raise OracleContractError(f"R12 typed-case type counts disagree: {dict(type_counts)}")
    if used_roles != set(artifact_specs):
        raise OracleContractError("R12 typed cases do not bind every required artifact role")
    for role, spec in artifact_specs.items():
        if spec.get("kind") == "screenshot_set" and used_screenshot_cases.get(role, set()) != set(spec.get("case_ids", [])):
            raise OracleContractError(f"R12 typed cases do not cover screenshot-set cases: {role}")

    expected_pointer_sets = {
        "rendering_row": {f"/province_rows/{key}" for key in pack["province_rows"]},
        "event_option_result": {f"/event_options/{key}" for key in pack["event_options"]},
        "origin_profile": {f"/origin_profiles/{key}" for key in pack["origin_profiles"]},
        "unification_province": {
            f"/unification/province_rows/{key}"
            for key in pack["unification"]["province_rows"]
        },
        "annual_lifecycle": {"/unification/lifecycle"},
    }
    history_by_type: dict[str, set[str]] = {
        "bookmark_state": set(),
        "history_boundary_state": set(),
        "non_boundary_slider_state": set(),
    }
    for key, value in pack["history_states"].items():
        if not isinstance(value, dict):
            raise OracleContractError(f"history oracle row is malformed: {key}")
        sample_kind = value.get("sample_kind")
        if sample_kind == "bookmark":
            target_type = "bookmark_state"
        elif isinstance(sample_kind, str) and sample_kind.startswith("boundary_"):
            target_type = "history_boundary_state"
        elif sample_kind == "non_boundary_slider":
            target_type = "non_boundary_slider_state"
        else:
            raise OracleContractError(f"history oracle sample kind is unknown: {sample_kind!r}")
        history_by_type[target_type].add(f"/history_states/{key}")
    expected_pointer_sets.update(history_by_type)
    for case_type, expected_pointers in expected_pointer_sets.items():
        if pointers_by_type[case_type] != expected_pointers:
            raise OracleContractError(f"typed-case oracle coverage disagrees: {case_type}")

    for case in cases:
        pointer = case["expected"]["pointer"]
        resolved = _json_pointer(pack, pointer)
        if case["type"] in {"bookmark_state", "history_boundary_state", "non_boundary_slider_state"} and resolved.get("case_id") != case["case_id"]:
            raise OracleContractError(f"history case id disagrees with its oracle: {case['case_id']}")
        if case["type"] == "origin_profile":
            tag = str(resolved.get("representative_tag", ""))
            if case["case_id"] != EXPECTED_ORIGIN_CASE_IDS.get(tag):
                raise OracleContractError(
                    f"origin case id disagrees with its oracle: {case['case_id']}"
                )
            mission_cases = {
                binding["case_id"]
                for binding in case["evidence_bindings"]
                if binding["role"] == "r12_origin_chain_completion_screenshot_set"
            }
            expected_missions = {f"r12_{mission}" for mission in resolved.get("missions", {})}
            if mission_cases != expected_missions:
                raise OracleContractError(f"origin mission evidence coverage disagrees: {case['case_id']}")
        elif case["type"] == "rendering_row" and case["case_id"] != f"r12_rendering_province_{resolved.get('id')}":
            raise OracleContractError(
                f"rendering case id disagrees with its oracle: {case['case_id']}"
            )
        elif case["type"] == "event_option_result" and case["case_id"] != (
            "r12_event_" + str(resolved.get("option_key", "")).replace(".", "_")
        ):
            raise OracleContractError(
                f"event case id disagrees with its oracle: {case['case_id']}"
            )
        elif case["type"] == "unification_province" and case["case_id"] != f"r12_unification_province_{resolved.get('province_id')}":
            raise OracleContractError(
                f"unification case id disagrees with its oracle: {case['case_id']}"
            )
        elif case["type"] == "annual_lifecycle" and case["case_id"] != "r12_twelve_month_reload_stability":
            raise OracleContractError("annual lifecycle case id disagrees")
    return _object_sha256(cases), _object_sha256(
        {case["case_id"]: _json_pointer(pack, case["expected"]["pointer"]) for case in cases}
    ), case_contracts


def verify_runtime_oracle(
    scenario: Mapping[str, object],
    artifact_specs: Mapping[str, Mapping[str, object]],
    session_assertion_ids: Sequence[str],
    repo_root: Path,
    game_root: Path,
    *,
    verify_sources: bool,
) -> dict[str, object]:
    """Verify the fixed pack, typed cases, evidence bindings, and optional sources."""

    if scenario.get("id") != "R12":
        raise OracleContractError("runtime oracle validation is defined only for R12")
    metadata = scenario.get("exact_oracle")
    if not isinstance(metadata, dict) or set(metadata) != {
        "id",
        "repo_relative_path",
        "schema",
        "sha256",
    }:
        raise OracleContractError("R12 exact_oracle metadata schema disagrees")
    expected_metadata = {
        "id": ORACLE_ID,
        "repo_relative_path": ORACLE_RELATIVE_PATH.as_posix(),
        "schema": ORACLE_SCHEMA,
    }
    if any(metadata.get(key) != value for key, value in expected_metadata.items()):
        raise OracleContractError("R12 exact_oracle identity/path/schema disagrees")
    expected_sha256 = metadata.get("sha256")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise OracleContractError("R12 exact_oracle SHA-256 is malformed")
    pack_path = _ordinary_file_under(
        repo_root, ORACLE_RELATIVE_PATH, "runtime oracle pack"
    )
    payload = _stable_file_bytes(pack_path, "runtime oracle pack")
    if not payload or len(payload) > MAX_ORACLE_PACK_BYTES:
        raise OracleContractError("runtime oracle pack size is unsafe")
    actual_sha256 = sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise OracleContractError("runtime oracle pack SHA-256 disagrees with R12 metadata")
    pack = _strict_json_bytes(payload, "runtime oracle pack")
    _validate_pack_shape(pack)
    _validate_semantic_pin(pack, scenario)
    source_pins = _validate_source_pin_manifest(pack.get("source_pins"))
    typed_cases_sha256, expected_objects_sha256, case_contracts = _validate_typed_cases(
        scenario, pack, artifact_specs, session_assertion_ids
    )
    _verify_referenced_sources(pack, source_pins)
    if verify_sources:
        _verify_source_pins(source_pins, repo_root.resolve(), game_root.resolve())
    return {
        "id": ORACLE_ID,
        "schema": ORACLE_SCHEMA,
        "path": str(pack_path),
        "sha256": actual_sha256,
        "runtime_matrix_semantic_pin": pack["runtime_matrix_semantic_pin"],
        "source_pin_count": len(source_pins),
        "source_pins_sha256": _object_sha256(source_pins),
        "source_pins": dict(source_pins),
        "typed_case_count": 282,
        "typed_cases_sha256": typed_cases_sha256,
        "expected_objects_sha256": expected_objects_sha256,
        "case_contracts": case_contracts,
        "sources_verified": verify_sources,
    }
