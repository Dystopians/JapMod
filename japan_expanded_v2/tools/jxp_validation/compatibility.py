"""Release compatibility checks for dynamic tooltips and Celestial unlocks."""

from __future__ import annotations

from pathlib import Path

from .clausewitz import (
    Object,
    Scalar,
    bare_scalars,
    find_assignments,
    find_objects,
    first_object,
    first_scalar,
)
from .core import CheckResult, ValidationContext


HAKKO_REFORM_FILE = Path("common/imperial_reforms/jxp_08_celestial_reforms.txt")
HAKKO_MISSION_FILE = Path("missions/jxp_03_overseas_missions.txt")
HAKKO_CATCHUP_FILE = Path("events/jxp_23_celestial_compat_events.txt")
HAKKO_EFFECT_FILE = Path("common/scripted_effects/jxp_08_celestial_effects.txt")
HAKKO_REWARD_FILE = Path("common/scripted_effects/jxp_03_overseas_effects.txt")
HAKKO_ON_ACTION_FILE = Path("common/on_actions/jxp_60_mission_runtime_on_actions.txt")
LEGACY_EFFECT_FILE = Path("common/scripted_effects/jxp_50_legacy_cabinet_effects.txt")
HAKKO_UNLOCK_FLAG = "jxp_unlocked_hakko_ichiu_reform"
HAKKO_MISSION = "jxp_mission_eastasia_claim_mandate"
HAKKO_UNLOCK_EFFECT = "jxp_unlock_hakko_ichiu_reform_effect"
HAKKO_RECONCILE_EFFECT = "jxp_reconcile_hakko_ichiu_reform_visibility_effect"
HAKKO_MIGRATION_FLAG = "jxp_hakko_visibility_reconciled_v0260"
HAKKO_FALLBACK_FLAG = "jxp_mandate_claim_fallback"
LEGACY_EFFECT_TOOLTIPS = {
    "jxp_50_execute_founder_legacy_effect": "jxp_legacy_cabinet_founder_legacy_dispatch_tt",
    "jxp_50_execute_founder_idea_effect": "jxp_legacy_cabinet_founder_idea_dispatch_tt",
    "jxp_50_execute_preunification_memory_effect": "jxp_legacy_cabinet_preunification_dispatch_tt",
    "jxp_50_execute_house_diet_legacy_effect": "jxp_legacy_cabinet_house_diet_dispatch_tt",
    "jxp_50_execute_route_house_compromise_effect": "jxp_legacy_cabinet_route_house_dispatch_tt",
}


def _top_objects(obj: Object, key: str) -> tuple[Object, ...]:
    return tuple(
        entry.value
        for entry in obj.entries
        if entry.key == key
        and entry.operator == "="
        and isinstance(entry.value, Object)
    )


def _has(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any(True for _path, _entry in find_assignments(obj, key, value))


def _event_by_id(root: Object, event_id: str) -> Object | None:
    for event in _top_objects(root, "country_event"):
        if first_scalar(event, "id") == event_id:
            return event
    return None


def _has_direct(obj: Object | None, key: str, value: str) -> bool:
    """Return whether ``key = value`` is a direct, positive assignment."""

    if obj is None:
        return False
    return any(
        entry.key == key
        and entry.operator == "="
        and isinstance(entry.value, Scalar)
        and entry.value.text == value
        for entry in obj.entries
    )


def _direct_objects(obj: Object | None, key: str) -> tuple[Object, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value
        for entry in obj.entries
        if entry.key == key
        and entry.operator == "="
        and isinstance(entry.value, Object)
    )


def _has_direct_object_with_all(
    obj: Object | None,
    object_key: str,
    assignments: tuple[tuple[str, str], ...],
) -> bool:
    """Require an exact scalar contract inside the same positive object."""

    return any(
        len(block.entries) == len(assignments)
        and sorted(
            (entry.key, entry.value.text)
            for entry in block.entries
            if entry.operator == "=" and isinstance(entry.value, Scalar)
        )
        == sorted(assignments)
        for block in _direct_objects(obj, object_key)
    )


def _has_direct_not(obj: Object | None, key: str, value: str) -> bool:
    return any(
        len(block.entries) == 1 and _has_direct(block, key, value)
        for block in _direct_objects(obj, "NOT")
    )


def _guarded_effect_blocks(
    obj: Object | None,
    *,
    guards: tuple[tuple[str, str], ...] = (),
    negated_guards: tuple[tuple[str, str], ...] = (),
    effects: tuple[tuple[str, str], ...] = (),
    alternatives: tuple[tuple[str, str], ...] = (),
) -> tuple[Object, ...]:
    """Find direct ``if`` blocks whose sole ``limit`` exactly matches the contract."""

    matches: list[Object] = []
    for block in _direct_objects(obj, "if"):
        limit_entries = tuple(entry for entry in block.entries if entry.key == "limit")
        if (
            len(limit_entries) != 1
            or limit_entries[0].operator != "="
            or not isinstance(limit_entries[0].value, Object)
        ):
            continue
        limit = limit_entries[0].value
        expected_limit_members = (
            len(guards) + len(negated_guards) + (1 if alternatives else 0)
        )
        if len(limit.entries) != expected_limit_members:
            continue
        if not all(_has_direct(limit, key, value) for key, value in guards):
            continue
        if any(_has_direct_not(limit, key, value) for key, value in guards):
            continue
        if not all(
            _has_direct_not(limit, key, value) for key, value in negated_guards
        ):
            continue
        if any(_has_direct(limit, key, value) for key, value in negated_guards):
            continue
        if alternatives and not _has_direct_object_with_all(
            limit, "OR", alternatives
        ):
            continue
        if not all(_has_direct(block, key, value) for key, value in effects):
            continue
        matches.append(block)
    return tuple(matches)


def _has_positive_object_with_direct_assignments(
    obj: Object | None,
    object_key: str,
    assignments: tuple[tuple[str, str], ...],
) -> bool:
    """Find a matching object outside any explicit ``NOT`` subtree."""

    if obj is None:
        return False
    for path, entry in find_objects(obj, object_key):
        if "NOT" in path or entry.operator != "=":
            continue
        if isinstance(entry.value, Object) and all(
            _has_direct(entry.value, key, value) for key, value in assignments
        ):
            return True
    return False


def check_release_compatibility(context: ValidationContext) -> CheckResult:
    result = CheckResult("Celestial unlock and dynamic tooltip compatibility")

    invalid_reform_progress = context.assignment_occurrences(
        "add_government_reform_progress", files=context.script_files()
    )
    for occurrence in invalid_reform_progress:
        result.add(
            "compat.invalid_reform_progress_effect",
            "EU4 1.37.5 uses change_government_reform_progress; "
            "add_government_reform_progress is not a valid effect",
            context.relative(occurrence.source),
            occurrence.entry.line,
        )

    reform_source = context.mod_root / HAKKO_REFORM_FILE
    reform_document = context.document(reform_source) if reform_source.is_file() else None
    reform = (
        first_object(reform_document.root, "jxp_hakko_ichiu_reform")
        if reform_document is not None
        else None
    )
    if reform is None:
        result.add(
            "compat.hakko_reform_missing",
            "jxp_hakko_ichiu_reform is missing or unparseable",
            HAKKO_REFORM_FILE.as_posix(),
        )
    else:
        potential = first_object(reform, "potential")
        trigger = first_object(reform, "trigger")
        if not _has_direct(potential, "jxp_is_japanese_polity_trigger", "yes"):
            result.add(
                "compat.hakko_potential_identity",
                "Hakko Ichiu potential must use stable Japanese-polity identity",
                HAKKO_REFORM_FILE.as_posix(),
            )
        for key, value in (
            ("has_country_flag", HAKKO_UNLOCK_FLAG),
            ("mission_completed", HAKKO_MISSION),
            ("has_dlc", "Mandate of Heaven"),
            ("is_emperor_of_china", "yes"),
        ):
            if _has(potential, key, value):
                result.add(
                    "compat.hakko_dynamic_potential",
                    f"Hakko Ichiu potential must not cache dynamic gate {key} = {value}",
                    HAKKO_REFORM_FILE.as_posix(),
                )
        for key, value, code in (
            ("has_dlc", "Mandate of Heaven", "compat.hakko_dlc_trigger"),
            (
                "jxp_is_japanese_polity_trigger",
                "yes",
                "compat.hakko_identity_trigger",
            ),
            ("is_emperor_of_china", "yes", "compat.hakko_emperor_trigger"),
        ):
            if not _has_direct(trigger, key, value):
                result.add(
                    code,
                    f"Hakko Ichiu trigger lacks {key} = {value}",
                    HAKKO_REFORM_FILE.as_posix(),
                )
        unlock_alternatives = (
            ("has_country_flag", HAKKO_UNLOCK_FLAG),
            ("mission_completed", HAKKO_MISSION),
        )
        if not any(
            _has_direct_object_with_all(tooltip, "OR", unlock_alternatives)
            for tooltip in _direct_objects(trigger, "custom_trigger_tooltip")
        ):
            result.add(
                "compat.hakko_unlock_or",
                "Hakko Ichiu must accept either the persistent flag or completed mission",
                HAKKO_REFORM_FILE.as_posix(),
            )

    mission_source = context.mod_root / HAKKO_MISSION_FILE
    mission_document = context.document(mission_source) if mission_source.is_file() else None
    mission: Object | None = None
    if mission_document is not None:
        matches = tuple(find_objects(mission_document.root, HAKKO_MISSION))
        if len(matches) == 1 and isinstance(matches[0][1].value, Object):
            mission = matches[0][1].value
    mission_effect = first_object(mission, "effect")
    if not _guarded_effect_blocks(
        mission_effect,
        guards=(("has_dlc", "Mandate of Heaven"),),
        effects=((HAKKO_UNLOCK_EFFECT, "yes"),),
    ):
        result.add(
            "compat.hakko_mission_reward",
            "the mandate-claim mission lacks a DLC-guarded persistent Hakko unlock",
            HAKKO_MISSION_FILE.as_posix(),
        )

    effect_source = context.mod_root / HAKKO_EFFECT_FILE
    effect_document = context.document(effect_source) if effect_source.is_file() else None
    unlock_effect = (
        first_object(effect_document.root, HAKKO_UNLOCK_EFFECT)
        if effect_document is not None
        else None
    )
    reconcile_effect = (
        first_object(effect_document.root, HAKKO_RECONCILE_EFFECT)
        if effect_document is not None
        else None
    )
    if unlock_effect is None:
        result.add(
            "compat.hakko_effect_missing",
            f"missing scripted effect {HAKKO_UNLOCK_EFFECT}",
            HAKKO_EFFECT_FILE.as_posix(),
        )
    else:
        unlock_hidden = first_object(unlock_effect, "hidden_effect")
        if not (
            _has_direct(unlock_hidden, "set_country_flag", HAKKO_UNLOCK_FLAG)
            and _has_direct(unlock_hidden, HAKKO_RECONCILE_EFFECT, "yes")
        ):
            result.add(
                "compat.hakko_effect_contract",
                f"{HAKKO_UNLOCK_EFFECT} must persist and reconcile inside hidden_effect",
                HAKKO_EFFECT_FILE.as_posix(),
            )

    reconcile_blocks: tuple[Object, ...] = ()
    if reconcile_effect is None:
        result.add(
            "compat.hakko_effect_missing",
            f"missing scripted effect {HAKKO_RECONCILE_EFFECT}",
            HAKKO_EFFECT_FILE.as_posix(),
        )
    else:
        reconcile_hidden = first_object(reconcile_effect, "hidden_effect")
        reconcile_blocks = _guarded_effect_blocks(
            reconcile_hidden,
            guards=(
                ("has_dlc", "Mandate of Heaven"),
                ("jxp_is_japanese_polity_trigger", "yes"),
                ("is_emperor_of_china", "yes"),
            ),
            effects=(
                ("regenerate_government_mechanics", "yes"),
                ("set_country_flag", HAKKO_MIGRATION_FLAG),
            ),
            alternatives=(
                ("has_country_flag", HAKKO_UNLOCK_FLAG),
                ("mission_completed", HAKKO_MISSION),
            ),
        )
        recovers_missing_flag = any(
            _guarded_effect_blocks(
                block,
                negated_guards=(("has_country_flag", HAKKO_UNLOCK_FLAG),),
                effects=(("set_country_flag", HAKKO_UNLOCK_FLAG),),
            )
            for block in reconcile_blocks
        )
        if not reconcile_blocks or not recovers_missing_flag:
            result.add(
                "compat.hakko_effect_contract",
                f"{HAKKO_RECONCILE_EFFECT} has an invalid guard/effect hierarchy or polarity",
                HAKKO_EFFECT_FILE.as_posix(),
            )
    if reconcile_effect is not None and not reconcile_blocks:
        result.add(
            "compat.hakko_reconcile_or",
            "Hakko reconciliation requires direct persisted/mission alternatives "
            "in its positive limit",
            HAKKO_EFFECT_FILE.as_posix(),
        )

    catchup_source = context.mod_root / HAKKO_CATCHUP_FILE
    catchup_document = context.document(catchup_source) if catchup_source.is_file() else None
    catchup = (
        _event_by_id(catchup_document.root, "jxp_celestial_compat.1")
        if catchup_document is not None
        else None
    )
    catchup_trigger = first_object(catchup, "trigger")
    catchup_mtth = first_object(catchup, "mean_time_to_happen")
    catchup_immediate = first_object(catchup, "immediate")
    if not (
        _has_direct(catchup, "hidden", "yes")
        and _has_direct(catchup_mtth, "days", "1")
        and _has_direct(catchup_trigger, "has_dlc", "Mandate of Heaven")
        and _has_direct(
            catchup_trigger, "jxp_is_japanese_polity_trigger", "yes"
        )
        and _has_direct(catchup_trigger, "is_emperor_of_china", "yes")
        and _has_direct_object_with_all(
            catchup_trigger,
            "OR",
            (
                ("mission_completed", HAKKO_MISSION),
                ("has_country_flag", HAKKO_UNLOCK_FLAG),
            ),
        )
        and _has_direct_not(
            catchup_trigger, "has_country_flag", HAKKO_MIGRATION_FLAG
        )
        and _has_direct(catchup_immediate, HAKKO_RECONCILE_EFFECT, "yes")
    ):
        result.add(
            "compat.hakko_catchup",
            "old saves need a one-day persisted/mission unlock reconciliation event",
            HAKKO_CATCHUP_FILE.as_posix(),
        )

    on_action_source = context.mod_root / HAKKO_ON_ACTION_FILE
    on_action_document = (
        context.document(on_action_source) if on_action_source.is_file() else None
    )
    on_action_root = on_action_document.root if on_action_document is not None else None
    startup = first_object(on_action_root, "on_startup")
    startup_events = first_object(startup, "events")
    startup_ids = {value.text for value in bare_scalars(startup_events)}
    government_change = first_object(on_action_root, "on_government_change")
    if "jxp_celestial_compat.1" not in startup_ids:
        result.add(
            "compat.hakko_startup_migration",
            "Hakko visibility reconciliation must run on startup for old saves",
            HAKKO_ON_ACTION_FILE.as_posix(),
        )
    if not _guarded_effect_blocks(
        government_change,
        guards=(("jxp_is_japanese_polity_trigger", "yes"),),
        effects=((HAKKO_RECONCILE_EFFECT, "yes"),),
    ):
        result.add(
            "compat.hakko_government_change",
            "government changes must reconcile cached Hakko visibility",
            HAKKO_ON_ACTION_FILE.as_posix(),
        )

    reward_source = context.mod_root / HAKKO_REWARD_FILE
    reward_document = context.document(reward_source) if reward_source.is_file() else None
    claim_reward = (
        first_object(reward_document.root, "jxp_apply_mandate_claim_reward_effect")
        if reward_document is not None
        else None
    )
    primary_reward = _guarded_effect_blocks(
        claim_reward,
        guards=(
            ("has_dlc", "Mandate of Heaven"),
            ("is_emperor_of_china", "yes"),
        ),
    )
    fallback_branches = _direct_objects(claim_reward, "else")
    fallback_ok = any(
        _has_direct(branch, "set_country_flag", HAKKO_FALLBACK_FLAG)
        and _has_positive_object_with_direct_assignments(
            branch,
            "add_country_modifier",
            (("name", "jxp_celestial_diplomacy"),),
        )
        and _has_positive_object_with_direct_assignments(
            branch,
            "add_country_modifier",
            (("name", "jxp_solar_court_recognition"),),
        )
        for branch in fallback_branches
    )
    if not primary_reward or not fallback_ok:
        result.add(
            "compat.hakko_no_dlc_fallback",
            "Mandate reward requires a positive DLC/emperor branch and direct "
            "no-DLC else fallback",
            HAKKO_REWARD_FILE.as_posix(),
        )

    legacy_source = context.mod_root / LEGACY_EFFECT_FILE
    legacy_document = context.document(legacy_source) if legacy_source.is_file() else None
    protected_effects = 0
    for effect_name, tooltip_key in LEGACY_EFFECT_TOOLTIPS.items():
        effect = (
            first_object(legacy_document.root, effect_name)
            if legacy_document is not None
            else None
        )
        if effect is None:
            result.add(
                "compat.legacy_effect_missing",
                f"missing legacy cabinet effect {effect_name}",
                LEGACY_EFFECT_FILE.as_posix(),
            )
            continue
        if first_scalar(effect, "custom_tooltip") != tooltip_key:
            result.add(
                "compat.legacy_tooltip",
                f"{effect_name} lacks stable tooltip {tooltip_key}",
                LEGACY_EFFECT_FILE.as_posix(),
            )
        hidden = first_object(effect, "hidden_effect")
        all_dispatches = tuple(find_objects(effect, "country_event"))
        hidden_dispatches = tuple(find_objects(hidden, "country_event")) if hidden is not None else ()
        if not all_dispatches or len(all_dispatches) != len(hidden_dispatches):
            result.add(
                "compat.legacy_visible_dispatch",
                f"all dynamic country_event dispatches in {effect_name} must be inside hidden_effect",
                LEGACY_EFFECT_FILE.as_posix(),
            )
        else:
            protected_effects += 1

    result.metrics.update(
        {
            "hakko_visible_when_locked": reform is not None
            and not _has(
                first_object(reform, "potential"),
                "has_country_flag",
                HAKKO_UNLOCK_FLAG,
            ),
            "hakko_cached_visibility_reconciled": reconcile_effect is not None
            and bool(reconcile_blocks),
            "legacy_tooltips_protected": protected_effects,
            "invalid_reform_progress_effects": len(invalid_reform_progress),
        }
    )
    result.summary = (
        f"Hakko Ichiu unlock/fallback/cache reconciliation; {protected_effects}/"
        f"{len(LEGACY_EFFECT_TOOLTIPS)} dynamic legacy tooltips protected"
    )
    return result
