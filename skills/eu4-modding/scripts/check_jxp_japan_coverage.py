#!/usr/bin/env python3
"""Audit coverage for the Japan Expanded (jxp_) EU4 mod.

This checker is intentionally tailored to the japan_expanded_v2 framework. It
does not validate EU4 syntax in general; it checks that broad-content promises
such as "every daimyo has ideas/flavor/legacy" and "route reforms are visible"
remain true as the mod grows.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROUTES = {
    "sakoku": {"flag": "jxp_path_sakoku", "tag": None},
    "open": {"flag": "jxp_path_open_trade", "tag": None},
    "kirishitan": {"flag": "jxp_path_kirishitan", "tag": "KJP"},
    "confucian": {"flag": "jxp_path_confucian", "tag": "CJP"},
    "imperial": {"flag": "jxp_path_imperial", "tag": "EJP"},
    "reformed": {"flag": "jxp_path_reformed", "tag": "RFJ"},
    "kaikyo": {"flag": "jxp_path_kaikyo", "tag": "SJP"},
    "ikko": {"flag": "jxp_path_ikko", "tag": "IJP"},
    "wokou": {"flag": "jxp_path_wokou", "tag": "WAK"},
}

HOUSE_ARCHETYPES = {
    "warrior": "jxp_has_warrior_house_origin_trigger",
    "court": "jxp_has_court_house_origin_trigger",
    "maritime": "jxp_has_maritime_house_origin_trigger",
    "frontier": "jxp_has_frontier_house_origin_trigger",
    "temple_market": "jxp_has_temple_market_house_origin_trigger",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_many(paths: list[Path]) -> str:
    return "\n".join(read_text(path) for path in paths if path.is_file())


def files(root: Path, glob: str) -> list[Path]:
    return sorted(path for path in root.glob(glob) if path.is_file())


def extract_block(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        return ""
    start = match.end() - 1
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return text[start:]


def extract_named_blocks(text: str, prefix: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    pattern = re.compile(rf"(?m)^\s*({re.escape(prefix)}[A-Za-z0-9_]+)\s*=\s*\{{")
    for match in pattern.finditer(text):
        key = match.group(1)
        start = match.end() - 1
        depth = 0
        for idx in range(start, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks[key] = text[start : idx + 1]
                    break
    return blocks


def extract_assignment_blocks(text: str, key: str) -> list[str]:
    blocks: list[str] = []
    pattern = re.compile(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{")
    for match in pattern.finditer(text):
        start = match.end() - 1
        depth = 0
        for idx in range(start, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start : idx + 1])
                    break
    return blocks


def localisation_keys(localisation_source: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*([A-Za-z0-9_.-]+):0\s+\"", localisation_source))


def expected_daimyo_tags(mod: Path) -> list[str]:
    trigger_path = mod / "common" / "scripted_triggers" / "jxp_04_daimyo_triggers.txt"
    text = read_text(trigger_path)
    block = extract_block(text, "jxp_is_major_daimyo_tag_trigger")
    tags = re.findall(r"\btag\s*=\s*([A-Z]{3})\b", block)
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    return ordered


def find_tag_blocks(text: str, key_prefix: str, tag: str) -> list[str]:
    matches = []
    blocks = extract_named_blocks(text, key_prefix)
    for key, block in blocks.items():
        if re.search(rf"\btag\s*=\s*{tag}\b", block):
            matches.append(key)
    return matches


def flags_set_in(block: str) -> set[str]:
    return set(re.findall(r"\bset_country_flag\s*=\s*([A-Za-z0-9_]+)\b", block))


def country_modifiers_added_in(block: str) -> set[str]:
    return set(re.findall(r"add_country_modifier\s*=\s*\{[^{}]*\bname\s*=\s*([A-Za-z0-9_]+)", block))


def direct_child_block_keys(block: str) -> list[str]:
    """Return immediate child block keys from a Paradox script block."""
    keys: list[str] = []
    depth = 0
    for line in block.splitlines():
        stripped = line.strip()
        if depth == 1:
            match = re.match(r"([A-Za-z0-9_]+)\s*=\s*\{", stripped)
            if match:
                keys.append(match.group(1))
        depth += line.count("{") - line.count("}")
    return keys


def idea_completeness_report(mod: Path) -> tuple[list[str], list[str]]:
    tags = expected_daimyo_tags(mod)
    ideas_text = read_many(files(mod / "common" / "ideas", "*.txt"))
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Daimyo national idea completeness:")
    rows.append("tag group start bonus trigger free seven_ideas loc")

    for tag in tags:
        group_key = f"{tag}_ideas"
        block = extract_block(ideas_text, group_key)
        child_keys = direct_child_block_keys(block)
        idea_keys = [key for key in child_keys if key not in {"start", "bonus", "trigger"}]
        trigger_block = extract_block(block, "trigger") if block else ""

        group_ok = bool(block)
        start_ok = "start" in child_keys
        bonus_ok = "bonus" in child_keys
        trigger_ok = bool(trigger_block) and re.search(rf"\btag\s*=\s*{tag}\b", trigger_block) is not None
        free_ok = bool(re.search(r"(?m)^\s*free\s*=\s*yes\b", block))
        seven_ideas_ok = len(idea_keys) == 7
        required_loc_keys = {group_key, f"{group_key}_start", f"{group_key}_bonus"}
        for idea_key in idea_keys:
            required_loc_keys.add(idea_key)
            required_loc_keys.add(f"{idea_key}_desc")
        loc_ok = seven_ideas_ok and required_loc_keys.issubset(loc_keys)

        checks = {
            "group": group_ok,
            "start": start_ok,
            "bonus": bonus_ok,
            "trigger": trigger_ok,
            "free": free_ok,
            "seven_ideas": seven_ideas_ok,
            "loc": loc_ok,
        }
        rows.append(f"{tag} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                detail = ""
                if name == "seven_ideas":
                    detail = f" ({len(idea_keys)} found: {', '.join(idea_keys) or 'none'})"
                elif name == "loc":
                    missing = sorted(required_loc_keys - loc_keys)
                    detail = f" (missing: {', '.join(missing) or 'n/a'})"
                issues.append(f"{tag}: incomplete national idea {name}{detail}")

    return rows, issues


def daimyo_idea_revision_report(mod: Path) -> tuple[list[str], list[str]]:
    idea_text = read_many(files(mod / "common" / "ideas", "*.txt"))
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    expected = [
        ("TKG_ideas", "TKG_ideas_start", None, ("global_unrest = -1",)),
        ("jxp_tkd_kurokawa_gold", "jxp_tkd_kurokawa_gold", "jxp_tkd_kurokawa_gold_desc", ("inflation_reduction = 0.05", "global_tax_modifier = 0.05")),
        ("jxp_ues_agakita_shu", "jxp_ues_agakita_shu", "jxp_ues_agakita_shu_desc", ("global_manpower_modifier = 0.10", "global_unrest = -0.5")),
        ("jxp_hjo_odawara_administration", "jxp_hjo_odawara_administration", "jxp_hjo_odawara_administration_desc", ("state_maintenance_modifier = -0.05", "governing_capacity_modifier = 0.05")),
        ("jxp_smz_tsurinobuse", "jxp_smz_tsurinobuse", "jxp_smz_tsurinobuse_desc", ("shock_damage = 0.05", "land_morale = 0.05")),
        ("jxp_otm_brave_retainers", "jxp_otm_brave_retainers", "jxp_otm_brave_retainers_desc", ("army_tradition = 0.5", "land_morale = 0.05")),
        ("jxp_dte_oshu_shugo", "jxp_dte_oshu_shugo", "jxp_dte_oshu_shugo_desc", ("governing_capacity_modifier = 0.05", "state_maintenance_modifier = -0.05")),
        ("jxp_dte_marriage_expansion", "jxp_dte_marriage_expansion", "jxp_dte_marriage_expansion_desc", ("diplomatic_upkeep = 1", "improve_relation_modifier = 0.10")),
        ("jxp_dte_renga_circle", "jxp_dte_renga_circle", "jxp_dte_renga_circle_desc", ("advisor_cost = -0.05", "prestige = 0.5")),
        ("jxp_csk_hundred_article_code", "jxp_csk_hundred_article_code", "jxp_csk_hundred_article_code_desc", ("global_unrest = -1", "state_maintenance_modifier = -0.05")),
        ("IMG_ideas", "IMG_ideas_start", None, ("diplomatic_reputation = 1",)),
        ("jxp_img_march_to_kyoto", "jxp_img_march_to_kyoto", "jxp_img_march_to_kyoto_desc", ("unjustified_demands = -0.10", "province_warscore_cost = -0.05")),
        ("AMA_ideas", "AMA_ideas_bonus", None, ("defensiveness = 0.10", "production_efficiency = 0.05")),
        ("jxp_akt_oshu_shogun", "jxp_akt_oshu_shogun", "jxp_akt_oshu_shogun_desc", ("land_morale = 0.05", "global_manpower_modifier = 0.05")),
        ("ASA_ideas", "ASA_ideas_start", None, ("advisor_cost = -0.05",)),
        ("MAE_ideas", "MAE_ideas_bonus", None, ("global_tax_modifier = 0.05", "production_efficiency = 0.05")),
        ("YMN_ideas", "YMN_ideas_bonus", None, ("diplomatic_reputation = 1",)),
        ("jxp_stk_fidelity", "jxp_stk_fidelity", "jxp_stk_fidelity_desc", ("army_tradition_decay = -0.005", "prestige = 0.5")),
        ("jxp_utn_oyama_annexation", "jxp_utn_oyama_annexation", "jxp_utn_oyama_annexation_desc", ("province_warscore_cost = -0.05",)),
        ("jxp_oda_tenka_fubu", "jxp_oda_tenka_fubu", "jxp_oda_tenka_fubu_desc", ("province_warscore_cost = -0.08", "governing_capacity_modifier = 0.05")),
        ("jxp_oda_kenchi_registers", "jxp_oda_kenchi_registers", "jxp_oda_kenchi_registers_desc", ("global_manpower_modifier = 0.10", "global_tax_modifier = 0.05", "state_maintenance_modifier = -0.05")),
        ("jxp_mri_oe_lineage", "jxp_mri_oe_lineage", "jxp_mri_oe_lineage_desc", ("diplomatic_reputation = 1", "advisor_cost = -0.05")),
        ("jxp_mri_kokujin_ikki", "jxp_mri_kokujin_ikki", "jxp_mri_kokujin_ikki_desc", ("global_manpower_modifier = 0.10", "global_unrest = -0.5")),
        ("jxp_ask_shugo_system", "jxp_ask_shugo_system", "jxp_ask_shugo_system_desc", ("diplomatic_reputation = 1", "vassal_income = 0.15", "improve_relation_modifier = 0.10")),
        ("jxp_ouc_baekje_lineage", "jxp_ouc_baekje_lineage", "jxp_ouc_baekje_lineage_desc", ("diplomatic_reputation = 1", "improve_relation_modifier = 0.10")),
        ("jxp_ouc_hakata_city", "jxp_ouc_hakata_city", "jxp_ouc_hakata_city_desc", ("merchants = 1", "trade_steering = 0.05")),
        ("jxp_soo_elementary_school", "jxp_soo_elementary_school", "jxp_soo_elementary_school_desc", ("global_institution_spread = 0.05", "improve_relation_modifier = 0.10")),
        ("OGS_ideas", "OGS_ideas_bonus", None, ("cavalry_power = 0.10", "army_tradition = 0.5")),
        ("jxp_ogs_ogasawara_ryu", "jxp_ogs_ogasawara_ryu", "jxp_ogs_ogasawara_ryu_desc", ("army_tradition = 0.5", "cavalry_cost = -0.05", "prestige_from_land = 0.5")),
        ("jxp_ito_gods_landing", "jxp_ito_gods_landing", "jxp_ito_gods_landing_desc", ("prestige = 1", "tolerance_own = 1")),
        ("jxp_ito_anti_shugo", "jxp_ito_anti_shugo", "jxp_ito_anti_shugo_desc", ("fabricate_claims_cost = -0.20", "years_of_nationalism = -2")),
        ("jxp_kno_yuzuki_castle", "jxp_kno_yuzuki_castle", "jxp_kno_yuzuki_castle_desc", ("global_autonomy = -0.05", "state_maintenance_modifier = -0.05")),
        ("jxp_tti_wise_opportunist", "jxp_tti_wise_opportunist", "jxp_tti_wise_opportunist_desc", ("diplomatic_reputation = 1", "spy_offence = 0.10")),
        ("jxp_tti_kofukuji_temple", "jxp_tti_kofukuji_temple", "jxp_tti_kofukuji_temple_desc", ("advisor_cost = -0.05", "stability_cost_modifier = -0.05")),
        ("RFR_ideas", "RFR_ideas_start", None, ("build_cost = -0.10", "hostile_attrition = 1")),
        ("HTK_ideas", "HTK_ideas_start", None, ("land_morale = 0.10", "merc_maintenance_modifier = -0.10")),
        ("jxp_htk_retainers", "jxp_htk_retainers", "jxp_htk_retainers_desc", ("global_manpower_modifier = 0.10", "global_regiment_cost = -0.05")),
        ("jxp_ike_domain_schools", "jxp_ike_domain_schools", "jxp_ike_domain_schools_desc", ("advisor_cost = -0.05", "global_institution_spread = 0.05")),
        ("SBA_ideas", "SBA_ideas_start", None, ("build_cost = -0.10", "global_regiment_cost = -0.10")),
        ("jxp_sba_military_office", "jxp_sba_military_office", "jxp_sba_military_office_desc", ("army_tradition = 0.5", "prestige_from_land = 0.5")),
        ("jxp_sba_three_provinces", "jxp_sba_three_provinces", "jxp_sba_three_provinces_desc", ("global_autonomy = -0.05", "state_maintenance_modifier = -0.05")),
        ("jxp_akm_western_kinai_claims", "jxp_akm_western_kinai_claims", "jxp_akm_western_kinai_claims_desc", ("fabricate_claims_cost = -0.20", "improve_relation_modifier = 0.05")),
        ("jxp_tki_three_rivers", "jxp_tki_three_rivers", "jxp_tki_three_rivers_desc", ("production_efficiency = 0.05", "state_maintenance_modifier = -0.05")),
        ("jxp_hjo_kamakura_legacy", "jxp_hjo_kamakura_legacy", "jxp_hjo_kamakura_legacy_desc", ("legitimacy = 0.5", "diplomatic_reputation = 1", "prestige_decay = -0.005")),
        ("jxp_ask_court_defenders", "jxp_ask_court_defenders", "jxp_ask_court_defenders_desc", ("diplomatic_reputation = 1", "prestige = 0.5", "global_spy_defence = 0.10")),
        ("IMG_ideas", "IMG_ideas_bonus", None, ("governing_capacity_modifier = 0.05", "prestige = 0.5")),
        ("jxp_ama_gassan_toda_castle", "jxp_ama_gassan_toda_castle", "jxp_ama_gassan_toda_castle_desc", ("defensiveness = 0.15", "hostile_attrition = 0.5", "fort_maintenance_modifier = -0.05")),
        ("jxp_hsk_kanrei", "jxp_hsk_kanrei", "jxp_hsk_kanrei_desc", ("diplomatic_reputation = 1", "governing_capacity_modifier = 0.05")),
        ("jxp_isk_samurai_dokoro", "jxp_isk_samurai_dokoro", "jxp_isk_samurai_dokoro_desc", ("global_unrest = -0.5", "global_spy_defence = 0.10")),
        ("jxp_tti_nara_city", "jxp_tti_nara_city", "jxp_tti_nara_city_desc", ("advisor_cost = -0.05", "prestige = 0.5", "improve_relation_modifier = 0.10")),
        ("jxp_rfr_rebellious_vassals", "jxp_rfr_rebellious_vassals", "jxp_rfr_rebellious_vassals_desc", ("global_unrest = -0.5", "manpower_recovery_speed = 0.05")),
        ("jxp_asa_seventeen_articles", "jxp_asa_seventeen_articles", "jxp_asa_seventeen_articles_desc", ("global_unrest = -0.5", "stability_cost_modifier = -0.05")),
        ("jxp_asa_keitai_legacy", "jxp_asa_keitai_legacy", "jxp_asa_keitai_legacy_desc", ("legitimacy = 0.5", "diplomatic_reputation = 1", "prestige_decay = -0.005")),
        ("jxp_htk_wakae_castle", "jxp_htk_wakae_castle", "jxp_htk_wakae_castle_desc", ("defensiveness = 0.15", "garrison_size = 0.10")),
        ("jxp_htk_clan_unification", "jxp_htk_clan_unification", "jxp_htk_clan_unification_desc", ("global_unrest = -0.5", "manpower_recovery_speed = 0.05")),
        ("jxp_ike_terumasa_governance", "jxp_ike_terumasa_governance", "jxp_ike_terumasa_governance_desc", ("global_unrest = -0.5", "state_maintenance_modifier = -0.05")),
        ("jxp_mae_kanazawa_castle", "jxp_mae_kanazawa_castle", "jxp_mae_kanazawa_castle_desc", ("defensiveness = 0.15", "prestige = 0.5")),
        ("jxp_sba_kanrei_consolidation", "jxp_sba_kanrei_consolidation", "jxp_sba_kanrei_consolidation_desc", ("diplomatic_reputation = 1", "governing_capacity_modifier = 0.05")),
        ("jxp_sba_retainers", "jxp_sba_retainers", "jxp_sba_retainers_desc", ("global_unrest = -0.5", "global_regiment_cost = -0.05")),
        ("jxp_ymn_nitta_descent", "jxp_ymn_nitta_descent", "jxp_ymn_nitta_descent_desc", ("legitimacy = 0.5", "improve_relation_modifier = 0.10")),
        ("jxp_ymn_isolated_heartland", "jxp_ymn_isolated_heartland", "jxp_ymn_isolated_heartland_desc", ("defensiveness = 0.15", "hostile_attrition = 0.5")),
        ("jxp_akm_castle_network", "jxp_akm_castle_network", "jxp_akm_castle_network_desc", ("defensiveness = 0.15", "global_spy_defence = 0.10")),
        ("jxp_stk_hitachi_genji", "jxp_stk_hitachi_genji", "jxp_stk_hitachi_genji_desc", ("legitimacy = 0.5", "cavalry_power = 0.05", "prestige_from_land = 0.5")),
        ("jxp_stk_ikki_suppression", "jxp_stk_ikki_suppression", "jxp_stk_ikki_suppression_desc", ("global_unrest = -0.5", "war_exhaustion = -0.01")),
        ("jxp_stk_mito_castle", "jxp_stk_mito_castle", "jxp_stk_mito_castle_desc", ("defensiveness = 0.15", "state_maintenance_modifier = -0.05")),
        ("jxp_tki_inabayama_castle", "jxp_tki_inabayama_castle", "jxp_tki_inabayama_castle_desc", ("defensiveness = 0.15", "spy_offence = 0.05")),
        ("jxp_utn_fujiwara_descent", "jxp_utn_fujiwara_descent", "jxp_utn_fujiwara_descent_desc", ("diplomatic_reputation = 1", "prestige_decay = -0.005")),
        ("jxp_utn_shirakawa_barrier", "jxp_utn_shirakawa_barrier", "jxp_utn_shirakawa_barrier_desc", ("defensiveness = 0.15", "movement_speed = 0.05")),
    ]

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Daimyo idea revision coverage:")
    rows.append("revision modifiers loc")
    modifier_ok_count = 0
    loc_ok_count = 0
    for block_key, loc_key, desc_key, snippets in expected:
        block = extract_block(idea_text, block_key)
        modifiers_ok = bool(block) and all(snippet in block for snippet in snippets)
        loc_ok = loc_key in loc_keys and (desc_key is None or desc_key in loc_keys)
        if modifiers_ok:
            modifier_ok_count += 1
        if loc_ok:
            loc_ok_count += 1
        if not modifiers_ok:
            issues.append(f"{block_key}: missing expected revised idea modifiers")
        if not loc_ok:
            issues.append(f"{block_key}: missing revised idea localisation")
    daimyo_idea_files = read_many([
        mod / "common" / "ideas" / "00_basic_z1_jxp_15_daimyo_ideas.txt",
        mod / "common" / "ideas" / "00_basic_z2_jxp_17_minor_daimyo_ideas.txt",
        mod / "common" / "ideas" / "00_basic_z3_jxp_18_remaining_daimyo_ideas.txt",
    ])
    clone_patterns = {
        "five-stat legitimacy template": r"legitimacy = 1\s+devotion = 1\s+republican_tradition = 0\.3\s+meritocracy = 1\s+horde_unity = 1",
        "single defensiveness 0.20 castle template": r"defensiveness = 0\.20\s+\}",
    }
    clone_ok = True
    for label, pattern in clone_patterns.items():
        if re.search(pattern, daimyo_idea_files):
            clone_ok = False
            issues.append(f"daimyo ideas: lingering {label}")
    rows.append(f"0_13_1_to_0_17_identity_pass {modifier_ok_count}/{len(expected)} {loc_ok_count}/{len(expected)}")
    rows.append(f"decloning_signatures {'OK' if clone_ok else 'MISS'}")

    return rows, issues


def early_daimyo_event_reward_report(mod: Path) -> tuple[list[str], list[str]]:
    major_event_text = read_text(mod / "events" / "jxp_07_major_daimyo_events.txt")
    minor_event_text = read_text(mod / "events" / "jxp_17_minor_daimyo_events.txt")
    remaining_event_text = read_text(mod / "events" / "jxp_19_remaining_daimyo_flavor_events.txt")
    minor_house_event_text = read_text(mod / "events" / "jxp_20_minor_house_events.txt")
    modifier_text = read_many([
        mod / "common" / "event_modifiers" / "jxp_42_early_daimyo_event_modifiers.txt",
        mod / "common" / "event_modifiers" / "jxp_19_remaining_daimyo_modifiers.txt",
        mod / "common" / "event_modifiers" / "jxp_20_minor_house_modifiers.txt",
    ])
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)

    major_expected = {
        "jxp_major_daimyo.1": ("jxp_42_oda_teppo_muster", "jxp_42_oda_court_notice"),
        "jxp_major_daimyo.2": ("jxp_42_tkg_fudai_oaths", "jxp_42_tkg_prudent_petitions"),
        "jxp_major_daimyo.3": ("jxp_42_tkd_cavalry_registers", "jxp_42_tkd_mountain_accounts"),
        "jxp_major_daimyo.4": ("jxp_42_ues_echigo_muster", "jxp_42_ues_justice_petition"),
        "jxp_major_daimyo.5": ("jxp_42_hjo_castle_net", "jxp_42_hjo_cadastral_review"),
        "jxp_major_daimyo.6": ("jxp_42_mri_setouchi_tides", "jxp_42_mri_kokujin_oaths"),
        "jxp_major_daimyo.7": ("jxp_42_smz_tanegashima_trials", "jxp_42_smz_ichimon_fire"),
        "jxp_major_daimyo.8": ("jxp_42_otm_funai_quarter", "jxp_42_otm_ritual_boundary"),
        "jxp_major_daimyo.9": ("jxp_42_dte_oshu_warband", "jxp_42_dte_distant_letters"),
        "jxp_major_daimyo.10": ("jxp_42_ask_kuban_restoration", "jxp_42_ask_bakufu_ledgers"),
        "jxp_major_daimyo.11": ("jxp_42_csk_ichiryo_muster", "jxp_42_csk_urado_sails"),
        "jxp_major_daimyo.12": ("jxp_42_ouc_yamaguchi_rites", "jxp_42_ouc_tang_goods"),
        "jxp_major_daimyo.13": ("jxp_42_img_kana_code", "jxp_42_img_tokaido_prestige"),
        "jxp_major_daimyo.14": ("jxp_42_soo_wakan_books", "jxp_42_soo_channel_protocols"),
    }
    minor_expected = {
        "jxp_minor_daimyo.1": ("jxp_42_kinai_old_letters", "jxp_42_kinai_domain_ledgers"),
        "jxp_minor_daimyo.2": ("jxp_42_western_sea_writs", "jxp_42_western_kin_compact"),
        "jxp_minor_daimyo.3": ("jxp_42_eastern_kokujin_muster", "jxp_42_eastern_ritual_pacification"),
        "jxp_minor_daimyo.4": ("jxp_42_northern_horse_roads", "jxp_42_northern_sea_posts"),
        "jxp_minor_daimyo.5": ("jxp_42_crossroads_petitions", "jxp_42_crossroads_castle_roads"),
        "jxp_minor_daimyo.6": ("jxp_42_kyushu_mountain_oaths", "jxp_42_kyushu_sea_books"),
        "jxp_minor_daimyo.7": ("jxp_42_hokuriku_court_seats", "jxp_42_hokuriku_storehouse_books"),
    }
    remaining_expected = {
        "jxp_remaining_daimyo.1": ("jxp_19_asa_ichijodani_council", "jxp_19_asa_valley_statutes"),
        "jxp_remaining_daimyo.2": ("jxp_19_htk_wakae_retainer_oaths", "jxp_19_htk_kanrei_petitions"),
        "jxp_remaining_daimyo.3": ("jxp_19_ike_himeji_accounts", "jxp_19_ike_white_wall_prestige"),
        "jxp_remaining_daimyo.4": ("jxp_19_mae_kanazawa_patronage", "jxp_19_mae_kaga_storehouse_books"),
        "jxp_remaining_daimyo.5": ("jxp_19_sba_buei_restoration", "jxp_19_sba_house_compacts"),
        "jxp_remaining_daimyo.6": ("jxp_19_ymn_sixth_share_registers", "jxp_19_ymn_western_army_oaths"),
        "jxp_remaining_daimyo.7": ("jxp_19_akm_banshu_castle_chain", "jxp_19_akm_court_rehabilitation"),
        "jxp_remaining_daimyo.8": ("jxp_19_kkc_aso_fire_rites", "jxp_19_kkc_kikuchi_muster"),
        "jxp_remaining_daimyo.9": ("jxp_19_stk_kashima_muster", "jxp_19_stk_kanto_petitions"),
        "jxp_remaining_daimyo.10": ("jxp_19_tki_mino_river_works", "jxp_19_tki_workshop_routes"),
        "jxp_remaining_daimyo.11": ("jxp_19_utn_nikko_barrier_guard", "jxp_19_utn_shimotsuke_guard"),
    }
    minor_house_expected = {
        "jxp_minor_house.1": ("jxp_20_ama_gassan_toda_registers", "jxp_20_ama_sanin_sea_ledgers"),
        "jxp_minor_house.2": ("jxp_20_hsk_sakai_kanrei_council", "jxp_20_hsk_kanrei_petitions"),
        "jxp_minor_house.3": ("jxp_20_shn_dazaifu_brokers", "jxp_20_shn_hakata_wind_books"),
        "jxp_minor_house.4": ("jxp_20_ogs_suwa_horse_masters", "jxp_20_ogs_suwa_rites"),
        "jxp_minor_house.5": ("jxp_20_ktb_ise_court_petition", "jxp_20_ktb_jingu_domain_accounts"),
        "jxp_minor_house.6": ("jxp_20_akt_ezochi_trade_brokers", "jxp_20_akt_northern_kin_guard"),
        "jxp_minor_house.7": ("jxp_20_cba_katori_muster", "jxp_20_cba_kanto_letters"),
        "jxp_minor_house.8": ("jxp_20_isk_tango_port_wardens", "jxp_20_isk_tango_road_accounts"),
        "jxp_minor_house.9": ("jxp_20_ito_hyuga_fort_network", "jxp_20_ito_mountain_rite_compacts"),
        "jxp_minor_house.10": ("jxp_20_kno_inland_sea_pilots", "jxp_20_kno_island_oaths"),
        "jxp_minor_house.11": ("jxp_20_tti_yamato_temple_compact", "jxp_20_tti_temple_ledgers"),
        "jxp_minor_house.12": ("jxp_20_rfr_mutsu_nine_gates", "jxp_20_rfr_northern_sea_posts"),
    }

    event_blocks: dict[str, str] = {}
    for text, namespace in (
        (major_event_text, "jxp_major_daimyo"),
        (minor_event_text, "jxp_minor_daimyo"),
        (remaining_event_text, "jxp_remaining_daimyo"),
        (minor_house_event_text, "jxp_minor_house"),
    ):
        for block in extract_assignment_blocks(text, "country_event"):
            id_match = re.search(rf"\bid\s*=\s*({namespace}\.\d+)\b", block)
            if id_match:
                event_blocks[id_match.group(1)] = block

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Early daimyo event reward coverage:")
    rows.append("series events modifiers loc cleanup no_generic_pool")
    all_expected = {**major_expected, **minor_expected, **remaining_expected, **minor_house_expected}
    event_ok_count = 0
    modifier_ok_count = 0
    loc_ok_count = 0
    cleanup_ok_count = 0

    for event_id, modifiers in all_expected.items():
        block = event_blocks.get(event_id, "")
        event_ok = bool(block) and all(f"name = {modifier}" in block for modifier in modifiers)
        if event_ok:
            event_ok_count += 1
        else:
            issues.append(f"{event_id}: missing expected dedicated event reward modifiers")
        for modifier in modifiers:
            modifier_ok = re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text) is not None
            loc_ok = modifier in loc_keys and f"{modifier}_desc" in loc_keys
            cleanup_ok = f"remove_country_modifier = {modifier}" in debug_text
            if modifier_ok:
                modifier_ok_count += 1
            else:
                issues.append(f"{modifier}: missing early daimyo event modifier definition")
            if loc_ok:
                loc_ok_count += 1
            else:
                issues.append(f"{modifier}: missing early daimyo event modifier localisation")
            if cleanup_ok:
                cleanup_ok_count += 1
            else:
                issues.append(f"{modifier}: missing debug cleanup")

    old_pool_pattern = r"name\s*=\s*jxp_daimyo_(domain_accounts|castle_town|courtly_petition|gun_foundries|namban_letters|league_of_kin)\b"
    all_event_text = "\n".join((major_event_text, minor_event_text, remaining_event_text, minor_house_event_text))
    no_generic_pool = re.search(old_pool_pattern, all_event_text) is None
    if not no_generic_pool:
        issues.append("early daimyo event series still use generic jxp_daimyo_* reward pool")

    modifier_total = len(all_expected) * 2
    def series_counts(expected: dict[str, tuple[str, str]]) -> tuple[int, int, int, int]:
        events = sum(1 for key in expected if key in event_blocks)
        modifiers = 0
        localisations = 0
        cleanups = 0
        for modifier_pair in expected.values():
            for modifier in modifier_pair:
                if re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text):
                    modifiers += 1
                if modifier in loc_keys and f"{modifier}_desc" in loc_keys:
                    localisations += 1
                if f"remove_country_modifier = {modifier}" in debug_text:
                    cleanups += 1
        return events, modifiers, localisations, cleanups

    major_counts = series_counts(major_expected)
    minor_counts = series_counts(minor_expected)
    remaining_counts = series_counts(remaining_expected)
    minor_house_counts = series_counts(minor_house_expected)
    rows.append(
        "jxp_07_major "
        f"{major_counts[0]}/{len(major_expected)} "
        f"{major_counts[1]}/{len(major_expected) * 2} "
        f"{major_counts[2]}/{len(major_expected) * 2} "
        f"{major_counts[3]}/{len(major_expected) * 2} "
        f"{'OK' if no_generic_pool else 'MISS'}"
    )
    rows.append(
        "jxp_17_minor "
        f"{minor_counts[0]}/{len(minor_expected)} "
        f"{minor_counts[1]}/{len(minor_expected) * 2} "
        f"{minor_counts[2]}/{len(minor_expected) * 2} "
        f"{minor_counts[3]}/{len(minor_expected) * 2} "
        f"{'OK' if no_generic_pool else 'MISS'}"
    )
    rows.append(
        "jxp_19_remaining "
        f"{remaining_counts[0]}/{len(remaining_expected)} "
        f"{remaining_counts[1]}/{len(remaining_expected) * 2} "
        f"{remaining_counts[2]}/{len(remaining_expected) * 2} "
        f"{remaining_counts[3]}/{len(remaining_expected) * 2} "
        f"{'OK' if no_generic_pool else 'MISS'}"
    )
    rows.append(
        "jxp_20_minor_house "
        f"{minor_house_counts[0]}/{len(minor_house_expected)} "
        f"{minor_house_counts[1]}/{len(minor_house_expected) * 2} "
        f"{minor_house_counts[2]}/{len(minor_house_expected) * 2} "
        f"{minor_house_counts[3]}/{len(minor_house_expected) * 2} "
        f"{'OK' if no_generic_pool else 'MISS'}"
    )
    if event_ok_count != len(all_expected):
        issues.append(f"early daimyo event rewards: {event_ok_count}/{len(all_expected)} events have expected modifiers")
    if modifier_ok_count != modifier_total:
        issues.append(f"early daimyo event rewards: {modifier_ok_count}/{modifier_total} modifiers defined")
    if loc_ok_count != modifier_total:
        issues.append(f"early daimyo event rewards: {loc_ok_count}/{modifier_total} modifiers localised")
    if cleanup_ok_count != modifier_total:
        issues.append(f"early daimyo event rewards: {cleanup_ok_count}/{modifier_total} modifiers cleaned up")

    return rows, issues


def preunification_memory_report(mod: Path) -> tuple[list[str], list[str]]:
    early_decision_text = read_many([
        mod / "decisions" / "jxp_15_daimyo_flavor_decisions.txt",
        mod / "decisions" / "jxp_19_remaining_daimyo_flavor_decisions.txt",
        mod / "decisions" / "jxp_20_minor_house_decisions.txt",
    ])
    decision_text = read_text(mod / "decisions" / "jxp_43_preunification_memory_decisions.txt")
    event_text = read_text(mod / "events" / "jxp_43_preunification_memory_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_43_preunification_memory_modifiers.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)

    expected = [
        (
            "oda",
            "jxp_decision_oda_tenka_fubu_edicts",
            "jxp_43_selected_oda_tenka_fubu",
            "jxp_preunification_memory.1",
            ("jxp_43_oda_azuchi_edicts_memory", "jxp_43_oda_market_law_memory"),
        ),
        (
            "tkg",
            "jxp_decision_tkg_mikawa_fudai_registers",
            "jxp_43_selected_tkg_fudai_registers",
            "jxp_preunification_memory.2",
            ("jxp_43_tkg_fudai_cadasters_memory", "jxp_43_tkg_road_oaths_memory"),
        ),
        (
            "tkd",
            "jxp_decision_tkd_koshu_hatagashira",
            "jxp_43_selected_tkd_hatagashira",
            "jxp_preunification_memory.3",
            ("jxp_43_tkd_koshu_muster_memory", "jxp_43_tkd_mountain_supply_memory"),
        ),
        (
            "ues",
            "jxp_decision_ues_kanto_kanrei_petition",
            "jxp_43_selected_ues_kanrei_petition",
            "jxp_preunification_memory.4",
            ("jxp_43_ues_righteous_petitions_memory", "jxp_43_ues_kanrei_arbiter_memory"),
        ),
        (
            "hjo",
            "jxp_decision_hjo_odawara_sogamae",
            "jxp_43_selected_hjo_sogamae",
            "jxp_preunification_memory.5",
            ("jxp_43_hjo_odawara_cadasters_memory", "jxp_43_hjo_sogamae_barriers_memory"),
        ),
        (
            "mri",
            "jxp_decision_mri_setouchi_suigun",
            "jxp_43_selected_mri_suigun",
            "jxp_preunification_memory.6",
            ("jxp_43_mri_suigun_admiralty_memory", "jxp_43_mri_setouchi_toll_memory"),
        ),
        (
            "smz",
            "jxp_decision_smz_satsuma_gunnery",
            "jxp_43_selected_smz_gunnery",
            "jxp_preunification_memory.7",
            ("jxp_43_smz_satsuma_foundries_memory", "jxp_43_smz_ichimon_fire_memory"),
        ),
        (
            "otm",
            "jxp_decision_otm_funai_foreign_quarter",
            "jxp_43_selected_otm_foreign_quarter",
            "jxp_preunification_memory.8",
            ("jxp_43_otm_funai_quarter_memory", "jxp_43_otm_foreign_gunwrights_memory"),
        ),
        (
            "dte",
            "jxp_decision_dte_oshu_kibamusha",
            "jxp_43_selected_dte_kibamusha",
            "jxp_preunification_memory.9",
            ("jxp_43_dte_oshu_cavalry_memory", "jxp_43_dte_distant_letters_memory"),
        ),
        (
            "ask",
            "jxp_decision_ask_reform_hokoshu",
            "jxp_43_selected_ask_hokoshu",
            "jxp_preunification_memory.10",
            ("jxp_43_ask_hokoshu_order_memory", "jxp_43_ask_kuban_arbitration_memory"),
        ),
        (
            "csk",
            "jxp_decision_csk_tosa_ichiryo_gusoku",
            "jxp_43_selected_csk_ichiryo_gusoku",
            "jxp_preunification_memory.11",
            ("jxp_43_csk_ichiryo_rolls_memory", "jxp_43_csk_urado_supply_memory"),
        ),
        (
            "ouc",
            "jxp_decision_ouc_yamaguchi_kanhe_trade",
            "jxp_43_selected_ouc_kanhe_trade",
            "jxp_preunification_memory.12",
            ("jxp_43_ouc_kanhe_bureau_memory", "jxp_43_ouc_yamaguchi_court_memory"),
        ),
        (
            "img",
            "jxp_decision_img_tokaido_lawbooks",
            "jxp_43_selected_img_lawbooks",
            "jxp_preunification_memory.13",
            ("jxp_43_img_kana_code_memory", "jxp_43_img_tokaido_arbitration_memory"),
        ),
        (
            "soo",
            "jxp_decision_soo_tsushima_brokers",
            "jxp_43_selected_soo_brokers",
            "jxp_preunification_memory.14",
            ("jxp_43_soo_wakan_office_memory", "jxp_43_soo_channel_protocols_memory"),
        ),
        (
            "asa",
            "jxp_decision_asa_ichijodani_council",
            "jxp_43_selected_asa_ichijodani_council",
            "jxp_preunification_memory.15",
            ("jxp_43_asa_ichijodani_council_memory", "jxp_43_asa_echizen_paper_office_memory"),
        ),
        (
            "ama",
            "jxp_decision_ama_gassan_toda_registers",
            "jxp_43_selected_ama_gassan_toda",
            "jxp_preunification_memory.16",
            ("jxp_43_ama_mountain_castle_memory", "jxp_43_ama_izumo_mine_registers_memory"),
        ),
        (
            "hsk",
            "jxp_decision_hsk_sakai_kanrei_council",
            "jxp_43_selected_hsk_sakai_council",
            "jxp_preunification_memory.17",
            ("jxp_43_hsk_sakai_council_memory", "jxp_43_hsk_merchant_arbitration_memory"),
        ),
        (
            "ktb",
            "jxp_decision_ktb_ise_court_petition",
            "jxp_43_selected_ktb_ise_petition",
            "jxp_preunification_memory.18",
            ("jxp_43_ktb_ise_shrine_court_memory", "jxp_43_ktb_kuki_pilots_memory"),
        ),
        (
            "akt",
            "jxp_decision_akt_ezochi_trade_brokers",
            "jxp_43_selected_akt_ezochi_brokers",
            "jxp_preunification_memory.19",
            ("jxp_43_akt_ezochi_trade_memory", "jxp_43_akt_northern_wardens_memory"),
        ),
        (
            "rfr",
            "jxp_decision_rfr_mutsu_nine_gates",
            "jxp_43_selected_rfr_mutsu_gates",
            "jxp_preunification_memory.20",
            ("jxp_43_rfr_mutsu_gate_wardens_memory", "jxp_43_rfr_morioka_granary_memory"),
        ),
        (
            "htk",
            "jxp_decision_htk_wakae_retainer_oaths",
            "jxp_43_selected_htk_wakae_oaths",
            "jxp_preunification_memory.21",
            ("jxp_43_htk_wakae_retainer_oaths_memory", "jxp_43_htk_saika_teppo_contracts_memory"),
        ),
        (
            "ike",
            "jxp_decision_ike_himeji_accounts",
            "jxp_43_selected_ike_himeji_accounts",
            "jxp_preunification_memory.22",
            ("jxp_43_ike_himeji_accounts_memory", "jxp_43_ike_setouchi_ledgers_memory"),
        ),
        (
            "mae",
            "jxp_decision_mae_kanazawa_patronage",
            "jxp_43_selected_mae_kanazawa_patronage",
            "jxp_preunification_memory.23",
            ("jxp_43_mae_kanazawa_storehouses_memory", "jxp_43_mae_tea_noh_patronage_memory"),
        ),
        (
            "sba",
            "jxp_decision_sba_buei_restoration",
            "jxp_43_selected_sba_buei_restoration",
            "jxp_preunification_memory.24",
            ("jxp_43_sba_buei_military_office_memory", "jxp_43_sba_hokuriku_roads_memory"),
        ),
        (
            "ymn",
            "jxp_decision_ymn_sixth_share_registers",
            "jxp_43_selected_ymn_sixth_share",
            "jxp_preunification_memory.25",
            ("jxp_43_ymn_sixth_share_registers_memory", "jxp_43_ymn_western_army_compacts_memory"),
        ),
        (
            "akm",
            "jxp_decision_akm_banshu_castle_chain",
            "jxp_43_selected_akm_banshu_castles",
            "jxp_preunification_memory.26",
            ("jxp_43_akm_banshu_castle_roads_memory", "jxp_43_akm_red_pine_oaths_memory"),
        ),
        (
            "kkc",
            "jxp_decision_kkc_aso_fire_rites",
            "jxp_43_selected_kkc_aso_rites",
            "jxp_preunification_memory.27",
            ("jxp_43_kkc_aso_fire_rites_memory", "jxp_43_kkc_kikuchi_scrolls_memory"),
        ),
        (
            "stk",
            "jxp_decision_stk_kashima_muster",
            "jxp_43_selected_stk_kashima_muster",
            "jxp_preunification_memory.28",
            ("jxp_43_stk_kashima_muster_memory", "jxp_43_stk_hitachi_oaths_memory"),
        ),
        (
            "tki",
            "jxp_decision_tki_mino_river_works",
            "jxp_43_selected_tki_mino_riverworks",
            "jxp_preunification_memory.29",
            ("jxp_43_tki_mino_riverworks_memory", "jxp_43_tki_toki_paper_memory"),
        ),
        (
            "utn",
            "jxp_decision_utn_nikko_barrier_guard",
            "jxp_43_selected_utn_nikko_barrier",
            "jxp_preunification_memory.30",
            ("jxp_43_utn_nikko_barrier_memory", "jxp_43_utn_shimotsuke_muster_memory"),
        ),
        (
            "shn",
            "jxp_decision_shn_dazaifu_brokers",
            "jxp_43_selected_shn_dazaifu_brokers",
            "jxp_preunification_memory.31",
            ("jxp_43_shn_dazaifu_brokers_memory", "jxp_43_shn_kyushu_tribute_memory"),
        ),
        (
            "ogs",
            "jxp_decision_ogs_suwa_horse_masters",
            "jxp_43_selected_ogs_suwa_horse",
            "jxp_preunification_memory.32",
            ("jxp_43_ogs_suwa_horse_memory", "jxp_43_ogs_pass_wardens_memory"),
        ),
        (
            "cba",
            "jxp_decision_cba_katori_muster",
            "jxp_43_selected_cba_katori_muster",
            "jxp_preunification_memory.33",
            ("jxp_43_cba_katori_muster_memory", "jxp_43_cba_shimosa_court_routes_memory"),
        ),
        (
            "isk",
            "jxp_decision_isk_tango_port_wardens",
            "jxp_43_selected_isk_tango_ports",
            "jxp_preunification_memory.34",
            ("jxp_43_isk_tango_port_wardens_memory", "jxp_43_isk_shugo_house_law_memory"),
        ),
        (
            "ito",
            "jxp_decision_ito_hyuga_fort_network",
            "jxp_43_selected_ito_hyuga_forts",
            "jxp_preunification_memory.35",
            ("jxp_43_ito_hyuga_fort_network_memory", "jxp_43_ito_shrine_temple_compacts_memory"),
        ),
        (
            "kno",
            "jxp_decision_kno_inland_sea_pilots",
            "jxp_43_selected_kno_inland_pilots",
            "jxp_preunification_memory.36",
            ("jxp_43_kno_setouchi_pilots_memory", "jxp_43_kno_iyo_port_law_memory"),
        ),
        (
            "tti",
            "jxp_decision_tti_yamato_temple_compact",
            "jxp_43_selected_tti_yamato_temple",
            "jxp_preunification_memory.37",
            ("jxp_43_tti_yamato_temple_compact_memory", "jxp_43_tti_kofukuji_castle_towns_memory"),
        ),
    ]

    event_blocks: dict[str, str] = {}
    for block in extract_assignment_blocks(event_text, "country_event"):
        id_match = re.search(r"\bid\s*=\s*(jxp_preunification_memory\.\d+)\b", block)
        if id_match:
            event_blocks[id_match.group(1)] = block

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Pre-unification policy memory coverage:")
    rows.append("tag early_flag dispatch event modifiers loc cleanup")

    decision_gate_ok = (
        "jxp_decision_recall_preunification_edicts" in decision_text
        and "jxp_is_unified_japan_state_trigger = yes" in decision_text
        and "NOT = { has_country_flag = jxp_43_preunification_memory_integrated }" in decision_text
        and "if = { limit =" in decision_text
        and "else_if = { limit =" in decision_text
    )
    decision_loc_ok = (
        "jxp_decision_recall_preunification_edicts_title" in loc_keys
        and "jxp_decision_recall_preunification_edicts_desc" in loc_keys
    )
    if not decision_gate_ok:
        issues.append("preunification memory: decision gate/dispatch is incomplete")
    if not decision_loc_ok:
        issues.append("preunification memory: decision localisation is incomplete")

    expected_tags = {tag.lower() for tag in expected_daimyo_tags(mod)}
    row_tags = {tag for tag, *_ in expected}
    if row_tags != expected_tags:
        missing = ", ".join(sorted(expected_tags - row_tags)) or "none"
        extra = ", ".join(sorted(row_tags - expected_tags)) or "none"
        issues.append(
            "preunification memory: expected-row tag set does not match major daimyo tags "
            f"(missing: {missing}; extra: {extra})"
        )

    totals = {"early_flag": 0, "dispatch": 0, "event": 0, "modifiers": 0, "loc": 0, "cleanup": 0}
    for tag, early_decision, memory_flag, event_id, modifiers in expected:
        early_block = extract_block(early_decision_text, early_decision)
        event_block = event_blocks.get(event_id, "")
        early_ok = memory_flag in early_block
        dispatch_ok = (
            memory_flag in decision_text
            and f"country_event = {{ id = {event_id} }}" in decision_text
        )
        event_ok = (
            bool(event_block)
            and "jxp_is_unified_japan_state_trigger = yes" in event_block
            and memory_flag in event_block
            and "set_country_flag = jxp_43_preunification_memory_integrated" in event_block
            and event_block.count("option = {") == 2
            and all(f"name = {modifier}" in event_block for modifier in modifiers)
        )
        modifiers_ok = all(
            re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text)
            for modifier in modifiers
        )
        loc_ok = (
            f"{event_id}.t" in loc_keys
            and f"{event_id}.d" in loc_keys
            and f"{event_id}.a" in loc_keys
            and f"{event_id}.b" in loc_keys
            and all(modifier in loc_keys and f"{modifier}_desc" in loc_keys for modifier in modifiers)
        )
        cleanup_ok = (
            f"clr_country_flag = {memory_flag}" in debug_text
            and "clr_country_flag = jxp_43_preunification_memory_integrated" in debug_text
            and all(f"remove_country_modifier = {modifier}" in debug_text for modifier in modifiers)
        )
        checks = {
            "early_flag": early_ok,
            "dispatch": dispatch_ok,
            "event": event_ok,
            "modifiers": modifiers_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        for name, ok in checks.items():
            if ok:
                totals[name] += 1
            else:
                issues.append(f"{tag}: missing or weak pre-unification policy memory {name} coverage")
        rows.append(f"{tag} " + " ".join("OK" if checks[name] else "MISS" for name in checks))

    rows.append(
        "totals "
        + " ".join(f"{name}={count}/{len(expected)}" for name, count in totals.items())
        + f" decision={'OK' if decision_gate_ok and decision_loc_ok else 'MISS'}"
    )
    return rows, issues


def daimyo_report(mod: Path) -> tuple[list[str], list[str]]:
    tags = expected_daimyo_tags(mod)
    ideas_text = read_many(files(mod / "common" / "ideas", "*.txt"))
    decisions_text = read_many(files(mod / "decisions", "*.txt"))
    events_text = read_many(files(mod / "events", "*.txt"))
    modifiers_text = read_many(files(mod / "common" / "event_modifiers", "*.txt"))
    trigger_text = read_text(mod / "common" / "scripted_triggers" / "jxp_04_daimyo_triggers.txt")
    effect_text = read_text(mod / "common" / "scripted_effects" / "jxp_04_daimyo_effects.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)

    issues: list[str] = []
    rows: list[str] = []
    rows.append("Daimyo coverage:")
    rows.append("tag ideas decision event origin legacy modifier loc cleanup")

    event_blocks = extract_assignment_blocks(events_text, "country_event")

    def pre_route_polity_block(block: str) -> bool:
        if "jxp_is_daimyo_stage_trigger = yes" in block:
            return True
        if "jxp_daimyo_has_working_port_trigger = yes" in block:
            return True
        return (
            "jxp_is_japanese_polity_trigger = yes" in block
            and "NOT = { jxp_has_any_route_trigger = yes }" in block
            and (
                "has_reform = shogunate" in block
                or "has_reform = daimyo" in block
                or "has_reform = indep_daimyo" in block
            )
            and "jxp_ensure_daimyo_polity_effect = yes" in block
        )

    for tag in tags:
        low = tag.lower()
        idea_ok = bool(re.search(rf"(?m)^\s*{tag}_ideas\s*=\s*\{{", ideas_text))
        idea_trigger_ok = bool(
            re.search(rf"{tag}_ideas\s*=\s*\{{.*?\btag\s*=\s*{tag}\b", ideas_text, re.S)
        )
        decision_keys = find_tag_blocks(decisions_text, "jxp_decision_", tag)
        decision_blocks = [
            extract_block(decisions_text, key)
            for key in decision_keys
            if pre_route_polity_block(extract_block(decisions_text, key))
        ]
        event_blocks_for_tag = [
            block
            for block in event_blocks
            if re.search(rf"\btag\s*=\s*{tag}\b", block)
            and pre_route_polity_block(block)
        ]
        daimyo_decision_ok = bool(decision_blocks)
        event_ok = bool(event_blocks_for_tag)
        decision_flags = {
            flag
            for block in decision_blocks
            for flag in flags_set_in(block)
            if flag.endswith("_taken")
        }
        event_flags = {
            flag
            for block in event_blocks_for_tag
            for flag in flags_set_in(block)
            if flag.endswith("_seen")
        }
        temporary_modifiers = {
            modifier
            for block in decision_blocks + event_blocks_for_tag
            for modifier in country_modifiers_added_in(block)
        }
        legacy_event_ok = any(
            "jxp_is_unified_japan_state_trigger = yes" in block
            and re.search(rf"\bhas_country_flag\s*=\s*jxp_origin_{low}\b", block)
            for block in event_blocks
        )
        origin_ok = (
            f"has_country_flag = jxp_origin_{low}" in trigger_text
            and f"set_country_flag = jxp_origin_{low}" in effect_text
        )
        legacy_modifier_ok = bool(
            re.search(rf"(?m)^\s*jxp_[A-Za-z0-9_]*legacy[A-Za-z0-9_]*_{low}\s*=\s*\{{", modifiers_text)
            or re.search(rf"(?m)^\s*jxp_daimyo_legacy_{low}\s*=\s*\{{", modifiers_text)
        )
        loc_ok = (
            f"{tag}_ideas" in loc_keys
            and f"{tag}_ideas_start" in loc_keys
            and any(low in key.lower() for key in loc_keys if key.startswith("jxp_"))
        )
        cleanup_ok = (
            f"clr_country_flag = jxp_origin_{low}" in debug_text
            and re.search(rf"remove_country_modifier\s*=\s*jxp_[A-Za-z0-9_]*legacy[A-Za-z0-9_]*_{low}\b", debug_text)
            and all(f"clr_country_flag = {flag}" in debug_text for flag in decision_flags | event_flags)
            and all(f"remove_country_modifier = {modifier}" in debug_text for modifier in temporary_modifiers)
        )

        checks = {
            "ideas": idea_ok and idea_trigger_ok,
            "decision": daimyo_decision_ok,
            "event": event_ok,
            "origin": origin_ok,
            "legacy": legacy_event_ok,
            "modifier": legacy_modifier_ok,
            "loc": loc_ok,
            "cleanup": bool(cleanup_ok),
        }
        rows.append(f"{tag} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{tag}: missing or weak daimyo {name} coverage")

    return rows, issues


def route_from_reform(key: str, block: str) -> str | None:
    for route, meta in ROUTES.items():
        if key.startswith(f"jxp_reform_{route}_"):
            return route
        if meta["flag"] in block:
            return route
        if meta["tag"] and re.search(rf"\btag\s*=\s*{meta['tag']}\b", block):
            return route
    return None


def route_report(mod: Path) -> tuple[list[str], list[str]]:
    reform_text = read_many(files(mod / "common" / "government_reforms", "*.txt"))
    government_text = read_many(files(mod / "common" / "governments", "*.txt"))
    effect_text = read_many(files(mod / "common" / "scripted_effects", "*.txt"))
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    reform_blocks = extract_named_blocks(reform_text, "jxp_reform_")

    by_route: dict[str, dict[str, list[str]]] = {
        route: {"hidden": [], "visible": [], "parked": []} for route in ROUTES
    }
    issues: list[str] = []

    for key, block in sorted(reform_blocks.items()):
        route = route_from_reform(key, block)
        if not route:
            continue
        is_basic = "basic_reform = yes" in block
        is_registered = re.search(rf"\b{re.escape(key)}\b", government_text) is not None
        if is_registered and is_basic:
            issues.append(f"{key}: registered visible reform still has basic_reform = yes")
        if is_registered:
            by_route[route]["visible"].append(key)
        elif is_basic:
            by_route[route]["hidden"].append(key)
        else:
            by_route[route]["parked"].append(key)
        if key not in loc_keys:
            issues.append(f"{key}: missing localisation key")
        if f"{key}_desc" not in loc_keys:
            issues.append(f"{key}: missing localisation desc key")
        if f"remove_government_reform = {key}" not in effect_text:
            issues.append(f"{key}: missing route-switch cleanup remove_government_reform")

    rows: list[str] = []
    rows.append("Route reform coverage:")
    rows.append("route hidden_auto visible_registered parked_definitions")
    for route in ROUTES:
        hidden_count = len(by_route[route]["hidden"])
        visible_count = len(by_route[route]["visible"])
        parked_count = len(by_route[route]["parked"])
        rows.append(f"{route} {hidden_count} {visible_count} {parked_count}")
        if visible_count != 3:
            issues.append(f"{route}: expected exactly 3 UI-safe visible route reforms, found {visible_count}")

    level_keys = [
        "jxp_route_institution_foundations",
        "jxp_route_institution_administration",
        "jxp_route_institution_command",
    ]
    parked_level_keys = [
        "jxp_route_institution_society",
        "jxp_route_institution_arms",
        "jxp_route_institution_horizon",
        "jxp_route_institution_state_doctrine",
        "jxp_route_institution_capstone",
        "jxp_route_institution_special_bureaus",
        "jxp_route_institution_secretariats",
        "jxp_route_institution_grand_design",
        "jxp_route_institution_branch_programs",
        "jxp_route_institution_privy_councils",
        "jxp_route_institution_sovereign_projects",
        "jxp_route_institution_high_offices",
    ]
    for key in level_keys:
        if key not in loc_keys:
            issues.append(f"{key}: missing reform-level localisation key")
        if key not in government_text:
            issues.append(f"{key}: missing from common/governments/00_governments.txt")
    for key in parked_level_keys:
        if key in government_text:
            issues.append(f"{key}: parked route reform level is still registered in government UI")

    return rows, issues


def founder_reform_report(mod: Path) -> tuple[list[str], list[str]]:
    tags = expected_daimyo_tags(mod)
    reform_text = read_many(files(mod / "common" / "government_reforms", "*.txt"))
    government_text = read_many(files(mod / "common" / "governments", "*.txt"))
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    effect_text = read_many(files(mod / "common" / "scripted_effects", "*.txt"))
    reform_blocks = extract_named_blocks(reform_text, "jxp_reform_founder_")

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Founder house reform coverage:")
    rows.append("tag reform registered potential loc cleanup")

    for tag in tags:
        low = tag.lower()
        matching_keys = [key for key in reform_blocks if key.startswith(f"jxp_reform_founder_{low}_")]
        reform_ok = len(matching_keys) == 1
        key = matching_keys[0] if matching_keys else f"jxp_reform_founder_{low}_<missing>"
        block = reform_blocks.get(key, "")
        registered_ok = bool(re.search(rf"\b{re.escape(key)}\b", government_text))
        potential_ok = (
            "jxp_is_unified_japan_state_trigger = yes" in block
            and f"has_country_flag = jxp_origin_{low}" in block
        )
        loc_ok = key in loc_keys and f"{key}_desc" in loc_keys
        cleanup_ok = (
            "jxp_clear_founder_house_reforms_effect = yes" in debug_text
            and f"remove_government_reform = {key}" in effect_text
        )
        checks = {
            "reform": reform_ok,
            "registered": registered_ok,
            "potential": potential_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        rows.append(f"{tag} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{tag}: missing or weak founder house reform {name} coverage")

    fallback_key = "jxp_reform_founder_generic_renovated_japan"
    fallback_block = reform_blocks.get(fallback_key, "")
    if fallback_key not in reform_blocks:
        issues.append(f"{fallback_key}: missing fallback founder reform")
    if fallback_key not in government_text:
        issues.append(f"{fallback_key}: fallback founder reform not registered")
    if fallback_key not in loc_keys or f"{fallback_key}_desc" not in loc_keys:
        issues.append(f"{fallback_key}: missing fallback localisation")
    if "NOT = { jxp_has_major_daimyo_origin_trigger = yes }" not in fallback_block:
        issues.append(f"{fallback_key}: fallback does not exclude known founder origins")

    return rows, issues


def founder_reform_by_origin(mod: Path) -> dict[str, str]:
    reform_text = read_many(files(mod / "common" / "government_reforms", "*.txt"))
    reform_blocks = extract_named_blocks(reform_text, "jxp_reform_founder_")
    mapping: dict[str, str] = {}
    for key, block in reform_blocks.items():
        match = re.search(r"\bhas_country_flag\s*=\s*jxp_origin_([a-z0-9]+)\b", block)
        if match:
            mapping[match.group(1)] = key
    return mapping


def archetype_origins(mod: Path) -> dict[str, list[str]]:
    trigger_text = read_text(mod / "common" / "scripted_triggers" / "jxp_22_house_ordinance_triggers.txt")
    grouped: dict[str, list[str]] = {}
    for house, trigger in HOUSE_ARCHETYPES.items():
        block = extract_block(trigger_text, trigger)
        grouped[house] = re.findall(r"\bjxp_origin_([a-z0-9]+)\b", block)
    return grouped


def founder_legacy_council_report(mod: Path) -> tuple[list[str], list[str]]:
    tags = expected_daimyo_tags(mod)
    decision_text = read_text(mod / "decisions" / "jxp_26_founder_legacy_councils.txt")
    trigger_text = read_text(mod / "common" / "scripted_triggers" / "jxp_26_founder_legacy_triggers.txt")
    event_text = read_text(mod / "events" / "jxp_26_founder_legacy_councils.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_26_founder_legacy_council_modifiers.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Founder legacy council coverage:")
    rows.append("tag trigger decision event options modifiers loc cleanup")

    origin_to_event_block: dict[str, str] = {}
    origin_to_event_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_founder_legacy\.\d+)\b", block)
        origin_match = re.search(r"\bhas_country_flag\s*=\s*jxp_origin_([a-z0-9_]+)\b", block)
        if id_match and origin_match:
            origin_to_event_block[origin_match.group(1)] = block
            origin_to_event_id[origin_match.group(1)] = id_match.group(1)

    for tag in tags:
        low = tag.lower()
        event_id = origin_to_event_id.get(low, "")
        event_block = origin_to_event_block.get(low, "")
        added_modifiers = sorted(country_modifiers_added_in(event_block))
        seen_flag = f"jxp_26_{low}_legacy_council_seen"
        trigger_ok = f"has_country_flag = jxp_origin_{low}" in trigger_text
        decision_ok = (
            f"has_country_flag = jxp_origin_{low}" in decision_text
            and bool(event_id)
            and f"country_event = {{ id = {event_id} }}" in decision_text
        )
        event_ok = (
            bool(event_block)
            and "jxp_is_unified_japan_state_trigger = yes" in event_block
            and "NOT = { has_country_flag = jxp_26_founder_legacy_council_taken }" in event_block
            and f"set_country_flag = {seen_flag}" in event_block
        )
        options_ok = bool(event_block) and len(re.findall(r"(?m)^\s*option\s*=\s*\{", event_block)) == 2
        modifiers_ok = (
            len(added_modifiers) == 2
            and all(re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text) for modifier in added_modifiers)
        )
        loc_ok = (
            bool(event_id)
            and f"{event_id}.t" in loc_keys
            and f"{event_id}.d" in loc_keys
            and f"{event_id}.a" in loc_keys
            and f"{event_id}.b" in loc_keys
            and all(modifier in loc_keys and f"{modifier}_desc" in loc_keys for modifier in added_modifiers)
        )
        cleanup_ok = (
            f"clr_country_flag = {seen_flag}" in debug_text
            and all(f"remove_country_modifier = {modifier}" in debug_text for modifier in added_modifiers)
        )
        checks = {
            "trigger": trigger_ok,
            "decision": decision_ok,
            "event": event_ok,
            "options": options_ok,
            "modifiers": modifiers_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        rows.append(f"{tag} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{tag}: missing or weak jxp_26 founder legacy council {name} coverage")

    return rows, issues


def route_house_compromise_report(mod: Path) -> tuple[list[str], list[str]]:
    decision_text = read_text(mod / "decisions" / "jxp_29_route_house_compromise_decisions.txt")
    event_text = read_text(mod / "events" / "jxp_29_route_house_compromise_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_29_route_house_compromise_modifiers.txt")
    effect_text = read_text(mod / "common" / "scripted_effects" / "jxp_29_route_house_compromise_effects.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")

    route_order = [
        ("sakoku", 1, "jxp_29_sakoku_house_ordinance", "jxp_29_sakoku_house_compromise_seen"),
        ("open", 2, "jxp_29_open_house_ordinance", "jxp_29_open_house_compromise_seen"),
        ("kirishitan", 3, "jxp_29_kirishitan_house_ordinance", "jxp_29_kirishitan_house_compromise_seen"),
        ("confucian", 4, "jxp_29_confucian_house_ordinance", "jxp_29_confucian_house_compromise_seen"),
        ("imperial", 5, "jxp_29_imperial_house_ordinance", "jxp_29_imperial_house_compromise_seen"),
        ("reformed", 6, "jxp_29_reformed_house_ordinance", "jxp_29_reformed_house_compromise_seen"),
        ("kaikyo", 7, "jxp_29_kaikyo_house_ordinance", "jxp_29_kaikyo_house_compromise_seen"),
        ("ikko", 8, "jxp_29_ikko_house_ordinance", "jxp_29_ikko_house_compromise_seen"),
        ("wokou", 9, "jxp_29_wokou_house_ordinance", "jxp_29_wokou_house_compromise_seen"),
    ]
    house_modifiers = {
        "jxp_has_warrior_house_origin_trigger": "jxp_29_house_warrior_tempered_route",
        "jxp_has_court_house_origin_trigger": "jxp_29_house_court_tempered_route",
        "jxp_has_maritime_house_origin_trigger": "jxp_29_house_maritime_tempered_route",
        "jxp_has_frontier_house_origin_trigger": "jxp_29_house_frontier_tempered_route",
        "jxp_has_temple_market_house_origin_trigger": "jxp_29_house_temple_market_tempered_route",
    }
    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_route_house_compromise\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Route-house compromise coverage:")
    rows.append("route decision event options modifier loc cleanup")

    clear_effect_ok = "jxp_clear_route_house_compromise_effect = yes" in debug_text
    for route, event_number, modifier, seen_flag in route_order:
        meta = ROUTES[route]
        event_id = f"jxp_route_house_compromise.{event_number}"
        block = event_by_id.get(event_id, "")
        dispatch_ok = (
            "jxp_decision_convene_route_house_compromise" in decision_text
            and f"country_event = {{ id = {event_id} }}" in decision_text
            and (meta["flag"] in decision_text or (meta["tag"] and f"tag = {meta['tag']}" in decision_text))
        )
        event_ok = (
            bool(block)
            and "is_triggered_only = yes" in block
            and "jxp_is_unified_japan_state_trigger = yes" in block
            and "NOT = { has_country_flag = jxp_29_route_house_compromise_taken }" in block
            and (meta["flag"] in block or (meta["tag"] and f"tag = {meta['tag']}" in block))
        )
        options_ok = (
            bool(block)
            and len(re.findall(r"(?m)^\s*option\s*=\s*\{", block)) == 2
            and f"add_country_modifier = {{ name = {modifier} duration = 5475 }}" in block
            and "jxp_apply_founder_house_compromise_effect = yes" in block
        )
        modifier_ok = re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text) is not None
        loc_ok = (
            f"{event_id}.t" in loc_keys
            and f"{event_id}.d" in loc_keys
            and f"{event_id}.a" in loc_keys
            and f"{event_id}.b" in loc_keys
            and modifier in loc_keys
            and f"{modifier}_desc" in loc_keys
        )
        cleanup_ok = (
            clear_effect_ok
            and f"clr_country_flag = {seen_flag}" in effect_text
            and f"remove_country_modifier = {modifier}" in effect_text
        )
        checks = {
            "decision": dispatch_ok,
            "event": event_ok,
            "options": options_ok,
            "modifier": modifier_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        rows.append(f"{route} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{route}: missing or weak route-house compromise {name} coverage")

    rows.append("house_trigger modifier cleanup loc")
    for trigger, modifier in house_modifiers.items():
        modifier_ok = re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text) is not None
        effect_ok = trigger in effect_text and f"add_country_modifier = {{ name = {modifier} duration = 5475 }}" in effect_text
        cleanup_ok = clear_effect_ok and f"remove_country_modifier = {modifier}" in effect_text
        loc_ok = modifier in loc_keys and f"{modifier}_desc" in loc_keys
        rows.append(
            f"{trigger} "
            + " ".join("OK" if check else "MISS" for check in (modifier_ok and effect_ok, cleanup_ok, loc_ok))
        )
        if not modifier_ok or not effect_ok:
            issues.append(f"{trigger}: missing route-house founder modifier application")
        if not cleanup_ok:
            issues.append(f"{trigger}: missing route-house founder modifier cleanup")
        if not loc_ok:
            issues.append(f"{trigger}: missing route-house founder modifier localisation")

    for key in ("jxp_decision_convene_route_house_compromise_title", "jxp_decision_convene_route_house_compromise_desc"):
        if key not in loc_keys:
            issues.append(f"{key}: missing route-house decision localisation")

    return rows, issues


def route_house_resonance_report(mod: Path) -> tuple[list[str], list[str]]:
    event_text = read_text(mod / "events" / "jxp_30_route_house_resonance_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_30_route_house_resonance_modifiers.txt")
    effect_text = read_text(mod / "common" / "scripted_effects" / "jxp_30_route_house_resonance_effects.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")

    house_events = [
        (
            "warrior",
            1,
            "jxp_has_warrior_house_origin_trigger",
            "jxp_30_warrior_route_resonance_seen",
            "jxp_30_route_over_warrior_houses",
            "jxp_30_warrior_houses_temper_route",
        ),
        (
            "court",
            2,
            "jxp_has_court_house_origin_trigger",
            "jxp_30_court_route_resonance_seen",
            "jxp_30_route_over_court_houses",
            "jxp_30_court_houses_temper_route",
        ),
        (
            "maritime",
            3,
            "jxp_has_maritime_house_origin_trigger",
            "jxp_30_maritime_route_resonance_seen",
            "jxp_30_route_over_maritime_houses",
            "jxp_30_maritime_houses_temper_route",
        ),
        (
            "frontier",
            4,
            "jxp_has_frontier_house_origin_trigger",
            "jxp_30_frontier_route_resonance_seen",
            "jxp_30_route_over_frontier_houses",
            "jxp_30_frontier_houses_temper_route",
        ),
        (
            "temple_market",
            5,
            "jxp_has_temple_market_house_origin_trigger",
            "jxp_30_temple_market_route_resonance_seen",
            "jxp_30_route_over_temple_market_houses",
            "jxp_30_temple_market_houses_temper_route",
        ),
    ]

    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_route_house_resonance\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Route-house resonance coverage:")
    rows.append("house event mtth options modifiers loc cleanup")

    clear_effect_ok = "jxp_clear_route_house_resonance_effect = yes" in debug_text
    route_effect_ok = (
        "jxp_add_current_route_resonance_effect" in effect_text
        and "jxp_add_current_house_resonance_effect" in effect_text
        and all(meta["flag"] in effect_text for meta in ROUTES.values())
    )
    if not route_effect_ok:
        issues.append("route-house resonance: route/house scripted effects do not cover every route flag")

    for house, number, trigger, seen_flag, route_modifier, house_modifier in house_events:
        event_id = f"jxp_route_house_resonance.{number}"
        block = event_by_id.get(event_id, "")
        event_ok = (
            bool(block)
            and "jxp_is_unified_japan_state_trigger = yes" in block
            and trigger in block
            and "jxp_has_any_route_trigger = yes" in block
            and f"NOT = {{ has_country_flag = {seen_flag} }}" in block
        )
        mtth_ok = "mean_time_to_happen" in block and re.search(r"\bmonths\s*=\s*(2[5-7]0)\b", block) is not None
        options_ok = (
            bool(block)
            and len(re.findall(r"(?m)^\s*option\s*=\s*\{", block)) == 2
            and "jxp_add_current_route_resonance_effect = yes" in block
            and "jxp_add_current_house_resonance_effect = yes" in block
            and f"add_country_modifier = {{ name = {route_modifier} duration = 3650 }}" in block
            and f"add_country_modifier = {{ name = {house_modifier} duration = 3650 }}" in block
        )
        modifiers_ok = all(
            re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text)
            for modifier in (route_modifier, house_modifier)
        )
        loc_ok = (
            f"{event_id}.t" in loc_keys
            and f"{event_id}.d" in loc_keys
            and f"{event_id}.a" in loc_keys
            and f"{event_id}.b" in loc_keys
            and all(modifier in loc_keys and f"{modifier}_desc" in loc_keys for modifier in (route_modifier, house_modifier))
        )
        cleanup_ok = (
            clear_effect_ok
            and f"clr_country_flag = {seen_flag}" in effect_text
            and f"remove_country_modifier = {route_modifier}" in effect_text
            and f"remove_country_modifier = {house_modifier}" in effect_text
        )
        checks = {
            "event": event_ok,
            "mtth": mtth_ok,
            "options": options_ok,
            "modifiers": modifiers_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        rows.append(f"{house} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{house}: missing or weak route-house resonance {name} coverage")

    return rows, issues


def founder_reform_pulse_report(mod: Path) -> tuple[list[str], list[str]]:
    event_text = read_text(mod / "events" / "jxp_38_founder_reform_pulse_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_38_founder_reform_pulse_modifiers.txt")
    trigger_text = read_text(mod / "common" / "scripted_triggers" / "jxp_38_founder_reform_pulse_triggers.txt")
    effect_text = read_many(files(mod / "common" / "scripted_effects", "*.txt"))
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")
    reform_by_origin = founder_reform_by_origin(mod)
    origins_by_house = archetype_origins(mod)

    house_events = [
        (
            "warrior",
            1,
            "jxp_has_warrior_founder_reform_trigger",
            "jxp_38_warrior_founder_reform_seen",
            "jxp_38_warrior_founder_military_codes",
            "jxp_38_warrior_founder_retainer_privileges",
        ),
        (
            "court",
            2,
            "jxp_has_court_founder_reform_trigger",
            "jxp_38_court_founder_reform_seen",
            "jxp_38_court_founder_office_precedents",
            "jxp_38_court_founder_domain_petitions",
        ),
        (
            "maritime",
            3,
            "jxp_has_maritime_founder_reform_trigger",
            "jxp_38_maritime_founder_reform_seen",
            "jxp_38_maritime_founder_port_compacts",
            "jxp_38_maritime_founder_admiralty_rolls",
        ),
        (
            "frontier",
            4,
            "jxp_has_frontier_founder_reform_trigger",
            "jxp_38_frontier_founder_reform_seen",
            "jxp_38_frontier_founder_barrier_offices",
            "jxp_38_frontier_founder_open_passes",
        ),
        (
            "temple_market",
            5,
            "jxp_has_temple_market_founder_reform_trigger",
            "jxp_38_temple_market_founder_reform_seen",
            "jxp_38_temple_founder_shrine_compact",
            "jxp_38_temple_founder_market_accounting",
        ),
    ]

    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_founder_reform_pulse\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Founder reform pulse coverage:")
    rows.append("house trigger event mtth options modifiers loc cleanup")
    clear_effect_ok = "jxp_clear_founder_reform_pulse_effect = yes" in debug_text

    for house, number, trigger, seen_flag, first_modifier, second_modifier in house_events:
        event_id = f"jxp_founder_reform_pulse.{number}"
        block = event_by_id.get(event_id, "")
        trigger_block = extract_block(trigger_text, trigger)
        origins = origins_by_house.get(house, [])
        expected_reforms = [reform_by_origin.get(origin, "") for origin in origins]
        trigger_ok = (
            bool(origins)
            and all(expected_reforms)
            and bool(trigger_block)
            and all(f"has_reform = {reform}" in trigger_block for reform in expected_reforms)
        )
        event_ok = (
            bool(block)
            and "jxp_is_unified_japan_state_trigger = yes" in block
            and trigger in block
            and f"NOT = {{ has_country_flag = {seen_flag} }}" in block
        )
        mtth_ok = "mean_time_to_happen" in block and re.search(r"\bmonths\s*=\s*3[3-5]0\b", block) is not None
        options_ok = (
            bool(block)
            and len(re.findall(r"(?m)^\s*option\s*=\s*\{", block)) == 2
            and f"set_country_flag = {seen_flag}" in block
            and "jxp_ensure_polity_mechanic_effect = yes" in block
            and f"add_country_modifier = {{ name = {first_modifier} duration = 5475 }}" in block
            and f"add_country_modifier = {{ name = {second_modifier} duration = 5475 }}" in block
        )
        modifiers_ok = all(
            re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text)
            for modifier in (first_modifier, second_modifier)
        )
        loc_ok = (
            f"{event_id}.t" in loc_keys
            and f"{event_id}.d" in loc_keys
            and f"{event_id}.a" in loc_keys
            and f"{event_id}.b" in loc_keys
            and all(modifier in loc_keys and f"{modifier}_desc" in loc_keys for modifier in (first_modifier, second_modifier))
        )
        cleanup_ok = (
            clear_effect_ok
            and f"clr_country_flag = {seen_flag}" in effect_text
            and f"remove_country_modifier = {first_modifier}" in effect_text
            and f"remove_country_modifier = {second_modifier}" in effect_text
        )
        checks = {
            "trigger": trigger_ok,
            "event": event_ok,
            "mtth": mtth_ok,
            "options": options_ok,
            "modifiers": modifiers_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        rows.append(f"{house} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{house}: missing or weak founder reform pulse {name} coverage")

    return rows, issues


def major_founder_house_policy_report(mod: Path) -> tuple[list[str], list[str]]:
    event_text = read_text(mod / "events" / "jxp_52_major_founder_house_policy_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_52_major_founder_house_policy_modifiers.txt")
    effect_text = read_text(mod / "common" / "scripted_effects" / "jxp_52_major_founder_house_policy_effects.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")

    expected = [
        ("ODA", 1, "jxp_reform_founder_oda_azuchi_statutes", "jxp_52_oda_major_founder_policy_seen", "jxp_52_oda_azuchi_bureau", "jxp_52_oda_rakuichi_markets"),
        ("TKG", 2, "jxp_reform_founder_tkg_mikawa_fudai_code", "jxp_52_tkg_major_founder_policy_seen", "jxp_52_tkg_fudai_roju", "jxp_52_tkg_road_barriers"),
        ("TKD", 3, "jxp_reform_founder_tkd_koshu_military_law", "jxp_52_tkd_major_founder_policy_seen", "jxp_52_tkd_koshu_banners", "jxp_52_tkd_mountain_codes"),
        ("UES", 4, "jxp_reform_founder_ues_kanto_justice", "jxp_52_ues_major_founder_policy_seen", "jxp_52_ues_kanto_justice", "jxp_52_ues_echigo_muster"),
        ("HJO", 5, "jxp_reform_founder_hjo_odawara_cadasters", "jxp_52_hjo_major_founder_policy_seen", "jxp_52_hjo_odawara_cadaster_review", "jxp_52_hjo_sogamae_watch"),
        ("MRI", 6, "jxp_reform_founder_mri_setouchi_admiralty", "jxp_52_mri_major_founder_policy_seen", "jxp_52_mri_setouchi_admiralty", "jxp_52_mri_kokujin_compacts"),
        ("SMZ", 7, "jxp_reform_founder_smz_satsuma_gunnery", "jxp_52_smz_major_founder_policy_seen", "jxp_52_smz_teppo_foundries", "jxp_52_smz_satsunan_learning"),
        ("OTM", 8, "jxp_reform_founder_otm_funai_arsenal", "jxp_52_otm_major_founder_policy_seen", "jxp_52_otm_funai_foreign_quarter", "jxp_52_otm_kunikuzushi_bureau"),
        ("DTE", 9, "jxp_reform_founder_dte_oshu_cavalry_envoys", "jxp_52_dte_major_founder_policy_seen", "jxp_52_dte_oshu_cavalry", "jxp_52_dte_keicho_embassy"),
        ("ASK", 10, "jxp_reform_founder_ask_muromachi_office", "jxp_52_ask_major_founder_policy_seen", "jxp_52_ask_hokoshu_order", "jxp_52_ask_higashiyama_culture"),
        ("CSK", 11, "jxp_reform_founder_csk_tosa_ichiryo_gusoku", "jxp_52_csk_major_founder_policy_seen", "jxp_52_csk_ichiryo_gusoku_rolls", "jxp_52_csk_tosa_sea_law"),
        ("OUC", 12, "jxp_reform_founder_ouc_yamaguchi_court", "jxp_52_ouc_major_founder_policy_seen", "jxp_52_ouc_yamaguchi_mercantile_court", "jxp_52_ouc_korean_envoys"),
        ("IMG", 13, "jxp_reform_founder_img_tokaido_lawbooks", "jxp_52_img_major_founder_policy_seen", "jxp_52_img_tokaido_lawbooks", "jxp_52_img_triple_alliance_model"),
        ("SOO", 14, "jxp_reform_founder_soo_tsushima_wakan", "jxp_52_soo_major_founder_policy_seen", "jxp_52_soo_wakan_office", "jxp_52_soo_tsushima_sea_wardens"),
    ]
    expected_tags = ["ODA", "TKG", "TKD", "UES", "HJO", "MRI", "SMZ", "OTM", "DTE", "ASK", "CSK", "OUC", "IMG", "SOO"]

    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_major_founder_house_policy\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Major founder house policy coverage:")
    rows.append("tag event mtth options modifiers loc cleanup")
    clear_effect_ok = "jxp_clear_major_founder_house_policy_effect = yes" in debug_text
    table_tags = [row[0] for row in expected]
    if table_tags != expected_tags:
        issues.append("major founder house policy: expected tag table drifted from the major-daimyo subset")

    for tag, number, reform, seen_flag, first_modifier, second_modifier in expected:
        event_id = f"jxp_major_founder_house_policy.{number}"
        block = event_by_id.get(event_id, "")
        event_ok = (
            bool(block)
            and "jxp_is_unified_japan_state_trigger = yes" in block
            and f"has_reform = {reform}" in block
            and f"NOT = {{ has_country_flag = {seen_flag} }}" in block
        )
        mtth_ok = "mean_time_to_happen" in block and re.search(r"\bmonths\s*=\s*3[6-8]0\b", block) is not None
        power_effects = re.findall(
            r"\bjxp_add_(?:tenka_order|imperial_sanction|oceanic_opening)_5_effect\s*=\s*yes\b",
            block,
        )
        options_ok = (
            bool(block)
            and len(re.findall(r"(?m)^\s*option\s*=\s*\{", block)) == 2
            and f"set_country_flag = {seen_flag}" in block
            and "jxp_ensure_polity_mechanic_effect = yes" in block
            and len(power_effects) >= 2
            and f"add_country_modifier = {{ name = {first_modifier} duration = 3650 }}" in block
            and f"add_country_modifier = {{ name = {second_modifier} duration = 3650 }}" in block
        )
        modifiers_ok = all(
            re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text)
            for modifier in (first_modifier, second_modifier)
        )
        loc_ok = (
            f"{event_id}.t" in loc_keys
            and f"{event_id}.d" in loc_keys
            and f"{event_id}.a" in loc_keys
            and f"{event_id}.b" in loc_keys
            and all(modifier in loc_keys and f"{modifier}_desc" in loc_keys for modifier in (first_modifier, second_modifier))
        )
        cleanup_ok = (
            clear_effect_ok
            and f"clr_country_flag = {seen_flag}" in effect_text
            and f"remove_country_modifier = {first_modifier}" in effect_text
            and f"remove_country_modifier = {second_modifier}" in effect_text
        )
        checks = {
            "event": event_ok,
            "mtth": mtth_ok,
            "options": options_ok,
            "modifiers": modifiers_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        rows.append(f"{tag} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{tag}: missing or weak major founder house policy {name} coverage")

    return rows, issues


def founder_idea_legacy_report(mod: Path) -> tuple[list[str], list[str]]:
    tags = expected_daimyo_tags(mod)
    decision_text = read_text(mod / "decisions" / "jxp_39_founder_idea_legacy_decisions.txt")
    event_text = read_text(mod / "events" / "jxp_39_founder_idea_legacy_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_39_founder_idea_legacy_modifiers.txt")
    effect_text = read_text(mod / "common" / "scripted_effects" / "jxp_39_founder_idea_legacy_effects.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")
    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_founder_idea_legacy\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    house_events = {
        "warrior": ("jxp_founder_idea_legacy.1", "jxp_39_warrior_idea_house_school"),
        "court": ("jxp_founder_idea_legacy.2", "jxp_39_court_idea_house_school"),
        "maritime": ("jxp_founder_idea_legacy.3", "jxp_39_maritime_idea_house_school"),
        "frontier": ("jxp_founder_idea_legacy.4", "jxp_39_frontier_idea_house_school"),
        "temple_market": ("jxp_founder_idea_legacy.5", "jxp_39_temple_market_idea_house_school"),
    }

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Founder idea legacy coverage:")
    rows.append("area decision/events modifiers loc cleanup")

    decision_ok = (
        "jxp_decision_compile_founder_idea_legacy" in decision_text
        and "jxp_is_unified_japan_state_trigger = yes" in decision_text
        and "jxp_has_founder_legacy_council_origin_trigger = yes" in decision_text
        and "NOT = { has_country_flag = jxp_39_founder_idea_legacy_compiled }" in decision_text
        and "add_adm_power = -75" in decision_text
        and all(event_id in decision_text for event_id, _modifier in house_events.values())
    )
    event_ok = True
    generic_modifiers_ok = True
    generic_loc_ok = True
    cleanup_ok = (
        "jxp_clear_founder_idea_legacy_effect = yes" in debug_text
        and "clr_country_flag = jxp_39_founder_idea_legacy_compiled" in effect_text
    )
    for house, (event_id, generic_modifier) in house_events.items():
        block = event_by_id.get(event_id, "")
        this_event_ok = (
            bool(block)
            and "is_triggered_only = yes" in block
            and len(re.findall(r"(?m)^\s*option\s*=\s*\{", block)) == 2
            and block.count("set_country_flag = jxp_39_founder_idea_legacy_compiled") == 2
            and "jxp_add_founder_idea_legacy_modifier_effect = yes" in block
            and f"add_country_modifier = {{ name = {generic_modifier} duration = -1 }}" in block
        )
        event_ok = event_ok and this_event_ok
        generic_modifiers_ok = generic_modifiers_ok and re.search(rf"(?m)^\s*{re.escape(generic_modifier)}\s*=\s*\{{", modifier_text) is not None
        generic_loc_ok = generic_loc_ok and generic_modifier in loc_keys and f"{generic_modifier}_desc" in loc_keys
        cleanup_ok = cleanup_ok and f"remove_country_modifier = {generic_modifier}" in effect_text
        if f"{event_id}.t" not in loc_keys or f"{event_id}.d" not in loc_keys or f"{event_id}.a" not in loc_keys or f"{event_id}.b" not in loc_keys:
            generic_loc_ok = False
        if not this_event_ok:
            issues.append(f"{house}: missing or weak founder idea legacy event")

    unique_modifiers_ok = True
    unique_loc_ok = True
    for tag in tags:
        low = tag.lower()
        modifier = f"jxp_39_{low}_idea_legacy"
        modifier_defined = re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text) is not None
        add_effect_ok = (
            f"has_country_flag = jxp_origin_{low}" in effect_text
            and f"add_country_modifier = {{ name = {modifier} duration = -1 }}" in effect_text
        )
        remove_effect_ok = f"remove_country_modifier = {modifier}" in effect_text
        loc_ok = modifier in loc_keys and f"{modifier}_desc" in loc_keys
        unique_modifiers_ok = unique_modifiers_ok and modifier_defined and add_effect_ok and remove_effect_ok
        unique_loc_ok = unique_loc_ok and loc_ok
        if not modifier_defined:
            issues.append(f"{tag}: missing founder idea legacy modifier")
        if not add_effect_ok:
            issues.append(f"{tag}: missing founder idea legacy origin add effect")
        if not remove_effect_ok:
            issues.append(f"{tag}: missing founder idea legacy cleanup")
        if not loc_ok:
            issues.append(f"{tag}: missing founder idea legacy localisation")

    checks = {
        "decision/events": decision_ok and event_ok,
        "modifiers": unique_modifiers_ok and generic_modifiers_ok,
        "loc": unique_loc_ok and generic_loc_ok,
        "cleanup": cleanup_ok,
    }
    rows.append("founder_ideas " + " ".join("OK" if checks[name] else "MISS" for name in checks))
    if not decision_ok:
        issues.append("founder idea legacy: decision dispatch or gating is incomplete")
    if not cleanup_ok:
        issues.append("founder idea legacy: debug cleanup or clear effect is incomplete")

    return rows, issues


def daimyo_house_diet_report(mod: Path) -> tuple[list[str], list[str]]:
    decision_text = read_text(mod / "decisions" / "jxp_34_daimyo_house_diets.txt")
    event_text = read_text(mod / "events" / "jxp_34_daimyo_house_diet_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_34_daimyo_house_diet_modifiers.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")
    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_house_diet\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    event_block = event_by_id.get("jxp_house_diet.1", "")
    archetypes = [
        (
            "warrior",
            "jxp_has_warrior_house_origin_trigger",
            ("jxp_house_diet.1.warrior_a", "jxp_house_diet.1.warrior_b"),
            ("jxp_34_warrior_muster_law", "jxp_34_warrior_captain_privileges"),
            ("jxp_34_selected_warrior_muster_law", "jxp_34_selected_warrior_captain_privileges"),
        ),
        (
            "court",
            "jxp_has_court_house_origin_trigger",
            ("jxp_house_diet.1.court_a", "jxp_house_diet.1.court_b"),
            ("jxp_34_court_rank_law", "jxp_34_court_domain_law"),
            ("jxp_34_selected_court_rank_law", "jxp_34_selected_court_domain_law"),
        ),
        (
            "maritime",
            "jxp_has_maritime_house_origin_trigger",
            ("jxp_house_diet.1.maritime_a", "jxp_house_diet.1.maritime_b"),
            ("jxp_34_maritime_port_law", "jxp_34_maritime_admiral_rolls"),
            ("jxp_34_selected_maritime_port_law", "jxp_34_selected_maritime_admiral_rolls"),
        ),
        (
            "frontier",
            "jxp_has_frontier_house_origin_trigger",
            ("jxp_house_diet.1.frontier_a", "jxp_house_diet.1.frontier_b"),
            ("jxp_34_frontier_barrier_law", "jxp_34_frontier_market_charter"),
            ("jxp_34_selected_frontier_barrier_law", "jxp_34_selected_frontier_market_charter"),
        ),
        (
            "temple_market",
            "jxp_has_temple_market_house_origin_trigger",
            ("jxp_house_diet.1.temple_market_a", "jxp_house_diet.1.temple_market_b"),
            ("jxp_34_temple_privilege_law", "jxp_34_temple_accounting_law"),
            ("jxp_34_selected_temple_privilege_law", "jxp_34_selected_temple_accounting_law"),
        ),
    ]

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Daimyo house diet coverage:")
    rows.append("chain decision event fallback loc cleanup")

    decision_ok = (
        "jxp_decision_convene_house_diet" in decision_text
        and "jxp_is_daimyo_stage_trigger = yes" in decision_text
        and "jxp_is_major_daimyo_tag_trigger = yes" in decision_text
        and "NOT = { has_country_flag = jxp_34_house_diet_convened }" in decision_text
        and "jxp_ensure_daimyo_polity_effect = yes" in decision_text
        and "country_event = { id = jxp_house_diet.1 }" in decision_text
    )
    event_ok = (
        bool(event_block)
        and "is_triggered_only = yes" in event_block
        and "set_country_flag = jxp_34_house_diet_convened" in event_block
        and len(re.findall(r"(?m)^\s*option\s*=\s*\{", event_block)) >= 10
    )
    fallback_ok = (
        "jxp_house_diet.1.fallback" in event_block
        and "NOT = { jxp_has_founder_legacy_council_origin_trigger = yes }" in event_block
    )
    chain_loc_ok = {
        "jxp_decision_convene_house_diet_title",
        "jxp_decision_convene_house_diet_desc",
        "jxp_house_diet.1.t",
        "jxp_house_diet.1.d",
        "jxp_house_diet.1.fallback",
    }.issubset(loc_keys)
    chain_cleanup_ok = "clr_country_flag = jxp_34_house_diet_convened" in debug_text
    rows.append(
        "house_diet "
        + " ".join(
            "OK" if ok else "MISS"
            for ok in (decision_ok, event_ok, fallback_ok, chain_loc_ok, chain_cleanup_ok)
        )
    )
    for name, ok in {
        "decision": decision_ok,
        "event": event_ok,
        "fallback": fallback_ok,
        "loc": chain_loc_ok,
        "cleanup": chain_cleanup_ok,
    }.items():
        if not ok:
            issues.append(f"house_diet: missing or weak {name} coverage")

    rows.append("archetype options modifiers loc cleanup")
    for archetype, trigger, option_keys, modifier_keys, selection_flags in archetypes:
        options_ok = (
            all(option_key in event_block for option_key in option_keys)
            and trigger in event_block
            and all(f"add_country_modifier = {{ name = {modifier} duration = 7300 }}" in event_block for modifier in modifier_keys)
            and all(f"set_country_flag = {flag}" in event_block for flag in selection_flags)
        )
        modifiers_ok = all(f"{modifier} =" in modifier_text for modifier in modifier_keys)
        loc_ok = all(key in loc_keys and f"{key}_desc" in loc_keys for key in modifier_keys) and all(
            option_key in loc_keys for option_key in option_keys
        )
        cleanup_ok = all(f"remove_country_modifier = {modifier}" in debug_text for modifier in modifier_keys) and all(
            f"clr_country_flag = {flag}" in debug_text for flag in selection_flags
        )
        rows.append(
            f"{archetype} "
            + " ".join("OK" if ok else "MISS" for ok in (options_ok, modifiers_ok, loc_ok, cleanup_ok))
        )
        for name, ok in {
            "options": options_ok,
            "modifiers": modifiers_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }.items():
            if not ok:
                issues.append(f"{archetype}: missing or weak house diet {name} coverage")

    return rows, issues


def house_diet_legacy_report(mod: Path) -> tuple[list[str], list[str]]:
    decision_text = read_text(mod / "decisions" / "jxp_35_house_diet_legacy_decisions.txt")
    event_text = read_text(mod / "events" / "jxp_35_house_diet_legacy_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_35_house_diet_legacy_modifiers.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")
    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_house_diet_legacy\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    block = event_by_id.get("jxp_house_diet_legacy.1", "")
    choices = [
        (
            "warrior_muster",
            "jxp_34_selected_warrior_muster_law",
            "jxp_34_warrior_muster_law",
            "jxp_house_diet_legacy.1.warrior_muster",
            "jxp_35_legacy_warrior_muster_law",
        ),
        (
            "warrior_captain",
            "jxp_34_selected_warrior_captain_privileges",
            "jxp_34_warrior_captain_privileges",
            "jxp_house_diet_legacy.1.warrior_captain",
            "jxp_35_legacy_warrior_captain_privileges",
        ),
        (
            "court_rank",
            "jxp_34_selected_court_rank_law",
            "jxp_34_court_rank_law",
            "jxp_house_diet_legacy.1.court_rank",
            "jxp_35_legacy_court_rank_law",
        ),
        (
            "court_domain",
            "jxp_34_selected_court_domain_law",
            "jxp_34_court_domain_law",
            "jxp_house_diet_legacy.1.court_domain",
            "jxp_35_legacy_court_domain_law",
        ),
        (
            "maritime_port",
            "jxp_34_selected_maritime_port_law",
            "jxp_34_maritime_port_law",
            "jxp_house_diet_legacy.1.maritime_port",
            "jxp_35_legacy_maritime_port_law",
        ),
        (
            "maritime_admiral",
            "jxp_34_selected_maritime_admiral_rolls",
            "jxp_34_maritime_admiral_rolls",
            "jxp_house_diet_legacy.1.maritime_admiral",
            "jxp_35_legacy_maritime_admiral_rolls",
        ),
        (
            "frontier_barrier",
            "jxp_34_selected_frontier_barrier_law",
            "jxp_34_frontier_barrier_law",
            "jxp_house_diet_legacy.1.frontier_barrier",
            "jxp_35_legacy_frontier_barrier_law",
        ),
        (
            "frontier_market",
            "jxp_34_selected_frontier_market_charter",
            "jxp_34_frontier_market_charter",
            "jxp_house_diet_legacy.1.frontier_market",
            "jxp_35_legacy_frontier_market_charter",
        ),
        (
            "temple_privilege",
            "jxp_34_selected_temple_privilege_law",
            "jxp_34_temple_privilege_law",
            "jxp_house_diet_legacy.1.temple_privilege",
            "jxp_35_legacy_temple_privilege_law",
        ),
        (
            "temple_accounting",
            "jxp_34_selected_temple_accounting_law",
            "jxp_34_temple_accounting_law",
            "jxp_house_diet_legacy.1.temple_accounting",
            "jxp_35_legacy_temple_accounting_law",
        ),
    ]

    rows: list[str] = []
    issues: list[str] = []
    rows.append("House diet legacy coverage:")
    rows.append("chain decision event fallback loc cleanup")
    decision_ok = (
        "jxp_decision_integrate_house_diet_law" in decision_text
        and "jxp_is_unified_japan_state_trigger = yes" in decision_text
        and "has_country_flag = jxp_34_house_diet_convened" in decision_text
        and "NOT = { has_country_flag = jxp_35_house_diet_law_integrated }" in decision_text
        and "country_event = { id = jxp_house_diet_legacy.1 }" in decision_text
    )
    event_ok = (
        bool(block)
        and "is_triggered_only = yes" in block
        and "set_country_flag = jxp_35_house_diet_law_integrated" in block
        and len(re.findall(r"(?m)^\s*option\s*=\s*\{", block)) >= 10
    )
    fallback_ok = "jxp_house_diet_legacy.1.fallback" in block and all(
        f"NOT = {{ has_country_flag = {selection_flag} }}" in block for _, selection_flag, _, _, _ in choices
    )
    chain_loc_ok = {
        "jxp_decision_integrate_house_diet_law_title",
        "jxp_decision_integrate_house_diet_law_desc",
        "jxp_house_diet_legacy.1.t",
        "jxp_house_diet_legacy.1.d",
        "jxp_house_diet_legacy.1.fallback",
    }.issubset(loc_keys)
    chain_cleanup_ok = "clr_country_flag = jxp_35_house_diet_law_integrated" in debug_text
    rows.append(
        "house_diet_legacy "
        + " ".join("OK" if ok else "MISS" for ok in (decision_ok, event_ok, fallback_ok, chain_loc_ok, chain_cleanup_ok))
    )
    for name, ok in {
        "decision": decision_ok,
        "event": event_ok,
        "fallback": fallback_ok,
        "loc": chain_loc_ok,
        "cleanup": chain_cleanup_ok,
    }.items():
        if not ok:
            issues.append(f"house_diet_legacy: missing or weak {name} coverage")

    rows.append("choice event modifier loc cleanup")
    for choice, selection_flag, old_modifier, option_key, legacy_modifier in choices:
        event_choice_ok = (
            option_key in block
            and f"has_country_flag = {selection_flag}" in block
            and f"remove_country_modifier = {old_modifier}" in block
            and f"add_country_modifier = {{ name = {legacy_modifier} duration = -1 }}" in block
        )
        modifier_ok = f"{legacy_modifier} =" in modifier_text
        loc_ok = option_key in loc_keys and legacy_modifier in loc_keys and f"{legacy_modifier}_desc" in loc_keys
        cleanup_ok = f"remove_country_modifier = {legacy_modifier}" in debug_text
        rows.append(
            f"{choice} "
            + " ".join("OK" if ok else "MISS" for ok in (event_choice_ok, modifier_ok, loc_ok, cleanup_ok))
        )
        for name, ok in {
            "event": event_choice_ok,
            "modifier": modifier_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }.items():
            if not ok:
                issues.append(f"{choice}: missing or weak house diet legacy {name} coverage")

    return rows, issues


def house_diet_mission_report(mod: Path) -> tuple[list[str], list[str]]:
    mission_text = read_text(mod / "missions" / "jxp_36_house_diet_legacy_missions.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_36_house_diet_mission_modifiers.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    group_block = extract_block(mission_text, "jxp_house_diet_legacy_missions")
    legacy_modifiers = [
        "jxp_35_legacy_warrior_muster_law",
        "jxp_35_legacy_warrior_captain_privileges",
        "jxp_35_legacy_court_rank_law",
        "jxp_35_legacy_court_domain_law",
        "jxp_35_legacy_maritime_port_law",
        "jxp_35_legacy_maritime_admiral_rolls",
        "jxp_35_legacy_frontier_barrier_law",
        "jxp_35_legacy_frontier_market_charter",
        "jxp_35_legacy_temple_privilege_law",
        "jxp_35_legacy_temple_accounting_law",
    ]
    missions = [
        (
            "into_realm",
            "jxp_mission_house_diet_into_realm",
            "position = 33",
            "has_country_flag = jxp_35_house_diet_law_integrated",
            "jxp_36_integrated_house_diet_records",
        ),
        (
            "local_offices",
            "jxp_mission_house_law_local_offices",
            "position = 34",
            "required_missions = { jxp_mission_house_diet_into_realm }",
            "jxp_36_house_law_local_offices",
        ),
        (
            "state_doctrine",
            "jxp_mission_house_law_state_doctrine",
            "position = 35",
            "required_missions = { jxp_mission_house_law_local_offices }",
            "jxp_36_house_law_state_doctrine",
        ),
    ]
    rows: list[str] = []
    issues: list[str] = []
    rows.append("House diet mission coverage:")
    rows.append("chain group loc cleanup")
    group_ok = (
        bool(group_block)
        and "slot = 5" in group_block
        and "always = no" in group_block
        and "generic = no" in group_block
        and all(f"tag = {tag}" in group_block for tag in ("JAP", "KJP", "CJP", "EJP", "RFJ", "SJP", "IJP", "WAK"))
    )
    chain_loc_ok = all(
        key in loc_keys
        for key in (
            "jxp_mission_house_diet_into_realm_title",
            "jxp_mission_house_diet_into_realm_desc",
            "jxp_mission_house_law_local_offices_title",
            "jxp_mission_house_law_local_offices_desc",
            "jxp_mission_house_law_state_doctrine_title",
            "jxp_mission_house_law_state_doctrine_desc",
        )
    )
    cleanup_ok = all(
        f"remove_country_modifier = {modifier}" in debug_text
        for modifier in (
            "jxp_36_integrated_house_diet_records",
            "jxp_36_house_law_local_offices",
            "jxp_36_house_law_state_doctrine",
        )
    )
    rows.append(
        "house_diet_missions "
        + " ".join("OK" if ok else "MISS" for ok in (group_ok, chain_loc_ok, cleanup_ok))
    )
    for name, ok in {"group": group_ok, "loc": chain_loc_ok, "cleanup": cleanup_ok}.items():
        if not ok:
            issues.append(f"house_diet_missions: missing or weak {name} coverage")

    rows.append("mission block trigger modifier loc cleanup")
    for label, mission_key, position_token, trigger_token, reward_modifier in missions:
        block = extract_block(mission_text, mission_key)
        block_ok = bool(block) and position_token in block and trigger_token in block
        if label == "local_offices":
            block_ok = block_ok and all(f"has_country_modifier = {modifier}" in block for modifier in legacy_modifiers)
        if label == "state_doctrine":
            block_ok = block_ok and all(
                token in block
                for token in (
                    "jxp_tenka_order_at_least_75 = yes",
                    "jxp_imperial_sanction_at_least_70 = yes",
                    "jxp_oceanic_opening_at_least_75 = yes",
                )
            )
        modifier_ok = (
            f"{reward_modifier} =" in modifier_text
            and "add_country_modifier" in block
            and f"name = {reward_modifier}" in block
        )
        loc_ok = reward_modifier in loc_keys and f"{reward_modifier}_desc" in loc_keys
        cleanup_modifier_ok = f"remove_country_modifier = {reward_modifier}" in debug_text
        rows.append(
            f"{label} "
            + " ".join("OK" if ok else "MISS" for ok in (block_ok, modifier_ok, loc_ok, cleanup_modifier_ok))
        )
        for name, ok in {
            "block": block_ok,
            "modifier": modifier_ok,
            "loc": loc_ok,
            "cleanup": cleanup_modifier_ok,
        }.items():
            if not ok:
                issues.append(f"{label}: missing or weak house diet mission {name} coverage")

    return rows, issues


def specific_route_house_combo_report(mod: Path) -> tuple[list[str], list[str]]:
    event_text = read_text(mod / "events" / "jxp_31_specific_route_house_events.txt")
    modifier_text = read_text(mod / "common" / "event_modifiers" / "jxp_31_specific_route_house_modifiers.txt")
    effect_text = read_text(mod / "common" / "scripted_effects" / "jxp_31_specific_route_house_effects.txt")
    debug_text = read_text(mod / "common" / "scripted_effects" / "jxp_debug_effects.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)
    event_blocks = extract_assignment_blocks(event_text, "country_event")

    combos = [
        (
            "otm_kirishitan",
            1,
            "jxp_origin_otm",
            ("jxp_path_kirishitan", "tag = KJP"),
            "jxp_31_otm_kirishitan_combo_seen",
            ("jxp_31_otm_funai_bishopric_court", "jxp_31_otm_bungo_retainer_compromise"),
        ),
        (
            "mri_open",
            2,
            "jxp_origin_mri",
            ("jxp_path_open_trade",),
            "jxp_31_mri_open_combo_seen",
            ("jxp_31_mri_setouchi_red_seals", "jxp_31_mri_kokujin_sea_oaths"),
        ),
        (
            "ask_imperial",
            3,
            "jxp_origin_ask",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_ask_imperial_combo_seen",
            ("jxp_31_ask_imperial_restoration_letters", "jxp_31_ask_hokoshu_court_guard"),
        ),
        (
            "asa_confucian",
            4,
            "jxp_origin_asa",
            ("jxp_path_confucian", "tag = CJP"),
            "jxp_31_asa_confucian_combo_seen",
            ("jxp_31_asa_ichijodani_academies", "jxp_31_asa_echizen_house_rites"),
        ),
        (
            "dte_open",
            5,
            "jxp_origin_dte",
            ("jxp_path_open_trade",),
            "jxp_31_dte_open_combo_seen",
            ("jxp_31_dte_keicho_embassy_routes", "jxp_31_dte_oshu_envoy_oaths"),
        ),
        (
            "soo_wokou",
            6,
            "jxp_origin_soo",
            ("jxp_path_wokou", "tag = WAK"),
            "jxp_31_soo_wokou_combo_seen",
            ("jxp_31_soo_tsushima_channel_writs", "jxp_31_soo_wakan_sea_wardens"),
        ),
        (
            "oda_open",
            7,
            "jxp_origin_oda",
            ("jxp_path_open_trade",),
            "jxp_31_oda_open_combo_seen",
            ("jxp_31_oda_azuchi_red_seal_markets", "jxp_31_oda_tenka_market_officers"),
        ),
        (
            "tkg_sakoku",
            8,
            "jxp_origin_tkg",
            ("jxp_path_sakoku",),
            "jxp_31_tkg_sakoku_combo_seen",
            ("jxp_31_tkg_fudai_closed_country", "jxp_31_tkg_mikawa_hostage_order"),
        ),
        (
            "tkd_confucian",
            9,
            "jxp_origin_tkd",
            ("jxp_path_confucian", "tag = CJP"),
            "jxp_31_tkd_confucian_combo_seen",
            ("jxp_31_tkd_koshu_confucian_law", "jxp_31_tkd_mountain_house_codes"),
        ),
        (
            "ues_imperial",
            10,
            "jxp_origin_ues",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_ues_imperial_combo_seen",
            ("jxp_31_ues_imperial_kanrei_letters", "jxp_31_ues_echigo_justice_oaths"),
        ),
        (
            "hjo_sakoku",
            11,
            "jxp_origin_hjo",
            ("jxp_path_sakoku",),
            "jxp_31_hjo_sakoku_combo_seen",
            ("jxp_31_hjo_odawara_closed_cadasters", "jxp_31_hjo_sogamae_domain_watch"),
        ),
        (
            "smz_kaikyo",
            12,
            "jxp_origin_smz",
            ("jxp_path_kaikyo", "tag = SJP"),
            "jxp_31_smz_kaikyo_combo_seen",
            ("jxp_31_smz_satsunan_halal_ports", "jxp_31_smz_satsuma_gunfounder_compact"),
        ),
        (
            "csk_ikko",
            13,
            "jxp_origin_csk",
            ("jxp_path_ikko", "tag = IJP"),
            "jxp_31_csk_ikko_combo_seen",
            ("jxp_31_csk_ichiryo_monto_muster", "jxp_31_csk_tosa_peasant_oaths"),
        ),
        (
            "ouc_open",
            14,
            "jxp_origin_ouc",
            ("jxp_path_open_trade",),
            "jxp_31_ouc_open_combo_seen",
            ("jxp_31_ouc_yamaguchi_sea_tribute", "jxp_31_ouc_suofu_merchant_council"),
        ),
        (
            "img_confucian",
            15,
            "jxp_origin_img",
            ("jxp_path_confucian", "tag = CJP"),
            "jxp_31_img_confucian_combo_seen",
            ("jxp_31_img_tokaido_confucian_codes", "jxp_31_img_suruga_house_law"),
        ),
        (
            "ama_sakoku",
            16,
            "jxp_origin_ama",
            ("jxp_path_sakoku",),
            "jxp_31_ama_sakoku_combo_seen",
            ("jxp_31_ama_gassan_closed_mines", "jxp_31_ama_shingu_retainer_rolls"),
        ),
        (
            "hsk_imperial",
            17,
            "jxp_origin_hsk",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_hsk_imperial_combo_seen",
            ("jxp_31_hsk_kanrei_restoration_cabinet", "jxp_31_hsk_sakai_court_brokers"),
        ),
        (
            "htk_reformed",
            18,
            "jxp_origin_htk",
            ("jxp_path_reformed", "tag = RFJ"),
            "jxp_31_htk_reformed_combo_seen",
            ("jxp_31_htk_wakae_synodic_oaths", "jxp_31_htk_kawachi_retainer_compact"),
        ),
        (
            "ike_open",
            19,
            "jxp_origin_ike",
            ("jxp_path_open_trade",),
            "jxp_31_ike_open_combo_seen",
            ("jxp_31_ike_himeji_oceanic_stewards", "jxp_31_ike_harima_castle_accounts"),
        ),
        (
            "mae_confucian",
            20,
            "jxp_origin_mae",
            ("jxp_path_confucian", "tag = CJP"),
            "jxp_31_mae_confucian_combo_seen",
            ("jxp_31_mae_kaga_confucian_academies", "jxp_31_mae_million_koku_granaries"),
        ),
        (
            "sba_imperial",
            21,
            "jxp_origin_sba",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_sba_imperial_combo_seen",
            ("jxp_31_sba_buei_imperial_offices", "jxp_31_sba_owari_house_guards"),
        ),
        (
            "ymn_imperial",
            22,
            "jxp_origin_ymn",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_ymn_imperial_combo_seen",
            ("jxp_31_ymn_roku_bun_ichi_rankings", "jxp_31_ymn_sanin_guard_houses"),
        ),
        (
            "rfr_sakoku",
            23,
            "jxp_origin_rfr",
            ("jxp_path_sakoku",),
            "jxp_31_rfr_sakoku_combo_seen",
            ("jxp_31_rfr_mutsu_border_cordon", "jxp_31_rfr_nine_gates_horse_rolls"),
        ),
        (
            "ktb_imperial",
            24,
            "jxp_origin_ktb",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_ktb_imperial_combo_seen",
            ("jxp_31_ktb_ise_imperial_rites", "jxp_31_ktb_kitabatake_court_law"),
        ),
        (
            "akm_sakoku",
            25,
            "jxp_origin_akm",
            ("jxp_path_sakoku",),
            "jxp_31_akm_sakoku_combo_seen",
            ("jxp_31_akm_harima_closed_roads", "jxp_31_akm_akasaka_retainer_codes"),
        ),
        (
            "akt_open",
            26,
            "jxp_origin_akt",
            ("jxp_path_open_trade",),
            "jxp_31_akt_open_combo_seen",
            ("jxp_31_akt_ezochi_trade_brokers", "jxp_31_akt_northern_watch_posts"),
        ),
        (
            "cba_sakoku",
            27,
            "jxp_origin_cba",
            ("jxp_path_sakoku",),
            "jxp_31_cba_sakoku_combo_seen",
            ("jxp_31_cba_katori_closed_musters", "jxp_31_cba_shimosa_barrier_law"),
        ),
        (
            "isk_open",
            28,
            "jxp_origin_isk",
            ("jxp_path_open_trade",),
            "jxp_31_isk_open_combo_seen",
            ("jxp_31_isk_tango_open_wardens", "jxp_31_isk_amanohashidate_pilots"),
        ),
        (
            "ito_kirishitan",
            29,
            "jxp_origin_ito",
            ("jxp_path_kirishitan", "tag = KJP"),
            "jxp_31_ito_kirishitan_combo_seen",
            ("jxp_31_ito_hyuga_seminary_castles", "jxp_31_ito_hyuga_clan_chapels"),
        ),
        (
            "kkc_confucian",
            30,
            "jxp_origin_kkc",
            ("jxp_path_confucian", "tag = CJP"),
            "jxp_31_kkc_confucian_combo_seen",
            ("jxp_31_kkc_aso_rite_schools", "jxp_31_kkc_kikuchi_hill_codes"),
        ),
        (
            "kno_wokou",
            31,
            "jxp_origin_kno",
            ("jxp_path_wokou", "tag = WAK"),
            "jxp_31_kno_wokou_combo_seen",
            ("jxp_31_kno_setouchi_corsair_pilots", "jxp_31_kno_iyo_sea_oaths"),
        ),
        (
            "ogs_imperial",
            32,
            "jxp_origin_ogs",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_ogs_imperial_combo_seen",
            ("jxp_31_ogs_suwa_imperial_archers", "jxp_31_ogs_shinano_horse_law"),
        ),
        (
            "shn_kaikyo",
            33,
            "jxp_origin_shn",
            ("jxp_path_kaikyo", "tag = SJP"),
            "jxp_31_shn_kaikyo_combo_seen",
            ("jxp_31_shn_dazaifu_maritime_brokers", "jxp_31_shn_kyushu_gateway_guards"),
        ),
        (
            "stk_imperial",
            34,
            "jxp_origin_stk",
            ("jxp_path_imperial", "tag = EJP"),
            "jxp_31_stk_imperial_combo_seen",
            ("jxp_31_stk_hitachi_imperial_musters", "jxp_31_stk_eastern_warrior_rolls"),
        ),
        (
            "tki_confucian",
            35,
            "jxp_origin_tki",
            ("jxp_path_confucian", "tag = CJP"),
            "jxp_31_tki_confucian_combo_seen",
            ("jxp_31_tki_mino_confucian_river_offices", "jxp_31_tki_toki_house_lawbooks"),
        ),
        (
            "utn_sakoku",
            36,
            "jxp_origin_utn",
            ("jxp_path_sakoku",),
            "jxp_31_utn_sakoku_combo_seen",
            ("jxp_31_utn_nikko_closed_barriers", "jxp_31_utn_shimotsuke_shrine_guard"),
        ),
        (
            "tti_ikko",
            37,
            "jxp_origin_tti",
            ("jxp_path_ikko", "tag = IJP"),
            "jxp_31_tti_ikko_combo_seen",
            ("jxp_31_tti_yamato_monto_compact", "jxp_31_tti_nara_temple_mediation"),
        ),
    ]

    event_by_id: dict[str, str] = {}
    for block in event_blocks:
        id_match = re.search(r"\bid\s*=\s*(jxp_specific_route_house\.\d+)\b", block)
        if id_match:
            event_by_id[id_match.group(1)] = block

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Specific route-house combo coverage:")
    rows.append("combo event mtth options modifiers loc cleanup")

    clear_effect_ok = "jxp_clear_specific_route_house_combo_effect = yes" in debug_text
    covered_origins = {origin_flag.removeprefix("jxp_origin_") for _, _, origin_flag, _, _, _ in combos}
    expected_origins = {tag.lower() for tag in expected_daimyo_tags(mod)}
    missing_expected_origins = sorted(expected_origins - covered_origins)
    major_origins = {"oda", "tkg", "tkd", "ues", "hjo", "mri", "smz", "otm", "dte", "ask", "csk", "ouc", "img", "soo"}
    missing_major_origins = sorted(major_origins - covered_origins)
    rows.append(f"major_origin_combo_coverage {len(major_origins) - len(missing_major_origins)}/{len(major_origins)}")
    rows.append(f"all_origin_combo_coverage {len(expected_origins) - len(missing_expected_origins)}/{len(expected_origins)}")
    if missing_major_origins:
        issues.append("specific route-house combos: missing major origin coverage for " + ", ".join(missing_major_origins))
    if missing_expected_origins:
        issues.append("specific route-house combos: missing expected origin coverage for " + ", ".join(missing_expected_origins))

    for combo, number, origin_flag, route_tokens, seen_flag, modifiers in combos:
        event_id = f"jxp_specific_route_house.{number}"
        block = event_by_id.get(event_id, "")
        event_ok = (
            bool(block)
            and "jxp_is_unified_japan_state_trigger = yes" in block
            and f"has_country_flag = {origin_flag}" in block
            and all(token in block for token in route_tokens)
            and f"NOT = {{ has_country_flag = {seen_flag} }}" in block
        )
        mtth_ok = "mean_time_to_happen" in block and re.search(r"\bmonths\s*=\s*(3[0-2]0)\b", block) is not None
        options_ok = (
            bool(block)
            and len(re.findall(r"(?m)^\s*option\s*=\s*\{", block)) == 2
            and all(f"add_country_modifier = {{ name = {modifier} duration = 3650 }}" in block for modifier in modifiers)
            and f"set_country_flag = {seen_flag}" in block
        )
        modifiers_ok = all(
            re.search(rf"(?m)^\s*{re.escape(modifier)}\s*=\s*\{{", modifier_text)
            for modifier in modifiers
        )
        loc_ok = (
            f"{event_id}.t" in loc_keys
            and f"{event_id}.d" in loc_keys
            and f"{event_id}.a" in loc_keys
            and f"{event_id}.b" in loc_keys
            and all(modifier in loc_keys and f"{modifier}_desc" in loc_keys for modifier in modifiers)
        )
        cleanup_ok = (
            clear_effect_ok
            and f"clr_country_flag = {seen_flag}" in effect_text
            and all(f"remove_country_modifier = {modifier}" in effect_text for modifier in modifiers)
        )
        checks = {
            "event": event_ok,
            "mtth": mtth_ok,
            "options": options_ok,
            "modifiers": modifiers_ok,
            "loc": loc_ok,
            "cleanup": cleanup_ok,
        }
        rows.append(f"{combo} " + " ".join("OK" if checks[name] else "MISS" for name in checks))
        for name, ok in checks.items():
            if not ok:
                issues.append(f"{combo}: missing or weak specific route-house combo {name} coverage")

    return rows, issues


def legacy_cabinet_report(mod: Path) -> tuple[list[str], list[str]]:
    decision_text = read_text(mod / "decisions" / "jxp_50_legacy_cabinet_decisions.txt")
    trigger_text = read_text(mod / "common" / "scripted_triggers" / "jxp_50_legacy_cabinet_triggers.txt")
    effect_text = read_text(mod / "common" / "scripted_effects" / "jxp_50_legacy_cabinet_effects.txt")
    event_text = read_text(mod / "events" / "jxp_50_legacy_cabinet_events.txt")
    loc_text = read_many(files(mod / "localisation_source", "*.yml"))
    loc_keys = localisation_keys(loc_text)

    rows: list[str] = []
    issues: list[str] = []
    rows.append("Legacy cabinet consolidation coverage:")
    rows.append("area status")

    decision_ok = (
        "jxp_decision_convene_legacy_cabinet" in decision_text
        and "jxp_50_any_legacy_cabinet_available_trigger = yes" in decision_text
        and "jxp_50_any_legacy_cabinet_allowed_trigger = yes" in decision_text
        and "country_event = { id = jxp_legacy_cabinet.1 }" in decision_text
    )
    rows.append(f"central_decision {'OK' if decision_ok else 'MISS'}")
    if not decision_ok:
        issues.append("legacy cabinet: missing or weak central decision")

    expected_triggers = [
        "jxp_50_founder_legacy_available_trigger",
        "jxp_50_founder_legacy_allowed_trigger",
        "jxp_50_founder_idea_available_trigger",
        "jxp_50_founder_idea_allowed_trigger",
        "jxp_50_preunification_memory_available_trigger",
        "jxp_50_preunification_memory_allowed_trigger",
        "jxp_50_house_diet_legacy_available_trigger",
        "jxp_50_house_diet_legacy_allowed_trigger",
        "jxp_50_route_house_compromise_available_trigger",
        "jxp_50_route_house_compromise_allowed_trigger",
        "jxp_50_any_legacy_cabinet_available_trigger",
        "jxp_50_any_legacy_cabinet_allowed_trigger",
    ]
    triggers_ok = all(f"{trigger} =" in trigger_text for trigger in expected_triggers)
    rows.append(f"scripted_triggers {'OK' if triggers_ok else 'MISS'}")
    if not triggers_ok:
        issues.append("legacy cabinet: missing scripted trigger")

    expected_effects = [
        "jxp_50_execute_founder_legacy_effect",
        "jxp_50_execute_founder_idea_effect",
        "jxp_50_execute_preunification_memory_effect",
        "jxp_50_execute_house_diet_legacy_effect",
        "jxp_50_execute_route_house_compromise_effect",
    ]
    effect_tokens = [
        "add_adm_power = -50",
        "add_adm_power = -75",
        "add_dip_power = -50",
        "add_adm_power = -25",
        "add_dip_power = -25",
        "country_event = { id = jxp_founder_legacy.1 }",
        "country_event = { id = jxp_founder_legacy.37 }",
        "country_event = { id = jxp_founder_idea_legacy.1 }",
        "country_event = { id = jxp_founder_idea_legacy.5 }",
        "country_event = { id = jxp_preunification_memory.1 }",
        "country_event = { id = jxp_preunification_memory.37 }",
        "country_event = { id = jxp_house_diet_legacy.1 }",
        "country_event = { id = jxp_route_house_compromise.1 }",
        "country_event = { id = jxp_route_house_compromise.9 }",
        "jxp_sanitize_route_state_effect = yes",
    ]
    effects_ok = all(f"{effect} =" in effect_text for effect in expected_effects) and all(
        token in effect_text for token in effect_tokens
    )
    rows.append(f"scripted_effects {'OK' if effects_ok else 'MISS'}")
    if not effects_ok:
        issues.append("legacy cabinet: missing old-chain dispatch or cost effect")

    event_options_ok = (
        "id = jxp_legacy_cabinet.1" in event_text
        and all(f"{effect} = yes" in event_text for effect in expected_effects)
        and len(re.findall(r"(?m)^\s*option\s*=\s*\{", event_text)) == 6
    )
    rows.append(f"event_menu {'OK' if event_options_ok else 'MISS'}")
    if not event_options_ok:
        issues.append("legacy cabinet: event menu is incomplete")

    old_decision_files = [
        "jxp_26_founder_legacy_councils.txt",
        "jxp_39_founder_idea_legacy_decisions.txt",
        "jxp_43_preunification_memory_decisions.txt",
        "jxp_35_house_diet_legacy_decisions.txt",
        "jxp_29_route_house_compromise_decisions.txt",
    ]
    hidden_ok = all(
        "has_country_flag = jxp_50_show_legacy_detail_decisions"
        in read_text(mod / "decisions" / filename)
        for filename in old_decision_files
    )
    rows.append(f"old_detail_decisions_hidden {'OK' if hidden_ok else 'MISS'}")
    if not hidden_ok:
        issues.append("legacy cabinet: old detail decisions are not all hidden behind debug/detail flag")

    required_loc = {
        "jxp_decision_convene_legacy_cabinet_title",
        "jxp_decision_convene_legacy_cabinet_desc",
        "jxp_legacy_cabinet.1.t",
        "jxp_legacy_cabinet.1.d",
        "jxp_legacy_cabinet.1.a",
        "jxp_legacy_cabinet.1.b",
        "jxp_legacy_cabinet.1.c",
        "jxp_legacy_cabinet.1.d_option",
        "jxp_legacy_cabinet.1.e",
        "jxp_legacy_cabinet.1.f",
    }
    loc_ok = required_loc.issubset(loc_keys)
    rows.append(f"localisation {'OK' if loc_ok else 'MISS'}")
    if not loc_ok:
        missing = sorted(required_loc - loc_keys)
        issues.append("legacy cabinet: missing localisation keys " + ", ".join(missing))

    return rows, issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mod_path", type=Path, help="Path to japan_expanded_v2 mod folder")
    parser.add_argument(
        "--game-root",
        type=Path,
        default=None,
        help="EU4 game root forwarded to the mod-owned validator when available",
    )
    args = parser.parse_args()

    mod = args.mod_path.expanduser().resolve()
    if not mod.exists():
        print(f"ERROR: mod path does not exist: {mod}", file=sys.stderr)
        return 2

    authoritative = mod / "tools" / "jxp_validation" / "run_validation.py"
    if authoritative.is_file():
        command = [
            sys.executable,
            str(authoritative),
            "--mod-root",
            str(mod),
        ]
        if args.game_root is not None:
            command.extend(["--game-root", str(args.game_root.expanduser().resolve())])
        print(
            "INFO: current JXP layout detected; delegating to the mod-owned "
            "authoritative validation suite."
        )
        return subprocess.run(command, check=False).returncode

    rows: list[str] = []
    issues: list[str] = []
    for section_func in (
        daimyo_report,
        idea_completeness_report,
        daimyo_idea_revision_report,
        early_daimyo_event_reward_report,
        preunification_memory_report,
        route_report,
        founder_reform_report,
        founder_legacy_council_report,
        route_house_compromise_report,
        route_house_resonance_report,
        founder_reform_pulse_report,
        major_founder_house_policy_report,
        founder_idea_legacy_report,
        daimyo_house_diet_report,
        house_diet_legacy_report,
        house_diet_mission_report,
        specific_route_house_combo_report,
        legacy_cabinet_report,
    ):
        section_rows, section_issues = section_func(mod)
        rows.extend(section_rows)
        rows.append("")
        issues.extend(section_issues)

    print("\n".join(rows).rstrip())
    if issues:
        print("\nCoverage issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(
        "\nOK: Japan Expanded daimyo, national idea/revision, early event reward, pre-unification memory, route/special-route reform, "
        "founder legacy council, route-house compromise, route-house resonance, "
        "founder reform pulse, major founder house policy, founder idea legacy, daimyo house diet, house diet legacy, house diet missions, "
        "specific route-house combo, and legacy cabinet consolidation coverage checks passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
