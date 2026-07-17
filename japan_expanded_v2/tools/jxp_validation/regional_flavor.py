"""Validate JXP-012 semantic regional flavor and companion-map integration.

The contract is deliberately narrow: the main mod owns reusable geography
triggers, events, decisions, rewards, and cleanup; the companion map only
publishes semantic province flags and extends the maritime house mission
column.  Vanilla province/area fallbacks must remain executable without the
companion, and the legacy Settsu/Awaji reward anchors are forbidden here.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
from types import ModuleType
from typing import Mapping

from .clausewitz import (
    ClausewitzParseError,
    Object,
    Scalar,
    bare_scalars,
    find_assignments,
    find_objects,
    first_object,
    first_scalar,
    parse_text,
)
from .core import CheckResult, ValidationContext


TRIGGER_FILE = Path("common/scripted_triggers/jxp_77_regional_flavor_triggers.txt")
EVENT_FILE = Path("events/jxp_77_regional_flavor_events.txt")
DECISION_FILE = Path("decisions/jxp_77_regional_flavor_decisions.txt")
MODIFIER_FILE = Path("common/event_modifiers/jxp_77_regional_flavor_modifiers.txt")
CLEANUP_FILE = Path("common/scripted_effects/jxp_77_regional_flavor_effects.txt")
DEBUG_EFFECT_FILE = Path("common/scripted_effects/jxp_debug_effects.txt")
LEGACY_OVERSEAS_MODIFIER_FILE = Path("common/event_modifiers/jxp_03_event_modifiers.txt")
LEGACY_FOUNDER_MODIFIER_FILE = Path(
    "common/event_modifiers/jxp_52_major_founder_house_policy_modifiers.txt"
)
SOURCE_LOC_FILE = Path(
    "localisation_source/jxp_77_regional_flavor_l_english_utf8_source.yml"
)
ACTIVE_LOC_FILE = Path("localisation/jxp_77_regional_flavor_l_english.yml")

MAP_CONTRACT_FILE = Path("tools/jxp_map_validation/main_compatibility_contract.json")
MAP_EFFECT_FILE = Path("common/scripted_effects/jxp_map_effects.txt")
MAP_MISSION_FILE = Path("missions/jxp_map_new_daimyo_missions.txt")
MAP_SOURCE_LOC_FILE = Path(
    "localisation_source/jxp_map_content_l_english_utf8_source.yml"
)
MAP_ACTIVE_LOC_FILE = Path("localisation/jxp_map_content_l_english.yml")

RECENT_MODIFIER = "jxp_77_regional_council_recent"
OUTCOME_MODIFIERS = (
    "jxp_77_tsushima_interpreter_office",
    "jxp_77_tsushima_coastal_watch",
    "jxp_77_setouchi_pilot_charters",
    "jxp_77_setouchi_toll_compromise",
    "jxp_77_ryukyu_tribute_bureau",
    "jxp_77_ryukyu_free_port",
)
ALL_MODIFIERS = frozenset((RECENT_MODIFIER, *OUTCOME_MODIFIERS))

SCHEDULE_EFFECTS = {
    "jxp_77.1": "jxp_77_schedule_tsushima_channel_council_effect",
    "jxp_77.2": "jxp_77_schedule_setouchi_pilot_circuit_effect",
    "jxp_77.3": "jxp_77_schedule_ryukyu_tribute_gateway_effect",
}

TRIGGER_CONTRACT = {
    "jxp_77_has_tsushima_channel_trigger": (
        "jxp_map_compat_tsushima_channel",
        "owns_or_non_sovereign_subject_of = 4651",
    ),
    "jxp_77_has_setouchi_circuit_trigger": (
        "jxp_map_compat_setouchi",
        "area = saigoku_area",
    ),
    "jxp_77_has_ryukyu_gateway_trigger": (
        "jxp_map_compat_ryukyu_gateway",
        "owns_or_non_sovereign_subject_of = 1015",
    ),
}

EVENT_OUTCOMES = {
    "jxp_77.1": (
        "jxp_77_tsushima_interpreter_office",
        "jxp_77_tsushima_coastal_watch",
    ),
    "jxp_77.2": (
        "jxp_77_setouchi_pilot_charters",
        "jxp_77_setouchi_toll_compromise",
    ),
    "jxp_77.3": (
        "jxp_77_ryukyu_tribute_bureau",
        "jxp_77_ryukyu_free_port",
    ),
}

MISSION_CONTRACT = {
    "jxp_77_mission_tsushima_channel_council": (
        "13",
        "jxp_map_mission_sea_strait_command",
        "jxp_77_has_tsushima_channel_trigger",
        SCHEDULE_EFFECTS["jxp_77.1"],
    ),
    "jxp_77_mission_setouchi_pilot_circuit": (
        "15",
        "jxp_77_mission_tsushima_channel_council",
        "jxp_77_has_setouchi_circuit_trigger",
        SCHEDULE_EFFECTS["jxp_77.2"],
    ),
    "jxp_77_mission_ryukyu_tribute_gateway": (
        "17",
        "jxp_77_mission_setouchi_pilot_circuit",
        "jxp_77_has_ryukyu_gateway_trigger",
        SCHEDULE_EFFECTS["jxp_77.3"],
    ),
}

PLAYER_DECISIONS = {
    "jxp_77_commission_tsushima_channel_council": (
        "jxp_77_has_tsushima_channel_trigger",
        SCHEDULE_EFFECTS["jxp_77.1"],
    ),
    "jxp_77_commission_setouchi_pilot_circuit": (
        "jxp_77_has_setouchi_circuit_trigger",
        SCHEDULE_EFFECTS["jxp_77.2"],
    ),
    "jxp_77_commission_ryukyu_tribute_gateway": (
        "jxp_77_has_ryukyu_gateway_trigger",
        SCHEDULE_EFFECTS["jxp_77.3"],
    ),
}

DEBUG_DECISIONS = {
    "jxp_77_debug_tsushima_channel_council": "jxp_77.1",
    "jxp_77_debug_setouchi_pilot_circuit": "jxp_77.2",
    "jxp_77_debug_ryukyu_tribute_gateway": "jxp_77.3",
}


def _read(root: Path, relative: Path, result: CheckResult) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        result.add(
            "regional_flavor.file_missing",
            f"cannot read {relative.as_posix()}: {exc}",
            relative.as_posix(),
        )
        return ""


def _parse(text: str, label: str, result: CheckResult) -> Object | None:
    try:
        return parse_text(text, Path(f"<{label}>")).root
    except ClausewitzParseError as exc:
        result.add(
            "regional_flavor.parse",
            f"cannot parse {label}: {exc}",
        )
        return None


def _direct_objects(obj: Object | None, key: str) -> tuple[Object, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value
        for entry in obj.entries
        if entry.key == key and isinstance(entry.value, Object)
    )


def _has_assignment(obj: Object | None, key: str, value: str) -> bool:
    return bool(obj is not None and find_assignments(obj, key, value))


def _has_negative_assignment(obj: Object | None, key: str, value: str) -> bool:
    return bool(
        obj is not None
        and any("NOT" in path for path, _entry in find_assignments(obj, key, value))
    )


def _modifier_signatures(text: str, label: str, result: CheckResult) -> dict[str, tuple[tuple[str, str], ...]]:
    root = _parse(text, label, result)
    if root is None:
        return {}
    return {
        entry.key: tuple(
            sorted(
                (member.key, member.value.text)
                for member in entry.value.entries
                if member.key is not None and isinstance(member.value, Scalar)
            )
        )
        for entry in root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }


def _normalise_clause(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_block(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if match is None:
        return None
    start = match.start()
    brace = text.find("{", match.start())
    depth = 0
    quoted = False
    escaped = False
    for index in range(brace, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            continue
        if quoted:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def audit_trigger_contract_text(text: str, result: CheckResult) -> None:
    normalised = _normalise_clause(text)
    for trigger, (semantic_flag, fallback) in TRIGGER_CONTRACT.items():
        block = _extract_block(text, trigger)
        block_normalised = _normalise_clause(block or "")
        if block is None or re.search(
            rf"\bhas_province_flag\s*=\s*{re.escape(semantic_flag)}\b", block_normalised
        ) is None:
            result.add(
                "regional_flavor.trigger_contract",
                f"{trigger} does not consume semantic flag {semantic_flag}",
                TRIGGER_FILE.as_posix(),
            )
        if block is None or _normalise_clause(fallback) not in block_normalised:
            result.add(
                "regional_flavor.fallback_missing",
                f"{trigger} lost standalone fallback {fallback}",
                TRIGGER_FILE.as_posix(),
            )
    if re.search(r"\barea\s*=\s*jxp_[a-z0-9_]+", normalised):
        result.add(
            "regional_flavor.optional_area_dependency",
            "main regional triggers hard-depend on a companion-only area",
            TRIGGER_FILE.as_posix(),
        )


def audit_forbidden_anchor_text(
    texts: Mapping[str, str], result: CheckResult
) -> None:
    for source, text in texts.items():
        anchors = sorted(set(re.findall(r"(?<!\d)(1021|4943)(?!\d)", text)))
        if anchors:
            result.add(
                "regional_flavor.forbidden_anchor",
                f"regional content references forbidden reward anchor(s) {anchors}",
                source,
            )


def audit_schedule_contract_text(text: str, result: CheckResult) -> None:
    root = _parse(text, "regional schedule effects", result)
    if root is None:
        return
    for event_id, schedule_effect in SCHEDULE_EFFECTS.items():
        body = first_object(root, schedule_effect)
        lock = first_object(body, "add_country_modifier")
        dispatch = first_object(body, "country_event")
        direct_keys = [entry.key for entry in body.entries] if body is not None else []
        try:
            lock_index = direct_keys.index("add_country_modifier")
            event_index = direct_keys.index("country_event")
        except ValueError:
            lock_index = event_index = -1
        if not all(
            (
                first_scalar(lock, "name") == RECENT_MODIFIER,
                first_scalar(lock, "duration") == "2",
                first_scalar(dispatch, "id") == event_id,
                first_scalar(dispatch, "days") == "1",
                lock_index >= 0,
                event_index > lock_index,
            )
        ):
            result.add(
                "regional_flavor.schedule_helper",
                f"{schedule_effect} must atomically write the 2-day lock before dispatching {event_id}",
                CLEANUP_FILE.as_posix(),
            )


def audit_regional_modifier_signature_contract(
    modifier_text: str,
    legacy_overseas_text: str,
    legacy_founder_text: str,
    result: CheckResult,
) -> None:
    current = _modifier_signatures(modifier_text, "regional modifiers", result)
    overseas = _modifier_signatures(
        legacy_overseas_text, "legacy overseas modifiers", result
    )
    founder = _modifier_signatures(
        legacy_founder_text, "legacy founder modifiers", result
    )
    comparisons = {
        "jxp_77_tsushima_interpreter_office": (
            (overseas, "jxp_ryukyu_tribute_port"),
            (founder, "jxp_52_soo_wakan_office"),
        ),
        "jxp_77_tsushima_coastal_watch": (
            (founder, "jxp_52_soo_tsushima_sea_wardens"),
        ),
    }
    for current_id, legacy_contracts in comparisons.items():
        signature = current.get(current_id)
        for legacy, legacy_id in legacy_contracts:
            legacy_signature = legacy.get(legacy_id)
            if signature is None or legacy_signature is None:
                result.add(
                    "regional_flavor.signature_inventory",
                    f"cannot compare {current_id} with {legacy_id}",
                    MODIFIER_FILE.as_posix(),
                )
            elif signature == legacy_signature:
                result.add(
                    "regional_flavor.legacy_signature_collision",
                    f"{current_id} mechanically duplicates legacy {legacy_id}",
                    MODIFIER_FILE.as_posix(),
                )


def audit_event_contract_text(text: str, result: CheckResult) -> None:
    root = _parse(text, "regional events", result)
    if root is None:
        return
    events: dict[str, Object] = {}
    duplicates: set[str] = set()
    for event in _direct_objects(root, "country_event"):
        event_id = first_scalar(event, "id")
        if event_id is None:
            continue
        if event_id in events:
            duplicates.add(event_id)
        events[event_id] = event
    if set(events) != set(EVENT_OUTCOMES) or duplicates:
        result.add(
            "regional_flavor.event_inventory",
            f"regional events are {sorted(events)} with duplicates {sorted(duplicates)}; "
            f"expected {sorted(EVENT_OUTCOMES)}",
            EVENT_FILE.as_posix(),
        )

    for event_id, outcomes in EVENT_OUTCOMES.items():
        event = events.get(event_id)
        if event is None:
            continue
        if first_scalar(event, "is_triggered_only") != "yes":
            result.add(
                "regional_flavor.event_dispatch",
                f"{event_id} must be is_triggered_only",
                EVENT_FILE.as_posix(),
            )
        options = _direct_objects(event, "option")
        if len(options) != 2:
            result.add(
                "regional_flavor.option_count",
                f"{event_id} has {len(options)} options; expected 2",
                EVENT_FILE.as_posix(),
            )
        seen_outcomes: set[str] = set()
        for index, option in enumerate(options, start=1):
            direct_keys = [entry.key for entry in option.entries]
            try:
                reset_index = direct_keys.index(
                    "jxp_77_clear_regional_outcomes_effect"
                )
                reward_index = direct_keys.index("add_country_modifier")
            except ValueError:
                reset_index = reward_index = -1
            if not (
                _has_assignment(
                    option, "jxp_77_clear_regional_outcomes_effect", "yes"
                )
                and reset_index >= 0
                and reward_index > reset_index
            ):
                result.add(
                    "regional_flavor.option_outcome_reset",
                    f"{event_id} option {index} must clear all old outcomes before rewards",
                    EVENT_FILE.as_posix(),
                )
            ai = first_object(option, "ai_chance")
            factor = first_scalar(ai, "factor")
            if ai is None or factor in {None, "0"}:
                result.add(
                    "regional_flavor.option_ai",
                    f"{event_id} option {index} lacks a positive ai_chance",
                    EVENT_FILE.as_posix(),
                )
            modifiers: dict[str, str | None] = {}
            for modifier in _direct_objects(option, "add_country_modifier"):
                name = first_scalar(modifier, "name")
                if name is not None:
                    modifiers[name] = first_scalar(modifier, "duration")
            if modifiers.get(RECENT_MODIFIER) != "1825":
                result.add(
                    "regional_flavor.cooldown_duration",
                    f"{event_id} option {index} needs the 1825-day shared cooldown",
                    EVENT_FILE.as_posix(),
                )
            selected = set(modifiers) & set(outcomes)
            if len(selected) != 1:
                result.add(
                    "regional_flavor.outcome_modifier",
                    f"{event_id} option {index} selects {sorted(selected)}; expected one outcome",
                    EVENT_FILE.as_posix(),
                )
            else:
                outcome = next(iter(selected))
                seen_outcomes.add(outcome)
                if modifiers[outcome] != "3650":
                    result.add(
                        "regional_flavor.outcome_duration",
                        f"{event_id} option {index} outcome must last 3650 days",
                        EVENT_FILE.as_posix(),
                    )
            for name, duration in modifiers.items():
                if duration is None or not duration.isdigit() or int(duration) <= 0:
                    result.add(
                        "regional_flavor.finite_duration",
                        f"{event_id} option {index} gives {name} non-finite duration {duration}",
                        EVENT_FILE.as_posix(),
                    )
            keys = {
                entry.key
                for entry in option.entries
                if entry.key is not None
                and isinstance(entry.value, Scalar)
                and entry.value.text == "yes"
            }
            if not any(key.startswith("jxp_add_") for key in keys) or not any(
                key.startswith("jxp_subtract_") for key in keys
            ):
                result.add(
                    "regional_flavor.option_tradeoff",
                    f"{event_id} option {index} lacks an era-attribute gain/cost",
                    EVENT_FILE.as_posix(),
                )
        if seen_outcomes != set(outcomes):
            result.add(
                "regional_flavor.outcome_coverage",
                f"{event_id} outcomes are {sorted(seen_outcomes)}; expected {sorted(outcomes)}",
                EVENT_FILE.as_posix(),
            )
    if re.search(r"\bset_(?:country|province|global)_flag\s*=", text):
        result.add(
            "regional_flavor.persistent_event_state",
            "regional events may not create persistent flags",
            EVENT_FILE.as_posix(),
        )


def audit_decision_contract_text(text: str, result: CheckResult) -> None:
    root = _parse(text, "regional decisions", result)
    decisions = first_object(root, "country_decisions") if root is not None else None
    if decisions is None:
        result.add(
            "regional_flavor.decision_inventory",
            "country_decisions block is missing",
            DECISION_FILE.as_posix(),
        )
        return
    found = {
        entry.key: entry.value
        for entry in decisions.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }
    expected = set(PLAYER_DECISIONS) | set(DEBUG_DECISIONS)
    if set(found) != expected:
        result.add(
            "regional_flavor.decision_inventory",
            f"regional decisions are {sorted(found)}; expected {sorted(expected)}",
            DECISION_FILE.as_posix(),
        )

    for decision_id, (geography_trigger, schedule_effect) in PLAYER_DECISIONS.items():
        body = found.get(decision_id)
        if body is None:
            continue
        potential = first_object(body, "potential")
        allow = first_object(body, "allow")
        effect = first_object(body, "effect")
        ai = first_object(body, "ai_will_do")
        if not _has_assignment(potential, geography_trigger, "yes"):
            result.add(
                "regional_flavor.decision_geography",
                f"{decision_id} does not use {geography_trigger}",
                DECISION_FILE.as_posix(),
            )
        if not _has_negative_assignment(
            allow, "has_country_modifier", RECENT_MODIFIER
        ):
            result.add(
                "regional_flavor.decision_cooldown",
                f"{decision_id} does not gate the shared cooldown",
                DECISION_FILE.as_posix(),
            )
        if not _has_assignment(effect, schedule_effect, "yes") or _direct_objects(
            effect, "country_event"
        ) or _direct_objects(effect, "add_country_modifier"):
            result.add(
                "regional_flavor.decision_schedule_helper",
                f"{decision_id} must dispatch only through {schedule_effect}",
                DECISION_FILE.as_posix(),
            )
        if not _has_assignment(effect, "add_dip_power", "-50") or not _has_assignment(
            effect, "add_treasury", "-75"
        ):
            result.add(
                "regional_flavor.decision_cost",
                f"{decision_id} lost its bounded commission cost",
                DECISION_FILE.as_posix(),
            )
        if first_scalar(ai, "factor") in {None, "0"} or not _direct_objects(
            ai, "modifier"
        ):
            result.add(
                "regional_flavor.decision_ai",
                f"{decision_id} needs positive contextual ai_will_do",
                DECISION_FILE.as_posix(),
            )

    for decision_id, event_id in DEBUG_DECISIONS.items():
        body = found.get(decision_id)
        if body is None:
            continue
        potential = first_object(body, "potential")
        effect = first_object(body, "effect")
        ai = first_object(body, "ai_will_do")
        dispatch = first_object(effect, "country_event")
        if not _has_assignment(potential, "ai", "no") or not _has_assignment(
            potential, "has_country_flag", "jxp_debug_enabled"
        ):
            result.add(
                "regional_flavor.debug_visibility",
                f"{decision_id} is not gated to the player debug menu",
                DECISION_FILE.as_posix(),
            )
        if not _has_assignment(effect, "jxp_77_clear_regional_flavor_effect", "yes"):
            result.add(
                "regional_flavor.debug_prepare",
                f"{decision_id} does not clear regional state before dispatch",
                DECISION_FILE.as_posix(),
            )
        if first_scalar(dispatch, "id") != event_id:
            result.add(
                "regional_flavor.debug_dispatch",
                f"{decision_id} does not dispatch {event_id}",
                DECISION_FILE.as_posix(),
            )
        if first_scalar(ai, "factor") != "0":
            result.add(
                "regional_flavor.debug_ai",
                f"{decision_id} must have ai_will_do factor 0",
                DECISION_FILE.as_posix(),
            )


def audit_cleanup_contract_text(
    cleanup_text: str, debug_text: str, result: CheckResult
) -> None:
    root = _parse(cleanup_text, "regional cleanup", result)
    cleanup = (
        first_object(root, "jxp_77_clear_regional_flavor_effect")
        if root is not None
        else None
    )
    outcome_cleanup = (
        first_object(root, "jxp_77_clear_regional_outcomes_effect")
        if root is not None
        else None
    )
    removed_outcomes = {
        entry.value.text
        for entry in outcome_cleanup.entries
        if outcome_cleanup is not None
        and entry.key == "remove_country_modifier"
        and isinstance(entry.value, Scalar)
    } if outcome_cleanup is not None else set()
    direct_removed = {
        entry.value.text
        for entry in cleanup.entries
        if cleanup is not None
        and entry.key == "remove_country_modifier"
        and isinstance(entry.value, Scalar)
    } if cleanup is not None else set()
    if removed_outcomes != set(OUTCOME_MODIFIERS):
        result.add(
            "regional_flavor.outcome_cleanup_contract",
            f"outcome cleanup removes {sorted(removed_outcomes)}; expected {sorted(OUTCOME_MODIFIERS)}",
            CLEANUP_FILE.as_posix(),
        )
    if direct_removed != {RECENT_MODIFIER} or not _has_assignment(
        cleanup, "jxp_77_clear_regional_outcomes_effect", "yes"
    ):
        result.add(
            "regional_flavor.cleanup_contract",
            "full regional cleanup must remove the cooldown and reuse outcome cleanup",
            CLEANUP_FILE.as_posix(),
        )
    debug_root = _parse(debug_text, "canonical debug cleanup", result)
    canonical = (
        first_object(debug_root, "jxp_debug_clear_event_state_effect")
        if debug_root is not None
        else None
    )
    if not _has_assignment(canonical, "jxp_77_clear_regional_flavor_effect", "yes"):
        result.add(
            "regional_flavor.cleanup_hook",
            "canonical debug cleanup does not call the regional clearer",
            DEBUG_EFFECT_FILE.as_posix(),
        )


def audit_map_contract(
    contract_text: str,
    effect_text: str,
    mission_text: str,
    result: CheckResult,
) -> None:
    try:
        contract = json.loads(contract_text)
    except json.JSONDecodeError as exc:
        result.add(
            "regional_flavor.map_contract_json",
            f"cannot parse companion geography contract: {exc}",
            MAP_CONTRACT_FILE.as_posix(),
        )
        contract = {}
    if contract.get("geography_flags", {}).get("jxp_map_compat_ryukyu_gateway") != [
        "jxp_ryukyu_area"
    ]:
        result.add(
            "regional_flavor.map_area_contract",
            "Ryukyu semantic flag is not mapped exactly to jxp_ryukyu_area",
            MAP_CONTRACT_FILE.as_posix(),
        )
    if contract.get("geography_province_flags", {}).get(
        "jxp_map_compat_tsushima_channel"
    ) != [4651]:
        result.add(
            "regional_flavor.map_province_contract",
            "Tsushima semantic flag is not mapped exactly to province 4651",
            MAP_CONTRACT_FILE.as_posix(),
        )

    root = _parse(effect_text, "companion effects", result)
    initializer = (
        first_object(root, "jxp_map_initialize_geography_contract_effect")
        if root is not None
        else None
    )
    area_mapping: dict[str, set[str]] = {}
    province_mapping: dict[str, set[int]] = {}
    every_provinces = (
        tuple(entry.value for _path, entry in find_objects(initializer, "every_province"))
        if initializer is not None
        else ()
    )
    for every in every_provinces:
        limit = first_object(every, "limit")
        area = first_scalar(limit, "area")
        province_id = first_scalar(limit, "province_id")
        for _path, assignment in find_assignments(every, "set_province_flag"):
            if not isinstance(assignment.value, Scalar):
                continue
            flag = assignment.value.text
            if area is not None:
                area_mapping.setdefault(flag, set()).add(area)
            if province_id is not None and province_id.isdigit():
                province_mapping.setdefault(flag, set()).add(int(province_id))
    if area_mapping.get("jxp_map_compat_ryukyu_gateway") != {"jxp_ryukyu_area"}:
        result.add(
            "regional_flavor.map_area_initializer",
            "geography initializer does not publish the exact Ryukyu semantic area flag",
            MAP_EFFECT_FILE.as_posix(),
        )
    if province_mapping.get("jxp_map_compat_tsushima_channel") != {4651}:
        result.add(
            "regional_flavor.map_province_initializer",
            "geography initializer does not publish the exact Tsushima province flag",
            MAP_EFFECT_FILE.as_posix(),
        )
    for flag in (
        "jxp_map_geography_contract_v011",
        "jxp_map_geography_contract_v012",
        "jxp_map_geography_contract_v013",
    ):
        if not _has_assignment(initializer, "has_global_flag", flag) or not _has_assignment(
            initializer, "set_global_flag", flag
        ):
            result.add(
                "regional_flavor.map_geography_migration",
                f"geography initializer does not read and set {flag}",
                MAP_EFFECT_FILE.as_posix(),
            )

    initialize = first_object(root, "jxp_map_initialize_effect") if root is not None else None
    direct_keys = [entry.key for entry in initialize.entries] if initialize is not None else []
    try:
        regional_index = direct_keys.index("jxp_map_migrate_regional_flavor_v013_effect")
        identity_index = direct_keys.index("jxp_map_migrate_identity_v012_effect")
    except ValueError:
        regional_index = identity_index = -1
    migration = (
        first_object(root, "jxp_map_migrate_regional_flavor_v013_effect")
        if root is not None
        else None
    )
    debug_reset = (
        first_object(root, "jxp_map_debug_full_reset_effect")
        if root is not None
        else None
    )
    migration_ok = (
        regional_index >= 0
        and identity_index >= 0
        and regional_index < identity_index
        and _has_assignment(
            migration, "has_country_flag", "jxp_map_regional_flavor_migration_v013"
        )
        and _has_assignment(
            migration, "set_country_flag", "jxp_map_regional_flavor_migration_v013"
        )
        and _has_assignment(migration, "jxp_refresh_route_missions_effect", "yes")
        and _has_assignment(
            debug_reset, "clr_country_flag", "jxp_map_regional_flavor_migration_v013"
        )
    )
    if not migration_ok:
        result.add(
            "regional_flavor.map_mission_migration",
            "companion v013 mission refresh/read/write/debug-clear contract is incomplete",
            MAP_EFFECT_FILE.as_posix(),
        )

    mission_root = _parse(mission_text, "companion regional missions", result)
    series = (
        first_object(mission_root, "jxp_map_sea_house_missions")
        if mission_root is not None
        else None
    )
    for mission_id, (
        position,
        dependency,
        trigger,
        schedule_effect,
    ) in MISSION_CONTRACT.items():
        mission = first_object(series, mission_id)
        if mission is None:
            result.add(
                "regional_flavor.map_mission_missing",
                f"{mission_id} is missing from jxp_map_sea_house_missions",
                MAP_MISSION_FILE.as_posix(),
            )
            continue
        required = bare_scalars(first_object(mission, "required_missions"))
        required_ids = {scalar.text for scalar in required}
        trigger_body = first_object(mission, "trigger")
        effect = first_object(mission, "effect")
        if (
            first_scalar(mission, "position") != position
            or required_ids != {dependency}
            or not _has_assignment(trigger_body, trigger, "yes")
            or not _has_negative_assignment(
                trigger_body, "has_country_modifier", RECENT_MODIFIER
            )
            or not _has_assignment(effect, schedule_effect, "yes")
            or bool(_direct_objects(effect, "country_event"))
            or bool(_direct_objects(effect, "add_country_modifier"))
        ):
            result.add(
                "regional_flavor.map_mission_contract",
                f"{mission_id} position/dependency/geography/cooldown/schedule contract is incomplete",
                MAP_MISSION_FILE.as_posix(),
            )


def _localisation_keys(text: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*([A-Za-z0-9_.]+):\d+\s+", text))


def _load_escape_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_jxp_77_escape", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit_localisation_pair(
    repo_root: Path,
    root: Path,
    source_relative: Path,
    active_relative: Path,
    required: set[str],
    result: CheckResult,
) -> None:
    source = _read(root, source_relative, result)
    active = _read(root, active_relative, result)
    for label, text in (("source", source), ("active", active)):
        missing = required - _localisation_keys(text)
        if missing:
            result.add(
                "regional_flavor.localisation_keys",
                f"{label} localisation misses {sorted(missing)}",
                (source_relative if label == "source" else active_relative).as_posix(),
            )
    try:
        escape = _load_escape_module(
            repo_root
            / "skills"
            / "eu4-modding"
            / "scripts"
            / "escape_eu4_special_localisation.py"
        ).escape_text
        expected = escape(source).encode("utf-8-sig")
        actual = (root / active_relative).read_bytes()
        if actual != expected:
            result.add(
                "regional_flavor.localisation_escape",
                "active localisation is not the exact canonical escaped source",
                active_relative.as_posix(),
            )
    except (OSError, ImportError, AttributeError) as exc:
        result.add(
            "regional_flavor.localisation_escape",
            f"cannot verify canonical localisation escape: {exc}",
            active_relative.as_posix(),
        )


def check_regional_flavor(
    context: ValidationContext,
    companion_context: ValidationContext | None = None,
) -> CheckResult:
    result = CheckResult("Semantic regional flavor")
    main_root = context.mod_root
    companion_context = companion_context or (
        ValidationContext(main_root.parent / "japan_expanded_v2_map")
        if (main_root.parent / "japan_expanded_v2_map").is_dir()
        else None
    )
    if companion_context is None:
        result.add(
            "regional_flavor.companion_missing",
            "japan_expanded_v2_map sibling is required for the regional integration audit",
        )
        result.summary = "companion map missing"
        return result
    map_root = companion_context.mod_root

    trigger_text = _read(main_root, TRIGGER_FILE, result)
    event_text = _read(main_root, EVENT_FILE, result)
    decision_text = _read(main_root, DECISION_FILE, result)
    modifier_text = _read(main_root, MODIFIER_FILE, result)
    cleanup_text = _read(main_root, CLEANUP_FILE, result)
    debug_text = _read(main_root, DEBUG_EFFECT_FILE, result)
    legacy_overseas_modifier_text = _read(
        main_root, LEGACY_OVERSEAS_MODIFIER_FILE, result
    )
    legacy_founder_modifier_text = _read(
        main_root, LEGACY_FOUNDER_MODIFIER_FILE, result
    )
    map_contract_text = _read(map_root, MAP_CONTRACT_FILE, result)
    map_effect_text = _read(map_root, MAP_EFFECT_FILE, result)
    map_mission_text = _read(map_root, MAP_MISSION_FILE, result)

    audit_trigger_contract_text(trigger_text, result)
    audit_event_contract_text(event_text, result)
    audit_decision_contract_text(decision_text, result)
    audit_schedule_contract_text(cleanup_text, result)
    audit_cleanup_contract_text(cleanup_text, debug_text, result)
    audit_regional_modifier_signature_contract(
        modifier_text,
        legacy_overseas_modifier_text,
        legacy_founder_modifier_text,
        result,
    )
    audit_map_contract(map_contract_text, map_effect_text, map_mission_text, result)

    modifier_root = _parse(modifier_text, "regional modifiers", result)
    modifier_ids = {
        entry.key
        for entry in modifier_root.entries
        if modifier_root is not None
        and entry.key is not None
        and isinstance(entry.value, Object)
    } if modifier_root is not None else set()
    if modifier_ids != ALL_MODIFIERS:
        result.add(
            "regional_flavor.modifier_inventory",
            f"regional modifiers are {sorted(modifier_ids)}; expected {sorted(ALL_MODIFIERS)}",
            MODIFIER_FILE.as_posix(),
        )

    if re.search(
        r"\bset_(?:country|province|global)_flag\s*=",
        "\n".join((trigger_text, event_text, decision_text, modifier_text, cleanup_text)),
    ):
        result.add(
            "regional_flavor.persistent_main_state",
            "jxp_77 main content creates a persistent flag",
        )

    audit_forbidden_anchor_text(
        {
            TRIGGER_FILE.as_posix(): trigger_text,
            EVENT_FILE.as_posix(): event_text,
            DECISION_FILE.as_posix(): decision_text,
            MODIFIER_FILE.as_posix(): modifier_text,
            CLEANUP_FILE.as_posix(): cleanup_text,
            MAP_MISSION_FILE.as_posix(): map_mission_text,
        },
        result,
    )

    main_loc_keys = {
        *(f"{decision}_title" for decision in PLAYER_DECISIONS),
        *(f"{decision}_desc" for decision in PLAYER_DECISIONS),
        *(f"{decision}_title" for decision in DEBUG_DECISIONS),
        *(f"{decision}_desc" for decision in DEBUG_DECISIONS),
        *ALL_MODIFIERS,
    }
    for event_id in EVENT_OUTCOMES:
        main_loc_keys.update(
            {f"{event_id}.t", f"{event_id}.d", f"{event_id}.a", f"{event_id}.b"}
        )
    map_loc_keys = {
        *(f"{mission}_title" for mission in MISSION_CONTRACT),
        *(f"{mission}_desc" for mission in MISSION_CONTRACT),
    }
    repo_root = main_root.parent
    _audit_localisation_pair(
        repo_root,
        main_root,
        SOURCE_LOC_FILE,
        ACTIVE_LOC_FILE,
        main_loc_keys,
        result,
    )
    _audit_localisation_pair(
        repo_root,
        map_root,
        MAP_SOURCE_LOC_FILE,
        MAP_ACTIVE_LOC_FILE,
        map_loc_keys,
        result,
    )

    result.metrics.update(
        {
            "semantic_gates": len(TRIGGER_CONTRACT),
            "regional_events": len(EVENT_OUTCOMES),
            "choice_options": len(EVENT_OUTCOMES) * 2,
            "regional_missions": len(MISSION_CONTRACT),
            "player_decisions": len(PLAYER_DECISIONS),
            "debug_decisions": len(DEBUG_DECISIONS),
            "finite_modifiers": len(ALL_MODIFIERS),
            "schedule_helpers": len(SCHEDULE_EFFECTS),
            "legacy_signature_collisions": 0,
        }
    )
    result.summary = (
        "3 semantic geography gates, 3 companion missions, 3 two-choice events, "
        "3 AI commissions, and canonical debug cleanup"
    )
    return result
