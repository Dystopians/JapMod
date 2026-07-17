#!/usr/bin/env python3
"""Generate Agent A Tier-S/A/B daimyo-depth runtime overlays.

ODA and IMG are intentionally owned by the hand-authored A2/A3 slice.  This
generator owns the other 65 identities while preserving the existing exact
eight-node branches as prerequisites for Tier S/A overlays.
"""

from __future__ import annotations

import argparse
import importlib.util
from itertools import combinations
import json
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
MAIN_ROOT = SCRIPT_DIR.parents[1]
REPO_ROOT = MAIN_ROOT.parent
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
PLAN_PATH = SCRIPT_DIR / "daimyo_depth_plan.json"
MAJOR_PLAN_PATH = MAIN_ROOT / "tools" / "jxp_validation" / "major_daimyo_mission_plan.json"
ESCAPE_SCRIPT = REPO_ROOT / "skills" / "eu4-modding" / "scripts" / "escape_eu4_special_localisation.py"

EXTERNALLY_OWNED = {"ODA", "IMG"}
EVENT_BASE = {"main": 1000, "map": 3000}
COMMON_ANCHORS = (
    "jxp_mission_daimyo_domain_accounts",
    "jxp_mission_daimyo_castle_town",
    "jxp_mission_daimyo_town_magistrates",
    "jxp_mission_daimyo_people_of_the_domain",
    "jxp_mission_daimyo_tenka_strategy",
)
ICONS = (
    "mission_monarch_in_throne_room",
    "mission_high_income",
    "mission_assemble_an_army",
    "mission_build_up_to_force_limit",
    "mission_have_two_subjects",
    "mission_assemble_an_army",
    "mission_conquer_50_development",
    "mission_cannons_firing",
)
AXIS_BY_FLAG = {
    "jxp_iface_house_government_ready": "government",
    "jxp_iface_house_diplomacy_ready": "diplomacy",
    "jxp_iface_house_maritime_ready": "maritime",
    "jxp_iface_house_logistics_ready": "logistics",
    "jxp_iface_house_frontier_ready": "frontier",
    "jxp_iface_house_religious_ready": "religious",
    "jxp_iface_house_mass_mobilization_ready": "mobilization",
}
AXIS_TRIGGER = {
    "government": ("stability = 1", "total_development = 40"),
    "diplomacy": ("num_of_allies = 1", "prestige = 0"),
    "maritime": ("any_owned_province = { is_port = yes }", "navy_size_percentage = 0.5"),
    "logistics": ("manpower_percentage = 0.5", "treasury = 50"),
    "frontier": ("army_size_percentage = 0.75", "any_owned_province = { fort_level = 1 }"),
    "religious": ("religious_unity = 0.75", "stability = 0"),
    "mobilization": ("army_size_percentage = 0.75", "manpower_percentage = 0.5"),
}
AXIS_REWARD = {
    "government": ("add_adm_power = 40", "change_government_reform_progress = 10"),
    "diplomacy": ("add_dip_power = 40", "add_prestige = 5"),
    "maritime": ("add_dip_power = 35", "add_navy_tradition = 5"),
    "logistics": ("add_adm_power = 30", "add_manpower = 0.10"),
    "frontier": ("add_mil_power = 35", "add_army_tradition = 3"),
    "religious": ("add_adm_power = 35", "add_prestige = 5"),
    "mobilization": ("add_mil_power = 40", "add_manpower = 0.10"),
}
AXIS_MODIFIERS = {
    "government": (("governing_capacity_modifier", "0.05"), ("reform_progress_growth", "0.10")),
    "diplomacy": (("diplomatic_reputation", "1"), ("improve_relation_modifier", "0.10")),
    "maritime": (("naval_morale", "0.10"), ("global_ship_trade_power", "0.15")),
    "logistics": (("reinforce_speed", "0.10"), ("land_maintenance_modifier", "-0.05")),
    "frontier": (("defensiveness", "0.10"), ("hostile_attrition", "1")),
    "religious": (("tolerance_own", "1"), ("religious_unity", "0.10")),
    "mobilization": (("manpower_recovery_speed", "0.10"), ("land_morale", "0.05")),
}
SIGNATURE_MODIFIERS = (
    ("global_tax_modifier", "0.05", "0.10"),
    ("production_efficiency", "0.05", "0.10"),
    ("trade_efficiency", "0.05", "0.10"),
    ("global_manpower_modifier", "0.05", "0.10"),
    ("land_forcelimit_modifier", "0.05", "0.10"),
    ("naval_forcelimit_modifier", "0.05", "0.10"),
    ("global_sailors_modifier", "0.10", "0.20"),
    ("fort_maintenance_modifier", "-0.05", "-0.10"),
    ("advisor_cost", "-0.05", "-0.10"),
    ("development_cost", "-0.03", "-0.05"),
    ("build_cost", "-0.05", "-0.10"),
    ("state_maintenance_modifier", "-0.05", "-0.10"),
    ("global_trade_power", "0.05", "0.10"),
    ("core_creation", "-0.03", "-0.05"),
    ("province_warscore_cost", "-0.03", "-0.05"),
    ("technology_cost", "-0.02", "-0.04"),
    ("idea_cost", "-0.02", "-0.04"),
    ("merc_maintenance_modifier", "-0.05", "-0.10"),
    ("ship_durability", "0.03", "0.05"),
    ("siege_ability", "0.03", "0.05"),
    ("recover_army_morale_speed", "0.05", "0.10"),
    ("global_regiment_cost", "-0.05", "-0.10"),
    ("legitimacy", "0.50", "1"),
    ("prestige", "0.50", "1"),
)


def _load_escape_module():
    spec = importlib.util.spec_from_file_location("jxp_escape_localisation", ESCAPE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical EU4SpecialEscape converter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_inputs() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    major = json.loads(MAJOR_PLAN_PATH.read_text(encoding="utf-8"))
    exact = {
        record["tag"]: record
        for surface in ("main", "map")
        for record in major[surface]
    }
    return plan, exact


def axis(record: dict[str, Any]) -> str:
    for flag in record["interface_flags"]:
        if flag in AXIS_BY_FLAG:
            return AXIS_BY_FLAG[flag]
    raise ValueError(f"{record['tag']} has no supported mechanical axis")


def existing_unique(record: dict[str, Any], exact: dict[str, dict[str, Any]]) -> int:
    return len(exact[record["tag"]]["chapters"]) if record["tag"] in exact else 0


def new_count(record: dict[str, Any], exact: dict[str, dict[str, Any]]) -> int:
    return record["planned_missions"] - existing_unique(record, exact)


def validate(plan: dict[str, Any], exact: dict[str, dict[str, Any]]) -> None:
    records = plan["daimyo"]
    runtime_records = [row for row in records if row["tag"] not in EXTERNALLY_OWNED]
    if len(runtime_records) != 65:
        raise ValueError(f"runtime generator must own 65 identities, found {len(runtime_records)}")
    for record in runtime_records:
        tag = record["tag"]
        count = new_count(record, exact)
        if record["tier"] in {"S", "A"} and tag not in exact:
            raise ValueError(f"Tier {record['tier']} {tag} lacks its required exact eight-node baseline")
        if record["tier"] == "B" and tag in exact:
            raise ValueError(f"Tier B {tag} unexpectedly owns a major exact baseline")
        expected_range = {"S": (6, 10), "A": (2, 5), "B": (4, 6)}[record["tier"]]
        if not expected_range[0] <= count <= expected_range[1]:
            raise ValueError(f"{tag} net-new mission count {count} violates {record['tier']} overlay range")
        if not 3 <= record["planned_events"] <= 15:
            raise ValueError(f"{tag} event count outside supported range")
        axis(record)


def _origin_clause(record: dict[str, Any]) -> str:
    if record["surface"] == "main":
        return f"tag = {record['tag']}"
    return f"has_country_flag = jxp_map_origin_{record['tag'].lower()}"


def _mission_id(tag: str, number: int) -> str:
    return f"jxp_a_mission_{tag.lower()}_depth_{number}"


def _event_id(surface: str, record_index: int, event_index: int) -> str:
    return f"jxp_daimyo_depth.{EVENT_BASE[surface] + record_index * 20 + event_index}"


def _recovery_event_index(record: dict[str, Any]) -> int:
    return 2 if record["planned_events"] == 4 else 3


def _legacy_event_index(record: dict[str, Any]) -> int:
    return 3 if record["planned_events"] == 4 else 4


def _positions(record: dict[str, Any], slot: int, count: int) -> list[int]:
    """Keep authored edges within the pinned renderer's two-row limit."""
    if record["tier"] == "B":
        return [1 + index * 2 for index in range(count)]
    return [2 + index * 2 for index in range(count)]


def _split_overlay(count: int) -> tuple[int, int]:
    left = (count + 1) // 2
    return left, count - left


def _series_layout(record: dict[str, Any], exact: dict[str, dict[str, Any]]) -> list[tuple[int, int, int]]:
    """Return (slot, first mission number, mission count)."""
    count = new_count(record, exact)
    if record["tier"] == "B":
        return [(3, 1, count)]
    if record["tier"] == "A":
        return [(4, existing_unique(record, exact) + 1, count)]
    left, right = _split_overlay(count)
    start = existing_unique(record, exact) + 1
    result = [(2, start, left)]
    if right:
        result.append((4, start + left, right))
    return result


def _baseline_anchor(
    record: dict[str, Any],
    exact: dict[str, dict[str, Any]],
    ordinal: int,
    row: int,
) -> str:
    if record["tier"] == "B":
        return COMMON_ANCHORS[min(ordinal, len(COMMON_ANCHORS) - 1)]
    chapters = exact[record["tag"]]["chapters"]
    chapter_index = min(max((row - 1) // 2, 0), len(chapters) - 1)
    chapter = chapters[chapter_index]
    prefix = "jxp_map_mission" if record["surface"] == "map" else "jxp_mission"
    return f"{prefix}_{record['tag'].lower()}_{chapter['slug']}"


def _mission_trigger(record: dict[str, Any], ordinal: int) -> tuple[str, ...]:
    mech = axis(record)
    themed = AXIS_TRIGGER[mech]
    primary = themed[ordinal % len(themed)]
    primary_key = primary.split("=", 1)[0].strip()
    generic = (
        f"num_of_cities = {min(2 + ordinal, 10)}",
        f"total_development = {20 + ordinal * 10}",
        "prestige = 0",
        "war = no",
    )
    distinct = tuple(item for item in generic if item.split("=", 1)[0].strip() != primary_key)
    return (primary, distinct[ordinal % len(distinct)])


def _mission_effect(
    record: dict[str, Any],
    event_id: str,
    is_final: bool,
    slot: int,
    slot_stage: int,
) -> tuple[str, ...]:
    rewards = list(AXIS_REWARD[axis(record)])
    if (slot == 2 and slot_stage <= 4) or (slot == 4 and slot_stage <= 3):
        rewards.append(
            f"set_country_flag = jxp_a_depth_slot_{slot}_stage_{slot_stage}_completed"
        )
    rewards.append(f"country_event = {{ id = {event_id} }}")
    if is_final:
        rewards.append(f"jxp_a_apply_{record['tag'].lower()}_depth_legacy_effect = yes")
    return tuple(rewards)


def render_missions(surface: str, records: list[dict[str, Any]], exact: dict[str, dict[str, Any]]) -> str:
    lines = ["# Generated by build_daimyo_depth_runtime.py. Do not edit.", ""]
    surface_records = [row for row in records if row["surface"] == surface and row["tag"] not in EXTERNALLY_OWNED]
    for record_index, record in enumerate(surface_records):
        all_layout = _series_layout(record, exact)
        total_new = new_count(record, exact)
        for slot, first_number, count in all_layout:
            tag_lower = record["tag"].lower()
            lines.extend(
                (
                    f"jxp_a_{tag_lower}_depth_slot_{slot}_missions = {{",
                    f"\tslot = {slot}",
                    "\tgeneric = no",
                    "\tai = yes",
                    "\tpotential = {",
                    "\t\tNOT = { map_setup = map_setup_random }",
                    "\t\tjxp_is_daimyo_stage_trigger = yes",
                    f"\t\ttag = {record['tag']}",
                    "\t}",
                    "\thas_country_shield = yes",
                    "",
                )
            )
            positions = _positions(record, slot, count)
            for local_index in range(count):
                number = first_number + local_index
                ordinal = number - (existing_unique(record, exact) + 1 if record["tier"] != "B" else 1)
                mission_id = _mission_id(record["tag"], number)
                prior = _mission_id(record["tag"], number - 1) if local_index else None
                baseline = _baseline_anchor(record, exact, ordinal, positions[local_index])
                if number == record["planned_missions"] and record["tier"] in {"S", "A"}:
                    last = exact[record["tag"]]["chapters"][-1]
                    prefix = "jxp_map_mission" if surface == "map" else "jxp_mission"
                    baseline = f"{prefix}_{record['tag'].lower()}_{last['slug']}"
                required = [prior] if prior else []
                event_index = min(local_index + (0 if slot == all_layout[0][0] else all_layout[0][2]), record["planned_events"] - 1)
                if number == record["planned_missions"]:
                    event_index = _legacy_event_index(record)
                event_id = _event_id(surface, record_index, event_index)
                lines.extend(
                    (
                        f"\t{mission_id} = {{",
                        f"\t\ticon = {ICONS[(number - 1) % len(ICONS)]}",
                        f"\t\tposition = {positions[local_index]}",
                    )
                )
                if required:
                    lines.append(f"\t\trequired_missions = {{ {' '.join(required)} }}")
                lines.extend(("\t\ttrigger = {", f"\t\t\tmission_completed = {baseline}"))
                lines.extend(f"\t\t\t{trigger}" for trigger in _mission_trigger(record, ordinal))
                lines.extend(("\t\t}", "\t\teffect = {"))
                lines.extend(
                    f"\t\t\t{effect}"
                    for effect in _mission_effect(
                        record,
                        event_id,
                        number == record["planned_missions"],
                        slot,
                        local_index + 1,
                    )
                )
                lines.extend(("\t\t}", "\t}", ""))
            lines.extend(("}", ""))
    return "\n".join(lines)


def render_slot_triggers(records: list[dict[str, Any]]) -> str:
    def block(name: str, predicate) -> list[str]:
        chosen = [row for row in records if predicate(row)]
        lines = [f"{name} = {{", "\tOR = {"]
        lines.extend(f"\t\t{_origin_clause(row)}" for row in chosen)
        lines.extend(("\t}", "}", ""))
        return lines

    lines = ["# Generated by build_daimyo_depth_runtime.py. Do not edit.", ""]
    lines.extend(block("jxp_a_uses_depth_slot_2_trigger", lambda row: row["tier"] == "S"))
    lines.extend(block("jxp_a_uses_depth_slot_4_trigger", lambda row: row["tier"] in {"S", "A"}))
    lines.extend(block("jxp_a_uses_depth_slot_3_trigger", lambda row: row["tier"] == "B"))
    lines.extend(block("jxp_a_has_depth_identity_trigger", lambda row: True))
    contact_missions = (
        ("market_roads", 1),
        ("sakai_hakata_merchants", 2),
        ("artisan_guilds", 2),
        ("tanegashima_rumors", 3),
        ("foreign_letters", 3),
        ("licensed_caravans", 4),
    )
    society_missions = (
        ("shrine_village_compact", 1),
        ("irrigation_works", 2),
        ("town_magistrates", 2),
        ("domain_school", 2),
        ("famine_reserves", 3),
        ("people_of_the_domain", 3),
    )
    for slug, index in contact_missions:
        mission_id = f"jxp_mission_daimyo_{slug}"
        lines.extend(
            (
                f"jxp_a_depth_{slug}_completed_trigger = {{",
                "\tOR = {",
                f"\t\tmission_completed = {mission_id}",
                f"\t\thas_country_flag = jxp_a_depth_slot_2_stage_{index}_completed",
                "\t}",
                "}",
                "",
            )
        )
    for slug, index in society_missions:
        mission_id = f"jxp_mission_daimyo_{slug}"
        lines.extend(
            (
                f"jxp_a_depth_{slug}_completed_trigger = {{",
                "\tOR = {",
                f"\t\tmission_completed = {mission_id}",
                f"\t\thas_country_flag = jxp_a_depth_slot_4_stage_{index}_completed",
                "\t}",
                "}",
                "",
            )
        )
    return "\n".join(lines)


def render_modifiers(surface: str, records: list[dict[str, Any]]) -> str:
    lines = ["# Generated by build_daimyo_depth_runtime.py. Do not edit.", ""]
    for record in records:
        if record["surface"] != surface or record["tag"] in EXTERNALLY_OWNED:
            continue
        tag = record["tag"].lower()
        modifiers = AXIS_MODIFIERS[axis(record)]
        base_keys = {key for key, _ in modifiers}
        candidates = [item for item in SIGNATURE_MODIFIERS if item[0] not in base_keys]
        peers = sorted(
            row["tag"]
            for row in records
            if row["tag"] not in EXTERNALLY_OWNED and axis(row) == axis(record)
        )
        signature_pairs = list(combinations(candidates, 2))
        signature = signature_pairs[peers.index(record["tag"])]
        for suffix, scale in (("council", 1), ("command", 1), ("legacy", 2)):
            lines.append(f"jxp_a_{tag}_{suffix}_modifier = {{")
            for key, value in modifiers:
                numeric = float(value) * scale
                rendered = str(int(numeric)) if numeric.is_integer() else f"{numeric:.2f}"
                lines.append(f"\t{key} = {rendered}")
            if suffix == "command":
                lines.append("\tglobal_unrest = 1")
                lines.append(f"\t{signature[1][0]} = {signature[1][1]}")
            elif suffix == "council":
                lines.append("\tglobal_autonomy = 0.02")
                lines.append(f"\t{signature[0][0]} = {signature[0][1]}")
            else:
                for key, _, legacy_value in signature:
                    lines.append(f"\t{key} = {legacy_value}")
            lines.extend(("}", ""))
    return "\n".join(lines)


def render_effects(surface: str, records: list[dict[str, Any]]) -> str:
    surface_records = [row for row in records if row["surface"] == surface and row["tag"] not in EXTERNALLY_OWNED]
    lines = ["# Generated by build_daimyo_depth_runtime.py. Do not edit.", ""]
    for record in surface_records:
        tag = record["tag"].lower()
        lines.append(f"jxp_a_apply_{tag}_depth_legacy_effect = {{")
        for flag in record["interface_flags"]:
            capability = flag.removeprefix("jxp_iface_")
            lines.append(f"\tjxp_a_mark_{capability}_effect = yes")
        lines.extend(
            (
                f"\tadd_country_modifier = {{ name = jxp_a_{tag}_legacy_modifier duration = 9125 }}",
                "}",
                "",
            )
        )
    lines.extend((f"jxp_a_clear_{surface}_daimyo_depth_effect = {{",))
    for slot in (2, 3, 4):
        for stage in range(1, 6):
            lines.append(f"\tclr_country_flag = jxp_a_depth_slot_{slot}_stage_{stage}_completed")
    for record in surface_records:
        tag = record["tag"].lower()
        lines.extend(
            (
                f"\tremove_country_modifier = jxp_a_{tag}_council_modifier",
                f"\tremove_country_modifier = jxp_a_{tag}_command_modifier",
                f"\tremove_country_modifier = jxp_a_{tag}_legacy_modifier",
            )
        )
    lines.extend(("}", ""))
    return "\n".join(lines)


def _event_option_effects(record: dict[str, Any], event_index: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tag = record["tag"].lower()
    if event_index == 0:
        return (
            (f"add_country_modifier = {{ name = jxp_a_{tag}_council_modifier duration = -1 }}", "add_adm_power = -25"),
            (f"add_country_modifier = {{ name = jxp_a_{tag}_command_modifier duration = -1 }}", "add_mil_power = -25"),
        )
    if event_index == 1:
        return (
            ("add_stability = -1", "change_government_reform_progress = 15", "add_prestige = 5"),
            ("add_prestige = -10", "add_years_of_income = -0.10", "change_government_reform_progress = 25"),
        )
    if event_index == _recovery_event_index(record):
        return (
            ("add_stability = 1", "add_prestige = 10", "add_years_of_income = -0.10"),
            ("add_mil_power = 50", "add_army_tradition = 5", "add_war_exhaustion = 1"),
        )
    if event_index == _legacy_event_index(record):
        return (
            (f"jxp_a_apply_{tag}_depth_legacy_effect = yes", "add_prestige = 10"),
            (f"jxp_a_apply_{tag}_depth_legacy_effect = yes", "change_government_reform_progress = 15"),
        )
    primary, secondary = AXIS_REWARD[axis(record)]
    return ((primary, "add_prestige = 5"), (secondary, "add_prestige = -5"))


def render_events(surface: str, records: list[dict[str, Any]]) -> str:
    surface_records = [row for row in records if row["surface"] == surface and row["tag"] not in EXTERNALLY_OWNED]
    lines = ["# Generated by build_daimyo_depth_runtime.py. Do not edit.", "namespace = jxp_daimyo_depth", ""]
    for record_index, record in enumerate(surface_records):
        for event_index in range(record["planned_events"]):
            event_id = _event_id(surface, record_index, event_index)
            options = _event_option_effects(record, event_index)
            lines.extend(
                (
                    "country_event = {",
                    f"\tid = {event_id}",
                    f"\ttitle = {event_id}.t",
                    f"\tdesc = {event_id}.d",
                    "\tpicture = COURT_eventPicture",
                    "\tis_triggered_only = yes",
                    "\ttrigger = {",
                    "\t\tjxp_is_daimyo_stage_trigger = yes",
                    f"\t\ttag = {record['tag']}",
                    "\t}",
                    "",
                )
            )
            for option_index, effects in enumerate(options, start=1):
                lines.extend(("\toption = {", f"\t\tname = {event_id}.{option_index}"))
                lines.extend(f"\t\t{effect}" for effect in effects)
                if event_index == 1 and option_index == 1 and record["planned_events"] > 5:
                    lines.append(f"\t\tcountry_event = {{ id = {_event_id(surface, record_index, 5)} days = 365 }}")
                if event_index >= 5 and event_index + 1 < record["planned_events"] and option_index == 1:
                    lines.append(f"\t\tcountry_event = {{ id = {_event_id(surface, record_index, event_index + 1)} days = 365 }}")
                lines.extend(("\t}", ""))
            lines.extend(("}", ""))
    lines.extend(
        (
            "country_event = {",
            f"\tid = jxp_daimyo_depth.{9000 if surface == 'main' else 9001}",
            "\ttitle = none",
            "\tdesc = none",
            "\tpicture = COURT_eventPicture",
            "\thidden = yes",
            "\tis_triggered_only = yes",
            "\timmediate = {",
            "\t\tif = {",
            "\t\t\tlimit = { NOT = { jxp_is_daimyo_stage_trigger = yes } }",
            f"\t\t\tjxp_a_clear_{surface}_daimyo_depth_effect = yes",
            "\t\t}",
            "\t}",
            "\toption = { name = \"OK\" }",
            "}",
            "",
        )
    )
    return "\n".join(lines)


def render_decisions(surface: str, records: list[dict[str, Any]]) -> str:
    surface_records = [row for row in records if row["surface"] == surface and row["tag"] not in EXTERNALLY_OWNED]
    lines = ["# Generated by build_daimyo_depth_runtime.py. Do not edit.", "country_decisions = {", f"\tjxp_a_rebuild_{surface}_house = {{", "\t\tmajor = yes", "\t\tpotential = {", "\t\t\tjxp_is_daimyo_stage_trigger = yes", "\t\t\tNOT = { has_country_flag = jxp_a_house_reconstruction_used }", "\t\t\tOR = {"]
    lines.extend(f"\t\t\t\ttag = {record['tag']}" for record in surface_records)
    lines.extend(("\t\t\t}", "\t\t}", "\t\tallow = {", "\t\t\tNOT = { num_of_cities = 6 }", "\t\t\tstability = 0", "\t\t\ttreasury = 50", "\t\t}", "\t\teffect = {", "\t\t\tset_country_flag = jxp_a_house_reconstruction_used", "\t\t\tadd_treasury = -50"))
    for record_index, record in enumerate(surface_records):
        lines.extend(("\t\t\tif = {", f"\t\t\t\tlimit = {{ tag = {record['tag']} }}", f"\t\t\t\tcountry_event = {{ id = {_event_id(surface, record_index, _recovery_event_index(record))} }}", "\t\t\t}"))
    lines.extend(("\t\t}", "\t\tai_will_do = { factor = 0.20 }", "\t}", "}", ""))
    return "\n".join(lines)


def render_on_actions(surface: str) -> str:
    event_id = 9000 if surface == "main" else 9001
    return "\n".join(
        (
            "# Generated by build_daimyo_depth_runtime.py. Do not edit.",
            "on_yearly_pulse = {",
            "\tevents = {",
            f"\t\tjxp_daimyo_depth.{event_id}",
            "\t}",
            "}",
            "",
        )
    )


def _mission_title(record: dict[str, Any], number: int) -> str:
    keyword = record["keywords"][(number - 1) % len(record["keywords"])]
    verbs = ("奠定", "整饬", "经营", "调和", "裁定", "守成", "再兴", "垂范")
    return f"{verbs[(number - 1) % len(verbs)]}{keyword}"


def render_localisation(surface: str, records: list[dict[str, Any]], exact: dict[str, dict[str, Any]]) -> str:
    surface_records = [row for row in records if row["surface"] == surface and row["tag"] not in EXTERNALLY_OWNED]
    lines = ["l_english:"]
    for record_index, record in enumerate(surface_records):
        existing = existing_unique(record, exact)
        for number in range(existing + 1, record["planned_missions"] + 1):
            mission_id = _mission_id(record["tag"], number)
            keyword = record["keywords"][(number - 1) % len(record["keywords"])]
            lines.append(f" {mission_id}_title:0 \"{_mission_title(record, number)}\"")
            lines.append(f" {mission_id}_desc:0 \"{record['name']}家将{keyword}化为可执行的领国制度，并在{record['internal_crisis']}的压力下决定权力由谁承担。完成此节点会推进本家的专属危机、重建或统一遗产，而非复制其他大名的通用奖励。\"")
        for event_index in range(record["planned_events"]):
            event_id = _event_id(surface, record_index, event_index)
            keyword = record["keywords"][event_index % len(record["keywords"])]
            if event_index == 0:
                title, desc = f"{record['name']}家的权力之约", f"围绕{keyword}的新制度已经触动旧有权利。我们必须决定以家臣合议分担责任，还是由当主直接统摄。"
            elif event_index == 1:
                title, desc = f"{record['name']}家的内部危机", record["internal_crisis"]
            elif event_index == _recovery_event_index(record):
                title, desc = f"{record['name']}再兴", record["alternate_success"]
            elif event_index == _legacy_event_index(record):
                title, desc = f"{record['name']}家的天下遗产", record["unified_legacy"]
            else:
                title, desc = f"{record['name']}：{keyword}", f"{keyword}不只是名号。它要求家中重新分配财赋、军役与裁判责任，并承担相应代价。"
            lines.extend(
                (
                    f" {event_id}.t:0 \"{title}\"",
                    f" {event_id}.d:0 \"{desc}\"",
                    f" {event_id}.1:0 \"以成文议定承担责任\"",
                    f" {event_id}.2:0 \"以当主军令推动变革\"",
                )
            )
        tag = record["tag"].lower()
        lines.extend(
            (
                f" jxp_a_{tag}_council_modifier:0 \"{record['name']}家中议定\"",
                f" jxp_a_{tag}_council_modifier_desc:0 \"家臣与在地力量取得制度化议席；行政更稳健，但地方权利随之扩大。\"",
                f" jxp_a_{tag}_command_modifier:0 \"{record['name']}当主直裁\"",
                f" jxp_a_{tag}_command_modifier_desc:0 \"当主以集中命令推动改革；动员更迅速，但不满也更容易积累。\"",
                f" jxp_a_{tag}_legacy_modifier:0 \"{record['unified_legacy']}\"",
                f" jxp_a_{tag}_legacy_modifier_desc:0 \"{record['unified_legacy']}已成为统一国家可继承的制度经验。\"",
            )
        )
    lines.extend(
        (
            f" jxp_a_rebuild_{surface}_house_title:0 \"重整本家旧盟\"",
            f" jxp_a_rebuild_{surface}_house_desc:0 \"当本家退守小领时，可付出财赋召回旧臣并启动各家独有的失败后重建方案。每国一局仅可使用一次。\"",
        )
    )
    return "\n".join(lines) + "\n"


def render_outputs(plan: dict[str, Any], exact: dict[str, dict[str, Any]]) -> dict[Path, str | bytes]:
    records = plan["daimyo"]
    outputs: dict[Path, str | bytes] = {
        MAIN_ROOT / "common" / "scripted_triggers" / "jxp_a_94_daimyo_depth_triggers.txt": render_slot_triggers(records),
    }
    escape = _load_escape_module()
    for surface, root, prefix in (("main", MAIN_ROOT, "jxp_a_94"), ("map", MAP_ROOT, "jxp_map_a_94")):
        source = render_localisation(surface, records, exact)
        outputs.update(
            {
                root / "missions" / f"{prefix}_daimyo_depth_missions.txt": render_missions(surface, records, exact),
                root / "common" / "event_modifiers" / f"{prefix}_daimyo_depth_modifiers.txt": render_modifiers(surface, records),
                root / "common" / "scripted_effects" / f"{prefix}_daimyo_depth_effects.txt": render_effects(surface, records),
                root / "events" / f"{prefix}_daimyo_depth_events.txt": render_events(surface, records),
                root / "decisions" / f"{prefix}_daimyo_depth_decisions.txt": render_decisions(surface, records),
                root / "common" / "on_actions" / f"{prefix}_daimyo_depth_on_actions.txt": render_on_actions(surface),
                root / "localisation_source" / f"{prefix}_daimyo_depth_l_english_utf8_source.yml": source,
                root / "localisation" / f"{prefix}_daimyo_depth_l_english.yml": escape.escape_text(source).encode("utf-8-sig"),
            }
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if any generated output drifts")
    args = parser.parse_args()
    plan, exact = load_inputs()
    validate(plan, exact)
    outputs = render_outputs(plan, exact)
    drift: list[Path] = []
    for path, payload in outputs.items():
        if args.check:
            if not path.is_file():
                drift.append(path)
                continue
            actual = path.read_bytes() if isinstance(payload, bytes) else path.read_text(encoding="utf-8")
            if actual != payload:
                drift.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(payload, encoding="utf-8", newline="")
        print(f"Created {path.relative_to(REPO_ROOT)}")
    if drift:
        for path in drift:
            print(f"DRIFT {path.relative_to(REPO_ROOT)}")
        return 1
    if args.check:
        print(f"PASS: {len(outputs)} daimyo-depth runtime outputs are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
