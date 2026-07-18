"""Validate the IJP congregation-pressure and temple-town state loop.

The contract fixes a complete, auditable state machine: defensive exclusive
route entry, next-day reconciliation, disaster isolation, bounded pressure,
three repeatable governance choices, recurring AI choices, two player exits,
route-loss cleanup, finite modifiers, and additive companion-map geography.
"""

from __future__ import annotations

from pathlib import Path
import re

from .clausewitz import (
    Document,
    Object,
    Scalar,
    entries_named,
    find_assignments,
    find_objects,
    first_object,
    first_scalar,
    parse_text,
)
from .core import CheckResult, ValidationContext


TRIGGER_FILE = Path("common/scripted_triggers/jxp_74_ijp_triggers.txt")
EFFECT_FILE = Path("common/scripted_effects/jxp_74_ijp_effects.txt")
MODIFIER_FILE = Path("common/event_modifiers/jxp_74_ijp_modifiers.txt")
DECISION_FILE = Path("decisions/jxp_74_ijp_decisions.txt")
DEBUG_DECISION_FILE = Path("decisions/jxp_74_ijp_debug_decisions.txt")
EVENT_FILE = Path("events/jxp_74_ijp_events.txt")
LEGACY_EVENT_FILE = Path("events/jxp_ikko_events.txt")
DISASTER_FILE = Path("common/disasters/jxp_japanese_disasters.txt")
SOURCE_LOC_FILE = Path("localisation_source/jxp_74_ijp_l_english_utf8_source.yml")
ACTIVE_LOC_FILE = Path("localisation/jxp_74_ijp_l_english.yml")

ACTIVE_FLAG = "jxp_74_ijp_cycle_active"
GUARD_FLAG = "jxp_74_ijp_route_guard_pending"
PRESSURE_VARIABLE = "jxp_a_shinshu_militancy"
ALLOWED_MAP_FLAG = "jxp_map_compat_ikko_heartland"

FOREIGN_ROUTE_FLAGS = (
    "jxp_path_sakoku",
    "jxp_path_open_trade",
    "jxp_path_kirishitan",
    "jxp_path_confucian",
    "jxp_path_imperial",
    "jxp_path_reformed",
    "jxp_path_kaikyo",
    "jxp_path_wokou",
)

EXPECTED_MODIFIERS = (
    "jxp_74_ijp_temple_market_charter",
    "jxp_74_ijp_machishu_investment",
    "jxp_74_ijp_somon_mediation",
    "jxp_74_ijp_war_bell_enforcement",
    "jxp_74_ijp_market_dividend",
    "jxp_74_ijp_assembly_hearing",
    "jxp_74_ijp_hardline_aftershock",
    "jxp_74_ijp_covenant_overreach",
    "jxp_74_ijp_crisis_recess",
    "jxp_74_ijp_chartered_commonwealth",
    "jxp_74_ijp_secular_settlement",
)

EXPECTED_DECISIONS = (
    "jxp_74_decision_convene_somon_commonwealth",
    "jxp_74_decision_invest_temple_markets",
    "jxp_74_decision_fund_mediation_circuits",
    "jxp_74_decision_enforce_war_bell_register",
    "jxp_74_decision_charter_temple_town_state",
    "jxp_74_decision_stand_down_armed_leagues",
)

EXPECTED_DEBUG_DECISIONS = (
    "jxp_debug_74_ijp_start_cycle",
    "jxp_debug_74_ijp_add_pressure",
    "jxp_debug_74_ijp_fire_petition",
    "jxp_debug_74_ijp_fire_crisis",
    "jxp_debug_74_ijp_reset_cycle",
)

EXPECTED_EFFECTS = (
    "jxp_74_ijp_clamp_pressure_effect",
    "jxp_74_ijp_add_pressure_10_effect",
    "jxp_74_ijp_add_pressure_15_effect",
    "jxp_74_ijp_add_pressure_20_effect",
    "jxp_74_ijp_subtract_pressure_10_effect",
    "jxp_74_ijp_subtract_pressure_15_effect",
    "jxp_74_ijp_subtract_pressure_20_effect",
    "jxp_74_ijp_subtract_pressure_40_effect",
    "jxp_74_ijp_cleanup_effect",
    "jxp_74_ijp_route_exit_effect",
    "jxp_74_ijp_enforce_route_exclusivity_effect",
    "jxp_74_ijp_route_entry_effect",
    "jxp_74_ijp_start_cycle_effect",
    "jxp_74_ijp_transform_commonwealth_effect",
    "jxp_74_ijp_stand_down_leagues_effect",
    "jxp_74_ijp_debug_reset_effect",
)

PRESSURE_EFFECT_VALUES = {
    "jxp_74_ijp_add_pressure_10_effect": "10",
    "jxp_74_ijp_add_pressure_15_effect": "15",
    "jxp_74_ijp_add_pressure_20_effect": "20",
    "jxp_74_ijp_subtract_pressure_10_effect": "-10",
    "jxp_74_ijp_subtract_pressure_15_effect": "-15",
    "jxp_74_ijp_subtract_pressure_20_effect": "-20",
    "jxp_74_ijp_subtract_pressure_40_effect": "-40",
}

REPEATABLE_DECISIONS = {
    "jxp_74_decision_invest_temple_markets": (
        "jxp_74_ijp_machishu_investment",
        "jxp_74_ijp_add_pressure_10_effect",
    ),
    "jxp_74_decision_fund_mediation_circuits": (
        "jxp_74_ijp_somon_mediation",
        "jxp_74_ijp_subtract_pressure_15_effect",
    ),
    "jxp_74_decision_enforce_war_bell_register": (
        "jxp_74_ijp_war_bell_enforcement",
        "jxp_74_ijp_subtract_pressure_10_effect",
    ),
}

EXPECTED_EVENTS = tuple(f"jxp_ijp_loop.{number}" for number in range(1, 7))

_EXPECTED_TRIGGER_DOCUMENT = parse_text(
    r"""
jxp_74_ijp_route_trigger = {
    jxp_is_japanese_polity_trigger = yes
    religion = jodo_shinshu
    OR = { tag = IJP has_country_flag = jxp_path_ikko }
    NOT = { OR = {
        has_country_flag = jxp_path_sakoku
        has_country_flag = jxp_path_open_trade
        has_country_flag = jxp_path_kirishitan
        has_country_flag = jxp_path_confucian
        has_country_flag = jxp_path_imperial
        has_country_flag = jxp_path_reformed
        has_country_flag = jxp_path_kaikyo
        has_country_flag = jxp_path_wokou
    } }
}
jxp_74_ijp_cycle_active_trigger = {
    jxp_74_ijp_route_trigger = yes
    has_country_flag = jxp_74_ijp_cycle_active
    has_country_modifier = jxp_74_ijp_temple_market_charter
    has_any_disaster = no
    NOT = { has_country_flag = jxp_ikko_rising_active }
    NOT = { has_country_flag = jxp_shimabara_crisis_active }
}
jxp_74_ijp_commons_ready_trigger = {
    religious_unity = 0.75
    has_estate = estate_church
    estate_loyalty = { estate = estate_church loyalty = 40 }
    has_estate = estate_burghers
    estate_loyalty = { estate = estate_burghers loyalty = 35 }
}
jxp_74_ijp_heartland_trigger = {
    OR = {
        any_owned_province = { OR = {
            area = kinai_area
            area = saigoku_area
            has_province_flag = jxp_map_compat_ikko_heartland
        } }
        any_owned_province = { has_province_modifier = jxp_ikko_terauchi_town }
    }
}
jxp_74_ijp_pressure_at_least_10_trigger = {
    jxp_a_shinshu_militancy_at_least_10_trigger = yes
}
jxp_74_ijp_pressure_at_least_50_trigger = {
    jxp_a_shinshu_militancy_at_least_50_trigger = yes
}
jxp_74_ijp_pressure_at_least_70_trigger = {
    jxp_a_shinshu_militancy_at_least_70_trigger = yes
}
jxp_74_ijp_pressure_at_least_85_trigger = {
    jxp_a_shinshu_militancy_at_least_85_trigger = yes
}
"""
)

EXPECTED_TRIGGER_BODIES = {
    entry.key: entry.value
    for entry in _EXPECTED_TRIGGER_DOCUMENT.root.entries
    if entry.key is not None and isinstance(entry.value, Object)
}

RAW_CJK = re.compile(r"[\u3400-\u9fff]")
MAP_TOKEN = re.compile(r"\bjxp_map_[A-Za-z0-9_]+\b")
COMPANION_PROVINCE = re.compile(r"\b(?:494[2-9]|49[5-7][0-9]|498[01])\b")
LOCALISATION_KEY = re.compile(r"^\s*([A-Za-z0-9_.-]+):\d+\s", re.MULTILINE)


def _canonical(obj: Object) -> tuple[object, ...]:
    members: list[tuple[object, ...]] = []
    for entry in obj.entries:
        if isinstance(entry.value, Object):
            value: tuple[object, ...] = ("object", _canonical(entry.value))
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
            "ijp_loop.file_missing",
            f"required IJP-loop file is missing: {relative.as_posix()}",
            relative.as_posix(),
        )
        return None
    document = context.document(source)
    if document is None:
        result.add(
            "ijp_loop.parse",
            context.parse_errors.get(source.resolve(), "could not parse file"),
            relative.as_posix(),
        )
    return document


def _named_object(obj: Object | None, key: str) -> Object | None:
    if obj is None:
        return None
    matches = entries_named(obj, key)
    if len(matches) != 1 or not isinstance(matches[0].value, Object):
        return None
    return matches[0].value


def _top_objects(document: Document | None) -> dict[str, Object]:
    if document is None:
        return {}
    return {
        entry.key: entry.value
        for entry in document.root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }


def _decision_bodies(document: Document | None) -> dict[str, Object]:
    wrapper = first_object(document.root, "country_decisions") if document else None
    if wrapper is None:
        return {}
    return {
        entry.key: entry.value
        for entry in wrapper.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }


def _event_bodies(document: Document | None) -> dict[str, Object]:
    found: dict[str, Object] = {}
    if document is None:
        return found
    for entry in entries_named(document.root, "country_event"):
        if not isinstance(entry.value, Object):
            continue
        event_id = first_scalar(entry.value, "id")
        if event_id is not None:
            found[event_id] = entry.value
    return found


def _options(obj: Object | None) -> list[Object]:
    if obj is None:
        return []
    return [
        entry.value
        for entry in entries_named(obj, "option")
        if isinstance(entry.value, Object)
    ]


def _positive(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any("NOT" not in path for path, _entry in find_assignments(obj, key, value))


def _negative(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any("NOT" in path for path, _entry in find_assignments(obj, key, value))


def _direct_index(obj: Object | None, key: str, value: str) -> int | None:
    if obj is None:
        return None
    for index, entry in enumerate(obj.entries):
        if (
            entry.key == key
            and isinstance(entry.value, Scalar)
            and entry.value.text == value
        ):
            return index
    return None


def _factor(obj: Object | None) -> float | None:
    if obj is None:
        return None
    value = first_scalar(obj, "factor")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _modifier_writes(obj: Object | None) -> list[tuple[str, str | None]]:
    found: list[tuple[str, str | None]] = []
    if obj is None:
        return found
    for _path, entry in find_objects(obj, "add_country_modifier"):
        name = first_scalar(entry.value, "name")
        if name is not None:
            found.append((name, first_scalar(entry.value, "duration")))
    return found


def _variable_operation(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    for _path, entry in find_objects(obj, key):
        if (
            first_scalar(entry.value, "which") == PRESSURE_VARIABLE
            and first_scalar(entry.value, "value") == value
        ):
            return True
    return False


def _scheduled_event(obj: Object | None, event_id: str, days: str) -> bool:
    if obj is None:
        return False
    for _path, entry in find_objects(obj, "country_event"):
        if (
            first_scalar(entry.value, "id") == event_id
            and first_scalar(entry.value, "days") == days
        ):
            return True
    return False


def _estate_loyalty(obj: Object | None, estate: str, loyalty: str) -> bool:
    if obj is None:
        return False
    for path, entry in find_objects(obj, "estate_loyalty"):
        if (
            "NOT" not in path
            and first_scalar(entry.value, "estate") == estate
            and first_scalar(entry.value, "loyalty") == loyalty
        ):
            return True
    return False


def _check_trigger_contract(document: Document | None, result: CheckResult) -> int:
    actual = _top_objects(document)
    if set(actual) != set(EXPECTED_TRIGGER_BODIES):
        result.add(
            "ijp_loop.trigger_inventory",
            "IJP trigger inventory differs from the eight-trigger contract",
            TRIGGER_FILE.as_posix(),
        )
    matched = 0
    for key, expected in EXPECTED_TRIGGER_BODIES.items():
        body = actual.get(key)
        if body is None or _canonical(body) != _canonical(expected):
            result.add(
                "ijp_loop.trigger_contract",
                f"{key} no longer matches its exact route/disaster/estate/geography contract",
                TRIGGER_FILE.as_posix(),
            )
        else:
            matched += 1

    route = actual.get("jxp_74_ijp_route_trigger")
    if not all(_negative(route, "has_country_flag", flag) for flag in FOREIGN_ROUTE_FLAGS):
        result.add(
            "ijp_loop.route_exclusivity",
            "IJP route trigger no longer excludes all eight foreign route flags",
            TRIGGER_FILE.as_posix(),
        )
    if not _positive(route, "religion", "jodo_shinshu"):
        result.add(
            "ijp_loop.religion_gate",
            "IJP production route entry must require its Jodo Shinshu religion",
            TRIGGER_FILE.as_posix(),
        )
    active = actual.get("jxp_74_ijp_cycle_active_trigger")
    if not all(
        (
            _positive(active, "has_any_disaster", "no"),
            _negative(active, "has_country_flag", "jxp_ikko_rising_active"),
            _negative(active, "has_country_flag", "jxp_shimabara_crisis_active"),
        )
    ):
        result.add(
            "ijp_loop.disaster_isolation",
            "active IJP cycle no longer excludes all disasters, Ikko rising, and Shimabara",
            TRIGGER_FILE.as_posix(),
        )
    if not _positive(
        active, "has_country_modifier", "jxp_74_ijp_temple_market_charter"
    ):
        result.add(
            "ijp_loop.charter_lifecycle",
            "IJP active-cycle state must expire with its 3650-day temple-market charter",
            TRIGGER_FILE.as_posix(),
        )
    commons = actual.get("jxp_74_ijp_commons_ready_trigger")
    if not all(
        (
            _positive(commons, "has_estate", "estate_church"),
            _estate_loyalty(commons, "estate_church", "40"),
            _positive(commons, "has_estate", "estate_burghers"),
            _estate_loyalty(commons, "estate_burghers", "35"),
        )
    ):
        result.add(
            "ijp_loop.estate_gate",
            "IJP production entry must require both church and burgher estates at their loyalty floors",
            TRIGGER_FILE.as_posix(),
        )
    return matched


def _check_decisions(document: Document | None, result: CheckResult) -> int:
    decisions = _decision_bodies(document)
    if set(decisions) != set(EXPECTED_DECISIONS):
        result.add(
            "ijp_loop.decision_inventory",
            "player decision inventory differs from the six-decision contract",
            DECISION_FILE.as_posix(),
        )

    entry = decisions.get("jxp_74_decision_convene_somon_commonwealth")
    potential = _named_object(entry, "potential")
    allow = _named_object(entry, "allow")
    effect = _named_object(entry, "effect")
    entry_ok = all(
        (
            _positive(potential, "jxp_74_ijp_route_trigger", "yes"),
            _positive(potential, "has_any_disaster", "no"),
            _negative(potential, "has_country_flag", "jxp_ikko_rising_active"),
            _negative(potential, "has_country_flag", "jxp_shimabara_crisis_active"),
            _negative(potential, "has_country_flag", GUARD_FLAG),
            _positive(allow, "jxp_74_ijp_commons_ready_trigger", "yes"),
            _positive(allow, "jxp_74_ijp_heartland_trigger", "yes"),
            _positive(allow, "mission_completed", "jxp_mission_terauchi_league"),
            _positive(effect, "jxp_74_ijp_start_cycle_effect", "yes"),
        )
    )
    if not entry_ok:
        result.add(
            "ijp_loop.entry_contract",
            "IJP entry lost route, disaster, pending-reconcile, commons, geography, mission, or canonical-start gating",
            DECISION_FILE.as_posix(),
        )

    repeatable = 0
    for decision_id, (cooldown, pressure_effect) in REPEATABLE_DECISIONS.items():
        body = decisions.get(decision_id)
        decision_allow = _named_object(body, "allow")
        decision_effect = _named_object(body, "effect")
        writes = dict(_modifier_writes(decision_effect))
        valid = all(
            (
                _positive(
                    _named_object(body, "potential"),
                    "jxp_74_ijp_cycle_active_trigger",
                    "yes",
                ),
                _negative(decision_allow, "has_country_modifier", cooldown),
                writes.get(cooldown) == "1825",
                _positive(decision_effect, pressure_effect, "yes"),
            )
        )
        if not valid:
            result.add(
                "ijp_loop.investment_contract",
                f"{decision_id} lost its active gate, 1825-day cooldown, or pressure tradeoff",
                DECISION_FILE.as_posix(),
            )
        else:
            repeatable += 1

    exits = {
        "jxp_74_decision_charter_temple_town_state": (
            "jxp_74_ijp_transform_commonwealth_effect",
            "jxp_74_ijp_pressure_at_least_50_trigger",
        ),
        "jxp_74_decision_stand_down_armed_leagues": (
            "jxp_74_ijp_stand_down_leagues_effect",
            None,
        ),
    }
    for decision_id, (exit_effect, threshold) in exits.items():
        body = decisions.get(decision_id)
        decision_allow = _named_object(body, "allow")
        decision_effect = _named_object(body, "effect")
        valid = all(
            (
                _positive(
                    _named_object(body, "potential"),
                    "jxp_74_ijp_cycle_active_trigger",
                    "yes",
                ),
                _positive(decision_allow, "is_at_war", "no"),
                threshold is None or _positive(decision_allow, threshold, "yes"),
                _positive(decision_effect, exit_effect, "yes"),
            )
        )
        if not valid:
            result.add(
                "ijp_loop.exit_path",
                f"{decision_id} lost its peacetime active-cycle exit contract",
                DECISION_FILE.as_posix(),
            )

    transform_allow = _named_object(
        decisions.get("jxp_74_decision_charter_temple_town_state"), "allow"
    )
    if not _positive(
        transform_allow, "mission_completed", "jxp_mission_peasant_commonwealth"
    ):
        result.add(
            "ijp_loop.mission_hook",
            "temple-town transformation no longer consumes the IJP commonwealth mission spine",
            DECISION_FILE.as_posix(),
        )

    for decision_id in EXPECTED_DECISIONS:
        ai = _named_object(decisions.get(decision_id), "ai_will_do")
        if _factor(ai) is None or _factor(ai) <= 0:
            result.add(
                "ijp_loop.ai_decision",
                f"{decision_id} has no positive AI base weight",
                DECISION_FILE.as_posix(),
            )
    return repeatable


def _check_debug_decisions(document: Document | None, result: CheckResult) -> int:
    decisions = _decision_bodies(document)
    if set(decisions) != set(EXPECTED_DEBUG_DECISIONS):
        result.add(
            "ijp_loop.debug_inventory",
            "IJP debug inventory differs from the five-entry contract",
            DEBUG_DECISION_FILE.as_posix(),
        )
    matched = 0
    for decision_id in EXPECTED_DEBUG_DECISIONS:
        body = decisions.get(decision_id)
        potential = _named_object(body, "potential")
        ai = _named_object(body, "ai_will_do")
        if (
            _positive(potential, "ai", "no")
            and _positive(potential, "has_country_flag", "jxp_debug_enabled")
            and _factor(ai) == 0
        ):
            matched += 1
        else:
            result.add(
                "ijp_loop.debug_gate",
                f"{decision_id} is not player/debug-only with zero AI weight",
                DEBUG_DECISION_FILE.as_posix(),
            )
    reset = _named_object(decisions.get("jxp_debug_74_ijp_reset_cycle"), "effect")
    if not _positive(reset, "jxp_74_ijp_debug_reset_effect", "yes"):
        result.add(
            "ijp_loop.debug_cleanup",
            "dedicated IJP reset decision cannot reach its cleanup effect",
            DEBUG_DECISION_FILE.as_posix(),
        )
    return matched


def _check_events(document: Document | None, result: CheckResult) -> tuple[int, int]:
    events = _event_bodies(document)
    if set(events) != set(EXPECTED_EVENTS):
        result.add(
            "ijp_loop.event_inventory",
            "IJP loop event inventory differs from events 1-5",
            EVENT_FILE.as_posix(),
        )

    visible_options = 0
    ai_options = 0
    for event_id in EXPECTED_EVENTS[:3]:
        body = events.get(event_id)
        trigger = _named_object(body, "trigger")
        mtth = _named_object(body, "mean_time_to_happen")
        options = _options(body)
        if not _positive(trigger, "jxp_74_ijp_cycle_active_trigger", "yes"):
            result.add(
                "ijp_loop.event_gate",
                f"{event_id} is not gated by the disaster-safe active cycle",
                EVENT_FILE.as_posix(),
            )
        if mtth is None or first_scalar(mtth, "days") is None:
            result.add(
                "ijp_loop.event_cadence",
                f"{event_id} has no mean-time cadence",
                EVENT_FILE.as_posix(),
            )
        if len(options) != 3:
            result.add(
                "ijp_loop.event_options",
                f"{event_id} has {len(options)} choices; expected 3",
                EVENT_FILE.as_posix(),
            )
        visible_options += len(options)
        for option in options:
            ai = _named_object(option, "ai_chance")
            if _factor(ai) is None or _factor(ai) <= 0:
                result.add(
                    "ijp_loop.ai_event",
                    f"an option in {event_id} has no positive AI base weight",
                    EVENT_FILE.as_posix(),
                )
            else:
                ai_options += 1

    if not _positive(
        _named_object(events.get("jxp_ijp_loop.2"), "trigger"),
        "jxp_74_ijp_pressure_at_least_50_trigger",
        "yes",
    ):
        result.add(
            "ijp_loop.pressure_escalation",
            "Somon dispute no longer begins at pressure 50",
            EVENT_FILE.as_posix(),
        )
    crisis = events.get("jxp_ijp_loop.3")
    if not _positive(
        _named_object(crisis, "trigger"),
        "jxp_74_ijp_pressure_at_least_85_trigger",
        "yes",
    ) or not any(
        _positive(option, "jxp_74_ijp_transform_commonwealth_effect", "yes")
        for option in _options(crisis)
    ):
        result.add(
            "ijp_loop.pressure_crisis",
            "pressure-85 crisis lost its state-transformation option",
            EVENT_FILE.as_posix(),
        )

    cleanup = events.get("jxp_ijp_loop.4")
    cleanup_trigger = _named_object(cleanup, "trigger")
    cleanup_mtth = _named_object(cleanup, "mean_time_to_happen")
    cleanup_immediate = _named_object(cleanup, "immediate")
    if not all(
        (
            first_scalar(cleanup, "hidden") == "yes" if cleanup else False,
            _positive(cleanup_trigger, "has_country_flag", ACTIVE_FLAG),
            _negative(cleanup_trigger, "jxp_74_ijp_cycle_active_trigger", "yes"),
            first_scalar(cleanup_mtth, "days") == "1" if cleanup_mtth else False,
            _positive(cleanup_immediate, "jxp_74_ijp_route_exit_effect", "yes"),
            len(_options(cleanup)) == 1,
        )
    ):
        result.add(
            "ijp_loop.route_loss_cleanup",
            "hidden one-day route exit no longer closes route loss or disaster overlap",
            EVENT_FILE.as_posix(),
        )

    reconcile = events.get("jxp_ijp_loop.5")
    reconcile_trigger = _named_object(reconcile, "trigger")
    reconcile_immediate = _named_object(reconcile, "immediate")
    if not all(
        (
            first_scalar(reconcile, "hidden") == "yes" if reconcile else False,
            first_scalar(reconcile, "is_triggered_only") == "yes" if reconcile else False,
            _positive(reconcile_trigger, "has_country_flag", GUARD_FLAG),
            _positive(reconcile_immediate, "clr_country_flag", GUARD_FLAG),
            _positive(
                reconcile_immediate,
                "jxp_74_ijp_enforce_route_exclusivity_effect",
                "yes",
            ),
            len(_options(reconcile)) == 1,
        )
    ):
        result.add(
            "ijp_loop.route_reconcile",
            "next-day IJP route reconciliation is incomplete",
            EVENT_FILE.as_posix(),
        )

    expiry = events.get("jxp_ijp_loop.6")
    expiry_immediate = _named_object(expiry, "immediate")
    expiry_if = _named_object(expiry_immediate, "if")
    expiry_limit = _named_object(expiry_if, "limit")
    if not all(
        (
            first_scalar(expiry, "hidden") == "yes" if expiry else False,
            first_scalar(expiry, "is_triggered_only") == "yes" if expiry else False,
            _positive(expiry_limit, "has_country_flag", ACTIVE_FLAG),
            _negative(
                expiry_limit,
                "has_country_modifier",
                "jxp_74_ijp_temple_market_charter",
            ),
            _positive(expiry_if, "jxp_74_ijp_route_exit_effect", "yes"),
            len(_options(expiry)) == 1,
        )
    ):
        result.add(
            "ijp_loop.expiry_lifecycle",
            "hidden IJP expiry must clean only an active cycle whose charter is absent",
            EVENT_FILE.as_posix(),
        )
    return visible_options, ai_options


def _check_effects(document: Document | None, result: CheckResult) -> int:
    effects = _top_objects(document)
    if set(effects) != set(EXPECTED_EFFECTS):
        result.add(
            "ijp_loop.effect_inventory",
            "IJP effect inventory differs from the sixteen-effect contract",
            EFFECT_FILE.as_posix(),
        )

    for effect_id, value in PRESSURE_EFFECT_VALUES.items():
        body = effects.get(effect_id)
        if not _variable_operation(body, "change_variable", value) or not _positive(
            body, "jxp_74_ijp_clamp_pressure_effect", "yes"
        ):
            result.add(
                "ijp_loop.pressure_effect",
                f"{effect_id} must change pressure by {value} and clamp it",
                EFFECT_FILE.as_posix(),
            )

    clamp = effects.get("jxp_74_ijp_clamp_pressure_effect")
    if not _variable_operation(clamp, "set_variable", "0") or not _variable_operation(
        clamp, "set_variable", "100"
    ):
        result.add(
            "ijp_loop.pressure_bounds",
            "pressure clamp no longer fixes both 0 and 100 bounds",
            EFFECT_FILE.as_posix(),
        )

    cleanup = effects.get("jxp_74_ijp_cleanup_effect")
    if not _positive(cleanup, "clr_country_flag", ACTIVE_FLAG) or not _variable_operation(
        cleanup, "set_variable", "20"
    ):
        result.add(
            "ijp_loop.cleanup_state",
            "cycle cleanup must clear the active flag and return militancy to the peaceful baseline",
            EFFECT_FILE.as_posix(),
        )
    for modifier in EXPECTED_MODIFIERS:
        if not _positive(cleanup, "remove_country_modifier", modifier):
            result.add(
                "ijp_loop.cleanup_modifier",
                f"cycle cleanup cannot remove {modifier}",
                EFFECT_FILE.as_posix(),
            )

    route_exit = effects.get("jxp_74_ijp_route_exit_effect")
    if not _positive(route_exit, "jxp_74_ijp_cleanup_effect", "yes") or not _positive(
        route_exit, "clr_country_flag", GUARD_FLAG
    ):
        result.add(
            "ijp_loop.route_exit",
            "public IJP route exit must clean cycle state and pending reconciliation",
            EFFECT_FILE.as_posix(),
        )

    enforce = effects.get("jxp_74_ijp_enforce_route_exclusivity_effect")
    clear_index = _direct_index(enforce, "jxp_clear_all_route_flags_effect", "yes")
    set_index = _direct_index(enforce, "set_country_flag", "jxp_path_ikko")
    if not all(
        (
            clear_index is not None,
            set_index is not None,
            clear_index < set_index if clear_index is not None and set_index is not None else False,
            not _positive(enforce, "set_country_flag", "jxp_ikko_contact"),
            _positive(enforce, "jxp_grant_route_reforms_effect", "yes"),
            _positive(enforce, "jxp_refresh_route_missions_effect", "yes"),
            _positive(enforce, "jxp_ensure_polity_mechanic_effect", "yes"),
        )
    ):
        result.add(
            "ijp_loop.route_entry_clear",
            "canonical IJP entry must clear route state before rebuilding Ikko identity without reviving the obsolete contact sentinel",
            EFFECT_FILE.as_posix(),
        )

    entry = effects.get("jxp_74_ijp_route_entry_effect")
    if not all(
        (
            _positive(entry, "jxp_74_ijp_enforce_route_exclusivity_effect", "yes"),
            _negative(entry, "has_country_flag", GUARD_FLAG),
            _positive(entry, "set_country_flag", GUARD_FLAG),
            _scheduled_event(entry, "jxp_ijp_loop.5", "1"),
        )
    ):
        result.add(
            "ijp_loop.route_reconcile",
            "canonical IJP entry no longer schedules exactly one next-day route reconcile",
            EFFECT_FILE.as_posix(),
        )

    start = effects.get("jxp_74_ijp_start_cycle_effect")
    start_writes = dict(_modifier_writes(start))
    if not all(
        (
            _positive(start, "jxp_74_ijp_cleanup_effect", "yes"),
            _positive(start, "set_country_flag", ACTIVE_FLAG),
            _variable_operation(start, "set_variable", "15"),
            start_writes.get("jxp_74_ijp_temple_market_charter") == "3650",
            _scheduled_event(start, "jxp_ijp_loop.6", "3651"),
        )
    ):
        result.add(
            "ijp_loop.start_state",
            "cycle start must clean, activate, initialize pressure 15, add a finite charter, and schedule guarded expiry",
            EFFECT_FILE.as_posix(),
        )

    exits = {
        "jxp_74_ijp_transform_commonwealth_effect": (
            "jxp_74_ijp_chartered_commonwealth",
            "7300",
        ),
        "jxp_74_ijp_stand_down_leagues_effect": (
            "jxp_74_ijp_secular_settlement",
            "3650",
        ),
    }
    closed = 0
    for effect_id, (modifier, duration) in exits.items():
        body = effects.get(effect_id)
        writes = dict(_modifier_writes(body))
        if _positive(body, "jxp_74_ijp_cleanup_effect", "yes") and writes.get(
            modifier
        ) == duration:
            closed += 1
        else:
            result.add(
                "ijp_loop.exit_effect",
                f"{effect_id} must clean active state then add finite {modifier}",
                EFFECT_FILE.as_posix(),
            )

    debug = effects.get("jxp_74_ijp_debug_reset_effect")
    if not _positive(debug, "jxp_74_ijp_route_exit_effect", "yes"):
        result.add(
            "ijp_loop.debug_cleanup",
            "dedicated IJP debug reset must delegate to the public route-exit lifecycle",
            EFFECT_FILE.as_posix(),
        )
    return closed


def _check_modifiers_and_durations(
    modifier_document: Document | None,
    documents: tuple[Document | None, ...],
    result: CheckResult,
) -> int:
    definitions = _top_objects(modifier_document)
    if set(definitions) != set(EXPECTED_MODIFIERS):
        result.add(
            "ijp_loop.modifier_inventory",
            "IJP modifier inventory differs from the eleven-modifier contract",
            MODIFIER_FILE.as_posix(),
        )
    writes = [
        write
        for document in documents
        if document is not None
        for write in _modifier_writes(document.root)
        if write[0].startswith("jxp_74_ijp_")
    ]
    used: set[str] = set()
    for name, duration in writes:
        used.add(name)
        if name not in EXPECTED_MODIFIERS:
            result.add(
                "ijp_loop.modifier_undefined",
                f"IJP loop writes unexpected modifier {name}",
                MODIFIER_FILE.as_posix(),
            )
            continue
        try:
            finite = duration is not None and int(duration) > 0
        except ValueError:
            finite = False
        if not finite:
            result.add(
                "ijp_loop.modifier_duration",
                f"{name} is written with non-finite duration {duration!r}",
                MODIFIER_FILE.as_posix(),
            )
    missing = sorted(set(EXPECTED_MODIFIERS) - used)
    if missing:
        result.add(
            "ijp_loop.modifier_unused",
            f"IJP modifier definitions are never added: {missing}",
            MODIFIER_FILE.as_posix(),
        )
    return len(definitions)


def _check_legacy_entry(document: Document | None, result: CheckResult) -> int:
    event = _event_bodies(document).get("jxp_ikko.1")
    trigger = _named_object(event, "trigger")
    options = _options(event)
    valid_trigger = all(
        (
            _positive(trigger, "jxp_is_japanese_polity_trigger", "yes"),
            _positive(trigger, "tag", "IJP"),
            _positive(trigger, "has_country_flag", "jxp_path_ikko"),
            _negative(trigger, "jxp_has_any_route_trigger", "yes"),
            _positive(trigger, "jxp_has_ikko_opening_trigger", "yes"),
        )
    )
    option = options[0] if len(options) == 1 else None
    valid_option = bool(
        option is not None
        and _positive(option, "jxp_74_ijp_route_entry_effect", "yes")
        and not _positive(option, "set_country_flag", "jxp_path_ikko")
    )
    if not valid_trigger:
        result.add(
            "ijp_loop.legacy_entry_gate",
            "jxp_ikko.1 lacks IJP/path/no-route opening defensive entry branches",
            LEGACY_EVENT_FILE.as_posix(),
        )
    if not valid_option:
        result.add(
            "ijp_loop.legacy_entry_effect",
            "jxp_ikko.1 must delegate its only option to canonical IJP route entry",
            LEGACY_EVENT_FILE.as_posix(),
        )
    return int(valid_trigger and valid_option)


def _check_disaster_isolation(
    disaster_document: Document | None,
    context: ValidationContext,
    result: CheckResult,
) -> int:
    disasters = _top_objects(disaster_document)
    ikko = disasters.get("jxp_ikko_rising")
    ikko_potential = _named_object(ikko, "potential")
    shimabara = disasters.get("jxp_shimabara_fire")
    shimabara_start = _named_object(shimabara, "can_start")
    contract_ok = all(
        (
            _positive(ikko_potential, "jxp_a_shinshu_crisis_scope_trigger", "yes"),
            _negative(
                ikko_potential,
                "jxp_a_ijp_has_terminal_settlement_trigger",
                "yes",
            ),
            first_scalar(ikko, "on_start") == "jxp_shinshu.100",
            first_scalar(ikko, "on_end") == "jxp_shinshu.190",
            _positive(shimabara_start, "has_any_disaster", "no"),
            _positive(
                shimabara_start,
                "has_country_flag",
                "jxp_hidden_christians_seen",
            ),
        )
    )
    if not contract_ok:
        result.add(
            "ijp_loop.disaster_contract",
            "Ikko rising lost the Shinshu lifecycle hooks/terminal guard, or Shimabara lost its false-positive gates",
            DISASTER_FILE.as_posix(),
        )

    loop_files = (
        TRIGGER_FILE,
        EFFECT_FILE,
        MODIFIER_FILE,
        DECISION_FILE,
        DEBUG_DECISION_FILE,
        EVENT_FILE,
    )
    text = "\n".join(
        (context.mod_root / relative).read_text(encoding="utf-8-sig")
        for relative in loop_files
        if (context.mod_root / relative).is_file()
    )
    forbidden_writes = re.findall(
        r"(?:set_country_flag|add_disaster_progress)\s*=\s*"
        r"(?:jxp_(?:ikko_rising|shimabara)[A-Za-z0-9_]*|\{[^}]*jxp_(?:ikko_rising|shimabara))",
        text,
    )
    if forbidden_writes or "jxp_hidden_christians_seen" in text:
        result.add(
            "ijp_loop.disaster_write",
            "IJP loop manufactures Ikko/Shimabara disaster pressure instead of remaining isolated",
            EVENT_FILE.as_posix(),
        )
    return int(contract_ok and not forbidden_writes and "jxp_hidden_christians_seen" not in text)


def _check_compatibility(context: ValidationContext, result: CheckResult) -> int:
    files = (
        TRIGGER_FILE,
        EFFECT_FILE,
        MODIFIER_FILE,
        DECISION_FILE,
        DEBUG_DECISION_FILE,
        EVENT_FILE,
    )
    text = "\n".join(
        (context.mod_root / relative).read_text(encoding="utf-8-sig")
        for relative in files
        if (context.mod_root / relative).is_file()
    )
    map_tokens = set(MAP_TOKEN.findall(text))
    tags = set(re.findall(r"\btag\s*=\s*([A-Z]{3})\b", text))
    areas = set(re.findall(r"\barea\s*=\s*([A-Za-z0-9_]+)", text))
    if map_tokens != {ALLOWED_MAP_FLAG}:
        result.add(
            "ijp_loop.map_contract",
            f"map references are {sorted(map_tokens)}; expected only {ALLOWED_MAP_FLAG}",
            TRIGGER_FILE.as_posix(),
        )
    if COMPANION_PROVINCE.search(text) or tags - {"IJP"}:
        result.add(
            "ijp_loop.map_contract",
            "IJP loop references a companion-only province or foreign literal tag",
            EVENT_FILE.as_posix(),
        )
    if areas != {"kinai_area", "saigoku_area"}:
        result.add(
            "ijp_loop.map_fallback",
            f"vanilla geography fallback changed from kinai/saigoku: {sorted(areas)}",
            TRIGGER_FILE.as_posix(),
        )
    fallback_ok = all(
        token in text
        for token in (
            "area = kinai_area",
            "area = saigoku_area",
            "has_province_modifier = jxp_ikko_terauchi_town",
            ALLOWED_MAP_FLAG,
        )
    )
    if not fallback_ok:
        result.add(
            "ijp_loop.map_fallback",
            "semantic Ikko heartland lost its vanilla areas or temple-town fallback",
            TRIGGER_FILE.as_posix(),
        )
    return int(
        map_tokens == {ALLOWED_MAP_FLAG}
        and not COMPANION_PROVINCE.search(text)
        and not (tags - {"IJP"})
        and areas == {"kinai_area", "saigoku_area"}
        and fallback_ok
    )


def _expected_localisation_keys() -> set[str]:
    keys: set[str] = set()
    for decision_id in EXPECTED_DECISIONS + EXPECTED_DEBUG_DECISIONS:
        keys.update({f"{decision_id}_title", f"{decision_id}_desc"})
    for event_id in EXPECTED_EVENTS[:3]:
        keys.update({f"{event_id}.t", f"{event_id}.d"})
        keys.update(f"{event_id}.{letter}" for letter in "abc")
    for modifier in EXPECTED_MODIFIERS:
        keys.update({modifier, f"{modifier}_desc"})
    keys.update(
        {
            "jxp_74_ijp_pressure_starts_15_tt",
            "jxp_74_ijp_pressure_rises_10_tt",
            "jxp_74_ijp_pressure_rises_15_tt",
            "jxp_74_ijp_pressure_rises_20_tt",
            "jxp_74_ijp_pressure_falls_10_tt",
            "jxp_74_ijp_pressure_falls_15_tt",
            "jxp_74_ijp_pressure_falls_20_tt",
            "jxp_74_ijp_pressure_falls_40_tt",
            "jxp_74_ijp_transform_tt",
            "jxp_74_ijp_stand_down_tt",
        }
    )
    return keys


def _check_localisation(context: ValidationContext, result: CheckResult) -> int:
    expected = _expected_localisation_keys()
    source_path = context.mod_root / SOURCE_LOC_FILE
    active_path = context.mod_root / ACTIVE_LOC_FILE
    if not source_path.is_file() or not active_path.is_file():
        result.add(
            "ijp_loop.localisation_missing",
            "IJP source or active localisation file is missing",
            SOURCE_LOC_FILE.as_posix(),
        )
        return 0
    source = source_path.read_text(encoding="utf-8-sig")
    active_bytes = active_path.read_bytes()
    active = active_bytes.decode("utf-8-sig")
    source_keys = set(LOCALISATION_KEY.findall(source))
    active_keys = set(LOCALISATION_KEY.findall(active))
    for label, keys, relative in (
        ("source", source_keys, SOURCE_LOC_FILE),
        ("active", active_keys, ACTIVE_LOC_FILE),
    ):
        missing = sorted(expected - keys)
        if missing:
            result.add(
                "ijp_loop.localisation_keys",
                f"{label} localisation misses {missing}",
                relative.as_posix(),
            )
    if not active_bytes.startswith(b"\xef\xbb\xbf") or RAW_CJK.search(active):
        result.add(
            "ijp_loop.localisation_pipeline",
            "active IJP localisation must be BOM-prefixed and EU4SpecialEscape encoded",
            ACTIVE_LOC_FILE.as_posix(),
        )
    return len(expected & source_keys & active_keys)


def check_ijp_loop(context: ValidationContext) -> CheckResult:
    """Return the executable JXP-009 long-loop contract."""

    result = CheckResult("IJP congregation-pressure long-term loop")
    trigger_document = _document(context, TRIGGER_FILE, result)
    effect_document = _document(context, EFFECT_FILE, result)
    modifier_document = _document(context, MODIFIER_FILE, result)
    decision_document = _document(context, DECISION_FILE, result)
    debug_document = _document(context, DEBUG_DECISION_FILE, result)
    event_document = _document(context, EVENT_FILE, result)
    legacy_document = _document(context, LEGACY_EVENT_FILE, result)
    disaster_document = _document(context, DISASTER_FILE, result)

    triggers = _check_trigger_contract(trigger_document, result)
    repeatable = _check_decisions(decision_document, result)
    debug_entries = _check_debug_decisions(debug_document, result)
    visible_options, ai_options = _check_events(event_document, result)
    exits = _check_effects(effect_document, result)
    modifiers = _check_modifiers_and_durations(
        modifier_document,
        (effect_document, decision_document, event_document),
        result,
    )
    legacy = _check_legacy_entry(legacy_document, result)
    disasters = _check_disaster_isolation(disaster_document, context, result)
    map_contract = _check_compatibility(context, result)
    localisation = _check_localisation(context, result)

    result.metrics.update(
        {
            "route_pressure_triggers": triggers,
            "player_decisions": len(EXPECTED_DECISIONS),
            "repeatable_governance_choices": repeatable,
            "events": len(EXPECTED_EVENTS),
            "visible_event_options": visible_options,
            "ai_weighted_options": ai_options,
            "exit_paths": exits,
            "modifiers": modifiers,
            "legacy_entry_hardened": legacy,
            "disaster_isolation": disasters,
            "debug_entries": debug_entries,
            "map_contract": map_contract,
            "localisation_keys": localisation,
        }
    )
    result.notes.append(
        "The main mod consumes only jxp_map_compat_ikko_heartland and retains kinai/saigoku plus temple-town fallback."
    )
    result.notes.append(
        "The dedicated jxp_74_ijp_debug_reset_effect is intentionally not wired into the canonical debug root by this parallel slice."
    )
    result.notes.append(
        "Static proof cannot replace runtime cadence, AI-observer, decision-tooltip, tag-change, and save/reload checks."
    )
    result.summary = (
        f"{repeatable}/3 governance choices, {exits}/2 exits, "
        f"{visible_options} visible event choices, {modifiers}/11 finite modifiers"
    )
    return result
