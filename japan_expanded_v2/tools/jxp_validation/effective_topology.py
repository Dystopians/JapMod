"""Pinned EU4 1.37.5 vanilla-plus-mod Japanese mission topology checks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, Iterable

from .clausewitz import Object, Scalar, first_scalar
from .core import CheckResult, Issue, ValidationContext
from .create_legacy_bom_mission_aliases_v0241 import FILE_PREFIX as LEGACY_BOM_FILE_PREFIX
from .create_japanese_mission_overrides_v0231 import patch_potentials
from .missions import (
    PROFILES,
    Mission,
    MissionSeries,
    Profile,
    evaluate_potential,
    extract_mission_series,
    find_dependency_cycles,
    find_position_collisions,
)


MANIFEST_PATH = Path(__file__).with_name("vanilla_1_37_5_manifest.json")
GENERIC_MISSION_FILES = (
    "00_Generic_missions.txt",
    "01_Generic_European_Missions.txt",
    "Asian_Missions.txt",
)
ROUTE_TAGS = {"KJP", "CJP", "EJP", "RFJ", "SJP", "IJP", "WAK", "TOY"}
FOUNDATION_MISSIONS = {
    "jxp_mission_route_inherited_realm",
    "jxp_mission_route_province_registers",
    "jxp_mission_route_archipelago_circuit",
    "jxp_mission_route_two_capitals",
    "jxp_mission_route_rice_and_silver",
    "jxp_mission_route_post_station_ledger",
    "jxp_mission_route_settle_new_constitution",
    "jxp_mission_route_laws_of_the_new_realm",
    "jxp_mission_route_renewed_japan",
    "jxp_mission_route_muster_rolls",
    "jxp_mission_route_firearm_offices",
    "jxp_mission_route_rites_of_the_isles",
    "jxp_mission_route_guard_the_sea_lanes",
}
UNIFIED_CONTINUITY_SERIES = {
    "jxp_japan_state_missions",
    "jxp_japan_court_missions",
}
BUDDHIST_REPLACEMENT_SERIES = {
    f"jxp_a_96_buddhist_slot_{slot}_missions" for slot in range(1, 6)
}


@dataclass(frozen=True, slots=True)
class TopologyProblem:
    code: str
    message: str
    source: Path | None = None
    line: int | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compress_rows(rows: Iterable[int]) -> str:
    ordered = sorted(set(rows))
    if not ordered:
        return "-"
    ranges: list[str] = []
    start = previous = ordered[0]
    for row in ordered[1:]:
        if row == previous + 1:
            previous = row
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = row
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(ranges)


def summarize_cells(missions: Iterable[Mission]) -> str:
    mission_list = tuple(missions)
    by_slot: dict[int, list[int]] = defaultdict(list)
    for mission in mission_list:
        if mission.slot is not None and mission.row is not None:
            by_slot[mission.slot].append(mission.row)
    layout = "; ".join(
        f"s{slot}:{_compress_rows(rows)}" for slot, rows in sorted(by_slot.items())
    )
    return f"{len(mission_list)} cells [{layout or '-'}]"


def _missions(series: Iterable[MissionSeries]) -> tuple[Mission, ...]:
    return tuple(mission for group in series for mission in group.missions)


def topology_shape(series: Iterable[MissionSeries]) -> tuple[int, int, int]:
    """Return cross-column edges, merge nodes and fork nodes."""

    missions = _missions(series)
    by_id = {mission.mission_id: mission for mission in missions}
    child_counts = {mission_id: 0 for mission_id in by_id}
    cross_column_edges = 0
    merge_nodes = 0
    for mission in missions:
        active_required = [item for item in mission.required if item in by_id]
        if len(active_required) >= 2:
            merge_nodes += 1
        for dependency in active_required:
            child_counts[dependency] += 1
            if by_id[dependency].slot != mission.slot:
                cross_column_edges += 1
    fork_nodes = sum(count >= 2 for count in child_counts.values())
    return cross_column_edges, merge_nodes, fork_nodes


def analyze_effective_topology(
    active_series: Iterable[MissionSeries],
    all_series: Iterable[MissionSeries],
    origin_for_source: Callable[[Path], str],
) -> tuple[tuple[TopologyProblem, ...], int]:
    """Validate one profile's active combined topology.

    The full catalog is used to distinguish an absent prerequisite from one
    whose defining mission series is inactive for the profile.
    """

    active_groups = tuple(active_series)
    catalog_groups = tuple(all_series)
    active_occurrences: dict[str, list[Mission]] = defaultdict(list)
    catalog_occurrences: dict[str, list[Mission]] = defaultdict(list)
    placements: list[tuple[int, int, str]] = []
    problems: list[TopologyProblem] = []

    active_series_by_slot: dict[int, list[MissionSeries]] = defaultdict(list)
    for series in active_groups:
        if series.slot is not None:
            active_series_by_slot[series.slot].append(series)
    for slot, groups in sorted(active_series_by_slot.items()):
        custom_groups = [group for group in groups if group.name.startswith("jxp_")]
        if custom_groups and len(groups) > 1:
            problems.append(
                TopologyProblem(
                    "effective.series_slot_overlap",
                    f"slot {slot} activates JXP alongside another mission series: "
                    + ", ".join(group.name for group in groups),
                )
            )

    for mission in _missions(catalog_groups):
        catalog_occurrences[mission.mission_id].append(mission)
    for mission in _missions(active_groups):
        active_occurrences[mission.mission_id].append(mission)
        if mission.slot is None or mission.slot not in range(1, 6):
            problems.append(
                TopologyProblem(
                    "effective.column_range",
                    f"active mission {mission.mission_id} uses column {mission.slot}; expected 1..5",
                    mission.source,
                    mission.line,
                )
            )
        if mission.slot is not None and mission.row is not None:
            origin = origin_for_source(mission.source)
            placements.append(
                (
                    mission.slot,
                    mission.row,
                    f"{mission.mission_id} [{origin}:{mission.series_name}]",
                )
            )

    for mission_id, occurrences in sorted(active_occurrences.items()):
        if len(occurrences) > 1:
            first = occurrences[0]
            for duplicate in occurrences[1:]:
                problems.append(
                    TopologyProblem(
                        "effective.duplicate_mission_id",
                        f"active mission id {mission_id} is also defined at "
                        f"{origin_for_source(first.source)}:{first.source.name}:{first.line}",
                        duplicate.source,
                        duplicate.line,
                    )
                )

    for (slot, row), labels in sorted(find_position_collisions(placements).items()):
        problems.append(
            TopologyProblem(
                "effective.cell_collision",
                f"effective collision at slot {slot}, row {row}: " + "; ".join(labels),
            )
        )

    active_unique = {
        mission_id: occurrences[0]
        for mission_id, occurrences in active_occurrences.items()
    }
    occupied = {
        (mission.slot, mission.row): mission
        for mission in active_unique.values()
        if mission.slot is not None and mission.row is not None
    }
    cross_source_edges = 0
    diagonal_edges: list[tuple[Mission, Mission]] = []
    for mission_id, mission in sorted(active_unique.items()):
        mission_origin = origin_for_source(mission.source)
        active_required = [
            dependency
            for dependency in mission.required
            if dependency in active_occurrences
        ]
        if len(active_required) > 3:
            problems.append(
                TopologyProblem(
                    "effective.parent_crowding",
                    f"active mission {mission_id} draws {len(active_required)} prerequisite "
                    "lines; vanilla Japanese missions draw at most 3",
                    mission.source,
                    mission.line,
                )
            )
        for dependency in mission.required:
            active_targets = active_occurrences.get(dependency, [])
            if not active_targets:
                catalog_targets = catalog_occurrences.get(dependency, [])
                if catalog_targets:
                    target_origins = sorted(
                        {origin_for_source(target.source) for target in catalog_targets}
                    )
                    cross_source = any(origin != mission_origin for origin in target_origins)
                    code = (
                        "effective.cross_source_prerequisite_inactive"
                        if cross_source
                        else "effective.prerequisite_inactive"
                    )
                    problems.append(
                        TopologyProblem(
                            code,
                            f"active mission {mission_id} requires inactive {dependency} "
                            f"from {', '.join(target_origins)} series",
                            mission.source,
                            mission.line,
                        )
                    )
                else:
                    problems.append(
                        TopologyProblem(
                            "effective.prerequisite_missing",
                            f"active mission {mission_id} requires {dependency}, which is absent "
                            "from the combined vanilla+mod catalog",
                            mission.source,
                            mission.line,
                        )
                    )
                continue

            target = active_targets[0]
            target_origin = origin_for_source(target.source)
            if mission_origin != target_origin:
                cross_source_edges += 1
            if (
                mission.row is not None
                and target.row is not None
                and mission.row <= target.row
            ):
                problems.append(
                    TopologyProblem(
                        "effective.edge_not_forward",
                        f"dependency edge {dependency} ({target_origin} row {target.row}) -> "
                        f"{mission_id} ({mission_origin} row {mission.row}) does not point to "
                        "a larger row",
                        mission.source,
                        mission.line,
                    )
                )
                continue
            if (
                mission.row is not None
                and target.row is not None
                and mission.slot is not None
                and target.slot is not None
            ):
                row_span = mission.row - target.row
                column_span = abs(mission.slot - target.slot)
                if row_span > 2:
                    problems.append(
                        TopologyProblem(
                            "effective.edge_row_span",
                            f"dependency edge {dependency} -> {mission_id} spans {row_span} "
                            "rows; pinned vanilla Japanese layouts use at most 2",
                            mission.source,
                            mission.line,
                        )
                    )
                if column_span > 1:
                    problems.append(
                        TopologyProblem(
                            "effective.edge_column_span",
                            f"dependency edge {dependency} -> {mission_id} spans "
                            f"{column_span} columns; pinned vanilla Japanese layouts use "
                            "adjacent columns only",
                            mission.source,
                            mission.line,
                        )
                    )
                if column_span == 1 and row_span != 1:
                    problems.append(
                        TopologyProblem(
                            "effective.edge_diagonal_span",
                            f"dependency edge {dependency} -> {mission_id} crosses an "
                            f"adjacent column but spans {row_span} rows; pinned vanilla "
                            "Japanese layouts only draw cross-column edges to the next row",
                            mission.source,
                            mission.line,
                        )
                    )
                if column_span == 0 and row_span == 2:
                    blocker = occupied.get((mission.slot, target.row + 1))
                    if blocker is not None:
                        problems.append(
                            TopologyProblem(
                                "effective.vertical_edge_occluded",
                                f"dependency edge {dependency} -> {mission_id} passes through "
                                f"occupied cell {blocker.mission_id}",
                                mission.source,
                                mission.line,
                            )
                        )
                if column_span == 1 and row_span == 1:
                    diagonal_edges.append((target, mission))

    for index, (first_parent, first_child) in enumerate(diagonal_edges):
        first_nodes = {first_parent.mission_id, first_child.mission_id}
        first_left_slot = min(first_parent.slot, first_child.slot)
        if first_parent.slot < first_child.slot:
            first_left_row, first_right_row = first_parent.row, first_child.row
        else:
            first_left_row, first_right_row = first_child.row, first_parent.row
        for second_parent, second_child in diagonal_edges[index + 1 :]:
            if first_nodes & {second_parent.mission_id, second_child.mission_id}:
                continue
            second_left_slot = min(second_parent.slot, second_child.slot)
            if first_left_slot != second_left_slot:
                continue
            if second_parent.slot < second_child.slot:
                second_left_row, second_right_row = second_parent.row, second_child.row
            else:
                second_left_row, second_right_row = second_child.row, second_parent.row
            if (
                (first_left_row - second_left_row)
                * (first_right_row - second_right_row)
                < 0
            ):
                problems.append(
                    TopologyProblem(
                        "effective.diagonal_crossing",
                        f"visible edges {first_parent.mission_id} -> {first_child.mission_id} "
                        f"and {second_parent.mission_id} -> {second_child.mission_id} cross",
                        first_child.source,
                        first_child.line,
                    )
                )

    for cycle in find_dependency_cycles(active_unique):
        first = active_unique[cycle[0]]
        problems.append(
            TopologyProblem(
                "effective.dependency_cycle",
                "effective dependency cycle: " + " -> ".join(cycle),
                first.source,
                first.line,
            )
        )
    return tuple(problems), cross_source_edges


def _merge_parse_issues(
    destination: CheckResult,
    source_result: CheckResult,
    prefix: str,
) -> None:
    for issue in source_result.issues:
        source = f"{prefix}:{issue.source}" if issue.source else prefix
        destination.issues.append(Issue(issue.code, issue.message, source, issue.line))


def _direct_jap_foundation(series: MissionSeries) -> bool:
    potential = series.potential
    if potential is None or not series.missions:
        return False
    direct_jap = any(
        entry.key == "tag"
        and isinstance(entry.value, Scalar)
        and entry.value.text == "JAP"
        for entry in potential.entries
    )
    rows = [mission.row for mission in series.missions if mission.row is not None]
    return direct_jap and bool(rows) and min(rows) >= 1 and max(rows) <= 8


def _object_contains_key(obj: Object | None, key: str) -> bool:
    if obj is None:
        return False
    for entry in obj.entries:
        if entry.key == key:
            return True
        if isinstance(entry.value, Object) and _object_contains_key(entry.value, key):
            return True
    return False


def _active_series(
    series_list: Iterable[MissionSeries],
    profile: Profile,
) -> tuple[tuple[MissionSeries, ...], tuple[tuple[MissionSeries, object], ...]]:
    active: list[MissionSeries] = []
    unknown: list[tuple[MissionSeries, object]] = []
    for series in series_list:
        if series.generic:
            continue
        possible, predicates = evaluate_potential(series.potential, profile)
        load_possible, load_predicates = evaluate_potential(
            series.potential_on_load,
            profile,
        )
        if True in possible and True in load_possible:
            unknown.extend((series, predicate) for predicate in predicates)
            unknown.extend((series, predicate) for predicate in load_predicates)
            active.append(series)
    return tuple(active), tuple(unknown)


def _active_generic_series(
    series_list: Iterable[MissionSeries],
    profile: Profile,
    occupied_slots: set[int],
) -> tuple[tuple[MissionSeries, ...], tuple[tuple[MissionSeries, object], ...]]:
    """Select vanilla generic fallback series for slots without a custom tree."""

    active: list[MissionSeries] = []
    unknown: list[tuple[MissionSeries, object]] = []
    for series in series_list:
        if not series.generic or series.slot in occupied_slots:
            continue
        possible, predicates = evaluate_potential(series.potential, profile)
        load_possible, load_predicates = evaluate_potential(
            series.potential_on_load,
            profile,
        )
        if True in possible and True in load_possible:
            unknown.extend((series, predicate) for predicate in predicates)
            unknown.extend((series, predicate) for predicate in load_predicates)
            active.append(series)
    return tuple(active), tuple(unknown)


def check_effective_topology(
    mod_context: ValidationContext,
    game_root: Path,
) -> CheckResult:
    result = CheckResult("Effective EU4 1.37.5 mission topology")
    game_root = game_root.resolve()
    manifest_relative = "tools/jxp_validation/vanilla_1_37_5_manifest.json"
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result.add("effective.manifest", f"cannot read pinned manifest: {exc}", manifest_relative)
        result.summary = "pinned vanilla manifest unavailable"
        return result

    pinned_version = str(manifest.get("eu4_raw_version", ""))
    launcher_path = game_root / "launcher-settings.json"
    actual_version: str | None = None
    if not launcher_path.is_file():
        result.add(
            "effective.game_version_file",
            "launcher-settings.json is missing",
            str(launcher_path),
        )
    else:
        try:
            launcher = json.loads(launcher_path.read_text(encoding="utf-8-sig"))
            actual_version = launcher.get("rawVersion")
        except (OSError, json.JSONDecodeError) as exc:
            result.add(
                "effective.game_version_file",
                f"cannot read launcher-settings.json: {exc}",
                str(launcher_path),
            )
    if actual_version != pinned_version:
        result.add(
            "effective.game_version",
            f"game rawVersion is {actual_version!r}; pinned topology requires {pinned_version!r}",
            str(launcher_path),
        )

    vanilla_sources: list[Path] = []
    effective_vanilla_sources: list[Path] = []
    generic_sources: list[Path] = []
    override_names: set[str] = set()
    manifest_files = manifest.get("files", [])
    if not isinstance(manifest_files, list) or not manifest_files:
        result.add("effective.manifest_files", "pinned manifest has no files", manifest_relative)
    else:
        for item in manifest_files:
            if not isinstance(item, dict):
                result.add(
                    "effective.manifest_entry",
                    "pinned manifest file entry is not an object",
                    manifest_relative,
                )
                continue
            relative = str(item.get("path", ""))
            expected_hash = str(item.get("sha256", "")).casefold()
            source = game_root.joinpath(*Path(relative).parts)
            vanilla_sources.append(source)
            override = mod_context.mod_root / "missions" / source.name
            override_names.add(source.name)
            if not override.is_file():
                result.add(
                    "effective.override_missing",
                    f"pinned JXP mission override is missing for {source.name}",
                    f"mod:missions/{source.name}",
                )
                effective_vanilla_sources.append(source)
            else:
                effective_vanilla_sources.append(override)
            if not source.is_file():
                result.add(
                    "effective.vanilla_file_missing",
                    f"pinned vanilla mission file is missing: {relative}",
                    str(source),
                )
                continue
            actual_hash = _sha256(source)
            if actual_hash != expected_hash:
                result.add(
                    "effective.vanilla_hash",
                    f"SHA256 {actual_hash} does not match pinned {expected_hash}",
                    f"vanilla:{relative}",
                )
            if override.is_file():
                source_text = source.read_text(encoding="utf-8-sig")
                expected_override, _ = patch_potentials(source_text, source.name)
                override_text = override.read_text(encoding="utf-8-sig")
                if override_text != expected_override:
                    result.add(
                        "effective.override_drift",
                        f"{source.name} differs from the pinned vanilla source beyond "
                        "the generated JXP preload disable and potential exclusion",
                        f"mod:missions/{source.name}",
                    )

    generic_manifest_files = manifest.get("generic_files", [])
    generic_manifest_names = {
        Path(str(item.get("path", ""))).name
        for item in generic_manifest_files
        if isinstance(item, dict)
    }
    if generic_manifest_names != set(GENERIC_MISSION_FILES):
        result.add(
            "effective.generic_manifest_files",
            "pinned generic mission manifest must contain exactly: "
            + ", ".join(GENERIC_MISSION_FILES),
            manifest_relative,
        )
    for item in generic_manifest_files:
        if not isinstance(item, dict):
            result.add(
                "effective.generic_manifest_entry",
                "pinned generic mission entry is not an object",
                manifest_relative,
            )
            continue
        relative = str(item.get("path", ""))
        source = game_root.joinpath(*Path(relative).parts)
        generic_sources.append(source)
        if not source.is_file():
            result.add(
                "effective.generic_file_missing",
                f"pinned generic mission file is missing: {relative}",
                str(source),
            )
            continue
        actual_hash = _sha256(source)
        expected_hash = str(item.get("sha256", "")).casefold()
        if actual_hash != expected_hash:
            result.add(
                "effective.generic_hash",
                f"SHA256 {actual_hash} does not match pinned {expected_hash}",
                f"vanilla:{relative}",
            )

    vanilla_context = ValidationContext(game_root)
    vanilla_parse = CheckResult("effective vanilla override parse")
    vanilla_series = extract_mission_series(
        vanilla_context,
        vanilla_parse,
        (source for source in effective_vanilla_sources if source.is_file()),
        infer_implicit_positions=True,
    )
    _merge_parse_issues(result, vanilla_parse, "override")
    for source in effective_vanilla_sources:
        message = vanilla_context.parse_errors.get(source.resolve())
        if message:
            result.add(
                "effective.override_parse",
                message,
                f"override:{source.name}",
            )

    generic_parse = CheckResult("effective generic mission parse")
    generic_series = extract_mission_series(
        vanilla_context,
        generic_parse,
        (source for source in generic_sources if source.is_file()),
        infer_implicit_positions=True,
    )
    _merge_parse_issues(result, generic_parse, "generic")
    for series in generic_series:
        if not series.generic:
            result.add(
                "effective.generic_series_marker",
                f"pinned fallback series {series.name} is not marked generic = yes",
                f"vanilla:{vanilla_context.relative(series.source)}",
                series.line,
            )

    for series in vanilla_series:
        if series.source.name not in override_names:
            continue
        if series.name.startswith("jxp_disabled_vanilla_"):
            result.add(
                "effective.override_legacy_key",
                f"override series {series.name} renames its vanilla save key; "
                "old saves cannot reconcile that serialized series during a mission swap",
                f"mod:missions/{series.source.name}",
                series.line,
            )
        if not _object_contains_key(series.potential, "jxp_use_custom_missions_trigger"):
            result.add(
                "effective.override_guard_missing",
                f"override series {series.name} does not exclude JXP custom missions in potential",
                f"mod:missions/{series.source.name}",
                series.line,
            )
        if series.potential is None or first_scalar(series.potential, "always") != "no":
            result.add(
                "effective.override_potential_not_disabled",
                f"override series {series.name} is not unconditionally disabled in potential",
                f"mod:missions/{series.source.name}",
                series.line,
            )
        if series.potential_on_load is None or first_scalar(
            series.potential_on_load,
            "always",
        ) != "no":
            result.add(
                "effective.override_preload_not_disabled",
                f"override series {series.name} is not unconditionally disabled in potential_on_load",
                f"mod:missions/{series.source.name}",
                series.line,
            )

    mod_mission_root = mod_context.mod_root / "missions"
    mod_parse = CheckResult("mod mission parse")
    mod_series = extract_mission_series(
        mod_context,
        mod_parse,
        (
            path
            for path in mod_mission_root.glob("*.txt")
            if path.name not in override_names
            and not path.name.startswith(LEGACY_BOM_FILE_PREFIX)
        )
        if mod_mission_root.is_dir()
        else (),
    )
    _merge_parse_issues(result, mod_parse, "mod")

    all_series = tuple(vanilla_series) + tuple(generic_series) + tuple(mod_series)
    mod_mission_occurrences: dict[str, list[Mission]] = defaultdict(list)
    for series in mod_series:
        for mission in series.missions:
            mod_mission_occurrences[mission.mission_id].append(mission)
    for mission_id in sorted(FOUNDATION_MISSIONS):
        occurrences = mod_mission_occurrences.get(mission_id, [])
        if len(occurrences) != 1:
            result.add(
                "effective.foundation_definition",
                f"consolidated foundation mission {mission_id} has "
                f"{len(occurrences)} definitions; expected exactly one",
            )
            continue
        if occurrences[0].series_name not in {
            "jxp_japan_state_missions",
            "jxp_japan_court_missions",
        }:
            result.add(
                "effective.foundation_series",
                f"foundation mission {mission_id} remains in separate series "
                f"{occurrences[0].series_name}; expected consolidated state/court series",
                f"mod:{mod_context.relative(occurrences[0].source)}",
                occurrences[0].line,
            )

    jap_only_foundations = tuple(
        series for series in vanilla_series if _direct_jap_foundation(series)
    )
    if not jap_only_foundations:
        result.add(
            "effective.vanilla_foundations_missing",
            "no direct JAP-only vanilla foundation groups were derived from pinned potentials",
            "vanilla:missions/DOM_Japanese_Missions.txt",
        )

    def origin_for_source(source: Path) -> str:
        try:
            source.resolve().relative_to(mod_context.mod_root)
            return "override" if source.name in override_names else "mod"
        except ValueError:
            return "vanilla"

    def display_source(source: Path) -> str:
        origin = origin_for_source(source)
        context = mod_context if origin in {"mod", "override"} else vanilla_context
        return f"{origin}:{context.relative(source)}"

    unknown_seen: set[tuple[str, str, int, str]] = set()
    total_cross_source_edges = 0
    route_profiles = tuple(profile for profile in PROFILES if profile.tag in ROUTE_TAGS)
    jap_profiles = tuple(profile for profile in PROFILES if profile.tag == "JAP")
    buddhist_profiles = tuple(
        profile
        for profile in jap_profiles
        if "jxp_path_buddhist" in profile.flags
    )

    for profile in PROFILES:
        active_vanilla, vanilla_unknown = _active_series(vanilla_series, profile)
        active_mod, mod_unknown = _active_series(mod_series, profile)
        occupied_non_generic_slots = {
            series.slot
            for series in active_vanilla + active_mod
            if series.slot is not None
        }
        active_generic, generic_unknown = _active_generic_series(
            generic_series,
            profile,
            occupied_non_generic_slots,
        )

        if active_generic:
            result.add(
                "effective.generic_fallback_active",
                f"profile {profile.name} still receives generic fallback mission "
                "series: " + ", ".join(series.name for series in active_generic),
            )
        for series, predicate in vanilla_unknown + mod_unknown + generic_unknown:
            key = (str(series.source), series.name, predicate.line, predicate.key)
            if key in unknown_seen:
                continue
            unknown_seen.add(key)
            result.add(
                "effective.profile_predicate_unknown",
                f"series {series.name} uses unsupported predicate {predicate.key}: "
                f"{predicate.reason}",
                display_source(series.source),
                predicate.line,
            )

        if active_vanilla:
            result.add(
                "effective.base_tree_active",
                f"profile {profile.name} still activates overridden Japanese mission "
                "series: " + ", ".join(series.name for series in active_vanilla),
            )

        active_mod_names = {series.name for series in active_mod}
        if profile in buddhist_profiles:
            missing_buddhist = sorted(BUDDHIST_REPLACEMENT_SERIES - active_mod_names)
            forbidden_continuity = sorted(
                UNIFIED_CONTINUITY_SERIES & active_mod_names
            )
            if missing_buddhist:
                result.add(
                    "effective.buddhist_replacement_incomplete",
                    f"profile {profile.name} lacks Buddhist replacement columns: "
                    + ", ".join(missing_buddhist),
                )
            if forbidden_continuity:
                result.add(
                    "effective.buddhist_shared_continuity_active",
                    f"profile {profile.name} activates shared columns alongside its "
                    "five-column Buddhist replacement: "
                    + ", ".join(forbidden_continuity),
                )
        elif not profile.daimyo_stage:
            missing_continuity = sorted(UNIFIED_CONTINUITY_SERIES - active_mod_names)
            if missing_continuity:
                result.add(
                    "effective.unified_continuity_missing",
                    f"profile {profile.name} loses shared completed-mission columns: "
                    + ", ".join(missing_continuity),
                )

        active_mod_rows = [
            mission.row
            for series in active_mod
            for mission in series.missions
            if mission.row is not None
        ]
        if active_mod_rows and min(active_mod_rows) != 1:
            result.add(
                "effective.custom_tree_top_gap",
                f"profile {profile.name} starts its custom tree at row "
                f"{min(active_mod_rows)} instead of row 1",
            )

        active_combined = tuple(active_vanilla) + tuple(active_mod) + tuple(active_generic)
        problems, cross_source_edges = analyze_effective_topology(
            active_combined,
            all_series,
            origin_for_source,
        )
        total_cross_source_edges += cross_source_edges
        for problem in problems:
            result.add(
                problem.code,
                f"profile {profile.name}: {problem.message}",
                display_source(problem.source) if problem.source is not None else None,
                problem.line,
            )

        cross_columns, merge_nodes, fork_nodes = topology_shape(active_mod)

        active_foundation = {
            mission.mission_id
            for series in active_mod
            for mission in series.missions
            if mission.mission_id in FOUNDATION_MISSIONS
        }
        if profile in route_profiles:
            active_jap_foundations = [
                series.name
                for series in jap_only_foundations
                if True in evaluate_potential(series.potential, profile)[0]
            ]
            if active_jap_foundations:
                result.add(
                    "effective.route_jap_foundation_active",
                    f"route tag {profile.tag} activates JAP-only vanilla foundations: "
                    + ", ".join(active_jap_foundations),
                )
            if active_foundation != FOUNDATION_MISSIONS:
                result.add(
                    "effective.route_foundation_incomplete",
                    f"route tag {profile.tag} activates consolidated foundation missions "
                    f"{sorted(active_foundation)}; expected {sorted(FOUNDATION_MISSIONS)}",
                )
        elif profile in jap_profiles and profile not in buddhist_profiles:
            if active_foundation != FOUNDATION_MISSIONS:
                result.add(
                    "effective.jap_foundation_incomplete",
                    f"profile {profile.name} does not activate every consolidated "
                    "foundation mission",
                )
        elif profile.daimyo_stage and active_foundation:
            result.add(
                "effective.daimyo_foundation_active",
                f"daimyo profile {profile.name} activates unified foundation missions",
            )

        result.notes.append(
            f"{profile.name}: overridden base {summarize_cells(_missions(active_vanilla))}; "
            f"mod {summarize_cells(_missions(active_mod))}; generic fallback "
            f"{summarize_cells(_missions(active_generic))}; shape "
            f"{cross_columns} cross-column / {merge_nodes} merges / {fork_nodes} forks"
        )

    result.metrics.update(
        {
            "pinned_version": pinned_version,
            "actual_version": actual_version,
            "pinned_vanilla_files": len(vanilla_sources),
            "mission_override_files": len(
                [source for source in effective_vanilla_sources if source.parent == mod_mission_root]
            ),
            "vanilla_series": len(vanilla_series),
            "generic_files": len(generic_sources),
            "generic_series": len(generic_series),
            "mod_series": len(mod_series),
            "profiles": len(PROFILES),
            "route_profiles": len(route_profiles),
            "vanilla_jap_foundation_groups": len(jap_only_foundations),
            "consolidated_foundation_missions": len(FOUNDATION_MISSIONS),
            "cross_source_edges": total_cross_source_edges,
            "continuity_series": len(UNIFIED_CONTINUITY_SERIES),
            "buddhist_replacement_series": len(BUDDHIST_REPLACEMENT_SERIES),
        }
    )
    result.summary = (
        f"{len(effective_vanilla_sources)} tombstoned pinned mission overrides + "
        f"{len(generic_sources)} pinned generic fallback files + "
        f"{len(mod_series)} custom series; "
        f"{len(PROFILES)} effective profiles"
    )
    return result
