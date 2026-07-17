"""Audit JXP runtime state lifecycles and disaster safety contracts.

This module is intentionally independent from ``run_validation.py`` so a
backlog audit can expose real gaps before the release gate is made stricter.
It scans the maintained main/companion release surface together, follows the
canonical debug-cleanup effect graph, and returns hard failures for orphaned
flags, dangling reads, uncleaned dynamic modifiers, and incomplete disasters.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import DefaultDict, Iterable

from .clausewitz import (
    Entry,
    Object,
    Scalar,
    find_assignments,
    find_objects,
    first_entry,
    first_object,
    first_scalar,
    walk_entries,
)
from .core import CheckResult, ValidationContext


FLAG_KINDS = ("country_flag", "province_flag", "global_flag")
MODIFIER_KINDS = ("country_modifier", "province_modifier")
STATE_KINDS = FLAG_KINDS + MODIFIER_KINDS

# Engine-rejected aliases observed against the pinned 1.37.5 executable. The
# replacements below are all used by pinned vanilla event modifiers or ideas.
INVALID_EVENT_MODIFIER_KEYS = {
    "goods_produced_modifier": "global_trade_goods_size_modifier",
    "global_trade_power_modifier": "global_trade_power",
    "ship_cost": "global_ship_cost",
    "local_trade_power": "province_trade_power_modifier",
}

FLAG_WRITE_KEYS = {
    "set_country_flag": "country_flag",
    "set_province_flag": "province_flag",
    "set_global_flag": "global_flag",
}
FLAG_READ_KEYS = {
    "has_country_flag": "country_flag",
    "had_country_flag": "country_flag",
    "has_province_flag": "province_flag",
    "had_province_flag": "province_flag",
    "has_global_flag": "global_flag",
    "had_global_flag": "global_flag",
}
FLAG_CLEAR_KEYS = {
    "clr_country_flag": "country_flag",
    "clr_province_flag": "province_flag",
    "clr_global_flag": "global_flag",
}
MODIFIER_ADD_KEYS = {
    "add_country_modifier": "country_modifier",
    "add_permanent_country_modifier": "country_modifier",
    "add_province_modifier": "province_modifier",
    "add_permanent_province_modifier": "province_modifier",
}
MODIFIER_READ_KEYS = {
    "has_country_modifier": "country_modifier",
    "has_province_modifier": "province_modifier",
}
MODIFIER_CLEAR_KEYS = {
    "remove_country_modifier": "country_modifier",
    "remove_province_modifier": "province_modifier",
}

MAIN_DEBUG_ROOTS = (
    "jxp_debug_clear_event_state_effect",
    "jxp_debug_clear_cooldowns_effect",
    "jxp_debug_clear_route_state_effect",
)
MAP_DEBUG_ROOTS = ("jxp_map_debug_full_reset_effect",)

# These flags are the companion's persistent semantic geography substrate.
# Clearing them during a country reset would break the parent/companion area
# bridge while the global one-time initializer remained set.  Every other
# created JXP state must have an executable cleanup path.
PERSISTENT_CLEANUP_EXEMPTIONS = {
    ("global_flag", "jxp_map_geography_contract_v011"),
    ("global_flag", "jxp_map_geography_contract_v012"),
    ("global_flag", "jxp_map_geography_contract_v013"),
    ("province_flag", "jxp_map_compat_ikko_heartland"),
    ("province_flag", "jxp_map_compat_ikko_formable_heartland"),
    ("province_flag", "jxp_map_compat_ryukyu_gateway"),
    ("province_flag", "jxp_map_compat_setouchi"),
    ("province_flag", "jxp_map_compat_shimabara_belt"),
    ("province_flag", "jxp_map_compat_tsushima_channel"),
    ("province_flag", "jxp_map_compat_wokou_waters"),
}


@dataclass(frozen=True, slots=True)
class Requirement:
    key: str
    value: str
    negative: bool = False


@dataclass(frozen=True, slots=True)
class DisasterContract:
    resolved_flag: str
    active_flag: str
    debug_token: str
    settlement_decision: str
    potential: tuple[Requirement, ...]
    can_start: tuple[Requirement, ...]


COMMON_DISASTER_POTENTIAL = (
    Requirement("normal_or_historical_nations", "yes"),
    Requirement("jxp_is_japanese_polity_trigger", "yes"),
    Requirement("is_free_or_tributary_trigger", "yes"),
)

# Known disasters get exact false-positive contracts.  A new disaster is a
# hard failure until it is deliberately added here with its identity, route,
# chronology, geography, and debug expectations.
DISASTER_CONTRACTS = {
    "jxp_shimabara_fire": DisasterContract(
        resolved_flag="jxp_shimabara_resolved",
        active_flag="jxp_shimabara_crisis_active",
        debug_token="shimabara",
        settlement_decision="jxp_decision_settle_shimabara_fire",
        potential=COMMON_DISASTER_POTENTIAL
        + (
            Requirement("has_country_flag", "jxp_shimabara_resolved", True),
            Requirement("has_country_flag", "jxp_path_kirishitan", True),
            Requirement("has_country_flag", "jxp_path_reformed", True),
            Requirement("tag", "KJP", True),
            Requirement("tag", "RFJ", True),
        ),
        can_start=(
            Requirement("has_any_disaster", "no"),
            Requirement("is_year", "1620"),
            Requirement("has_province_flag", "jxp_map_compat_shimabara_belt"),
        ),
    ),
    "jxp_ikko_rising": DisasterContract(
        resolved_flag="jxp_ikko_rising_resolved",
        active_flag="jxp_ikko_rising_active",
        debug_token="ikko",
        settlement_decision="jxp_decision_settle_ikko_rising",
        potential=(
            Requirement("normal_or_historical_nations", "yes"),
            Requirement("jxp_a_shinshu_crisis_scope_trigger", "yes"),
            Requirement("is_free_or_tributary_trigger", "yes"),
            Requirement("has_country_flag", "jxp_ikko_rising_resolved", True),
            Requirement("jxp_a_ijp_has_terminal_settlement_trigger", "yes", True),
        ),
        can_start=(
            Requirement("has_any_disaster", "no"),
            Requirement("is_year", "1460"),
            Requirement("num_of_cities", "8"),
            Requirement("jxp_tenka_order_at_least_50", "yes", True),
        ),
    ),
    "jxp_keian_ronin_crisis": DisasterContract(
        resolved_flag="jxp_keian_ronin_crisis_resolved",
        active_flag="jxp_keian_ronin_crisis_active",
        debug_token="keian",
        settlement_decision="jxp_decision_resolve_keian_ronin_crisis",
        potential=COMMON_DISASTER_POTENTIAL
        + (
            Requirement("jxp_is_unified_japan_state_trigger", "yes"),
            Requirement("government", "monarchy"),
            Requirement(
                "has_country_flag", "jxp_keian_ronin_crisis_resolved", True
            ),
            Requirement("tag", "IJP", True),
            Requirement("tag", "WAK", True),
        ),
        can_start=(
            Requirement("has_any_disaster", "no"),
            Requirement("is_year", "1651"),
            Requirement("num_of_cities", "20"),
            Requirement("owns", "1028"),
            Requirement("stability", "1", True),
            Requirement("war_exhaustion", "3"),
            Requirement("num_of_loans", "2"),
            Requirement("manpower_percentage", "0.50", True),
        ),
    ),
    "jxp_tenmei_famine": DisasterContract(
        resolved_flag="jxp_tenmei_famine_resolved",
        active_flag="jxp_tenmei_famine_active",
        debug_token="tenmei",
        settlement_decision="jxp_decision_resolve_tenmei_famine",
        potential=COMMON_DISASTER_POTENTIAL
        + (
            Requirement("jxp_is_unified_japan_state_trigger", "yes"),
            Requirement("has_country_flag", "jxp_tenmei_famine_resolved", True),
        ),
        can_start=(
            Requirement("has_any_disaster", "no"),
            Requirement("is_year", "1783"),
            Requirement("num_of_cities", "20"),
            Requirement("total_development", "250"),
            Requirement("owns", "1028"),
            Requirement("stability", "1", True),
            Requirement("war_exhaustion", "3"),
            Requirement("num_of_loans", "3"),
            Requirement("manpower_percentage", "0.60", True),
        ),
    ),
}

PRESSURE_KEYS = {
    "stability",
    "war_exhaustion",
    "religious_unity",
    "global_unrest",
    "legitimacy",
    "republican_tradition",
    "devotion",
    "horde_unity",
    "mandate",
    "corruption",
    "num_of_loans",
    "overextension_percentage",
    "manpower_percentage",
}
CHRONOLOGY_KEYS = {"is_year", "year"}
EXPOSURE_KEYS = {
    "owns",
    "owns_or_non_sovereign_subject_of",
    "has_country_flag",
    "has_country_modifier",
    "religion",
    "dominant_religion",
    "any_owned_province",
    "jxp_ikko_historical_heartland_trigger",
}

SWORD_HUNT_FILE = Path("decisions/jxp_polity_decisions.txt")
SWORD_HUNT_DECISION = "jxp_decision_issue_sword_hunt"
SWORD_HUNT_POTENTIAL_CONTRACT = (
    Requirement("jxp_is_japanese_polity_trigger", "yes"),
    Requirement("is_subject_of_type", "daimyo_vassal", True),
    Requirement("has_country_modifier", "subject_sword_hunt", True),
    Requirement("has_country_modifier", "overlord_sword_hunt", True),
)


@dataclass(frozen=True, slots=True)
class Occurrence:
    surface: str
    source: str
    line: int


def _usage_map() -> DefaultDict[str, DefaultDict[str, list[Occurrence]]]:
    return defaultdict(lambda: defaultdict(list))


@dataclass(slots=True)
class Inventory:
    writes: DefaultDict[str, DefaultDict[str, list[Occurrence]]] = field(
        default_factory=_usage_map
    )
    content_writes: DefaultDict[str, DefaultDict[str, list[Occurrence]]] = field(
        default_factory=_usage_map
    )
    persistent_content_writes: DefaultDict[
        str, DefaultDict[str, list[Occurrence]]
    ] = field(default_factory=_usage_map)
    reads: DefaultDict[str, DefaultDict[str, list[Occurrence]]] = field(
        default_factory=_usage_map
    )
    clears: DefaultDict[str, DefaultDict[str, list[Occurrence]]] = field(
        default_factory=_usage_map
    )
    modifier_definitions: DefaultDict[str, list[Occurrence]] = field(
        default_factory=lambda: defaultdict(list)
    )


@dataclass(frozen=True, slots=True)
class Surface:
    label: str
    context: ValidationContext
    debug_roots: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EventRecord:
    event_id: str
    body: Object
    occurrence: Occurrence


@dataclass(frozen=True, slots=True)
class DisasterRecord:
    key: str
    body: Object
    occurrence: Occurrence


def _display_source(surface: Surface, source: Path) -> str:
    return f"{surface.label}/{surface.context.relative(source)}"


def _occurrence(surface: Surface, source: Path, line: int) -> Occurrence:
    return Occurrence(surface.label, _display_source(surface, source), line)


def _is_debug_source(context: ValidationContext, source: Path) -> bool:
    relative = Path(context.relative(source))
    return "debug" in relative.stem.casefold()


def _scalar_jxp(entry: Entry) -> str | None:
    if isinstance(entry.value, Scalar) and entry.value.text.startswith("jxp_"):
        return entry.value.text
    return None


def _modifier_name(entry: Entry) -> str | None:
    if isinstance(entry.value, Scalar):
        name = entry.value.text
    elif isinstance(entry.value, Object):
        name = first_scalar(entry.value, "name")
    else:  # pragma: no cover - Clausewitz values are exhaustive.
        name = None
    return name if name is not None and name.startswith("jxp_") else None


def _modifier_write_is_persistent(entry: Entry) -> bool:
    if entry.key is not None and entry.key.startswith("add_permanent_"):
        return True
    if isinstance(entry.value, Scalar):
        return True
    if not isinstance(entry.value, Object):
        return True
    duration = first_scalar(entry.value, "duration")
    return duration is None or duration == "-1"


def _record(
    target: DefaultDict[str, DefaultDict[str, list[Occurrence]]],
    kind: str,
    name: str,
    occurrence: Occurrence,
) -> None:
    target[kind][name].append(occurrence)


def _scan_inventory(surfaces: Iterable[Surface]) -> Inventory:
    inventory = Inventory()
    for surface in surfaces:
        for source in surface.context.script_files():
            document = surface.context.document(source)
            if document is None:
                continue
            is_debug = _is_debug_source(surface.context, source)
            for _path, entry in walk_entries(document.root):
                occurrence = _occurrence(surface, source, entry.line)
                scalar = _scalar_jxp(entry)
                if scalar is not None and entry.key in FLAG_WRITE_KEYS:
                    kind = FLAG_WRITE_KEYS[entry.key]
                    _record(inventory.writes, kind, scalar, occurrence)
                    if not is_debug:
                        _record(inventory.content_writes, kind, scalar, occurrence)
                        _record(
                            inventory.persistent_content_writes,
                            kind,
                            scalar,
                            occurrence,
                        )
                elif scalar is not None and entry.key in FLAG_READ_KEYS:
                    _record(inventory.reads, FLAG_READ_KEYS[entry.key], scalar, occurrence)
                elif scalar is not None and entry.key in FLAG_CLEAR_KEYS:
                    _record(inventory.clears, FLAG_CLEAR_KEYS[entry.key], scalar, occurrence)
                elif entry.key in MODIFIER_ADD_KEYS:
                    name = _modifier_name(entry)
                    if name is not None:
                        kind = MODIFIER_ADD_KEYS[entry.key]
                        _record(inventory.writes, kind, name, occurrence)
                        if not is_debug:
                            _record(inventory.content_writes, kind, name, occurrence)
                            if _modifier_write_is_persistent(entry):
                                _record(
                                    inventory.persistent_content_writes,
                                    kind,
                                    name,
                                    occurrence,
                                )
                elif scalar is not None and entry.key in MODIFIER_READ_KEYS:
                    _record(
                        inventory.reads,
                        MODIFIER_READ_KEYS[entry.key],
                        scalar,
                        occurrence,
                    )
                elif scalar is not None and entry.key in MODIFIER_CLEAR_KEYS:
                    _record(
                        inventory.clears,
                        MODIFIER_CLEAR_KEYS[entry.key],
                        scalar,
                        occurrence,
                    )

        modifier_root = surface.context.mod_root / "common" / "event_modifiers"
        if modifier_root.is_dir():
            for source in sorted(modifier_root.rglob("*.txt")):
                document = surface.context.document(source)
                if document is None:
                    continue
                for entry in document.root.entries:
                    if (
                        entry.key is not None
                        and entry.key.startswith("jxp_")
                        and isinstance(entry.value, Object)
                    ):
                        inventory.modifier_definitions[entry.key].append(
                            _occurrence(surface, source, entry.line)
                        )
    return inventory


def _effect_definitions(surface: Surface) -> dict[str, Object]:
    definitions: dict[str, Object] = {}
    root = surface.context.mod_root / "common" / "scripted_effects"
    if not root.is_dir():
        return definitions
    for source in sorted(root.rglob("*.txt")):
        document = surface.context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if (
                entry.key is not None
                and entry.key.startswith("jxp_")
                and isinstance(entry.value, Object)
            ):
                definitions[entry.key] = entry.value
    return definitions


def _cleanup_in_object(obj: Object) -> DefaultDict[str, set[str]]:
    cleanup: DefaultDict[str, set[str]] = defaultdict(set)
    for _path, entry in walk_entries(obj):
        scalar = _scalar_jxp(entry)
        if scalar is not None and entry.key in FLAG_CLEAR_KEYS:
            cleanup[FLAG_CLEAR_KEYS[entry.key]].add(scalar)
        elif scalar is not None and entry.key in MODIFIER_CLEAR_KEYS:
            cleanup[MODIFIER_CLEAR_KEYS[entry.key]].add(scalar)
    return cleanup


def _debug_cleanup_closure(
    surface: Surface,
    result: CheckResult,
) -> DefaultDict[str, set[str]]:
    definitions = _effect_definitions(surface)
    cleanup: DefaultDict[str, set[str]] = defaultdict(set)
    seen: set[str] = set()
    stack = list(surface.debug_roots)
    for root in surface.debug_roots:
        if root not in definitions:
            result.add(
                "state.debug_root_missing",
                f"{surface.label} debug cleanup root {root} is not defined",
            )

    while stack:
        effect = stack.pop()
        if effect in seen:
            continue
        seen.add(effect)
        body = definitions.get(effect)
        if body is None:
            continue
        for kind, names in _cleanup_in_object(body).items():
            cleanup[kind].update(names)
        for _path, entry in walk_entries(body):
            if (
                entry.key in definitions
                and isinstance(entry.value, Scalar)
                and entry.value.text == "yes"
            ):
                stack.append(entry.key)
    result.metrics[f"{surface.label}_debug_effects_reachable"] = len(seen)
    return cleanup


def _first_occurrence(occurrences: list[Occurrence]) -> Occurrence:
    return sorted(occurrences, key=lambda item: (item.source.casefold(), item.line))[0]


def _add_occurrence_issue(
    result: CheckResult,
    code: str,
    message: str,
    occurrences: list[Occurrence],
) -> None:
    occurrence = _first_occurrence(occurrences)
    result.add(code, message, occurrence.source, occurrence.line)


def _check_state_inventory(
    inventory: Inventory,
    surfaces: tuple[Surface, ...],
    debug_cleanup: dict[str, DefaultDict[str, set[str]]],
    result: CheckResult,
) -> None:
    orphan_writes = 0
    dangling_reads = 0
    lifecycle_missing = 0
    debug_missing = 0
    lifecycle_missing_by_kind: DefaultDict[str, int] = defaultdict(int)
    debug_missing_by_kind: DefaultDict[str, int] = defaultdict(int)

    for kind in FLAG_KINDS:
        written = set(inventory.writes[kind])
        read = set(inventory.reads[kind])
        for name in sorted(written - read):
            orphan_writes += 1
            _add_occurrence_issue(
                result,
                "state.flag_orphan_write",
                f"{kind} {name} is created but never read on the combined release surface",
                inventory.writes[kind][name],
            )
        for name in sorted(read - written):
            dangling_reads += 1
            _add_occurrence_issue(
                result,
                "state.flag_dangling_read",
                f"{kind} {name} is read but never created on the combined release surface",
                inventory.reads[kind][name],
            )

    for kind in STATE_KINDS:
        lifecycle_writes = (
            inventory.content_writes[kind]
            if kind in FLAG_KINDS
            else inventory.persistent_content_writes[kind]
        )
        for name, occurrences in sorted(lifecycle_writes.items()):
            if (kind, name) in PERSISTENT_CLEANUP_EXEMPTIONS:
                continue
            if name not in inventory.clears[kind]:
                lifecycle_missing += 1
                lifecycle_missing_by_kind[kind] += 1
                _add_occurrence_issue(
                    result,
                    "state.lifecycle_cleanup_missing",
                    f"{kind} {name} is created by gameplay but has no clear/remove path",
                    occurrences,
                )

        for name, occurrences in sorted(inventory.content_writes[kind].items()):
            if (kind, name) in PERSISTENT_CLEANUP_EXEMPTIONS:
                continue
            for surface_label in sorted({item.surface for item in occurrences}):
                if name in debug_cleanup.get(surface_label, {}).get(kind, set()):
                    continue
                debug_missing += 1
                debug_missing_by_kind[kind] += 1
                surface_occurrences = [
                    item for item in occurrences if item.surface == surface_label
                ]
                _add_occurrence_issue(
                    result,
                    "state.debug_cleanup_missing",
                    f"{surface_label} debug reset cannot clear {kind} {name}",
                    surface_occurrences,
                )

    definitions = inventory.modifier_definitions
    added_modifiers = set(inventory.writes["country_modifier"]) | set(
        inventory.writes["province_modifier"]
    )
    read_modifiers = set(inventory.reads["country_modifier"]) | set(
        inventory.reads["province_modifier"]
    )
    cleared_modifiers = set(inventory.clears["country_modifier"]) | set(
        inventory.clears["province_modifier"]
    )

    for name, occurrences in sorted(definitions.items()):
        if len(occurrences) != 1:
            _add_occurrence_issue(
                result,
                "modifier.definition_duplicate",
                f"modifier {name} has {len(occurrences)} definitions; expected exactly one",
                occurrences,
            )
        if name not in added_modifiers and name not in read_modifiers:
            _add_occurrence_issue(
                result,
                "modifier.definition_orphan",
                f"modifier {name} is defined but never added or read",
                occurrences,
            )

    for name in sorted(added_modifiers - set(definitions)):
        occurrences = inventory.writes["country_modifier"].get(name, []) + inventory.writes[
            "province_modifier"
        ].get(name, [])
        _add_occurrence_issue(
            result,
            "modifier.undefined_add",
            f"dynamic modifier {name} is added but has no event-modifier definition",
            occurrences,
        )
    for name in sorted(read_modifiers - set(definitions)):
        occurrences = inventory.reads["country_modifier"].get(name, []) + inventory.reads[
            "province_modifier"
        ].get(name, [])
        _add_occurrence_issue(
            result,
            "modifier.undefined_read",
            f"dynamic modifier {name} is read but has no event-modifier definition",
            occurrences,
        )
    for name in sorted(cleared_modifiers - set(definitions)):
        occurrences = inventory.clears["country_modifier"].get(name, []) + inventory.clears[
            "province_modifier"
        ].get(name, [])
        _add_occurrence_issue(
            result,
            "modifier.undefined_cleanup",
            f"dynamic modifier {name} is removed but has no event-modifier definition",
            occurrences,
        )

    for kind in STATE_KINDS:
        result.metrics[f"{kind}_created"] = len(inventory.writes[kind])
        result.metrics[f"{kind}_read"] = len(inventory.reads[kind])
        result.metrics[f"{kind}_cleared"] = len(inventory.clears[kind])
    result.metrics.update(
        {
            "flag_orphan_writes": orphan_writes,
            "flag_dangling_reads": dangling_reads,
            "lifecycle_cleanup_missing": lifecycle_missing,
            "debug_cleanup_missing": debug_missing,
            "modifier_definitions": len(definitions),
        }
    )
    for kind in STATE_KINDS:
        result.metrics[f"{kind}_lifecycle_cleanup_missing"] = (
            lifecycle_missing_by_kind[kind]
        )
        result.metrics[f"{kind}_debug_cleanup_missing"] = debug_missing_by_kind[kind]
        result.metrics[f"{kind}_persistent_created"] = len(
            inventory.persistent_content_writes[kind]
        )


def _negative_path(path: tuple[str, ...]) -> bool:
    return sum(component in {"NOT", "NOR", "NAND"} for component in path) % 2 == 1


def _has_requirement(obj: Object | None, requirement: Requirement) -> bool:
    if obj is None:
        return False
    return any(
        _negative_path(path) == requirement.negative
        for path, _entry in find_assignments(obj, requirement.key, requirement.value)
    )


def _has_positive(obj: Object | None, key: str, value: str) -> bool:
    return _has_requirement(obj, Requirement(key, value))


def _check_sword_hunt_gate(surface: Surface, result: CheckResult) -> None:
    source = surface.context.mod_root / SWORD_HUNT_FILE
    document = surface.context.document(source) if source.is_file() else None
    country_decisions = (
        first_object(document.root, "country_decisions")
        if document is not None
        else None
    )
    definitions = (
        tuple(
            entry
            for entry in country_decisions.entries
            if entry.key == SWORD_HUNT_DECISION and isinstance(entry.value, Object)
        )
        if country_decisions is not None
        else ()
    )
    if len(definitions) != 1:
        result.add(
            "safety.sword_hunt_gate",
            f"{SWORD_HUNT_DECISION} has {len(definitions)} definitions; expected one",
            f"{surface.label}/{SWORD_HUNT_FILE.as_posix()}",
        )
        result.metrics["sword_hunt_contract"] = 0
        return

    decision = definitions[0]
    assert isinstance(decision.value, Object)
    potential = first_object(decision.value, "potential")
    passed = 0
    for requirement in SWORD_HUNT_POTENTIAL_CONTRACT:
        if _has_requirement(potential, requirement):
            passed += 1
            continue
        polarity = "explicit NOT" if requirement.negative else "positive identity"
        result.add(
            "safety.sword_hunt_gate",
            f"{SWORD_HUNT_DECISION} potential lacks {polarity} "
            f"{requirement.key} = {requirement.value}",
            _display_source(surface, source),
            decision.line,
        )
    result.metrics["sword_hunt_contract"] = passed


def _events(surface: Surface) -> dict[str, EventRecord]:
    records: dict[str, EventRecord] = {}
    root = surface.context.mod_root / "events"
    if not root.is_dir():
        return records
    for source in sorted(root.rglob("*.txt")):
        document = surface.context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if entry.key not in {"country_event", "province_event"} or not isinstance(
                entry.value, Object
            ):
                continue
            event_id = first_scalar(entry.value, "id")
            if event_id is not None:
                records[event_id] = EventRecord(
                    event_id,
                    entry.value,
                    _occurrence(surface, source, entry.line),
                )
    return records


def _check_hidden_event_contracts(surface: Surface, result: CheckResult) -> None:
    checked = 0
    for event in _events(surface).values():
        if first_scalar(event.body, "hidden") != "yes":
            continue
        checked += 1
        missing = [
            key
            for key in ("title", "desc", "picture")
            if first_scalar(event.body, key) is None
        ]
        options = [
            entry
            for entry in event.body.entries
            if entry.key == "option" and isinstance(entry.value, Object)
        ]
        if missing or not options:
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if not options:
                details.append("missing option")
            result.add(
                "event.hidden_contract",
                f"hidden event {event.event_id} has an incomplete engine shell: "
                + "; ".join(details),
                event.occurrence.source,
                event.occurrence.line,
            )
    result.metrics["hidden_events_checked"] = (
        int(result.metrics.get("hidden_events_checked", 0)) + checked
    )


def _check_event_modifier_keys(surface: Surface, result: CheckResult) -> None:
    checked = 0
    root = surface.context.mod_root / "common" / "event_modifiers"
    if not root.is_dir():
        return
    for source in sorted(root.rglob("*.txt")):
        document = surface.context.document(source)
        if document is None:
            continue
        for definition in document.root.entries:
            if not isinstance(definition.value, Object):
                continue
            for modifier in definition.value.entries:
                if modifier.key is None:
                    continue
                checked += 1
                replacement = INVALID_EVENT_MODIFIER_KEYS.get(modifier.key)
                if replacement is None:
                    continue
                result.add(
                    "modifier.engine_alias",
                    f"{definition.key} uses engine-rejected modifier "
                    f"{modifier.key}; use {replacement}",
                    _display_source(surface, source),
                    modifier.line,
                )
    result.metrics["event_modifier_entries_checked"] = (
        int(result.metrics.get("event_modifier_entries_checked", 0)) + checked
    )


def _scripted_effects(
    surface: Surface,
) -> dict[str, tuple[Object, Occurrence]]:
    effects: dict[str, tuple[Object, Occurrence]] = {}
    root = surface.context.mod_root / "common" / "scripted_effects"
    if not root.is_dir():
        return effects
    for source in sorted(root.rglob("*.txt")):
        document = surface.context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if entry.key is not None and isinstance(entry.value, Object):
                effects[entry.key] = (
                    entry.value,
                    _occurrence(surface, source, entry.line),
                )
    return effects


def _disaster_progress_targets(body: Object) -> tuple[tuple[str, int], ...]:
    targets: list[tuple[str, int]] = []
    for _path, entry in find_objects(body, "add_disaster_progress"):
        if not isinstance(entry.value, Object):
            continue
        disaster = first_scalar(entry.value, "disaster")
        if disaster is not None:
            targets.append((disaster, entry.line))
    return tuple(targets)


def _debug_decisions(surface: Surface) -> dict[str, tuple[Object, Occurrence]]:
    decisions: dict[str, tuple[Object, Occurrence]] = {}
    root = surface.context.mod_root / "decisions"
    if not root.is_dir():
        return decisions
    for source in sorted(root.rglob("*.txt")):
        if "debug" not in source.stem.casefold():
            continue
        document = surface.context.document(source)
        if document is None:
            continue
        country_decisions = first_object(document.root, "country_decisions")
        if country_decisions is None:
            continue
        for entry in country_decisions.entries:
            if entry.key is not None and isinstance(entry.value, Object):
                decisions[entry.key] = (
                    entry.value,
                    _occurrence(surface, source, entry.line),
                )
    return decisions


def _all_country_decisions(
    surface: Surface,
) -> dict[str, tuple[Object, Occurrence]]:
    decisions: dict[str, tuple[Object, Occurrence]] = {}
    root = surface.context.mod_root / "decisions"
    if not root.is_dir():
        return decisions
    for source in sorted(root.rglob("*.txt")):
        document = surface.context.document(source)
        if document is None:
            continue
        country_decisions = first_object(document.root, "country_decisions")
        if country_decisions is None:
            continue
        for entry in country_decisions.entries:
            if entry.key is not None and isinstance(entry.value, Object):
                decisions[entry.key] = (
                    entry.value,
                    _occurrence(surface, source, entry.line),
                )
    return decisions


def _disasters(surface: Surface) -> tuple[DisasterRecord, ...]:
    records: list[DisasterRecord] = []
    root = surface.context.mod_root / "common" / "disasters"
    if not root.is_dir():
        return ()
    for source in sorted(root.rglob("*.txt")):
        document = surface.context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if (
                entry.key is not None
                and entry.key.startswith("jxp_")
                and isinstance(entry.value, Object)
            ):
                records.append(
                    DisasterRecord(
                        entry.key,
                        entry.value,
                        _occurrence(surface, source, entry.line),
                    )
                )
    return tuple(records)


def _decision_calls_event(body: Object, event_id: str) -> bool:
    return any(
        first_scalar(entry.value, "id") == event_id
        for _path, entry in find_objects(body, "country_event")
        if isinstance(entry.value, Object)
    )


def _has_timed_country_flag(obj: Object | None, flag: str, days: int) -> bool:
    if obj is None:
        return False
    return any(
        first_scalar(entry.value, "flag") == flag
        and first_scalar(entry.value, "days") == str(days)
        for _path, entry in find_objects(obj, "had_country_flag")
        if isinstance(entry.value, Object)
    )


def _resolves_disaster(
    body: Object,
    resolved_flag: str,
    disaster_key: str,
    events: dict[str, EventRecord],
) -> bool:
    candidate_bodies = [body]
    for _path, entry in find_objects(body, "country_event"):
        if not isinstance(entry.value, Object):
            continue
        event_id = first_scalar(entry.value, "id")
        if event_id in events:
            candidate_bodies.append(events[event_id].body)
    return any(
        _has_positive(candidate, "set_country_flag", resolved_flag)
        and _has_positive(candidate, "end_disaster", disaster_key)
        for candidate in candidate_bodies
    )


def _resolved_flag_from_end(
    body: Object,
    events: dict[str, EventRecord],
) -> str | None:
    on_end = first_entry(body, "on_end")
    if on_end is None:
        return None
    if isinstance(on_end.value, Scalar) and on_end.value.text in events:
        end_body = events[on_end.value.text].body
    else:
        return None
    candidates = {
        entry.value.text
        for _path, entry in find_assignments(end_body, "set_country_flag")
        if isinstance(entry.value, Scalar) and entry.value.text.endswith("_resolved")
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def _end_body(body: Object, events: dict[str, EventRecord]) -> Object | None:
    on_end = first_entry(body, "on_end")
    if on_end is None:
        return None
    if isinstance(on_end.value, Scalar) and on_end.value.text in events:
        return events[on_end.value.text].body
    return None


def _has_cleanup(obj: Object | None) -> bool:
    if obj is None:
        return False
    cleanup_keys = set(FLAG_CLEAR_KEYS) | set(MODIFIER_CLEAR_KEYS)
    return any(entry.key in cleanup_keys for _path, entry in walk_entries(obj))


def _check_disasters(
    surface: Surface,
    debug_cleanup: DefaultDict[str, set[str]],
    result: CheckResult,
    minimum_disasters: int,
    maximum_disasters: int,
) -> None:
    disasters = _disasters(surface)
    events = _events(surface)
    debug_decisions = _debug_decisions(surface)
    all_decisions = _all_country_decisions(surface)
    scripted_effects = _scripted_effects(surface)

    progress_events: DefaultDict[str, list[EventRecord]] = defaultdict(list)
    for event in events.values():
        for target, _line in _disaster_progress_targets(event.body):
            progress_events[target].append(event)

    scripted_progress = 0
    for effect_name, (effect, occurrence) in scripted_effects.items():
        for target, line in _disaster_progress_targets(effect):
            if not target.startswith("jxp_"):
                continue
            scripted_progress += 1
            result.add(
                "disaster.debug_seed_load_order",
                f"{effect_name} embeds add_disaster_progress for custom disaster "
                f"{target}; dispatch to a complete hidden event so the disaster "
                "registry exists before effect validation",
                occurrence.source,
                line,
            )
    result.metrics["disaster_debug_progress_scripted"] = scripted_progress
    result.metrics["disaster_debug_progress_events"] = sum(
        len(progress_events.get(disaster.key, ())) for disaster in disasters
    )

    if not minimum_disasters <= len(disasters) <= maximum_disasters:
        result.add(
            "disaster.count",
            f"defined {len(disasters)} JXP disasters; acceptance requires "
            f"{minimum_disasters}-{maximum_disasters}",
            f"{surface.label}/common/disasters",
        )

    for disaster in disasters:
        body = disaster.body
        contract = DISASTER_CONTRACTS.get(disaster.key)
        if contract is None:
            result.add(
                "disaster.contract_missing",
                f"{disaster.key} has no explicit false-positive/debug contract",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )

        required_objects = (
            "potential",
            "can_start",
            "can_stop",
            "progress",
            "can_end",
            "modifier",
        )
        blocks = {key: first_object(body, key) for key in required_objects}
        for key, block in blocks.items():
            if block is None or (key == "modifier" and not block.entries):
                result.add(
                    "disaster.structure_missing",
                    f"{disaster.key} requires a non-empty {key} block",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
        if first_entry(body, "on_start") is None or first_entry(body, "on_end") is None:
            result.add(
                "disaster.structure_missing",
                f"{disaster.key} requires both on_start and on_end",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )

        potential = blocks["potential"]
        can_start = blocks["can_start"]
        can_stop = blocks["can_stop"]
        progress = blocks["progress"]
        can_end = blocks["can_end"]
        resolved_flag = (
            contract.resolved_flag
            if contract is not None
            else _resolved_flag_from_end(body, events)
        )
        if resolved_flag is None:
            result.add(
                "disaster.resolution_flag_missing",
                f"{disaster.key} has no unique *_resolved flag in its end path",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )
        elif not _has_requirement(
            potential,
            Requirement("has_country_flag", resolved_flag, True),
        ):
            result.add(
                "disaster.false_positive_gate",
                f"{disaster.key} potential must negate its resolved flag {resolved_flag}",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )

        requirements = (
            contract.potential if contract is not None else COMMON_DISASTER_POTENTIAL
        )
        for requirement in requirements:
            if not _has_requirement(potential, requirement):
                polarity = "negative" if requirement.negative else "positive"
                result.add(
                    "disaster.false_positive_gate",
                    f"{disaster.key} potential lacks {polarity} "
                    f"{requirement.key} = {requirement.value}",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
        if contract is not None:
            for requirement in contract.can_start:
                if not _has_requirement(can_start, requirement):
                    polarity = "negative" if requirement.negative else "positive"
                    result.add(
                        "disaster.false_positive_gate",
                        f"{disaster.key} can_start lacks {polarity} "
                        f"{requirement.key} = {requirement.value}",
                        disaster.occurrence.source,
                        disaster.occurrence.line,
                    )

        start_keys = {
            entry.key
            for _path, entry in walk_entries(can_start)
            if entry.key is not None
        } if can_start is not None else set()
        if not (start_keys & CHRONOLOGY_KEYS):
            result.add(
                "disaster.false_positive_gate",
                f"{disaster.key} can_start lacks a chronology gate",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )
        if len(start_keys & PRESSURE_KEYS) < 2:
            result.add(
                "disaster.false_positive_gate",
                f"{disaster.key} can_start needs at least two independent pressure dimensions",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )
        if not (start_keys & EXPOSURE_KEYS):
            result.add(
                "disaster.false_positive_gate",
                f"{disaster.key} can_start lacks a route, religion, or geographic exposure gate",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )
        if not _has_positive(can_start, "has_any_disaster", "no"):
            result.add(
                "disaster.false_positive_gate",
                f"{disaster.key} can_start must require has_any_disaster = no",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )

        factors: list[float] = []
        if progress is not None:
            for _path, entry in find_assignments(progress, "factor"):
                assert isinstance(entry.value, Scalar)
                try:
                    factors.append(float(entry.value.text))
                except ValueError:
                    continue
        if not any(value > 0 for value in factors) or not any(
            value < 0 for value in factors
        ):
            result.add(
                "disaster.progress_balance",
                f"{disaster.key} progress requires both accelerating and relieving factors",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )

        if resolved_flag is not None:
            if not _has_positive(can_stop, "has_country_flag", resolved_flag):
                result.add(
                    "disaster.resolution_path",
                    f"{disaster.key} can_stop does not honor {resolved_flag}",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
            if not _has_positive(can_end, "has_country_flag", resolved_flag):
                result.add(
                    "disaster.resolution_path",
                    f"{disaster.key} can_end does not honor {resolved_flag}",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
            recovery_assignments = [
                entry
                for _path, entry in walk_entries(can_end)
                if entry.key is not None
                and isinstance(entry.value, Scalar)
                and not (
                    entry.key == "has_country_flag"
                    and isinstance(entry.value, Scalar)
                    and entry.value.text == resolved_flag
                )
            ] if can_end is not None else []
            if not recovery_assignments:
                result.add(
                    "disaster.resolution_path",
                    f"{disaster.key} can_end has no organic recovery path",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )

        on_start = first_entry(body, "on_start")
        start_event_id = (
            on_start.value.text
            if on_start is not None and isinstance(on_start.value, Scalar)
            else None
        )
        start_event = events.get(start_event_id or "")
        if start_event is None:
            result.add(
                "disaster.start_event_missing",
                f"{disaster.key} on_start event {start_event_id!r} is missing",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )
        else:
            if first_scalar(start_event.body, "is_triggered_only") != "yes":
                result.add(
                    "disaster.start_event_not_triggered",
                    f"{disaster.key} on_start event must be is_triggered_only = yes",
                    start_event.occurrence.source,
                    start_event.occurrence.line,
                )
            options = tuple(
                entry.value
                for entry in start_event.body.entries
                if entry.key == "option" and isinstance(entry.value, Object)
            )
            if resolved_flag is not None and (
                (
                    options
                    and all(
                        _has_positive(option, "set_country_flag", resolved_flag)
                        for option in options
                    )
                )
                or (
                    not options
                    and _has_positive(
                        start_event.body, "set_country_flag", resolved_flag
                    )
                )
            ):
                result.add(
                    "disaster.instant_resolution",
                    f"every {disaster.key} on_start choice immediately sets {resolved_flag}",
                    start_event.occurrence.source,
                    start_event.occurrence.line,
                )

            if contract is not None and not _has_positive(
                start_event.body, "set_country_flag", contract.active_flag
            ):
                result.add(
                    "disaster.active_lifecycle",
                    f"{disaster.key} on_start event does not set "
                    f"{contract.active_flag}",
                    start_event.occurrence.source,
                    start_event.occurrence.line,
                )

        if contract is not None:
            if not _has_timed_country_flag(can_end, contract.active_flag, 365):
                result.add(
                    "disaster.minimum_duration",
                    f"{disaster.key} organic recovery must require "
                    f"{contract.active_flag} for 365 days",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )

            settlement = all_decisions.get(contract.settlement_decision)
            if settlement is None:
                result.add(
                    "disaster.settlement_missing",
                    f"{disaster.key} settlement decision "
                    f"{contract.settlement_decision} is missing",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
            else:
                settlement_body, settlement_occurrence = settlement
                settlement_potential = first_object(settlement_body, "potential")
                settlement_allow = first_object(settlement_body, "allow")
                settlement_ai = first_object(settlement_body, "ai_will_do")
                if not _has_positive(
                    settlement_potential, "has_disaster", disaster.key
                ) or not _has_positive(
                    settlement_potential,
                    "has_country_flag",
                    contract.active_flag,
                ):
                    result.add(
                        "disaster.settlement_gate",
                        f"{contract.settlement_decision} must require the active "
                        f"{disaster.key} and {contract.active_flag}",
                        settlement_occurrence.source,
                        settlement_occurrence.line,
                    )
                if not _has_timed_country_flag(
                    settlement_allow, contract.active_flag, 365
                ):
                    result.add(
                        "disaster.minimum_duration",
                        f"{contract.settlement_decision} must require "
                        f"{contract.active_flag} for 365 days",
                        settlement_occurrence.source,
                        settlement_occurrence.line,
                    )
                if not _resolves_disaster(
                    settlement_body,
                    contract.resolved_flag,
                    disaster.key,
                    events,
                ):
                    result.add(
                        "disaster.settlement_resolution",
                        f"{contract.settlement_decision} does not set "
                        f"{contract.resolved_flag} and end {disaster.key}",
                        settlement_occurrence.source,
                        settlement_occurrence.line,
                    )
                ai_factor = (
                    first_scalar(settlement_ai, "factor")
                    if settlement_ai is not None
                    else None
                )
                try:
                    ai_enabled = ai_factor is not None and float(ai_factor) > 0
                except ValueError:
                    ai_enabled = False
                if not ai_enabled:
                    result.add(
                        "disaster.ai_recovery_missing",
                        f"{contract.settlement_decision} must remain available to AI",
                        settlement_occurrence.source,
                        settlement_occurrence.line,
                    )

        on_end = first_entry(body, "on_end")
        end_event_id = (
            on_end.value.text
            if on_end is not None and isinstance(on_end.value, Scalar)
            else None
        )
        if on_end is not None and end_event_id is None:
            result.add(
                "disaster.end_event_reference",
                f"{disaster.key} on_end must be a scalar event ID, not an effect block",
                disaster.occurrence.source,
                on_end.line,
            )
        elif end_event_id is not None and end_event_id not in events:
            result.add(
                "disaster.end_event_missing",
                f"{disaster.key} on_end event {end_event_id!r} is missing",
                disaster.occurrence.source,
                on_end.line if on_end is not None else disaster.occurrence.line,
            )

        end_body = _end_body(body, events)
        if resolved_flag is not None and not _has_positive(
            end_body, "set_country_flag", resolved_flag
        ):
            result.add(
                "disaster.resolution_path",
                f"{disaster.key} on_end does not set {resolved_flag}",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )
        if not _has_cleanup(end_body):
            result.add(
                "disaster.end_cleanup",
                f"{disaster.key} on_end has no flag/modifier cleanup",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )
        elif end_body is not None:
            for kind, names in _cleanup_in_object(end_body).items():
                for name in sorted(names - debug_cleanup.get(kind, set())):
                    result.add(
                        "disaster.debug_cleanup_missing",
                        f"debug reset cannot reproduce {disaster.key} end cleanup for "
                        f"{kind} {name}",
                        disaster.occurrence.source,
                        disaster.occurrence.line,
                    )

        if contract is not None and not _has_positive(
            end_body, "clr_country_flag", contract.active_flag
        ):
            result.add(
                "disaster.active_lifecycle",
                f"{disaster.key} on_end does not clear {contract.active_flag}",
                disaster.occurrence.source,
                disaster.occurrence.line,
            )

        if contract is not None:
            token = contract.debug_token
            seed_events = progress_events.get(disaster.key, [])
            if len(seed_events) != 1:
                result.add(
                    "disaster.debug_seed_event",
                    f"{disaster.key} requires exactly one hidden triggered event "
                    f"that applies add_disaster_progress; found {len(seed_events)}",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
            else:
                seed_event = seed_events[0]
                if (
                    first_scalar(seed_event.body, "hidden") != "yes"
                    or first_scalar(seed_event.body, "is_triggered_only") != "yes"
                ):
                    result.add(
                        "disaster.debug_seed_event",
                        f"{seed_event.event_id} must be hidden and triggered-only",
                        seed_event.occurrence.source,
                        seed_event.occurrence.line,
                    )
                effect_name = f"jxp_debug_seed_{token}_pressure_effect"
                effect_record = scripted_effects.get(effect_name)
                if effect_record is None or not _decision_calls_event(
                    effect_record[0], seed_event.event_id
                ):
                    result.add(
                        "disaster.debug_seed_dispatch",
                        f"{effect_name} does not dispatch {seed_event.event_id}",
                        disaster.occurrence.source,
                        disaster.occurrence.line,
                    )
            seed_decisions = [
                (name, decision)
                for name, decision in debug_decisions.items()
                if name.startswith("jxp_debug_seed_") and token in name
            ]
            if not seed_decisions:
                result.add(
                    "disaster.debug_seed_missing",
                    f"{disaster.key} has no dedicated jxp_debug_seed_* entry",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
            resolution_decisions = [
                name
                for name, (decision, _occurrence_) in debug_decisions.items()
                if token in name
                and (
                    (start_event_id is not None and _decision_calls_event(decision, start_event_id))
                    or _has_positive(
                        decision, "set_country_flag", contract.resolved_flag
                    )
                )
            ]
            if not resolution_decisions:
                result.add(
                    "disaster.debug_resolution_missing",
                    f"{disaster.key} has no dedicated debug resolution entry",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
            if contract.resolved_flag not in debug_cleanup.get("country_flag", set()):
                result.add(
                    "disaster.debug_cleanup_missing",
                    f"debug reset cannot clear {contract.resolved_flag}",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )
            if contract.active_flag not in debug_cleanup.get("country_flag", set()):
                result.add(
                    "disaster.debug_cleanup_missing",
                    f"debug reset cannot clear {contract.active_flag}",
                    disaster.occurrence.source,
                    disaster.occurrence.line,
                )

    result.metrics["disasters"] = len(disasters)
    result.metrics["disaster_contracts"] = sum(
        disaster.key in DISASTER_CONTRACTS for disaster in disasters
    )


def check_state_safety(
    main_context: ValidationContext,
    companion_context: ValidationContext | None = None,
    *,
    minimum_disasters: int = 4,
    maximum_disasters: int = 5,
) -> CheckResult:
    """Return the combined state/disaster audit for the maintained release surface."""

    result = CheckResult("Runtime state and disaster safety")
    surfaces = [Surface("main", main_context, MAIN_DEBUG_ROOTS)]
    if companion_context is not None:
        surfaces.append(Surface("map", companion_context, MAP_DEBUG_ROOTS))
    surface_tuple = tuple(surfaces)
    inventory = _scan_inventory(surface_tuple)
    debug_cleanup = {
        surface.label: _debug_cleanup_closure(surface, result)
        for surface in surface_tuple
    }
    _check_state_inventory(inventory, surface_tuple, debug_cleanup, result)
    _check_sword_hunt_gate(surface_tuple[0], result)
    for surface in surface_tuple:
        _check_hidden_event_contracts(surface, result)
        _check_event_modifier_keys(surface, result)
    _check_disasters(
        surface_tuple[0],
        debug_cleanup["main"],
        result,
        minimum_disasters,
        maximum_disasters,
    )

    for surface in surface_tuple:
        for source, message in sorted(
            surface.context.parse_errors.items(),
            key=lambda item: surface.context.relative(item[0]).casefold(),
        ):
            result.add(
                "state.parse",
                message,
                _display_source(surface, source),
            )

    result.metrics["surfaces"] = len(surface_tuple)
    result.summary = (
        f"{result.metrics.get('country_flag_created', 0)} country flags, "
        f"{result.metrics.get('province_flag_created', 0)} province flags, "
        f"{result.metrics.get('modifier_definitions', 0)} modifier definitions, "
        f"{result.metrics.get('disasters', 0)} disasters; "
        f"{len(result.issues)} hard failure(s)"
    )
    return result


def _parse_args() -> argparse.Namespace:
    default_main = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod-root", type=Path, default=default_main)
    parser.add_argument("--companion-root", type=Path)
    parser.add_argument("--minimum-disasters", type=int, default=4)
    parser.add_argument("--maximum-disasters", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    main_root = args.mod_root.resolve()
    companion_root = args.companion_root
    if companion_root is None:
        candidate = main_root.parent / "japan_expanded_v2_map"
        companion_root = candidate if candidate.is_dir() else None
    companion_context = (
        ValidationContext(companion_root.resolve())
        if companion_root is not None and companion_root.is_dir()
        else None
    )
    result = check_state_safety(
        ValidationContext(main_root),
        companion_context,
        minimum_disasters=args.minimum_disasters,
        maximum_disasters=args.maximum_disasters,
    )
    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        status = "OK" if result.passed else "ERROR"
        print(f"{status}: {result.summary}")
        for key, value in sorted(result.metrics.items()):
            print(f"METRIC: {key}={value}")
        for issue in result.issues:
            location = issue.source or "<combined>"
            if issue.line is not None:
                location += f":{issue.line}"
            print(f"ERROR [{issue.code}] {location}: {issue.message}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
