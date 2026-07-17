#!/usr/bin/env python3
"""Generate runtime mission fingerprints for JXP and its companion map."""

from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path("common/scripted_triggers/jxp_60_mission_runtime_triggers.txt")

VANILLA_ANCHORS = (
    "jap_balance_shinokosho",
    "mng_cornerstone_empire2",
    "jap_edo_jidai",
    "jap_port_dejima",
    "jap_imjin_war",
    "mng_reform_civil_registration2",
    "jap_issue_new_coin",
    "jap_shinto_or_christian",
    "jap_restoration",
    "jap_spread_the_christian_faith",
    "mng_tame_china_sorrow2",
    "jap_bugeijuuhappan_or_naval_academy_of_japan",
    "jap_bugeijuuhappan",
    "jap_naval_academy_of_japan",
    "jap_strengthen_bakuhan_system",
    "mng_expand_bogue2",
    "jap_bushido_code",
    "mng_form_depots2",
    "JAP_pacify_the_north",
    "the_divine_wind",
    "JAP_expand_the_kokka",
    "strengthen_the_bushido",
    "JAP_balance_the_four_divisions",
)

# A serialized generic series can survive a non-generic swap even when the
# current profile owns all five custom slots.  These are the four generic
# anchors eligible for an ordinary Asian monarchy in the pinned 1.37.5 tree.
GENERIC_ANCHORS = (
    "build_army_mission",
    "building_alliances",
    "high_income_mission",
    "control_spice_trade_asia",
)

DAIMYO_COMMON = (
    "jxp_mission_daimyo_domain_accounts",
    "jxp_mission_daimyo_market_roads",
    "jxp_mission_daimyo_shrine_village_compact",
    "jxp_mission_daimyo_raise_the_banner",
)

DAIMYO_HOUSES = (
    ("jxp_has_warrior_house_origin_trigger", "jxp_mission_house_warrior_muster"),
    ("jxp_has_court_house_origin_trigger", "jxp_mission_house_court_genealogies"),
    ("jxp_has_maritime_house_origin_trigger", "jxp_mission_house_sea_port_registers"),
    ("jxp_has_frontier_house_origin_trigger", "jxp_mission_house_frontier_passes"),
    (
        "jxp_has_temple_market_house_origin_trigger",
        "jxp_mission_house_temple_ledgers",
    ),
)

PLAN_PATH = Path(__file__).resolve().with_name("major_daimyo_mission_plan.json")
_MAJOR_PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))["main"]
DAIMYO_MAJOR_HOUSES = tuple(
    (
        record["tag"],
        f"jxp_mission_{record['tag'].lower()}_{record['chapters'][0]['slug']}",
    )
    for record in _MAJOR_PLAN
)

COMPANION_MAP_TRIGGER = "jxp_has_companion_map_origin_trigger"

UNIFIED_COMMON = (
    "jxp_mission_secure_home_domain",
    "jxp_mission_capital_cities",
)

ROUTE_PROFILES = (
    (
        "toyotomi",
        ("tag = TOY", "NOT = { jxp_has_any_route_trigger = yes }"),
        (
            "jxp_mission_toyotomi_yamazaki_settlement",
            "jxp_mission_toyotomi_osaka_castle_town",
            "jxp_mission_toyotomi_kyushu_settlement",
        ),
    ),
    (
        "uncommitted",
        ("tag = JAP", "NOT = { jxp_has_any_route_trigger = yes }"),
        (
            "jxp_mission_uncommitted_reckon_warrior_houses",
            "jxp_mission_shrine_land_registers",
            "jxp_mission_uncommitted_watch_the_four_seas",
        ),
    ),
    (
        "sakoku",
        ("has_country_flag = jxp_path_sakoku",),
        (
            "jxp_mission_temple_registration",
            "jxp_mission_shrine_land_registers",
            "jxp_mission_sakoku_coastal_magistrates",
        ),
    ),
    (
        "open_trade",
        ("has_country_flag = jxp_path_open_trade",),
        (
            "jxp_mission_open_nagasaki",
            "jxp_mission_eastasia_ryukyu_gateway",
            "jxp_mission_pacific_charter",
        ),
    ),
    (
        "confucian",
        (
            "OR = {",
            "\ttag = CJP",
            "\thas_country_flag = jxp_path_confucian",
            "}",
        ),
        (
            "jxp_mission_domain_school_exams",
            "jxp_mission_cjp_three_teachings_register",
            "jxp_mission_zhu_xi_lectures",
        ),
    ),
    (
        "imperial",
        (
            "OR = {",
            "\ttag = EJP",
            "\thas_country_flag = jxp_path_imperial",
            "}",
        ),
        (
            "jxp_mission_ejp_restore_daijokan",
            "jxp_mission_ejp_repair_kinri",
            "jxp_mission_ejp_guard_four_seas",
        ),
    ),
    (
        "kirishitan",
        (
            "OR = {",
            "\ttag = KJP",
            "\thas_country_flag = jxp_path_kirishitan",
            "}",
        ),
        (
            "jxp_mission_welcome_missionaries",
            "jxp_mission_kirishitan_settlement",
            "jxp_mission_port_congregation_registers",
        ),
    ),
    (
        "reformed",
        (
            "OR = {",
            "\ttag = RFJ",
            "\thas_country_flag = jxp_path_reformed",
            "}",
        ),
        (
            "jxp_mission_hirado_synod",
            "jxp_mission_reformed_settlement",
            "jxp_mission_rfj_oranda_factors",
        ),
    ),
    (
        "kaikyo",
        (
            "OR = {",
            "\ttag = SJP",
            "\thas_country_flag = jxp_path_kaikyo",
            "}",
        ),
        (
            "jxp_mission_malay_factory",
            "jxp_mission_harbor_mosque_registers",
            "jxp_mission_kaikyo_settlement",
        ),
    ),
    (
        "ikko",
        (
            "OR = {",
            "\ttag = IJP",
            "\thas_country_flag = jxp_path_ikko",
            "}",
        ),
        (
            "jxp_mission_terauchi_league",
            "jxp_mission_monto_rolls",
            "jxp_mission_ikko_temple_granaries",
        ),
    ),
    (
        "wokou",
        (
            "OR = {",
            "\ttag = WAK",
            "\thas_country_flag = jxp_path_wokou",
            "}",
        ),
        (
            "jxp_mission_fund_wokou",
            "jxp_mission_wak_letters_of_black_current",
            "jxp_mission_northern_sea_office",
        ),
    ),
)


def _assignment_lines(values: tuple[str, ...], indent: int) -> list[str]:
    prefix = "\t" * indent
    return [f"{prefix}has_mission = {value}" for value in values]


def _condition_lines(values: tuple[str, ...], indent: int) -> list[str]:
    prefix = "\t" * indent
    return [prefix + value for value in values]


def _forbid_lines(values: tuple[str, ...], indent: int) -> list[str]:
    prefix = "\t" * indent
    lines = [f"{prefix}NOT = {{", f"{prefix}\tOR = {{"]
    lines.extend(_assignment_lines(values, indent + 2))
    lines.extend((f"{prefix}\t}}", f"{prefix}}}"))
    return lines


def render() -> str:
    route_anchors = tuple(
        dict.fromkeys(anchor for _name, _condition, anchors in ROUTE_PROFILES for anchor in anchors)
    )
    family_anchors = tuple(anchor for _trigger, anchor in DAIMYO_HOUSES)
    major_anchors = tuple(anchor for _tag, anchor in DAIMYO_MAJOR_HOUSES)
    major_tags = tuple(tag for tag, _anchor in DAIMYO_MAJOR_HOUSES)
    house_anchors = family_anchors + major_anchors

    lines = [
        "# Generated by create_mission_runtime_fingerprint_v0242.py.",
        "# Exact anchors let old saves repair missing, stale, or overlapping mission trees.",
        "",
        "jxp_has_legacy_japanese_mission_trigger = {",
        "\tOR = {",
        *_assignment_lines(VANILLA_ANCHORS + GENERIC_ANCHORS, 2),
        "\t}",
        "}",
        "",
        "jxp_mission_tree_fingerprint_valid_trigger = {",
        "\tNOT = { jxp_has_legacy_japanese_mission_trigger = yes }",
        "\tOR = {",
        "\t\tAND = {",
        "\t\t\tjxp_is_daimyo_stage_trigger = yes",
        *_assignment_lines(DAIMYO_COMMON, 3),
        "\t\t\tOR = {",
    ]

    lines.extend(
        (
            "\t\t\t\t# Companion-map daimyo own their exact slot-3 fingerprint.",
            "\t\t\t\tAND = {",
            f"\t\t\t\t\t{COMPANION_MAP_TRIGGER} = yes",
            *_forbid_lines(house_anchors, 5),
            "\t\t\t\t}",
        )
    )

    for tag, allowed_anchor in DAIMYO_MAJOR_HOUSES:
        forbidden = tuple(anchor for anchor in house_anchors if anchor != allowed_anchor)
        lines.extend(
            (
                "\t\t\t\tAND = {",
                f"\t\t\t\t\ttag = {tag}",
                f"\t\t\t\t\thas_mission = {allowed_anchor}",
                *_forbid_lines(forbidden, 5),
                "\t\t\t\t}",
            )
        )

    for trigger, allowed_anchor in DAIMYO_HOUSES:
        forbidden = tuple(anchor for anchor in house_anchors if anchor != allowed_anchor)
        lines.extend(
            (
                "\t\t\t\tAND = {",
                f"\t\t\t\t\tNOT = {{ {COMPANION_MAP_TRIGGER} = yes }}",
                "\t\t\t\t\tNOT = {",
                "\t\t\t\t\t\tOR = {",
                *[f"\t\t\t\t\t\t\ttag = {tag}" for tag in major_tags],
                "\t\t\t\t\t\t}",
                "\t\t\t\t\t}",
                f"\t\t\t\t\t{trigger} = yes",
                f"\t\t\t\t\thas_mission = {allowed_anchor}",
                *_forbid_lines(forbidden, 5),
                "\t\t\t\t}",
            )
        )
    lines.extend(
        (
            "\t\t\t}",
            *_forbid_lines(UNIFIED_COMMON + route_anchors, 3),
            "\t\t}",
            "\t\tAND = {",
            "\t\t\tjxp_is_unified_japan_state_trigger = yes",
            *_assignment_lines(UNIFIED_COMMON, 3),
            *_forbid_lines(DAIMYO_COMMON + house_anchors, 3),
            "\t\t\tOR = {",
        )
    )

    for name, condition, allowed in ROUTE_PROFILES:
        forbidden = tuple(anchor for anchor in route_anchors if anchor not in allowed)
        lines.extend(
            (
                f"\t\t\t\t# {name}",
                "\t\t\t\tAND = {",
                *_condition_lines(condition, 5),
                *_assignment_lines(allowed, 5),
                *_forbid_lines(forbidden, 5),
                "\t\t\t\t}",
            )
        )

    lines.extend(
        (
            "\t\t\t}",
            "\t\t}",
            "\t}",
            "}",
            "",
            "jxp_mission_tree_needs_reconcile_trigger = {",
            "\tjxp_is_japanese_polity_trigger = yes",
            "\tNOT = { jxp_mission_tree_fingerprint_valid_trigger = yes }",
            "}",
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    mod_root = Path(__file__).resolve().parents[2]
    output = mod_root / OUTPUT
    output.write_text(render(), encoding="utf-8", newline="")
    print(
        f"Created {output}: {len(VANILLA_ANCHORS)} vanilla + "
        f"{len(GENERIC_ANCHORS)} generic anchors, {len(DAIMYO_MAJOR_HOUSES)} "
        f"major daimyo profiles, {len(ROUTE_PROFILES)} route profiles."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
