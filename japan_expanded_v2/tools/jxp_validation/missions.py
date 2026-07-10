"""Mission layout, dependency, and representative-profile validation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
import re
from typing import Iterable

from .clausewitz import (
    Entry,
    Object,
    Scalar,
    bare_scalars,
    entries_named,
    first_entry,
    first_object,
    first_scalar,
)
from .core import CheckResult, ValidationContext
from .create_legacy_bom_mission_aliases_v0241 import FILE_PREFIX as LEGACY_BOM_FILE_PREFIX


MISSION_SERIES_METADATA = {
    "slot",
    "generic",
    "ai",
    "potential",
    "potential_on_load",
    "has_country_shield",
}
CORE_TAGS = {"JAP", "KJP", "CJP", "EJP", "RFJ", "SJP", "IJP", "WAK"}
ROUTE_FLAGS = {
    "jxp_path_sakoku",
    "jxp_path_open_trade",
    "jxp_path_kirishitan",
    "jxp_path_confucian",
    "jxp_path_imperial",
    "jxp_path_reformed",
    "jxp_path_kaikyo",
    "jxp_path_ikko",
    "jxp_path_wokou",
}
LOCALISATION_KEY_PATTERN = re.compile(r"(?m)^\s*([A-Za-z0-9_.-]+):\d+\s")
PINNED_OVERRIDE_FILES = {"Japanese_Missions.txt", "DOM_Japanese_Missions.txt"}
DAIMYO_TAGS = (
    "AKM", "AKT", "AMA", "ASA", "ASK", "CBA", "CSK", "DTE", "HJO",
    "HSK", "HTK", "IKE", "IMG", "ISK", "ITO", "KKC", "KNO", "KTB",
    "MAE", "MRI", "ODA", "OGS", "OTM", "OUC", "RFR", "SBA", "SHN",
    "SMZ", "SOO", "STK", "TKD", "TKG", "TKI", "TTI", "UES", "UTN",
    "YMN", "TOY",
)


@dataclass(frozen=True, slots=True)
class Mission:
    mission_id: str
    row: int | None
    required: tuple[str, ...]
    source: Path
    line: int
    series_name: str
    slot: int | None


@dataclass(frozen=True, slots=True)
class MissionSeries:
    name: str
    slot: int | None
    generic: bool
    potential: Object | None
    missions: tuple[Mission, ...]
    source: Path
    line: int
    potential_on_load: Object | None = None


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    tag: str
    religion: str
    religion_group: str
    flags: frozenset[str] = frozenset()
    harmonized: frozenset[str] = frozenset()
    reforms: frozenset[str] = frozenset()
    culture_group: str = "japanese_g"
    daimyo_stage: bool = False
    japanese_polity: bool = True
    map_setup: str = "map_setup_normal"
    dlcs: frozenset[str] = frozenset({"Domination", "Mandate of Heaven"})
    emperor_of_china: bool = False
    capital_continent: str = "asia"


BASE_PROFILES = tuple(
    Profile(
        f"daimyo tag {tag}",
        tag,
        "shinto",
        "eastern",
        reforms=frozenset({"shogunate"}),
        daimyo_stage=True,
    )
    for tag in DAIMYO_TAGS
) + (
    Profile("JAP Shinto (uncommitted)", "JAP", "shinto", "eastern"),
    Profile(
        "JAP Shinto (sakoku)",
        "JAP",
        "shinto",
        "eastern",
        flags=frozenset({"jxp_path_sakoku", "christianity_defeated_flag"}),
    ),
    Profile(
        "JAP Shinto (open)",
        "JAP",
        "shinto",
        "eastern",
        flags=frozenset({"jxp_path_open_trade", "jap_chose_kaikoku_flag"}),
    ),
    Profile(
        "CJP Confucian + harmonized Shinto",
        "CJP",
        "confucianism",
        "eastern",
        flags=frozenset({"jxp_path_confucian"}),
        harmonized=frozenset({"shinto"}),
    ),
    Profile(
        "KJP Christian",
        "KJP",
        "catholic",
        "christian",
        flags=frozenset({"jxp_path_kirishitan"}),
    ),
    Profile(
        "EJP Imperial",
        "EJP",
        "shinto",
        "eastern",
        flags=frozenset({"jxp_path_imperial"}),
    ),
    Profile(
        "RFJ Reformed",
        "RFJ",
        "reformed",
        "christian",
        flags=frozenset({"jxp_path_reformed"}),
    ),
    Profile(
        "SJP Kaikyo",
        "SJP",
        "sunni",
        "muslim",
        flags=frozenset({"jxp_path_kaikyo"}),
    ),
    Profile(
        "IJP Ikko",
        "IJP",
        "shinto",
        "eastern",
        flags=frozenset({"jxp_path_ikko"}),
    ),
    Profile(
        "WAK Wokou",
        "WAK",
        "shinto",
        "eastern",
        flags=frozenset({"jxp_path_wokou"}),
    ),
)

DLC_PROFILE_VARIANTS = (
    ("", frozenset({"Domination", "Mandate of Heaven"})),
    (" [Domination only]", frozenset({"Domination"})),
    (" [Mandate of Heaven only]", frozenset({"Mandate of Heaven"})),
    (" [no relevant DLC]", frozenset()),
)

PROFILES = tuple(
    replace(profile, name=f"{profile.name}{suffix}", dlcs=dlcs)
    for profile in BASE_PROFILES
    for suffix, dlcs in DLC_PROFILE_VARIANTS
)


@dataclass(frozen=True, slots=True)
class UnknownPredicate:
    key: str
    line: int
    reason: str


def _parse_integer(text: str | None) -> int | None:
    if text is None or not re.fullmatch(r"[+-]?\d+", text):
        return None
    return int(text)


def _truth_and(values: Iterable[frozenset[bool]]) -> frozenset[bool]:
    possible = {True}
    for value in values:
        possible = {left and right for left in possible for right in value}
    return frozenset(possible)


def _truth_or(values: Iterable[frozenset[bool]]) -> frozenset[bool]:
    possible = {False}
    for value in values:
        possible = {left or right for left in possible for right in value}
    return frozenset(possible)


def _apply_yes_no(value: str, actual: bool) -> frozenset[bool] | None:
    if value == "yes":
        return frozenset({actual})
    if value == "no":
        return frozenset({not actual})
    return None


def evaluate_potential(
    potential: Object | None,
    profile: Profile,
) -> tuple[frozenset[bool], tuple[UnknownPredicate, ...]]:
    """Return possible truth values and unsupported predicates.

    Unknown predicates remain both true and false.  This makes collision
    detection conservative while also surfacing the unsupported grammar.
    """

    unknown: list[UnknownPredicate] = []

    def evaluate_sequence(obj: Object) -> frozenset[bool]:
        return _truth_and(evaluate_entry(entry) for entry in obj.entries)

    def malformed(entry: Entry, reason: str) -> frozenset[bool]:
        unknown.append(UnknownPredicate(entry.key or "<bare>", entry.line, reason))
        return frozenset({False, True})

    def evaluate_entry(entry: Entry) -> frozenset[bool]:
        if entry.key is None:
            return malformed(entry, "bare scalar in potential block")

        key = entry.key
        value = entry.value
        if key in {"AND", "OR", "NOT"}:
            if not isinstance(value, Object):
                return malformed(entry, f"{key} requires an object")
            if key == "AND":
                return evaluate_sequence(value)
            if key == "OR":
                return _truth_or(evaluate_entry(child) for child in value.entries)
            nested = evaluate_sequence(value)
            return frozenset(not item for item in nested)

        if key == "capital_scope":
            if not isinstance(value, Object):
                return malformed(entry, "capital_scope requires an object")
            scoped_values: list[frozenset[bool]] = []
            for child in value.entries:
                if (
                    child.key == "continent"
                    and isinstance(child.value, Scalar)
                ):
                    scoped_values.append(
                        frozenset({profile.capital_continent == child.value.text})
                    )
                else:
                    scoped_values.append(
                        malformed(child, "unsupported capital_scope predicate")
                    )
            return _truth_and(scoped_values)

        if not isinstance(value, Scalar):
            return malformed(entry, f"{key} requires a scalar")

        text = value.text
        if key == "always":
            interpreted = _apply_yes_no(text, True)
            return interpreted or malformed(entry, "always must be yes or no")
        if key == "tag":
            return frozenset({profile.tag == text})
        if key == "religion":
            return frozenset({profile.religion == text})
        if key == "religion_group":
            return frozenset({profile.religion_group == text})
        if key == "culture_group":
            return frozenset({profile.culture_group == text})
        if key == "map_setup":
            return frozenset({profile.map_setup == text})
        if key == "has_country_flag":
            return frozenset({text in profile.flags})
        if key == "has_harmonized_with":
            return frozenset({text in profile.harmonized})
        if key == "has_reform":
            return frozenset({text in profile.reforms})
        if key == "has_dlc":
            return frozenset({text in profile.dlcs})
        if key == "is_emperor_of_china":
            interpreted = _apply_yes_no(text, profile.emperor_of_china)
            return interpreted or malformed(
                entry,
                "is_emperor_of_china must be compared with yes or no",
            )

        scripted_values = {
            "jxp_is_daimyo_stage_trigger": profile.daimyo_stage,
            "jxp_is_japanese_polity_trigger": profile.japanese_polity,
            "jxp_has_any_route_trigger": bool(profile.flags & ROUTE_FLAGS),
            "jxp_not_sakoku_locked_trigger": "jxp_path_sakoku" not in profile.flags,
            "jxp_is_japan_expanded_core_tag_trigger": profile.tag in CORE_TAGS,
            "jxp_use_custom_missions_trigger": (
                profile.japanese_polity or profile.daimyo_stage
            ),
            "jxp_can_use_overseas_expansion_trigger": (
                profile.japanese_polity
                and "jxp_path_sakoku" not in profile.flags
                and (profile.tag in CORE_TAGS or bool(profile.flags & ROUTE_FLAGS))
            ),
        }
        if key in scripted_values:
            interpreted = _apply_yes_no(text, scripted_values[key])
            return interpreted or malformed(entry, f"{key} must be compared with yes or no")

        return malformed(entry, "unsupported profile predicate")

    if potential is None:
        return frozenset({True}), ()
    values = evaluate_sequence(potential)
    deduplicated = tuple(dict.fromkeys(unknown))
    return values, deduplicated


def find_position_collisions(
    placements: Iterable[tuple[int, int, str]],
) -> dict[tuple[int, int], tuple[str, ...]]:
    occupancy: dict[tuple[int, int], list[str]] = defaultdict(list)
    for slot, row, label in placements:
        occupancy[(slot, row)].append(label)
    return {
        coordinate: tuple(labels)
        for coordinate, labels in occupancy.items()
        if len(labels) > 1
    }


def extract_mission_series(
    context: ValidationContext,
    result: CheckResult,
    sources: Iterable[Path],
    *,
    infer_implicit_positions: bool = False,
) -> tuple[MissionSeries, ...]:
    """Parse mission series from selected files.

    EU4's vanilla mission files may omit ``position`` and advance one row in
    source order. Mod files are deliberately held to explicit positions.
    """

    series_list: list[MissionSeries] = []
    for source in sorted(sources, key=lambda path: context.relative(path).casefold()):
        document = context.document(source)
        if document is None:
            continue
        for series_entry in document.root.entries:
            if series_entry.key is None or not isinstance(series_entry.value, Object):
                result.add(
                    "mission.invalid_series",
                    "top-level mission entry must be a named object",
                    context.relative(source),
                    series_entry.line,
                )
                continue

            body = series_entry.value
            slot_entries = entries_named(body, "slot")
            slot_text = first_scalar(body, "slot")
            slot = _parse_integer(slot_text)
            if len(slot_entries) != 1 or slot is None:
                result.add(
                    "mission.slot_invalid",
                    f"series {series_entry.key} must declare exactly one integer slot",
                    context.relative(source),
                    series_entry.line,
                )
                slot = None
            elif slot not in range(1, 6):
                result.add(
                    "mission.slot_range",
                    f"series {series_entry.key} uses slot {slot}; expected 1..5",
                    context.relative(source),
                    slot_entries[0].line,
                )

            potential_entry = first_entry(body, "potential")
            potential = first_object(body, "potential")
            if potential_entry is not None and potential is None:
                result.add(
                    "mission.potential_invalid",
                    f"series {series_entry.key} potential must be an object",
                    context.relative(source),
                    potential_entry.line,
                )

            missions: list[Mission] = []
            next_implicit_row = 1
            for mission_entry in body.entries:
                if mission_entry.key in MISSION_SERIES_METADATA or mission_entry.key is None:
                    continue
                if not isinstance(mission_entry.value, Object):
                    continue

                position_entries = entries_named(mission_entry.value, "position")
                position_text = first_scalar(mission_entry.value, "position")
                row = _parse_integer(position_text)
                if not position_entries and infer_implicit_positions:
                    row = next_implicit_row
                elif len(position_entries) != 1 or row is None:
                    result.add(
                        "mission.position_invalid",
                        f"mission {mission_entry.key} must declare exactly one integer position",
                        context.relative(source),
                        mission_entry.line,
                    )
                    row = None
                elif row <= 0:
                    result.add(
                        "mission.position_nonpositive",
                        f"mission {mission_entry.key} uses non-positive row {row}",
                        context.relative(source),
                        position_entries[0].line,
                    )
                if row is not None:
                    next_implicit_row = row + 1

                required: list[str] = []
                required_entries = entries_named(mission_entry.value, "required_missions")
                if len(required_entries) > 1:
                    result.add(
                        "mission.required_duplicate_field",
                        f"mission {mission_entry.key} declares required_missions more than once",
                        context.relative(source),
                        required_entries[1].line,
                    )
                for required_entry in required_entries:
                    if not isinstance(required_entry.value, Object):
                        result.add(
                            "mission.required_invalid",
                            f"mission {mission_entry.key} required_missions must be an object",
                            context.relative(source),
                            required_entry.line,
                        )
                        continue
                    required.extend(value.text for value in bare_scalars(required_entry.value))
                    for item in required_entry.value.entries:
                        if item.key is not None:
                            result.add(
                                "mission.required_invalid_item",
                                f"mission {mission_entry.key} has a keyed required_missions item",
                                context.relative(source),
                                item.line,
                            )

                missions.append(
                    Mission(
                        mission_entry.key,
                        row,
                        tuple(required),
                        source,
                        mission_entry.line,
                        series_entry.key,
                        slot,
                    )
                )

            series_list.append(
                MissionSeries(
                    series_entry.key,
                    slot,
                    first_scalar(body, "generic") == "yes",
                    potential,
                    tuple(missions),
                    source,
                    series_entry.line,
                    first_object(body, "potential_on_load"),
                )
            )
    return tuple(series_list)


def find_dependency_cycles(missions: dict[str, Mission]) -> tuple[tuple[str, ...], ...]:
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[tuple[str, ...]] = []
    seen: set[frozenset[str]] = set()

    def visit(mission_id: str) -> None:
        state[mission_id] = 1
        stack.append(mission_id)
        for dependency in missions[mission_id].required:
            if dependency not in missions:
                continue
            if state.get(dependency) == 1:
                start = stack.index(dependency)
                cycle = tuple(stack[start:] + [dependency])
                identity = frozenset(cycle[:-1])
                if identity not in seen:
                    seen.add(identity)
                    cycles.append(cycle)
            elif state.get(dependency, 0) == 0:
                visit(dependency)
        stack.pop()
        state[mission_id] = 2

    for mission_id in missions:
        if state.get(mission_id, 0) == 0:
            visit(mission_id)
    return tuple(cycles)


def _localisation_keys(mod_root: Path) -> set[str]:
    keys: set[str] = set()
    for directory_name in ("localisation_source", "localisation"):
        directory = mod_root / directory_name
        if not directory.is_dir():
            continue
        for source in directory.rglob("*.yml"):
            data = source.read_bytes()
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = data.decode("cp1252")
            keys.update(LOCALISATION_KEY_PATTERN.findall(text))
    return keys


def _jxp_trigger_calls(block: Object) -> tuple[tuple[str, int], ...]:
    calls: list[tuple[str, int]] = []

    def visit(obj: Object) -> None:
        for entry in obj.entries:
            if entry.key is not None and entry.key.startswith("jxp_"):
                calls.append((entry.key, entry.line))
            if isinstance(entry.value, Object):
                visit(entry.value)

    visit(block)
    return tuple(calls)


def check_mission_scripted_triggers(
    context: ValidationContext,
    result: CheckResult,
    mission_sources: Iterable[Path],
) -> int:
    definitions: set[str] = set()
    trigger_root = context.mod_root / "common" / "scripted_triggers"
    if trigger_root.is_dir():
        for source in trigger_root.glob("*.txt"):
            document = context.document(source)
            if document is None:
                continue
            definitions.update(
                entry.key
                for entry in document.root.entries
                if entry.key is not None and isinstance(entry.value, Object)
            )

    calls_checked = 0
    seen: set[tuple[str, str, int]] = set()
    for source in mission_sources:
        document = context.document(source)
        if document is None:
            continue
        for series_entry in document.root.entries:
            if series_entry.key is None or not isinstance(series_entry.value, Object):
                continue
            series_body = series_entry.value
            trigger_blocks: list[Object] = []
            for key in ("potential", "potential_on_load"):
                block = first_object(series_body, key)
                if block is not None:
                    trigger_blocks.append(block)
            for mission_entry in series_body.entries:
                if (
                    mission_entry.key in MISSION_SERIES_METADATA
                    or mission_entry.key is None
                    or not isinstance(mission_entry.value, Object)
                ):
                    continue
                for key in ("trigger", "provinces_to_highlight"):
                    block = first_object(mission_entry.value, key)
                    if block is not None:
                        trigger_blocks.append(block)

            for block in trigger_blocks:
                for key, line in _jxp_trigger_calls(block):
                    identity = (str(source), key, line)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    calls_checked += 1
                    if key not in definitions:
                        result.add(
                            "mission.scripted_trigger_missing",
                            f"mission trigger calls undefined scripted trigger {key}",
                            context.relative(source),
                            line,
                        )
    return calls_checked


def check_missions(context: ValidationContext) -> CheckResult:
    result = CheckResult("Missions")
    mission_root = context.mod_root / "missions"
    if not mission_root.is_dir():
        result.add("mission.directory_missing", "missions directory is missing", "missions")
        series_list: tuple[MissionSeries, ...] = ()
        mission_sources: tuple[Path, ...] = ()
    else:
        mission_sources = tuple(
            sorted(
                path
                for path in mission_root.glob("*.txt")
                if path.name not in PINNED_OVERRIDE_FILES
                and not path.name.startswith(LEGACY_BOM_FILE_PREFIX)
            )
        )
        series_list = extract_mission_series(
            context,
            result,
            mission_sources,
        )

    scripted_trigger_calls = check_mission_scripted_triggers(
        context,
        result,
        mission_sources,
    )

    series_by_name: dict[str, list[MissionSeries]] = defaultdict(list)
    mission_occurrences: dict[str, list[Mission]] = defaultdict(list)
    for series in series_list:
        series_by_name[series.name].append(series)
        if (
            series.potential_on_load is not None
            and first_scalar(series.potential_on_load, "always") == "yes"
        ):
            result.add(
                "mission.potential_on_load_broad",
                f"series {series.name} uses potential_on_load = always yes; rely on its "
                "normal potential and swap_non_generic_missions instead",
                context.relative(series.source),
                series.line,
            )
        previous: Mission | None = None
        for mission in series.missions:
            mission_occurrences[mission.mission_id].append(mission)
            if mission.row is None:
                continue
            if previous is not None and previous.row is not None:
                delta = mission.row - previous.row
                if delta <= 0:
                    result.add(
                        "mission.source_order_nonmonotonic",
                        f"series {series.name} declares {mission.mission_id} at row "
                        f"{mission.row} after {previous.mission_id} at row {previous.row}; "
                        "EU4 assembles columns in declaration order",
                        context.relative(mission.source),
                        mission.line,
                    )
                elif delta > 2:
                    result.add(
                        "mission.source_gap_too_wide",
                        f"series {series.name} leaves {delta - 1} empty rows between "
                        f"{previous.mission_id} and {mission.mission_id}; authored JXP "
                        "columns permit at most one empty row",
                        context.relative(mission.source),
                        mission.line,
                    )
            previous = mission

    for name, occurrences in sorted(series_by_name.items()):
        if len(occurrences) > 1:
            for duplicate in occurrences[1:]:
                result.add(
                    "mission.duplicate_series",
                    f"series id {name} is also defined in {context.relative(occurrences[0].source)}",
                    context.relative(duplicate.source),
                    duplicate.line,
                )

    for mission_id, occurrences in sorted(mission_occurrences.items()):
        if len(occurrences) > 1:
            first = occurrences[0]
            for duplicate in occurrences[1:]:
                result.add(
                    "mission.duplicate_id",
                    f"mission id {mission_id} is also defined at "
                    f"{context.relative(first.source)}:{first.line}",
                    context.relative(duplicate.source),
                    duplicate.line,
                )

    missions = {mission_id: values[0] for mission_id, values in mission_occurrences.items()}
    for mission_id, mission in sorted(missions.items()):
        for dependency in mission.required:
            target = missions.get(dependency)
            if target is None:
                result.add(
                    "mission.required_missing",
                    f"{mission_id} requires missing mission {dependency}",
                    context.relative(mission.source),
                    mission.line,
                )
                continue
            if mission.row is not None and target.row is not None and mission.row <= target.row:
                result.add(
                    "mission.edge_not_forward",
                    f"dependency edge {dependency} (row {target.row}) -> {mission_id} "
                    f"(row {mission.row}) does not point to a larger row",
                    context.relative(mission.source),
                    mission.line,
                )

    for cycle in find_dependency_cycles(missions):
        first = missions[cycle[0]]
        result.add(
            "mission.dependency_cycle",
            "dependency cycle: " + " -> ".join(cycle),
            context.relative(first.source),
            first.line,
        )

    localisation_keys = _localisation_keys(context.mod_root)
    for mission_id, mission in sorted(missions.items()):
        for suffix in ("_title", "_desc"):
            key = mission_id + suffix
            if key not in localisation_keys:
                result.add(
                    "mission.localisation_missing",
                    f"mission {mission_id} is missing canonical localisation key {key}",
                    context.relative(mission.source),
                    mission.line,
                )

    maximum_profile_empty_run = 0
    minimum_unified_slot_missions: int | None = None
    maximum_unified_terminal_spread = 0
    unified_signatures: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for profile in PROFILES:
        placements: list[tuple[int, int, str]] = []
        active_series: list[str] = []
        active_series_by_slot: dict[int, list[str]] = defaultdict(list)
        for series in series_list:
            if series.generic:
                continue
            possible, unknown = evaluate_potential(series.potential, profile)
            for predicate in unknown:
                result.add(
                    "mission.profile_predicate_unknown",
                    f"series {series.name} uses unsupported predicate "
                    f"{predicate.key}: {predicate.reason}",
                    context.relative(series.source),
                    predicate.line,
                )
            if True not in possible:
                continue
            active_series.append(series.name)
            if series.slot is not None:
                active_series_by_slot[series.slot].append(series.name)
            for mission in series.missions:
                if mission.slot in range(1, 6) and mission.row is not None and mission.row > 0:
                    placements.append(
                        (
                            mission.slot,
                            mission.row,
                            f"{mission.mission_id} [{series.name}]",
                        )
                    )

        for slot, names in sorted(active_series_by_slot.items()):
            if len(names) > 1:
                result.add(
                    "mission.profile_series_overlap",
                    f"profile {profile.name} activates multiple non-generic mission "
                    f"series in slot {slot}: " + ", ".join(names),
                )

        active_slots = set(active_series_by_slot)
        if active_slots != set(range(1, 6)):
            result.add(
                "mission.profile_slot_coverage",
                f"profile {profile.name} activates custom slots "
                f"{sorted(active_slots)}; expected complete 1..5 coverage so EU4 "
                "cannot insert generic fallback missions",
            )

        for (slot, row), labels in sorted(find_position_collisions(placements).items()):
            result.add(
                "mission.profile_collision",
                f"profile {profile.name} has active collision at slot {slot}, row {row}: "
                + "; ".join(labels),
            )
        occupied_rows = sorted({row for _slot, row, _label in placements})
        profile_empty_run = max(
            (right - left - 1 for left, right in zip(occupied_rows, occupied_rows[1:])),
            default=0,
        )
        maximum_profile_empty_run = max(maximum_profile_empty_run, profile_empty_run)
        if profile_empty_run > 1:
            result.add(
                "mission.profile_vertical_void",
                f"profile {profile.name} contains a whole-tree vertical void of "
                f"{profile_empty_run} rows; compact JXP layouts allow at most one",
            )

        if profile.japanese_polity and not profile.daimyo_stage and active_slots == set(range(1, 6)):
            slot_counts: dict[int, int] = {}
            slot_terminals: dict[int, int] = {}
            signature: list[str] = []
            for slot in range(1, 6):
                names = active_series_by_slot[slot]
                if len(names) != 1:
                    continue
                name = names[0]
                signature.append(name)
                active = series_by_name[name][0]
                rows = [mission.row for mission in active.missions if mission.row is not None]
                if not rows:
                    continue
                slot_counts[slot] = len(active.missions)
                slot_terminals[slot] = max(rows)
                minimum_unified_slot_missions = min(
                    minimum_unified_slot_missions or len(active.missions),
                    len(active.missions),
                )
                if len(active.missions) < 5:
                    result.add(
                        "mission.unified_slot_too_short",
                        f"profile {profile.name} slot {slot} uses {name} with only "
                        f"{len(active.missions)} missions; every unified final tree slot "
                        "requires at least five",
                    )
                if slot >= 3 and max(rows) < 10:
                    result.add(
                        "mission.unified_route_terminal_too_early",
                        f"profile {profile.name} route slot {slot} ends at row {max(rows)}; "
                        "route columns must reach row 10 or later",
                    )

            if len(slot_terminals) == 5:
                spread = max(slot_terminals.values()) - min(slot_terminals.values())
                maximum_unified_terminal_spread = max(
                    maximum_unified_terminal_spread,
                    spread,
                )
                if spread > 5:
                    result.add(
                        "mission.unified_terminal_imbalance",
                        f"profile {profile.name} slot terminals are "
                        f"{[slot_terminals[slot] for slot in range(1, 6)]}; "
                        "a final tree may differ by at most five rows",
                    )

            # Record only the full-DLC base profile once. Every final tag/route
            # must own a distinct five-series identity instead of sharing an
            # apparently generic late-game tree.
            if " [" not in profile.name and len(signature) == 5:
                unified_signatures[tuple(signature)].append(profile.name)
        result.notes.append(
            f"{profile.name}: {len(active_series)} active series across "
            f"{len(active_slots)} custom slots, {len(placements)} occupied rows"
        )

    for signature, profile_names in sorted(unified_signatures.items()):
        if len(profile_names) > 1:
            result.add(
                "mission.unified_signature_duplicate",
                "unified profiles share the same five-series mission identity: "
                + ", ".join(profile_names)
                + " ("
                + ", ".join(signature)
                + ")",
            )

    result.metrics.update(
        {
            "files": len({series.source for series in series_list}),
            "series": len(series_list),
            "missions": len(mission_occurrences),
            "profiles": len(PROFILES),
            "scripted_trigger_calls": scripted_trigger_calls,
            "localisation_keys": len(localisation_keys),
            "maximum_profile_empty_run": maximum_profile_empty_run,
            "minimum_unified_slot_missions": minimum_unified_slot_missions or 0,
            "maximum_unified_terminal_spread": maximum_unified_terminal_spread,
        }
    )
    result.summary = (
        f"{len(mission_occurrences)} mission ids in {len(series_list)} series; "
        f"{len(PROFILES)} representative profile states"
    )
    return result
