#!/usr/bin/env python3
"""Apply the reviewed 0.23.0 mission topology without changing mission IDs."""

from __future__ import annotations

from pathlib import Path
import re


Layout = tuple[int, tuple[str, ...]]
LAYOUT: dict[str, Layout] = {}


def node(mission_id: str, row: int, *required: str) -> None:
    if mission_id in LAYOUT:
        raise ValueError(f"duplicate layout entry: {mission_id}")
    LAYOUT[mission_id] = (row, tuple(required))


# Route-tag foundation: five outward branches converge on a new constitution.
node("jxp_mission_route_inherited_realm", 1)
node("jxp_mission_route_province_registers", 5, "jxp_mission_route_inherited_realm", "jxp_mission_route_settle_new_constitution")
node("jxp_mission_route_archipelago_circuit", 8, "jxp_mission_route_province_registers", "jxp_mission_route_firearm_offices", "jxp_mission_route_laws_of_the_new_realm")
node("jxp_mission_route_two_capitals", 2)
node("jxp_mission_route_rice_and_silver", 5, "jxp_mission_route_two_capitals", "jxp_mission_route_settle_new_constitution")
node("jxp_mission_route_post_station_ledger", 8, "jxp_mission_route_rice_and_silver", "jxp_mission_route_guard_the_sea_lanes", "jxp_mission_route_laws_of_the_new_realm")
node("jxp_mission_route_settle_new_constitution", 3, "jxp_mission_route_inherited_realm", "jxp_mission_route_two_capitals", "jxp_mission_route_muster_rolls", "jxp_mission_route_rites_of_the_isles")
node("jxp_mission_route_laws_of_the_new_realm", 6, "jxp_mission_route_province_registers", "jxp_mission_route_rice_and_silver", "jxp_mission_route_firearm_offices", "jxp_mission_route_guard_the_sea_lanes")
node("jxp_mission_route_renewed_japan", 9, "jxp_mission_route_laws_of_the_new_realm", "jxp_mission_route_archipelago_circuit", "jxp_mission_route_post_station_ledger")
node("jxp_mission_route_muster_rolls", 1)
node("jxp_mission_route_firearm_offices", 5, "jxp_mission_route_muster_rolls", "jxp_mission_route_settle_new_constitution")
node("jxp_mission_route_rites_of_the_isles", 2)
node("jxp_mission_route_guard_the_sea_lanes", 5, "jxp_mission_route_rites_of_the_isles", "jxp_mission_route_settle_new_constitution")

# Shared post-unification spine: two columns form a ladder of mutual support.
node("jxp_mission_secure_home_domain", 9)
node("jxp_mission_road_to_kyoto", 12, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_unite_the_isles", 15, "jxp_mission_road_to_kyoto", "jxp_mission_kyoto_and_edo")
node("jxp_mission_settle_the_realm", 18, "jxp_mission_unite_the_isles", "jxp_mission_iwami_silver")
node("jxp_mission_land_survey_state", 22, "jxp_mission_settle_the_realm", "jxp_mission_osaka_granary")
node("jxp_mission_modern_state", 26, "jxp_mission_land_survey_state", "jxp_mission_tanegashima_firearms")
node("jxp_mission_capital_cities", 9)
node("jxp_mission_kyoto_and_edo", 13, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_iwami_silver", 16, "jxp_mission_road_to_kyoto", "jxp_mission_kyoto_and_edo")
node("jxp_mission_osaka_granary", 19, "jxp_mission_unite_the_isles", "jxp_mission_iwami_silver")
node("jxp_mission_tanegashima_firearms", 23, "jxp_mission_settle_the_realm", "jxp_mission_osaka_granary")
node("jxp_mission_massed_volley", 27, "jxp_mission_land_survey_state", "jxp_mission_tanegashima_firearms")

# Daimyo stage: domain, contacts and one house archetype interleave below vanilla.
node("jxp_mission_daimyo_domain_accounts", 9)
node("jxp_mission_daimyo_castle_town", 12, "jxp_mission_daimyo_domain_accounts", "jxp_mission_daimyo_sakai_hakata_merchants")
node("jxp_mission_daimyo_clan_league", 16, "jxp_mission_daimyo_castle_town", "jxp_mission_daimyo_tanegashima_rumors")
node("jxp_mission_daimyo_petition_kyoto", 20, "jxp_mission_daimyo_clan_league", "jxp_mission_daimyo_foreign_letters")
node("jxp_mission_daimyo_path_to_kyoto", 23, "jxp_mission_daimyo_petition_kyoto", "jxp_mission_daimyo_foreign_letters")
node("jxp_mission_daimyo_sakai_hakata_merchants", 9)
node("jxp_mission_daimyo_tanegashima_rumors", 13, "jxp_mission_daimyo_domain_accounts", "jxp_mission_daimyo_sakai_hakata_merchants")
node("jxp_mission_daimyo_foreign_letters", 17, "jxp_mission_daimyo_castle_town", "jxp_mission_daimyo_tanegashima_rumors")

for first, second, third, root, bridge in (
    ("jxp_mission_house_warrior_muster", "jxp_mission_house_warrior_castle_roads", "jxp_mission_house_warrior_banner_legacy", "jxp_mission_daimyo_domain_accounts", "jxp_mission_daimyo_castle_town"),
    ("jxp_mission_house_court_genealogies", "jxp_mission_house_court_petitions", "jxp_mission_house_court_kanrei_memory", "jxp_mission_daimyo_domain_accounts", "jxp_mission_daimyo_castle_town"),
    ("jxp_mission_house_sea_port_registers", "jxp_mission_house_sea_shipwrights", "jxp_mission_house_sea_strait_laws", "jxp_mission_daimyo_sakai_hakata_merchants", "jxp_mission_daimyo_tanegashima_rumors"),
    ("jxp_mission_house_frontier_passes", "jxp_mission_house_frontier_markets", "jxp_mission_house_frontier_border_oaths", "jxp_mission_daimyo_domain_accounts", "jxp_mission_daimyo_castle_town"),
    ("jxp_mission_house_temple_ledgers", "jxp_mission_house_temple_market_towns", "jxp_mission_house_temple_public_law", "jxp_mission_daimyo_domain_accounts", "jxp_mission_daimyo_tanegashima_rumors"),
):
    node(first, 11, root)
    node(second, 15, first, bridge)
    node(third, 19, second, "jxp_mission_daimyo_clan_league", "jxp_mission_daimyo_foreign_letters")

# Shinto and rite branches used by JAP, CJP, EJP and WAK.
node("jxp_mission_shrine_land_registers", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_ise_pilgrim_roads", 15, "jxp_mission_shrine_land_registers", "jxp_mission_road_to_kyoto", "jxp_mission_kyoto_and_edo")
node("jxp_mission_kami_castle_towns", 18, "jxp_mission_shrine_land_registers", "jxp_mission_unite_the_isles", "jxp_mission_iwami_silver")
node("jxp_mission_incident_order", 22, "jxp_mission_ise_pilgrim_roads", "jxp_mission_kami_castle_towns", "jxp_mission_settle_the_realm")
node("jxp_mission_sacred_isles", 26, "jxp_mission_incident_order", "jxp_mission_land_survey_state", "jxp_mission_tanegashima_firearms")

node("jxp_mission_port_congregation_registers", 11, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_kana_doctrine", 15, "jxp_mission_port_congregation_registers", "jxp_mission_road_to_kyoto", "jxp_mission_kyoto_and_edo")
node("jxp_mission_church_court_compact", 19, "jxp_mission_port_congregation_registers", "jxp_mission_unite_the_isles", "jxp_mission_iwami_silver")
node("jxp_mission_martyrs_and_merchants", 23, "jxp_mission_kana_doctrine", "jxp_mission_church_court_compact", "jxp_mission_settle_the_realm", "jxp_mission_osaka_granary")
node("jxp_mission_cross_sun_commonwealth", 27, "jxp_mission_martyrs_and_merchants", "jxp_mission_land_survey_state", "jxp_mission_tanegashima_firearms")

node("jxp_mission_domain_school_exams", 11, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities", "jxp_mission_zhu_xi_lectures")
node("jxp_mission_ritual_census", 14, "jxp_mission_domain_school_exams", "jxp_mission_domain_schools")
node("jxp_mission_harmonize_kami_rites", 17, "jxp_mission_domain_school_exams", "jxp_mission_kyoto_rites")
node("jxp_mission_embassies_of_rite", 21, "jxp_mission_ritual_census", "jxp_mission_harmonize_kami_rites", "jxp_mission_merit_over_lineage")
node("jxp_mission_ordered_rite_state", 25, "jxp_mission_embassies_of_rite", "jxp_mission_korean_envoys")

node("jxp_mission_harbor_mosque_registers", 11, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities", "jxp_mission_malay_factory")
node("jxp_mission_qadi_port_courts", 15, "jxp_mission_harbor_mosque_registers", "jxp_mission_halal_port_law")
node("jxp_mission_south_sea_brokers", 19, "jxp_mission_harbor_mosque_registers", "jxp_mission_hajj_fleet")
node("jxp_mission_halal_granary_law", 23, "jxp_mission_qadi_port_courts", "jxp_mission_south_sea_brokers", "jxp_mission_melaka_interpreters")
node("jxp_mission_south_sea_maritime_law", 27, "jxp_mission_halal_granary_law", "jxp_mission_sultanate_of_wa")

node("jxp_mission_monto_rolls", 11, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities", "jxp_mission_terauchi_league")
node("jxp_mission_terauchi_market_charters", 15, "jxp_mission_monto_rolls", "jxp_mission_monto_muskets")
node("jxp_mission_village_militia_oaths", 17, "jxp_mission_monto_rolls", "jxp_mission_ishiyama_honganji")
node("jxp_mission_kinri_monto_compact", 22, "jxp_mission_terauchi_market_charters", "jxp_mission_village_militia_oaths", "jxp_mission_break_warrior_country")
node("jxp_mission_commonwealth_covenant", 26, "jxp_mission_kinri_monto_compact", "jxp_mission_guard_the_kinri")

# Sakoku and open-trade route braids.
node("jxp_mission_temple_registration", 11, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities", "jxp_mission_shrine_land_registers")
node("jxp_mission_expel_padres", 14, "jxp_mission_temple_registration", "jxp_mission_road_to_kyoto", "jxp_mission_kyoto_and_edo")
node("jxp_mission_closed_country_edicts", 17, "jxp_mission_expel_padres", "jxp_mission_ise_pilgrim_roads")
node("jxp_mission_dejima_window", 21, "jxp_mission_closed_country_edicts", "jxp_mission_kami_castle_towns")
node("jxp_mission_warrior_house_laws", 24, "jxp_mission_dejima_window", "jxp_mission_incident_order")
node("jxp_mission_genroku_prosperity", 28, "jxp_mission_warrior_house_laws", "jxp_mission_sacred_isles", "jxp_mission_massed_volley")
node("jxp_mission_repulse_foreign_ships", 32, "jxp_mission_genroku_prosperity", "jxp_mission_modern_state")

node("jxp_mission_open_nagasaki", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_nanban_factory", 14, "jxp_mission_open_nagasaki", "jxp_mission_road_to_kyoto", "jxp_mission_kyoto_and_edo")
node("jxp_mission_red_seal_ships", 18, "jxp_mission_nanban_factory", "jxp_mission_unite_the_isles", "jxp_mission_iwami_silver")
node("jxp_mission_translation_bureau", 22, "jxp_mission_red_seal_ships", "jxp_mission_settle_the_realm", "jxp_mission_osaka_granary")
node("jxp_mission_oceanic_shipyards", 26, "jxp_mission_translation_bureau", "jxp_mission_land_survey_state", "jxp_mission_tanegashima_firearms")
node("jxp_mission_manila_route", 30, "jxp_mission_oceanic_shipyards", "jxp_mission_eastasia_nagasaki_interpreters", "jxp_mission_pacific_manila_link")
node("jxp_mission_equal_treaties", 36, "jxp_mission_manila_route", "jxp_mission_eastasia_balance_mandate", "jxp_mission_pacific_north_charts")

# Open-trade outer wings. Their late nodes cross back through the central route.
node("jxp_mission_eastasia_ryukyu_gateway", 11, "jxp_mission_open_nagasaki")
node("jxp_mission_eastasia_korea_embassy", 15, "jxp_mission_eastasia_ryukyu_gateway", "jxp_mission_nanban_factory")
node("jxp_mission_eastasia_tsushima_office", 21, "jxp_mission_eastasia_korea_embassy", "jxp_mission_eastasia_tribute_registry")
node("jxp_mission_eastasia_liaodong_route", 19, "jxp_mission_eastasia_korea_embassy", "jxp_mission_red_seal_ships")
node("jxp_mission_eastasia_manchu_watch", 23, "jxp_mission_eastasia_liaodong_route", "jxp_mission_translation_bureau")
node("jxp_mission_eastasia_ming_trade", 16, "jxp_mission_eastasia_ryukyu_gateway", "jxp_mission_nanban_factory")
node("jxp_mission_eastasia_tribute_registry", 20, "jxp_mission_eastasia_ming_trade", "jxp_mission_red_seal_ships")
node("jxp_mission_eastasia_ryukyu_registry", 17, "jxp_mission_eastasia_ryukyu_gateway", "jxp_mission_eastasia_ming_trade")
node("jxp_mission_eastasia_nagasaki_interpreters", 24, "jxp_mission_eastasia_tribute_registry", "jxp_mission_translation_bureau")
node("jxp_mission_eastasia_taiwan_lanes", 25, "jxp_mission_eastasia_ryukyu_registry", "jxp_mission_eastasia_nagasaki_interpreters")
node("jxp_mission_eastasia_balance_mandate", 28, "jxp_mission_eastasia_manchu_watch", "jxp_mission_eastasia_nagasaki_interpreters", "jxp_mission_eastasia_taiwan_lanes", "jxp_mission_oceanic_shipyards")
node("jxp_mission_eastasia_claim_mandate", 31, "jxp_mission_eastasia_balance_mandate", "jxp_mission_manila_route")
node("jxp_mission_eastasia_break_mandate", 34, "jxp_mission_eastasia_balance_mandate", "jxp_mission_manila_route")
node("jxp_mission_eastasia_hegemon_of_the_seas", 37, "jxp_mission_eastasia_claim_mandate", "jxp_mission_eastasia_break_mandate", "jxp_mission_equal_treaties")
node("jxp_mission_eastasia_celestial_diplomacy", 41, "jxp_mission_eastasia_hegemon_of_the_seas")
node("jxp_mission_eastasia_littoral_entrepots", 43, "jxp_mission_eastasia_hegemon_of_the_seas", "jxp_mission_pacific_new_world_towns")
node("jxp_mission_eastasia_rite_sphere", 46, "jxp_mission_eastasia_celestial_diplomacy", "jxp_mission_eastasia_littoral_entrepots", "jxp_mission_pacific_oceanic_sun")

node("jxp_mission_pacific_charter", 12, "jxp_mission_open_nagasaki", "jxp_mission_eastasia_ryukyu_gateway")
node("jxp_mission_pacific_ogasawara_anchor", 17, "jxp_mission_pacific_charter", "jxp_mission_nanban_factory")
node("jxp_mission_pacific_guam_waystation", 21, "jxp_mission_pacific_ogasawara_anchor", "jxp_mission_red_seal_ships")
node("jxp_mission_pacific_admiralty", 27, "jxp_mission_pacific_charter", "jxp_mission_oceanic_shipyards")
node("jxp_mission_pacific_manila_link", 25, "jxp_mission_pacific_guam_waystation", "jxp_mission_translation_bureau")
node("jxp_mission_pacific_hawaii_soundings", 28, "jxp_mission_pacific_guam_waystation", "jxp_mission_oceanic_shipyards")
node("jxp_mission_pacific_north_charts", 32, "jxp_mission_pacific_hawaii_soundings", "jxp_mission_pacific_admiralty")
node("jxp_mission_pacific_alaska_posts", 35, "jxp_mission_pacific_hawaii_soundings", "jxp_mission_pacific_north_charts")
node("jxp_mission_pacific_california_harbors", 37, "jxp_mission_pacific_hawaii_soundings", "jxp_mission_pacific_north_charts")
node("jxp_mission_pacific_silver_current", 33, "jxp_mission_pacific_manila_link", "jxp_mission_pacific_admiralty")
node("jxp_mission_pacific_new_world_towns", 40, "jxp_mission_pacific_alaska_posts", "jxp_mission_pacific_california_harbors")
node("jxp_mission_pacific_oceanic_sun", 44, "jxp_mission_pacific_admiralty", "jxp_mission_pacific_silver_current", "jxp_mission_pacific_new_world_towns", "jxp_mission_equal_treaties")

# Christian Japan: Catholic and Reformed routes share the right-hand branch.
node("jxp_mission_welcome_missionaries", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_baptized_daimyo", 14, "jxp_mission_welcome_missionaries", "jxp_mission_port_congregation_registers")
node("jxp_mission_nagasaki_church_port", 17, "jxp_mission_baptized_daimyo", "jxp_mission_kana_doctrine")
node("jxp_mission_kyushu_seminary", 21, "jxp_mission_nagasaki_church_port", "jxp_mission_church_court_compact")
node("jxp_mission_tensho_embassy", 25, "jxp_mission_kyushu_seminary", "jxp_mission_martyrs_and_merchants")
node("jxp_mission_christian_sun", 29, "jxp_mission_tensho_embassy", "jxp_mission_cross_sun_commonwealth", "jxp_mission_roman_kyoto_embassy")
node("jxp_mission_shimabara_reconciliation", 33, "jxp_mission_christian_sun", "jxp_mission_shimabara_healed")
node("jxp_mission_kirishitan_settlement", 12, "jxp_mission_welcome_missionaries", "jxp_mission_port_congregation_registers")
node("jxp_mission_church_and_court", 16, "jxp_mission_kirishitan_settlement", "jxp_mission_baptized_daimyo", "jxp_mission_kana_doctrine")
node("jxp_mission_nagasaki_bishopric", 20, "jxp_mission_kirishitan_settlement", "jxp_mission_nagasaki_church_port", "jxp_mission_church_court_compact")
node("jxp_mission_roman_kyoto_embassy", 28, "jxp_mission_church_and_court", "jxp_mission_nagasaki_bishopric", "jxp_mission_tensho_embassy", "jxp_mission_cross_sun_commonwealth")
node("jxp_mission_shimabara_healed", 32, "jxp_mission_nagasaki_bishopric", "jxp_mission_christian_sun")
node("jxp_mission_oceanic_church_state", 36, "jxp_mission_roman_kyoto_embassy", "jxp_mission_shimabara_healed", "jxp_mission_shimabara_reconciliation")

node("jxp_mission_hirado_synod", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_oranda_scriptures", 14, "jxp_mission_hirado_synod", "jxp_mission_port_congregation_registers")
node("jxp_mission_court_covenant", 18, "jxp_mission_oranda_scriptures", "jxp_mission_kana_doctrine")
node("jxp_mission_oranda_ports", 22, "jxp_mission_court_covenant", "jxp_mission_church_court_compact")
node("jxp_mission_reformed_sun", 26, "jxp_mission_oranda_ports", "jxp_mission_martyrs_and_merchants")
node("jxp_mission_reformed_settlement", 12, "jxp_mission_hirado_synod", "jxp_mission_port_congregation_registers")
node("jxp_mission_consistory_registers", 16, "jxp_mission_reformed_settlement", "jxp_mission_oranda_scriptures", "jxp_mission_kana_doctrine")
node("jxp_mission_oranda_colleges", 20, "jxp_mission_reformed_settlement", "jxp_mission_court_covenant", "jxp_mission_church_court_compact")
node("jxp_mission_batavia_compacts", 24, "jxp_mission_oranda_colleges", "jxp_mission_oranda_ports", "jxp_mission_martyrs_and_merchants")
node("jxp_mission_reformed_volley", 29, "jxp_mission_consistory_registers", "jxp_mission_reformed_sun", "jxp_mission_cross_sun_commonwealth")
node("jxp_mission_covenant_commonwealth", 33, "jxp_mission_batavia_compacts", "jxp_mission_reformed_volley", "jxp_mission_reformed_sun")

# Confucian/imperial synthesis and its CJP institutional continuation.
node("jxp_mission_zhu_xi_lectures", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_domain_schools", 13, "jxp_mission_zhu_xi_lectures", "jxp_mission_shrine_land_registers")
node("jxp_mission_kyoto_rites", 16, "jxp_mission_domain_schools", "jxp_mission_ise_pilgrim_roads")
node("jxp_mission_merit_over_lineage", 20, "jxp_mission_kyoto_rites", "jxp_mission_kami_castle_towns")
node("jxp_mission_korean_envoys", 24, "jxp_mission_merit_over_lineage", "jxp_mission_incident_order")
node("jxp_mission_yamato_restoration", 28, "jxp_mission_korean_envoys", "jxp_mission_sacred_isles")
node("jxp_mission_ritual_state", 32, "jxp_mission_yamato_restoration", "jxp_mission_modern_state", "jxp_mission_massed_volley")
node("jxp_mission_osaka_rice_ledger", 29, "jxp_mission_settle_the_realm", "jxp_mission_ordered_rite_state", "jxp_mission_yamato_restoration")
node("jxp_mission_castle_town_markets", 33, "jxp_mission_osaka_rice_ledger", "jxp_mission_ritual_state")
node("jxp_mission_domain_school_network", 36, "jxp_mission_osaka_rice_ledger", "jxp_mission_castle_town_markets")
node("jxp_mission_nagasaki_translation_house", 39, "jxp_mission_castle_town_markets", "jxp_mission_domain_school_network")
node("jxp_mission_silver_silk_routing", 42, "jxp_mission_domain_school_network", "jxp_mission_nagasaki_translation_house")
node("jxp_mission_three_capitals_ledgers", 45, "jxp_mission_silver_silk_routing")

# Kaikyo Japan.
node("jxp_mission_malay_factory", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_halal_port_law", 14, "jxp_mission_malay_factory", "jxp_mission_harbor_mosque_registers")
node("jxp_mission_hajj_fleet", 18, "jxp_mission_halal_port_law", "jxp_mission_qadi_port_courts")
node("jxp_mission_melaka_interpreters", 22, "jxp_mission_hajj_fleet", "jxp_mission_south_sea_brokers")
node("jxp_mission_sultanate_of_wa", 26, "jxp_mission_melaka_interpreters", "jxp_mission_halal_granary_law")
node("jxp_mission_kaikyo_settlement", 12, "jxp_mission_malay_factory", "jxp_mission_harbor_mosque_registers")
node("jxp_mission_qadi_courts", 16, "jxp_mission_kaikyo_settlement", "jxp_mission_halal_port_law", "jxp_mission_qadi_port_courts")
node("jxp_mission_sakai_malay_brokers", 20, "jxp_mission_kaikyo_settlement", "jxp_mission_hajj_fleet", "jxp_mission_south_sea_brokers")
node("jxp_mission_hajj_registry", 24, "jxp_mission_qadi_courts", "jxp_mission_halal_granary_law")
node("jxp_mission_south_sea_compact", 29, "jxp_mission_sakai_malay_brokers", "jxp_mission_sultanate_of_wa", "jxp_mission_south_sea_maritime_law")
node("jxp_mission_sultanate_sea_law", 33, "jxp_mission_hajj_registry", "jxp_mission_south_sea_compact", "jxp_mission_sultanate_of_wa")

# Ikko and Wokou routes.
node("jxp_mission_terauchi_league", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_monto_muskets", 14, "jxp_mission_terauchi_league", "jxp_mission_monto_rolls")
node("jxp_mission_ishiyama_honganji", 16, "jxp_mission_terauchi_league", "jxp_mission_terauchi_market_charters")
node("jxp_mission_break_warrior_country", 20, "jxp_mission_monto_muskets", "jxp_mission_ishiyama_honganji", "jxp_mission_village_militia_oaths")
node("jxp_mission_guard_the_kinri", 23, "jxp_mission_ishiyama_honganji", "jxp_mission_break_warrior_country")
node("jxp_mission_peasant_commonwealth", 27, "jxp_mission_break_warrior_country", "jxp_mission_guard_the_kinri", "jxp_mission_commonwealth_covenant")
node("jxp_mission_pure_land_covenant", 31, "jxp_mission_peasant_commonwealth", "jxp_mission_modern_state", "jxp_mission_massed_volley")

node("jxp_mission_fund_wokou", 10, "jxp_mission_secure_home_domain", "jxp_mission_capital_cities")
node("jxp_mission_setouchi_suigun", 14, "jxp_mission_fund_wokou", "jxp_mission_shrine_land_registers")
node("jxp_mission_tsushima_brokers", 16, "jxp_mission_fund_wokou", "jxp_mission_ise_pilgrim_roads")
node("jxp_mission_ryukyu_sea_gate", 19, "jxp_mission_tsushima_brokers", "jxp_mission_kami_castle_towns")
node("jxp_mission_ming_sea_smugglers", 23, "jxp_mission_setouchi_suigun", "jxp_mission_ryukyu_sea_gate", "jxp_mission_incident_order")
node("jxp_mission_wokou_admiralty", 27, "jxp_mission_ming_sea_smugglers", "jxp_mission_sacred_isles")
node("jxp_mission_lords_of_eastern_sea", 35, "jxp_mission_wokou_admiralty", "jxp_mission_northern_sea_office", "jxp_mission_matsumae_treaties")
node("jxp_mission_northern_sea_office", 29, "jxp_mission_wokou_admiralty", "jxp_mission_modern_state", "jxp_mission_massed_volley")
node("jxp_mission_matsumae_treaties", 32, "jxp_mission_northern_sea_office")
node("jxp_mission_coastal_beacon_chain", 33, "jxp_mission_northern_sea_office", "jxp_mission_matsumae_treaties")
node("jxp_mission_tsushima_interpreters", 36, "jxp_mission_coastal_beacon_chain", "jxp_mission_lords_of_eastern_sea")
node("jxp_mission_ryukyu_embassy_records", 39, "jxp_mission_tsushima_interpreters")
node("jxp_mission_east_sea_protocol", 42, "jxp_mission_matsumae_treaties", "jxp_mission_ryukyu_embassy_records")

# House law becomes a parallel late-game branch for every unified route.
node("jxp_mission_house_diet_into_realm", 30, "jxp_mission_modern_state", "jxp_mission_massed_volley")
node("jxp_mission_house_law_local_offices", 34, "jxp_mission_house_diet_into_realm")
node("jxp_mission_house_law_state_doctrine", 38, "jxp_mission_house_law_local_offices")


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    in_comment = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_comment:
            if char in "\r\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"unclosed block at offset {opening}")


def update_mission(text: str, mission_id: str, row: int, required: tuple[str, ...]) -> str:
    pattern = re.compile(rf"(?m)^[ \t]+{re.escape(mission_id)}[ \t]*=[ \t]*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"expected one definition of {mission_id}, found {len(matches)}")
    opening = text.find("{", matches[0].start(), matches[0].end())
    closing = matching_brace(text, opening)
    block = text[matches[0].start():closing + 1]

    position_pattern = re.compile(r"(?m)^\t\tposition[ \t]*=[ \t]*\d+[ \t]*(?=\r?$)")
    if len(position_pattern.findall(block)) != 1:
        raise ValueError(f"expected one position field in {mission_id}")
    block = position_pattern.sub(f"\t\tposition = {row}", block, count=1)

    required_pattern = re.compile(r"(?m)^\t\trequired_missions[ \t]*=[ \t]*\{")
    required_matches = list(required_pattern.finditer(block))
    if len(required_matches) != 1:
        raise ValueError(f"expected one required_missions field in {mission_id}")
    required_open = block.find("{", required_matches[0].start(), required_matches[0].end())
    required_close = matching_brace(block, required_open)
    dependency_text = " ".join(required)
    replacement = f"\t\trequired_missions = {{ {dependency_text} }}"
    block = block[:required_matches[0].start()] + replacement + block[required_close + 1:]
    return text[:matches[0].start()] + block + text[closing + 1:]


def main() -> int:
    mod_root = Path(__file__).resolve().parents[2]
    mission_files = sorted((mod_root / "missions").glob("*.txt"))
    texts: dict[Path, str] = {}
    for path in mission_files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            texts[path] = handle.read()

    definitions: dict[str, Path] = {}
    for mission_id in LAYOUT:
        assignment = re.compile(rf"(?m)^[ \t]+{re.escape(mission_id)}[ \t]*=[ \t]*\{{")
        owners = [path for path, text in texts.items() if assignment.search(text)]
        if len(owners) != 1:
            raise ValueError(f"expected one source file for {mission_id}, found {len(owners)}")
        definitions[mission_id] = owners[0]

    for mission_id, (row, required) in LAYOUT.items():
        owner = definitions[mission_id]
        texts[owner] = update_mission(texts[owner], mission_id, row, required)

    for path, text in texts.items():
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    print(f"Reflowed {len(LAYOUT)} missions across {len(mission_files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
