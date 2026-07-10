"""Validate the seven route end-tag national idea sets."""

from __future__ import annotations

from pathlib import Path

from .clausewitz import Object, Scalar, first_object, first_scalar
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
GROUP_METADATA = {"start", "bonus", "trigger", "free", "category", "important"}
ROUTE_SIGNATURES = {
    "KJP_ideas": {"global_missionary_strength", "artillery_power"},
    "CJP_ideas": {"administrative_efficiency", "core_creation"},
    "EJP_ideas": {"administrative_efficiency", "discipline"},
    "RFJ_ideas": {"monthly_fervor_increase", "fire_damage"},
    "SJP_ideas": {"merchants", "ship_power_propagation"},
    "IJP_ideas": {"development_cost", "manpower_recovery_speed"},
    "WAK_ideas": {"privateer_efficiency", "capture_ship_chance"},
}


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
                if child.key in {"trigger", "free", "category", "important"}:
                    continue
                if not isinstance(child.value, Object):
                    continue
                catalog.update(_modifier_keys(child.value))
    return catalog


def check_route_ideas(context: ValidationContext, game_root: Path) -> CheckResult:
    result = CheckResult("Route end-tag national ideas")
    source = context.mod_root / "common" / "ideas" / "jxp_route_ideas.txt"
    document = context.document(source)
    if document is None:
        result.add("ideas.file_missing", "jxp_route_ideas.txt is missing or invalid", context.relative(source))
        result.summary = "route idea file unavailable"
        return result

    groups = {
        entry.key: entry
        for entry in document.root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }
    catalog = _vanilla_modifier_catalog(game_root)
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

        for unknown in sorted(set(keys) - catalog):
            result.add(
                "ideas.unknown_modifier",
                f"{group_name} uses modifier {unknown}, absent from the vanilla idea catalog",
                context.relative(source),
                entry.line,
            )

    unexpected = sorted(set(groups) - set(EXPECTED))
    if unexpected:
        result.add(
            "ideas.unexpected_group",
            "unexpected route idea groups: " + ", ".join(unexpected),
            context.relative(source),
        )

    script_files = context.script_files()
    swaps = context.assignment_occurrences(
        "swap_free_idea_group", "yes", files=script_files
    )
    if len(swaps) != 1:
        result.add(
            "ideas.swap_count",
            f"found {len(swaps)} free national-idea swaps; expected one canonical sync effect",
        )
    elif context.relative(swaps[0].source) != "common/scripted_effects/jxp_scripted_effects.txt":
        result.add(
            "ideas.swap_location",
            "swap_free_idea_group must live in jxp_sync_route_national_ideas_effect",
            context.relative(swaps[0].source),
            swaps[0].entry.line,
        )

    sync_calls = context.assignment_occurrences(
        "jxp_sync_route_national_ideas_effect", "yes", files=script_files
    )
    if len(sync_calls) < 2:
        result.add(
            "ideas.sync_coverage",
            "route grants and the 0.24.1 migration must both call the idea sync helper",
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
            "groups": checked,
            "modifiers": modifier_total,
            "canonical_swaps": len(swaps),
            "sync_calls": len(sync_calls),
        }
    )
    result.summary = (
        f"{checked}/7 route idea groups; {modifier_total} modifier entries; "
        f"{len(swaps)} canonical swap"
    )
    return result
