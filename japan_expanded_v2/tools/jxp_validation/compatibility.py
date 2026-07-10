"""Release compatibility checks for dynamic tooltips and Celestial unlocks."""

from __future__ import annotations

from pathlib import Path

from .clausewitz import Object, find_assignments, find_objects, first_object, first_scalar
from .core import CheckResult, ValidationContext


HAKKO_REFORM_FILE = Path("common/imperial_reforms/jxp_08_celestial_reforms.txt")
HAKKO_MISSION_FILE = Path("missions/jxp_03_overseas_missions.txt")
HAKKO_CATCHUP_FILE = Path("events/jxp_23_celestial_compat_events.txt")
LEGACY_EFFECT_FILE = Path("common/scripted_effects/jxp_50_legacy_cabinet_effects.txt")
HAKKO_UNLOCK_FLAG = "jxp_unlocked_hakko_ichiu_reform"
HAKKO_MISSION = "jxp_mission_eastasia_claim_mandate"
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
        if entry.key == key and isinstance(entry.value, Object)
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
        if _has(potential, "has_country_flag", HAKKO_UNLOCK_FLAG):
            result.add(
                "compat.hakko_hidden",
                "Hakko Ichiu potential must not hide the reform behind its unlock flag",
                HAKKO_REFORM_FILE.as_posix(),
            )
        for key, value, code in (
            ("has_country_flag", HAKKO_UNLOCK_FLAG, "compat.hakko_flag_trigger"),
            ("mission_completed", HAKKO_MISSION, "compat.hakko_mission_trigger"),
        ):
            if not _has(trigger, key, value):
                result.add(
                    code,
                    f"Hakko Ichiu trigger lacks {key} = {value}",
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
    if not _has(mission_effect, "jxp_unlock_hakko_ichiu_reform_effect", "yes"):
        result.add(
            "compat.hakko_mission_reward",
            "the mandate-claim mission does not persistently unlock Hakko Ichiu",
            HAKKO_MISSION_FILE.as_posix(),
        )

    catchup_source = context.mod_root / HAKKO_CATCHUP_FILE
    catchup_document = context.document(catchup_source) if catchup_source.is_file() else None
    catchup = (
        _event_by_id(catchup_document.root, "jxp_celestial_compat.1")
        if catchup_document is not None
        else None
    )
    if not (
        _has(catchup, "mission_completed", HAKKO_MISSION)
        and _has(catchup, "set_country_flag", HAKKO_UNLOCK_FLAG)
    ):
        result.add(
            "compat.hakko_catchup",
            "old saves need a hidden mission-completion catch-up event for Hakko Ichiu",
            HAKKO_CATCHUP_FILE.as_posix(),
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
            and not _has(first_object(reform, "potential"), "has_country_flag", HAKKO_UNLOCK_FLAG),
            "legacy_tooltips_protected": protected_effects,
            "invalid_reform_progress_effects": len(invalid_reform_progress),
        }
    )
    result.summary = (
        f"Hakko Ichiu old-save unlock path; {protected_effects}/"
        f"{len(LEGACY_EFFECT_TOOLTIPS)} dynamic legacy tooltips protected"
    )
    return result
