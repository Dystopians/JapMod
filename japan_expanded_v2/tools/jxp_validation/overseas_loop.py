"""Validate the JXP-011 Pacific overseas long-term loop.

The contract proves a bounded state machine around Manila-Nagasaki, Alaska,
California, and an oceanic Japanese state: semantic entry, route-divergent
investments, finite outcomes, pressure, recurring choices, two exits, AI
policy, route/disaster-loss cleanup, debug reachability, and standalone main-
mod compatibility.
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
)
from .core import CheckResult, ValidationContext


TRIGGER_FILE = Path("common/scripted_triggers/jxp_76_overseas_loop_triggers.txt")
EFFECT_FILE = Path("common/scripted_effects/jxp_76_overseas_loop_effects.txt")
MODIFIER_FILE = Path("common/event_modifiers/jxp_76_overseas_loop_modifiers.txt")
LEGACY_MODIFIER_FILE = Path("common/event_modifiers/jxp_03_event_modifiers.txt")
DECISION_FILE = Path("decisions/jxp_76_overseas_loop_decisions.txt")
DEBUG_DECISION_FILE = Path("decisions/jxp_76_overseas_debug_decisions.txt")
EVENT_FILE = Path("events/jxp_76_overseas_loop_events.txt")
DEBUG_ROOT_FILE = Path("common/scripted_effects/jxp_debug_effects.txt")
SOURCE_LOC_FILE = Path(
    "localisation_source/jxp_76_overseas_loop_l_english_utf8_source.yml"
)
ACTIVE_LOC_FILE = Path("localisation/jxp_76_overseas_loop_l_english.yml")

ACTIVE_FLAG = "jxp_76_pacific_network_active"
PRESSURE_VARIABLE = "jxp_76_pacific_pressure"

EXPECTED_TRIGGERS = (
    "jxp_76_pacific_network_eligible_trigger",
    "jxp_76_pacific_network_active_trigger",
    "jxp_76_pacific_manila_profile_trigger",
    "jxp_76_pacific_alaska_profile_trigger",
    "jxp_76_pacific_california_profile_trigger",
    "jxp_76_pacific_court_profile_trigger",
    "jxp_76_pacific_manila_anchor_trigger",
    "jxp_76_pacific_alaska_anchor_trigger",
    "jxp_76_pacific_california_anchor_trigger",
    "jxp_76_pacific_any_anchor_trigger",
    "jxp_76_pacific_pressure_at_least_10_trigger",
    "jxp_76_pacific_pressure_at_least_50_trigger",
    "jxp_76_pacific_pressure_at_least_70_trigger",
    "jxp_76_pacific_pressure_at_least_85_trigger",
)

EXPECTED_EFFECTS = (
    "jxp_76_pacific_clamp_pressure_effect",
    "jxp_76_pacific_add_pressure_5_effect",
    "jxp_76_pacific_add_pressure_10_effect",
    "jxp_76_pacific_add_pressure_15_effect",
    "jxp_76_pacific_add_pressure_20_effect",
    "jxp_76_pacific_subtract_pressure_10_effect",
    "jxp_76_pacific_subtract_pressure_15_effect",
    "jxp_76_pacific_subtract_pressure_20_effect",
    "jxp_76_pacific_subtract_pressure_40_effect",
    "jxp_76_pacific_network_cleanup_effect",
    "jxp_76_pacific_network_start_effect",
    "jxp_76_pacific_compact_effect",
    "jxp_76_pacific_stand_down_effect",
    "jxp_76_pacific_debug_reset_effect",
)

PRESSURE_EFFECT_VALUES = {
    "jxp_76_pacific_add_pressure_5_effect": "5",
    "jxp_76_pacific_add_pressure_10_effect": "10",
    "jxp_76_pacific_add_pressure_15_effect": "15",
    "jxp_76_pacific_add_pressure_20_effect": "20",
    "jxp_76_pacific_subtract_pressure_10_effect": "-10",
    "jxp_76_pacific_subtract_pressure_15_effect": "-15",
    "jxp_76_pacific_subtract_pressure_20_effect": "-20",
    "jxp_76_pacific_subtract_pressure_40_effect": "-40",
}

EXPECTED_MODIFIERS = (
    "jxp_76_pacific_network_charter",
    "jxp_76_manila_nagasaki_convoys",
    "jxp_76_alaska_survey_stations",
    "jxp_76_california_settlement_compacts",
    "jxp_76_pacific_court_council",
    "jxp_76_brokerage_dividend",
    "jxp_76_mission_house_network",
    "jxp_76_court_route_register",
    "jxp_76_public_network_hearing",
    "jxp_76_speculative_overreach",
    "jxp_76_arbitration_recent",
    "jxp_76_crisis_recess",
    "jxp_76_pacific_compact",
    "jxp_76_pacific_retrenchment",
)

EXPECTED_DECISIONS = (
    "jxp_76_decision_open_pacific_network",
    "jxp_76_decision_fund_manila_nagasaki_convoys",
    "jxp_76_decision_build_alaska_survey_stations",
    "jxp_76_decision_charter_california_settlements",
    "jxp_76_decision_convene_pacific_court_council",
    "jxp_76_decision_proclaim_pacific_compact",
    "jxp_76_decision_stand_down_pacific_network",
)

INVESTMENT_DECISIONS = {
    "jxp_76_decision_fund_manila_nagasaki_convoys": (
        "jxp_76_pacific_manila_profile_trigger",
        "jxp_76_pacific_manila_anchor_trigger",
        "jxp_76_manila_nagasaki_convoys",
        "jxp_76_pacific_add_pressure_15_effect",
    ),
    "jxp_76_decision_build_alaska_survey_stations": (
        "jxp_76_pacific_alaska_profile_trigger",
        "jxp_76_pacific_alaska_anchor_trigger",
        "jxp_76_alaska_survey_stations",
        "jxp_76_pacific_add_pressure_10_effect",
    ),
    "jxp_76_decision_charter_california_settlements": (
        "jxp_76_pacific_california_profile_trigger",
        "jxp_76_pacific_california_anchor_trigger",
        "jxp_76_california_settlement_compacts",
        "jxp_76_pacific_add_pressure_20_effect",
    ),
    "jxp_76_decision_convene_pacific_court_council": (
        "jxp_76_pacific_court_profile_trigger",
        None,
        "jxp_76_pacific_court_council",
        "jxp_76_pacific_subtract_pressure_15_effect",
    ),
}

EXPECTED_DEBUG_DECISIONS = (
    "jxp_debug_76_start_pacific_network",
    "jxp_debug_76_add_pacific_pressure",
    "jxp_debug_76_fire_pacific_review",
    "jxp_debug_76_fire_pacific_crisis",
    "jxp_debug_76_reset_pacific_network",
)

EXPECTED_EVENTS = tuple(f"jxp_overseas_loop.{number}" for number in range(1, 5))

ROUTE_PROFILE_REQUIREMENTS = {
    "jxp_76_pacific_manila_profile_trigger": {
        "jxp_path_open_trade",
        "jxp_path_kirishitan",
        "jxp_path_reformed",
        "jxp_path_kaikyo",
        "jxp_path_wokou",
    },
    "jxp_76_pacific_alaska_profile_trigger": {
        "jxp_path_open_trade",
        "jxp_path_reformed",
        "jxp_path_imperial",
    },
    "jxp_76_pacific_california_profile_trigger": {
        "jxp_path_open_trade",
        "jxp_path_kirishitan",
        "jxp_path_reformed",
    },
    "jxp_76_pacific_court_profile_trigger": {
        "jxp_path_confucian",
        "jxp_path_imperial",
    },
}

TOOLTIPS = {
    "jxp_76_pacific_pressure_starts_10_tt",
    "jxp_76_pacific_pressure_rises_10_tt",
    "jxp_76_pacific_pressure_rises_15_tt",
    "jxp_76_pacific_pressure_rises_20_tt",
    "jxp_76_pacific_pressure_falls_10_tt",
    "jxp_76_pacific_pressure_falls_15_tt",
    "jxp_76_pacific_pressure_falls_20_tt",
    "jxp_76_pacific_pressure_falls_40_tt",
    "jxp_76_pacific_compact_tt",
    "jxp_76_pacific_stand_down_tt",
}

RAW_CJK = re.compile(r"[\u3400-\u9fff]")
LOCALISATION_KEY = re.compile(r"^\s*([A-Za-z0-9_.-]+):\d+\s", re.MULTILINE)
MAP_TOKEN = re.compile(r"\bjxp_map_[A-Za-z0-9_]+\b")
COMPANION_PROVINCE = re.compile(r"\b(?:494[2-9]|49[5-7][0-9]|498[01])\b")


def _document(
    context: ValidationContext, relative: Path, result: CheckResult
) -> Document | None:
    source = context.mod_root / relative
    if not source.is_file():
        result.add(
            "overseas_loop.file_missing",
            f"required overseas-loop file is missing: {relative.as_posix()}",
            relative.as_posix(),
        )
        return None
    document = context.document(source)
    if document is None:
        result.add(
            "overseas_loop.parse",
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


def _options(obj: Object | None) -> list[Object]:
    if obj is None:
        return []
    return [
        entry.value
        for entry in entries_named(obj, "option")
        if isinstance(entry.value, Object)
    ]


def _modifier_writes(obj: Object | None) -> list[tuple[str, str | None]]:
    found: list[tuple[str, str | None]] = []
    if obj is None:
        return found
    for _path, entry in find_objects(obj, "add_country_modifier"):
        name = first_scalar(entry.value, "name")
        if name is not None:
            found.append((name, first_scalar(entry.value, "duration")))
    return found


def _mechanical_signature(obj: Object) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (entry.key, entry.value.text)
            for entry in obj.entries
            if entry.key is not None and isinstance(entry.value, Scalar)
        )
    )


def _check_legacy_modifier_signatures(
    modifier_document: Document | None,
    legacy_document: Document | None,
    result: CheckResult,
) -> int:
    current = _top_objects(modifier_document)
    legacy = _top_objects(legacy_document)
    legacy_by_signature: dict[tuple[tuple[str, str], ...], list[str]] = {}
    for legacy_id, body in legacy.items():
        legacy_by_signature.setdefault(_mechanical_signature(body), []).append(
            legacy_id
        )
    collisions = 0
    for modifier_id, body in current.items():
        duplicates = legacy_by_signature.get(_mechanical_signature(body), [])
        if duplicates:
            collisions += 1
            result.add(
                "overseas_loop.legacy_signature_collision",
                f"{modifier_id} mechanically duplicates legacy {sorted(duplicates)}",
                MODIFIER_FILE.as_posix(),
            )
    return collisions


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


def _check_triggers(document: Document | None, result: CheckResult) -> int:
    triggers = _top_objects(document)
    if set(triggers) != set(EXPECTED_TRIGGERS):
        result.add(
            "overseas_loop.trigger_inventory",
            "overseas trigger inventory differs from the fourteen-trigger contract",
            TRIGGER_FILE.as_posix(),
        )

    eligible = triggers.get("jxp_76_pacific_network_eligible_trigger")
    if not all(
        (
            _positive(eligible, "jxp_allows_private_overseas_trade_trigger", "yes"),
            _positive(eligible, "has_country_flag", "jxp_polity_initialized"),
            _positive(eligible, "has_country_flag", "jxp_pacific_charter_enacted"),
        )
    ):
        result.add(
            "overseas_loop.entry_semantics",
            "entry must reuse private-overseas eligibility, polity init, and the Pacific charter",
            TRIGGER_FILE.as_posix(),
        )

    active = triggers.get("jxp_76_pacific_network_active_trigger")
    if not all(
        (
            _positive(active, "jxp_76_pacific_network_eligible_trigger", "yes"),
            _positive(active, "has_country_flag", ACTIVE_FLAG),
            _positive(active, "has_any_disaster", "no"),
        )
    ):
        result.add(
            "overseas_loop.active_gate",
            "active network must retain eligibility, active state, and disaster isolation",
            TRIGGER_FILE.as_posix(),
        )

    for trigger_id, route_flags in ROUTE_PROFILE_REQUIREMENTS.items():
        body = triggers.get(trigger_id)
        missing = sorted(
            flag for flag in route_flags if not _positive(body, "has_country_flag", flag)
        )
        if missing:
            result.add(
                "overseas_loop.route_profiles",
                f"{trigger_id} misses route identities {missing}",
                TRIGGER_FILE.as_posix(),
            )

    any_anchor = triggers.get("jxp_76_pacific_any_anchor_trigger")
    for anchor in (
        "jxp_76_pacific_manila_anchor_trigger",
        "jxp_76_pacific_alaska_anchor_trigger",
        "jxp_76_pacific_california_anchor_trigger",
    ):
        if not _positive(any_anchor, anchor, "yes"):
            result.add(
                "overseas_loop.anchor_closure",
                f"entry anchor does not consume {anchor}",
                TRIGGER_FILE.as_posix(),
            )

    for threshold in ("10", "50", "70", "85"):
        body = triggers.get(f"jxp_76_pacific_pressure_at_least_{threshold}_trigger")
        if not _variable_operation(body, "check_variable", threshold):
            result.add(
                "overseas_loop.pressure_trigger",
                f"pressure threshold {threshold} is missing or targets the wrong variable",
                TRIGGER_FILE.as_posix(),
            )
    return len(triggers)


def _check_effects(document: Document | None, result: CheckResult) -> int:
    effects = _top_objects(document)
    if set(effects) != set(EXPECTED_EFFECTS):
        result.add(
            "overseas_loop.effect_inventory",
            "overseas effect inventory differs from the fourteen-effect contract",
            EFFECT_FILE.as_posix(),
        )

    for effect_id, value in PRESSURE_EFFECT_VALUES.items():
        body = effects.get(effect_id)
        if not _variable_operation(body, "change_variable", value) or not _positive(
            body, "jxp_76_pacific_clamp_pressure_effect", "yes"
        ):
            result.add(
                "overseas_loop.pressure_effect",
                f"{effect_id} must change pressure by {value} and clamp it",
                EFFECT_FILE.as_posix(),
            )

    clamp = effects.get("jxp_76_pacific_clamp_pressure_effect")
    if not _variable_operation(clamp, "set_variable", "0") or not _variable_operation(
        clamp, "set_variable", "100"
    ):
        result.add(
            "overseas_loop.pressure_bounds",
            "pressure clamp no longer enforces both 0 and 100",
            EFFECT_FILE.as_posix(),
        )

    cleanup = effects.get("jxp_76_pacific_network_cleanup_effect")
    if not _positive(cleanup, "clr_country_flag", ACTIVE_FLAG) or not _variable_operation(
        cleanup, "set_variable", "0"
    ):
        result.add(
            "overseas_loop.cleanup_state",
            "cleanup must clear active state and reset pressure",
            EFFECT_FILE.as_posix(),
        )
    for modifier in EXPECTED_MODIFIERS:
        if not _positive(cleanup, "remove_country_modifier", modifier):
            result.add(
                "overseas_loop.cleanup_modifier",
                f"cleanup cannot remove {modifier}",
                EFFECT_FILE.as_posix(),
            )

    start = effects.get("jxp_76_pacific_network_start_effect")
    start_writes = dict(_modifier_writes(start))
    if not all(
        (
            _positive(start, "jxp_76_pacific_network_cleanup_effect", "yes"),
            _positive(start, "set_country_flag", ACTIVE_FLAG),
            _variable_operation(start, "set_variable", "10"),
            start_writes.get("jxp_76_pacific_network_charter") == "3650",
        )
    ):
        result.add(
            "overseas_loop.start_state",
            "entry must clean, activate, initialize pressure 10, and add a finite charter",
            EFFECT_FILE.as_posix(),
        )

    exits = {
        "jxp_76_pacific_compact_effect": ("jxp_76_pacific_compact", "7300"),
        "jxp_76_pacific_stand_down_effect": ("jxp_76_pacific_retrenchment", "3650"),
    }
    closed = 0
    for effect_id, (modifier, duration) in exits.items():
        body = effects.get(effect_id)
        writes = dict(_modifier_writes(body))
        if _positive(body, "jxp_76_pacific_network_cleanup_effect", "yes") and writes.get(
            modifier
        ) == duration:
            closed += 1
        else:
            result.add(
                "overseas_loop.exit_effect",
                f"{effect_id} must clean the loop and add finite {modifier}",
                EFFECT_FILE.as_posix(),
            )

    debug = effects.get("jxp_76_pacific_debug_reset_effect")
    if not _positive(debug, "jxp_76_pacific_network_cleanup_effect", "yes"):
        result.add(
            "overseas_loop.debug_cleanup",
            "debug reset must reuse canonical overseas cleanup",
            EFFECT_FILE.as_posix(),
        )
    return closed


def _check_decisions(document: Document | None, result: CheckResult) -> tuple[int, int]:
    decisions = _decision_bodies(document)
    if set(decisions) != set(EXPECTED_DECISIONS):
        result.add(
            "overseas_loop.decision_inventory",
            "overseas decision inventory differs from the seven-decision contract",
            DECISION_FILE.as_posix(),
        )

    for decision_id, body in decisions.items():
        if _named_object(body, "ai_will_do") is None:
            result.add(
                "overseas_loop.ai_decision",
                f"{decision_id} has no AI policy",
                DECISION_FILE.as_posix(),
            )

    entry = decisions.get("jxp_76_decision_open_pacific_network")
    entry_potential = _named_object(entry, "potential")
    entry_effect = _named_object(entry, "effect")
    if not all(
        (
            _positive(entry_potential, "jxp_76_pacific_network_eligible_trigger", "yes"),
            _positive(entry_potential, "jxp_76_pacific_any_anchor_trigger", "yes"),
            _negative(entry_potential, "has_country_flag", ACTIVE_FLAG),
            _positive(entry_effect, "jxp_76_pacific_network_start_effect", "yes"),
        )
    ):
        result.add(
            "overseas_loop.entry_decision",
            "player entry lost semantic eligibility, anchor, inactive guard, or canonical start",
            DECISION_FILE.as_posix(),
        )

    investments = 0
    for decision_id, (profile, anchor, modifier, pressure_effect) in INVESTMENT_DECISIONS.items():
        body = decisions.get(decision_id)
        potential = _named_object(body, "potential")
        allow = _named_object(body, "allow")
        effect = _named_object(body, "effect")
        writes = dict(_modifier_writes(effect))
        valid = all(
            (
                _positive(potential, "jxp_76_pacific_network_active_trigger", "yes"),
                _positive(potential, profile, "yes"),
                anchor is None or _positive(potential, anchor, "yes"),
                _negative(allow, "has_country_modifier", modifier),
                writes.get(modifier) == "1825",
                _positive(effect, pressure_effect, "yes"),
            )
        )
        if valid:
            investments += 1
        else:
            result.add(
                "overseas_loop.investment_contract",
                f"{decision_id} lost its route/anchor/cooldown/pressure contract",
                DECISION_FILE.as_posix(),
            )

    for decision_id, effect_id in (
        ("jxp_76_decision_proclaim_pacific_compact", "jxp_76_pacific_compact_effect"),
        ("jxp_76_decision_stand_down_pacific_network", "jxp_76_pacific_stand_down_effect"),
    ):
        effect = _named_object(decisions.get(decision_id), "effect")
        if not _positive(effect, effect_id, "yes"):
            result.add(
                "overseas_loop.exit_decision",
                f"{decision_id} no longer calls {effect_id}",
                DECISION_FILE.as_posix(),
            )
    return investments, len(decisions)


def _check_events(document: Document | None, result: CheckResult) -> tuple[int, int]:
    events = _event_bodies(document)
    if set(events) != set(EXPECTED_EVENTS):
        result.add(
            "overseas_loop.event_inventory",
            "overseas event inventory differs from the four-event contract",
            EVENT_FILE.as_posix(),
        )

    expected_options = {"jxp_overseas_loop.1": 4, "jxp_overseas_loop.2": 3, "jxp_overseas_loop.3": 3}
    visible = 0
    ai_weighted = 0
    for event_id, count in expected_options.items():
        event = events.get(event_id)
        trigger = _named_object(event, "trigger")
        options = _options(event)
        if not _positive(trigger, "jxp_76_pacific_network_active_trigger", "yes"):
            result.add(
                "overseas_loop.event_active_gate",
                f"{event_id} can fire outside the active network",
                EVENT_FILE.as_posix(),
            )
        if len(options) != count:
            result.add(
                "overseas_loop.event_options",
                f"{event_id} has {len(options)} options; expected {count}",
                EVENT_FILE.as_posix(),
            )
        visible += len(options)
        for option in options:
            if _named_object(option, "ai_chance") is None:
                result.add(
                    "overseas_loop.ai_event",
                    f"{event_id} has a visible option without AI weight",
                    EVENT_FILE.as_posix(),
                )
            else:
                ai_weighted += 1

    pressure_event = events.get("jxp_overseas_loop.2")
    if not _positive(
        _named_object(pressure_event, "trigger"),
        "jxp_76_pacific_pressure_at_least_50_trigger",
        "yes",
    ):
        result.add(
            "overseas_loop.pressure_event",
            "mid-pressure event lost its 50-pressure gate",
            EVENT_FILE.as_posix(),
        )

    crisis = events.get("jxp_overseas_loop.3")
    crisis_trigger = _named_object(crisis, "trigger")
    crisis_options = _options(crisis)
    if not _positive(
        crisis_trigger, "jxp_76_pacific_pressure_at_least_85_trigger", "yes"
    ) or not all(
        any(_positive(option, effect_id, "yes") for option in crisis_options)
        for effect_id in (
            "jxp_76_pacific_compact_effect",
            "jxp_76_pacific_stand_down_effect",
        )
    ):
        result.add(
            "overseas_loop.crisis_exits",
            "pressure-85 crisis must retain both compact and retrenchment exits",
            EVENT_FILE.as_posix(),
        )

    cleanup = events.get("jxp_overseas_loop.4")
    cleanup_trigger = _named_object(cleanup, "trigger")
    cleanup_mtth = _named_object(cleanup, "mean_time_to_happen")
    cleanup_immediate = _named_object(cleanup, "immediate")
    if not all(
        (
            first_scalar(cleanup, "hidden") == "yes" if cleanup else False,
            _positive(cleanup_trigger, "has_country_flag", ACTIVE_FLAG),
            _negative(
                cleanup_trigger, "jxp_76_pacific_network_active_trigger", "yes"
            ),
            first_scalar(cleanup_mtth, "days") == "1" if cleanup_mtth else False,
            _positive(
                cleanup_immediate, "jxp_76_pacific_network_cleanup_effect", "yes"
            ),
            len(_options(cleanup)) == 1,
        )
    ):
        result.add(
            "overseas_loop.loss_cleanup",
            "hidden one-day cleanup no longer closes route/disaster loss",
            EVENT_FILE.as_posix(),
        )
    return visible, ai_weighted


def _check_modifiers(
    modifier_document: Document | None,
    documents: tuple[Document | None, ...],
    result: CheckResult,
) -> int:
    definitions = _top_objects(modifier_document)
    if set(definitions) != set(EXPECTED_MODIFIERS):
        result.add(
            "overseas_loop.modifier_inventory",
            "overseas modifier inventory differs from the fourteen-modifier contract",
            MODIFIER_FILE.as_posix(),
        )
    writes = [
        write
        for document in documents
        if document is not None
        for write in _modifier_writes(document.root)
    ]
    written_names = {name for name, _duration in writes}
    for name, duration in writes:
        try:
            finite = duration is not None and int(duration) > 0
        except ValueError:
            finite = False
        if name not in EXPECTED_MODIFIERS:
            result.add(
                "overseas_loop.modifier_undefined",
                f"overseas loop writes unexpected modifier {name}",
                MODIFIER_FILE.as_posix(),
            )
        elif not finite:
            result.add(
                "overseas_loop.modifier_duration",
                f"{name} is written with non-finite duration {duration!r}",
                MODIFIER_FILE.as_posix(),
            )
    missing_writes = sorted(set(EXPECTED_MODIFIERS) - written_names)
    if missing_writes:
        result.add(
            "overseas_loop.modifier_unused",
            f"defined overseas modifiers are never added: {missing_writes}",
            MODIFIER_FILE.as_posix(),
        )
    return len(definitions)


def _check_debug(
    decision_document: Document | None,
    root_document: Document | None,
    result: CheckResult,
) -> tuple[int, int]:
    decisions = _decision_bodies(decision_document)
    if set(decisions) != set(EXPECTED_DEBUG_DECISIONS):
        result.add(
            "overseas_loop.debug_inventory",
            "overseas debug inventory differs from the five-decision contract",
            DEBUG_DECISION_FILE.as_posix(),
        )
    for decision_id, body in decisions.items():
        ai = _named_object(body, "ai_will_do")
        if first_scalar(ai, "factor") != "0" if ai else True:
            result.add(
                "overseas_loop.debug_ai",
                f"{decision_id} is not player-only",
                DEBUG_DECISION_FILE.as_posix(),
            )
    reset = _named_object(
        decisions.get("jxp_debug_76_reset_pacific_network"), "effect"
    )
    if not _positive(reset, "jxp_76_pacific_debug_reset_effect", "yes"):
        result.add(
            "overseas_loop.debug_reset",
            "debug reset bypasses canonical Pacific cleanup",
            DEBUG_DECISION_FILE.as_posix(),
        )

    root = _named_object(
        root_document.root if root_document is not None else None,
        "jxp_debug_clear_event_state_effect",
    )
    reachable = int(_positive(root, "jxp_76_pacific_debug_reset_effect", "yes"))
    if not reachable:
        result.add(
            "overseas_loop.debug_root",
            "canonical event-state debug reset cannot reach Pacific cleanup",
            DEBUG_ROOT_FILE.as_posix(),
        )
    return len(decisions), reachable


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
    map_tokens = sorted(set(MAP_TOKEN.findall(text)))
    if map_tokens:
        result.add(
            "overseas_loop.map_contract",
            f"main-only overseas loop directly references companion tokens {map_tokens}",
            TRIGGER_FILE.as_posix(),
        )
    if COMPANION_PROVINCE.search(text):
        result.add(
            "overseas_loop.companion_province",
            "main-only overseas loop hard-references a companion province ID",
            TRIGGER_FILE.as_posix(),
        )
    required_existing = {
        "jxp_pacific_charter_enacted",
        "jxp_manila_nagasaki_route_seen",
        "jxp_alaska_survey_seen",
        "jxp_california_anchorages_seen",
        "colonial_alaska",
        "colonial_california",
        "luzon_area",
    }
    missing = sorted(token for token in required_existing if token not in text)
    if missing:
        result.add(
            "overseas_loop.reuse_contract",
            f"overseas loop no longer reuses existing Pacific anchors {missing}",
            TRIGGER_FILE.as_posix(),
        )
    return int(not map_tokens and not COMPANION_PROVINCE.search(text) and not missing)


def _expected_localisation_keys() -> set[str]:
    keys = {
        key
        for decision_id in (*EXPECTED_DECISIONS, *EXPECTED_DEBUG_DECISIONS)
        for key in (f"{decision_id}_title", f"{decision_id}_desc")
    }
    for event_id, options in (
        ("jxp_overseas_loop.1", "abcd"),
        ("jxp_overseas_loop.2", "abc"),
        ("jxp_overseas_loop.3", "abc"),
    ):
        keys.update({f"{event_id}.t", f"{event_id}.d"})
        keys.update(f"{event_id}.{option}" for option in options)
    keys.update(
        key
        for modifier in EXPECTED_MODIFIERS
        for key in (modifier, f"{modifier}_desc")
    )
    keys.update(TOOLTIPS)
    return keys


def _check_localisation(context: ValidationContext, result: CheckResult) -> int:
    expected = _expected_localisation_keys()
    source_path = context.mod_root / SOURCE_LOC_FILE
    active_path = context.mod_root / ACTIVE_LOC_FILE
    if not source_path.is_file() or not active_path.is_file():
        result.add(
            "overseas_loop.localisation_missing",
            "overseas source or active localisation file is missing",
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
                "overseas_loop.localisation_keys",
                f"{label} localisation misses {missing}",
                relative.as_posix(),
            )
    if not active_bytes.startswith(b"\xef\xbb\xbf") or RAW_CJK.search(active):
        result.add(
            "overseas_loop.localisation_pipeline",
            "active overseas localisation must be BOM-prefixed and EU4SpecialEscape encoded",
            ACTIVE_LOC_FILE.as_posix(),
        )
    return len(expected & source_keys & active_keys)


def check_overseas_loop(context: ValidationContext) -> CheckResult:
    """Return the executable JXP-011 Pacific-network contract."""

    result = CheckResult("Pacific overseas long-term loop")
    trigger_document = _document(context, TRIGGER_FILE, result)
    effect_document = _document(context, EFFECT_FILE, result)
    modifier_document = _document(context, MODIFIER_FILE, result)
    legacy_modifier_document = _document(context, LEGACY_MODIFIER_FILE, result)
    decision_document = _document(context, DECISION_FILE, result)
    debug_decision_document = _document(context, DEBUG_DECISION_FILE, result)
    event_document = _document(context, EVENT_FILE, result)
    debug_root_document = _document(context, DEBUG_ROOT_FILE, result)

    triggers = _check_triggers(trigger_document, result)
    exits = _check_effects(effect_document, result)
    investments, decisions = _check_decisions(decision_document, result)
    visible_options, ai_options = _check_events(event_document, result)
    modifiers = _check_modifiers(
        modifier_document,
        (effect_document, decision_document, event_document),
        result,
    )
    signature_collisions = _check_legacy_modifier_signatures(
        modifier_document, legacy_modifier_document, result
    )
    debug_entries, debug_root = _check_debug(
        debug_decision_document, debug_root_document, result
    )
    compatibility = _check_compatibility(context, result)
    localisation = _check_localisation(context, result)

    result.metrics.update(
        {
            "triggers": triggers,
            "player_decisions": decisions,
            "repeatable_investments": investments,
            "events": len(EXPECTED_EVENTS),
            "visible_event_options": visible_options,
            "ai_weighted_options": ai_options,
            "exit_paths": exits,
            "finite_modifiers": modifiers,
            "legacy_signature_collisions": signature_collisions,
            "debug_entries": debug_entries,
            "debug_root": debug_root,
            "standalone_contract": compatibility,
            "localisation_keys": localisation,
        }
    )
    result.notes.append(
        "The main loop reuses vanilla colonial regions and existing JXP Pacific anchors without companion-only objects."
    )
    result.notes.append(
        "Static proof cannot replace runtime pacing, AI-observer, tooltip, and save/reload checks."
    )
    result.summary = (
        f"{investments}/4 route-divergent investments, {exits}/2 exits, "
        f"{visible_options} event choices, {modifiers}/14 finite modifiers"
    )
    return result
