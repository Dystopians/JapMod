"""Executable contract for the ten unified Japanese final states."""

from __future__ import annotations

from dataclasses import dataclass, replace
import importlib.util
from pathlib import Path
import re
from types import ModuleType

from .clausewitz import Object, Scalar, bare_scalars, first_object, first_scalar
from .core import CheckResult, ValidationContext
from .missions import BASE_PROFILES, evaluate_potential, extract_mission_series


TRIGGER_FILE = Path("common/scripted_triggers/jxp_79_final_state_triggers.txt")
REFORM_FILE = Path("common/government_reforms/jxp_79_final_state_power_structures.txt")
LEGACY_REFORM_FILE = Path("common/government_reforms/jxp_japanese_reforms.txt")
EFFECT_FILE = Path("common/scripted_effects/jxp_79_final_state_effects.txt")
ROUTE_EFFECT_FILE = Path("common/scripted_effects/jxp_scripted_effects.txt")
LIFECYCLE_FILE = Path("common/scripted_effects/jxp_73_state_lifecycle_cleanup_effects.txt")
MODIFIER_FILE = Path("common/event_modifiers/jxp_79_final_state_modifiers.txt")
MIGRATION_FILE = Path("events/jxp_79_final_state_migration_events.txt")
MISSION_REFRESH_FILE = Path("events/jxp_23_mission_refresh_events.txt")
ON_ACTION_FILE = Path("common/on_actions/jxp_60_mission_runtime_on_actions.txt")
DEBUG_FILE = Path("common/scripted_effects/jxp_debug_effects.txt")
SOURCE_LOC_FILE = Path("localisation_source/jxp_79_final_states_l_english_utf8_source.yml")
ACTIVE_LOC_FILE = Path("localisation/jxp_79_final_states_l_english.yml")
MISSION_FILES = (
    Path("missions/jxp_09_religious_route_missions.txt"),
    Path("missions/jxp_40_final_state_completion_missions.txt"),
    Path("missions/jxp_56_final_tag_identity_missions.txt"),
    Path("missions/jxp_japan_missions.txt"),
)
MIGRATION_FLAG = "jxp_final_state_power_migration_v0280"


@dataclass(frozen=True, slots=True)
class FinalStateContract:
    key: str
    profile_name: str
    trigger_id: str
    reform_id: str
    mission_id: str
    series_id: str
    previous_mission_id: str
    mission_row: int
    modifier_id: str
    new_reform: bool
    tag: str
    route_flag: str | None = None


FINAL_STATES = (
    FinalStateContract(
        "uncommitted",
        "JAP Shinto (uncommitted)",
        "jxp_final_state_uncommitted_trigger",
        "jxp_uncommitted_realm_council_reform",
        "jxp_mission_uncommitted_codify_realm_council",
        "jxp_japan_uncommitted_council_missions",
        "jxp_mission_uncommitted_draft_realm_program",
        12,
        "jxp_79_uncommitted_realm_program",
        True,
        "JAP",
    ),
    FinalStateContract(
        "sakoku",
        "JAP Shinto (sakoku)",
        "jxp_final_state_sakoku_trigger",
        "jxp_sakoku_bakuhan_council_reform",
        "jxp_mission_sakoku_bakuhan_constitution",
        "jxp_japan_sakoku_horizon_missions",
        "jxp_mission_sakoku_four_seas_under_watch",
        16,
        "jxp_79_sakoku_bakuhan_constitution",
        True,
        "JAP",
        "jxp_path_sakoku",
    ),
    FinalStateContract(
        "open",
        "JAP Shinto (open)",
        "jxp_final_state_open_trigger",
        "jxp_open_maritime_cabinet_reform",
        "jxp_mission_open_maritime_cabinet",
        "jxp_japan_open_missions",
        "jxp_mission_equal_treaties",
        16,
        "jxp_79_open_maritime_cabinet",
        True,
        "JAP",
        "jxp_path_open_trade",
    ),
    FinalStateContract(
        "kirishitan",
        "KJP Christian",
        "jxp_final_state_kirishitan_trigger",
        "jxp_kirishitan_estates_general_reform",
        "jxp_mission_kjp_estates_concordat",
        "jxp_kirishitan_deep_missions",
        "jxp_mission_oceanic_church_state",
        15,
        "jxp_79_kirishitan_estates_concordat",
        True,
        "KJP",
        "jxp_path_kirishitan",
    ),
    FinalStateContract(
        "confucian",
        "CJP Confucian + harmonized Shinto",
        "jxp_final_state_confucian_trigger",
        "jxp_confucian_censorate_reform",
        "jxp_mission_cjp_censorate_charter",
        "jxp_cjp_syncretic_missions",
        "jxp_mission_cjp_rites_without_severance",
        13,
        "jxp_79_confucian_censorate_charter",
        True,
        "CJP",
        "jxp_path_confucian",
    ),
    FinalStateContract(
        "imperial",
        "EJP Imperial",
        "jxp_final_state_imperial_trigger",
        "jxp_imperial_daijokan_reform",
        "jxp_mission_ejp_daijokan_charter",
        "jxp_ejp_restoration_state_missions",
        "jxp_mission_ejp_imperial_constitution",
        12,
        "jxp_79_imperial_daijokan_charter",
        True,
        "EJP",
        "jxp_path_imperial",
    ),
    FinalStateContract(
        "reformed",
        "RFJ Reformed",
        "jxp_final_state_reformed_trigger",
        "jxp_reformed_japan_reform",
        "jxp_mission_rfj_synodic_constitution",
        "jxp_rfj_covenant_horizon_missions",
        "jxp_mission_rfj_free_seas_commonwealth",
        14,
        "jxp_79_reformed_synodic_constitution",
        False,
        "RFJ",
        "jxp_path_reformed",
    ),
    FinalStateContract(
        "kaikyo",
        "SJP Kaikyo",
        "jxp_final_state_kaikyo_trigger",
        "jxp_kaikyo_japan_reform",
        "jxp_mission_sjp_diwan_constitution",
        "jxp_kaikyo_deep_missions",
        "jxp_mission_sultanate_sea_law",
        15,
        "jxp_79_kaikyo_diwan_constitution",
        False,
        "SJP",
        "jxp_path_kaikyo",
    ),
    FinalStateContract(
        "ikko",
        "IJP Ikko",
        "jxp_final_state_ikko_trigger",
        "jxp_ikko_commonwealth_reform",
        "jxp_mission_ijp_somon_constitution",
        "jxp_ikko_common_economy_missions",
        "jxp_mission_ikko_realm_of_fellowship",
        16,
        "jxp_79_ikko_somon_constitution",
        False,
        "IJP",
        "jxp_path_ikko",
    ),
    FinalStateContract(
        "wokou",
        "WAK Wokou",
        "jxp_final_state_wokou_trigger",
        "jxp_wokou_admiralty_reform",
        "jxp_mission_wak_admiralty_articles",
        "jxp_wak_black_current_missions",
        "jxp_mission_wak_black_tide_code",
        13,
        "jxp_79_wokou_admiralty_articles",
        False,
        "WAK",
        "jxp_path_wokou",
    ),
)


def _top_objects(context: ValidationContext, relative: Path) -> dict[str, list[Object]]:
    source = context.mod_root / relative
    document = context.document(source) if source.is_file() else None
    result: dict[str, list[Object]] = {}
    if document is None:
        return result
    for entry in document.root.entries:
        if entry.key is not None and isinstance(entry.value, Object):
            result.setdefault(entry.key, []).append(entry.value)
    return result


def _contains_assignment(obj: Object | None, key: str, value: str | None = None) -> bool:
    if obj is None:
        return False
    for entry in obj.entries:
        if entry.key == key and isinstance(entry.value, Scalar):
            if value is None or entry.value.text == value:
                return True
        if isinstance(entry.value, Object) and _contains_assignment(entry.value, key, value):
            return True
    return False


def _assignment_values(obj: Object | None, key: str) -> tuple[str, ...]:
    values: list[str] = []
    if obj is None:
        return ()
    for entry in obj.entries:
        if entry.key == key and isinstance(entry.value, Scalar):
            values.append(entry.value.text)
        if isinstance(entry.value, Object):
            values.extend(_assignment_values(entry.value, key))
    return tuple(values)


def _event_by_id(context: ValidationContext, relative: Path, event_id: str) -> Object | None:
    for event in _top_objects(context, relative).get("country_event", []):
        if first_scalar(event, "id") == event_id:
            return event
    return None


def _named_modifier(effect: Object | None, modifier_id: str) -> bool:
    if effect is None:
        return False
    for entry in effect.entries:
        if entry.key == "add_country_modifier" and isinstance(entry.value, Object):
            if first_scalar(entry.value, "name") == modifier_id:
                return True
        if isinstance(entry.value, Object) and _named_modifier(entry.value, modifier_id):
            return True
    return False


def _localisation_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    pattern = re.compile(r"(?m)^\s*([A-Za-z0-9_.-]+):\d+\s")
    for folder in ("localisation_source", "localisation"):
        for source in sorted((root / folder).glob("*.yml")):
            keys.update(pattern.findall(source.read_text(encoding="utf-8-sig")))
    return keys


def _load_escape_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_jxp_79_escape", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load localisation escape helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_localisation_pipeline(
    context: ValidationContext,
    result: CheckResult,
) -> None:
    source = context.mod_root / SOURCE_LOC_FILE
    active = context.mod_root / ACTIVE_LOC_FILE
    if not source.is_file():
        result.add(
            "final_state.localisation_source_missing",
            "final-state UTF-8 localisation source is missing",
            str(SOURCE_LOC_FILE),
        )
        return
    if not active.is_file():
        result.add(
            "final_state.localisation_active_missing",
            "final-state escaped active localisation is missing",
            str(ACTIVE_LOC_FILE),
        )
        return
    try:
        escape_path = (
            Path(__file__).resolve().parents[3]
            / "skills"
            / "eu4-modding"
            / "scripts"
            / "escape_eu4_special_localisation.py"
        )
        escape_text = _load_escape_module(escape_path).escape_text
        expected = escape_text(source.read_text(encoding="utf-8-sig")).encode("utf-8-sig")
        actual = active.read_bytes()
        if actual != expected:
            result.add(
                "final_state.localisation_escape",
                "active final-state localisation is not the exact escaped canonical source",
                str(ACTIVE_LOC_FILE),
            )
        if not actual.startswith(b"\xef\xbb\xbf"):
            result.add(
                "final_state.localisation_bom",
                "active final-state localisation must carry a UTF-8 BOM",
                str(ACTIVE_LOC_FILE),
            )
        active_text = actual.decode("utf-8-sig")
        if any("\u3400" <= character <= "\u9fff" for character in active_text):
            result.add(
                "final_state.localisation_raw_cjk",
                "active final-state localisation contains raw CJK text",
                str(ACTIVE_LOC_FILE),
            )
    except Exception as exc:
        result.add(
            "final_state.localisation_escape",
            f"cannot verify final-state localisation escape: {exc}",
            str(ACTIVE_LOC_FILE),
        )


def check_final_states(context: ValidationContext) -> CheckResult:
    """Prove reform exclusivity, migration closure, and ten political capstones."""

    result = CheckResult("Unified final states")
    expected_reforms = {state.reform_id for state in FINAL_STATES}
    expected_triggers = {state.trigger_id for state in FINAL_STATES}
    expected_modifiers = {state.modifier_id for state in FINAL_STATES}

    trigger_objects = _top_objects(context, TRIGGER_FILE)
    reform_objects = _top_objects(context, REFORM_FILE)
    legacy_reform_objects = _top_objects(context, LEGACY_REFORM_FILE)
    effect_objects = _top_objects(context, EFFECT_FILE)
    modifier_objects = _top_objects(context, MODIFIER_FILE)

    new_expected = {state.reform_id for state in FINAL_STATES if state.new_reform}
    actual_new = set(reform_objects)
    if actual_new != new_expected:
        result.add(
            "final_state.new_reform_inventory",
            "jxp_79 final-state reforms mismatch; missing="
            + ", ".join(sorted(new_expected - actual_new))
            + "; foreign="
            + ", ".join(sorted(actual_new - new_expected)),
            str(REFORM_FILE),
        )

    reform_signatures: dict[tuple[tuple[str, str], ...], list[str]] = {}
    for state in FINAL_STATES:
        source_objects = reform_objects if state.new_reform else legacy_reform_objects
        definitions = source_objects.get(state.reform_id, [])
        if len(definitions) != 1:
            result.add(
                "final_state.reform_missing",
                f"{state.key} power structure {state.reform_id} has "
                f"{len(definitions)} definitions; expected exactly one",
                str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
            )
            continue
        definition = definitions[0]
        if first_scalar(definition, "basic_reform") != "yes":
            result.add(
                "final_state.reform_visibility",
                f"{state.reform_id} must be a visible basic_reform",
                str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
            )
        if first_scalar(definition, "valid_for_nation_designer") != "no":
            result.add(
                "final_state.reform_nation_designer",
                f"{state.reform_id} must be excluded from the nation designer",
                str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
            )
        modifiers = first_object(definition, "modifiers")
        signature = tuple(
            sorted(
                (entry.key, entry.value.text)
                for entry in (modifiers.entries if modifiers is not None else ())
                if entry.key is not None and isinstance(entry.value, Scalar)
            )
        )
        if len(signature) < 3:
            result.add(
                "final_state.reform_depth",
                f"{state.reform_id} has {len(signature)} modifiers; expected at least three",
                str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
            )
        reform_signatures.setdefault(signature, []).append(state.reform_id)
        potential = first_object(definition, "potential")
        potential_source = REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE
        if not _contains_assignment(potential, state.trigger_id, "yes"):
            result.add(
                "final_state.reform_potential",
                f"{state.reform_id} does not use final-only gate {state.trigger_id}; "
                "route flags alone would expose it before the final tag exists",
                str(potential_source),
            )
        if not _contains_assignment(potential, "has_reform", state.reform_id):
            result.add(
                "final_state.reform_selected_fallback",
                f"{state.reform_id} does not preserve its selected state",
                str(potential_source),
            )

    for signature, reforms in reform_signatures.items():
        if signature and len(reforms) > 1:
            result.add(
                "final_state.reform_signature_duplicate",
                "power structures share an identical modifier signature: "
                + ", ".join(sorted(reforms)),
            )

    # Evaluate the actual scripted trigger grammar against the same ten
    # representative profiles used by the mission and reform visibility gates.
    profiles = {
        profile.name: profile for profile in BASE_PROFILES if not profile.daimyo_stage
    }
    trigger_matches: dict[str, list[str]] = {trigger: [] for trigger in expected_triggers}
    for state in FINAL_STATES:
        definitions = trigger_objects.get(state.trigger_id, [])
        if len(definitions) != 1:
            result.add(
                "final_state.trigger_missing",
                f"{state.trigger_id} has {len(definitions)} definitions; expected one",
                str(TRIGGER_FILE),
            )
    for profile_name, profile in profiles.items():
        matched: list[str] = []
        for state in FINAL_STATES:
            definitions = trigger_objects.get(state.trigger_id, [])
            if len(definitions) != 1:
                continue
            values, unknown = evaluate_potential(definitions[0], profile)
            for predicate in unknown:
                result.add(
                    "final_state.trigger_predicate_unknown",
                    f"{state.trigger_id} uses unsupported predicate {predicate.key}: "
                    f"{predicate.reason}",
                    str(TRIGGER_FILE),
                    predicate.line,
                )
            if True in values:
                matched.append(state.trigger_id)
                trigger_matches[state.trigger_id].append(profile_name)
        expected = next(
            (state.trigger_id for state in FINAL_STATES if state.profile_name == profile_name),
            None,
        )
        if matched != ([expected] if expected is not None else []):
            result.add(
                "final_state.trigger_exclusivity",
                f"profile {profile_name} matches {matched}; expected {[expected]}",
                str(TRIGGER_FILE),
            )
    for trigger_id, matched_profiles in trigger_matches.items():
        if len(matched_profiles) != 1:
            result.add(
                "final_state.trigger_density",
                f"{trigger_id} matches {len(matched_profiles)} final profiles; expected one",
                str(TRIGGER_FILE),
            )

    route_flags = tuple(
        state.route_flag for state in FINAL_STATES if state.route_flag is not None
    )
    base_jap_profile = profiles["JAP Shinto (uncommitted)"]
    jap_route_state_vectors = 0
    for mask in range(1 << len(route_flags)):
        flags = frozenset(
            flag for index, flag in enumerate(route_flags) if mask & (1 << index)
        )
        synthetic = replace(
            base_jap_profile,
            name="JAP route vector " + "+".join(sorted(flags)),
            flags=flags,
        )
        matched: list[str] = []
        for state in FINAL_STATES:
            definitions = trigger_objects.get(state.trigger_id, [])
            if len(definitions) != 1:
                continue
            values, _unknown = evaluate_potential(definitions[0], synthetic)
            if True in values:
                matched.append(state.trigger_id)
        if not flags:
            expected = ["jxp_final_state_uncommitted_trigger"]
        elif flags == {"jxp_path_sakoku"}:
            expected = ["jxp_final_state_sakoku_trigger"]
        elif flags == {"jxp_path_open_trade"}:
            expected = ["jxp_final_state_open_trigger"]
        else:
            # Final-tag routes must not expose their power structure while the
            # country is still JAP, and contaminated multi-route states are
            # deliberately left to the canonical sanitizer.
            expected = []
        if matched != expected:
            result.add(
                "final_state.jap_route_vector_exclusivity",
                f"JAP route vector {sorted(flags)} matches {matched}; expected {expected}",
                str(TRIGGER_FILE),
            )
        jap_route_state_vectors += 1

    for state in FINAL_STATES:
        mismatch_id = f"jxp_final_state_{state.key}_power_mismatch_trigger"
        definitions = trigger_objects.get(mismatch_id, [])
        if len(definitions) != 1:
            result.add(
                "final_state.mismatch_trigger_missing",
                f"{mismatch_id} has {len(definitions)} definitions; expected one",
                str(TRIGGER_FILE),
            )
            continue
        mismatch_or = first_object(definitions[0], "OR")
        listed = _assignment_values(mismatch_or, "has_reform")
        if set(listed) != expected_reforms or len(listed) != len(expected_reforms):
            result.add(
                "final_state.mismatch_inventory",
                f"{mismatch_id} must inspect all ten power structures exactly once",
                str(TRIGGER_FILE),
            )
        foreign_modifiers = _assignment_values(mismatch_or, "has_country_modifier")
        expected_foreign_modifiers = expected_modifiers - {state.modifier_id}
        if (
            set(foreign_modifiers) != expected_foreign_modifiers
            or len(foreign_modifiers) != len(expected_foreign_modifiers)
        ):
            result.add(
                "final_state.mismatch_modifier_inventory",
                f"{mismatch_id} must detect the other nine states' capstone modifiers",
                str(TRIGGER_FILE),
            )
        expected_negated = bool(
            mismatch_or
            and any(
                entry.key == "NOT"
                and isinstance(entry.value, Object)
                and _contains_assignment(entry.value, "has_reform", state.reform_id)
                for entry in mismatch_or.entries
            )
        )
        if not expected_negated:
            result.add(
                "final_state.mismatch_expected_gate",
                f"{mismatch_id} must treat missing {state.reform_id} as a mismatch",
                str(TRIGGER_FILE),
            )

    clear = effect_objects.get("jxp_clear_final_state_power_structures_effect", [])
    sync = effect_objects.get("jxp_sync_final_state_power_structure_effect", [])
    if len(clear) != 1:
        result.add(
            "final_state.clear_effect_missing",
            "canonical final-state clear effect must be defined exactly once",
            str(EFFECT_FILE),
        )
        clear_obj = None
    else:
        clear_obj = clear[0]
    removed = _assignment_values(clear_obj, "remove_government_reform")
    if set(removed) != expected_reforms or len(removed) != len(expected_reforms):
        result.add(
            "final_state.clear_inventory",
            "canonical clear effect must remove each of the ten power structures exactly once",
            str(EFFECT_FILE),
        )

    capstone_clear = effect_objects.get(
        "jxp_clear_final_state_capstone_modifiers_effect", []
    )
    cleared_modifiers = _assignment_values(
        capstone_clear[0] if len(capstone_clear) == 1 else None,
        "remove_country_modifier",
    )
    if (
        len(capstone_clear) != 1
        or set(cleared_modifiers) != expected_modifiers
        or len(cleared_modifiers) != len(expected_modifiers)
    ):
        result.add(
            "final_state.capstone_clear_inventory",
            "canonical capstone cleanup must remove each of the ten political modifiers once",
            str(EFFECT_FILE),
        )

    if len(sync) != 1:
        result.add(
            "final_state.sync_effect_missing",
            "canonical final-state sync effect must be defined exactly once",
            str(EFFECT_FILE),
        )
        sync_obj = None
    else:
        sync_obj = sync[0]
    if not _contains_assignment(
        sync_obj, "jxp_clear_final_state_power_structures_effect", "yes"
    ):
        result.add(
            "final_state.sync_without_clear",
            "canonical sync must clear stale power structures before assigning one",
            str(EFFECT_FILE),
        )
    if not _contains_assignment(sync_obj, "regenerate_government_mechanics", "yes"):
        result.add(
            "final_state.sync_without_regenerate",
            "canonical sync must regenerate government mechanics",
            str(EFFECT_FILE),
        )
    added = _assignment_values(sync_obj, "add_government_reform")
    if set(added) != expected_reforms or len(added) != len(expected_reforms):
        result.add(
            "final_state.sync_inventory",
            "canonical sync must add each of the ten power structures exactly once",
            str(EFFECT_FILE),
        )
    hidden = first_object(sync_obj, "hidden_effect")
    branches = [
        entry.value
        for entry in (hidden.entries if hidden is not None else ())
        if entry.key in {"if", "else_if"} and isinstance(entry.value, Object)
    ]
    for state in FINAL_STATES:
        mismatch_id = f"jxp_final_state_{state.key}_power_mismatch_trigger"
        matching = [
            branch
            for branch in branches
            if _contains_assignment(first_object(branch, "limit"), state.trigger_id, "yes")
            and _contains_assignment(branch, mismatch_id, "yes")
            and _contains_assignment(
                branch, "jxp_clear_final_state_power_structures_effect", "yes"
            )
            and _contains_assignment(
                branch, "jxp_clear_final_state_capstone_modifiers_effect", "yes"
            )
            and _contains_assignment(branch, "add_government_reform", state.reform_id)
        ]
        if len(matching) != 1:
            result.add(
                "final_state.sync_mapping",
                f"{state.trigger_id} must map once to {state.reform_id} behind "
                f"mismatch guard {mismatch_id}",
                str(EFFECT_FILE),
            )
    orphan_modifier_checks = _assignment_values(sync_obj, "has_country_modifier")
    if (
        set(orphan_modifier_checks) != expected_modifiers
        or len(orphan_modifier_checks) != len(expected_modifiers)
    ):
        result.add(
            "final_state.orphan_capstone_cleanup",
            "non-final states are not checked for all ten orphaned capstone modifiers",
            str(EFFECT_FILE),
        )

    route_objects = _top_objects(context, ROUTE_EFFECT_FILE)
    route_clear = route_objects.get("jxp_clear_route_reforms_effect", [])
    route_grant = route_objects.get("jxp_grant_route_reforms_effect", [])
    if len(route_clear) != 1 or not _contains_assignment(
        route_clear[0], "jxp_clear_final_state_power_structures_effect", "yes"
    ):
        result.add(
            "final_state.route_clear_wiring",
            "canonical route clear does not clear final-state power structures",
            str(ROUTE_EFFECT_FILE),
        )
    if len(route_clear) != 1 or not _contains_assignment(
        route_clear[0], "jxp_clear_final_state_capstone_modifiers_effect", "yes"
    ):
        result.add(
            "final_state.route_capstone_clear_wiring",
            "canonical route clear does not clear final-state capstone modifiers",
            str(ROUTE_EFFECT_FILE),
        )
    if len(route_grant) != 1 or not _contains_assignment(
        route_grant[0], "jxp_sync_final_state_power_structure_effect", "yes"
    ):
        result.add(
            "final_state.route_sync_wiring",
            "canonical route grant does not synchronize final-state power structures",
            str(ROUTE_EFFECT_FILE),
        )

    migration = _event_by_id(context, MIGRATION_FILE, "jxp_migration_v028.1")
    if migration is None:
        result.add(
            "final_state.migration_missing",
            "0.28 final-state migration event is missing",
            str(MIGRATION_FILE),
        )
    else:
        trigger = first_object(migration, "trigger")
        immediate = first_object(migration, "immediate")
        if not _contains_assignment(trigger, "has_country_flag", MIGRATION_FLAG):
            result.add(
                "final_state.migration_guard",
                f"0.28 migration is not guarded by {MIGRATION_FLAG}",
                str(MIGRATION_FILE),
            )
        for key, code in (
            ("jxp_sanitize_route_state_effect", "final_state.migration_sanitize"),
            ("jxp_sync_final_state_power_structure_effect", "final_state.migration_sync"),
            ("jxp_refresh_route_missions_effect", "final_state.migration_refresh"),
        ):
            if not _contains_assignment(immediate, key, "yes"):
                result.add(code, f"0.28 migration does not call {key}", str(MIGRATION_FILE))
        if not _contains_assignment(immediate, "set_country_flag", MIGRATION_FLAG):
            result.add(
                "final_state.migration_flag",
                f"0.28 migration does not set {MIGRATION_FLAG}",
                str(MIGRATION_FILE),
            )

    on_actions = _top_objects(context, ON_ACTION_FILE)
    startup = on_actions.get("on_startup", [])
    startup_events = first_object(startup[0], "events") if len(startup) == 1 else None
    startup_event_ids = (
        {scalar.text for scalar in bare_scalars(startup_events)}
        if startup_events is not None
        else set()
    )
    if "jxp_migration_v028.1" not in startup_event_ids:
        result.add(
            "final_state.migration_on_startup",
            "0.28 final-state migration is not registered on_startup",
            str(ON_ACTION_FILE),
        )
    for action in ("on_religion_change", "on_government_change"):
        objects = on_actions.get(action, [])
        if len(objects) != 1 or not _contains_assignment(
            objects[0], "jxp_sync_final_state_power_structure_effect", "yes"
        ):
            result.add(
                "final_state.external_change_wiring",
                f"{action} does not reconcile the final-state power structure",
                str(ON_ACTION_FILE),
            )

    delayed_refresh = _event_by_id(context, MISSION_REFRESH_FILE, "jxp_mission_refresh.1")
    delayed_immediate = first_object(delayed_refresh, "immediate") if delayed_refresh else None
    if not _contains_assignment(
        delayed_immediate, "jxp_sync_final_state_power_structure_effect", "yes"
    ):
        result.add(
            "final_state.next_day_sync",
            "the canonical next-day mission refresh does not reconcile power structures",
            str(MISSION_REFRESH_FILE),
        )

    debug_objects = _top_objects(context, DEBUG_FILE)
    debug_has_clear = any(
        _contains_assignment(obj, "clr_country_flag", MIGRATION_FLAG)
        for objects in debug_objects.values()
        for obj in objects
    )
    if not debug_has_clear:
        result.add(
            "final_state.debug_cleanup",
            f"debug cleanup does not clear {MIGRATION_FLAG}",
            str(DEBUG_FILE),
        )
    lifecycle_objects = _top_objects(context, LIFECYCLE_FILE)
    lifecycle_cleanup = lifecycle_objects.get("jxp_debug_clear_legacy_state_debt_effect", [])
    if len(lifecycle_cleanup) != 1 or not _contains_assignment(
        lifecycle_cleanup[0], "jxp_clear_final_state_capstone_modifiers_effect", "yes"
    ):
        result.add(
            "final_state.lifecycle_cleanup",
            "canonical lifecycle/debug reset cannot clear final-state capstone modifiers",
            str(LIFECYCLE_FILE),
        )

    # Capstone density is executable rather than documentary: every state has
    # one new mission in its live series, gated by its own power structure and
    # granting a distinct permanent political modifier.
    mission_result = CheckResult("final-state mission extraction")
    mission_sources = tuple(context.mod_root / path for path in MISSION_FILES)
    series_list = extract_mission_series(context, mission_result, mission_sources)
    for issue in mission_result.issues:
        result.add(
            "final_state.mission_parse",
            issue.message,
            issue.source,
            issue.line,
        )
    series_by_name = {series.name: series for series in series_list}
    localisation_keys = _localisation_keys(context.mod_root)
    for state in FINAL_STATES:
        series = series_by_name.get(state.series_id)
        mission = next(
            (item for item in series.missions if item.mission_id == state.mission_id),
            None,
        ) if series is not None else None
        if mission is None:
            result.add(
                "final_state.capstone_missing",
                f"{state.key} lacks political capstone {state.mission_id} in {state.series_id}",
            )
            continue
        if mission.row != state.mission_row:
            result.add(
                "final_state.capstone_row",
                f"{state.mission_id} uses row {mission.row}; expected {state.mission_row}",
                context.relative(mission.source),
                mission.line,
            )
        if mission.required != (state.previous_mission_id,):
            result.add(
                "final_state.capstone_dependency",
                f"{state.mission_id} must depend directly on {state.previous_mission_id}",
                context.relative(mission.source),
                mission.line,
            )
        source_objects = _top_objects(context, Path(context.relative(mission.source)))
        series_objects = source_objects.get(state.series_id, [])
        mission_body = (
            first_object(series_objects[0], state.mission_id)
            if len(series_objects) == 1
            else None
        )
        trigger = first_object(mission_body, "trigger")
        effect = first_object(mission_body, "effect")
        if not _contains_assignment(trigger, "has_reform", state.reform_id):
            result.add(
                "final_state.capstone_reform_gate",
                f"{state.mission_id} is not gated by {state.reform_id}",
                context.relative(mission.source),
                mission.line,
            )
        if not _named_modifier(effect, state.modifier_id):
            result.add(
                "final_state.capstone_modifier",
                f"{state.mission_id} does not grant {state.modifier_id}",
                context.relative(mission.source),
                mission.line,
            )
        progress = first_scalar(effect, "change_government_reform_progress")
        if progress is None or not re.fullmatch(r"[1-9]\d*", progress):
            result.add(
                "final_state.capstone_reform_progress",
                f"{state.mission_id} must grant positive government reform progress",
                context.relative(mission.source),
                mission.line,
            )
        for suffix in ("_title", "_desc"):
            if state.mission_id + suffix not in localisation_keys:
                result.add(
                    "final_state.capstone_localisation",
                    f"{state.mission_id} is missing {state.mission_id + suffix}",
                    context.relative(mission.source),
                    mission.line,
                )

    actual_modifiers = set(modifier_objects)
    if actual_modifiers != expected_modifiers:
        result.add(
            "final_state.modifier_inventory",
            "final-state capstone modifier inventory mismatch; missing="
            + ", ".join(sorted(expected_modifiers - actual_modifiers))
            + "; foreign="
            + ", ".join(sorted(actual_modifiers - expected_modifiers)),
            str(MODIFIER_FILE),
        )
    for modifier_id in expected_modifiers:
        objects = modifier_objects.get(modifier_id, [])
        scalar_count = sum(
            isinstance(entry.value, Scalar)
            for entry in (objects[0].entries if len(objects) == 1 else ())
            if entry.key is not None
        )
        if scalar_count < 2:
            result.add(
                "final_state.modifier_depth",
                f"{modifier_id} has {scalar_count} effects; expected at least two",
                str(MODIFIER_FILE),
            )
        if modifier_id not in localisation_keys:
            result.add(
                "final_state.modifier_localisation",
                f"{modifier_id} is not localised",
                str(SOURCE_LOC_FILE),
            )

    for state in FINAL_STATES:
        for key in (state.reform_id, state.reform_id + "_desc"):
            if key not in localisation_keys:
                result.add(
                    "final_state.reform_localisation",
                    f"{state.reform_id} is missing localisation key {key}",
                    str(SOURCE_LOC_FILE if state.new_reform else LEGACY_REFORM_FILE),
                )
    _check_localisation_pipeline(context, result)

    result.metrics.update(
        {
            "final_states": len(FINAL_STATES),
            "power_structures": len(expected_reforms),
            "new_power_structures": len(new_expected),
            "reused_power_structures": len(expected_reforms - new_expected),
            "exclusive_trigger_profiles": sum(
                len(matches) == 1 for matches in trigger_matches.values()
            ),
            "political_capstones": len(FINAL_STATES),
            "capstone_modifiers": len(expected_modifiers),
            "capstone_cleanup": len(cleared_modifiers),
            "unique_reform_signatures": len(reform_signatures),
            "mismatch_guards": sum(
                len(trigger_objects.get(f"jxp_final_state_{state.key}_power_mismatch_trigger", []))
                == 1
                for state in FINAL_STATES
            ),
            "jap_route_state_vectors": jap_route_state_vectors,
        }
    )
    result.summary = (
        "10 exclusive final-state power structures and 10 political capstones; "
        "0.28 migration plus next-day reconciliation"
    )
    return result
