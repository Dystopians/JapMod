"""Confucian-Shinto bridge and native conversion-center checks."""

from __future__ import annotations

from pathlib import Path

from .clausewitz import (
    Entry,
    Object,
    Scalar,
    bare_scalars,
    entries_named,
    find_assignments,
    find_objects,
    first_object,
    first_scalar,
)
from .core import CheckResult, ValidationContext


RELIGION_FILE = Path("common/religions/00_religion.txt")
CONVERSION_DIRECTORY = Path("common/religious_conversions")
BRIDGE_EFFECT_FILE = Path("common/scripted_effects/jxp_07_confucian_religion_effects.txt")
BRIDGE_TRIGGER_FILE = Path("common/scripted_triggers/jxp_13_confucian_shinto_triggers.txt")
BRIDGE_EVENT_FILES = (
    Path("events/jxp_confucian_shinto_bridge_events.txt"),
    Path("events/jxp_22_confucian_incident_bridge_events.txt"),
)
DEBUG_DECISION_FILE = Path("decisions/jxp_debug_decisions.txt")
BRIDGE_DECISION_FILE = Path("decisions/jxp_23_confucian_incident_decisions.txt")
CONVERSION_ID = "confucianism_center_of_reformation"
BRIDGE_CHAINS = (
    ("jxp_confucian_shinto.1", "jxp_confucian_shinto.2", "jxp_confucian_shinto.3"),
    ("jxp_confucian_shinto.10", "jxp_confucian_shinto.11", "jxp_confucian_shinto.12"),
    (
        "jxp_confucian_shinto.20",
        "jxp_confucian_shinto.21",
        "jxp_confucian_shinto.22",
        "jxp_confucian_shinto.23",
    ),
    ("jxp_confucian_incident.1", "jxp_confucian_incident.2"),
    ("jxp_confucian_incident.10", "jxp_confucian_incident.11"),
    ("jxp_confucian_incident.20", "jxp_confucian_incident.21"),
    ("jxp_confucian_incident.30", "jxp_confucian_incident.31"),
    ("jxp_confucian_incident.40", "jxp_confucian_incident.41"),
)
BRIDGE_STARTS = {
    "jxp_confucian_shinto.1": "jxp_confucian_bridge_neo_available_trigger",
    "jxp_confucian_shinto.10": "jxp_confucian_bridge_urban_available_trigger",
    "jxp_confucian_shinto.20": "jxp_confucian_bridge_nanban_available_trigger",
    "jxp_confucian_incident.1": "jxp_confucian_bridge_firearms_available_trigger",
    "jxp_confucian_incident.10": "jxp_confucian_bridge_christian_available_trigger",
    "jxp_confucian_incident.20": "jxp_confucian_bridge_authority_available_trigger",
    "jxp_confucian_incident.30": "jxp_confucian_bridge_ikko_available_trigger",
    "jxp_confucian_incident.40": "jxp_confucian_bridge_wokou_available_trigger",
}
BRIDGE_STARTED_FLAGS = {
    "jxp_confucian_shinto.1": "jxp_confucian_bridge_neo_started",
    "jxp_confucian_shinto.10": "jxp_confucian_bridge_urban_started",
    "jxp_confucian_shinto.20": "jxp_confucian_bridge_nanban_started",
    "jxp_confucian_incident.1": "jxp_confucian_bridge_firearms_started",
    "jxp_confucian_incident.10": "jxp_confucian_bridge_christian_started",
    "jxp_confucian_incident.20": "jxp_confucian_bridge_authority_started",
    "jxp_confucian_incident.30": "jxp_confucian_bridge_ikko_started",
    "jxp_confucian_incident.40": "jxp_confucian_bridge_wokou_started",
}
BRIDGE_ENDS = {
    "jxp_confucian_shinto.3": "end_of_neo_confucianism_chain",
    "jxp_confucian_shinto.12": "end_of_urbanisation_chain",
    "jxp_confucian_shinto.23": "end_of_nanban_chain",
    "jxp_confucian_incident.2": "end_of_incident_firearms_chain",
    "jxp_confucian_incident.11": "end_of_incident_spread_of_christianity_chain",
    "jxp_confucian_incident.21": "end_of_incident_shogunate_authority_chain",
    "jxp_confucian_incident.31": "end_of_ikko_chain",
    "jxp_confucian_incident.41": "end_of_wokou_chain",
}
DOWNSTREAM_OUTCOME_FLAGS = {
    "jxp_confucian_shinto.23": (
        "jap_chose_kaikoku_flag",
        "jap_chose_trade_with_west_flag",
    ),
    "jxp_confucian_incident.2": (
        "perfecting_the_musket_flag",
        "example_of_bushido_flag",
    ),
    "jxp_confucian_incident.11": (
        "significant_christian_presence_flag",
        "christianity_defeated_flag",
    ),
}


def _top_objects(obj: Object, key: str) -> tuple[Entry, ...]:
    return tuple(
        entry
        for entry in obj.entries
        if entry.key == key and isinstance(entry.value, Object)
    )


def _has_assignment(
    obj: Object | None,
    key: str,
    value: str,
    ancestor: str | None = None,
) -> bool:
    if obj is None:
        return False
    return any(
        ancestor is None or ancestor in path
        for path, _entry in find_assignments(obj, key, value)
    )


def _require_assignment(
    result: CheckResult,
    context: ValidationContext,
    obj: Object | None,
    key: str,
    value: str,
    code: str,
    message: str,
    source: Path,
    ancestor: str | None = None,
) -> None:
    if not _has_assignment(obj, key, value, ancestor):
        result.add(code, message, context.relative(source))


def check_confucian_bridge(context: ValidationContext) -> CheckResult:
    result = CheckResult("Confucian bridge and native centers")

    mutations = context.assignment_occurrences("add_harmonized_religion", "shinto")
    if len(mutations) != 1:
        result.add(
            "confucian.harmonization_count",
            f"found {len(mutations)} add_harmonized_religion = shinto mutations; expected exactly one",
        )
    elif (
        context.relative(mutations[0].source) != BRIDGE_EFFECT_FILE.as_posix()
        or not mutations[0].path
        or mutations[0].path[0] != "jxp_confucian_sync_shinto_effect"
    ):
        result.add(
            "confucian.harmonization_location",
            "the sole Shinto harmonization mutation must be inside "
            "jxp_confucian_sync_shinto_effect",
            context.relative(mutations[0].source),
            mutations[0].entry.line,
        )

    removals = context.assignment_occurrences(
        "remove_country_modifier",
        "harmonized_shinto",
    )
    for occurrence in removals:
        result.add(
            "confucian.harmonized_modifier_removal",
            "remove_country_modifier = harmonized_shinto is forbidden",
            context.relative(occurrence.source),
            occurrence.entry.line,
        )

    religion_source = context.mod_root / RELIGION_FILE
    religion_document = context.document(religion_source) if religion_source.is_file() else None
    confucian: Object | None = None
    if religion_document is None:
        result.add(
            "confucian.religion_copy_missing",
            "full common/religions/00_religion.txt copy is missing or unparseable",
            RELIGION_FILE.as_posix(),
        )
    else:
        eastern_entries = _top_objects(religion_document.root, "eastern")
        if len(eastern_entries) != 1:
            result.add(
                "confucian.eastern_group_count",
                f"full religion copy has {len(eastern_entries)} eastern groups; expected one",
                RELIGION_FILE.as_posix(),
            )
        elif isinstance(eastern_entries[0].value, Object):
            confucian_entries = _top_objects(eastern_entries[0].value, "confucianism")
            if len(confucian_entries) != 1:
                result.add(
                    "confucian.religion_count",
                    f"eastern group has {len(confucian_entries)} confucianism definitions; expected one",
                    RELIGION_FILE.as_posix(),
                )
            elif isinstance(confucian_entries[0].value, Object):
                confucian = confucian_entries[0].value

        allowed = first_object(confucian, "allowed_center_conversion")
        allowed_values = {value.text for value in bare_scalars(allowed)}
        if "shinto" not in allowed_values:
            result.add(
                "confucian.allowed_center_conversion",
                "confucianism must include shinto in allowed_center_conversion",
                RELIGION_FILE.as_posix(),
            )

    conversion_root = context.mod_root / CONVERSION_DIRECTORY
    conversion_matches: list[tuple[Path, Entry]] = []
    if conversion_root.is_dir():
        for source in sorted(conversion_root.glob("*.txt"), key=lambda path: path.name.casefold()):
            document = context.document(source)
            if document is not None:
                conversion_matches.extend(
                    (source, entry) for entry in _top_objects(document.root, CONVERSION_ID)
                )
    if len(conversion_matches) != 1:
        result.add(
            "confucian.conversion_definition_count",
            f"found {len(conversion_matches)} {CONVERSION_ID} definitions; expected exactly one",
            CONVERSION_DIRECTORY.as_posix(),
        )
        conversion: Object | None = None
        conversion_source = conversion_root / "jxp_confucian_center.txt"
    else:
        conversion_source, conversion_entry = conversion_matches[0]
        conversion = conversion_entry.value if isinstance(conversion_entry.value, Object) else None

    if conversion is not None:
        if first_scalar(conversion, "religion") != "confucianism":
            result.add(
                "confucian.conversion_religion",
                f"{CONVERSION_ID} must set religion = confucianism",
                context.relative(conversion_source),
            )
        weights = first_object(conversion, "target_province_weights")
        if weights is None:
            result.add(
                "confucian.conversion_weights",
                f"{CONVERSION_ID} lacks target_province_weights",
                context.relative(conversion_source),
            )
        else:
            excludes_ise = False
            for _path, modifier_entry in find_objects(weights, "modifier"):
                modifier = modifier_entry.value
                assert isinstance(modifier, Object)
                factor = first_scalar(modifier, "factor")
                if factor in {"0", "0.0"} and _has_assignment(
                    modifier,
                    "province_id",
                    "4359",
                ):
                    excludes_ise = True
                    break
            if not excludes_ise:
                result.add(
                    "confucian.conversion_ise_exclusion",
                    "conversion target weights must give province 4359 factor 0",
                    context.relative(conversion_source),
                )
            if not _has_assignment(weights, "religion", "shinto", ancestor="NOT"):
                result.add(
                    "confucian.conversion_shinto_target",
                    "conversion target weights must reject provinces that are not Shinto",
                    context.relative(conversion_source),
                )

    effect_source = context.mod_root / BRIDGE_EFFECT_FILE
    trigger_source = context.mod_root / BRIDGE_TRIGGER_FILE
    effect_document = context.document(effect_source) if effect_source.is_file() else None
    trigger_document = context.document(trigger_source) if trigger_source.is_file() else None

    def effect(name: str) -> Object | None:
        if effect_document is None:
            return None
        matches = _top_objects(effect_document.root, name)
        if len(matches) != 1:
            result.add(
                "confucian.effect_count",
                f"found {len(matches)} {name} definitions; expected exactly one",
                BRIDGE_EFFECT_FILE.as_posix(),
            )
            return None
        value = matches[0].value
        return value if isinstance(value, Object) else None

    protect_ise = effect("jxp_confucian_protect_ise_effect")
    sync = effect("jxp_confucian_sync_shinto_effect")
    add_center = effect("jxp_add_confucian_reform_center_here_effect")
    spawn = effect("jxp_spawn_confucian_reform_centers_effect")
    remove_centers = effect("jxp_remove_confucian_native_centers_effect")

    if sync is not None and not _has_assignment(sync, "add_harmonized_religion", "shinto"):
        result.add(
            "confucian.sync_mutation_missing",
            "jxp_confucian_sync_shinto_effect lacks the Shinto harmonization mutation",
            BRIDGE_EFFECT_FILE.as_posix(),
        )

    guarded_mutation = False
    if sync is not None:
        for if_entry in _top_objects(sync, "if"):
            if_obj = if_entry.value
            assert isinstance(if_obj, Object)
            if not _has_assignment(if_obj, "add_harmonized_religion", "shinto"):
                continue
            limit = first_object(if_obj, "limit")
            if _has_assignment(
                limit,
                "has_harmonized_with",
                "shinto",
                ancestor="NOT",
            ):
                guarded_mutation = True
                break
    if not guarded_mutation:
        result.add(
            "confucian.sync_mutation_guard",
            "the Shinto harmonization mutation must be guarded by "
            "NOT = { has_harmonized_with = shinto } in the same if block",
            BRIDGE_EFFECT_FILE.as_posix(),
        )

    _require_assignment(
        result,
        context,
        protect_ise,
        "change_religion",
        "shinto",
        "confucian.ise_protection",
        "Ise protection effect must restore province 4359 to Shinto",
        effect_source,
    )
    _require_assignment(
        result,
        context,
        add_center,
        "province_id",
        "4359",
        "confucian.spawn_ise_exclusion",
        "center-creation effect must exclude province 4359",
        effect_source,
        ancestor="NOT",
    )
    _require_assignment(
        result,
        context,
        spawn,
        "province_id",
        "4359",
        "confucian.spawn_ise_exclusion",
        "center-spawning effect must exclude province 4359",
        effect_source,
        ancestor="NOT",
    )

    trigger: Object | None = None
    if trigger_document is None:
        result.add(
            "confucian.cap_trigger_missing",
            "Confucian native-center cap trigger file is missing or unparseable",
            BRIDGE_TRIGGER_FILE.as_posix(),
        )
    else:
        trigger_matches = _top_objects(
            trigger_document.root,
            "jxp_confucian_has_three_native_centers_trigger",
        )
        if len(trigger_matches) != 1:
            result.add(
                "confucian.cap_trigger_count",
                "expected exactly one jxp_confucian_has_three_native_centers_trigger",
                BRIDGE_TRIGGER_FILE.as_posix(),
            )
        else:
            trigger_value = trigger_matches[0].value
            trigger = trigger_value if isinstance(trigger_value, Object) else None

    for key, value, code, message in (
        ("amount", "3", "confucian.cap_amount", "native-center cap trigger must use amount = 3"),
        (
            "is_reformation_center",
            "yes",
            "confucian.cap_center_filter",
            "native-center cap must count active reformation centers",
        ),
        (
            "has_province_flag",
            "jxp_confucian_native_center",
            "confucian.cap_marker_filter",
            "native-center cap must count only marked native centers",
        ),
    ):
        _require_assignment(result, context, trigger, key, value, code, message, trigger_source)

    _require_assignment(
        result,
        context,
        add_center,
        "jxp_confucian_has_three_native_centers_trigger",
        "yes",
        "confucian.add_cap_guard",
        "center-creation effect lacks the three-center cap guard",
        effect_source,
        ancestor="NOT",
    )
    _require_assignment(
        result,
        context,
        spawn,
        "jxp_confucian_has_three_native_centers_trigger",
        "yes",
        "confucian.spawn_cap_guard",
        "center-spawning effect lacks the three-center cap guard",
        effect_source,
        ancestor="NOT",
    )

    for key, value, code, message in (
        (
            "add_reform_center",
            "confucianism",
            "confucian.add_center",
            "center-creation effect must add a Confucian reform center",
        ),
        (
            "set_province_flag",
            "jxp_confucian_native_center",
            "confucian.add_marker",
            "center-creation effect must mark native centers",
        ),
        (
            "name",
            "jxp_confucian_reform_center",
            "confucian.add_modifier",
            "center-creation effect must add the native-center modifier",
        ),
    ):
        _require_assignment(result, context, add_center, key, value, code, message, effect_source)

    _require_assignment(
        result,
        context,
        spawn,
        "has_country_flag",
        "jxp_confucian_native_centers_v1",
        "confucian.completion_guard",
        "center-spawning effect lacks the native_centers_v1 completion guard",
        effect_source,
        ancestor="NOT",
    )
    for key, value, code, message in (
        (
            "remove_province_modifier",
            "jxp_confucian_reform_center",
            "confucian.stale_modifier_cleanup",
            "spawn completion must clean stale unmarked center modifiers",
        ),
        (
            "set_country_flag",
            "jxp_confucian_native_centers_v1",
            "confucian.completion_marker",
            "spawn completion must set jxp_confucian_native_centers_v1",
        ),
        (
            "set_country_flag",
            "jxp_confucian_centers_established",
            "confucian.established_marker",
            "spawn completion must set jxp_confucian_centers_established",
        ),
        (
            "clr_country_flag",
            "jxp_confucian_conversion_active",
            "confucian.active_marker_cleanup",
            "spawn completion must clear jxp_confucian_conversion_active",
        ),
    ):
        _require_assignment(result, context, spawn, key, value, code, message, effect_source)

    for key, value, code, message in (
        (
            "remove_reform_center",
            "confucianism",
            "confucian.remove_center_cleanup",
            "native-center cleanup must remove Confucian reform centers",
        ),
        (
            "remove_province_modifier",
            "jxp_confucian_reform_center",
            "confucian.remove_modifier_cleanup",
            "native-center cleanup must remove center modifiers",
        ),
        (
            "clr_province_flag",
            "jxp_confucian_native_center",
            "confucian.remove_marker_cleanup",
            "native-center cleanup must clear province markers",
        ),
    ):
        _require_assignment(
            result,
            context,
            remove_centers,
            key,
            value,
            code,
            message,
            effect_source,
        )

    if trigger_document is not None:
        for trigger_name in (*BRIDGE_STARTS.values(), "jxp_confucian_any_bridge_available_trigger"):
            matches = _top_objects(trigger_document.root, trigger_name)
            if len(matches) != 1:
                result.add(
                    "confucian.bridge_trigger_count",
                    f"found {len(matches)} {trigger_name} definitions; expected exactly one",
                    BRIDGE_TRIGGER_FILE.as_posix(),
                )

    bridge_events: dict[str, tuple[Object, Path]] = {}
    for relative_source in BRIDGE_EVENT_FILES:
        source = context.mod_root / relative_source
        document = context.document(source) if source.is_file() else None
        if document is None:
            result.add(
                "confucian.bridge_event_file",
                "bridge event file is missing or unparseable",
                relative_source.as_posix(),
            )
            continue
        for event_entry in _top_objects(document.root, "country_event"):
            event = event_entry.value
            assert isinstance(event, Object)
            event_id = first_scalar(event, "id")
            if event_id is not None:
                bridge_events[event_id] = (event, relative_source)

    for event_id, trigger_name in BRIDGE_STARTS.items():
        event_record = bridge_events.get(event_id)
        if event_record is None:
            result.add(
                "confucian.bridge_start_missing",
                f"missing bridge start event {event_id}",
            )
            continue
        event, source = event_record
        event_trigger = first_object(event, "trigger")
        _require_assignment(
            result,
            context,
            event_trigger,
            trigger_name,
            "yes",
            "confucian.bridge_start_trigger",
            f"{event_id} does not use {trigger_name}",
            context.mod_root / source,
        )
        if event_trigger is not None and any(
            True for _path, _entry in find_assignments(event_trigger, "is_incident_happened")
        ):
            result.add(
                "confucian.bridge_history_block",
                f"{event_id} must not reject an incident merely because it began before conversion",
                source.as_posix(),
            )
        _require_assignment(
            result,
            context,
            event,
            "set_country_flag",
            BRIDGE_STARTED_FLAGS[event_id],
            "confucian.bridge_started_flag",
            f"{event_id} does not mark its chain as started before scheduling continuation",
            context.mod_root / source,
        )

    delayed_links = 0
    for chain in BRIDGE_CHAINS:
        for current_id, next_id in zip(chain, chain[1:]):
            event_record = bridge_events.get(current_id)
            if event_record is None:
                continue
            event, source = event_record
            options = _top_objects(event, "option")
            if not options:
                result.add(
                    "confucian.bridge_option_missing",
                    f"{current_id} has no selectable option to continue its chain",
                    source.as_posix(),
                )
                continue
            for option_entry in options:
                option = option_entry.value
                assert isinstance(option, Object)
                dispatches = tuple(find_objects(option, "country_event"))
                has_delayed_edge = any(
                    first_scalar(dispatch.value, "id") == next_id
                    and first_scalar(dispatch.value, "days") == "1095"
                    for _path, dispatch in dispatches
                    if isinstance(dispatch.value, Object)
                )
                if not has_delayed_edge:
                    result.add(
                        "confucian.bridge_continuation_edge",
                        f"an option in {current_id} does not schedule {next_id} after 1095 days",
                        source.as_posix(),
                        option_entry.line,
                    )
            delayed_links += 1

        for continuation_id in chain[1:]:
            event_record = bridge_events.get(continuation_id)
            if event_record is None:
                continue
            event, source = event_record
            _require_assignment(
                result,
                context,
                event,
                "is_triggered_only",
                "yes",
                "confucian.bridge_continuation_triggered_only",
                f"continuation {continuation_id} must fire only from its scheduled predecessor",
                context.mod_root / source,
            )
            continuation_trigger = first_object(event, "trigger")
            _require_assignment(
                result,
                context,
                continuation_trigger,
                "jxp_confucian_shinto_bridge_country_trigger",
                "yes",
                "confucian.bridge_continuation_country",
                f"continuation {continuation_id} lacks the Confucian-Shinto country guard",
                context.mod_root / source,
            )
            for blocking_key, blocking_value in (
                ("has_country_modifier", "jxp_confucian_incident_review_recent"),
                ("has_country_flag", "jxp_confucian_bridge_forced_dispatch"),
            ):
                if _has_assignment(continuation_trigger, blocking_key, blocking_value):
                    result.add(
                        "confucian.bridge_continuation_blocked",
                        f"continuation {continuation_id} must not depend on start-only cooldown/dispatch state",
                        source.as_posix(),
                    )

    for event_id, end_flag in BRIDGE_ENDS.items():
        event_record = bridge_events.get(event_id)
        if event_record is None:
            result.add(
                "confucian.bridge_end_missing",
                f"missing bridge conclusion event {event_id}",
            )
            continue
        event, source = event_record
        _require_assignment(
            result,
            context,
            event,
            "set_country_flag",
            end_flag,
            "confucian.bridge_end_flag",
            f"{event_id} does not write vanilla completion flag {end_flag}",
            context.mod_root / source,
        )
        for outcome_flag in DOWNSTREAM_OUTCOME_FLAGS.get(event_id, ()):
            _require_assignment(
                result,
                context,
                event,
                "set_country_flag",
                outcome_flag,
                "confucian.bridge_outcome_flag",
                f"{event_id} does not write downstream outcome flag {outcome_flag}",
                context.mod_root / source,
            )

    migration_record = bridge_events.get("jxp_confucian_incident.98")
    if migration_record is None or not _has_assignment(
        migration_record[0],
        "set_country_flag",
        "jxp_confucian_bridge_incident_state_v0231",
    ):
        result.add(
            "confucian.bridge_migration",
            "old-save bridge state migration event jxp_confucian_incident.98 is missing",
            BRIDGE_EVENT_FILES[1].as_posix(),
        )

    debug_source = context.mod_root / DEBUG_DECISION_FILE
    debug_document = context.document(debug_source) if debug_source.is_file() else None
    debug_covered = 0
    for event_id in BRIDGE_STARTS:
        if debug_document is not None and _has_assignment(
            debug_document.root,
            "id",
            event_id,
            ancestor="country_event",
        ):
            debug_covered += 1
        else:
            result.add(
                "confucian.bridge_debug_coverage",
                f"debug decisions do not expose bridge start {event_id}",
                DEBUG_DECISION_FILE.as_posix(),
            )

    bridge_decision_source = context.mod_root / BRIDGE_DECISION_FILE
    bridge_decision_document = (
        context.document(bridge_decision_source)
        if bridge_decision_source.is_file()
        else None
    )
    for event_id in BRIDGE_STARTS:
        if bridge_decision_document is None or not _has_assignment(
            bridge_decision_document.root,
            "id",
            event_id,
            ancestor="country_event",
        ):
            result.add(
                "confucian.bridge_player_dispatch",
                f"normal continuation decision does not dispatch bridge start {event_id}",
                BRIDGE_DECISION_FILE.as_posix(),
            )

    cleanup_record = bridge_events.get("jxp_confucian_incident.99")
    if cleanup_record is None or not _has_assignment(
        cleanup_record[0],
        "clr_country_flag",
        "jxp_confucian_bridge_forced_dispatch",
    ):
        result.add(
            "confucian.bridge_dispatch_cleanup",
            "dispatch cleanup event must clear only the temporary forced-dispatch gate",
            BRIDGE_EVENT_FILES[1].as_posix(),
        )

    result.metrics.update(
        {
            "harmonization_mutations": len(mutations),
            "forbidden_modifier_removals": len(removals),
            "conversion_definitions": len(conversion_matches),
            "native_center_cap": 3,
            "bridge_chains": len(BRIDGE_STARTS),
            "bridge_delayed_links": delayed_links,
            "bridge_debug_entries": debug_covered,
        }
    )
    result.summary = (
        f"{len(mutations)} Shinto harmonization mutation; "
        f"{len(BRIDGE_STARTS)} inherited incident chains with {delayed_links} delayed links; "
        f"{len(conversion_matches)} custom conversion definition; cap 3"
    )
    return result
