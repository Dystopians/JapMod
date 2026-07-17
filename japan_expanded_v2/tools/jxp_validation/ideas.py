"""Validate every mod-owned national idea group and route-specific identity."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from .clausewitz import Object, Scalar, entries_named, first_object, first_scalar
from .build_consolidated_country_ideas import (
    OUTPUT_RELATIVE as CONSOLIDATED_IDEA_FILE,
    appended_source_groups as consolidated_appended_source_groups,
    build_registry as build_consolidated_registry,
    source_groups as consolidated_source_groups,
)
from .core import CheckResult, ValidationContext


EXPECTED = {
    "KJP_ideas": "KJP",
    "CJP_ideas": "CJP",
    "EJP_ideas": "EJP",
    "RFJ_ideas": "RFJ",
    "SJP_ideas": "SJP",
    "IJP_ideas": "IJP",
    "WAK_ideas": "WAK",
}
NATIONAL_IDEA_COUNT = 7
REQUIRED_OBJECT_MEMBERS = ("start", "bonus", "trigger")
OPTIONAL_OBJECT_MEMBERS = ("ai_will_do",)
REQUIRED_SCALAR_MEMBERS = ("free",)
OPTIONAL_SCALAR_MEMBERS = ("category", "important")
GROUP_METADATA = set(
    REQUIRED_OBJECT_MEMBERS
    + OPTIONAL_OBJECT_MEMBERS
    + REQUIRED_SCALAR_MEMBERS
    + OPTIONAL_SCALAR_MEMBERS
)
NON_MODIFIER_METADATA = GROUP_METADATA - {"start", "bonus"}
ROUTE_SIGNATURES = {
    "KJP_ideas": {"global_missionary_strength", "artillery_power"},
    "CJP_ideas": {"administrative_efficiency", "core_creation"},
    "EJP_ideas": {"administrative_efficiency", "discipline"},
    "RFJ_ideas": {"monthly_fervor_increase", "fire_damage"},
    "SJP_ideas": {"merchants", "ship_power_propagation"},
    "IJP_ideas": {"development_cost", "manpower_recovery_speed"},
    "WAK_ideas": {"privateer_efficiency", "capture_ship_chance"},
}
NATIONAL_IDEA_GROUP_PATTERN = re.compile(r"_ideas(?:_\d+)?$", re.IGNORECASE)


def _is_national_idea_group_name(name: str | None) -> bool:
    return bool(name and NATIONAL_IDEA_GROUP_PATTERN.search(name))


def check_national_idea_structure(context: ValidationContext) -> CheckResult:
    """Enforce the project-wide ``start + 7 ideas + bonus`` UI contract.

    JXP owns a generated copy of the pinned vanilla country registry, so this
    check accepts the historical vanilla key variants ``*_Ideas`` and
    ``*_ideas_N`` while still treating every top-level member as an activatable
    national-idea group.  A newly added group cannot bypass the UI limit merely
    because it is outside the seven route end-tag definitions.
    """

    result = CheckResult("National idea group structure")
    ideas_root = context.mod_root / "common" / "ideas"
    files = tuple(sorted(ideas_root.glob("*.txt"))) if ideas_root.is_dir() else ()
    if not files:
        result.add(
            "ideas.directory_missing",
            "common/ideas contains no national idea definition files",
            "common/ideas",
        )
        result.summary = "no national idea files available"
        return result

    definitions: dict[str, list[tuple[Path, int]]] = {}
    group_count = 0
    valid_group_count = 0
    idea_count = 0

    for source in files:
        document = context.document(source)
        if document is None:
            result.add(
                "ideas.file_invalid",
                "idea file is missing or could not be parsed",
                context.relative(source),
            )
            continue

        for entry in document.root.entries:
            if (
                entry.key is None
                or entry.operator != "="
                or not isinstance(entry.value, Object)
                or not _is_national_idea_group_name(entry.key)
            ):
                label = entry.key if entry.key is not None else "<bare value>"
                result.add(
                    "ideas.top_level_member",
                    f"unexpected top-level idea-file member {label!r}; expected NAME_ideas = {{ ... }}",
                    context.relative(source),
                    entry.line,
                )
                continue

            group_count += 1
            group_name = entry.key
            body = entry.value
            definitions.setdefault(group_name, []).append((source, entry.line))
            issue_count_before = len(result.issues)

            for key in REQUIRED_OBJECT_MEMBERS:
                members = entries_named(body, key)
                if not members:
                    result.add(
                        f"ideas.{key}_missing",
                        f"{group_name} is missing required top-level {key} = {{ ... }}",
                        context.relative(source),
                        entry.line,
                    )
                    continue
                if len(members) != 1:
                    result.add(
                        f"ideas.{key}_count",
                        f"{group_name} defines {len(members)} top-level {key} members; expected exactly one",
                        context.relative(source),
                        entry.line,
                    )
                for member in members:
                    if member.operator != "=" or not isinstance(member.value, Object):
                        result.add(
                            "ideas.member_type",
                            f"{group_name} top-level {key} must be an object assignment",
                            context.relative(source),
                            member.line,
                        )

            for key in OPTIONAL_OBJECT_MEMBERS:
                members = entries_named(body, key)
                if len(members) > 1:
                    result.add(
                        "ideas.metadata_count",
                        f"{group_name} defines {len(members)} top-level {key} members; expected at most one",
                        context.relative(source),
                        entry.line,
                    )
                for member in members:
                    if member.operator != "=" or not isinstance(member.value, Object):
                        result.add(
                            "ideas.member_type",
                            f"{group_name} top-level {key} must be an object assignment",
                            context.relative(source),
                            member.line,
                        )

            for key in REQUIRED_SCALAR_MEMBERS:
                members = entries_named(body, key)
                if not members:
                    result.add(
                        f"ideas.{key}_missing",
                        f"{group_name} is missing required top-level {key} = yes",
                        context.relative(source),
                        entry.line,
                    )
                    continue
                if len(members) != 1:
                    result.add(
                        f"ideas.{key}_count",
                        f"{group_name} defines {len(members)} top-level {key} members; expected exactly one",
                        context.relative(source),
                        entry.line,
                    )
                for member in members:
                    if (
                        member.operator != "="
                        or not isinstance(member.value, Scalar)
                        or member.value.text != "yes"
                    ):
                        result.add(
                            "ideas.free_value",
                            f"{group_name} must define exactly one top-level free = yes",
                            context.relative(source),
                            member.line,
                        )

            for key in OPTIONAL_SCALAR_MEMBERS:
                members = entries_named(body, key)
                if len(members) > 1:
                    result.add(
                        "ideas.metadata_count",
                        f"{group_name} defines {len(members)} top-level {key} members; expected at most one",
                        context.relative(source),
                        entry.line,
                    )
                for member in members:
                    if member.operator != "=" or not isinstance(member.value, Scalar):
                        result.add(
                            "ideas.member_type",
                            f"{group_name} top-level {key} must be a scalar assignment",
                            context.relative(source),
                            member.line,
                        )

            ideas = []
            for child in body.entries:
                if child.key in GROUP_METADATA:
                    continue
                if (
                    child.key is None
                    or child.operator != "="
                    or not isinstance(child.value, Object)
                ):
                    label = child.key if child.key is not None else "<bare value>"
                    result.add(
                        "ideas.unexpected_member",
                        f"{group_name} has unexpected top-level member {label!r}; "
                        "only idea objects and recognised metadata are allowed",
                        context.relative(source),
                        child.line,
                    )
                    continue
                ideas.append(child)

            idea_count += len(ideas)
            if len(ideas) != NATIONAL_IDEA_COUNT:
                result.add(
                    "ideas.count",
                    f"{group_name} defines {len(ideas)} ideas; expected exactly {NATIONAL_IDEA_COUNT}",
                    context.relative(source),
                    entry.line,
                )
            duplicate_ideas = sorted(
                key
                for key, count in Counter(child.key for child in ideas).items()
                if count > 1
            )
            if duplicate_ideas:
                result.add(
                    "ideas.duplicate_idea",
                    f"{group_name} repeats idea members: {', '.join(duplicate_ideas)}",
                    context.relative(source),
                    entry.line,
                )

            if len(result.issues) == issue_count_before:
                valid_group_count += 1

    for group_name, locations in sorted(definitions.items()):
        if len(locations) <= 1:
            continue
        rendered = ", ".join(
            f"{context.relative(source)}:{line}" for source, line in locations
        )
        result.add(
            "ideas.duplicate_group",
            f"{group_name} is defined more than once: {rendered}",
        )

    result.metrics.update(
        {
            "files": len(files),
            "groups": group_count,
            "valid_groups": valid_group_count,
            "ideas": idea_count,
        }
    )
    result.summary = (
        f"{valid_group_count}/{group_count} groups satisfy exact "
        f"start + {NATIONAL_IDEA_COUNT} ideas + bonus structure across {len(files)} files"
    )
    return result


def _national_idea_definition_sources(context: ValidationContext) -> dict[str, list[Path]]:
    definitions: dict[str, list[Path]] = {}
    ideas_root = context.mod_root / "common" / "ideas"
    for source in sorted(ideas_root.glob("*.txt"), key=lambda path: path.name.casefold()):
        document = context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if (
                entry.key is not None
                and _is_national_idea_group_name(entry.key)
                and isinstance(entry.value, Object)
            ):
                definitions.setdefault(entry.key, []).append(source)
    return definitions


def check_vanilla_national_idea_precedence(
    context: ValidationContext,
    game_root: Path,
) -> CheckResult:
    """Prove that JXP owns one duplicate-free national-idea registry file.

    Runtime evidence disproved the former additive-file ordering assumption:
    duplicate free groups in separate files can truncate EU4's IdeaDatabase
    even when their filenames appear to sit between the two vanilla files.
    JXP therefore replaces the exact pinned ``00_country_ideas.txt`` path with
    one generated registry and permits no second runtime idea file.
    """

    result = CheckResult("Vanilla national idea override precedence")
    mod_definitions = _national_idea_definition_sources(context)
    vanilla_context = ValidationContext(game_root)
    vanilla_definitions = _national_idea_definition_sources(vanilla_context)
    ideas_root = context.mod_root / "common" / "ideas"
    runtime_sources = tuple(
        sorted(ideas_root.glob("*.txt"), key=lambda source: source.name.casefold())
    ) if ideas_root.is_dir() else ()
    output = context.mod_root / CONSOLIDATED_IDEA_FILE
    foreign_sources = [source for source in runtime_sources if source != output]
    for source in foreign_sources:
        result.add(
            "ideas.additive_registry_file",
            f"{source.name} is a second runtime idea file; additive free-group files "
            "can truncate EU4's national-idea registry",
            context.relative(source),
        )
    if not output.is_file():
        result.add(
            "ideas.consolidated_registry_missing",
            "JXP must replace common/ideas/00_country_ideas.txt with one generated registry",
            str(CONSOLIDATED_IDEA_FILE),
        )

    authored_count = 0
    companion_tail_count = 0
    authored_overlaps: list[str] = []
    generated_current = False
    source_root = context.mod_root / "tools" / "jxp_validation" / "idea_sources"
    if source_root.is_dir() and output.is_file():
        try:
            authored = consolidated_source_groups(source_root)
            companion_tail = consolidated_appended_source_groups(source_root)
            authored_count = len(authored)
            companion_tail_count = len(companion_tail)
            authored_overlaps = sorted(
                {group for group, _block in (*authored, *companion_tail)}
                & set(vanilla_definitions)
            )
            expected = build_consolidated_registry(game_root, source_root)
            if output.read_bytes() != expected:
                result.add(
                    "ideas.consolidated_registry_drift",
                    "runtime 00_country_ideas.txt is not the exact pinned generated registry",
                    context.relative(output),
                )
            else:
                generated_current = True
        except Exception as exc:
            result.add(
                "ideas.consolidated_registry_build",
                f"could not reproduce the consolidated national-idea registry: {exc}",
                context.relative(source_root),
            )

    duplicate_groups = {
        group: sources for group, sources in mod_definitions.items() if len(sources) != 1
    }
    for group, sources in sorted(duplicate_groups.items()):
        result.add(
            "ideas.consolidated_duplicate_group",
            f"{group} appears {len(sources)} times in the runtime registry",
            context.relative(sources[0]),
        )
    safe = (
        output.is_file()
        and not foreign_sources
        and not duplicate_groups
        and (not source_root.is_dir() or generated_current)
    )
    result.metrics.update(
        {
            "vanilla_overrides": len(authored_overlaps),
            "precedence_safe_overrides": len(authored_overlaps) if safe else 0,
            "idea_files": len(runtime_sources),
            "registry_safe_files": 1 if safe else 0,
            "authored_groups": authored_count,
            "companion_tail_groups": companion_tail_count,
            "managed_groups": authored_count + companion_tail_count,
        }
    )
    result.summary = (
        f"{1 if safe else 0}/1 consolidated runtime registry; "
        f"{len(authored_overlaps) if safe else 0}/{len(authored_overlaps)} "
        "authored same-key vanilla groups replaced "
        f"without duplicate IDs; {authored_count} primary + "
        f"{companion_tail_count} companion-tail groups"
    )
    return result


def _count_scalar_assignments(obj: Object | None, key: str, value: str) -> int:
    if obj is None:
        return 0
    count = 0
    for entry in obj.entries:
        if (
            entry.key == key
            and isinstance(entry.value, Scalar)
            and entry.value.text == value
        ):
            count += 1
        if isinstance(entry.value, Object):
            count += _count_scalar_assignments(entry.value, key, value)
    return count


def _scalar_assignment_values(obj: Object | None, key: str) -> list[str]:
    if obj is None:
        return []
    values: list[str] = []
    for entry in obj.entries:
        if entry.key == key and isinstance(entry.value, Scalar):
            values.append(entry.value.text)
        if isinstance(entry.value, Object):
            values.extend(_scalar_assignment_values(entry.value, key))
    return values


def _managed_main_idea_tags(context: ValidationContext) -> set[str]:
    tags = {"JAP"}
    source_root = context.mod_root / "tools" / "jxp_validation" / "idea_sources"
    authored_ids = (
        {group for group, _block in consolidated_source_groups(source_root)}
        if source_root.is_dir()
        else None
    )
    ideas_root = context.mod_root / "common" / "ideas"
    for source in sorted(ideas_root.glob("*.txt")):
        document = context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if not (
                entry.key
                and _is_national_idea_group_name(entry.key)
                and isinstance(entry.value, Object)
            ):
                continue
            if authored_ids is not None and entry.key not in authored_ids:
                continue
            trigger = first_object(entry.value, "trigger")
            tag = first_scalar(trigger, "tag") if trigger is not None else None
            if tag:
                tags.add(tag)
    return tags


def _modifier_keys(block: Object | None) -> list[str]:
    if block is None:
        return []
    return [
        entry.key
        for entry in block.entries
        if entry.key is not None and isinstance(entry.value, Scalar)
    ]


def _vanilla_modifier_catalog(game_root: Path) -> set[str]:
    context = ValidationContext(game_root)
    catalog: set[str] = set()
    sources = list((game_root / "common" / "ideas").glob("*.txt"))
    sources.extend((game_root / "common" / "custom_ideas").glob("*.txt"))
    for source in sorted(sources):
        document = context.document(source)
        if document is None:
            continue
        for group_entry in document.root.entries:
            if not isinstance(group_entry.value, Object):
                continue
            for child in group_entry.value.entries:
                if child.key in NON_MODIFIER_METADATA:
                    continue
                if not isinstance(child.value, Object):
                    continue
                catalog.update(_modifier_keys(child.value))
    return catalog


def check_national_idea_modifiers(
    context: ValidationContext,
    game_root: Path,
) -> CheckResult:
    """Reject modifier keys absent from the pinned vanilla idea vocabulary."""

    result = CheckResult("National idea modifier vocabulary")
    catalog = _vanilla_modifier_catalog(game_root)
    checked_groups = 0
    modifier_entries = 0
    ideas_root = context.mod_root / "common" / "ideas"
    for source in sorted(ideas_root.glob("*.txt")):
        document = context.document(source)
        if document is None:
            continue
        for entry in document.root.entries:
            if (
                entry.key is None
                or not _is_national_idea_group_name(entry.key)
                or not isinstance(entry.value, Object)
            ):
                continue
            checked_groups += 1
            body = entry.value
            blocks = [first_object(body, "start"), first_object(body, "bonus")]
            blocks.extend(
                child.value
                for child in body.entries
                if child.key not in GROUP_METADATA and isinstance(child.value, Object)
            )
            keys = [key for block in blocks for key in _modifier_keys(block)]
            modifier_entries += len(keys)
            for unknown in sorted(set(keys) - catalog):
                result.add(
                    "ideas.unknown_modifier",
                    f"{entry.key} uses modifier {unknown}, absent from the pinned vanilla idea catalog",
                    context.relative(source),
                    entry.line,
                )
    result.metrics.update(
        {
            "groups": checked_groups,
            "modifier_entries": modifier_entries,
            "vanilla_catalog_entries": len(catalog),
        }
    )
    result.summary = (
        f"{checked_groups} groups / {modifier_entries} modifier entries checked "
        f"against {len(catalog)} vanilla keys"
    )
    return result


def check_route_ideas(context: ValidationContext, game_root: Path) -> CheckResult:
    structure = check_national_idea_structure(context)
    vocabulary = check_national_idea_modifiers(context, game_root)
    precedence = check_vanilla_national_idea_precedence(context, game_root)
    result = CheckResult("National ideas and route identity")
    result.issues.extend(structure.issues)
    result.issues.extend(vocabulary.issues)
    result.issues.extend(precedence.issues)
    result.notes.extend(structure.notes)
    result.metrics.update(structure.metrics)
    result.metrics["all_group_modifier_entries"] = vocabulary.metrics.get(
        "modifier_entries", 0
    )
    result.metrics.update(precedence.metrics)
    result.metrics["companion_group_modifier_entries"] = 0
    source = context.mod_root / CONSOLIDATED_IDEA_FILE
    document = context.document(source)
    if document is None:
        result.add(
            "ideas.file_missing",
            "consolidated 00_country_ideas.txt is missing or invalid",
            context.relative(source),
        )
        result.summary = f"{structure.summary}; consolidated idea registry unavailable"
        return result

    groups = {
        entry.key: entry
        for entry in document.root.entries
        if entry.key in EXPECTED and isinstance(entry.value, Object)
    }
    source_root = context.mod_root / "tools" / "jxp_validation" / "idea_sources"
    try:
        companion_group_ids = {
            group for group, _block in consolidated_appended_source_groups(source_root)
        }
    except (OSError, RuntimeError) as exc:
        companion_group_ids = set()
        result.add(
            "ideas.companion_tail_source",
            f"could not load the companion idea tail source: {exc}",
            context.relative(source_root),
        )
    companion_modifier_entries = 0
    for entry in document.root.entries:
        if entry.key not in companion_group_ids or not isinstance(entry.value, Object):
            continue
        body = entry.value
        blocks = [first_object(body, "start"), first_object(body, "bonus")]
        blocks.extend(
            child.value
            for child in body.entries
            if child.key not in GROUP_METADATA and isinstance(child.value, Object)
        )
        companion_modifier_entries += sum(len(_modifier_keys(block)) for block in blocks)
    result.metrics["companion_group_modifier_entries"] = companion_modifier_entries
    checked = 0
    modifier_total = 0

    for group_name, expected_tag in EXPECTED.items():
        entry = groups.get(group_name)
        if entry is None or not isinstance(entry.value, Object):
            result.add("ideas.group_missing", f"missing {group_name}", context.relative(source))
            continue
        checked += 1
        body = entry.value
        trigger = first_object(body, "trigger")
        actual_tag = first_scalar(trigger, "tag") if trigger is not None else None
        if actual_tag != expected_tag:
            result.add(
                "ideas.trigger_tag",
                f"{group_name} triggers for {actual_tag!r}; expected {expected_tag}",
                context.relative(source),
                entry.line,
            )

        ideas = [
            child
            for child in body.entries
            if child.key not in GROUP_METADATA and isinstance(child.value, Object)
        ]
        if len(ideas) != 7:
            result.add(
                "ideas.count",
                f"{group_name} defines {len(ideas)} ideas; expected 7",
                context.relative(source),
                entry.line,
            )

        blocks = [first_object(body, "start"), first_object(body, "bonus")]
        blocks.extend(child.value for child in ideas if isinstance(child.value, Object))
        keys = [key for block in blocks for key in _modifier_keys(block)]
        modifier_total += len(keys)
        dual_ideas = sum(len(_modifier_keys(child.value)) >= 2 for child in ideas)
        if len(keys) < 15 or dual_ideas < 5:
            result.add(
                "ideas.power_floor",
                f"{group_name} has {len(keys)} total modifiers and {dual_ideas} dual-modifier "
                "ideas; expected at least 15 and 5",
                context.relative(source),
                entry.line,
            )

        signatures = ROUTE_SIGNATURES[group_name]
        missing_signatures = sorted(signatures - set(keys))
        if missing_signatures:
            result.add(
                "ideas.route_signature",
                f"{group_name} lacks route signatures: {', '.join(missing_signatures)}",
                context.relative(source),
                entry.line,
            )

    script_files = context.script_files()
    swaps = context.assignment_occurrences(
        "swap_free_idea_group", "yes", files=script_files
    )
    expected_swap_locations = Counter(
        {
            "common/scripted_effects/jxp_scripted_effects.txt": 2,
            "common/scripted_effects/jxp_81_national_idea_registry_effects.txt": 1,
        }
    )
    actual_swap_locations = Counter(context.relative(swap.source) for swap in swaps)
    if len(swaps) != 3:
        result.add(
            "ideas.swap_count",
            f"found {len(swaps)} free national-idea swaps; expected one idempotent "
            "route sync plus two narrowly versioned forced migrations",
        )
    if actual_swap_locations != expected_swap_locations:
        result.add(
            "ideas.swap_location",
            f"free-idea swaps are in {dict(actual_swap_locations)}; expected "
            f"{dict(expected_swap_locations)}",
        )

    effects_source = (
        context.mod_root / "common" / "scripted_effects" / "jxp_scripted_effects.txt"
    )
    effects_document = context.document(effects_source)
    ordinary_sync = (
        first_object(effects_document.root, "jxp_sync_route_national_ideas_effect")
        if effects_document is not None
        else None
    )
    forced_sync = (
        first_object(effects_document.root, "jxp_force_sync_route_national_ideas_effect")
        if effects_document is not None
        else None
    )
    if _count_scalar_assignments(ordinary_sync, "swap_free_idea_group", "yes") != 1:
        result.add(
            "ideas.idempotent_swap_shape",
            "jxp_sync_route_national_ideas_effect must contain exactly one guarded swap",
            context.relative(effects_source),
        )
    if (
        _count_scalar_assignments(
            ordinary_sync, "jxp_has_expected_route_national_ideas_trigger", "yes"
        )
        != 1
    ):
        result.add(
            "ideas.idempotent_swap_guard",
            "ordinary route idea sync must guard its swap with the exact expected-group trigger",
            context.relative(effects_source),
        )
    if (
        _count_scalar_assignments(
            ordinary_sync, "has_country_flag", "jxp_route_ideas_synced_v0241"
        )
        != 0
    ):
        result.add(
            "ideas.idempotent_swap_flag_gate",
            "ordinary route idea sync must not swap merely because a migration marker is absent",
            context.relative(effects_source),
        )
    if _count_scalar_assignments(forced_sync, "swap_free_idea_group", "yes") != 1:
        result.add(
            "ideas.forced_swap_shape",
            "jxp_force_sync_route_national_ideas_effect must contain exactly one forced swap",
            context.relative(effects_source),
        )

    managed_effects_source = (
        context.mod_root
        / "common/scripted_effects/jxp_81_national_idea_registry_effects.txt"
    )
    managed_effects_document = context.document(managed_effects_source)
    managed_sync = (
        first_object(
            managed_effects_document.root,
            "jxp_sync_managed_national_ideas_effect",
        )
        if managed_effects_document is not None
        else None
    )
    if _count_scalar_assignments(managed_sync, "swap_free_idea_group", "yes") != 1:
        result.add(
            "ideas.managed_swap_shape",
            "jxp_sync_managed_national_ideas_effect must contain exactly one guarded swap",
            context.relative(managed_effects_source),
        )
    if (
        _count_scalar_assignments(
            managed_sync, "jxp_uses_managed_national_ideas_trigger", "yes"
        )
        != 1
        or _count_scalar_assignments(managed_sync, "has_custom_ideas", "no") != 1
        or _count_scalar_assignments(
            managed_sync,
            "jxp_has_expected_managed_national_ideas_trigger",
            "yes",
        )
        != 1
    ):
        result.add(
            "ideas.managed_swap_guard",
            "managed idea sync must be restricted to managed tags without custom ideas "
            "and guarded by the exact expected-group postcondition",
            context.relative(managed_effects_source),
        )

    managed_trigger_source = (
        context.mod_root
        / "common/scripted_triggers/jxp_80_national_idea_triggers.txt"
    )
    managed_trigger_document = context.document(managed_trigger_source)
    managed_trigger = (
        first_object(
            managed_trigger_document.root,
            "jxp_uses_managed_national_ideas_trigger",
        )
        if managed_trigger_document is not None
        else None
    )
    expected_managed_tags = _managed_main_idea_tags(context)
    actual_managed_tag_values = _scalar_assignment_values(managed_trigger, "tag")
    actual_managed_tags = set(actual_managed_tag_values)
    if actual_managed_tags != expected_managed_tags or len(actual_managed_tag_values) != len(
        actual_managed_tags
    ):
        result.add(
            "ideas.managed_tag_coverage",
            "managed idea migration tags differ from the main idea registry: "
            f"missing={sorted(expected_managed_tags - actual_managed_tags)}, "
            f"extra={sorted(actual_managed_tags - expected_managed_tags)}, "
            f"duplicates={sorted(tag for tag, count in Counter(actual_managed_tag_values).items() if count > 1)}",
            context.relative(managed_trigger_source),
        )

    expected_trigger = (
        first_object(
            managed_trigger_document.root,
            "jxp_has_expected_managed_national_ideas_trigger",
        )
        if managed_trigger_document is not None
        else None
    )
    expected_or = first_object(expected_trigger, "OR")
    actual_expected_pairs: list[tuple[str, str]] = []
    if expected_or is not None:
        for entry in entries_named(expected_or, "AND"):
            if not isinstance(entry.value, Object):
                continue
            tags = _scalar_assignment_values(entry.value, "tag")
            groups = _scalar_assignment_values(entry.value, "has_idea_group")
            if len(tags) == 1 and len(groups) == 1:
                actual_expected_pairs.append((tags[0], groups[0]))
    expected_managed_pairs = {
        (tag, f"{tag}_ideas") for tag in expected_managed_tags
    }
    if (
        set(actual_expected_pairs) != expected_managed_pairs
        or len(actual_expected_pairs) != len(expected_managed_pairs)
    ):
        result.add(
            "ideas.managed_expected_group_coverage",
            "managed idea postcondition differs from the exact tag/group registry: "
            f"missing={sorted(expected_managed_pairs - set(actual_expected_pairs))}, "
            f"extra={sorted(set(actual_expected_pairs) - expected_managed_pairs)}, "
            f"duplicates={sorted(pair for pair, count in Counter(actual_expected_pairs).items() if count > 1)}",
            context.relative(managed_trigger_source),
        )

    sync_calls = context.assignment_occurrences(
        "jxp_sync_route_national_ideas_effect", "yes", files=script_files
    )
    if len(sync_calls) < 2:
        result.add(
            "ideas.sync_coverage",
            "route grants and the 0.24.1 migration must both call the idea sync helper",
        )

    forced_sync_calls = context.assignment_occurrences(
        "jxp_force_sync_route_national_ideas_effect", "yes", files=script_files
    )
    if len(forced_sync_calls) != 2:
        result.add(
            "ideas.forced_sync_coverage",
            f"found {len(forced_sync_calls)} forced idea-sync calls; expected the 0.24.1 "
            "repair plus the 0.28.1 one-time migration",
        )

    managed_sync_calls = context.assignment_occurrences(
        "jxp_sync_managed_national_ideas_effect", "yes", files=script_files
    )
    if len(managed_sync_calls) != 1:
        result.add(
            "ideas.managed_sync_coverage",
            f"found {len(managed_sync_calls)} managed idea-registry repair calls; expected one",
        )
    startup_source = (
        context.mod_root
        / "common/on_actions/jxp_60_mission_runtime_on_actions.txt"
    )
    startup_text = (
        startup_source.read_text(encoding="utf-8-sig")
        if startup_source.is_file()
        else ""
    )
    if startup_text.count("jxp_idea_registry.1") != 1:
        result.add(
            "ideas.managed_startup_registration",
            "jxp_idea_registry.1 must be registered exactly once in on_startup",
            context.relative(startup_source),
        )

    prompts = context.assignment_occurrences("id", "ideagroups.1", files=script_files)
    if prompts:
        result.add(
            "ideas.optional_prompt",
            "route tag changes must not use the optional vanilla idea-swap prompt",
            context.relative(prompts[0].source),
            prompts[0].entry.line,
        )

    for group_name in EXPECTED:
        if not context.assignment_occurrences(
            "has_idea_group", group_name, files=script_files
        ):
            result.add(
                "ideas.sync_expected_group",
                f"idea sync helper does not verify {group_name}",
            )

    result.metrics.update(
        {
            "route_groups": checked,
            "route_modifiers": modifier_total,
            "canonical_swaps": len(swaps),
            "sync_calls": len(sync_calls),
            "forced_sync_calls": len(forced_sync_calls),
            "managed_sync_calls": len(managed_sync_calls),
            "managed_tags": len(actual_managed_tags),
        }
    )
    result.summary = (
        f"{structure.summary}; {checked}/7 route groups; "
        f"{modifier_total} route modifier entries; {precedence.summary}; "
        f"{len(swaps)} canonical swaps"
    )
    return result
