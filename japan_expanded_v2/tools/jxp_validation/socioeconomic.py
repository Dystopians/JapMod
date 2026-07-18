"""Validate Agent A's Japanese estate and socioeconomic reconstruction."""

from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from .clausewitz import Object, Scalar, first_scalar
from .core import CheckResult, ValidationContext
from .missions import MISSION_SERIES_METADATA


PLAN_PATH = Path("tools/jxp_a_socioeconomic_builder/socioeconomic_plan.json")
FROZEN_MISSION_PATH = Path("tools/jxp_a_socioeconomic_builder/frozen_mission_surface.json")
BUILDER_PATHS = (
    Path("tools/jxp_a_socioeconomic_builder/build_estates.py"),
    Path("tools/jxp_a_socioeconomic_builder/build_economy.py"),
    Path("tools/jxp_a_socioeconomic_builder/build_missions_routes.py"),
    Path("tools/jxp_a_socioeconomic_builder/build_integration.py"),
    Path("tools/jxp_a_socioeconomic_builder/build_socioeconomic_system.py"),
)

INTEGRATION_PATHS = (
    Path("common/scripted_triggers/jxp_a_106_socioeconomic_integration_triggers.txt"),
    Path("common/scripted_effects/jxp_a_106_socioeconomic_integration_effects.txt"),
    Path("common/on_actions/jxp_a_106_socioeconomic_integration_on_actions.txt"),
    Path("events/jxp_a_106_socioeconomic_integration_events.txt"),
    Path("decisions/jxp_a_106_socioeconomic_guide_decisions.txt"),
)

SOURCE_LOC_PATTERNS = (
    "jxp_85_ui_flag_labels_l_english_utf8_source.yml",
    "jxp_a_10*_l_english_utf8_source.yml",
    "jxp_a_11*_l_english_utf8_source.yml",
    "zzz_jxp_a_105*_l_english_utf8_source.yml",
)
LOCALISATION_KEY_PATTERN = re.compile(r"(?m)^\s*([A-Za-z0-9_.-]+):\d+\s")

REQUIRED_MARKET_EFFECTS = (
    "jxp_a_set_market_stage_1",
    "jxp_a_set_market_stage_2",
    "jxp_a_set_market_stage_3",
    "jxp_a_set_market_stage_4",
    "jxp_a_clear_illegal_market_stages",
    "jxp_a_reconcile_market_stage",
)
REQUIRED_COMPANY_EFFECTS = (
    "jxp_a_initialize_company_core_effect",
    "jxp_a_reconcile_companies_effect",
    "jxp_a_company_full_cleanup_effect",
    "jxp_a_company_annual_pulse_effect",
    "jxp_a_reconcile_company_interfaces_effect",
)
REQUIRED_ESTATE_EFFECTS = (
    "jxp_a_reconcile_japanese_estates_effect",
    "jxp_a_clear_japanese_estates_effect",
    "jxp_a_clear_illegal_japanese_estate_privileges_effect",
)
REQUIRED_MISSION_EFFECTS = (
    "jxp_a_105_capture_legacy_mission_progress_effect",
    "jxp_a_105_replay_mission_progress_effect",
    "jxp_a_105_reconcile_mission_profile_effect",
    "jxp_a_105_migrate_mission_schema_effect",
)
REQUIRED_DISASTERS = (
    "jxp_a_household_particularism",
    "jxp_a_religious_diet_collapse",
    "jxp_a_merchant_oligarchy",
    "jxp_a_tokusei_communal_rising",
)
COMPANY_FLAGS = (
    "jxp_a_company_mining_chartered",
    "jxp_a_company_shipping_chartered",
    "jxp_a_company_rice_credit_chartered",
    "jxp_a_company_textile_chartered",
    "jxp_a_company_armaments_chartered",
)


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        # The three pinned 1.37.5 estate overrides preserve Paradox's legacy
        # single-byte comments exactly.  Their executable tokens are ASCII.
        return path.read_text(encoding="latin-1")


def _all_new_script_text(mod_root: Path) -> str:
    selected: list[Path] = []
    for root_name in ("common", "decisions", "events", "missions"):
        root = mod_root / root_name
        if not root.is_dir():
            continue
        selected.extend(
            path
            for path in root.rglob("*.txt")
            if re.search(r"jxp_a_(?:10[3-6]|11[0-4])", path.name)
            or path.name.startswith("zzz_jxp_a_105")
        )
    return "\n".join(_read_text(path) for path in sorted(set(selected)))


def _top_level_prefixed_keys(context: ValidationContext, directory: str, prefix: str) -> set[str]:
    keys: set[str] = set()
    root = context.mod_root / directory
    if not root.is_dir():
        return keys
    for path in root.glob("*.txt"):
        document = context.document(path)
        if document is None:
            continue
        keys.update(
            entry.key
            for entry in document.root.entries
            if entry.key is not None
            and entry.key.startswith(prefix)
            and isinstance(entry.value, Object)
        )
    return keys


def _mission_counts(
    context: ValidationContext,
) -> tuple[
    int,
    Counter[str],
    Counter[tuple[str, int]],
    Counter[int],
    set[str],
    Counter[str],
]:
    plan = _load_json(context.mod_root / PLAN_PATH)
    profile_keys = tuple(
        str(record["key"])
        for record in plan.get("profiles", [])
        if isinstance(record, dict) and "key" in record
    )
    total = 0
    per_profile: Counter[str] = Counter()
    per_profile_slot: Counter[tuple[str, int]] = Counter()
    shared_per_slot: Counter[int] = Counter()
    mission_ids: set[str] = set()
    generated_path = context.mod_root / "missions/zzz_jxp_a_105_socioeconomic_missions.txt"
    document = context.document(generated_path) if generated_path.is_file() else None
    if document is not None:
        for series_entry in document.root.entries:
            if series_entry.key is None or not isinstance(series_entry.value, Object):
                continue
            body = series_entry.value
            slot_text = first_scalar(body, "slot")
            if slot_text not in {"1", "2", "3"}:
                continue
            slot = int(slot_text)
            series = series_entry.key
            profile: str | None = None
            if series.startswith("jxp_a_105_commercial_council_slot_"):
                profile = "commercial_council"
            else:
                match = re.fullmatch(r"jxp_a_105_([a-z_]+)_domestic_missions", series)
                if match is not None and match.group(1) in profile_keys:
                    profile = match.group(1)
            for entry in body.entries:
                if (
                    entry.key is None
                    or entry.key in MISSION_SERIES_METADATA
                    or not isinstance(entry.value, Object)
                ):
                    continue
                total += 1
                mission_ids.add(entry.key)
                if series.startswith("jxp_a_105_shared_capital_slot_"):
                    shared_per_slot[slot] += 1
                elif profile is not None:
                    per_profile[profile] += 1
                    per_profile_slot[(profile, slot)] += 1

    global_id_counts: Counter[str] = Counter()
    for path in (context.mod_root / "missions").glob("*.txt"):
        document = context.document(path)
        if document is None:
            continue
        for series_entry in document.root.entries:
            if series_entry.key is None or not isinstance(series_entry.value, Object):
                continue
            body = series_entry.value
            for entry in body.entries:
                if (
                    entry.key is None
                    or entry.key in MISSION_SERIES_METADATA
                    or not isinstance(entry.value, Object)
                ):
                    continue
                if entry.key in mission_ids:
                    global_id_counts[entry.key] += 1
    return (
        total,
        per_profile,
        per_profile_slot,
        shared_per_slot,
        mission_ids,
        global_id_counts,
    )


def _top_level_block_bytes(data: bytes, key: str) -> bytes | None:
    match = re.search(
        rb"(?m)^" + re.escape(key.encode("ascii")) + rb"[ \t]*=[ \t]*\{",
        data,
    )
    if match is None:
        return None
    brace = data.find(b"{", match.start())
    depth = 0
    quoted = False
    escaped = False
    comment = False
    for index in range(brace, len(data)):
        byte = data[index]
        if comment:
            if byte in (10, 13):
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
            continue
        if byte == 35:
            comment = True
        elif byte == 34:
            quoted = True
        elif byte == 123:
            depth += 1
        elif byte == 125:
            depth -= 1
            if depth == 0:
                end = index + 1
                if data[end : end + 2] == b"\r\n":
                    end += 2
                elif data[end : end + 1] == b"\n":
                    end += 1
                return data[match.start() : end]
    return None


def _localisation_keys(mod_root: Path) -> set[str]:
    keys: set[str] = set()
    source_root = mod_root / "localisation_source"
    for pattern in SOURCE_LOC_PATTERNS:
        for path in source_root.glob(pattern):
            keys.update(LOCALISATION_KEY_PATTERN.findall(_read_text(path)))
    return keys


def _top_level_text_block(text: str, key: str) -> str:
    """Return a simple top-level generated block, or an empty string."""

    marker = f"\n{key} = {{"
    start = text.find(marker)
    if start >= 0:
        start += 1
    elif text.startswith(f"{key} = {{"):
        start = 0
    else:
        return ""
    brace = text.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    quoted = False
    escaped = False
    comment = False
    for index in range(brace, len(text)):
        char = text[index]
        if comment:
            if char in "\r\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def _audit_localisation_mirrors(mod_root: Path, result: CheckResult) -> None:
    source_root = mod_root / "localisation_source"
    active_root = mod_root / "localisation"
    escape_path = (
        mod_root.parent
        / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py"
    )
    try:
        spec = importlib.util.spec_from_file_location(
            "jxp_socioeconomic_escape", escape_path
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {escape_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        escape_text = module.escape_text
    except (OSError, ImportError, AttributeError) as exc:
        result.add(
            "socioeconomic.localisation_escaper",
            f"cannot load canonical localisation escaper: {exc}",
        )
        return

    sources = sorted(
        {
            path
            for pattern in SOURCE_LOC_PATTERNS
            for path in source_root.glob(pattern)
        }
    )
    for source in sources:
        active_name = source.name.replace("_utf8_source", "")
        active = active_root / active_name
        if not active.is_file():
            result.add(
                "socioeconomic.localisation_active_missing",
                f"active localisation mirror is missing for {source.name}",
                source.relative_to(mod_root).as_posix(),
            )
            continue
        payload = active.read_bytes()
        if not payload.startswith(b"\xef\xbb\xbf"):
            result.add(
                "socioeconomic.localisation_bom",
                f"{active.name} is not UTF-8 BOM encoded",
                active.relative_to(mod_root).as_posix(),
            )
            continue
        expected = escape_text(_read_text(source)).encode("utf-8-sig")
        if payload != expected:
            result.add(
                "socioeconomic.localisation_drift",
                f"{active.name} is not the exact escaped mirror of its readable source",
                active.relative_to(mod_root).as_posix(),
            )


def check_socioeconomic_system(context: ValidationContext) -> CheckResult:
    result = CheckResult("Agent A socioeconomic reconstruction")
    plan_file = context.mod_root / PLAN_PATH
    frozen_file = context.mod_root / FROZEN_MISSION_PATH
    if not plan_file.is_file() or not frozen_file.is_file():
        result.add(
            "socioeconomic.authority_missing",
            "socioeconomic plan or frozen mission manifest is missing",
        )
        result.summary = "authority files missing"
        return result

    try:
        plan = _load_json(plan_file)
        frozen = _load_json(frozen_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result.add("socioeconomic.authority_invalid", str(exc))
        result.summary = "authority files invalid"
        return result

    mission_contract = plan.get("mission_contract")
    if not isinstance(mission_contract, dict) or mission_contract != {
        "agent_a_slots": [1, 2, 3],
        "agent_b_frozen_slots": [4, 5],
        "shared_capital_slot_counts": [18, 17],
        "shared_capital_missions": 35,
        "regular_profile_slot_counts": [0, 0, 8],
        "commercial_profile_slot_counts": [7, 7, 7],
        "regular_profile_count": 12,
        "total_profile_count": 13,
        "total_agent_a_missions": 152,
        "globally_unique_mission_ids": True,
        "no_same_slot_competing_series": True,
    }:
        result.add(
            "socioeconomic.mission_plan",
            "mission plan must preserve A slots 1-3, B slots 4-5 and the 35+12x8+21 contract",
            PLAN_PATH.as_posix(),
        )

    builders_missing = [path.as_posix() for path in BUILDER_PATHS if not (context.mod_root / path).is_file()]
    if builders_missing:
        result.add(
            "socioeconomic.builders_missing",
            "missing deterministic builders: " + ", ".join(builders_missing),
        )

    frozen_whole = frozen.get("whole_file_sha256")
    frozen_blocks = frozen.get("slot_series_sha256")
    if (
        frozen.get("schema_version") != 2
        or not isinstance(frozen_whole, dict)
        or not isinstance(frozen_blocks, dict)
    ):
        result.add(
            "socioeconomic.frozen_manifest",
            "frozen mission manifest must use schema 2 whole-file and slot-series tables",
        )
        frozen_whole = {}
        frozen_blocks = {}
    else:
        for relative, expected in frozen_whole.items():
            path = context.mod_root / str(relative)
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            if actual != expected:
                result.add(
                    "socioeconomic.b_slot_drift",
                    f"frozen B mission file drifted: expected {expected}, got {actual}",
                    str(relative),
                )
        for relative, records in frozen_blocks.items():
            path = context.mod_root / str(relative)
            if not isinstance(records, dict) or not path.is_file():
                result.add(
                    "socioeconomic.frozen_manifest",
                    "frozen slot-series record is malformed or missing",
                    str(relative),
                )
                continue
            payload = path.read_bytes()
            for series, expected in records.items():
                block = _top_level_block_bytes(payload, str(series))
                actual = hashlib.sha256(block).hexdigest() if block is not None else None
                if actual != expected:
                    result.add(
                        "socioeconomic.b_slot_drift",
                        f"frozen B slot series drifted: {series}: expected {expected}, got {actual}",
                        str(relative),
                    )

    for path in INTEGRATION_PATHS:
        if not (context.mod_root / path).is_file():
            result.add(
                "socioeconomic.integration_missing",
                "central migration or guide output is missing",
                path.as_posix(),
            )

    new_text = _all_new_script_text(context.mod_root)
    for token in REQUIRED_ESTATE_EFFECTS + REQUIRED_MARKET_EFFECTS + REQUIRED_COMPANY_EFFECTS + REQUIRED_MISSION_EFFECTS:
        if token not in new_text:
            result.add(
                "socioeconomic.interface_missing",
                f"required idempotent interface is missing: {token}",
            )
    for disaster in REQUIRED_DISASTERS:
        if re.search(rf"(?m)^{re.escape(disaster)}\s*=\s*\{{", new_text) is None:
            result.add(
                "socioeconomic.disaster_missing",
                f"required estate disaster is missing: {disaster}",
            )
    for flag in COMPANY_FLAGS:
        if flag not in new_text:
            result.add("socioeconomic.company_missing", f"domestic company is missing: {flag}")

    if re.search(r"(?m)^\s*on_monthly_pulse\s*=", new_text):
        result.add("socioeconomic.monthly_scan", "new socioeconomic code must not use a monthly pulse")
    if re.search(r"(?m)^\s*(every_country|every_province)\s*=", new_text):
        result.add("socioeconomic.world_scan", "new socioeconomic code must not scan every country/province")
    if re.search(r"jxp_a_(?:capitalism|company|market)_(?:score|meter|progress)\b", new_text):
        result.add("socioeconomic.meter", "new capitalism/company 0-100 meter detected")

    privilege_ids = _top_level_prefixed_keys(context, "common/estate_privileges", "jxp_a_")
    agenda_ids = _top_level_prefixed_keys(context, "common/estate_agendas", "jxp_a_")
    if len(privilege_ids) < 48:
        result.add(
            "socioeconomic.privilege_count",
            f"expected at least 48 Japanese estate privileges, found {len(privilege_ids)}",
        )
    if len(agenda_ids) < 40:
        result.add(
            "socioeconomic.agenda_count",
            f"expected at least 40 Japanese estate agendas, found {len(agenda_ids)}",
        )

    estate_text = "\n".join(
        _read_text(path) for path in (context.mod_root / "common/estates").glob("*.txt")
    ) if (context.mod_root / "common/estates").is_dir() else ""
    if "jxp_estate_village_communes" not in estate_text:
        result.add("socioeconomic.fourth_estate", "village communes estate is not registered")
    if estate_text.count("custom_name = {") < 4:
        result.add("socioeconomic.dynamic_names", "Japanese estate dynamic/fallback names are incomplete")

    (
        total,
        per_profile,
        per_slot,
        shared_per_slot,
        mission_ids,
        global_id_counts,
    ) = _mission_counts(context)
    if total != 152 or len(mission_ids) != 152:
        result.add(
            "socioeconomic.mission_count",
            f"expected 152 unique Agent A socioeconomic missions, found {total}/{len(mission_ids)}",
        )
    if [shared_per_slot[1], shared_per_slot[2]] != [18, 17]:
        result.add(
            "socioeconomic.shared_mission_slots",
            "shared capital chapter must contain 18 slot-1 and 17 slot-2 missions",
        )
    duplicates = sorted(
        mission_id for mission_id, count in global_id_counts.items() if count != 1
    )
    if duplicates:
        result.add(
            "socioeconomic.mission_id_collision",
            "generated mission ids are not globally unique: " + ", ".join(duplicates[:12]),
        )
    profile_records = [record for record in plan.get("profiles", []) if isinstance(record, dict)]
    for record in profile_records:
        key = str(record.get("key"))
        expected = int(record.get("a_task_count", 0))
        if per_profile[key] != expected:
            result.add(
                "socioeconomic.profile_density",
                f"profile {key} has {per_profile[key]} A missions; expected {expected}",
            )
        expected_slots = [7, 7, 7] if key == "commercial_council" else [0, 0, 8]
        actual_slots = [per_slot[(key, slot)] for slot in (1, 2, 3)]
        if actual_slots != expected_slots:
            result.add(
                "socioeconomic.profile_slots",
                f"profile {key} A slot density is {actual_slots}; expected {expected_slots}",
            )

    loc_keys = _localisation_keys(context.mod_root)
    for mission_id in mission_ids:
        for suffix in ("_title", "_desc", "_reward_tt"):
            key = mission_id + suffix
            if key not in loc_keys:
                result.add(
                    "socioeconomic.mission_localisation",
                    f"mission localisation key is missing: {key}",
                )
    _audit_localisation_mirrors(context.mod_root, result)

    # The public guide and script tooltips expose these flags directly.  A
    # same-name label is required so players never see a raw implementation
    # identifier in a condition or disaster panel.
    for key in (
        "jxp_a_nobles_estate_interaction_recent",
        "jxp_a_church_estate_interaction_recent",
        "jxp_a_burghers_estate_interaction_recent",
        "jxp_a_villages_estate_interaction_recent",
        "jxp_iface_overseas_charter_ready",
        "jxp_a_105_commercial_crisis_pressure",
        "jxp_a_105_commercial_crisis_resolved",
    ):
        if key not in loc_keys:
            result.add(
                "socioeconomic.visible_state_localisation",
                f"player-visible state localisation is missing: {key}",
            )

    source_text = "\n".join(
        _read_text(path)
        for pattern in SOURCE_LOC_PATTERNS
        for path in sorted((context.mod_root / "localisation_source").glob(pattern))
    )
    loc_values = {
        key: value
        for key, value in re.findall(
            r'(?m)^\s*([A-Za-z0-9_.-]+):\d+\s+"((?:[^"\\]|\\.)*)"',
            source_text,
        )
    }
    reward_values = {
        loc_values.get(mission_id + "_reward_tt", "") for mission_id in mission_ids
    }
    reward_values.discard("")
    if len(reward_values) < 60:
        result.add(
            "socioeconomic.reward_tooltip_placeholders",
            f"152 missions expose only {len(reward_values)} distinct reward tooltips; "
            "market/company/estate unlocks are still presented as placeholders",
        )

    modifier_path = context.mod_root / "common/event_modifiers/jxp_a_105_missions_routes_modifiers.txt"
    modifier_text = _read_text(modifier_path) if modifier_path.is_file() else ""
    visible_modifiers = set(
        re.findall(r"(?m)^(jxp_a_105_[A-Za-z0-9_]+)\s*=\s*\{", modifier_text)
    )
    for modifier in sorted(visible_modifiers):
        if modifier not in loc_keys or modifier + "_desc" not in loc_keys:
            result.add(
                "socioeconomic.modifier_localisation",
                f"visible modifier requires a name and description: {modifier}",
                modifier_path.relative_to(context.mod_root).as_posix(),
            )

    reform_path = context.mod_root / "common/government_reforms/jxp_a_105_commercial_reforms.txt"
    government_path = context.mod_root / "common/governments/00_governments.txt"
    reform_text = _read_text(reform_path) if reform_path.is_file() else ""
    government_text = _read_text(government_path) if government_path.is_file() else ""
    commercial_reforms = (
        "jxp_a_105_commercial_council_state_reform",
        "jxp_a_105_commercial_shogunate_reform",
        "jxp_a_105_commercial_merchant_council_reform",
        "jxp_a_105_commercial_company_empire_reform",
    )
    for reform in commercial_reforms:
        if not _top_level_text_block(reform_text, reform):
            result.add(
                "socioeconomic.commercial_reform_missing",
                f"commercial tier-one reform is missing: {reform}",
            )
        if reform not in government_text:
            result.add(
                "socioeconomic.commercial_reform_unregistered",
                f"commercial tier-one reform is not centrally registered: {reform}",
                government_path.relative_to(context.mod_root).as_posix(),
            )

    mission_trigger_path = context.mod_root / "common/scripted_triggers/jxp_a_105_missions_routes_triggers.txt"
    mission_effect_path = context.mod_root / "common/scripted_effects/jxp_a_105_missions_routes_effects.txt"
    mission_trigger_text = _read_text(mission_trigger_path) if mission_trigger_path.is_file() else ""
    mission_effect_text = _read_text(mission_effect_path) if mission_effect_path.is_file() else ""
    for trigger in (
        "jxp_a_105_founder_legacy_consistent_trigger",
        "jxp_a_105_unification_method_consistent_trigger",
        "jxp_a_105_profile_state_consistent_trigger",
        "jxp_a_105_any_persistent_state_trigger",
    ):
        if not _top_level_text_block(mission_trigger_text, trigger):
            result.add(
                "socioeconomic.consistency_trigger_missing",
                f"public consistency trigger is missing: {trigger}",
            )
    if not _top_level_text_block(mission_effect_text, "jxp_a_105_full_cleanup_effect"):
        result.add(
            "socioeconomic.full_cleanup_missing",
            "mission/profile persistent state has no complete cleanup effect",
        )

    # Verify the 67 main+map origins are an exact partition of the five
    # founder legacies.  Importing this deterministic authority has no writes.
    mission_builder = context.mod_root / "tools/jxp_a_socioeconomic_builder/build_missions_routes.py"
    try:
        spec = importlib.util.spec_from_file_location(
            "jxp_socioeconomic_mission_authority", mission_builder
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {mission_builder}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        founder_origins = [
            origin
            for origins in module.FOUNDER_ORIGINS.values()
            for origin in origins
        ]
        founder_origins.extend(
            origin
            for origins in module.MAP_FOUNDER_ORIGINS.values()
            for origin in origins
        )
        if len(founder_origins) != 67 or len(set(founder_origins)) != 67:
            result.add(
                "socioeconomic.founder_partition",
                f"founder legacy authority must partition 67 origins exactly; "
                f"found {len(founder_origins)}/{len(set(founder_origins))}",
            )
    except (OSError, ImportError, AttributeError) as exc:
        result.add(
            "socioeconomic.founder_authority",
            f"cannot inspect founder legacy authority: {exc}",
        )

    economy_trigger_path = context.mod_root / "common/scripted_triggers/jxp_a_104_economy_triggers.txt"
    economy_trigger_text = _read_text(economy_trigger_path) if economy_trigger_path.is_file() else ""
    company_pulse = _top_level_text_block(
        economy_trigger_text, "jxp_a_company_pulse_relevant_trigger"
    )
    if not company_pulse or "jxp_iface_a_company_core_ready" in company_pulse:
        result.add(
            "socioeconomic.company_pulse_scope",
            "company yearly pulse must require an actual company or pending company state, "
            "not company-core readiness alone",
        )

    # Company-state identity belongs only to the commercial route.  Other
    # systems may read or clear it but must not set it generically.
    allowed_company_state_setters = {
        "common/scripted_effects/jxp_a_105_missions_routes_effects.txt",
        "events/jxp_a_105_domestic_route_events.txt",
        "missions/zzz_jxp_a_105_socioeconomic_missions.txt",
    }
    for root_name in ("common", "decisions", "events", "missions"):
        for path in (context.mod_root / root_name).rglob("*.txt"):
            relative = path.relative_to(context.mod_root).as_posix()
            if (
                "set_country_flag = jxp_iface_a_company_state_route" in _read_text(path)
                and relative not in allowed_company_state_setters
            ):
                result.add(
                    "socioeconomic.company_state_owner",
                    "only the Commercial Council route may set the company-state interface",
                    relative,
                )

    visible_event_count = 0
    event_paths = {
        *(context.mod_root / "events").glob("jxp_a_10*.txt"),
        *(context.mod_root / "events").glob("jxp_a_11*.txt"),
    }
    for path in sorted(event_paths):
        document = context.document(path)
        if document is None:
            continue
        for entry in document.root.entries:
            if entry.key != "country_event" or not isinstance(entry.value, Object):
                continue
            if first_scalar(entry.value, "hidden") != "yes" and first_scalar(entry.value, "title") not in {None, "none"}:
                visible_event_count += 1
    if visible_event_count < 40:
        result.add(
            "socioeconomic.visible_events",
            f"expected at least 40 visible socioeconomic events, found {visible_event_count}",
        )

    result.metrics.update(
        {
            "privileges": len(privilege_ids),
            "agendas": len(agenda_ids),
            "a_missions": total,
            "profiles": len(profile_records),
            "visible_events": visible_event_count,
            "frozen_mission_files": len(frozen_whole) + len(frozen_blocks),
        }
    )
    result.summary = (
        f"{len(privilege_ids)} privileges; {len(agenda_ids)} agendas; "
        f"{total}/152 A missions across {len(profile_records)} profiles; "
        f"{visible_event_count} visible events"
    )
    return result
