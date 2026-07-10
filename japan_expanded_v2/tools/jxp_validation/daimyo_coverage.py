"""Executable all-daimyo idea, identity-mission, and strength matrix.

JXP ships as a maintained main/companion pair.  This check deliberately
audits every selectable daimyo literal instead of sampling one member of each
house family.  It also keeps the claims separate:

* an identity idea is a free national-idea group selected by one exact tag;
* an identity mission is one explicit, non-generic slot-3 series selected for
  the tag in every supported DLC state;
* influence tiers set minimum idea density and mission depth without changing
  the five-column ownership contract.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from .clausewitz import Object, Scalar, first_object
from .core import CheckResult, ValidationContext
from .effective_topology import analyze_effective_topology
from .ideas import GROUP_METADATA
from .missions import (
    DAIMYO_TAGS,
    DLC_PROFILE_VARIANTS,
    PINNED_OVERRIDE_FILES,
    MissionSeries,
    Profile,
    evaluate_potential,
    extract_mission_series,
)


MAIN_TIER_S = frozenset({"ODA", "TOY"})
MAIN_TIER_A = frozenset(
    {
        "ASK", "CSK", "DTE", "HJO", "IMG", "MRI", "OTM", "OUC",
        "SMZ", "SOO", "TKD", "TKG", "UES",
    }
)

# These companion houses materially shaped a regional balance, controlled an
# exceptional religious/maritime institution, or became a major Sengoku / early
# Edo state.  Keeping the list executable prevents an informal "famous tag"
# exception from drifting between audits.
MAP_TIER_A = frozenset(
    {
        "ARI", "AZI", "HNG", "KRD", "MOG", "MTS", "MTU", "MYO",
        "NBS", "RKK", "RZJ", "STM", "STO", "TGR", "UKT",
    }
)
MAP_TIER_B = frozenset(
    {
        "ASN", "HCS", "HNM", "KMP", "KYO", "MKM", "NHT", "OSK",
        "SGR", "SMA", "WKT", "YMC",
    }
)

TIER_STRENGTH_FLOORS = {
    "S": (13, 3),
    "A": (13, 3),
    "B": (12, 1),
    "C": (11, 1),
}
TIER_MISSION_FLOORS = {"S": 6, "A": 6, "B": 6, "C": 6}


@dataclass(frozen=True, slots=True)
class IdeaIdentity:
    group: str
    tags: tuple[str, ...]
    free: bool
    idea_count: int
    modifier_entries: int
    dual_modifier_ideas: int
    mechanical_signature: tuple[tuple[tuple[str, str], ...], ...]
    source: Path
    line: int


@dataclass(frozen=True, slots=True)
class DaimyoCoverageRow:
    surface: str
    tag: str
    tier: str
    idea_group: str | None
    idea_modifier_entries: int
    dual_modifier_ideas: int
    identity_series: str | None
    identity_missions: int
    complete_dlc_profiles: int


def _tier(surface: str, tag: str) -> str:
    if surface == "main":
        if tag in MAIN_TIER_S:
            return "S"
        if tag in MAIN_TIER_A:
            return "A"
        return "B"
    if tag in MAP_TIER_A:
        return "A"
    if tag in MAP_TIER_B:
        return "B"
    return "C"


def _scalars(block: Object | None) -> tuple[tuple[str, str], ...]:
    if block is None:
        return ()
    return tuple(
        sorted(
            (entry.key, entry.value.text)
            for entry in block.entries
            if entry.key is not None and isinstance(entry.value, Scalar)
        )
    )


def _trigger_tags(block: Object | None) -> tuple[str, ...]:
    """Collect literal tags while rejecting no structure.

    The caller deliberately requires exactly one result for an identity idea.
    Recursive collection lets that hard failure remain useful when a mutation
    wraps a shared list in OR/AND rather than merely changing formatting.
    """

    if block is None:
        return ()
    found: list[str] = []
    for entry in block.entries:
        if entry.key == "tag" and isinstance(entry.value, Scalar):
            found.append(entry.value.text)
        elif isinstance(entry.value, Object):
            found.extend(_trigger_tags(entry.value))
    return tuple(found)


def collect_idea_identities(context: ValidationContext) -> tuple[IdeaIdentity, ...]:
    found: list[IdeaIdentity] = []
    ideas_root = context.mod_root / "common" / "ideas"
    for source in sorted(ideas_root.glob("*.txt")):
        document = context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if (
                entry.key is None
                or not entry.key.endswith("_ideas")
                or not isinstance(entry.value, Object)
            ):
                continue
            body = entry.value
            idea_blocks = [
                child.value
                for child in body.entries
                if child.key not in GROUP_METADATA and isinstance(child.value, Object)
            ]
            mechanical_blocks = [first_object(body, "start"), *idea_blocks, first_object(body, "bonus")]
            modifier_entries = sum(len(_scalars(block)) for block in mechanical_blocks)
            dual_modifier_ideas = sum(len(_scalars(block)) >= 2 for block in idea_blocks)
            free_members = [child for child in body.entries if child.key == "free"]
            found.append(
                IdeaIdentity(
                    group=entry.key,
                    tags=_trigger_tags(first_object(body, "trigger")),
                    free=(
                        len(free_members) == 1
                        and isinstance(free_members[0].value, Scalar)
                        and free_members[0].value.text == "yes"
                    ),
                    idea_count=len(idea_blocks),
                    modifier_entries=modifier_entries,
                    dual_modifier_ideas=dual_modifier_ideas,
                    mechanical_signature=tuple(_scalars(block) for block in mechanical_blocks),
                    source=source,
                    line=entry.line,
                )
            )
    return tuple(found)


def audit_idea_assignment(
    surface: str,
    tag: str,
    tier: str,
    identities: Iterable[IdeaIdentity],
    result: CheckResult,
) -> IdeaIdentity | None:
    matches = tuple(identities)
    identity = matches[0] if len(matches) == 1 else None
    if len(matches) != 1:
        result.add(
            "daimyo.idea_coverage",
            f"{surface} {tag} resolves to {len(matches)} free-idea groups; expected exactly one",
        )
        return identity
    if identity.tags != (tag,):
        result.add(
            "daimyo.idea_not_exact_tag",
            f"{surface} {tag} uses shared idea group {identity.group} with tags {identity.tags}",
            str(identity.source),
            identity.line,
        )
    if not identity.free:
        result.add(
            "daimyo.idea_not_free",
            f"{surface} {tag} idea group {identity.group} is not selected by exactly one free = yes",
            str(identity.source),
            identity.line,
        )
    if identity.idea_count != 7:
        result.add(
            "daimyo.idea_shape",
            f"{surface} {tag} idea group {identity.group} has {identity.idea_count} ideas; expected 7",
            str(identity.source),
            identity.line,
        )
    min_entries, min_dual = TIER_STRENGTH_FLOORS[tier]
    if identity.modifier_entries < min_entries or identity.dual_modifier_ideas < min_dual:
        result.add(
            "daimyo.idea_strength_floor",
            f"{surface} {tag} tier {tier} has {identity.modifier_entries} modifier entries / "
            f"{identity.dual_modifier_ideas} dual ideas; expected at least {min_entries} / {min_dual}",
            str(identity.source),
            identity.line,
        )
    return identity


def audit_identity_depth(
    surface: str,
    tag: str,
    tier: str,
    series_name: str | None,
    mission_count: int,
    result: CheckResult,
) -> None:
    if mission_count < TIER_MISSION_FLOORS[tier]:
        result.add(
            "daimyo.identity_depth_floor",
            f"{surface} {tag} tier {tier} identity series {series_name!r} has "
            f"{mission_count} missions; expected at least {TIER_MISSION_FLOORS[tier]}",
        )


def audit_map_identity_migration_text(
    text: str, result: CheckResult, source: str | None = None
) -> None:
    for token in (
        "jxp_map_migrate_identity_v012_effect = {",
        "jxp_map_identity_migration_v012",
        "clr_country_flag = jxp_map_identity_migration_v012",
        "jxp_refresh_route_missions_effect = yes",
    ):
        if token not in text:
            result.add(
                "daimyo.map_identity_migration",
                f"companion identity migration is missing {token}",
                source,
            )


def audit_post_tag_idea_sync_text(
    main_effects: str,
    map_events: str,
    map_effects: str,
    result: CheckResult,
) -> None:
    requirements = (
        (
            main_effects,
            "AND = { tag = JAP NOT = { has_idea_group = JAP_ideas } }",
            "main canonical idea sync does not repair uncommitted JAP",
        ),
        (
            map_events,
            "id = jxp_map.102",
            "companion post-tag idea catch-up event is missing",
        ),
        (
            map_events,
            "jxp_sync_route_national_ideas_effect = yes",
            "companion post-tag catch-up bypasses the main canonical idea sync",
        ),
        (
            map_events,
            "set_country_flag = jxp_map_post_tag_idea_sync_v012",
            "companion post-tag catch-up lacks its one-time marker",
        ),
        (
            map_effects,
            "clr_country_flag = jxp_map_post_tag_idea_sync_v012",
            "companion debug reset cannot clear the post-tag idea marker",
        ),
    )
    for haystack, token, message in requirements:
        if token not in haystack:
            result.add("daimyo.post_tag_idea_sync", message)


def audit_forbidden_modifier_text(
    text: str, result: CheckResult, source: str | None = None
) -> None:
    forbidden = "fort_" + "defense"
    if forbidden in text:
        result.add(
            "daimyo.unknown_modifier_alias",
            f"{forbidden} is not an EU4 1.37.5 modifier; use defensiveness",
            source,
        )


def _mission_completed_calls(block: Object | None) -> tuple[str, ...]:
    if block is None:
        return ()
    found: list[str] = []
    for entry in block.entries:
        if entry.key == "mission_completed" and isinstance(entry.value, Scalar):
            found.append(entry.value.text)
        elif isinstance(entry.value, Object):
            found.extend(_mission_completed_calls(entry.value))
    return tuple(found)


def _series_trigger_dependencies(
    context: ValidationContext,
    series_catalog: Iterable[MissionSeries],
) -> dict[tuple[str, str], tuple[str, ...]]:
    dependencies: dict[tuple[str, str], tuple[str, ...]] = {}
    cached: dict[Path, Object] = {}
    for series in series_catalog:
        document = context.document(series.source)
        if document is None:
            continue
        root = cached.setdefault(series.source, document.root)
        series_entry = next(
            (
                entry
                for entry in root.entries
                if entry.key == series.name and isinstance(entry.value, Object)
            ),
            None,
        )
        if series_entry is None or not isinstance(series_entry.value, Object):
            continue
        for mission_entry in series_entry.value.entries:
            if mission_entry.key is None or not isinstance(mission_entry.value, Object):
                continue
            dependencies[(series.name, mission_entry.key)] = _mission_completed_calls(
                first_object(mission_entry.value, "trigger")
            )
    return dependencies


def _active_series(
    catalog: Iterable[MissionSeries],
    profile: Profile,
    result: CheckResult,
) -> tuple[MissionSeries, ...]:
    active: list[MissionSeries] = []
    for series in catalog:
        if series.generic:
            continue
        possible, unknown = evaluate_potential(series.potential, profile)
        load_possible, load_unknown = evaluate_potential(series.potential_on_load, profile)
        for predicate in unknown + load_unknown:
            result.add(
                "daimyo.profile_unknown_predicate",
                f"{profile.name}: {series.name} uses unsupported {predicate.key}: {predicate.reason}",
                str(series.source),
                series.line,
            )
        if True in possible and True in load_possible:
            active.append(series)
    return tuple(active)


def _coverage_tags(map_root: Path) -> tuple[set[str], dict[str, str]]:
    contract_path = map_root / "tools" / "jxp_map_validation" / "main_compatibility_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    group_for_tag: dict[str, str] = {}
    for group_name, group in contract["groups"].items():
        for tag in group["tags"]:
            group_for_tag[tag] = group_name
    return set(group_for_tag), group_for_tag


def build_daimyo_coverage_matrix(
    context: ValidationContext,
    result: CheckResult | None = None,
) -> tuple[DaimyoCoverageRow, ...]:
    """Build and audit the 68-tag x four-DLC coverage matrix."""

    if result is None:
        result = CheckResult("All-daimyo coverage matrix")
    map_root = context.mod_root.parent / "japan_expanded_v2_map"
    map_context = ValidationContext(map_root)
    map_tags, _group_for_tag = _coverage_tags(map_root)
    main_tags = set(DAIMYO_TAGS)
    identity_plan_path = map_root / "tools" / "jxp_map_builder" / "daimyo_identity_plan.json"
    identity_plan = json.loads(identity_plan_path.read_text(encoding="utf-8"))
    planned_tags = set(identity_plan.get("tags", {}))
    if planned_tags != map_tags:
        result.add(
            "daimyo.identity_plan_coverage",
            f"companion identity plan differs from contract: missing={sorted(map_tags - planned_tags)}, "
            f"extra={sorted(planned_tags - map_tags)}",
            str(identity_plan_path),
        )
    for tag in sorted(map_tags & planned_tags):
        planned_tier = identity_plan["tags"][tag].get("tier")
        if planned_tier != _tier("map", tag):
            result.add(
                "daimyo.identity_plan_tier",
                f"map {tag} plan tier {planned_tier!r} differs from executable tier {_tier('map', tag)}",
                str(identity_plan_path),
            )

    main_ideas = collect_idea_identities(context)
    map_ideas = collect_idea_identities(map_context)
    idea_by_tag: dict[str, list[IdeaIdentity]] = defaultdict(list)
    for identity in (*main_ideas, *map_ideas):
        for tag in identity.tags:
            if tag in main_tags | map_tags:
                idea_by_tag[tag].append(identity)

    main_parse = CheckResult("main mission parse")
    map_parse = CheckResult("map mission parse")
    main_sources = tuple(
        source
        for source in sorted((context.mod_root / "missions").glob("*.txt"))
        if source.name not in PINNED_OVERRIDE_FILES
        and not source.name.startswith("jxp_00_legacy_bom_")
    )
    main_series = extract_mission_series(
        context,
        main_parse,
        main_sources,
    )
    map_series = extract_mission_series(
        map_context,
        map_parse,
        tuple(sorted((map_root / "missions").glob("*.txt"))),
    )
    result.issues.extend(main_parse.issues)
    result.issues.extend(map_parse.issues)
    all_series = tuple(main_series) + tuple(map_series)
    dependency_maps = {}
    dependency_maps.update(_series_trigger_dependencies(context, main_series))
    dependency_maps.update(_series_trigger_dependencies(map_context, map_series))

    signature_owners: dict[
        tuple[tuple[tuple[str, str], ...], ...], list[str]
    ] = defaultdict(list)
    rows: list[DaimyoCoverageRow] = []
    for surface, tags in (("main", main_tags), ("map", map_tags)):
        for tag in sorted(tags):
            tier = _tier(surface, tag)
            identity = audit_idea_assignment(
                surface, tag, tier, idea_by_tag[tag], result
            )
            if identity is not None:
                signature_owners[identity.mechanical_signature].append(f"{surface}:{tag}")

            identity_names: set[str] = set()
            identity_counts: set[int] = set()
            complete_profiles = 0
            for suffix, dlcs in DLC_PROFILE_VARIANTS:
                profile = Profile(
                    name=f"{surface} daimyo {tag}{suffix}",
                    tag=tag,
                    religion="shinto",
                    religion_group="eastern",
                    reforms=frozenset({"daimyo"}),
                    daimyo_stage=True,
                    dlcs=dlcs,
                )
                active = _active_series(all_series, profile, result)
                by_slot: dict[int, list[MissionSeries]] = defaultdict(list)
                for series in active:
                    if series.slot is not None:
                        by_slot[series.slot].append(series)
                exact_slots = set(by_slot) == set(range(1, 6)) and all(
                    len(owners) == 1 for owners in by_slot.values()
                )
                if not exact_slots:
                    result.add(
                        "daimyo.profile_slot_owners",
                        f"{profile.name}: expected one non-generic owner in slots 1..5; got "
                        + str({slot: [owner.name for owner in owners] for slot, owners in by_slot.items()}),
                    )
                    continue
                identity_series = by_slot[3][0]
                explicit_tags = _trigger_tags(identity_series.potential)
                if identity_series.generic or tag not in explicit_tags:
                    result.add(
                        "daimyo.identity_mission_not_explicit",
                        f"{profile.name}: slot-3 owner {identity_series.name} is not an explicit non-generic identity series",
                        str(identity_series.source),
                        identity_series.line,
                    )
                active_ids = {
                    mission.mission_id for series in active for mission in series.missions
                }
                for series in active:
                    for mission in series.missions:
                        for dependency in dependency_maps.get(
                            (series.name, mission.mission_id), ()
                        ):
                            if dependency not in active_ids:
                                result.add(
                                    "daimyo.profile_inactive_trigger_dependency",
                                    f"{profile.name}: {mission.mission_id} requires inactive {dependency}",
                                    str(mission.source),
                                    mission.line,
                                )
                def origin_for_source(source: Path) -> str:
                    return "main" if source.resolve().is_relative_to(context.mod_root.resolve()) else "map"

                problems, _edges = analyze_effective_topology(
                    active, all_series, origin_for_source
                )
                for problem in problems:
                    result.add(
                        f"daimyo.{problem.code}",
                        f"{profile.name}: {problem.message}",
                    )
                identity_names.add(identity_series.name)
                identity_counts.add(len(identity_series.missions))
                complete_profiles += 1

            if len(identity_names) != 1 or len(identity_counts) != 1:
                result.add(
                    "daimyo.identity_dlc_drift",
                    f"{surface} {tag} identity changes across DLC states: series={sorted(identity_names)}, "
                    f"mission_counts={sorted(identity_counts)}",
                )
            identity_name = next(iter(identity_names), None)
            identity_count = next(iter(identity_counts), 0)
            audit_identity_depth(
                surface, tag, tier, identity_name, identity_count, result
            )
            if tier == "S" and identity_name is not None:
                selected_series = next(
                    series for series in all_series if series.name == identity_name
                )
                series_scope = {
                    candidate
                    for candidate in main_tags | map_tags
                    if candidate in _trigger_tags(
                        selected_series.potential
                    )
                }
                if len(series_scope) > 2:
                    result.add(
                        "daimyo.hegemon_series_scope",
                        f"{surface} {tag} tier-S series {identity_name} covers {sorted(series_scope)}; expected at most two lineage-linked tags",
                    )
                if (
                    surface != "main"
                    or identity_name != "jxp_oda_toyotomi_house_missions"
                    or "jxp_mission_oda_tenka_fubu_mainline"
                    not in {mission.mission_id for mission in selected_series.missions}
                ):
                    result.add(
                        "daimyo.tenka_fubu_mainline",
                        f"{surface} {tag} does not retain the ODA/TOY Tenka Fubu mainline",
                    )
            rows.append(
                DaimyoCoverageRow(
                    surface=surface,
                    tag=tag,
                    tier=tier,
                    idea_group=identity.group if identity is not None else None,
                    idea_modifier_entries=identity.modifier_entries if identity is not None else 0,
                    dual_modifier_ideas=identity.dual_modifier_ideas if identity is not None else 0,
                    identity_series=identity_name,
                    identity_missions=identity_count,
                    complete_dlc_profiles=complete_profiles,
                )
            )

    for signature, owners in signature_owners.items():
        if signature and len(owners) > 1:
            result.add(
                "daimyo.idea_mechanical_clone",
                "national idea mechanical signature is shared by " + ", ".join(sorted(owners)),
            )
    return tuple(rows)


def check_daimyo_coverage(context: ValidationContext) -> CheckResult:
    result = CheckResult("All selectable daimyo identity and strength matrix")
    map_root = context.mod_root.parent / "japan_expanded_v2_map"
    if not map_root.is_dir():
        result.add(
            "daimyo.map_root_missing",
            "mandatory companion root japan_expanded_v2_map is missing",
        )
        result.summary = "companion unavailable"
        return result
    rows = build_daimyo_coverage_matrix(context, result)
    map_context = ValidationContext(map_root)
    swaps = map_context.assignment_occurrences(
        "swap_free_idea_group", "yes", files=map_context.script_files()
    )
    if len(swaps) != 1:
        result.add(
            "daimyo.map_idea_migration_swap",
            f"companion defines {len(swaps)} idea swaps; expected one v012 migration swap",
        )
    elif map_context.relative(swaps[0].source) != "common/scripted_effects/jxp_map_effects.txt":
        result.add(
            "daimyo.map_idea_migration_location",
            "companion idea swap must live in jxp_map_migrate_identity_v012_effect",
            map_context.relative(swaps[0].source),
            swaps[0].entry.line,
        )
    map_effects_path = map_root / "common" / "scripted_effects" / "jxp_map_effects.txt"
    map_effects_text = map_effects_path.read_text(encoding="cp1252")
    audit_map_identity_migration_text(
        map_effects_text, result, str(map_effects_path)
    )
    main_effects_text = (
        context.mod_root / "common" / "scripted_effects" / "jxp_scripted_effects.txt"
    ).read_text(encoding="cp1252")
    map_events_text = (map_root / "events" / "jxp_map_events.txt").read_text(
        encoding="cp1252"
    )
    audit_post_tag_idea_sync_text(
        main_effects_text, map_events_text, map_effects_text, result
    )
    scan_roots = (
        *(context.mod_root / name for name in ("common", "decisions", "events", "missions")),
        *(map_root / name for name in ("common", "decisions", "events", "missions")),
        map_root / "tools" / "jxp_map_builder",
    )
    for scan_root in scan_roots:
        if not scan_root.is_dir():
            continue
        for source in sorted(scan_root.rglob("*")):
            if source.suffix.lower() not in {".txt", ".py", ".json"}:
                continue
            audit_forbidden_modifier_text(
                source.read_text(encoding="utf-8", errors="ignore"),
                result,
                source.as_posix(),
            )
    by_tier: dict[str, int] = defaultdict(int)
    for row in rows:
        by_tier[f"{row.surface}_{row.tier}"] += 1
    complete_profiles = sum(row.complete_dlc_profiles for row in rows)
    result.metrics.update(
        {
            "tags": len(rows),
            "main_tags": sum(row.surface == "main" for row in rows),
            "map_tags": sum(row.surface == "map" for row in rows),
            "exact_idea_groups": sum(
                row.idea_group is not None
                and next(
                    identity.tags
                    for identity in (
                        *collect_idea_identities(context),
                        *collect_idea_identities(ValidationContext(map_root)),
                    )
                    if identity.group == row.idea_group
                )
                == (row.tag,)
                for row in rows
            ),
            "identity_series": sum(row.identity_series is not None for row in rows),
            "dlc_profiles": complete_profiles,
            **dict(sorted(by_tier.items())),
        }
    )
    result.summary = (
        f"{len(rows)} daimyo tags ({result.metrics['main_tags']} main + "
        f"{result.metrics['map_tags']} map); {complete_profiles}/272 tag-DLC profiles; "
        f"{result.metrics['exact_idea_groups']}/{len(rows)} exact-tag free idea identities; "
        f"{result.metrics['identity_series']}/{len(rows)} non-generic identity series"
    )
    return result
