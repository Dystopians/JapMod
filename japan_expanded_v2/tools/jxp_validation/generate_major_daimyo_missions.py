#!/usr/bin/env python3
"""Generate exact-tag Tier-S/A daimyo mission branches for main and map mods."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
MAIN_ROOT = SCRIPT_DIR.parents[1]
REPO_ROOT = MAIN_ROOT.parent
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
PLAN_PATH = SCRIPT_DIR / "major_daimyo_mission_plan.json"

DEPTH_TIER_S = frozenset(
    {
        "ODA", "ASK", "TKG", "IMG", "TKD", "UES", "HJO", "MRI",
        "SMZ", "OTM", "OUC", "DTE", "SOO", "HNG", "MYO", "MTS",
    }
)
DEPTH_TIER_A = frozenset(
    {"CSK", "ARI", "AZI", "KRD", "MOG", "MTU", "NBS", "RKK", "RZJ", "STM", "STO", "TGR", "UKT"}
)
CONTACT_MISSIONS = frozenset(
    {
        "jxp_mission_daimyo_market_roads",
        "jxp_mission_daimyo_sakai_hakata_merchants",
        "jxp_mission_daimyo_artisan_guilds",
        "jxp_mission_daimyo_tanegashima_rumors",
        "jxp_mission_daimyo_foreign_letters",
        "jxp_mission_daimyo_licensed_caravans",
    }
)
SOCIETY_MISSIONS = frozenset(
    {
        "jxp_mission_daimyo_shrine_village_compact",
        "jxp_mission_daimyo_irrigation_works",
        "jxp_mission_daimyo_town_magistrates",
        "jxp_mission_daimyo_domain_school",
        "jxp_mission_daimyo_famine_reserves",
        "jxp_mission_daimyo_people_of_the_domain",
    }
)


def _depth_replacement_trigger(mission_id: str) -> str:
    prefix = "jxp_mission_daimyo_"
    if not mission_id.startswith(prefix):
        raise ValueError(f"cannot derive depth trigger for {mission_id}")
    return f"jxp_a_depth_{mission_id[len(prefix):]}_completed_trigger = yes"

POSITIONS = (1, 3, 5, 7, 9, 11, 13, 15)
COMMON_REQUIRED = {
    1: "jxp_mission_daimyo_market_roads",
    3: "jxp_mission_daimyo_artisan_guilds",
    5: "jxp_mission_daimyo_foreign_letters",
    6: "jxp_mission_daimyo_licensed_caravans",
}
COMMON_TRIGGER = {
    0: "mission_completed = jxp_mission_daimyo_domain_accounts",
    1: "mission_completed = jxp_mission_daimyo_shrine_village_compact",
    2: "mission_completed = jxp_mission_daimyo_castle_town",
    3: "mission_completed = jxp_mission_daimyo_town_magistrates",
    5: "mission_completed = jxp_mission_daimyo_clan_league",
    6: "mission_completed = jxp_mission_daimyo_people_of_the_domain",
    7: "mission_completed = jxp_mission_daimyo_tenka_strategy",
}
CITY_FLOORS = (0, 3, 5, 6, 8, 10, 12, 15)

FAMILY_REWARD_SCHEDULE = {
    "warrior": {
        0: ("jxp_add_tenka_order_5_effect",),
        3: ("jxp_add_imperial_sanction_5_effect",),
        5: (
            "jxp_add_tenka_order_5_effect",
            "jxp_add_imperial_sanction_5_effect",
        ),
        7: ("jxp_add_tenka_order_10_effect",),
    },
    "court": {
        0: ("jxp_add_imperial_sanction_5_effect",),
        3: ("jxp_add_tenka_order_5_effect",),
        5: (
            "jxp_add_imperial_sanction_5_effect",
            "jxp_add_tenka_order_5_effect",
        ),
        7: ("jxp_add_imperial_sanction_10_effect",),
    },
    "maritime": {
        0: ("jxp_add_oceanic_opening_5_effect",),
        3: ("jxp_add_tenka_order_5_effect",),
        5: (
            "jxp_add_oceanic_opening_5_effect",
            "jxp_add_tenka_order_5_effect",
        ),
        7: ("jxp_add_oceanic_opening_10_effect",),
    },
    "frontier": {
        0: ("jxp_add_tenka_order_5_effect",),
        3: ("jxp_add_oceanic_opening_5_effect",),
        5: (
            "jxp_add_tenka_order_5_effect",
            "jxp_add_oceanic_opening_5_effect",
        ),
        7: ("jxp_add_tenka_order_10_effect",),
    },
    "temple_market": {
        0: ("jxp_add_imperial_sanction_5_effect",),
        3: ("jxp_add_tenka_order_5_effect",),
        5: (
            "jxp_add_imperial_sanction_5_effect",
            "jxp_add_tenka_order_5_effect",
        ),
        7: ("jxp_add_imperial_sanction_10_effect",),
    },
}
FAMILY_AGENDA = {
    "warrior": ("jxp_25_warrior_agenda_seen", "jxp_daimyo_agenda.1"),
    "court": ("jxp_25_court_agenda_seen", "jxp_daimyo_agenda.2"),
    "maritime": ("jxp_25_maritime_agenda_seen", "jxp_daimyo_agenda.3"),
    "frontier": ("jxp_25_frontier_agenda_seen", "jxp_daimyo_agenda.4"),
    "temple_market": ("jxp_25_temple_market_agenda_seen", "jxp_daimyo_agenda.5"),
}

MAIN_OLD_MISSIONS = {
    "warrior": (
        "jxp_mission_house_warrior_muster",
        "jxp_mission_house_warrior_war_council",
        "jxp_mission_house_warrior_castle_roads",
        "jxp_mission_house_warrior_firearm_drill",
        "jxp_mission_house_warrior_commanders_oath",
        "jxp_mission_house_warrior_banner_legacy",
    ),
    "court": (
        "jxp_mission_house_court_genealogies",
        "jxp_mission_house_court_rank_and_office",
        "jxp_mission_house_court_petitions",
        "jxp_mission_house_court_mediator_network",
        "jxp_mission_house_court_kinri_escort",
        "jxp_mission_house_court_kanrei_memory",
    ),
    "maritime": (
        "jxp_mission_house_sea_port_registers",
        "jxp_mission_house_sea_harbor_council",
        "jxp_mission_house_sea_shipwrights",
        "jxp_mission_house_sea_atakebune",
        "jxp_mission_house_sea_tide_brokers",
        "jxp_mission_house_sea_strait_laws",
    ),
    "frontier": (
        "jxp_mission_house_frontier_passes",
        "jxp_mission_house_frontier_border_council",
        "jxp_mission_house_frontier_markets",
        "jxp_mission_house_frontier_guides",
        "jxp_mission_house_frontier_hostage_oaths",
        "jxp_mission_house_frontier_border_oaths",
    ),
    "temple_market": (
        "jxp_mission_house_temple_ledgers",
        "jxp_mission_house_temple_market_council",
        "jxp_mission_house_temple_market_towns",
        "jxp_mission_house_temple_free_markets",
        "jxp_mission_house_temple_debt_relief",
        "jxp_mission_house_temple_public_law",
    ),
}

MAP_OLD_MISSIONS = {
    "warrior": (
        "jxp_map_mission_warrior_muster",
        "jxp_map_mission_warrior_castle_roads",
        "jxp_map_mission_warrior_provincial_banner",
        "jxp_map_mission_warrior_retainer_census",
        "jxp_map_mission_warrior_hostage_registers",
        "jxp_map_mission_warrior_hegemon_oath",
    ),
    "court": (
        "jxp_map_mission_court_genealogies",
        "jxp_map_mission_court_capital_petitions",
        "jxp_map_mission_court_old_province_claim",
        "jxp_map_mission_court_shugo_archives",
        "jxp_map_mission_court_kinri_embassies",
        "jxp_map_mission_court_realm_arbitration",
    ),
    "maritime": (
        "jxp_map_mission_sea_port_registers",
        "jxp_map_mission_sea_shipwright_leagues",
        "jxp_map_mission_sea_inner_routes",
        "jxp_map_mission_sea_harbor_magistrates",
        "jxp_map_mission_sea_red_seal_networks",
        "jxp_map_mission_sea_strait_command",
    ),
    "frontier": (
        "jxp_map_mission_frontier_passes",
        "jxp_map_mission_frontier_new_fields",
        "jxp_map_mission_frontier_border_oaths",
        "jxp_map_mission_frontier_hostage_registers",
        "jxp_map_mission_frontier_winter_roads",
        "jxp_map_mission_frontier_march_law",
    ),
    "temple_market": (
        "jxp_map_mission_temple_ledgers",
        "jxp_map_mission_temple_market_towns",
        "jxp_map_mission_temple_public_law",
        "jxp_map_mission_temple_debt_arbitration",
        "jxp_map_mission_temple_common_granaries",
        "jxp_map_mission_temple_realm_compact",
    ),
}

FOCUS_ICONS = {
    "administrative": (
        "mission_rice_field", "mission_high_income", "mission_monarch_in_throne_room",
        "mission_japanese_fort", "mission_to_japan", "mission_diplomatic_relation",
        "mission_japanese_samurai", "mission_assemble_an_army",
    ),
    "diplomatic": (
        "mission_diplomatic_relation", "mission_to_japan", "mission_asian_trader",
        "mission_monarch_in_throne_room", "mission_market_place_with_asian_traders",
        "mission_trade_with_japan", "mission_japanese_fort", "mission_japanese_samurai",
    ),
    "military": (
        "mission_assemble_an_army", "mission_japanese_fort", "mission_japanese_samurai",
        "mission_cannons_firing", "mission_chinese_general_riding", "mission_steppe_warriors",
        "mission_monarch_in_throne_room", "mission_assemble_an_army",
    ),
    "naval": (
        "mission_trade_with_japan", "mission_asian_trader", "mission_galleys_in_port",
        "jap_deploy_atakebune", "mission_market_place_with_asian_traders",
        "mission_establish_high_seas_navy", "mission_diplomatic_relation",
        "mission_establish_high_seas_navy",
    ),
    "religious": (
        "mission_religious", "mission_monarch_in_throne_room", "mission_rice_field",
        "mission_high_income", "mission_to_japan", "mission_diplomatic_relation",
        "mission_japanese_fort", "mission_religious",
    ),
}

FOCUS_POWER = {
    "administrative": "add_adm_power",
    "diplomatic": "add_dip_power",
    "military": "add_mil_power",
    "naval": "add_dip_power",
    "religious": "add_adm_power",
}


def _mission_id(surface: str, tag: str, slug: str) -> str:
    prefix = "jxp_map_mission" if surface == "map" else "jxp_mission"
    return f"{prefix}_{tag.lower()}_{slug}"


def _series_id(surface: str, tag: str) -> str:
    prefix = "jxp_map" if surface == "map" else "jxp"
    return f"{prefix}_{tag.lower()}_identity_missions"


def _modifier_id(surface: str, tag: str) -> str:
    prefix = "jxp_map_15" if surface == "map" else "jxp_81"
    return f"{prefix}_{tag.lower()}_legacy"


def _focus_trigger(focus: str, stage: int) -> list[str]:
    if stage not in {2, 4, 7}:
        return []
    if focus == "military":
        return ["army_size_percentage = 0.75" if stage == 2 else "army_size_percentage = 0.90"]
    if focus == "naval":
        return [f"num_of_ports = {2 if stage == 2 else 4 if stage == 4 else 6}"]
    if focus == "administrative":
        return ["stability = 1"]
    if focus == "diplomatic":
        return [f"num_of_allies = {1 if stage == 2 else 2}"]
    return ["religious_unity = 0.90" if stage == 2 else "religious_unity = 1"]


def _focus_reward(focus: str, stage: int) -> list[str]:
    power = FOCUS_POWER[focus]
    if stage == 0:
        return [f"{power} = 35", "add_prestige = 5"]
    if stage == 1:
        return [f"{power} = 40", "add_legitimacy = 5"]
    if stage == 2:
        if focus == "military":
            return ["add_army_tradition = 5", f"{power} = 40"]
        if focus == "naval":
            return ["add_navy_tradition = 5", f"{power} = 40"]
        return ["add_prestige = 10", f"{power} = 40"]
    if stage == 3:
        return ["change_government_reform_progress = 20", f"{power} = 45"]
    if stage == 4:
        return [f"{power} = 50", "add_legitimacy = 5", "add_prestige = 5"]
    if stage == 5:
        return [f"{power} = 60", "add_prestige = 10"]
    if stage == 6:
        return [f"{power} = 60", "change_government_reform_progress = 25"]
    if focus == "military":
        return ["add_army_tradition = 10", "add_prestige = 20"]
    if focus == "naval":
        return ["add_navy_tradition = 10", "add_prestige = 20"]
    return [f"{power} = 75", "add_prestige = 20"]


def _render_mission(surface: str, record: dict[str, Any], stage: int) -> list[str]:
    tag = record["tag"]
    focus = record["focus"]
    chapter = record["chapters"][stage]
    mission_id = _mission_id(surface, tag, chapter["slug"])
    previous = (
        _mission_id(surface, tag, record["chapters"][stage - 1]["slug"])
        if stage
        else None
    )
    if "required_missions" in chapter:
        required = list(chapter["required_missions"])
    else:
        required = [] if previous is None else [previous]
        if stage in COMMON_REQUIRED:
            required.append(COMMON_REQUIRED[stage])
    replacement_triggers: list[str] = []
    if tag in DEPTH_TIER_S:
        for required_id in tuple(required):
            if required_id in CONTACT_MISSIONS:
                required.remove(required_id)
                replacement_triggers.append(_depth_replacement_trigger(required_id))
    if tag in DEPTH_TIER_S | DEPTH_TIER_A:
        for required_id in tuple(required):
            if required_id in SOCIETY_MISSIONS:
                required.remove(required_id)
                replacement_triggers.append(_depth_replacement_trigger(required_id))
    lines = [
        f"\t{mission_id} = {{",
        f"\t\ticon = {FOCUS_ICONS[focus][stage]}",
        f"\t\tposition = {POSITIONS[stage]}",
    ]
    if required:
        lines.append(f"\t\trequired_missions = {{ {' '.join(required)} }}")
    lines.append("\t\ttrigger = {")
    anchor_triggers = list(chapter.get(
        "triggers",
        (COMMON_TRIGGER[stage],) if stage in COMMON_TRIGGER else (),
    ))
    for index, item in enumerate(anchor_triggers):
        if not item.startswith("mission_completed = "):
            continue
        anchor_mission_id = item.split("=", 1)[1].strip()
        if tag in DEPTH_TIER_S and anchor_mission_id in CONTACT_MISSIONS:
            anchor_triggers[index] = _depth_replacement_trigger(anchor_mission_id)
        elif tag in DEPTH_TIER_S | DEPTH_TIER_A and anchor_mission_id in SOCIETY_MISSIONS:
            anchor_triggers[index] = _depth_replacement_trigger(anchor_mission_id)
    anchor_triggers.extend(replacement_triggers)
    anchor_triggers = list(dict.fromkeys(anchor_triggers))
    lines.extend(f"\t\t\t{item}" for item in anchor_triggers)
    if CITY_FLOORS[stage]:
        lines.append(f"\t\t\tnum_of_cities = {CITY_FLOORS[stage]}")
    if stage in {4, 7}:
        lines.append(f"\t\t\tprestige = {15 if stage == 4 else 30}")
    lines.extend(f"\t\t\t{item}" for item in _focus_trigger(focus, stage))
    lines.extend(("\t\t}", "\t\teffect = {"))
    initialize = "jxp_map_initialize_effect" if surface == "map" else "jxp_ensure_daimyo_polity_effect"
    guard = (
        "jxp_map_major_daimyo_mission_replay_guard"
        if surface == "map"
        else "jxp_major_daimyo_mission_replay_guard"
    )
    lines.extend(
        (
            f"\t\t\t{initialize} = yes",
            "\t\t\tif = {",
            f"\t\t\t\tlimit = {{ NOT = {{ has_country_flag = {guard} }} }}",
        )
    )
    lines.extend(f"\t\t\t\t{item}" for item in _focus_reward(focus, stage))
    for reward_effect in FAMILY_REWARD_SCHEDULE[record["family"]].get(stage, ()):
        lines.append(f"\t\t\t\t{reward_effect} = yes")
    lines.extend(f"\t\t\t\t{item}" for item in chapter.get("extra_effects", ()))
    if surface == "main" and stage == 0:
        seen_flag, event_id = FAMILY_AGENDA[record["family"]]
        lines.extend(
            (
                "\t\t\t\tif = {",
                f"\t\t\t\t\tlimit = {{ NOT = {{ has_country_flag = {seen_flag} }} }}",
                f"\t\t\t\t\tcountry_event = {{ id = {event_id} }}",
                "\t\t\t\t}",
            )
        )
    if stage in {6, 7}:
        duration = 5475 if stage == 6 else 9125
        lines.extend(
            (
                "\t\t\t\tadd_country_modifier = {",
                f"\t\t\t\t\tname = {_modifier_id(surface, tag)}",
                f"\t\t\t\t\tduration = {duration}",
                "\t\t\t\t}",
            )
        )
    if stage == 7:
        lines.append("\t\t\t\tset_country_flag = jxp_24_house_path_completed")
    lines.extend(("\t\t\t}", "\t\t}", "\t}", ""))
    return lines


def render_missions(surface: str, records: list[dict[str, Any]]) -> str:
    lines = [
        "# Generated by generate_major_daimyo_missions.py.",
        "# Exact-tag slot-3 branches for historically influential daimyo.",
        "",
    ]
    for record in records:
        lines.extend(
            (
                f"{_series_id(surface, record['tag'])} = {{",
                "\tslot = 3",
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
        for stage in range(8):
            lines.extend(_render_mission(surface, record, stage))
        lines.extend(("}", ""))
    return "\n".join(lines)


def render_modifiers(surface: str, records: list[dict[str, Any]]) -> str:
    lines = ["# Generated by generate_major_daimyo_missions.py.", ""]
    for record in records:
        lines.append(f"{_modifier_id(surface, record['tag'])} = {{")
        for key, value in record["modifier"].items():
            lines.append(f"\t{key} = {value}")
        lines.extend(("}", ""))
    return "\n".join(lines)


def render_cleanup_effects(surface: str, records: list[dict[str, Any]]) -> str:
    is_map = surface == "map"
    prefix = "jxp_map_major_daimyo_mission" if is_map else "jxp_major_daimyo_mission"
    effect_id = (
        "jxp_map_clear_major_daimyo_identity_state_effect"
        if is_map
        else "jxp_clear_major_daimyo_identity_state_effect"
    )
    migration_version = "v014" if is_map else "v0281"
    lines = [
        "# Generated by generate_major_daimyo_missions.py.",
        "",
        f"{effect_id} = {{",
        "\thidden_effect = {",
        f"\t\tclr_country_flag = {prefix}_migration_{migration_version}",
        f"\t\tclr_country_flag = {prefix}_migration_pending",
        f"\t\tclr_country_flag = {prefix}_replay_guard",
    ]
    for stage in range(1, 7):
        lines.append(f"\t\tclr_country_flag = {prefix}_old_progress_{stage}")
    for record in records:
        modifier_id = _modifier_id(surface, record["tag"])
        lines.append(f"\t\tremove_country_modifier = {modifier_id}")
    lines.extend(("\t}", "}", ""))
    return "\n".join(lines)


def render_localisation(surface: str, records: list[dict[str, Any]]) -> str:
    lines = ["l_english:"]
    for record in records:
        for chapter in record["chapters"]:
            mission_id = _mission_id(surface, record["tag"], chapter["slug"])
            lines.append(f" {mission_id}_title:0 \"{chapter['title']}\"")
            lines.append(f" {mission_id}_desc:0 \"{chapter['desc']}\"")
        modifier_id = _modifier_id(surface, record["tag"])
        lines.append(f" {modifier_id}:0 \"{record['legacy_title']}\"")
        lines.append(f" {modifier_id}_desc:0 \"{record['legacy_desc']}\"")
    return "\n".join(lines) + "\n"


def render_identity_triggers(surface: str, records: list[dict[str, Any]]) -> str:
    prefix = "jxp_map" if surface == "map" else "jxp"
    lines = [
        "# Generated by generate_major_daimyo_missions.py.",
        "",
        f"{prefix}_is_major_daimyo_identity_tag_trigger = {{",
        "\tOR = {",
    ]
    lines.extend(f"\t\ttag = {record['tag']}" for record in records)
    lines.extend(("\t}", "}", ""))
    if surface == "map":
        family_anchors = tuple(values[0] for values in MAP_OLD_MISSIONS.values())
        major_anchors = tuple(
            _mission_id(surface, record["tag"], record["chapters"][0]["slug"])
            for record in records
        )
        all_anchors = family_anchors + major_anchors + ("building_alliances",)
        lines.extend(
            (
                "jxp_map_major_daimyo_mission_fingerprint_valid_trigger = {",
                "\tjxp_is_daimyo_stage_trigger = yes",
                "\tOR = {",
            )
        )
        for record, allowed in zip(records, major_anchors):
            lines.extend(("\t\tAND = {", f"\t\t\ttag = {record['tag']}", f"\t\t\thas_mission = {allowed}", "\t\t\tNOT = {", "\t\t\t\tOR = {"))
            lines.extend(f"\t\t\t\t\thas_mission = {anchor}" for anchor in all_anchors if anchor != allowed)
            lines.extend(("\t\t\t\t}", "\t\t\t}", "\t\t}"))
        lines.extend(("\t}", "}", ""))
    return "\n".join(lines)


def render_migration(surface: str, records: list[dict[str, Any]]) -> str:
    is_map = surface == "map"
    namespace = "jxp_map_daimyo_identity" if is_map else "jxp_daimyo_identity"
    flag_prefix = "jxp_map_major_daimyo_mission" if is_map else "jxp_major_daimyo_mission"
    old_missions = MAP_OLD_MISSIONS if is_map else MAIN_OLD_MISSIONS
    all_old_anchors = tuple(values[0] for values in old_missions.values())
    new_anchors = tuple(
        _mission_id(surface, record["tag"], record["chapters"][0]["slug"])
        for record in records
    )
    lines = [
        "# Generated by generate_major_daimyo_missions.py.",
        f"namespace = {namespace}",
        "",
        "country_event = {",
        f"\tid = {namespace}.1",
        "\ttitle = none",
        "\tdesc = none",
        "\tpicture = COURT_eventPicture",
        "\thidden = yes",
        "\tis_triggered_only = yes",
        "",
        "\ttrigger = {",
        f"\t\t{'jxp_map' if is_map else 'jxp'}_is_major_daimyo_identity_tag_trigger = yes",
        f"\t\tNOT = {{ has_country_flag = {flag_prefix}_migration_v0{'14' if is_map else '281'} }}",
        "\t}",
        "",
        "\timmediate = {",
        "\t\tif = {",
        "\t\t\tlimit = {",
        "\t\t\t\tOR = {",
    ]
    lines.extend(f"\t\t\t\t\thas_mission = {anchor}" for anchor in all_old_anchors)
    lines.extend(("\t\t\t\t}", "\t\t\t\tNOT = {", "\t\t\t\t\tOR = {"))
    lines.extend(f"\t\t\t\t\t\thas_mission = {anchor}" for anchor in new_anchors)
    lines.extend(("\t\t\t\t\t}", "\t\t\t\t}", "\t\t\t}", f"\t\t\tset_country_flag = {flag_prefix}_replay_guard"))
    for index in range(6):
        lines.extend(("\t\t\tif = {", "\t\t\t\tlimit = {", "\t\t\t\t\tOR = {"))
        lines.extend(f"\t\t\t\t\t\tmission_completed = {missions[index]}" for missions in old_missions.values())
        lines.extend(("\t\t\t\t\t}", "\t\t\t\t}", f"\t\t\t\tset_country_flag = {flag_prefix}_old_progress_{index + 1}", "\t\t\t}"))
    lines.extend(
        (
            f"\t\t\tset_country_flag = {flag_prefix}_migration_pending",
            "\t\t\tjxp_refresh_route_missions_effect = yes",
            f"\t\t\tcountry_event = {{ id = {namespace}.2 days = 2 }}",
            "\t\t}",
            "\t\telse = {",
            f"\t\t\tset_country_flag = {flag_prefix}_migration_v0{'14' if is_map else '281'}",
            "\t\t}",
            "\t}",
            "",
            "\toption = { name = \"OK\" }",
            "}",
            "",
            "country_event = {",
            f"\tid = {namespace}.2",
            "\ttitle = none",
            "\tdesc = none",
            "\tpicture = COURT_eventPicture",
            "\thidden = yes",
            "\tis_triggered_only = yes",
            "",
            f"\ttrigger = {{ has_country_flag = {flag_prefix}_migration_pending }}",
            "",
            "\timmediate = {",
        )
    )
    for record in records:
        lines.extend(("\t\tif = {", f"\t\t\tlimit = {{ tag = {record['tag']} }}"))
        for index, chapter in enumerate(record["chapters"][:6]):
            lines.extend(
                (
                    "\t\t\tif = {",
                    f"\t\t\t\tlimit = {{ has_country_flag = {flag_prefix}_old_progress_{index + 1} }}",
                    f"\t\t\t\tcomplete_mission = {_mission_id(surface, record['tag'], chapter['slug'])}",
                    "\t\t\t}",
                )
            )
        lines.append("\t\t}")
    for index in range(6):
        lines.append(f"\t\tclr_country_flag = {flag_prefix}_old_progress_{index + 1}")
    lines.extend(
        (
            f"\t\tclr_country_flag = {flag_prefix}_replay_guard",
            f"\t\tclr_country_flag = {flag_prefix}_migration_pending",
            f"\t\tset_country_flag = {flag_prefix}_migration_v0{'14' if is_map else '281'}",
            "\t}",
            "",
            "\toption = { name = \"OK\" }",
            "}",
            "",
        )
    )
    return "\n".join(lines)


def load_plan() -> dict[str, Any]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    for surface in ("main", "map"):
        records = plan[surface]
        tags: set[str] = set()
        for record in records:
            tag = record["tag"]
            if tag in tags:
                raise ValueError(f"duplicate {surface} tag {tag}")
            tags.add(tag)
            if record["family"] not in FAMILY_REWARD_SCHEDULE:
                raise ValueError(f"unknown family for {surface} {tag}")
            if record["focus"] not in FOCUS_ICONS:
                raise ValueError(f"unknown focus for {surface} {tag}")
            if len(record["chapters"]) != 8:
                raise ValueError(f"{surface} {tag} must define eight chapters")
            slugs = [chapter["slug"] for chapter in record["chapters"]]
            if len(set(slugs)) != 8:
                raise ValueError(f"{surface} {tag} has duplicate chapter slugs")
            if any(re.fullmatch(r"[a-z0-9_]+", slug) is None for slug in slugs):
                raise ValueError(f"{surface} {tag} has a non-ASCII or unsafe chapter slug")
            for chapter in record["chapters"]:
                for mission_id in chapter.get("required_missions", ()):
                    if re.fullmatch(r"[a-z0-9_]+", mission_id) is None:
                        raise ValueError(f"{surface} {tag} has an unsafe required mission")
                for field in ("triggers", "extra_effects"):
                    for script_line in chapter.get(field, ()):
                        if (
                            not isinstance(script_line, str)
                            or "\n" in script_line
                            or "\r" in script_line
                            or not script_line.strip()
                        ):
                            raise ValueError(f"{surface} {tag} has an unsafe {field} line")
            if len(record["modifier"]) != 2:
                raise ValueError(f"{surface} {tag} must define exactly two legacy modifiers")
    return plan


def render_outputs(plan: dict[str, Any]) -> dict[Path, str]:
    main_records = plan["main"]
    map_records = plan["map"]
    return {
        MAIN_ROOT / "missions" / "jxp_81_major_daimyo_identity_missions.txt": render_missions("main", main_records),
        MAIN_ROOT / "common" / "event_modifiers" / "jxp_81_major_daimyo_identity_modifiers.txt": render_modifiers("main", main_records),
        MAIN_ROOT / "common" / "scripted_effects" / "jxp_81_major_daimyo_identity_cleanup_effects.txt": render_cleanup_effects("main", main_records),
        MAIN_ROOT / "common" / "scripted_triggers" / "jxp_81_major_daimyo_mission_triggers.txt": render_identity_triggers("main", main_records),
        MAIN_ROOT / "events" / "jxp_81_major_daimyo_migration_events.txt": render_migration("main", main_records),
        MAIN_ROOT / "localisation_source" / "jxp_81_major_daimyo_missions_l_english_utf8_source.yml": render_localisation("main", main_records),
        MAP_ROOT / "missions" / "jxp_map_15_major_daimyo_identity_missions.txt": render_missions("map", map_records),
        MAP_ROOT / "common" / "event_modifiers" / "jxp_map_15_major_daimyo_identity_modifiers.txt": render_modifiers("map", map_records),
        MAP_ROOT / "common" / "scripted_effects" / "jxp_map_15_major_daimyo_identity_cleanup_effects.txt": render_cleanup_effects("map", map_records),
        MAP_ROOT / "common" / "scripted_triggers" / "jxp_map_15_major_daimyo_mission_triggers.txt": render_identity_triggers("map", map_records),
        MAP_ROOT / "events" / "jxp_map_15_major_daimyo_migration_events.txt": render_migration("map", map_records),
        MAP_ROOT / "localisation_source" / "jxp_map_15_major_daimyo_missions_l_english_utf8_source.yml": render_localisation("map", map_records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when any generated output is missing or differs",
    )
    args = parser.parse_args()
    outputs = render_outputs(load_plan())
    drift: list[Path] = []
    for path, text in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                drift.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        print(f"Created {path.relative_to(REPO_ROOT)}")
    if drift:
        for path in drift:
            print(f"DRIFT {path.relative_to(REPO_ROOT)}")
        return 1
    if args.check:
        print(f"PASS: {len(outputs)} major-daimyo generated outputs are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
