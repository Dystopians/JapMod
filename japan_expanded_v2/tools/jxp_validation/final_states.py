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
POLITICAL_REFORM_FILE = Path(
    "common/government_reforms/jxp_80_final_state_political_reforms.txt"
)
CELESTIAL_REFORM_FILE = Path(
    "common/government_reforms/01_government_reforms_monarchies.txt"
)
EOC_POWER_MODIFIER_FILE = Path(
    "common/triggered_modifiers/jxp_82_eoc_final_state_power_structures.txt"
)
GOVERNMENT_FILE = Path("common/governments/00_governments.txt")
EFFECT_FILE = Path("common/scripted_effects/jxp_79_final_state_effects.txt")
ROUTE_EFFECT_FILE = Path("common/scripted_effects/jxp_scripted_effects.txt")
LIFECYCLE_FILE = Path("common/scripted_effects/jxp_73_state_lifecycle_cleanup_effects.txt")
MODIFIER_FILE = Path("common/event_modifiers/jxp_79_final_state_modifiers.txt")
MIGRATION_FILE = Path("events/jxp_79_final_state_migration_events.txt")
MISSION_REFRESH_FILE = Path("events/jxp_23_mission_refresh_events.txt")
ON_ACTION_FILE = Path("common/on_actions/jxp_60_mission_runtime_on_actions.txt")
DEBUG_FILE = Path("common/scripted_effects/jxp_debug_effects.txt")
DEBUG_DECISION_FILE = Path("decisions/jxp_80_final_state_debug_decisions.txt")
SOURCE_LOC_FILE = Path("localisation_source/jxp_79_final_states_l_english_utf8_source.yml")
ACTIVE_LOC_FILE = Path("localisation/jxp_79_final_states_l_english.yml")
POLITICAL_SOURCE_LOC_FILE = Path(
    "localisation_source/jxp_80_final_state_reforms_l_english_utf8_source.yml"
)
POLITICAL_ACTIVE_LOC_FILE = Path(
    "localisation/jxp_80_final_state_reforms_l_english.yml"
)
MISSION_FILES = (
    Path("missions/jxp_09_religious_route_missions.txt"),
    Path("missions/jxp_40_final_state_completion_missions.txt"),
    Path("missions/jxp_56_final_tag_identity_missions.txt"),
    Path("missions/jxp_japan_missions.txt"),
)
MIGRATION_FLAG = "jxp_final_state_power_migration_v0280"
POLITICAL_MIGRATION_FLAG = "jxp_final_state_political_reform_migration_v0283"
POLITICAL_REFORM_TIER = "absolute_rule_vs_constitutional"
CELESTIAL_REFORM_ID = "celestial_empire"
POLITY_MECHANIC_ID = "jxp_japanese_polity_mechanic"
POLITICAL_REFORM_MODIFIERS = {
    "jxp_reform_final_uncommitted_consensus": (
        ("all_estate_loyalty_equilibrium", "0.05"),
        ("reform_progress_growth", "0.10"),
    ),
    "jxp_reform_final_sakoku_constitution": (
        ("global_unrest", "-1"),
        ("max_absolutism", "5"),
    ),
    "jxp_reform_final_open_cabinet": (
        ("free_policy", "1"),
        ("possible_policy", "1"),
    ),
    "jxp_reform_final_kirishitan_estates": (
        ("burghers_loyalty_modifier", "0.05"),
        ("church_loyalty_modifier", "0.10"),
    ),
    "jxp_reform_final_confucian_censorate": (
        ("reform_progress_growth", "0.10"),
        ("yearly_corruption", "-0.05"),
    ),
    "jxp_reform_final_imperial_daijokan": (
        ("max_absolutism", "10"),
        ("yearly_absolutism", "0.5"),
    ),
    "jxp_reform_final_reformed_synod": (
        ("burghers_loyalty_modifier", "0.10"),
        ("global_institution_spread", "0.10"),
    ),
    "jxp_reform_final_kaikyo_diwan": (
        ("caravan_power", "0.15"),
        ("trade_steering", "0.10"),
    ),
    "jxp_reform_final_ikko_somon": (
        ("all_estate_loyalty_equilibrium", "0.05"),
        ("global_unrest", "-1"),
    ),
    "jxp_reform_final_wokou_admiralty": (
        ("global_ship_recruit_speed", "-0.10"),
        ("navy_tradition", "0.5"),
    ),
}


@dataclass(frozen=True, slots=True)
class FinalStateContract:
    key: str
    profile_name: str
    trigger_id: str
    reform_id: str
    political_reform_id: str
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
        "jxp_reform_final_uncommitted_consensus",
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
        "jxp_reform_final_sakoku_constitution",
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
        "jxp_reform_final_open_cabinet",
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
        "jxp_reform_final_kirishitan_estates",
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
        "jxp_reform_final_confucian_censorate",
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
        "jxp_reform_final_imperial_daijokan",
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
        "jxp_reform_final_reformed_synod",
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
        "jxp_reform_final_kaikyo_diwan",
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
        "jxp_reform_final_ikko_somon",
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
        "jxp_reform_final_wokou_admiralty",
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


def _bare_values(obj: Object | None) -> tuple[str, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value.text
        for entry in obj.entries
        if entry.key is None and isinstance(entry.value, Scalar)
    )


def _direct_objects(obj: Object | None, key: str) -> tuple[Object, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value
        for entry in obj.entries
        if entry.key == key and isinstance(entry.value, Object)
    )


def _direct_scalar_signature(
    obj: Object | None,
    *,
    excluded: frozenset[str] = frozenset(),
) -> tuple[tuple[str, str], ...]:
    if obj is None:
        return ()
    return tuple(
        sorted(
            (entry.key, entry.value.text)
            for entry in obj.entries
            if entry.key is not None
            and entry.key not in excluded
            and isinstance(entry.value, Scalar)
        )
    )


def _exact_power_potential(
    potential: Object | None,
    *,
    trigger_id: str,
    reform_id: str,
) -> bool:
    """Require `(exact final state AND not EoC) OR selected self`."""

    if potential is None or len(potential.entries) != 1:
        return False
    alternatives = _direct_objects(potential, "OR")
    if len(alternatives) != 1 or len(alternatives[0].entries) != 2:
        return False
    state_blocks = _direct_objects(alternatives[0], "AND")
    self_values = tuple(
        entry.value.text
        for entry in alternatives[0].entries
        if entry.key == "has_reform" and isinstance(entry.value, Scalar)
    )
    if len(state_blocks) != 1 or self_values != (reform_id,):
        return False
    return _direct_scalar_signature(state_blocks[0]) == tuple(
        sorted(((trigger_id, "yes"), ("is_emperor_of_china", "no")))
    )


def _exact_power_active_trigger(
    obj: Object | None,
    *,
    trigger_id: str,
    reform_id: str,
) -> bool:
    if obj is None or len(obj.entries) != 2:
        return False
    if _direct_scalar_signature(obj) != ((trigger_id, "yes"),):
        return False
    alternatives = _direct_objects(obj, "OR")
    if len(alternatives) != 1 or len(alternatives[0].entries) != 2:
        return False
    branches = _direct_objects(alternatives[0], "AND")
    expected = {
        tuple(sorted((("has_reform", reform_id), ("is_emperor_of_china", "no")))),
        tuple(
            sorted(
                (
                    ("has_reform", CELESTIAL_REFORM_ID),
                    ("is_emperor_of_china", "yes"),
                )
            )
        ),
    }
    return len(branches) == 2 and {_direct_scalar_signature(branch) for branch in branches} == expected


def _eoc_modifier_id(state: FinalStateContract) -> str:
    return f"jxp_82_eoc_{state.key}_power_structure"


def _reform_registration_paths(
    obj: Object,
    path: tuple[str, ...] = (),
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    registrations: list[tuple[str, tuple[str, ...]]] = []
    for entry in obj.entries:
        if entry.key == "reforms" and isinstance(entry.value, Object):
            registrations.extend(
                (value.text, path)
                for value in bare_scalars(entry.value)
            )
        if isinstance(entry.value, Object):
            registrations.extend(
                _reform_registration_paths(
                    entry.value,
                    path + ((entry.key or "{}"),),
                )
            )
    return tuple(registrations)


def _evaluate_final_reform_predicate(
    obj: Object | None,
    profile,
    trigger_objects: dict[str, list[Object]],
) -> tuple[frozenset[bool], tuple[str, ...]]:
    """Evaluate reform predicates after expanding the ten final-state triggers."""

    unknown: list[str] = []

    def truth_and(values: list[frozenset[bool]]) -> frozenset[bool]:
        possible = {True}
        for value in values:
            possible = {left and right for left in possible for right in value}
        return frozenset(possible)

    def truth_or(values: list[frozenset[bool]]) -> frozenset[bool]:
        possible = {False}
        for value in values:
            possible = {left or right for left in possible for right in value}
        return frozenset(possible)

    def evaluate_sequence(block: Object) -> frozenset[bool]:
        return truth_and([evaluate_entry(entry) for entry in block.entries])

    def evaluate_entry(entry) -> frozenset[bool]:
        if entry.key in {"AND", "OR", "NOT"} and isinstance(entry.value, Object):
            nested = [evaluate_entry(child) for child in entry.value.entries]
            if entry.key == "AND":
                return truth_and(nested)
            if entry.key == "OR":
                return truth_or(nested)
            return frozenset(not value for value in truth_and(nested))

        if entry.key in trigger_objects and isinstance(entry.value, Scalar):
            definitions = trigger_objects[entry.key]
            if len(definitions) != 1 or entry.value.text not in {"yes", "no"}:
                unknown.append(f"{entry.key}@{entry.line}")
                return frozenset({False, True})
            values, predicates = evaluate_potential(definitions[0], profile)
            unknown.extend(
                f"{entry.key}->{predicate.key}@{predicate.line}"
                for predicate in predicates
            )
            if entry.value.text == "no":
                return frozenset(not value for value in values)
            return values

        values, predicates = evaluate_potential(Object((entry,)), profile)
        unknown.extend(
            f"{predicate.key}@{predicate.line}" for predicate in predicates
        )
        return values

    if obj is None:
        return frozenset({True}), ()
    return evaluate_sequence(obj), tuple(dict.fromkeys(unknown))


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
    source_relative: Path = SOURCE_LOC_FILE,
    active_relative: Path = ACTIVE_LOC_FILE,
    code_prefix: str = "final_state",
    label: str = "final-state",
) -> None:
    source = context.mod_root / source_relative
    active = context.mod_root / active_relative
    if not source.is_file():
        result.add(
            f"{code_prefix}.localisation_source_missing",
            f"{label} UTF-8 localisation source is missing",
            str(source_relative),
        )
        return
    if not active.is_file():
        result.add(
            f"{code_prefix}.localisation_active_missing",
            f"{label} escaped active localisation is missing",
            str(active_relative),
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
                f"{code_prefix}.localisation_escape",
                f"active {label} localisation is not the exact escaped canonical source",
                str(active_relative),
            )
        if not actual.startswith(b"\xef\xbb\xbf"):
            result.add(
                f"{code_prefix}.localisation_bom",
                f"active {label} localisation must carry a UTF-8 BOM",
                str(active_relative),
            )
        active_text = actual.decode("utf-8-sig")
        if any("\u3400" <= character <= "\u9fff" for character in active_text):
            result.add(
                f"{code_prefix}.localisation_raw_cjk",
                f"active {label} localisation contains raw CJK text",
                str(active_relative),
            )
    except Exception as exc:
        result.add(
            f"{code_prefix}.localisation_escape",
            f"cannot verify {label} localisation escape: {exc}",
            str(active_relative),
        )


def check_final_states(context: ValidationContext) -> CheckResult:
    """Prove reform exclusivity, migration closure, and ten political capstones."""

    result = CheckResult("Unified final states")
    expected_reforms = {state.reform_id for state in FINAL_STATES}
    expected_political_reforms = {
        state.political_reform_id for state in FINAL_STATES
    }
    expected_triggers = {state.trigger_id for state in FINAL_STATES}
    expected_modifiers = {state.modifier_id for state in FINAL_STATES}

    if set(POLITICAL_REFORM_MODIFIERS) != expected_political_reforms:
        result.add(
            "final_state.political_reform_modifier_manifest_inventory",
            "political reform modifier manifest must cover the exact ten final states",
            str(POLITICAL_REFORM_FILE),
        )

    trigger_objects = _top_objects(context, TRIGGER_FILE)
    reform_objects = _top_objects(context, REFORM_FILE)
    legacy_reform_objects = _top_objects(context, LEGACY_REFORM_FILE)
    political_reform_objects = _top_objects(context, POLITICAL_REFORM_FILE)
    celestial_reform_objects = _top_objects(context, CELESTIAL_REFORM_FILE)
    eoc_power_modifier_objects = _top_objects(context, EOC_POWER_MODIFIER_FILE)
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
    if set(political_reform_objects) != expected_political_reforms:
        result.add(
            "final_state.political_reform_inventory",
            "final-state selectable political reform inventory mismatch; missing="
            + ", ".join(
                sorted(expected_political_reforms - set(political_reform_objects))
            )
            + "; foreign="
            + ", ".join(
                sorted(set(political_reform_objects) - expected_political_reforms)
            ),
            str(POLITICAL_REFORM_FILE),
        )

    reform_signatures: dict[tuple[tuple[str, str], ...], list[str]] = {}
    power_modifier_signatures: dict[str, tuple[tuple[str, str], ...]] = {}
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
        if first_scalar(definition, "basic_reform") is not None:
            result.add(
                "final_state.reform_visibility",
                f"{state.reform_id} must be a registered tier reform, not basic_reform",
                str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
            )
        for key, value, code in (
            ("allow_normal_conversion", "no", "final_state.reform_conversion"),
            ("lock_level_when_selected", "yes", "final_state.reform_lock"),
            ("maintain_dynasty", "yes", "final_state.reform_dynasty"),
        ):
            if first_scalar(definition, key) != value:
                result.add(
                    code,
                    f"{state.reform_id} must define {key} = {value}",
                    str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
                )
        if first_scalar(definition, "monarchy") is not None or first_scalar(
            definition, "republic"
        ) is not None:
            result.add(
                "final_state.reform_category_carrier",
                f"{state.reform_id} must inherit its monarchy category from its tier",
                str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
            )
        abilities = first_object(definition, "government_abilities")
        if _bare_values(abilities) != ("jxp_japanese_polity_mechanic",):
            result.add(
                "final_state.reform_mechanic",
                f"{state.reform_id} must carry only jxp_japanese_polity_mechanic",
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
        power_modifier_signatures[state.reform_id] = signature
        potential = first_object(definition, "potential")
        potential_source = REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE
        if not _exact_power_potential(
            potential,
            trigger_id=state.trigger_id,
            reform_id=state.reform_id,
        ):
            result.add(
                "final_state.reform_potential",
                f"{state.reform_id} must use `(exact {state.trigger_id} AND "
                "is_emperor_of_china = no) OR has_reform = self`",
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

    expected_eoc_modifiers = {_eoc_modifier_id(state) for state in FINAL_STATES}
    if set(eoc_power_modifier_objects) != expected_eoc_modifiers:
        result.add(
            "final_state.eoc_modifier_inventory",
            "EoC power-equivalence modifier inventory mismatch; missing="
            + ", ".join(sorted(expected_eoc_modifiers - set(eoc_power_modifier_objects)))
            + "; foreign="
            + ", ".join(sorted(set(eoc_power_modifier_objects) - expected_eoc_modifiers)),
            str(EOC_POWER_MODIFIER_FILE),
        )
    eoc_modifier_equivalence = 0
    for state in FINAL_STATES:
        modifier_id = _eoc_modifier_id(state)
        definitions = eoc_power_modifier_objects.get(modifier_id, [])
        if len(definitions) != 1:
            result.add(
                "final_state.eoc_modifier_missing",
                f"{modifier_id} has {len(definitions)} definitions; expected one",
                str(EOC_POWER_MODIFIER_FILE),
            )
            continue
        definition = definitions[0]
        potential = first_object(definition, "potential")
        trigger = first_object(definition, "trigger")
        expected_potential = tuple(
            sorted(
                (
                    ("has_reform", CELESTIAL_REFORM_ID),
                    ("is_emperor_of_china", "yes"),
                    (state.trigger_id, "yes"),
                )
            )
        )
        if _direct_scalar_signature(potential) != expected_potential:
            result.add(
                "final_state.eoc_modifier_potential",
                f"{modifier_id} must require exact {state.trigger_id}, EoC, and "
                f"{CELESTIAL_REFORM_ID}",
                str(EOC_POWER_MODIFIER_FILE),
            )
        if _direct_scalar_signature(trigger) != (("always", "yes"),):
            result.add(
                "final_state.eoc_modifier_trigger",
                f"{modifier_id} must use trigger = {{ always = yes }}",
                str(EOC_POWER_MODIFIER_FILE),
            )
        signature = _direct_scalar_signature(definition)
        expected_signature = power_modifier_signatures.get(state.reform_id, ())
        if signature != expected_signature:
            result.add(
                "final_state.eoc_modifier_equivalence",
                f"{modifier_id} modifiers are {signature}; expected exact mirror "
                f"{expected_signature} from {state.reform_id}",
                str(EOC_POWER_MODIFIER_FILE),
            )
        else:
            eoc_modifier_equivalence += 1

    celestial_definitions = celestial_reform_objects.get(CELESTIAL_REFORM_ID, [])
    celestial_reform = (
        celestial_definitions[0] if len(celestial_definitions) == 1 else None
    )
    if len(celestial_definitions) != 1:
        result.add(
            "final_state.celestial_reform_inventory",
            f"{CELESTIAL_REFORM_ID} has {len(celestial_definitions)} definitions; "
            "expected the exact vanilla identity once",
            str(CELESTIAL_REFORM_FILE),
        )
    japanese_ability_conditionals = []
    for conditional in _direct_objects(celestial_reform, "conditional"):
        allow = first_object(conditional, "allow")
        abilities = first_object(conditional, "government_abilities")
        if _bare_values(abilities) == (POLITY_MECHANIC_ID,):
            japanese_ability_conditionals.append(conditional)
            if _direct_scalar_signature(allow) != (
                ("jxp_is_japanese_polity_trigger", "yes"),
            ):
                result.add(
                    "final_state.celestial_mechanic_scope",
                    "celestial_empire may grant the JXP polity mechanic only to the "
                    "stable Japanese-polity identity gate",
                    str(CELESTIAL_REFORM_FILE),
                )
    if len(japanese_ability_conditionals) != 1:
        result.add(
            "final_state.celestial_mechanic",
            "celestial_empire must contain exactly one conditional Japanese polity mechanic",
            str(CELESTIAL_REFORM_FILE),
        )
    if _bare_values(first_object(celestial_reform, "government_abilities")):
        result.add(
            "final_state.celestial_mechanic_foreign_leak",
            "celestial_empire must not grant the JXP polity mechanic unconditionally",
            str(CELESTIAL_REFORM_FILE),
        )

    political_signatures: dict[tuple[tuple[str, str], ...], list[str]] = {}
    for state in FINAL_STATES:
        definitions = political_reform_objects.get(state.political_reform_id, [])
        if len(definitions) != 1:
            result.add(
                "final_state.political_reform_missing",
                f"{state.key} political reform {state.political_reform_id} has "
                f"{len(definitions)} definitions; expected exactly one",
                str(POLITICAL_REFORM_FILE),
            )
            continue
        definition = definitions[0]
        for key, value, code in (
            ("monarchy", "yes", "final_state.political_reform_monarchy"),
            (
                "allow_normal_conversion",
                "yes",
                "final_state.political_reform_conversion",
            ),
            (
                "valid_for_nation_designer",
                "no",
                "final_state.political_reform_nation_designer",
            ),
        ):
            if first_scalar(definition, key) != value:
                result.add(
                    code,
                    f"{state.political_reform_id} must define {key} = {value}",
                    str(POLITICAL_REFORM_FILE),
                )
        if first_scalar(definition, "icon") is None:
            result.add(
                "final_state.political_reform_icon",
                f"{state.political_reform_id} lacks an icon",
                str(POLITICAL_REFORM_FILE),
            )
        if first_scalar(definition, "basic_reform") is not None:
            result.add(
                "final_state.political_reform_basic",
                f"{state.political_reform_id} must remain a selectable tier reform, "
                "not a basic_reform power structure",
                str(POLITICAL_REFORM_FILE),
            )
        potential = first_object(definition, "potential")
        trigger = first_object(definition, "trigger")
        if not _contains_assignment(potential, state.trigger_id, "yes"):
            result.add(
                "final_state.political_reform_potential",
                f"{state.political_reform_id} potential lacks {state.trigger_id}",
                str(POLITICAL_REFORM_FILE),
            )
        if _contains_assignment(
            potential, "jxp_is_japanese_polity_trigger", "yes"
        ):
            result.add(
                "final_state.political_reform_broad_potential",
                f"{state.political_reform_id} would be visible to every Japanese polity",
                str(POLITICAL_REFORM_FILE),
            )
        if not _contains_assignment(
            potential, "has_reform", state.political_reform_id
        ):
            result.add(
                "final_state.political_reform_selected_fallback",
                f"{state.political_reform_id} does not preserve its selected state",
                str(POLITICAL_REFORM_FILE),
            )
        if not _contains_assignment(trigger, state.trigger_id, "yes"):
            result.add(
                "final_state.political_reform_trigger",
                f"{state.political_reform_id} trigger lacks {state.trigger_id}",
                str(POLITICAL_REFORM_FILE),
            )
        foreign_potential = sorted(
            candidate.trigger_id
            for candidate in FINAL_STATES
            if candidate != state
            and _contains_assignment(potential, candidate.trigger_id, "yes")
        )
        foreign_trigger = sorted(
            candidate.trigger_id
            for candidate in FINAL_STATES
            if candidate != state
            and _contains_assignment(trigger, candidate.trigger_id, "yes")
        )
        if foreign_potential or foreign_trigger:
            result.add(
                "final_state.political_reform_cross_route",
                f"{state.political_reform_id} references foreign final states: "
                + ", ".join(foreign_potential + foreign_trigger),
                str(POLITICAL_REFORM_FILE),
            )
        modifiers = first_object(definition, "modifiers")
        signature = tuple(
            sorted(
                (entry.key, entry.value.text)
                for entry in (modifiers.entries if modifiers is not None else ())
                if entry.key is not None and isinstance(entry.value, Scalar)
            )
        )
        expected_signature = POLITICAL_REFORM_MODIFIERS.get(
            state.political_reform_id, ()
        )
        if signature != expected_signature:
            result.add(
                "final_state.political_reform_modifier_manifest",
                f"{state.political_reform_id} modifiers are {signature}; "
                f"expected {expected_signature}",
                str(POLITICAL_REFORM_FILE),
            )
        political_signatures.setdefault(signature, []).append(
            state.political_reform_id
        )

    for signature, reforms in political_signatures.items():
        if signature and len(reforms) > 1:
            result.add(
                "final_state.political_reform_signature_duplicate",
                "selectable final-state reforms share an identical modifier signature: "
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

    power_active_profiles = 0
    expected_active_triggers = {
        f"jxp_final_state_{state.key}_power_active_trigger" for state in FINAL_STATES
    }
    actual_active_triggers = {
        trigger_id
        for trigger_id in trigger_objects
        if trigger_id.startswith("jxp_final_state_")
        and trigger_id.endswith("_power_active_trigger")
    }
    if actual_active_triggers != expected_active_triggers:
        result.add(
            "final_state.power_active_inventory",
            "state-aware capstone power triggers mismatch; missing="
            + ", ".join(sorted(expected_active_triggers - actual_active_triggers))
            + "; foreign="
            + ", ".join(sorted(actual_active_triggers - expected_active_triggers)),
            str(TRIGGER_FILE),
        )
    for state in FINAL_STATES:
        active_id = f"jxp_final_state_{state.key}_power_active_trigger"
        definitions = trigger_objects.get(active_id, [])
        if len(definitions) != 1 or not _exact_power_active_trigger(
            definitions[0] if len(definitions) == 1 else None,
            trigger_id=state.trigger_id,
            reform_id=state.reform_id,
        ):
            result.add(
                "final_state.power_active_shape",
                f"{active_id} must require exact state plus either the non-EoC route "
                f"reform or EoC {CELESTIAL_REFORM_ID}",
                str(TRIGGER_FILE),
            )
            continue
        base_profile = profiles.get(state.profile_name)
        if base_profile is None:
            continue
        for emperor, reforms, label in (
            (False, frozenset({state.reform_id}), "non-EoC"),
            (True, frozenset({CELESTIAL_REFORM_ID}), "EoC"),
        ):
            profile = replace(
                base_profile,
                name=f"{state.profile_name} ({label} power active)",
                emperor_of_china=emperor,
                reforms=reforms,
            )
            matched = []
            for candidate in FINAL_STATES:
                candidate_id = (
                    f"jxp_final_state_{candidate.key}_power_active_trigger"
                )
                candidate_definitions = trigger_objects.get(candidate_id, [])
                if len(candidate_definitions) != 1:
                    continue
                values, unknown = _evaluate_final_reform_predicate(
                    candidate_definitions[0], profile, trigger_objects
                )
                for predicate in unknown:
                    result.add(
                        "final_state.power_active_predicate_unknown",
                        f"{candidate_id} uses unsupported predicate {predicate}",
                        str(TRIGGER_FILE),
                    )
                if True in values:
                    matched.append(candidate_id)
            if matched != [active_id]:
                result.add(
                    "final_state.power_active_matrix",
                    f"{profile.name} matches {matched}; expected {[active_id]}",
                    str(TRIGGER_FILE),
                )
            else:
                power_active_profiles += 1

    political_visibility_profiles = 0
    political_selectability_profiles = 0
    power_visibility_profiles = 0
    eoc_power_visibility_profiles = 0
    eoc_modifier_profiles = 0
    eoc_political_visibility_profiles = 0
    eoc_political_selectability_profiles = 0
    for profile_name, profile in profiles.items():
        expected_state = next(
            (state for state in FINAL_STATES if state.profile_name == profile_name),
            None,
        )
        if expected_state is None:
            continue
        expected = {expected_state.political_reform_id}
        expected_power = {expected_state.reform_id}
        visible_power: set[str] = set()
        visible: set[str] = set()
        selectable: set[str] = set()
        for state in FINAL_STATES:
            source_objects = reform_objects if state.new_reform else legacy_reform_objects
            power_definitions = source_objects.get(state.reform_id, [])
            if len(power_definitions) == 1:
                power_potential = first_object(power_definitions[0], "potential")
                power_values, power_unknown = _evaluate_final_reform_predicate(
                    power_potential, profile, trigger_objects
                )
                for unknown in power_unknown:
                    result.add(
                        "final_state.power_predicate_unknown",
                        f"{state.reform_id} uses unsupported predicate {unknown}",
                        str(REFORM_FILE if state.new_reform else LEGACY_REFORM_FILE),
                    )
                if True in power_values:
                    visible_power.add(state.reform_id)
            definitions = political_reform_objects.get(
                state.political_reform_id, []
            )
            if len(definitions) != 1:
                continue
            potential = first_object(definitions[0], "potential")
            trigger = first_object(definitions[0], "trigger")
            potential_values, potential_unknown = _evaluate_final_reform_predicate(
                potential, profile, trigger_objects
            )
            trigger_values, trigger_unknown = _evaluate_final_reform_predicate(
                trigger, profile, trigger_objects
            )
            for unknown in (*potential_unknown, *trigger_unknown):
                result.add(
                    "final_state.political_predicate_unknown",
                    f"{state.political_reform_id} uses unsupported predicate {unknown}",
                    str(POLITICAL_REFORM_FILE),
                )
            if True in potential_values:
                visible.add(state.political_reform_id)
                if True in trigger_values:
                    selectable.add(state.political_reform_id)
        if visible_power != expected_power:
            result.add(
                "final_state.power_visibility_matrix",
                f"profile {profile_name} sees power structures {sorted(visible_power)}; "
                f"expected {sorted(expected_power)}",
                str(REFORM_FILE),
            )
        else:
            power_visibility_profiles += 1
        if visible != expected:
            result.add(
                "final_state.political_visibility_matrix",
                f"profile {profile_name} sees {sorted(visible)}; expected {sorted(expected)}",
                str(POLITICAL_REFORM_FILE),
            )
        else:
            political_visibility_profiles += 1
        if selectable != expected:
            result.add(
                "final_state.political_selectability_matrix",
                f"profile {profile_name} can select {sorted(selectable)}; "
                f"expected {sorted(expected)}",
                str(POLITICAL_REFORM_FILE),
            )
        else:
            political_selectability_profiles += 1

        active_non_eoc_modifiers: set[str] = set()
        for candidate in FINAL_STATES:
            definitions = eoc_power_modifier_objects.get(_eoc_modifier_id(candidate), [])
            if len(definitions) != 1:
                continue
            values, unknown = _evaluate_final_reform_predicate(
                first_object(definitions[0], "potential"), profile, trigger_objects
            )
            for predicate in unknown:
                result.add(
                    "final_state.eoc_modifier_predicate_unknown",
                    f"{_eoc_modifier_id(candidate)} uses unsupported predicate {predicate}",
                    str(EOC_POWER_MODIFIER_FILE),
                )
            if True in values:
                active_non_eoc_modifiers.add(_eoc_modifier_id(candidate))
        if active_non_eoc_modifiers:
            result.add(
                "final_state.eoc_modifier_non_eoc_leak",
                f"non-EoC profile {profile_name} activates "
                f"{sorted(active_non_eoc_modifiers)}",
                str(EOC_POWER_MODIFIER_FILE),
            )

        eoc_profile = replace(
            profile,
            name=f"{profile_name} (EoC)",
            emperor_of_china=True,
            reforms=frozenset({CELESTIAL_REFORM_ID}),
        )
        visible_eoc_power: set[str] = set()
        visible_eoc_political: set[str] = set()
        selectable_eoc_political: set[str] = set()
        active_eoc_modifiers: set[str] = set()
        for candidate in FINAL_STATES:
            source_objects = (
                reform_objects if candidate.new_reform else legacy_reform_objects
            )
            power_definitions = source_objects.get(candidate.reform_id, [])
            if len(power_definitions) == 1:
                values, unknown = _evaluate_final_reform_predicate(
                    first_object(power_definitions[0], "potential"),
                    eoc_profile,
                    trigger_objects,
                )
                for predicate in unknown:
                    result.add(
                        "final_state.power_predicate_unknown",
                        f"{candidate.reform_id} uses unsupported predicate {predicate}",
                        str(REFORM_FILE if candidate.new_reform else LEGACY_REFORM_FILE),
                    )
                if True in values:
                    visible_eoc_power.add(candidate.reform_id)

            political_definitions = political_reform_objects.get(
                candidate.political_reform_id, []
            )
            if len(political_definitions) == 1:
                potential_values, potential_unknown = _evaluate_final_reform_predicate(
                    first_object(political_definitions[0], "potential"),
                    eoc_profile,
                    trigger_objects,
                )
                trigger_values, trigger_unknown = _evaluate_final_reform_predicate(
                    first_object(political_definitions[0], "trigger"),
                    eoc_profile,
                    trigger_objects,
                )
                for predicate in (*potential_unknown, *trigger_unknown):
                    result.add(
                        "final_state.political_predicate_unknown",
                        f"{candidate.political_reform_id} uses unsupported predicate "
                        f"{predicate}",
                        str(POLITICAL_REFORM_FILE),
                    )
                if True in potential_values:
                    visible_eoc_political.add(candidate.political_reform_id)
                    if True in trigger_values:
                        selectable_eoc_political.add(candidate.political_reform_id)

            modifier_definitions = eoc_power_modifier_objects.get(
                _eoc_modifier_id(candidate), []
            )
            if len(modifier_definitions) == 1:
                values, unknown = _evaluate_final_reform_predicate(
                    first_object(modifier_definitions[0], "potential"),
                    eoc_profile,
                    trigger_objects,
                )
                for predicate in unknown:
                    result.add(
                        "final_state.eoc_modifier_predicate_unknown",
                        f"{_eoc_modifier_id(candidate)} uses unsupported predicate "
                        f"{predicate}",
                        str(EOC_POWER_MODIFIER_FILE),
                    )
                if True in values:
                    active_eoc_modifiers.add(_eoc_modifier_id(candidate))

        expected_eoc_modifier = {_eoc_modifier_id(expected_state)}
        if visible_eoc_power:
            result.add(
                "final_state.eoc_power_visibility_matrix",
                f"EoC profile {profile_name} sees route tier-one reforms "
                f"{sorted(visible_eoc_power)}; expected none beside celestial_empire",
                str(REFORM_FILE),
            )
        else:
            eoc_power_visibility_profiles += 1
        if active_eoc_modifiers != expected_eoc_modifier:
            result.add(
                "final_state.eoc_modifier_matrix",
                f"EoC profile {profile_name} activates {sorted(active_eoc_modifiers)}; "
                f"expected {sorted(expected_eoc_modifier)}",
                str(EOC_POWER_MODIFIER_FILE),
            )
        else:
            eoc_modifier_profiles += 1
        if visible_eoc_political != expected:
            result.add(
                "final_state.eoc_political_visibility_matrix",
                f"EoC profile {profile_name} sees {sorted(visible_eoc_political)}; "
                f"expected {sorted(expected)}",
                str(POLITICAL_REFORM_FILE),
            )
        else:
            eoc_political_visibility_profiles += 1
        if selectable_eoc_political != expected:
            result.add(
                "final_state.eoc_political_selectability_matrix",
                f"EoC profile {profile_name} can select "
                f"{sorted(selectable_eoc_political)}; expected {sorted(expected)}",
                str(POLITICAL_REFORM_FILE),
            )
        else:
            eoc_political_selectability_profiles += 1

    foreign_eoc = replace(
        profiles["JAP Shinto (uncommitted)"],
        name="foreign EoC",
        tag="MNG",
        japanese_polity=False,
        flags=frozenset(),
        reforms=frozenset({CELESTIAL_REFORM_ID}),
        emperor_of_china=True,
    )
    foreign_eoc_modifiers = set()
    for state in FINAL_STATES:
        definitions = eoc_power_modifier_objects.get(_eoc_modifier_id(state), [])
        if len(definitions) != 1:
            continue
        values, _unknown = _evaluate_final_reform_predicate(
            first_object(definitions[0], "potential"), foreign_eoc, trigger_objects
        )
        if True in values:
            foreign_eoc_modifiers.add(_eoc_modifier_id(state))
    if foreign_eoc_modifiers:
        result.add(
            "final_state.eoc_modifier_foreign_leak",
            f"foreign Emperor of China activates {sorted(foreign_eoc_modifiers)}",
            str(EOC_POWER_MODIFIER_FILE),
        )

    government_source = context.mod_root / GOVERNMENT_FILE
    government_document = (
        context.document(government_source) if government_source.is_file() else None
    )
    registrations = (
        _reform_registration_paths(government_document.root)
        if government_document is not None
        else ()
    )
    for state in FINAL_STATES:
        power_paths = [
            path
            for reform_id, path in registrations
            if reform_id == state.reform_id
        ]
        expected_power_path = (
            "monarchy",
            "reform_levels",
            "feudalism_vs_autocracy",
        )
        if power_paths != [expected_power_path]:
            result.add(
                "final_state.power_reform_registration",
                f"{state.reform_id} is registered at {power_paths}; "
                f"expected exactly {[expected_power_path]}",
                str(GOVERNMENT_FILE),
            )
        paths = [
            path
            for reform_id, path in registrations
            if reform_id == state.political_reform_id
        ]
        expected_path = (
            "monarchy",
            "reform_levels",
            POLITICAL_REFORM_TIER,
        )
        if paths != [expected_path]:
            result.add(
                "final_state.political_reform_registration",
                f"{state.political_reform_id} is registered at {paths}; "
                f"expected exactly {[expected_path]}",
                str(GOVERNMENT_FILE),
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
    non_celestial_sync = effect_objects.get(
        "jxp_sync_non_celestial_final_state_power_structure_effect", []
    )
    celestial_sync = effect_objects.get(
        "jxp_sync_celestial_final_state_power_structure_effect", []
    )
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

    political_sanitizers = effect_objects.get(
        "jxp_sanitize_final_state_political_reforms_effect", []
    )
    political_sanitizer = (
        political_sanitizers[0] if len(political_sanitizers) == 1 else None
    )
    political_removed = _assignment_values(
        political_sanitizer, "remove_government_reform"
    )
    political_checked = _assignment_values(political_sanitizer, "has_reform")
    if (
        len(political_sanitizers) != 1
        or set(political_removed) != expected_political_reforms
        or len(political_removed) != len(expected_political_reforms)
        or set(political_checked) != expected_political_reforms
        or len(political_checked) != len(expected_political_reforms)
    ):
        result.add(
            "final_state.political_sanitizer_inventory",
            "political reform sanitizer must inspect and remove all ten selectable "
            "final-state reforms exactly once",
            str(EFFECT_FILE),
        )
    sanitizer_branches = [
        entry.value
        for entry in (
            political_sanitizer.entries if political_sanitizer is not None else ()
        )
        if entry.key == "if" and isinstance(entry.value, Object)
    ]
    for state in FINAL_STATES:
        matching = [
            branch
            for branch in sanitizer_branches
            if _contains_assignment(
                first_object(branch, "limit"),
                "has_reform",
                state.political_reform_id,
            )
            and _contains_assignment(
                first_object(first_object(branch, "limit"), "NOT"),
                state.trigger_id,
                "yes",
            )
            and _contains_assignment(
                branch,
                "remove_government_reform",
                state.political_reform_id,
            )
        ]
        if len(matching) != 1:
            result.add(
                "final_state.political_sanitizer_mapping",
                f"{state.political_reform_id} must be removed exactly once when "
                f"{state.trigger_id} is false",
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

    capstone_sanitizers = effect_objects.get(
        "jxp_sanitize_final_state_capstone_modifiers_effect", []
    )
    capstone_sanitizer = (
        capstone_sanitizers[0] if len(capstone_sanitizers) == 1 else None
    )
    sanitized_capstones = _assignment_values(
        capstone_sanitizer, "remove_country_modifier"
    )
    inspected_capstones = _assignment_values(
        capstone_sanitizer, "has_country_modifier"
    )
    if (
        len(capstone_sanitizers) != 1
        or set(sanitized_capstones) != expected_modifiers
        or len(sanitized_capstones) != len(expected_modifiers)
        or set(inspected_capstones) != expected_modifiers
        or len(inspected_capstones) != len(expected_modifiers)
    ):
        result.add(
            "final_state.capstone_sanitizer_inventory",
            "state-aware capstone sanitizer must inspect and remove all ten modifiers once",
            str(EFFECT_FILE),
        )
    capstone_sanitizer_branches = _direct_objects(capstone_sanitizer, "if")
    for state in FINAL_STATES:
        matching = [
            branch
            for branch in capstone_sanitizer_branches
            if _contains_assignment(
                first_object(branch, "limit"),
                "has_country_modifier",
                state.modifier_id,
            )
            and _contains_assignment(
                first_object(first_object(branch, "limit"), "NOT"),
                state.trigger_id,
                "yes",
            )
            and _contains_assignment(
                branch, "remove_country_modifier", state.modifier_id
            )
        ]
        if len(matching) != 1:
            result.add(
                "final_state.capstone_sanitizer_mapping",
                f"{state.modifier_id} must be removed exactly once outside "
                f"{state.trigger_id}",
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
    non_celestial_obj = (
        non_celestial_sync[0] if len(non_celestial_sync) == 1 else None
    )
    celestial_obj = celestial_sync[0] if len(celestial_sync) == 1 else None
    if non_celestial_obj is None:
        result.add(
            "final_state.non_celestial_sync_missing",
            "non-EoC final-state sync helper must be defined exactly once",
            str(EFFECT_FILE),
        )
    if celestial_obj is None:
        result.add(
            "final_state.celestial_sync_missing",
            "EoC final-state sync helper must be defined exactly once",
            str(EFFECT_FILE),
        )
    if not _contains_assignment(
        sync_obj, "jxp_sanitize_final_state_political_reforms_effect", "yes"
    ):
        result.add(
            "final_state.political_sync_without_sanitizer",
            "canonical final-state sync must sanitize stale selectable political reforms",
            str(EFFECT_FILE),
        )
    if not _contains_assignment(
        sync_obj, "jxp_sanitize_final_state_capstone_modifiers_effect", "yes"
    ):
        result.add(
            "final_state.capstone_sync_without_sanitizer",
            "canonical final-state sync must remove only foreign-state capstone modifiers",
            str(EFFECT_FILE),
        )
    if not _contains_assignment(sync_obj, "regenerate_government_mechanics", "yes"):
        result.add(
            "final_state.sync_without_regenerate",
            "canonical sync must regenerate government mechanics",
            str(EFFECT_FILE),
        )
    hidden = first_object(sync_obj, "hidden_effect")
    split_branches = tuple(
        branch
        for branch in _direct_objects(hidden, "if")
        if _direct_scalar_signature(first_object(branch, "limit"))
        == (("is_emperor_of_china", "yes"),)
    )
    split_else = tuple(
        branch
        for branch in _direct_objects(hidden, "else")
        if _contains_assignment(
            branch,
            "jxp_sync_non_celestial_final_state_power_structure_effect",
            "yes",
        )
    )
    valid_split = (
        len(split_branches) == 1
        and _contains_assignment(
            split_branches[0],
            "jxp_sync_celestial_final_state_power_structure_effect",
            "yes",
        )
        and len(split_else) == 1
    )
    if not valid_split:
        result.add(
            "final_state.sync_eoc_split",
            "canonical sync must route EoC and non-EoC states to distinct helpers",
            str(EFFECT_FILE),
        )

    added = _assignment_values(non_celestial_obj, "add_government_reform")
    if set(added) != expected_reforms or len(added) != len(expected_reforms):
        result.add(
            "final_state.sync_inventory",
            "non-EoC sync must add each of the ten power structures exactly once",
            str(EFFECT_FILE),
        )
    branches = [
        entry.value
        for entry in (non_celestial_obj.entries if non_celestial_obj is not None else ())
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
            and _contains_assignment(branch, "add_government_reform", state.reform_id)
        ]
        if len(matching) != 1:
            result.add(
                "final_state.sync_mapping",
                f"{state.trigger_id} must map once to {state.reform_id} behind "
                f"mismatch guard {mismatch_id}",
                str(EFFECT_FILE),
            )
        elif _contains_assignment(
            matching[0], "jxp_clear_final_state_capstone_modifiers_effect", "yes"
        ):
            result.add(
                "final_state.sync_mapping_destructive_capstone_clear",
                f"{state.trigger_id} must preserve its own completed capstone while "
                "repairing the route reform",
                str(EFFECT_FILE),
            )
    orphan_modifier_checks = _assignment_values(
        non_celestial_obj, "has_country_modifier"
    )
    if (
        set(orphan_modifier_checks) != expected_modifiers
        or len(orphan_modifier_checks) != len(expected_modifiers)
    ):
        result.add(
            "final_state.orphan_capstone_cleanup",
            "non-final states are not checked for all ten orphaned capstone modifiers",
            str(EFFECT_FILE),
        )

    celestial_removals = _assignment_values(
        non_celestial_obj, "remove_government_reform"
    )
    celestial_checks = _assignment_values(non_celestial_obj, "has_reform")
    if celestial_removals.count(CELESTIAL_REFORM_ID) != 1 or celestial_checks.count(
        CELESTIAL_REFORM_ID
    ) != 1:
        result.add(
            "final_state.non_celestial_clears_celestial",
            "non-EoC sync must inspect and remove a residual celestial_empire exactly once",
            str(EFFECT_FILE),
        )
    celestial_added = _assignment_values(celestial_obj, "add_government_reform")
    celestial_has = _assignment_values(celestial_obj, "has_reform")
    if not _contains_assignment(
        celestial_obj, "jxp_clear_final_state_power_structures_effect", "yes"
    ) or celestial_added != (CELESTIAL_REFORM_ID,) or celestial_has.count(
        CELESTIAL_REFORM_ID
    ) != 1:
        result.add(
            "final_state.celestial_sync_postcondition",
            "EoC sync must clear every JXP tier-one reform and ensure celestial_empire once",
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

    political_migration = _event_by_id(
        context, MIGRATION_FILE, "jxp_migration_v028.2"
    )
    if political_migration is None:
        result.add(
            "final_state.political_migration_missing",
            "0.28.3 selectable political-reform migration event is missing",
            str(MIGRATION_FILE),
        )
    else:
        trigger = first_object(political_migration, "trigger")
        immediate = first_object(political_migration, "immediate")
        if not _contains_assignment(
            trigger, "has_country_flag", POLITICAL_MIGRATION_FLAG
        ):
            result.add(
                "final_state.political_migration_guard",
                f"0.28.3 migration is not guarded by {POLITICAL_MIGRATION_FLAG}",
                str(MIGRATION_FILE),
            )
        if not _contains_assignment(
            immediate, "jxp_sync_final_state_power_structure_effect", "yes"
        ):
            result.add(
                "final_state.political_migration_sync",
                "0.28.3 migration does not rebuild final-state reform candidates",
                str(MIGRATION_FILE),
            )
        if not _contains_assignment(
            immediate, "set_country_flag", POLITICAL_MIGRATION_FLAG
        ):
            result.add(
                "final_state.political_migration_flag",
                f"0.28.3 migration does not set {POLITICAL_MIGRATION_FLAG}",
                str(MIGRATION_FILE),
            )
        forbidden_mission_mutations = (
            "jxp_refresh_route_missions_effect",
            "swap_non_generic_missions",
        )
        for key in forbidden_mission_mutations:
            if _contains_assignment(immediate, key):
                result.add(
                    "final_state.political_migration_mission_mutation",
                    f"0.28.3 reform-only migration must not call {key}",
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
    if "jxp_migration_v028.2" not in startup_event_ids:
        result.add(
            "final_state.political_migration_on_startup",
            "0.28.3 selectable political-reform migration is not registered on_startup",
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
    mandate_action_wiring = 0
    for action in ("on_mandate_of_heaven_gained", "on_mandate_of_heaven_lost"):
        objects = on_actions.get(action, [])
        valid = False
        if len(objects) == 1:
            branches = _direct_objects(objects[0], "if")
            valid = (
                len(branches) == 1
                and _direct_scalar_signature(first_object(branches[0], "limit"))
                == (("jxp_is_japanese_polity_trigger", "yes"),)
                and _contains_assignment(
                    branches[0],
                    "jxp_sync_final_state_power_structure_effect",
                    "yes",
                )
                and _contains_assignment(
                    branches[0],
                    "jxp_reconcile_hakko_ichiu_reform_visibility_effect",
                    "yes",
                )
            )
        if not valid:
            result.add(
                "final_state.mandate_change_wiring",
                f"{action} must reconcile Japanese final-state and Hakko identities "
                "without affecting foreign emperors",
                str(ON_ACTION_FILE),
            )
        else:
            mandate_action_wiring += 1

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
    political_debug_has_clear = any(
        _contains_assignment(obj, "clr_country_flag", POLITICAL_MIGRATION_FLAG)
        for objects in debug_objects.values()
        for obj in objects
    )
    if not political_debug_has_clear:
        result.add(
            "final_state.political_debug_cleanup",
            f"debug cleanup does not clear {POLITICAL_MIGRATION_FLAG}",
            str(DEBUG_FILE),
        )

    debug_decision_roots = _top_objects(context, DEBUG_DECISION_FILE).get(
        "country_decisions", []
    )
    debug_decision = (
        first_object(
            debug_decision_roots[0],
            "jxp_debug_80_refresh_final_state_reforms",
        )
        if len(debug_decision_roots) == 1
        else None
    )
    debug_effect = first_object(debug_decision, "effect")
    if (
        first_scalar(debug_effect, "change_government_reform_progress") != "5000"
        or not _contains_assignment(
            debug_effect, "jxp_sanitize_final_state_political_reforms_effect", "yes"
        )
        or not _contains_assignment(
            debug_effect, "jxp_sync_final_state_power_structure_effect", "yes"
        )
    ):
        result.add(
            "final_state.political_debug_decision",
            "final-state reform debug decision must grant 5000 progress, sanitize stale "
            "choices, and rebuild government mechanics",
            str(DEBUG_DECISION_FILE),
        )
    baseline_objects = debug_objects.get("jxp_debug_return_jap_baseline_effect", [])
    baseline_hidden = (
        first_object(baseline_objects[0], "hidden_effect")
        if len(baseline_objects) == 1
        else None
    )
    baseline_setup_order = (
        tuple(
            entry.key
            for entry in baseline_hidden.entries
            if entry.key
            in {
                "jxp_debug_clear_route_state_effect",
                "jxp_debug_clear_event_state_effect",
                "jxp_debug_prepare_polity_effect",
            }
        )
        if baseline_hidden is not None
        else ()
    )
    if baseline_setup_order != (
        "jxp_debug_clear_route_state_effect",
        "jxp_debug_clear_event_state_effect",
        "jxp_debug_prepare_polity_effect",
    ):
        result.add(
            "final_state.debug_baseline_order",
            "JAP baseline reset must clear route/event state before rebuilding polity state",
            str(DEBUG_FILE),
        )
    if not _contains_assignment(baseline_hidden, "tag", "TOY"):
        result.add(
            "final_state.debug_baseline_toy",
            "JAP baseline reset does not return TOY to JAP",
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
        active_trigger_id = f"jxp_final_state_{state.key}_power_active_trigger"
        if not _contains_assignment(trigger, active_trigger_id, "yes"):
            result.add(
                "final_state.capstone_reform_gate",
                f"{state.mission_id} is not gated by {active_trigger_id}; direct reform "
                "checks would strand the capstone after taking the Mandate",
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
        eoc_modifier_id = _eoc_modifier_id(state)
        if eoc_modifier_id not in localisation_keys:
            result.add(
                "final_state.eoc_modifier_localisation",
                f"{eoc_modifier_id} is not localised",
                str(SOURCE_LOC_FILE),
            )
        for key in (state.reform_id, state.reform_id + "_desc"):
            if key not in localisation_keys:
                result.add(
                    "final_state.reform_localisation",
                    f"{state.reform_id} is missing localisation key {key}",
                    str(SOURCE_LOC_FILE if state.new_reform else LEGACY_REFORM_FILE),
                )
        for key in (
            state.political_reform_id,
            state.political_reform_id + "_desc",
        ):
            if key not in localisation_keys:
                result.add(
                    "final_state.political_reform_localisation",
                    f"{state.political_reform_id} is missing localisation key {key}",
                    str(POLITICAL_SOURCE_LOC_FILE),
                )
    _check_localisation_pipeline(context, result)
    _check_localisation_pipeline(
        context,
        result,
        POLITICAL_SOURCE_LOC_FILE,
        POLITICAL_ACTIVE_LOC_FILE,
        "final_state.political",
        "final-state political-reform",
    )

    result.metrics.update(
        {
            "final_states": len(FINAL_STATES),
            "power_structures": len(expected_reforms),
            "new_power_structures": len(new_expected),
            "reused_power_structures": len(expected_reforms - new_expected),
            "selectable_political_reforms": len(expected_political_reforms),
            "political_visibility_profiles": political_visibility_profiles,
            "political_selectability_profiles": political_selectability_profiles,
            "power_visibility_profiles": power_visibility_profiles,
            "eoc_power_visibility_profiles": eoc_power_visibility_profiles,
            "eoc_power_modifier_profiles": eoc_modifier_profiles,
            "eoc_modifier_equivalence": eoc_modifier_equivalence,
            "eoc_political_visibility_profiles": eoc_political_visibility_profiles,
            "eoc_political_selectability_profiles": eoc_political_selectability_profiles,
            "power_active_profiles": power_active_profiles,
            "mandate_action_wiring": mandate_action_wiring,
            "political_sanitizer_cleanup": len(political_removed),
            "exclusive_trigger_profiles": sum(
                len(matches) == 1 for matches in trigger_matches.values()
            ),
            "political_capstones": len(FINAL_STATES),
            "capstone_modifiers": len(expected_modifiers),
            "capstone_cleanup": len(cleared_modifiers),
            "capstone_sanitizer_cleanup": len(sanitized_capstones),
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
        "10 exclusive final-state power structures, 10 selectable political reforms, "
        "10 EoC-equivalent power modifiers, and 10 political capstones; "
        "Mandate gain/loss plus next-day reconciliation"
    )
    return result
