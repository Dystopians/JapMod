"""Validate the Sakoku, Open Trade, and Imperial route-council slice.

The checker deliberately fixes the complete interaction contract instead of
only counting content.  A route council is valid when its route gate is
defensively exclusive, its three visible reforms each own one option, every
option changes era attributes and creates only finite state, the player and
debug decisions reach the same event, and canonical debug reset removes every
modifier written by the slice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .clausewitz import (
    Document,
    Entry,
    Object,
    Scalar,
    entries_named,
    find_assignments,
    first_object,
    first_scalar,
    parse_text,
)
from .core import CheckResult, ValidationContext


TRIGGER_FILE = Path("common/scripted_triggers/jxp_71_route_parity_triggers.txt")
EVENT_FILE = Path("events/jxp_71_route_parity_events.txt")
DECISION_FILE = Path("decisions/jxp_71_route_parity_decisions.txt")
DEBUG_DECISION_FILE = Path("decisions/jxp_71_route_parity_debug_decisions.txt")
MODIFIER_FILE = Path("common/event_modifiers/jxp_71_route_parity_modifiers.txt")
DEBUG_EFFECT_FILE = Path("common/scripted_effects/jxp_debug_effects.txt")
ROUTE_EFFECT_FILE = Path("common/scripted_effects/jxp_scripted_effects.txt")
SOURCE_LOC_FILE = Path(
    "localisation_source/jxp_71_route_parity_l_english_utf8_source.yml"
)
ACTIVE_LOC_FILE = Path("localisation/jxp_71_route_parity_l_english.yml")

COOLDOWN_MODIFIER = "jxp_71_route_council_recent"
COOLDOWN_DAYS = "3650"
ERA_EFFECT_PATTERN = re.compile(
    r"^jxp_(?:add|subtract)_(?:tenka_order|imperial_sanction|oceanic_opening)_"
    r"(?:5|10|15)_effect$"
)
COMPANION_ONLY_REFERENCE = re.compile(
    r"\bjxp_map_[A-Za-z0-9_]+\b|\b49(?:4[2-9]|[5-7][0-9]|8[01])\b"
)
RAW_CJK = re.compile(r"[\u3400-\u9fff]")


@dataclass(frozen=True, slots=True)
class OptionContract:
    reform: str
    option_key: str
    outcome_modifier: str
    era_effects: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RouteContract:
    slug: str
    route_trigger: str
    reform_trigger: str
    event_id: str
    decision_id: str
    debug_decision_id: str
    power_trigger: str
    power_effect: str
    options: tuple[OptionContract, ...]


ROUTES = (
    RouteContract(
        slug="sakoku",
        route_trigger="jxp_71_is_sakoku_route_trigger",
        reform_trigger="jxp_71_has_sakoku_council_reform_trigger",
        event_id="jxp_route_parity.1",
        decision_id="jxp_decision_review_sakoku_council",
        debug_decision_id="jxp_debug_fire_route_parity_sakoku",
        power_trigger="adm_power",
        power_effect="add_adm_power",
        options=(
            OptionContract(
                "jxp_reform_sakoku_sankin_kotai_roads",
                "jxp_route_parity.1.a",
                "jxp_71_sakoku_post_road_registers",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_add_imperial_sanction_5_effect",
                    "jxp_subtract_oceanic_opening_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_sakoku_coastal_barriers",
                "jxp_route_parity.1.b",
                "jxp_71_sakoku_coastal_musters",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_subtract_oceanic_opening_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_sakoku_hidden_learning",
                "jxp_route_parity.1.c",
                "jxp_71_sakoku_sealed_translation_room",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_subtract_tenka_order_5_effect",
                ),
            ),
        ),
    ),
    RouteContract(
        slug="open_trade",
        route_trigger="jxp_71_is_open_trade_route_trigger",
        reform_trigger="jxp_71_has_open_trade_council_reform_trigger",
        event_id="jxp_route_parity.2",
        decision_id="jxp_decision_audit_open_trade_council",
        debug_decision_id="jxp_debug_fire_route_parity_open_trade",
        power_trigger="dip_power",
        power_effect="add_dip_power",
        options=(
            OptionContract(
                "jxp_reform_open_silver_exchange",
                "jxp_route_parity.2.a",
                "jxp_71_open_silver_assay_board",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_add_tenka_order_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_open_foreign_artillery_contracts",
                "jxp_route_parity.2.b",
                "jxp_71_open_artillery_inspectors",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_add_tenka_order_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_open_chartered_factories",
                "jxp_route_parity.2.c",
                "jxp_71_open_charter_auditors",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
        ),
    ),
    RouteContract(
        slug="imperial",
        route_trigger="jxp_71_is_imperial_route_trigger",
        reform_trigger="jxp_71_has_imperial_council_reform_trigger",
        event_id="jxp_route_parity.3",
        decision_id="jxp_decision_convene_imperial_circuit_council",
        debug_decision_id="jxp_debug_fire_route_parity_imperial",
        power_trigger="adm_power",
        power_effect="add_adm_power",
        options=(
            OptionContract(
                "jxp_reform_imperial_kokugaku_office",
                "jxp_route_parity.3.a",
                "jxp_71_imperial_rite_register",
                (
                    "jxp_add_imperial_sanction_5_effect",
                    "jxp_subtract_oceanic_opening_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_imperial_kokushi_governors",
                "jxp_route_parity.3.b",
                "jxp_71_imperial_kokushi_circuit",
                (
                    "jxp_add_imperial_sanction_5_effect",
                    "jxp_add_tenka_order_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_imperial_restoration_army",
                "jxp_route_parity.3.c",
                "jxp_71_imperial_guard_muster",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_add_imperial_sanction_5_effect",
                    "jxp_subtract_oceanic_opening_5_effect",
                ),
            ),
        ),
    ),
)

OUTCOME_MODIFIERS = tuple(
    option.outcome_modifier for route in ROUTES for option in route.options
)
EXPECTED_MODIFIERS = (COOLDOWN_MODIFIER,) + OUTCOME_MODIFIERS


_EXPECTED_TRIGGER_DOCUMENT = parse_text(
    r"""
jxp_71_is_sakoku_route_trigger = {
	tag = JAP
	jxp_is_japanese_polity_trigger = yes
	has_country_flag = jxp_path_sakoku
	NOT = { OR = {
		has_country_flag = jxp_path_open_trade
		has_country_flag = jxp_path_kirishitan
		has_country_flag = jxp_path_confucian
		has_country_flag = jxp_path_imperial
		has_country_flag = jxp_path_reformed
		has_country_flag = jxp_path_kaikyo
		has_country_flag = jxp_path_ikko
		has_country_flag = jxp_path_wokou
	} }
}
jxp_71_is_open_trade_route_trigger = {
	tag = JAP
	jxp_is_japanese_polity_trigger = yes
	has_country_flag = jxp_path_open_trade
	NOT = { OR = {
		has_country_flag = jxp_path_sakoku
		has_country_flag = jxp_path_kirishitan
		has_country_flag = jxp_path_confucian
		has_country_flag = jxp_path_imperial
		has_country_flag = jxp_path_reformed
		has_country_flag = jxp_path_kaikyo
		has_country_flag = jxp_path_ikko
		has_country_flag = jxp_path_wokou
	} }
}
jxp_71_is_imperial_route_trigger = {
	jxp_is_japanese_polity_trigger = yes
	OR = { tag = EJP has_country_flag = jxp_path_imperial }
	NOT = { OR = {
		has_country_flag = jxp_path_sakoku
		has_country_flag = jxp_path_open_trade
		has_country_flag = jxp_path_kirishitan
		has_country_flag = jxp_path_confucian
		has_country_flag = jxp_path_reformed
		has_country_flag = jxp_path_kaikyo
		has_country_flag = jxp_path_ikko
		has_country_flag = jxp_path_wokou
	} }
}
jxp_71_has_sakoku_council_reform_trigger = { OR = {
	has_reform = jxp_reform_sakoku_sankin_kotai_roads
	has_reform = jxp_reform_sakoku_coastal_barriers
	has_reform = jxp_reform_sakoku_hidden_learning
} }
jxp_71_has_open_trade_council_reform_trigger = { OR = {
	has_reform = jxp_reform_open_silver_exchange
	has_reform = jxp_reform_open_foreign_artillery_contracts
	has_reform = jxp_reform_open_chartered_factories
} }
jxp_71_has_imperial_council_reform_trigger = { OR = {
	has_reform = jxp_reform_imperial_kokugaku_office
	has_reform = jxp_reform_imperial_kokushi_governors
	has_reform = jxp_reform_imperial_restoration_army
} }
"""
)
EXPECTED_TRIGGER_BODIES = {
    entry.key: entry.value
    for entry in _EXPECTED_TRIGGER_DOCUMENT.root.entries
    if entry.key is not None and isinstance(entry.value, Object)
}


def _canonical_object(obj: Object) -> tuple[object, ...]:
    members: list[tuple[object, ...]] = []
    for entry in obj.entries:
        if isinstance(entry.value, Object):
            value: tuple[object, ...] = ("object", _canonical_object(entry.value))
        else:
            value = ("scalar", entry.value.text)
        members.append((entry.key, entry.operator, value))
    return tuple(sorted(members, key=repr))


def _document(
    context: ValidationContext, relative: Path, result: CheckResult
) -> Document | None:
    source = context.mod_root / relative
    if not source.is_file():
        result.add(
            "route_parity.file_missing",
            f"required route-parity file is missing: {relative.as_posix()}",
            relative.as_posix(),
        )
        return None
    document = context.document(source)
    if document is None:
        result.add(
            "route_parity.parse",
            context.parse_errors.get(source.resolve(), "could not parse file"),
            relative.as_posix(),
        )
    return document


def _named_object(obj: Object | None, key: str) -> Object | None:
    matches = entries_named(obj, key)
    if len(matches) != 1 or not isinstance(matches[0].value, Object):
        return None
    return matches[0].value


def _direct_scalar(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any(
        entry.key == key
        and isinstance(entry.value, Scalar)
        and entry.value.text == value
        for entry in obj.entries
    )


def _event_bodies(document: Document | None) -> dict[str, Object]:
    found: dict[str, Object] = {}
    if document is None:
        return found
    for entry in entries_named(document.root, "country_event"):
        if isinstance(entry.value, Object):
            event_id = first_scalar(entry.value, "id")
            if event_id is not None:
                found[event_id] = entry.value
    return found


def _modifier_writes(option: Object) -> dict[str, str | None]:
    found: dict[str, str | None] = {}
    for entry in entries_named(option, "add_country_modifier"):
        if not isinstance(entry.value, Object):
            continue
        name = first_scalar(entry.value, "name")
        if name is not None:
            found[name] = first_scalar(entry.value, "duration")
    return found


def _decision_bodies(document: Document | None) -> dict[str, Object]:
    wrapper = first_object(document.root, "country_decisions") if document else None
    if wrapper is None:
        return {}
    return {
        entry.key: entry.value
        for entry in wrapper.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }


def _event_call_id(effect: Object | None) -> str | None:
    if effect is None:
        return None
    calls = entries_named(effect, "country_event")
    if len(calls) != 1 or not isinstance(calls[0].value, Object):
        return None
    return first_scalar(calls[0].value, "id")


def _check_triggers(
    document: Document | None, result: CheckResult
) -> int:
    if document is None:
        return 0
    matched = 0
    actual_keys = {
        entry.key
        for entry in document.root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }
    if actual_keys != set(EXPECTED_TRIGGER_BODIES):
        result.add(
            "route_parity.trigger_inventory",
            "route-parity trigger inventory differs from the fixed six-trigger contract",
            TRIGGER_FILE.as_posix(),
        )
    for key, expected in EXPECTED_TRIGGER_BODIES.items():
        actual = _named_object(document.root, key)
        if actual is None or _canonical_object(actual) != _canonical_object(expected):
            result.add(
                "route_parity.trigger_contract",
                f"{key} no longer matches its mutually exclusive route/reform contract",
                TRIGGER_FILE.as_posix(),
            )
        else:
            matched += 1
    return matched


def _check_events(document: Document | None, result: CheckResult) -> tuple[int, int]:
    events = _event_bodies(document)
    expected_ids = {route.event_id for route in ROUTES}
    if set(events) != expected_ids:
        result.add(
            "route_parity.event_inventory",
            f"event file defines {sorted(events)}; expected {sorted(expected_ids)}",
            EVENT_FILE.as_posix(),
        )
    namespace_count = 0
    if document is not None:
        namespace_count = sum(
            1
            for entry in entries_named(document.root, "namespace")
            if isinstance(entry.value, Scalar)
            and entry.value.text == "jxp_route_parity"
        )
    if namespace_count != 1:
        result.add(
            "route_parity.namespace",
            f"jxp_route_parity namespace appears {namespace_count} times; expected once",
            EVENT_FILE.as_posix(),
        )

    matched_events = 0
    matched_options = 0
    for route in ROUTES:
        event = events.get(route.event_id)
        if event is None:
            continue
        trigger = first_object(event, "trigger")
        mtth = first_object(event, "mean_time_to_happen")
        if not (
            _direct_scalar(trigger, route.route_trigger, "yes")
            and _direct_scalar(trigger, route.reform_trigger, "yes")
            and first_scalar(mtth, "months") == "96"
        ):
            result.add(
                "route_parity.event_reachability",
                f"{route.event_id} must use its positive route/reform gates and 96-month MTTH",
                EVENT_FILE.as_posix(),
            )
        cooldown_reads = find_assignments(trigger, "has_country_modifier", COOLDOWN_MODIFIER) if trigger else ()
        if len(cooldown_reads) != 1 or "NOT" not in cooldown_reads[0][0]:
            result.add(
                "route_parity.event_cooldown",
                f"{route.event_id} must positively exclude the shared recent-council modifier",
                EVENT_FILE.as_posix(),
            )

        options = tuple(
            entry.value
            for entry in entries_named(event, "option")
            if isinstance(entry.value, Object)
        )
        if len(options) != len(route.options):
            result.add(
                "route_parity.option_count",
                f"{route.event_id} has {len(options)} options; expected {len(route.options)}",
                EVENT_FILE.as_posix(),
            )
            continue

        options_by_reform: dict[str, Object] = {}
        for option in options:
            option_trigger = first_object(option, "trigger")
            reform_values = tuple(
                entry.value.text
                for entry in entries_named(option_trigger, "has_reform")
                if isinstance(entry.value, Scalar)
            )
            if len(reform_values) == 1:
                options_by_reform[reform_values[0]] = option

        route_ok = True
        for contract in route.options:
            option = options_by_reform.get(contract.reform)
            if option is None or first_scalar(option, "name") != contract.option_key:
                result.add(
                    "route_parity.option_reform_contract",
                    f"{route.event_id} is missing the exact option for {contract.reform}",
                    EVENT_FILE.as_posix(),
                )
                route_ok = False
                continue
            writes = _modifier_writes(option)
            expected_writes = {
                COOLDOWN_MODIFIER: COOLDOWN_DAYS,
                contract.outcome_modifier: COOLDOWN_DAYS,
            }
            if writes != expected_writes:
                result.add(
                    "route_parity.option_modifier_contract",
                    f"{contract.option_key} writes {writes}; expected two finite 3650-day modifiers",
                    EVENT_FILE.as_posix(),
                )
                route_ok = False
            actual_effects = tuple(
                entry.key
                for entry in option.entries
                if entry.key is not None
                and isinstance(entry.value, Scalar)
                and entry.value.text == "yes"
                and ERA_EFFECT_PATTERN.fullmatch(entry.key)
            )
            if set(actual_effects) != set(contract.era_effects) or len(actual_effects) != len(
                contract.era_effects
            ):
                result.add(
                    "route_parity.option_attribute_contract",
                    f"{contract.option_key} era effects are {actual_effects}; expected {contract.era_effects}",
                    EVENT_FILE.as_posix(),
                )
                route_ok = False
            if first_object(option, "ai_chance") is None:
                result.add(
                    "route_parity.option_ai",
                    f"{contract.option_key} lacks explicit AI weighting",
                    EVENT_FILE.as_posix(),
                )
                route_ok = False
            if route_ok:
                matched_options += 1
        if route_ok:
            matched_events += 1
    return matched_events, matched_options


def _check_decisions(
    document: Document | None,
    debug_document: Document | None,
    result: CheckResult,
) -> tuple[int, int]:
    decisions = _decision_bodies(document)
    debug_decisions = _decision_bodies(debug_document)
    expected = {route.decision_id for route in ROUTES}
    expected_debug = {route.debug_decision_id for route in ROUTES}
    if set(decisions) != expected:
        result.add(
            "route_parity.decision_inventory",
            f"native decision inventory is {sorted(decisions)}; expected {sorted(expected)}",
            DECISION_FILE.as_posix(),
        )
    if set(debug_decisions) != expected_debug:
        result.add(
            "route_parity.debug_inventory",
            f"debug decision inventory is {sorted(debug_decisions)}; expected {sorted(expected_debug)}",
            DEBUG_DECISION_FILE.as_posix(),
        )

    matched = 0
    debug_matched = 0
    for route in ROUTES:
        decision = decisions.get(route.decision_id)
        if decision is not None:
            potential = first_object(decision, "potential")
            allow = first_object(decision, "allow")
            effect = first_object(decision, "effect")
            ai = first_object(decision, "ai_will_do")
            cooldown_reads = find_assignments(allow, "has_country_modifier", COOLDOWN_MODIFIER) if allow else ()
            valid = (
                _direct_scalar(potential, route.route_trigger, "yes")
                and _direct_scalar(allow, route.reform_trigger, "yes")
                and _direct_scalar(allow, "is_at_war", "no")
                and _direct_scalar(allow, route.power_trigger, "25")
                and len(cooldown_reads) == 1
                and "NOT" in cooldown_reads[0][0]
                and _direct_scalar(effect, route.power_effect, "-25")
                and _event_call_id(effect) == route.event_id
                and first_scalar(ai, "factor") == "1"
                and len(entries_named(ai, "modifier")) >= 2
            )
            if not valid:
                result.add(
                    "route_parity.decision_contract",
                    f"{route.decision_id} no longer has its route/reform/cost/cooldown/event/AI contract",
                    DECISION_FILE.as_posix(),
                )
            else:
                matched += 1

        debug = debug_decisions.get(route.debug_decision_id)
        if debug is not None:
            potential = first_object(debug, "potential")
            effect = first_object(debug, "effect")
            ai = first_object(debug, "ai_will_do")
            expected_removals = {COOLDOWN_MODIFIER} | {
                option.outcome_modifier for option in route.options
            }
            removals = {
                entry.value.text
                for entry in entries_named(effect, "remove_country_modifier")
                if isinstance(entry.value, Scalar)
            }
            valid = (
                _direct_scalar(potential, "ai", "no")
                and _direct_scalar(potential, "has_country_flag", "jxp_debug_enabled")
                and _direct_scalar(potential, "has_country_flag", "jxp_debug_events_enabled")
                and _direct_scalar(
                    potential, "has_country_flag", "jxp_debug_event_category_early"
                )
                and _direct_scalar(potential, route.route_trigger, "yes")
                and _direct_scalar(potential, route.reform_trigger, "yes")
                and removals == expected_removals
                and _event_call_id(effect) == route.event_id
                and first_scalar(ai, "factor") == "0"
            )
            if not valid:
                result.add(
                    "route_parity.debug_contract",
                    f"{route.debug_decision_id} no longer seeds the exact ready route event safely",
                    DEBUG_DECISION_FILE.as_posix(),
                )
            else:
                debug_matched += 1
    return matched, debug_matched


def _check_modifiers_and_cleanup(
    context: ValidationContext,
    modifier_document: Document | None,
    debug_document: Document | None,
    route_effect_document: Document | None,
    result: CheckResult,
) -> tuple[int, int, int]:
    definitions = (
        {
            entry.key
            for entry in modifier_document.root.entries
            if entry.key is not None and isinstance(entry.value, Object)
        }
        if modifier_document is not None
        else set()
    )
    if definitions != set(EXPECTED_MODIFIERS):
        result.add(
            "route_parity.modifier_inventory",
            f"modifier inventory is {sorted(definitions)}; expected {sorted(EXPECTED_MODIFIERS)}",
            MODIFIER_FILE.as_posix(),
        )

    cleanup_matched = 0
    if debug_document is not None:
        for modifier in EXPECTED_MODIFIERS:
            occurrences = find_assignments(
                debug_document.root, "remove_country_modifier", modifier
            )
            expected_root = (
                "jxp_debug_clear_cooldowns_effect"
                if modifier == COOLDOWN_MODIFIER
                else "jxp_debug_clear_event_state_effect"
            )
            if len(occurrences) != 1 or expected_root not in occurrences[0][0]:
                result.add(
                    "route_parity.debug_cleanup",
                    f"{modifier} must be removed exactly once through {expected_root}",
                    DEBUG_EFFECT_FILE.as_posix(),
                )
            else:
                cleanup_matched += 1

    route_cleanup_matched = 0
    if route_effect_document is not None:
        for modifier in EXPECTED_MODIFIERS:
            occurrences = find_assignments(
                route_effect_document.root, "remove_country_modifier", modifier
            )
            if (
                len(occurrences) != 1
                or "jxp_clear_route_modifiers_effect" not in occurrences[0][0]
            ):
                result.add(
                    "route_parity.route_cleanup",
                    f"{modifier} must be removed exactly once by jxp_clear_route_modifiers_effect",
                    ROUTE_EFFECT_FILE.as_posix(),
                )
            else:
                route_cleanup_matched += 1
    return (
        len(definitions & set(EXPECTED_MODIFIERS)),
        cleanup_matched,
        route_cleanup_matched,
    )


def _localisation_keys() -> set[str]:
    keys: set[str] = set()
    for route in ROUTES:
        keys.update(
            {
                f"{route.decision_id}_title",
                f"{route.decision_id}_desc",
                route.reform_trigger,
                f"{route.event_id}.t",
                f"{route.event_id}.d",
                f"{route.debug_decision_id}_title",
                f"{route.debug_decision_id}_desc",
            }
        )
        keys.update(option.option_key for option in route.options)
    for modifier in EXPECTED_MODIFIERS:
        keys.add(modifier)
        keys.add(f"{modifier}_desc")
    return keys


def _read_loc_keys(path: Path, encoding: str) -> set[str]:
    text = path.read_text(encoding=encoding)
    return {
        match.group(1)
        for match in re.finditer(r"^\s+([A-Za-z0-9_.-]+):\d+\s+", text, re.MULTILINE)
    }


def _check_localisation(context: ValidationContext, result: CheckResult) -> int:
    required = _localisation_keys()
    source = context.mod_root / SOURCE_LOC_FILE
    active = context.mod_root / ACTIVE_LOC_FILE
    matched = 0
    if not source.is_file() or not active.is_file():
        result.add(
            "route_parity.localisation_file",
            "route-parity source and active localisation files are both required",
        )
        return 0
    source_text = source.read_text(encoding="utf-8-sig")
    source_keys = _read_loc_keys(source, "utf-8-sig")
    active_keys = _read_loc_keys(active, "utf-8-sig")
    if not RAW_CJK.search(source_text):
        result.add(
            "route_parity.localisation_source",
            "UTF-8 source localisation must retain readable Chinese prose",
            SOURCE_LOC_FILE.as_posix(),
        )
    active_bytes = active.read_bytes()
    active_text = active_bytes.decode("utf-8-sig")
    if not active_bytes.startswith(b"\xef\xbb\xbf") or RAW_CJK.search(active_text):
        result.add(
            "route_parity.localisation_active",
            "active localisation must be UTF-8 BOM and EU4SpecialEscape encoded",
            ACTIVE_LOC_FILE.as_posix(),
        )
    missing_source = required - source_keys
    missing_active = required - active_keys
    if missing_source or missing_active:
        result.add(
            "route_parity.localisation_keys",
            f"missing source={sorted(missing_source)} active={sorted(missing_active)}",
        )
    else:
        matched = len(required)
    return matched


def _check_surface_safety(context: ValidationContext, result: CheckResult) -> None:
    gameplay = (TRIGGER_FILE, EVENT_FILE, DECISION_FILE)
    for relative in gameplay:
        source = context.mod_root / relative
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8-sig")
        if re.search(r"\bset_country_flag\s*=\s*jxp_path_", text):
            result.add(
                "route_parity.route_mutation",
                "route-parity content must consume canonical route state, never write it",
                relative.as_posix(),
            )
        if re.search(r"\bchange_tag\s*=", text):
            result.add(
                "route_parity.tag_mutation",
                "route-parity content must not change country tags",
                relative.as_posix(),
            )
        match = COMPANION_ONLY_REFERENCE.search(text)
        if match is not None:
            result.add(
                "route_parity.companion_reference",
                f"main route-parity file references companion-only object {match.group(0)}",
                relative.as_posix(),
                text.count("\n", 0, match.start()) + 1,
            )


def check_route_parity_content(context: ValidationContext) -> CheckResult:
    """Return the fixed route-parity interaction contract result."""

    result = CheckResult("Sakoku, Open Trade, and Imperial route parity")
    trigger_document = _document(context, TRIGGER_FILE, result)
    event_document = _document(context, EVENT_FILE, result)
    decision_document = _document(context, DECISION_FILE, result)
    debug_decision_document = _document(context, DEBUG_DECISION_FILE, result)
    modifier_document = _document(context, MODIFIER_FILE, result)
    debug_document = _document(context, DEBUG_EFFECT_FILE, result)
    route_effect_document = _document(context, ROUTE_EFFECT_FILE, result)

    triggers = _check_triggers(trigger_document, result)
    events, options = _check_events(event_document, result)
    decisions, debug_decisions = _check_decisions(
        decision_document, debug_decision_document, result
    )
    modifiers, cleanup, route_cleanup = _check_modifiers_and_cleanup(
        context,
        modifier_document,
        debug_document,
        route_effect_document,
        result,
    )
    localisation = _check_localisation(context, result)
    _check_surface_safety(context, result)

    result.metrics.update(
        {
            "route_gates": triggers,
            "native_events": events,
            "reform_options": options,
            "native_decisions": decisions,
            "debug_entries": debug_decisions,
            "modifiers": modifiers,
            "debug_cleanup": cleanup,
            "route_cleanup": route_cleanup,
            "localisation_keys": localisation,
        }
    )
    result.summary = (
        f"{events}/{len(ROUTES)} native events; "
        f"{options}/{sum(len(route.options) for route in ROUTES)} reform options; "
        f"{decisions}/{len(ROUTES)} native decisions; "
        f"{cleanup}/{len(EXPECTED_MODIFIERS)} debug-cleaned and "
        f"{route_cleanup}/{len(EXPECTED_MODIFIERS)} route-cleared modifiers"
    )
    return result
