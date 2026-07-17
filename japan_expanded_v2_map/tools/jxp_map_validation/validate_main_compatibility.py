#!/usr/bin/env python3
"""Validate the effective main-mod plus companion-map gameplay contract."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .gameplay_text import read_gameplay_text
except ImportError:  # pragma: no cover - direct script entry point
    from gameplay_text import read_gameplay_text


MAP_ROOT = SCRIPT_DIR.parents[1]
CONTRACT_PATH = SCRIPT_DIR / "main_compatibility_contract.json"
HISTORY_PLAN_PATH = MAP_ROOT / "tools" / "jxp_map_builder" / "history_plan.json"
PROVINCE_PLAN_PATH = MAP_ROOT / "tools" / "jxp_map_builder" / "province_plan.json"
ACTIVE_ROOTS = (
    "events",
    "missions",
    "decisions",
    "common/scripted_effects",
    "common/scripted_triggers",
    "common/disasters",
    "common/on_actions",
)
PINNED_OVERRIDE_NAMES = {"Japanese_Missions.txt", "DOM_Japanese_Missions.txt"}
LEGACY_BOM_PREFIX = "jxp_00_legacy_bom_"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def emit(self) -> int:
        for message in self.notes:
            print(f"NOTE: {message}")
        for message in self.errors:
            print(f"ERROR: {message}")
        print(f"SUMMARY: {len(self.errors)} error(s), 0 warning(s)")
        return 1 if self.errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--main-mod", type=Path, required=True)
    return parser.parse_args()


def read_text(path: Path) -> str:
    return read_gameplay_text(path)


def extract_block(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        return None
    cursor = match.end() - 1
    depth = 0
    in_quote = False
    escaped = False
    while cursor < len(text):
        char = text[cursor]
        if escaped:
            escaped = False
        elif char == "\\" and in_quote:
            escaped = True
        elif char == '"':
            in_quote = not in_quote
        elif not in_quote and char == "#":
            newline = text.find("\n", cursor)
            cursor = len(text) if newline < 0 else newline
            continue
        elif not in_quote and char == "{":
            depth += 1
        elif not in_quote and char == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : cursor + 1]
        cursor += 1
    return None


def gameplay_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for relative in ACTIVE_ROOTS:
        directory = root.joinpath(*relative.split("/"))
        if directory.is_dir():
            files.extend(directory.rglob("*.txt"))
    return tuple(
        sorted(
            (
                path
                for path in files
                if path.name not in PINNED_OVERRIDE_NAMES
                and not path.name.startswith(LEGACY_BOM_PREFIX)
            ),
            key=lambda path: str(path).casefold(),
        )
    )


def duplicate_items(values: dict[str, list[str]]) -> dict[str, list[str]]:
    return {key: sources for key, sources in values.items() if len(sources) > 1}


def main() -> int:
    args = parse_args()
    game_root = args.game_root.resolve()
    main_mod = args.main_mod.resolve()
    report = Report()

    sys.path.insert(0, str(main_mod / "tools"))
    from jxp_validation.clausewitz import (  # type: ignore[import-not-found]
        Object,
        Scalar,
        bare_scalars,
        entries_named,
        find_assignments,
        first_object,
        first_scalar,
        parse_file,
        parse_text,
        walk_entries,
    )
    from jxp_validation.core import (  # type: ignore[import-not-found]
        CheckResult,
        ValidationContext,
    )
    from jxp_validation.daimyo_coverage import (  # type: ignore[import-not-found]
        collect_idea_identities,
    )
    from jxp_validation.effective_topology import (  # type: ignore[import-not-found]
        analyze_effective_topology,
    )
    from jxp_validation.missions import (  # type: ignore[import-not-found]
        MissionSeries,
        Profile,
        evaluate_potential,
        extract_mission_series,
    )

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    history_plan = json.loads(HISTORY_PLAN_PATH.read_text(encoding="utf-8"))
    province_plan = json.loads(PROVINCE_PLAN_PATH.read_text(encoding="utf-8"))
    depth_plan = json.loads(
        (
            main_mod
            / "tools"
            / "jxp_a_content_builder"
            / "daimyo_depth_plan.json"
        ).read_text(encoding="utf-8")
    )
    tags = {country["tag"] for country in history_plan["countries"]}
    country_by_tag = {country["tag"]: country for country in history_plan["countries"]}
    map_depth_by_tag = {
        record["tag"]: record
        for record in depth_plan["daimyo"]
        if record["surface"] == "map"
    }
    if set(map_depth_by_tag) != tags:
        report.error(
            "Map daimyo depth-plan coverage differs from history plan: "
            f"missing={sorted(tags - set(map_depth_by_tag))}, "
            f"extra={sorted(set(map_depth_by_tag) - tags)}"
        )

    group_for_tag: dict[str, str] = {}
    for group_name, group in contract["groups"].items():
        for tag in group["tags"]:
            if tag in group_for_tag:
                report.error(f"Compatibility contract assigns {tag} to multiple groups")
            group_for_tag[tag] = group_name
    if set(group_for_tag) != tags:
        report.error(
            "Compatibility group coverage differs from history plan: "
            f"missing={sorted(tags - set(group_for_tag))}, extra={sorted(set(group_for_tag) - tags)}"
        )

    external_tag_catalog: set[str] = set()
    for tag_root in (game_root / "common" / "country_tags", main_mod / "common" / "country_tags"):
        if not tag_root.is_dir():
            continue
        for source in tag_root.glob("*.txt"):
            external_tag_catalog.update(
                re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*=", read_text(source))
            )
    conflicting_tags = tags & external_tag_catalog
    if conflicting_tags:
        report.error(
            f"Companion country tags collide with vanilla/main registrations: {sorted(conflicting_tags)}"
        )

    # Validate all primary cultures against the pinned game catalog.
    culture_catalog: set[str] = set()
    culture_root = game_root / "common" / "cultures"
    for source in culture_root.glob("*.txt"):
        document = parse_file(source)
        for group_entry in document.root.entries:
            if group_entry.key is None or not isinstance(group_entry.value, Object):
                continue
            culture_catalog.update(
                entry.key
                for entry in group_entry.value.entries
                if entry.key is not None and isinstance(entry.value, Object)
            )
    invalid_cultures = {
        tag: country_by_tag[tag]["culture"]
        for tag in sorted(tags)
        if country_by_tag[tag]["culture"] not in culture_catalog
    }
    if invalid_cultures:
        report.error(f"Map country history uses unknown culture keys: {invalid_cultures}")
    for tag, country in sorted(country_by_tag.items()):
        country_history = next((MAP_ROOT / "history" / "countries").glob(f"{tag} - *.txt"), None)
        if country_history is None:
            report.error(f"Missing generated country history for {tag}")
            continue
        expected = f"primary_culture = {country['culture']}"
        if expected not in read_text(country_history):
            report.error(f"Generated history for {tag} does not contain {expected}")

    main_context = ValidationContext(main_mod)
    map_context = ValidationContext(MAP_ROOT)
    main_sources = tuple(
        path
        for path in (main_mod / "missions").glob("*.txt")
        if path.name not in PINNED_OVERRIDE_NAMES
        and not path.name.startswith(LEGACY_BOM_PREFIX)
    )
    map_sources = tuple((MAP_ROOT / "missions").glob("*.txt"))
    main_parse = CheckResult("main mission parse")
    map_parse = CheckResult("map mission parse")
    main_series = extract_mission_series(main_context, main_parse, main_sources)
    map_series = extract_mission_series(map_context, map_parse, map_sources)
    for issue in main_parse.issues + map_parse.issues:
        report.error(
            f"Mission parse contract failed: {issue.code}: {issue.message}"
            + (f" ({issue.source}:{issue.line})" if issue.source else "")
        )
    all_series = tuple(main_series) + tuple(map_series)

    series_occurrences: dict[str, list[str]] = defaultdict(list)
    mission_occurrences: dict[str, list[str]] = defaultdict(list)
    for series in all_series:
        origin = "main" if series.source.is_relative_to(main_mod) else "map"
        series_occurrences[series.name].append(f"{origin}:{series.source.name}:{series.line}")
        for mission in series.missions:
            mission_occurrences[mission.mission_id].append(
                f"{origin}:{mission.source.name}:{mission.line}"
            )
    if duplicates := duplicate_items(series_occurrences):
        report.error(f"Combined mission series IDs collide: {duplicates}")
    if duplicates := duplicate_items(mission_occurrences):
        report.error(f"Combined mission IDs collide: {duplicates}")

    combined_localisation_keys: set[str] = set()
    for root in (main_mod, MAP_ROOT):
        for directory_name in ("localisation_source", "localisation"):
            directory = root / directory_name
            if not directory.is_dir():
                continue
            for source in directory.rglob("*.yml"):
                combined_localisation_keys.update(
                    re.findall(
                        r"(?m)^\s*([A-Za-z0-9_.-]+):\d+\s",
                        read_text(source),
                    )
                )
    missing_mission_localisation = sorted(
        key
        for mission_id in mission_occurrences
        for key in (mission_id + "_title", mission_id + "_desc")
        if key not in combined_localisation_keys
    )
    if missing_mission_localisation:
        report.error(
            "Combined missions lack canonical title/description localisation: "
            + ", ".join(missing_mission_localisation)
        )

    trigger_dependencies: dict[tuple[str, str], set[str]] = defaultdict(set)
    for context, catalog in ((main_context, main_series), (map_context, map_series)):
        for series in catalog:
            document = context.document(series.source)
            if document is None:
                continue
            series_entry = next(
                (
                    entry
                    for entry in document.root.entries
                    if entry.key == series.name and isinstance(entry.value, Object)
                ),
                None,
            )
            if series_entry is None or not isinstance(series_entry.value, Object):
                continue
            for mission_entry in series_entry.value.entries:
                if mission_entry.key is None or not isinstance(mission_entry.value, Object):
                    continue
                trigger = first_object(mission_entry.value, "trigger")
                if trigger is None:
                    continue
                for _path, dependency in find_assignments(
                    trigger, "mission_completed"
                ):
                    if isinstance(dependency.value, Scalar):
                        trigger_dependencies[(series.name, mission_entry.key)].add(
                            dependency.value.text
                        )

    dlc_variants = (
        frozenset({"Domination", "Mandate of Heaven"}),
        frozenset({"Domination"}),
        frozenset({"Mandate of Heaven"}),
        frozenset(),
    )
    expected_main = {int(slot): name for slot, name in contract["shared_main_series"].items()}
    exact_identity_series = contract.get("exact_identity_series", {})
    unknown_exact_tags = sorted(set(exact_identity_series) - tags)
    if unknown_exact_tags:
        report.error(
            "Exact identity mission contract references unknown map tags: "
            + ", ".join(unknown_exact_tags)
        )
    if len(set(exact_identity_series.values())) != len(exact_identity_series):
        report.error("Exact identity mission contract reuses a series across multiple tags")
    map_series_by_name = {series.name: series for series in map_series}
    for tag, series_name in sorted(exact_identity_series.items()):
        series = map_series_by_name.get(series_name)
        if series is None:
            report.error(f"Exact identity mission series for {tag} is absent: {series_name}")
        elif len(series.missions) != 8:
            report.error(
                f"Exact identity mission series for {tag} has {len(series.missions)} missions; expected 8"
            )
    checked_profiles = 0

    def origin_for_source(source: Path) -> str:
        return "main" if source.resolve().is_relative_to(main_mod) else "map"

    for tag in sorted(tags):
        group = contract["groups"][group_for_tag[tag]]
        expected_by_slot = dict(expected_main)
        expected_by_slot[3] = exact_identity_series.get(tag, group["map_series"])
        tier_slots = {"S": (2, 4), "A": (4,), "B": (3,)}
        tier = map_depth_by_tag.get(tag, {}).get("tier")
        if tier not in tier_slots:
            report.error(f"Map daimyo {tag} has unsupported depth tier {tier!r}")
        else:
            for slot in tier_slots[tier]:
                expected_by_slot[slot] = (
                    f"jxp_a_{tag.lower()}_depth_slot_{slot}_missions"
                )
        for dlcs in dlc_variants:
            checked_profiles += 1
            profile = Profile(
                name=f"map daimyo {tag} dlc={','.join(sorted(dlcs)) or 'none'}",
                tag=tag,
                religion="shinto",
                religion_group="eastern",
                reforms=frozenset({"daimyo"}),
                daimyo_stage=True,
                dlcs=dlcs,
            )
            active: list[MissionSeries] = []
            for series in all_series:
                if series.generic:
                    continue
                possible, unknown = evaluate_potential(series.potential, profile)
                load_possible, load_unknown = evaluate_potential(
                    series.potential_on_load, profile
                )
                for predicate in unknown + load_unknown:
                    report.error(
                        f"{profile.name}: unsupported potential predicate {predicate.key} "
                        f"in {series.name}: {predicate.reason}"
                    )
                if True in possible and True in load_possible:
                    active.append(series)

            by_slot: dict[int, list[MissionSeries]] = defaultdict(list)
            for series in active:
                if series.slot is not None:
                    by_slot[series.slot].append(series)
            actual_by_slot = {
                slot: groups[0].name
                for slot, groups in by_slot.items()
                if len(groups) == 1
            }
            if set(by_slot) != set(range(1, 6)) or any(
                len(groups) != 1 for groups in by_slot.values()
            ):
                report.error(
                    f"{profile.name}: effective non-generic slot owners are "
                    + str({slot: [group.name for group in groups] for slot, groups in by_slot.items()})
                )
            if actual_by_slot != expected_by_slot:
                report.error(
                    f"{profile.name}: slot signature {actual_by_slot}, expected {expected_by_slot}"
                )

            active_mission_ids = {
                mission.mission_id for series in active for mission in series.missions
            }
            for series in active:
                for mission in series.missions:
                    if mission.slot in range(1, 6) and mission.row is not None:
                        expected_parity = 1 if mission.slot % 2 else 0
                        if mission.row % 2 != expected_parity:
                            report.error(
                                f"{profile.name}: {mission.mission_id} uses slot {mission.slot}, "
                                f"row {mission.row}; canonical parity is violated"
                            )
                    for dependency in trigger_dependencies.get(
                        (series.name, mission.mission_id), set()
                    ):
                        if dependency not in active_mission_ids:
                            report.error(
                                f"{profile.name}: active mission {mission.mission_id} has inactive "
                                f"mission_completed gate {dependency}"
                            )

            problems, _cross_source_edges = analyze_effective_topology(
                active, all_series, origin_for_source
            )
            for problem in problems:
                report.error(f"{profile.name}: {problem.code}: {problem.message}")

    # Cross-mod ID and callable closure.
    def collect_top_level(directory: Path) -> dict[str, list[str]]:
        found: dict[str, list[str]] = defaultdict(list)
        if not directory.is_dir():
            return found
        context = main_context if directory.is_relative_to(main_mod) else map_context
        for source in directory.glob("*.txt"):
            document = context.document(source)
            if document is None:
                report.error(f"Cannot parse {source}")
                continue
            for entry in document.root.entries:
                if entry.key is not None and isinstance(entry.value, Object):
                    found[entry.key].append(str(source))
        return found

    callable_definitions: dict[str, list[str]] = defaultdict(list)
    for root in (main_mod, MAP_ROOT):
        for relative in ("common/scripted_triggers", "common/scripted_effects"):
            for key, sources in collect_top_level(root.joinpath(*relative.split("/"))).items():
                callable_definitions[key].extend(sources)
    if duplicates := duplicate_items(callable_definitions):
        report.error(f"Combined scripted trigger/effect IDs collide: {duplicates}")

    callable_names = set(callable_definitions)
    unresolved_calls: dict[str, set[str]] = defaultdict(set)
    for source in gameplay_files(MAP_ROOT):
        document = map_context.document(source)
        if document is None:
            continue
        for path, entry in walk_entries(document.root):
            if (
                path
                and entry.key is not None
                and entry.key.startswith("jxp_")
                and isinstance(entry.value, Scalar)
                and entry.value.text in {"yes", "no"}
                and entry.key not in callable_names
            ):
                unresolved_calls[entry.key].add(str(source.relative_to(MAP_ROOT)))
    if unresolved_calls:
        report.error(
            "Companion calls undefined main/map scripted symbols: "
            + str({key: sorted(value) for key, value in unresolved_calls.items()})
        )

    main_text_by_file = {
        source: read_text(source) for source in gameplay_files(main_mod)
    }
    tag_pattern = re.compile(
        r"\btag\s*=\s*(" + "|".join(sorted(tags)) + r")\b"
    )
    unsafe_tag_refs = [
        str(source.relative_to(main_mod))
        for source, text in main_text_by_file.items()
        if tag_pattern.search(text)
    ]
    if unsafe_tag_refs:
        report.error(
            "Standalone main mod directly references optional map tags: "
            + ", ".join(unsafe_tag_refs)
        )

    main_house_text = read_text(
        main_mod / "common" / "scripted_triggers" / "jxp_22_house_ordinance_triggers.txt"
    )
    map_trigger_text = read_text(
        MAP_ROOT / "common" / "scripted_triggers" / "jxp_map_triggers.txt"
    )
    for group_name, group in contract["groups"].items():
        expected_flags = {f"jxp_map_origin_{tag.lower()}" for tag in group["tags"]}
        for label, text, trigger_name in (
            ("main", main_house_text, group["main_origin_trigger"]),
            ("map", map_trigger_text, group["map_origin_trigger"]),
        ):
            block = extract_block(text, trigger_name) or ""
            actual_flags = set(re.findall(r"has_country_flag\s*=\s*(jxp_map_origin_[a-z0-9]+)", block))
            if actual_flags != expected_flags:
                report.error(
                    f"{label} {group_name} origin contract is {sorted(actual_flags)}, "
                    f"expected {sorted(expected_flags)}"
                )

    major_origin_text = extract_block(
        read_text(
            main_mod
            / "common"
            / "scripted_triggers"
            / "jxp_04_daimyo_triggers.txt"
        ),
        "jxp_has_major_daimyo_origin_trigger",
    ) or ""
    if "jxp_map_origin_" in major_origin_text:
        report.error(
            "Optional map origins entered jxp_has_major_daimyo_origin_trigger; "
            "this would suppress the generic founder-reform fallback"
        )
    generic_founder_text = extract_block(
        read_text(
            main_mod
            / "common"
            / "government_reforms"
            / "jxp_28_founder_house_reforms.txt"
        ),
        "jxp_reform_founder_generic_renovated_japan",
    ) or ""
    for token in (
        "jxp_is_unified_japan_state_trigger = yes",
        "NOT = { jxp_has_major_daimyo_origin_trigger = yes }",
    ):
        if token not in generic_founder_text:
            report.error(f"Map-origin founder-reform fallback is missing token: {token}")

    runtime_text = read_text(
        main_mod / "common" / "scripted_triggers" / "jxp_60_mission_runtime_triggers.txt"
    )
    required_runtime_tokens = (
        "jxp_has_companion_map_origin_trigger = yes",
        "jxp_has_maritime_house_origin_trigger = yes",
        "NOT = { jxp_has_companion_map_origin_trigger = yes }",
    )
    for token in required_runtime_tokens:
        if token not in runtime_text:
            report.error(f"Main runtime fingerprint is missing companion token: {token}")
    for token in (
        "jxp_map_daimyo_mission_fingerprint_valid_trigger",
        "jxp_map_daimyo_mission_tree_needs_reconcile_trigger",
    ):
        if token not in map_trigger_text:
            report.error(f"Companion runtime fingerprint is missing {token}")
    map_effect_text = read_text(
        MAP_ROOT / "common" / "scripted_effects" / "jxp_map_effects.txt"
    )
    map_event_text = read_text(MAP_ROOT / "events" / "jxp_map_events.txt")
    map_on_action_text = read_text(
        MAP_ROOT / "common" / "on_actions" / "jxp_map_on_actions.txt"
    )
    if "jxp_map_initialize_geography_contract_effect = yes" not in map_on_action_text:
        report.error("Companion on_startup does not initialize the geography contract")
    for token in (
        "jxp_map_runtime_migration_v011",
        "jxp_map_reconcile_daimyo_missions_effect = yes",
        "jxp_refresh_route_missions_effect = yes",
    ):
        if token not in map_effect_text + map_event_text:
            report.error(f"Companion runtime migration/repair is missing {token}")

    map_event_document = map_context.document(MAP_ROOT / "events" / "jxp_map_events.txt")
    legacy_dispatch_keys: list[str] = []
    if map_event_document is not None:
        for event_entry in map_event_document.root.entries:
            if event_entry.key != "country_event" or not isinstance(event_entry.value, Object):
                continue
            if first_scalar(event_entry.value, "id") != "jxp_map.100":
                continue
            immediate = first_object(event_entry.value, "immediate")
            if immediate is not None:
                legacy_dispatch_keys = [
                    entry.key or "<bare>"
                    for entry in immediate.entries
                    if entry.key in {"if", "else_if"}
                ]
    if legacy_dispatch_keys != ["if", "else_if", "else_if", "else_if", "else_if"]:
        report.error(
            "Map legacy dispatch must be one deterministic if/else_if chain; got "
            + str(legacy_dispatch_keys)
        )

    # Event, decision, modifier, and idea ownership must remain disjoint.
    event_ids: dict[str, list[str]] = defaultdict(list)
    decision_ids: dict[str, list[str]] = defaultdict(list)
    modifier_ids: dict[str, list[str]] = defaultdict(list)
    for root, context in ((main_mod, main_context), (MAP_ROOT, map_context)):
        event_root = root / "events"
        if event_root.is_dir():
            for source in event_root.glob("*.txt"):
                document = context.document(source)
                if document is None:
                    continue
                for entry in document.root.entries:
                    if entry.key not in {"country_event", "province_event", "news_event"}:
                        continue
                    if not isinstance(entry.value, Object):
                        continue
                    event_id = first_scalar(entry.value, "id")
                    if event_id:
                        event_ids[event_id].append(str(source))
        decision_root = root / "decisions"
        if decision_root.is_dir():
            for source in decision_root.glob("*.txt"):
                document = context.document(source)
                if document is None:
                    continue
                for container in entries_named(document.root, "country_decisions"):
                    if not isinstance(container.value, Object):
                        continue
                    for entry in container.value.entries:
                        if entry.key and isinstance(entry.value, Object):
                            decision_ids[entry.key].append(str(source))
        for key, sources in collect_top_level(root / "common" / "event_modifiers").items():
            modifier_ids[key].extend(sources)
    if duplicates := duplicate_items(event_ids):
        report.error(f"Combined event IDs collide: {duplicates}")
    if duplicates := duplicate_items(decision_ids):
        report.error(f"Combined decision IDs collide: {duplicates}")
    if duplicates := duplicate_items(modifier_ids):
        report.error(f"Combined event modifier IDs collide: {duplicates}")

    idea_tag_counts = Counter()
    for identity in (
        *collect_idea_identities(main_context),
        *collect_idea_identities(map_context),
    ):
        if not identity.free:
            continue
        for tag in identity.tags:
            if tag in tags:
                idea_tag_counts[tag] += 1
    bad_idea_coverage = {
        tag: idea_tag_counts[tag] for tag in sorted(tags) if idea_tag_counts[tag] != 1
    }
    if bad_idea_coverage:
        report.error(f"Map tags must occur in exactly one free-idea trigger: {bad_idea_coverage}")

    # Descriptor dependency must match the main display name exactly.
    main_descriptor = parse_file(main_mod / "descriptor.mod")
    map_descriptor = parse_file(MAP_ROOT / "descriptor.mod")
    main_name = first_scalar(main_descriptor.root, "name")
    dependencies = {
        scalar.text for scalar in bare_scalars(first_object(map_descriptor.root, "dependencies"))
    }
    if main_name not in dependencies:
        report.error(
            f"Companion descriptor dependencies {sorted(dependencies)} do not include {main_name!r}"
        )

    # Strategic anchors and expanded Japan-region closure.
    definitions: dict[int, str] = {}
    for line in read_text(MAP_ROOT / "map" / "definition.csv").splitlines():
        fields = line.split(";")
        if fields and fields[0].isdigit() and len(fields) >= 5:
            definitions[int(fields[0])] = fields[4]
    for province_text, expected_name in contract["strategic_anchors"].items():
        province_id = int(province_text)
        if definitions.get(province_id) != expected_name:
            report.error(
                f"Strategic province {province_id} is {definitions.get(province_id)!r}; "
                f"expected {expected_name!r}"
            )

    area_document = parse_file(MAP_ROOT / "map" / "area.txt")
    region_document = parse_file(MAP_ROOT / "map" / "region.txt")
    area_members: dict[str, set[int]] = {}
    for entry in area_document.root.entries:
        if entry.key is None or not isinstance(entry.value, Object):
            continue
        area_members[entry.key] = {
            int(scalar.text)
            for scalar in bare_scalars(entry.value)
            if scalar.text.isdigit()
        }
    japan_entry = next(
        (
            entry
            for entry in region_document.root.entries
            if entry.key == "japan_region" and isinstance(entry.value, Object)
        ),
        None,
    )
    japan_provinces: set[int] = set()
    if japan_entry is None or not isinstance(japan_entry.value, Object):
        report.error("Map region.txt does not define japan_region")
    else:
        japan_areas = {
            scalar.text for scalar in bare_scalars(first_object(japan_entry.value, "areas"))
        }
        for area in japan_areas:
            if area not in area_members:
                report.error(f"japan_region references missing area {area}")
            japan_provinces.update(area_members.get(area, set()))
    planned_japan = set(province_plan["existing_japan_ids"]) | {
        province["id"] for province in province_plan["new_provinces"]
    }
    if japan_provinces != planned_japan:
        report.error(
            "Expanded japan_region closure differs from the 88-province plan: "
            f"missing={sorted(planned_japan - japan_provinces)}, "
            f"extra={sorted(japan_provinces - planned_japan)}"
        )

    active_main_text = "\n".join(main_text_by_file.values())
    japanese_hardcodes = {
        int(value)
        for value in re.findall(
            r"\b(?:owns|controls|province_id|owns_core_province)\s*=\s*(\d+)",
            active_main_text,
        )
        if int(value) in planned_japan
    }
    outside_region = japanese_hardcodes - japan_provinces
    if outside_region:
        report.error(f"Main hardcoded Japanese anchors left japan_region: {sorted(outside_region)}")

    area_references = set(re.findall(r"\barea\s*=\s*([a-z0-9_]+)", active_main_text))
    missing_areas = area_references - set(area_members)
    if missing_areas:
        report.error(f"Main gameplay references areas absent from the companion map: {sorted(missing_areas)}")
    region_definitions = {
        entry.key
        for entry in region_document.root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }
    region_references = set(re.findall(r"\bregion\s*=\s*([a-z0-9_]+)", active_main_text))
    missing_regions = region_references - region_definitions
    if missing_regions:
        report.error(
            f"Main gameplay references regions absent from the companion map: {sorted(missing_regions)}"
        )

    geography_block = extract_block(
        map_effect_text, "jxp_map_initialize_geography_contract_effect"
    )
    actual_geography: dict[str, set[str]] = defaultdict(set)
    actual_province_geography: dict[str, set[int]] = defaultdict(set)
    if geography_block is None:
        report.error("Companion geography compatibility initializer is missing")
    else:
        geography_document = parse_text(geography_block, Path("<geography-contract>"))
        geography_body = first_object(
            geography_document.root, "jxp_map_initialize_geography_contract_effect"
        )
        for _path, every_province in walk_entries(geography_body):
            if (
                every_province.key != "every_province"
                or not isinstance(every_province.value, Object)
            ):
                continue
            limit = first_object(every_province.value, "limit")
            areas = {
                assignment.value.text
                for _path, assignment in find_assignments(limit, "area")
                if isinstance(assignment.value, Scalar)
            }
            province_id = first_scalar(limit, "province_id")
            for _path, assignment in find_assignments(
                every_province.value, "set_province_flag"
            ):
                if isinstance(assignment.value, Scalar):
                    for area in areas:
                        actual_geography[assignment.value.text].add(area)
                    if province_id and province_id.isdigit():
                        actual_province_geography[assignment.value.text].add(
                            int(province_id)
                        )
    expected_geography = {
        flag: set(areas) for flag, areas in contract["geography_flags"].items()
    }
    if actual_geography != expected_geography:
        report.error(
            f"Companion geography flag mapping {dict(actual_geography)}, "
            f"expected {expected_geography}"
        )
    expected_province_geography = {
        flag: {int(province) for province in provinces}
        for flag, provinces in contract.get("geography_province_flags", {}).items()
    }
    if actual_province_geography != expected_province_geography:
        report.error(
            "Companion exact-province geography flag mapping "
            f"{dict(actual_province_geography)}, expected {expected_province_geography}"
        )
    for flag in expected_geography.keys() | expected_province_geography.keys():
        if not re.search(rf"has_province_flag\s*=\s*{re.escape(flag)}\b", active_main_text):
            report.error(f"Main gameplay never consumes companion geography flag {flag}")

    threshold_occurrences = re.findall(r"\bnum_of_cities\s*=\s*(25|30)\b", active_main_text)
    report.note(
        f"Combined mission assembly: {checked_profiles} profiles, 30 tags x 4 DLC states"
    )
    report.note(
        f"Mission ownership: {len(exact_identity_series)} exact eight-stage identities; "
        f"{len(tags) - len(exact_identity_series)} shared-family profiles"
    )
    report.note(
        f"Origin contract: {len(tags)} tags in 5 exclusive groups; culture catalog closure passed"
    )
    report.note(
        f"Geography contract: {len(japan_provinces)} Japan provinces, "
        f"{len(japanese_hardcodes)} active hardcoded Japanese anchors, "
        f"{len(expected_geography)} additive macro-scope flags and "
        f"{len(expected_province_geography)} exact-province flags"
    )
    report.note(
        f"Balance review inventory: {len(threshold_occurrences)} active num_of_cities 25/30 gates "
        "remain map-scale-sensitive and are intentionally reported rather than auto-rescaled"
    )
    report.note(
        f"Combined ID closure: {len(event_ids)} events, {len(decision_ids)} decisions, "
        f"{len(callable_definitions)} scripted callables, {len(modifier_ids)} modifiers"
    )
    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
