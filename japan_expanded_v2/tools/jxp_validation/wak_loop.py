"""Validate the WAK privateer-league long-term gameplay loop.

The contract fixes a complete state machine rather than counting flavour:
exclusive entry, three repeatable investments with finite cooldowns, bounded
pressure, recurring rewards and costs, AI choices, two exits, route-loss
cleanup, and additive companion-map geography consumption.
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


TRIGGER_FILE = Path("common/scripted_triggers/jxp_72_wak_triggers.txt")
EFFECT_FILE = Path("common/scripted_effects/jxp_72_wak_effects.txt")
MODIFIER_FILE = Path("common/event_modifiers/jxp_72_wak_modifiers.txt")
DECISION_FILE = Path("decisions/jxp_72_wak_decisions.txt")
DEBUG_DECISION_FILE = Path("decisions/jxp_72_wak_debug_decisions.txt")
EVENT_FILE = Path("events/jxp_72_wak_events.txt")
LEGACY_EVENT_FILE = Path("events/jxp_wokou_events.txt")
DEBUG_ROOT_FILE = Path("common/scripted_effects/jxp_debug_effects.txt")
SOURCE_LOC_FILE = Path("localisation_source/jxp_72_wak_l_english_utf8_source.yml")
ACTIVE_LOC_FILE = Path("localisation/jxp_72_wak_l_english.yml")

ACTIVE_FLAG = "jxp_72_wak_cycle_active"
PRESSURE_VARIABLE = "jxp_72_wak_pressure"
ALLOWED_MAP_FLAG = "jxp_map_compat_wokou_waters"

EXPECTED_MODIFIERS = (
    "jxp_72_wak_sea_league_charter",
    "jxp_72_wak_rotating_letters",
    "jxp_72_wak_free_port_endowment",
    "jxp_72_wak_convoy_courts",
    "jxp_72_wak_unlicensed_dividend",
    "jxp_72_wak_federation_hearing",
    "jxp_72_wak_repression_aftershock",
    "jxp_72_wak_black_current_overreach",
    "jxp_72_wak_crisis_recess",
    "jxp_72_wak_chartered_maritime_state",
    "jxp_72_wak_flotillas_disarmed",
)

EXPECTED_DECISIONS = (
    "jxp_72_decision_convene_sea_league",
    "jxp_72_decision_rotate_letters_of_mark",
    "jxp_72_decision_endow_free_ports",
    "jxp_72_decision_fund_convoy_courts",
    "jxp_72_decision_charter_maritime_state",
    "jxp_72_decision_stand_down_flotillas",
)

EXPECTED_DEBUG_DECISIONS = (
    "jxp_debug_72_wak_start_cycle",
    "jxp_debug_72_wak_add_pressure",
    "jxp_debug_72_wak_fire_dividend",
    "jxp_debug_72_wak_fire_crisis",
    "jxp_debug_72_wak_reset_cycle",
)

EXPECTED_EFFECTS = (
    "jxp_72_wak_clamp_pressure_effect",
    "jxp_72_wak_add_pressure_5_effect",
    "jxp_72_wak_add_pressure_10_effect",
    "jxp_72_wak_add_pressure_15_effect",
    "jxp_72_wak_add_pressure_20_effect",
    "jxp_72_wak_subtract_pressure_10_effect",
    "jxp_72_wak_subtract_pressure_15_effect",
    "jxp_72_wak_subtract_pressure_20_effect",
    "jxp_72_wak_subtract_pressure_40_effect",
    "jxp_72_wak_start_cycle_effect",
    "jxp_72_wak_cleanup_effect",
    "jxp_72_wak_transform_to_maritime_state_effect",
    "jxp_72_wak_stand_down_cycle_effect",
    "jxp_72_wak_debug_reset_effect",
)

PRESSURE_EFFECT_VALUES = {
    "jxp_72_wak_add_pressure_5_effect": "5",
    "jxp_72_wak_add_pressure_10_effect": "10",
    "jxp_72_wak_add_pressure_15_effect": "15",
    "jxp_72_wak_add_pressure_20_effect": "20",
    "jxp_72_wak_subtract_pressure_10_effect": "-10",
    "jxp_72_wak_subtract_pressure_15_effect": "-15",
    "jxp_72_wak_subtract_pressure_20_effect": "-20",
    "jxp_72_wak_subtract_pressure_40_effect": "-40",
}

REPEATABLE_DECISIONS = {
    "jxp_72_decision_rotate_letters_of_mark": (
        "jxp_72_wak_rotating_letters",
        "jxp_72_wak_add_pressure_15_effect",
    ),
    "jxp_72_decision_endow_free_ports": (
        "jxp_72_wak_free_port_endowment",
        "jxp_72_wak_add_pressure_5_effect",
    ),
    "jxp_72_decision_fund_convoy_courts": (
        "jxp_72_wak_convoy_courts",
        "jxp_72_wak_subtract_pressure_15_effect",
    ),
}

EXPECTED_EVENTS = tuple(f"jxp_wak_loop.{number}" for number in range(1, 6))


_EXPECTED_TRIGGER_DOCUMENT = parse_text(
    r"""
jxp_72_wak_route_trigger = {
	jxp_is_japanese_polity_trigger = yes
	OR = { tag = WAK has_country_flag = jxp_path_wokou }
	NOT = { OR = {
		has_country_flag = jxp_path_sakoku
		has_country_flag = jxp_path_open_trade
		has_country_flag = jxp_path_kirishitan
		has_country_flag = jxp_path_confucian
		has_country_flag = jxp_path_imperial
		has_country_flag = jxp_path_reformed
		has_country_flag = jxp_path_kaikyo
		has_country_flag = jxp_path_ikko
	} }
}
jxp_72_wak_cycle_active_trigger = {
	jxp_72_wak_route_trigger = yes
	has_country_flag = jxp_72_wak_cycle_active
	has_country_modifier = jxp_72_wak_sea_league_charter
}
jxp_72_wak_harbor_network_trigger = {
	OR = {
		num_of_ports = 8
		any_owned_province = { has_province_flag = jxp_map_compat_wokou_waters }
	}
}
jxp_72_wak_pressure_at_least_10_trigger = {
	check_variable = { which = jxp_72_wak_pressure value = 10 }
}
jxp_72_wak_pressure_at_least_50_trigger = {
	check_variable = { which = jxp_72_wak_pressure value = 50 }
}
jxp_72_wak_pressure_at_least_70_trigger = {
	check_variable = { which = jxp_72_wak_pressure value = 70 }
}
jxp_72_wak_pressure_at_least_85_trigger = {
	check_variable = { which = jxp_72_wak_pressure value = 85 }
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
            "wak_loop.file_missing",
            f"required WAK-loop file is missing: {relative.as_posix()}",
            relative.as_posix(),
        )
        return None
    document = context.document(source)
    if document is None:
        result.add(
            "wak_loop.parse",
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


def _check_trigger_contract(
    document: Document | None, result: CheckResult
) -> int:
    actual = _top_objects(document)
    expected_keys = set(EXPECTED_TRIGGER_BODIES)
    if set(actual) != expected_keys:
        result.add(
            "wak_loop.trigger_inventory",
            "WAK loop trigger inventory differs from the seven-trigger contract",
            TRIGGER_FILE.as_posix(),
        )
    matched = 0
    for key, expected in EXPECTED_TRIGGER_BODIES.items():
        body = actual.get(key)
        if body is None or _canonical(body) != _canonical(expected):
            result.add(
                "wak_loop.trigger_contract",
                f"{key} no longer matches its exact route/pressure/geography contract",
                TRIGGER_FILE.as_posix(),
            )
        else:
            matched += 1
    active = actual.get("jxp_72_wak_cycle_active_trigger")
    if not _positive(
        active, "has_country_modifier", "jxp_72_wak_sea_league_charter"
    ):
        result.add(
            "wak_loop.charter_lifecycle",
            "WAK active-cycle state must expire with its 3650-day sea-league charter",
            TRIGGER_FILE.as_posix(),
        )
    return matched


def _check_decisions(document: Document | None, result: CheckResult) -> int:
    decisions = _decision_bodies(document)
    if set(decisions) != set(EXPECTED_DECISIONS):
        result.add(
            "wak_loop.decision_inventory",
            "player decision inventory differs from the six-decision contract",
            DECISION_FILE.as_posix(),
        )

    entry = decisions.get("jxp_72_decision_convene_sea_league")
    entry_potential = _named_object(entry, "potential")
    entry_allow = _named_object(entry, "allow")
    entry_effect = _named_object(entry, "effect")
    if not _positive(entry_potential, "jxp_72_wak_route_trigger", "yes"):
        result.add(
            "wak_loop.entry_gate",
            "sea-league entry is not positively gated by the exclusive WAK route trigger",
            DECISION_FILE.as_posix(),
        )
    for name in (
        ACTIVE_FLAG,
        "jxp_72_wak_chartered_maritime_state",
        "jxp_72_wak_flotillas_disarmed",
    ):
        key = "has_country_flag" if name == ACTIVE_FLAG else "has_country_modifier"
        if not _negative(entry_potential, key, name):
            result.add(
                "wak_loop.entry_gate",
                f"sea-league entry does not exclude active/cooldown state {name}",
                DECISION_FILE.as_posix(),
            )
    for key, value in (
        ("num_of_ports", "5"),
        ("jxp_oceanic_opening_at_least_35", "yes"),
        ("jxp_not_sakoku_locked_trigger", "yes"),
    ):
        if not _positive(entry_allow, key, value):
            result.add(
                "wak_loop.entry_gate",
                f"sea-league entry is missing allow condition {key} = {value}",
                DECISION_FILE.as_posix(),
            )
    if not _positive(entry_effect, "jxp_72_wak_start_cycle_effect", "yes"):
        result.add(
            "wak_loop.entry_effect",
            "sea-league entry does not call the canonical cycle start effect",
            DECISION_FILE.as_posix(),
        )

    repeatable = 0
    for decision_id, (cooldown, pressure_effect) in REPEATABLE_DECISIONS.items():
        body = decisions.get(decision_id)
        potential = _named_object(body, "potential")
        allow = _named_object(body, "allow")
        effect = _named_object(body, "effect")
        if not _positive(potential, "jxp_72_wak_cycle_active_trigger", "yes"):
            result.add(
                "wak_loop.investment_gate",
                f"{decision_id} is not gated by the active-cycle trigger",
                DECISION_FILE.as_posix(),
            )
        if not _negative(allow, "has_country_modifier", cooldown):
            result.add(
                "wak_loop.investment_cooldown",
                f"{decision_id} does not block its own finite cooldown {cooldown}",
                DECISION_FILE.as_posix(),
            )
        writes = dict(_modifier_writes(effect))
        if writes.get(cooldown) != "1825":
            result.add(
                "wak_loop.investment_cooldown",
                f"{decision_id} must write {cooldown} for exactly 1825 days",
                DECISION_FILE.as_posix(),
            )
        if not _positive(effect, pressure_effect, "yes"):
            result.add(
                "wak_loop.investment_pressure",
                f"{decision_id} does not apply {pressure_effect}",
                DECISION_FILE.as_posix(),
            )
        if all(
            (
                _positive(potential, "jxp_72_wak_cycle_active_trigger", "yes"),
                _negative(allow, "has_country_modifier", cooldown),
                writes.get(cooldown) == "1825",
                _positive(effect, pressure_effect, "yes"),
            )
        ):
            repeatable += 1

    exits = {
        "jxp_72_decision_charter_maritime_state": (
            "jxp_72_wak_transform_to_maritime_state_effect",
            "jxp_72_wak_pressure_at_least_50_trigger",
        ),
        "jxp_72_decision_stand_down_flotillas": (
            "jxp_72_wak_stand_down_cycle_effect",
            None,
        ),
    }
    for decision_id, (exit_effect, threshold) in exits.items():
        body = decisions.get(decision_id)
        potential = _named_object(body, "potential")
        allow = _named_object(body, "allow")
        effect = _named_object(body, "effect")
        if not _positive(potential, "jxp_72_wak_cycle_active_trigger", "yes"):
            result.add(
                "wak_loop.exit_gate",
                f"{decision_id} is not gated by an active cycle",
                DECISION_FILE.as_posix(),
            )
        if not _positive(allow, "is_at_war", "no"):
            result.add(
                "wak_loop.exit_gate",
                f"{decision_id} lacks a peacetime settlement gate",
                DECISION_FILE.as_posix(),
            )
        if threshold and not _positive(allow, threshold, "yes"):
            result.add(
                "wak_loop.exit_gate",
                f"{decision_id} lacks its pressure threshold {threshold}",
                DECISION_FILE.as_posix(),
            )
        if not _positive(effect, exit_effect, "yes"):
            result.add(
                "wak_loop.exit_path",
                f"{decision_id} does not call canonical exit {exit_effect}",
                DECISION_FILE.as_posix(),
            )

    for decision_id in EXPECTED_DECISIONS:
        ai = _named_object(decisions.get(decision_id), "ai_will_do")
        if _factor(ai) is None or _factor(ai) <= 0:
            result.add(
                "wak_loop.ai_decision",
                f"{decision_id} has no positive AI base weight",
                DECISION_FILE.as_posix(),
            )
    return repeatable


def _check_debug_decisions(document: Document | None, result: CheckResult) -> int:
    decisions = _decision_bodies(document)
    if set(decisions) != set(EXPECTED_DEBUG_DECISIONS):
        result.add(
            "wak_loop.debug_inventory",
            "WAK debug inventory differs from the five-entry contract",
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
                "wak_loop.debug_gate",
                f"{decision_id} is not player/debug-only with zero AI weight",
                DEBUG_DECISION_FILE.as_posix(),
            )
    reset_effect = _named_object(
        decisions.get("jxp_debug_72_wak_reset_cycle"), "effect"
    )
    if not _positive(reset_effect, "jxp_72_wak_debug_reset_effect", "yes"):
        result.add(
            "wak_loop.debug_cleanup",
            "dedicated WAK debug reset does not call canonical cleanup",
            DEBUG_DECISION_FILE.as_posix(),
        )
    return matched


def _check_events(document: Document | None, result: CheckResult) -> tuple[int, int]:
    events = _event_bodies(document)
    if set(events) != set(EXPECTED_EVENTS):
        result.add(
            "wak_loop.event_inventory",
            "WAK loop event inventory differs from events 1-4",
            EVENT_FILE.as_posix(),
        )

    visible_options = 0
    ai_options = 0
    for event_id in EXPECTED_EVENTS[:3]:
        body = events.get(event_id)
        trigger = _named_object(body, "trigger")
        mtth = _named_object(body, "mean_time_to_happen")
        options = [
            entry.value
            for entry in entries_named(body, "option") if body is not None
            if isinstance(entry.value, Object)
        ]
        if not _positive(trigger, "jxp_72_wak_cycle_active_trigger", "yes"):
            result.add(
                "wak_loop.event_gate",
                f"{event_id} is not positively gated by the active cycle",
                EVENT_FILE.as_posix(),
            )
        if mtth is None or first_scalar(mtth, "days") is None:
            result.add(
                "wak_loop.event_cadence",
                f"{event_id} has no mean-time cadence",
                EVENT_FILE.as_posix(),
            )
        if len(options) != 3:
            result.add(
                "wak_loop.event_options",
                f"{event_id} has {len(options)} choices; expected 3",
                EVENT_FILE.as_posix(),
            )
        visible_options += len(options)
        for option in options:
            ai = _named_object(option, "ai_chance")
            if _factor(ai) is None or _factor(ai) <= 0:
                result.add(
                    "wak_loop.ai_event",
                    f"an option in {event_id} has no positive AI base weight",
                    EVENT_FILE.as_posix(),
                )
            else:
                ai_options += 1

    event2_trigger = _named_object(events.get("jxp_wak_loop.2"), "trigger")
    if not _positive(
        event2_trigger, "jxp_72_wak_pressure_at_least_50_trigger", "yes"
    ):
        result.add(
            "wak_loop.pressure_escalation",
            "federation quarrel event no longer starts at pressure 50",
            EVENT_FILE.as_posix(),
        )
    event3 = events.get("jxp_wak_loop.3")
    event3_trigger = _named_object(event3, "trigger")
    if not _positive(
        event3_trigger, "jxp_72_wak_pressure_at_least_85_trigger", "yes"
    ) or not _negative(
        event3_trigger, "has_country_modifier", "jxp_72_wak_crisis_recess"
    ):
        result.add(
            "wak_loop.pressure_crisis",
            "black-current crisis must require pressure 85 and its finite recess",
            EVENT_FILE.as_posix(),
        )
    crisis_options = (
        [entry.value for entry in entries_named(event3, "option") if isinstance(entry.value, Object)]
        if event3 is not None
        else []
    )
    if not any(
        _positive(option, "jxp_72_wak_transform_to_maritime_state_effect", "yes")
        and (_factor(_named_object(option, "ai_chance")) or 0) > 0
        for option in crisis_options
    ):
        result.add(
            "wak_loop.ai_exit",
            "crisis lacks an AI-reachable maritime-state transformation",
            EVENT_FILE.as_posix(),
        )

    cleanup = events.get("jxp_wak_loop.4")
    cleanup_trigger = _named_object(cleanup, "trigger")
    cleanup_mtth = _named_object(cleanup, "mean_time_to_happen")
    cleanup_immediate = _named_object(cleanup, "immediate")
    cleanup_options = entries_named(cleanup, "option") if cleanup is not None else ()
    if not all(
        (
            first_scalar(cleanup, "hidden") == "yes" if cleanup else False,
            _positive(cleanup_trigger, "has_country_flag", ACTIVE_FLAG),
            _negative(cleanup_trigger, "jxp_72_wak_cycle_active_trigger", "yes"),
            first_scalar(cleanup_mtth, "days") == "1" if cleanup_mtth else False,
            _positive(cleanup_immediate, "jxp_72_wak_cleanup_effect", "yes"),
            len(cleanup_options) == 1,
        )
    ):
        result.add(
            "wak_loop.route_loss_cleanup",
            "hidden one-day event must clean route loss or charter expiry and retain one OK option",
            EVENT_FILE.as_posix(),
        )

    expiry = events.get("jxp_wak_loop.5")
    expiry_immediate = _named_object(expiry, "immediate")
    expiry_if = _named_object(expiry_immediate, "if")
    expiry_limit = _named_object(expiry_if, "limit")
    expiry_options = entries_named(expiry, "option") if expiry is not None else ()
    if not all(
        (
            first_scalar(expiry, "hidden") == "yes" if expiry else False,
            first_scalar(expiry, "is_triggered_only") == "yes" if expiry else False,
            _positive(expiry_limit, "has_country_flag", ACTIVE_FLAG),
            _negative(
                expiry_limit,
                "has_country_modifier",
                "jxp_72_wak_sea_league_charter",
            ),
            _positive(expiry_if, "jxp_72_wak_cleanup_effect", "yes"),
            len(expiry_options) == 1,
        )
    ):
        result.add(
            "wak_loop.expiry_lifecycle",
            "hidden WAK expiry must clean only an active cycle whose charter is absent",
            EVENT_FILE.as_posix(),
        )
    return visible_options, ai_options


def _check_effects(document: Document | None, result: CheckResult) -> int:
    effects = _top_objects(document)
    if set(effects) != set(EXPECTED_EFFECTS):
        result.add(
            "wak_loop.effect_inventory",
            "WAK effect inventory differs from the fixed 14-effect contract",
            EFFECT_FILE.as_posix(),
        )

    for effect_id, value in PRESSURE_EFFECT_VALUES.items():
        body = effects.get(effect_id)
        if not _variable_operation(body, "change_variable", value) or not _positive(
            body, "jxp_72_wak_clamp_pressure_effect", "yes"
        ):
            result.add(
                "wak_loop.pressure_effect",
                f"{effect_id} must change pressure by {value} and clamp it",
                EFFECT_FILE.as_posix(),
            )

    clamp = effects.get("jxp_72_wak_clamp_pressure_effect")
    if not _variable_operation(clamp, "set_variable", "0") or not _variable_operation(
        clamp, "set_variable", "100"
    ):
        result.add(
            "wak_loop.pressure_bounds",
            "pressure clamp no longer fixes both the 0 and 100 bounds",
            EFFECT_FILE.as_posix(),
        )

    start = effects.get("jxp_72_wak_start_cycle_effect")
    start_writes = dict(_modifier_writes(start))
    if not all(
        (
            _positive(start, "jxp_72_wak_cleanup_effect", "yes"),
            _positive(start, "set_country_flag", ACTIVE_FLAG),
            _variable_operation(start, "set_variable", "10"),
            start_writes.get("jxp_72_wak_sea_league_charter") == "3650",
            _scheduled_event(start, "jxp_wak_loop.5", "3651"),
        )
    ):
        result.add(
            "wak_loop.start_state",
            "cycle start must clean, activate, initialize pressure 10, add a finite charter, and schedule guarded expiry",
            EFFECT_FILE.as_posix(),
        )

    cleanup = effects.get("jxp_72_wak_cleanup_effect")
    if not _positive(cleanup, "clr_country_flag", ACTIVE_FLAG) or not _variable_operation(
        cleanup, "set_variable", "0"
    ):
        result.add(
            "wak_loop.cleanup_state",
            "cycle cleanup must clear the active flag and reset pressure to 0",
            EFFECT_FILE.as_posix(),
        )
    for modifier in EXPECTED_MODIFIERS:
        if not _positive(cleanup, "remove_country_modifier", modifier):
            result.add(
                "wak_loop.cleanup_modifier",
                f"cycle cleanup cannot remove {modifier}",
                EFFECT_FILE.as_posix(),
            )

    exits = {
        "jxp_72_wak_transform_to_maritime_state_effect": (
            "jxp_72_wak_chartered_maritime_state",
            "7300",
        ),
        "jxp_72_wak_stand_down_cycle_effect": (
            "jxp_72_wak_flotillas_disarmed",
            "3650",
        ),
    }
    closed = 0
    for effect_id, (modifier, duration) in exits.items():
        body = effects.get(effect_id)
        writes = dict(_modifier_writes(body))
        if _positive(body, "jxp_72_wak_cleanup_effect", "yes") and writes.get(
            modifier
        ) == duration:
            closed += 1
        else:
            result.add(
                "wak_loop.exit_effect",
                f"{effect_id} must clean active state then add finite {modifier}",
                EFFECT_FILE.as_posix(),
            )
    if not _positive(
        effects.get("jxp_72_wak_debug_reset_effect"),
        "jxp_72_wak_cleanup_effect",
        "yes",
    ):
        result.add(
            "wak_loop.debug_cleanup",
            "WAK debug reset does not reuse canonical cleanup",
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
            "wak_loop.modifier_inventory",
            "WAK modifier inventory differs from the eleven-modifier contract",
            MODIFIER_FILE.as_posix(),
        )
    writes = [
        write
        for document in documents
        if document is not None
        for write in _modifier_writes(document.root)
    ]
    for name, duration in writes:
        if name not in EXPECTED_MODIFIERS:
            result.add(
                "wak_loop.modifier_undefined",
                f"WAK loop writes unexpected modifier {name}",
                MODIFIER_FILE.as_posix(),
            )
            continue
        try:
            finite = duration is not None and int(duration) > 0
        except ValueError:
            finite = False
        if not finite:
            result.add(
                "wak_loop.modifier_duration",
                f"{name} is written with non-finite duration {duration!r}",
                MODIFIER_FILE.as_posix(),
            )
    return len(definitions)


def _check_legacy_entry(document: Document | None, result: CheckResult) -> int:
    event = _event_bodies(document).get("jxp_wokou.1")
    trigger = _named_object(event, "trigger")
    options = (
        [entry.value for entry in entries_named(event, "option") if isinstance(entry.value, Object)]
        if event is not None
        else []
    )
    valid_trigger = all(
        (
            _positive(trigger, "jxp_is_japanese_polity_trigger", "yes"),
            _positive(trigger, "tag", "WAK"),
            _positive(trigger, "has_country_flag", "jxp_path_wokou"),
            _negative(trigger, "jxp_has_any_route_trigger", "yes"),
            _positive(trigger, "jxp_has_wokou_opening_trigger", "yes"),
        )
    )
    option = options[0] if len(options) == 1 else None
    clear_index = _direct_index(option, "jxp_clear_all_route_flags_effect", "yes")
    set_index = _direct_index(option, "set_country_flag", "jxp_path_wokou")
    if not valid_trigger:
        result.add(
            "wak_loop.legacy_entry_gate",
            "jxp_wokou.1 lacks its WAK/path/no-route defensive trigger",
            LEGACY_EVENT_FILE.as_posix(),
        )
    if clear_index is None or set_index is None or clear_index >= set_index:
        result.add(
            "wak_loop.legacy_entry_clear",
            "jxp_wokou.1 must clear canonical route state before writing jxp_path_wokou",
            LEGACY_EVENT_FILE.as_posix(),
        )
    return int(valid_trigger and clear_index is not None and set_index is not None and clear_index < set_index)


def _check_debug_root(document: Document | None, result: CheckResult) -> int:
    root = _named_object(
        document.root if document is not None else None,
        "jxp_debug_clear_event_state_effect",
    )
    if not _positive(root, "jxp_72_wak_debug_reset_effect", "yes"):
        result.add(
            "wak_loop.debug_root",
            "canonical event-state debug reset cannot reach the WAK cleanup effect",
            DEBUG_ROOT_FILE.as_posix(),
        )
        return 0
    return 1


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
    if map_tokens != {ALLOWED_MAP_FLAG}:
        result.add(
            "wak_loop.map_contract",
            f"map references are {sorted(map_tokens)}; expected only {ALLOWED_MAP_FLAG}",
            TRIGGER_FILE.as_posix(),
        )
    if COMPANION_PROVINCE.search(text):
        result.add(
            "wak_loop.map_contract",
            "main WAK loop hard-references a companion-only province ID",
            EVENT_FILE.as_posix(),
        )
    tags = set(re.findall(r"\btag\s*=\s*([A-Z]{3})\b", text))
    if tags - {"WAK"}:
        result.add(
            "wak_loop.map_contract",
            f"WAK loop references unexpected literal tags {sorted(tags - {'WAK'})}",
            TRIGGER_FILE.as_posix(),
        )
    if re.search(r"\barea\s*=|\bprovince_id\s*=|\bowns\s*=", text):
        result.add(
            "wak_loop.map_contract",
            "WAK loop hard-references an area or province instead of semantic geography",
            EVENT_FILE.as_posix(),
        )
    if "num_of_ports = 8" not in text or ALLOWED_MAP_FLAG not in text:
        result.add(
            "wak_loop.map_fallback",
            "semantic Wokou waters must retain a standalone num_of_ports fallback",
            TRIGGER_FILE.as_posix(),
        )
    return int(
        map_tokens == {ALLOWED_MAP_FLAG}
        and not COMPANION_PROVINCE.search(text)
        and not (tags - {"WAK"})
        and not re.search(r"\barea\s*=|\bprovince_id\s*=|\bowns\s*=", text)
        and "num_of_ports = 8" in text
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
            "jxp_72_wak_pressure_starts_10_tt",
            "jxp_72_wak_pressure_rises_5_tt",
            "jxp_72_wak_pressure_rises_10_tt",
            "jxp_72_wak_pressure_rises_15_tt",
            "jxp_72_wak_pressure_rises_20_tt",
            "jxp_72_wak_pressure_falls_10_tt",
            "jxp_72_wak_pressure_falls_15_tt",
            "jxp_72_wak_pressure_falls_20_tt",
            "jxp_72_wak_pressure_falls_40_tt",
            "jxp_72_wak_transform_tt",
            "jxp_72_wak_stand_down_tt",
        }
    )
    return keys


def _check_localisation(context: ValidationContext, result: CheckResult) -> int:
    expected = _expected_localisation_keys()
    source_path = context.mod_root / SOURCE_LOC_FILE
    active_path = context.mod_root / ACTIVE_LOC_FILE
    if not source_path.is_file() or not active_path.is_file():
        result.add(
            "wak_loop.localisation_missing",
            "WAK source or active localisation file is missing",
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
                "wak_loop.localisation_keys",
                f"{label} localisation misses {missing}",
                relative.as_posix(),
            )
    if not active_bytes.startswith(b"\xef\xbb\xbf") or RAW_CJK.search(active):
        result.add(
            "wak_loop.localisation_pipeline",
            "active WAK localisation must be BOM-prefixed and EU4SpecialEscape encoded",
            ACTIVE_LOC_FILE.as_posix(),
        )
    return len(expected & source_keys & active_keys)


def check_wak_loop(context: ValidationContext) -> CheckResult:
    """Return the executable JXP-008 long-loop contract."""

    result = CheckResult("WAK privateer long-term loop")
    trigger_document = _document(context, TRIGGER_FILE, result)
    effect_document = _document(context, EFFECT_FILE, result)
    modifier_document = _document(context, MODIFIER_FILE, result)
    decision_document = _document(context, DECISION_FILE, result)
    debug_decision_document = _document(context, DEBUG_DECISION_FILE, result)
    event_document = _document(context, EVENT_FILE, result)
    legacy_event_document = _document(context, LEGACY_EVENT_FILE, result)
    debug_root_document = _document(context, DEBUG_ROOT_FILE, result)

    trigger_count = _check_trigger_contract(trigger_document, result)
    repeatable = _check_decisions(decision_document, result)
    debug_entries = _check_debug_decisions(debug_decision_document, result)
    visible_options, ai_options = _check_events(event_document, result)
    exits = _check_effects(effect_document, result)
    modifiers = _check_modifiers_and_durations(
        modifier_document,
        (effect_document, decision_document, event_document),
        result,
    )
    legacy_entry = _check_legacy_entry(legacy_event_document, result)
    debug_root = _check_debug_root(debug_root_document, result)
    map_contract = _check_compatibility(context, result)
    localisation = _check_localisation(context, result)

    result.metrics.update(
        {
            "route_pressure_triggers": trigger_count,
            "player_decisions": len(EXPECTED_DECISIONS),
            "repeatable_investments": repeatable,
            "events": len(EXPECTED_EVENTS),
            "visible_event_options": visible_options,
            "ai_weighted_options": ai_options,
            "exit_paths": exits,
            "modifiers": modifiers,
            "legacy_entry_hardened": legacy_entry,
            "debug_entries": debug_entries,
            "debug_root": debug_root,
            "map_contract": map_contract,
            "localisation_keys": localisation,
        }
    )
    result.notes.append(
        "The main mod consumes only jxp_map_compat_wokou_waters and keeps a port-count fallback."
    )
    result.notes.append(
        "Static proof cannot replace runtime timing, AI-observer, tooltip, and save/reload checks."
    )
    result.summary = (
        f"{repeatable}/3 repeatable investments, {exits}/2 exits, "
        f"{visible_options} visible event choices, {modifiers}/11 finite modifiers"
    )
    return result
