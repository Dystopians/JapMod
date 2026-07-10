"""Validate the immediate, delayed, and self-healing mission refresh architecture."""

from __future__ import annotations

from .core import CheckResult, ValidationContext
from .create_legacy_bom_mission_aliases_v0241 import (
    LEGACY_BOM_SERIES,
    alias_file_name,
    render_alias,
)
from .create_mission_runtime_fingerprint_v0242 import (
    COMPANION_MAP_TRIGGER,
    DAIMYO_HOUSES,
    OUTPUT as FINGERPRINT_OUTPUT,
    render as render_fingerprint,
)
from .clausewitz import Object


def check_mission_refresh(context: ValidationContext) -> CheckResult:
    result = CheckResult("Two-phase mission refresh")
    script_files = context.script_files()
    swaps = context.assignment_occurrences(
        "swap_non_generic_missions", "yes", files=script_files
    )
    expected_sources = {
        "common/scripted_effects/jxp_scripted_effects.txt",
        "events/jxp_23_mission_refresh_events.txt",
    }
    if len(swaps) != 2:
        result.add(
            "refresh.swap_count",
            f"found {len(swaps)} executable mission swaps; expected one immediate and one delayed swap",
        )
    for occurrence in swaps:
        source = context.relative(occurrence.source)
        if source not in expected_sources:
            result.add(
                "refresh.direct_swap",
                "mission swaps must run only in the canonical helper or delayed hidden event",
                source,
                occurrence.entry.line,
            )
    if {context.relative(occurrence.source) for occurrence in swaps} != expected_sources:
        result.add(
            "refresh.phase_coverage",
            "the canonical helper and delayed event must each contain one mission swap",
        )

    helper_calls = context.assignment_occurrences(
        "jxp_refresh_route_missions_effect", "yes", files=script_files
    )
    if len(helper_calls) < 10:
        result.add(
            "refresh.helper_coverage",
            f"only {len(helper_calls)} routed refresh calls remain; expected broad route coverage",
        )

    pending_set = context.assignment_occurrences(
        "set_country_flag", "jxp_mission_refresh_pending", files=script_files
    )
    pending_clear = context.assignment_occurrences(
        "clr_country_flag", "jxp_mission_refresh_pending", files=script_files
    )
    event_ids = context.assignment_occurrences(
        "id", "jxp_mission_refresh.1", files=script_files
    )
    reconcile_event_ids = context.assignment_occurrences(
        "id", "jxp_mission_refresh.2", files=script_files
    )
    topology_migration_flags = context.assignment_occurrences(
        "set_country_flag", "jxp_mission_topology_migration_v023", files=script_files
    )
    renderer_migration_flags = context.assignment_occurrences(
        "set_country_flag", "jxp_mission_renderer_migration_v0231", files=script_files
    )
    renderer_hotfix_flags = context.assignment_occurrences(
        "set_country_flag", "jxp_mission_renderer_migration_v0233", files=script_files
    )
    expansion_migration_flags = context.assignment_occurrences(
        "set_country_flag", "jxp_mission_expansion_migration_v024", files=script_files
    )
    runtime_repair_flags = context.assignment_occurrences(
        "set_country_flag", "jxp_runtime_state_repair_v0241", files=script_files
    )
    runtime_repair_v0242_flags = context.assignment_occurrences(
        "set_country_flag", "jxp_mission_runtime_repair_v0242", files=script_files
    )
    final_tag_tree_v0250_flags = context.assignment_occurrences(
        "set_country_flag", "jxp_final_tag_tree_migration_v0250", files=script_files
    )
    if not pending_set or not pending_clear:
        result.add(
            "refresh.guard",
            "the pending refresh flag must be set by the helper and cleared by the event",
        )
    if len(event_ids) != 2:
        result.add(
            "refresh.event",
            f"found {len(event_ids)} definitions/references for jxp_mission_refresh.1; "
            "expected one scheduled call and one event definition",
        )
    if len(topology_migration_flags) != 1:
        result.add(
            "refresh.migration",
            "0.23.0 must set one old-save mission topology migration flag",
        )
    if len(renderer_migration_flags) != 1:
        result.add(
            "refresh.renderer_migration",
            "0.23.1 must set one renderer-safe mission migration flag",
        )
    if len(renderer_hotfix_flags) != 1:
        result.add(
            "refresh.renderer_hotfix_migration",
            "0.23.3 must set one strict renderer-geometry migration flag",
        )
    if len(expansion_migration_flags) != 1:
        result.add(
            "refresh.expansion_migration",
            "0.24.0 must set one five-slot mission expansion migration flag",
        )
    if len(runtime_repair_flags) != 1:
        result.add(
            "refresh.runtime_repair_migration",
            "0.24.1 must set one old-save mission/idea runtime repair flag",
        )
    if len(runtime_repair_v0242_flags) != 1:
        result.add(
            "refresh.runtime_repair_v0242_migration",
            "0.24.2 must set one mission tombstone/layout runtime repair flag",
        )
    if len(final_tag_tree_v0250_flags) != 1:
        result.add(
            "refresh.final_tag_tree_v0250_migration",
            "0.25.0 must set one compact final-tag tree migration flag",
        )
    if len(reconcile_event_ids) != 1:
        result.add(
            "refresh.reconcile_event",
            f"found {len(reconcile_event_ids)} definitions for jxp_mission_refresh.2; expected one",
        )

    startup_source = (
        context.mod_root
        / "common"
        / "on_actions"
        / "jxp_60_mission_runtime_on_actions.txt"
    )
    startup_tokens = (
        "on_startup = {",
        "jxp_migration_v023.7",
        "jxp_migration_v025.1",
        "jxp_mission_refresh.2",
        "on_religion_change = {",
        "on_government_change = {",
    )
    startup_text = (
        startup_source.read_text(encoding="utf-8") if startup_source.is_file() else ""
    )
    startup_hooks_ok = all(token in startup_text for token in startup_tokens)
    if not startup_hooks_ok:
        result.add(
            "refresh.startup_hooks",
            "mission migration/reconciliation must run on startup and refresh after external religion/government changes",
            context.relative(startup_source),
        )

    fingerprint_source = context.mod_root / FINGERPRINT_OUTPUT
    if not fingerprint_source.is_file():
        result.add(
            "refresh.fingerprint_missing",
            "the generated runtime mission fingerprint is missing",
            context.relative(fingerprint_source),
        )
        fingerprint_ok = False
    else:
        fingerprint_ok = fingerprint_source.read_text(encoding="utf-8") == render_fingerprint()
        if not fingerprint_ok:
            result.add(
                "refresh.fingerprint_drift",
                "the runtime mission fingerprint differs from its deterministic generator",
                context.relative(fingerprint_source),
            )

    trigger_definitions: set[str] = set()
    trigger_root = context.mod_root / "common" / "scripted_triggers"
    if trigger_root.is_dir():
        for source in trigger_root.glob("*.txt"):
            document = context.document(source)
            if document is None:
                continue
            trigger_definitions.update(
                entry.key
                for entry in document.root.entries
                if entry.key is not None and isinstance(entry.value, Object)
            )
    required_fingerprint_triggers = {
        COMPANION_MAP_TRIGGER,
        *(trigger for trigger, _anchor in DAIMYO_HOUSES),
    }
    missing_fingerprint_triggers = sorted(
        required_fingerprint_triggers - trigger_definitions
    )
    if missing_fingerprint_triggers:
        result.add(
            "refresh.fingerprint_trigger_missing",
            "runtime fingerprint references undefined scripted triggers: "
            + ", ".join(missing_fingerprint_triggers),
            context.relative(fingerprint_source),
        )

    bom_aliases = 0
    for series_name, slot in sorted(LEGACY_BOM_SERIES.items()):
        source = context.mod_root / "missions" / alias_file_name(series_name)
        if not source.is_file():
            result.add(
                "refresh.bom_alias_missing",
                f"missing old-save BOM mission alias for {series_name}",
                context.relative(source),
            )
            continue
        if source.read_bytes() != render_alias(series_name, slot):
            result.add(
                "refresh.bom_alias_drift",
                f"BOM mission alias for {series_name} is not the exact inactive byte fixture",
                context.relative(source),
            )
            continue
        bom_aliases += 1

    result.metrics.update(
        {
            "executable_swaps": len(swaps),
            "helper_calls": len(helper_calls),
            "pending_sets": len(pending_set),
            "pending_clears": len(pending_clear),
            "topology_migrations": len(topology_migration_flags),
            "renderer_migrations": len(renderer_migration_flags),
            "renderer_hotfix_migrations": len(renderer_hotfix_flags),
            "expansion_migrations": len(expansion_migration_flags),
            "runtime_repair_migrations": len(runtime_repair_flags),
            "runtime_repair_v0242_migrations": len(runtime_repair_v0242_flags),
            "final_tag_tree_v0250_migrations": len(final_tag_tree_v0250_flags),
            "runtime_fingerprint": fingerprint_ok,
            "fingerprint_trigger_contract": not missing_fingerprint_triggers,
            "startup_hooks": startup_hooks_ok,
            "legacy_bom_aliases": bom_aliases,
        }
    )
    migrations_present = bool(
        topology_migration_flags
        and renderer_migration_flags
        and renderer_hotfix_flags
        and expansion_migration_flags
        and runtime_repair_flags
        and runtime_repair_v0242_flags
        and final_tag_tree_v0250_flags
    )
    result.summary = (
        f"{len(swaps)} two-phase swaps; {len(helper_calls)} routed refresh calls; "
        f"runtime fingerprint {'exact' if fingerprint_ok else 'invalid'}; "
        f"{bom_aliases}/{len(LEGACY_BOM_SERIES)} legacy BOM aliases; "
        f"old-save migrations {'present' if migrations_present else 'missing'}"
    )
    return result
