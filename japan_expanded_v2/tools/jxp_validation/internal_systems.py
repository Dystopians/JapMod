"""Validate Agent A's simulated nested-lord and internal-war contracts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Mapping

from .core import CheckResult, ValidationContext


PLAN_FILE = Path("tools/jxp_a_internal_builder/internal_system_plan.json")
TRIGGER_FILE = Path("common/scripted_triggers/jxp_a_92_nested_lord_triggers.txt")
EFFECT_FILE = Path("common/scripted_effects/jxp_a_92_nested_lord_effects.txt")
ACTION_FILE = Path("common/new_diplomatic_actions/jxp_a_92_nested_lord_actions.txt")
ON_ACTION_FILE = Path("common/on_actions/jxp_a_92_nested_lord_on_actions.txt")
EVENT_FILE = Path("events/jxp_a_92_nested_lords.txt")
CB_FILE = Path("common/cb_types/jxp_a_93_internal_war_cb_types.txt")
WARGOAL_FILE = Path("common/wargoal_types/jxp_a_93_internal_war_wargoals.txt")
PATCHED_REGISTRY = Path("common/wargoal_types/00_wargoal_types.txt")
WAR_ACTION_FILE = Path("common/new_diplomatic_actions/jxp_a_93_internal_war_actions.txt")
WAR_ON_ACTION_FILE = Path("common/on_actions/jxp_a_93_internal_war_on_actions.txt")
SOURCE_LOC_FILE = Path("localisation_source/jxp_a_92_93_internal_systems_l_english_utf8_source.yml")
ACTIVE_LOC_FILE = Path("localisation/jxp_a_92_93_internal_systems_l_english.yml")
BUILDER_FILE = Path("tools/jxp_a_internal_builder/build_internal_wargoals.py")

TEXT_FILES = (
    TRIGGER_FILE,
    EFFECT_FILE,
    ACTION_FILE,
    ON_ACTION_FILE,
    EVENT_FILE,
    CB_FILE,
    WARGOAL_FILE,
    PATCHED_REGISTRY,
    WAR_ACTION_FILE,
    WAR_ON_ACTION_FILE,
    SOURCE_LOC_FILE,
)


def load_payload(mod_root: Path) -> dict[str, str]:
    return {
        path.as_posix(): (mod_root / path).read_text(encoding="utf-8-sig")
        for path in TEXT_FILES
    }


def _require(
    issues: list[str],
    code: str,
    text: str,
    needles: tuple[str, ...],
) -> None:
    if any(needle not in text for needle in needles):
        issues.append(code)


def audit_payload(payload: Mapping[str, str], plan: Mapping[str, object]) -> list[str]:
    issues: list[str] = []
    if plan.get("implementation_path") != "B" or plan.get("native_nested_subject_type") is not False:
        issues.append("internal_systems.path_b")

    relationship = plan.get("relationship_authority")
    if not isinstance(relationship, dict) or set(relationship) != {
        "client_flag",
        "client_to_patron_opinion",
        "patron_to_client_opinion",
        "cache_variable",
    }:
        issues.append("internal_systems.relationship_authority")

    capacity = plan.get("capacity")
    if capacity != {"base": 1, "development_step": 100, "hard_cap": 3, "ai_cap": 2}:
        issues.append("internal_systems.capacity_plan")

    trigger = payload.get(TRIGGER_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.capacity_runtime",
        trigger,
        (
            "jxp_a_nested_has_capacity_trigger = {",
            "total_development = 100",
            "total_development = 200",
            "which = jxp_a_nested_client_count\n\t\t\tvalue = 3",
            "which = jxp_a_nested_client_count\n\t\t\t\tvalue = 2",
            "ai = no",
        ),
    )
    _require(
        issues,
        "internal_systems.stage_scope",
        trigger,
        (
            "culture_group = japanese_g",
            "has_reform = daimyo",
            "jxp_is_daimyo_stage_trigger = yes",
            "capital_scope = { region = japan_region }",
            "NOT = { owns = 1020 }",
            "NOT = { total_development = 41 }",
        ),
    )

    effects = payload.get(EFFECT_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.rebuild_cleanup",
        effects,
        (
            "jxp_a_rebuild_nested_client_cache_effect = {",
            "jxp_a_clear_nested_relations_effect = {",
            "jxp_a_reconcile_nested_relations_effect = {",
            "has_opinion_modifier = {",
            "clr_country_flag = jxp_a_nested_client",
            "set_variable = {\n\t\twhich = jxp_a_nested_client_count\n\t\tvalue = 0",
            "which = jxp_a_nested_client_count\n\t\t\t\t\t\tvalue = 4",
            "NOT = { total_development = 100 }",
            "NOT = { total_development = 200 }",
        ),
    )

    nested_actions = payload.get(ACTION_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.actions",
        nested_actions,
        (
            "jxp_a_establish_kokujin_relation = {",
            "jxp_a_release_kokujin_relation = {",
            "jxp_a_request_kokujin_defection = {",
            "jxp_a_shogunal_adjudicate_kokujin = {",
            "jxp_a_request_kokujin_military_service = {",
            "modifier = jxp_a_opinion_kokujin_patron",
            "modifier = jxp_a_opinion_protected_kokujin",
        ),
    )
    for forbidden in (
        "create_subject",
        "subject_type =",
        "join_all_offensive_wars",
        "join_all_defensive_wars",
        "join_all_wars",
        "add_permanent_claim",
    ):
        if forbidden in nested_actions:
            issues.append("internal_systems.native_or_global_leak")

    on_actions = payload.get(ON_ACTION_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.pulses",
        on_actions,
        (
            "on_startup = {",
            "on_yearly_pulse = {",
            "jxp_a_reconcile_nested_relations_effect = yes",
            "jxp_nested_lords.1",
        ),
    )
    event = payload.get(EVENT_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.ai_cap",
        event,
        (
            "ai = yes",
            "jxp_a_nested_has_capacity_trigger = yes",
            "has_opinion = { who = ROOT value = 150 }",
            "95 = { }",
            "5 = {",
            "title = none",
            "desc = none",
            "picture = COURT_eventPicture",
            'name = "OK"',
        ),
    )

    cb_text = payload.get(CB_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.cb_scope",
        cb_text,
        (
            "cb_jxp_a_daimyo_border_dispute = {",
            "cb_jxp_a_kokujin_subjugation = {",
            "cb_jxp_a_shogunal_censure = {",
            "jxp_a_internal_war_actor_trigger = yes",
            "jxp_a_internal_war_target_trigger = yes",
            "has_reform = shogunate",
        ),
    )

    wargoals = payload.get(WARGOAL_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.wargoal_balance",
        wargoals,
        (
            "jxp_a_daimyo_border_dispute = {",
            "badboy_factor = 0.70",
            "peace_cost_factor = 0.85",
            "jxp_a_kokujin_subjugation = {",
            "peace_cost_factor = 0.90",
            "jxp_a_shogunal_censure = {",
            "badboy_factor = 0.75",
        ),
    )
    if wargoals.count("region = japan_region") != 3 or wargoals.count(
        "culture_group = japanese_g"
    ) < 4:
        issues.append("internal_systems.wargoal_geography")
    for forbidden in ("add_permanent_claim", "po_make_vassal", "core_creation_cost"):
        if forbidden in wargoals:
            issues.append("internal_systems.wargoal_leak")

    registry = payload.get(PATCHED_REGISTRY.as_posix(), "")
    try:
        start = registry.index("annex_country_japan = {")
        end = registry.index("\nwar_goal_change_government = {", start)
        annex = registry[start:end]
    except ValueError:
        annex = ""
    _require(
        issues,
        "internal_systems.annex_region",
        annex,
        (
            "region = japan_region",
            "culture_group = japanese_g",
            "jxp_is_daimyo_stage_trigger = yes",
            "ROOT = { jxp_is_daimyo_stage_trigger = yes }",
        ),
    )
    if "add_permanent_claim" in annex or "core_creation_cost" in annex:
        issues.append("internal_systems.annex_leak")

    war_action = payload.get(WAR_ACTION_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.ordinary_claim",
        war_action,
        (
            "jxp_a_press_border_arbitration = {",
            "region = japan_region",
            "add_claim = ROOT",
            "duration = 1825",
        ),
    )
    if "add_permanent_claim" in war_action:
        issues.append("internal_systems.permanent_claim")

    war_on_action = payload.get(WAR_ON_ACTION_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.integration_reaction",
        war_on_action,
        (
            "on_province_owner_change = {",
            "region = japan_region",
            "add_local_autonomy = 10",
            "name = jxp_a_disputed_internal_integration",
            "duration = 3650",
        ),
    )

    localisation = payload.get(SOURCE_LOC_FILE.as_posix(), "")
    _require(
        issues,
        "internal_systems.localisation_limits",
        localisation,
        (
            "令陪臣自动加入当前或今后的全部战争",
            "把脚本关系伪装成原生属国和平条款",
            "普通宣称",
            "绝非永久宣称",
        ),
    )
    return sorted(set(issues))


def _load_builder(mod_root: Path):
    path = mod_root / BUILDER_FILE
    spec = importlib.util.spec_from_file_location("jxp_a_internal_wargoal_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_internal_systems(
    context: ValidationContext,
    game_root: Path,
) -> CheckResult:
    result = CheckResult("Agent A internal systems")
    try:
        plan = json.loads((context.mod_root / PLAN_FILE).read_text(encoding="utf-8"))
        payload = load_payload(context.mod_root)
    except (OSError, json.JSONDecodeError) as exc:
        result.add("internal_systems.input", str(exc))
        result.summary = "authoritative inputs unavailable"
        return result

    for code in audit_payload(payload, plan):
        result.add(code, "Agent A internal-system contract drifted")

    active_loc = context.mod_root / ACTIVE_LOC_FILE
    if not active_loc.is_file() or not active_loc.read_bytes().startswith(b"\xef\xbb\xbf"):
        result.add(
            "internal_systems.active_localisation",
            "active localisation must exist and use UTF-8 BOM",
            ACTIVE_LOC_FILE.as_posix(),
        )

    try:
        builder = _load_builder(context.mod_root)
        expected = builder.expected_bytes(game_root)
        actual = (context.mod_root / PATCHED_REGISTRY).read_bytes()
        if actual != expected:
            result.add(
                "internal_systems.generator_drift",
                "00_wargoal_types.txt differs from the pinned generator output",
                PATCHED_REGISTRY.as_posix(),
            )
    except (OSError, RuntimeError, ValueError) as exc:
        result.add("internal_systems.generator", str(exc), BUILDER_FILE.as_posix())

    subject_payload = "\n".join(
        path.read_text(encoding="utf-8-sig")
        for path in sorted((context.mod_root / "common/subject_types").glob("*.txt"))
    )
    if "jxp_a_nested" in subject_payload or "jxp_kokujin_client" in subject_payload:
        result.add(
            "internal_systems.native_subject",
            "path B may not register a native nested subject type",
            "common/subject_types",
        )

    pins = plan.get("vanilla_pins", {})
    subject_source = game_root / "common/subject_types/00_subject_types.txt"
    expected_subject_hash = pins.get("common/subject_types/00_subject_types.txt")
    try:
        actual_subject_hash = hashlib.sha256(subject_source.read_bytes()).hexdigest()
    except OSError as exc:
        result.add("internal_systems.subject_pin", str(exc), subject_source.as_posix())
    else:
        if actual_subject_hash != expected_subject_hash:
            result.add(
                "internal_systems.subject_pin",
                "pinned EU4 1.37.5 subject registry drifted",
                subject_source.as_posix(),
            )

    result.metrics = {
        "implementation_path": plan.get("implementation_path"),
        "hard_cap": plan.get("capacity", {}).get("hard_cap"),
        "ai_cap": plan.get("capacity", {}).get("ai_cap"),
        "wargoals": len(plan.get("internal_wargoals", {})),
    }
    result.summary = (
        "simulated one-level nested lords and three Japan-only wargoals are locked"
        if result.passed
        else f"{len(result.issues)} internal-system issue(s)"
    )
    return result
