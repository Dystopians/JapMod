#!/usr/bin/env python3
"""Build the isolated Agent A Buddhist-Japan route slice.

This module is the authoritative source for the A11 route.  Runtime files are
generated so mission topology, sect-seat limits, crisis coverage, private
state, and Chinese localisation remain deterministic.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
MAIN_ROOT = SCRIPT_DIR.parents[1]
REPO_ROOT = MAIN_ROOT.parent
ESCAPE_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "eu4-modding"
    / "scripts"
    / "escape_eu4_special_localisation.py"
)
B115_BUILDER = (
    MAIN_ROOT
    / "tools"
    / "jxp_b_external_route_builder"
    / "build_external_routes.py"
)

ROUTE_FLAG = "jxp_path_buddhist"
INTERFACE_FLAG = "jxp_iface_buddhist_diplomacy_ready"
DYNAMIC_NAME = "JXP_BUDDHIST_JAPAN_STRING"
SEAT_VARIABLE = "jxp_a_buddhist_seat_count"
RUNTIME_MISSION_SLOTS = (4, 5)
OTHER_ROUTE_FLAGS = (
    "jxp_path_sakoku",
    "jxp_path_open_trade",
    "jxp_path_kirishitan",
    "jxp_path_confucian",
    "jxp_path_imperial",
    "jxp_path_reformed",
    "jxp_path_kaikyo",
    "jxp_path_ikko",
    "jxp_path_wokou",
)


@dataclass(frozen=True)
class Mission:
    key: str
    title: str
    description: str
    slot: int
    position: int
    icon: str
    trigger: tuple[str, ...]
    effect: tuple[str, ...]

    @property
    def mission_id(self) -> str:
        return f"jxp_a_buddhist_{self.key}"


@dataclass(frozen=True)
class Seat:
    key: str
    title: str
    benefit: str
    cost: str
    modifiers: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Finale:
    key: str
    title: str
    description: str
    icon: str
    modifiers: tuple[tuple[str, str], ...]

    @property
    def reform_id(self) -> str:
        return f"jxp_a_96_buddhist_{self.key}_reform"


@dataclass(frozen=True)
class Crisis:
    event_id: int
    title: str
    description: str
    trigger: tuple[str, ...]
    first_title: str
    first_effect: tuple[str, ...]
    second_title: str
    second_effect: tuple[str, ...]


def _mission(
    key: str,
    title: str,
    description: str,
    slot: int,
    position: int,
    icon: str,
    trigger: Iterable[str],
    effect: Iterable[str],
) -> Mission:
    return Mission(
        key,
        title,
        description,
        slot,
        position,
        icon,
        tuple(trigger),
        tuple(effect),
    )


MISSIONS = (
    _mission("nanto_garan", "南都伽蓝", "以朝廷名义保护南都寺院，并把修复责任写入国家簿册。", 1, 1, "mission_religious", ("owns = 1020", "stability = 0"), ("add_prestige = 10", "add_adm_power = 25")),
    _mission("hieizan_guarantee", "比叡山安堵", "确认山门领地与护持义务，使大寺院的权利同时受到国家约束。", 1, 3, "mission_to_japan", ("num_of_owned_provinces_with = { value = 4 OR = { has_building = temple has_building = cathedral } }", "prestige = 10"), ("add_adm_power = 40", "add_country_modifier = { name = jxp_a_buddhist_sanctuary_guarantees duration = 3650 }")),
    _mission("koyasan_pilgrimage", "高野山参诣", "把参诣、宿坊与道路保护纳入公仪，使圣地不再依赖临时施舍。", 1, 5, "mission_religious", ("treasury = 200", "adm_power = 75"), ("add_prestige = 15", "add_legitimacy = 5")),
    _mission("kyoto_temple_restoration", "京都诸寺修复", "以统一后的财赋修复京都诸寺，同时编定工程与寺领的责任边界。", 1, 7, "mission_have_manufactories", ("owns = 1020", "total_development = 200", "treasury = 300"), ("add_adm_power = 50", "add_country_modifier = { name = jxp_a_buddhist_capital_temples duration = 7300 }")),
    _mission("gozan_register", "五山名籍", "重订五山名籍与住持履历，让学问、外交和任官都可受国家稽核。", 1, 9, "mission_early_modern_university", ("adm_tech = 9", "num_of_cities = 15", "prestige = 25"), ("add_dip_power = 40", "add_country_modifier = { name = jxp_a_buddhist_gozan_register duration = 7300 }")),
    _mission("shinbutsu_compact", "神佛习合之议", "以成文国制划定神祇礼仪与佛教寺院的共同空间，而非强迫全国一夜改宗。", 1, 11, "mission_monarch_in_throne_room", ("stability = 2", "OR = { NOT = { religion = shinto } has_country_flag = jxp_a_buddhist_shinbutsu_prepared }"), ("add_country_modifier = { name = jxp_a_buddhist_shinbutsu_compact duration = -1 }", "add_prestige = 15")),

    _mission("temple_magistrate", "寺社奉行", "设置专责奉行，审理寺社诉讼、住持任命与公仪命令。", 2, 2, "mission_monarch_in_throne_room", ("legitimacy = 50", "adm_power = 100"), ("add_adm_power = 50", "add_country_modifier = { name = jxp_a_buddhist_temple_magistracy duration = -1 }")),
    _mission("temple_land_survey", "寺领检地", "把寺领田畠、坊舍与佃户纳入统一检地，同时承认确有凭据的旧权利。", 2, 4, "mission_rice_field", ("adm_tech = 8", "num_of_owned_provinces_with = { value = 8 OR = { has_building = temple has_building = cathedral } }"), ("add_adm_power = 40", "change_government_reform_progress = 10")),
    _mission("tax_exempt_register", "免税地名簿", "刊定免税地名簿，阻止寺院与武家借宗教名义隐匿新田。", 2, 6, "mission_rice_field", ("treasury = 500", "NOT = { inflation = 5 }"), ("add_adm_power = 50", "add_country_modifier = { name = jxp_a_buddhist_exemption_ledger duration = 7300 }")),
    _mission("warrior_monk_service", "僧兵军役", "把僧兵护院义务改为受限军役，不让寺院武力成为无主的私兵。", 2, 8, "mission_japanese_samurai", ("army_size_percentage = 0.75", "army_tradition = 20"), ("add_mil_power = 50", "add_army_tradition = 5")),
    _mission("kanjin_public_works", "勧进与普请", "把勧进从临时募缘转为可核销的桥梁、堤防与寺院普请制度。", 2, 10, "mission_have_manufactories", ("total_development = 300", "num_of_owned_provinces_with = { value = 15 OR = { has_building = temple has_building = workshop has_building = counting_house } }"), ("add_adm_power = 40", "add_country_modifier = { name = jxp_a_buddhist_public_works duration = 7300 }")),
    _mission("royal_buddhist_law", "王法与佛法", "以王法统辖财政、军役和裁判，以佛法为护国与施济提供合法性。", 2, 12, "mission_monarch_in_throne_room", ("stability = 2", "legitimacy = 70", "mission_completed = jxp_a_buddhist_shinbutsu_compact"), ("change_government_reform_progress = 25", "add_country_modifier = { name = jxp_a_buddhist_royal_law duration = -1 }")),

    _mission("convene_sect_council", "召开诸宗评议", "召集五类宗派代表，先议职责与代价，再决定正式席位。", 3, 1, "mission_monarch_in_throne_room", ("stability = 1", "mission_completed = jxp_a_buddhist_nanto_garan", "mission_completed = jxp_a_buddhist_temple_magistrate"), ("add_prestige = 10", "set_country_flag = jxp_a_buddhist_council_opened")),
    _mission("tendai_shingon_seat", "天台真言席", "审议天台、真言的护国仪礼与大寺院土地要求。", 3, 3, "mission_religious", ("prestige = 30",), ("country_event = { id = jxp_buddhist_state.100 }",)),
    _mission("zen_gozan_seat", "禅林五山席", "审议禅林五山的文书、顾问与海外僧侣网络，以及其精英化代价。", 3, 5, "mission_early_modern_university", ("dip_power = 100",), ("country_event = { id = jxp_buddhist_state.101 }",)),
    _mission("jodo_shinshu_seat", "净土真宗席", "审议净土、净土真宗的讲众施济与乡村动员，同时处理自治和武装化风险。", 3, 7, "mission_religious", ("religious_unity = 0.8",), ("country_event = { id = jxp_buddhist_state.102 }",)),
    _mission("lotus_seat", "法华宗席", "审议法华宗的町众、商业和民兵网络，并约束排他性冲突。", 3, 9, "mission_high_income", ("num_of_cities = 20",), ("country_event = { id = jxp_buddhist_state.103 }",)),
    _mission("nanto_old_seat", "南都旧宗席", "审议南都旧宗的朝廷礼仪、学问与奈良经济，以及旧寺领特权。", 3, 11, "mission_to_japan", ("owns = 1020", "legitimacy = 60"), ("country_event = { id = jxp_buddhist_state.104 }",)),
    _mission("sectarian_accord", "诸宗和议", "三席既定后，以公开条款安排其余宗派的宽容、限制与申诉渠道。", 3, 13, "mission_monarch_in_throne_room", ("check_variable = { which = jxp_a_buddhist_seat_count value = 3 }", "stability = 2"), ("add_country_modifier = { name = jxp_a_buddhist_three_seat_accord duration = -1 }", "change_government_reform_progress = 25")),

    _mission("woodblocks_scriptures", "版木与经卷", "组织版木、校勘与经卷流通，使寺院学问不再受单一山门垄断。", 4, 2, "mission_early_modern_university", ("OR = { adm_tech = 9 has_institution = printing_press }",), ("add_adm_power = 40", "add_country_modifier = { name = jxp_a_buddhist_printing_houses duration = 7300 }")),
    _mission("monastic_schools", "学寮与寺子教育", "以学寮培养僧侣文书官，并让寺子教育进入城镇与村落。", 4, 4, "mission_early_modern_university", ("total_development = 250", "num_of_owned_provinces_with = { value = 8 OR = { has_building = temple has_building = cathedral } }"), ("add_adm_power = 50", "add_country_modifier = { name = jxp_a_buddhist_school_network duration = 7300 }")),
    _mission("medicine_halls", "施药院", "把施药院、药材供给与行旅救护纳入寺社奉行的账册。", 4, 6, "mission_high_income", ("treasury = 400", "num_of_cities = 15"), ("add_prestige = 10", "add_country_modifier = { name = jxp_a_buddhist_relief_network duration = 7300 }")),
    _mission("charity_granaries", "义仓与饥馑救济", "由国家、寺院和町众共同充实义仓，在饥馑时按簿册放粮。", 4, 8, "mission_rice_field", ("stability = 1", "treasury = 600", "num_of_cities = 20"), ("add_adm_power = 40", "add_country_modifier = { name = jxp_a_buddhist_relief_network duration = -1 }")),
    _mission("pilgrimage_roads", "参诣道路", "修复通往诸山的参诣道路，并以宿站保护僧侣、商旅和普通信众。", 4, 10, "mission_to_japan", ("adm_tech = 10", "num_of_owned_provinces_with = { value = 12 OR = { has_building = temple has_building = workshop } }"), ("add_dip_power = 40", "add_country_modifier = { name = jxp_a_buddhist_pilgrimage_circuit duration = 7300 }")),
    _mission("clerical_scribes", "僧侣文书官", "以受训僧侣承担外交文书、地方档案与经卷翻译，同时接受公仪考成。", 4, 12, "mission_early_modern_university", ("adm_power = 150", "dip_power = 150"), ("add_adm_power = 50", "add_dip_power = 50")),
    _mission("town_temple_credit", "町众与寺院信用", "整顿寺院借贷与町众信用，限制借宗教权威规避债务的行为。", 4, 14, "mission_high_income", ("treasury = 1000", "NOT = { inflation = 5 }", "stability = 1"), ("add_country_modifier = { name = jxp_a_buddhist_temple_credit duration = -1 }", "add_dip_power = 50")),

    _mission("korean_scriptures", "朝鲜经卷", "通过朝鲜寺院与使节取得经卷、印刷法和校勘传统。", 5, 1, "mission_to_japan", ("OR = { any_known_country = { capital_scope = { region = korea_region } } any_owned_province = { region = korea_region } }",), ("add_dip_power = 40", "add_prestige = 10")),
    _mission("chinese_monks", "中华僧侣往来", "恢复与中国寺院和僧侣的文书往来，以学问交流取代单纯朝贡模仿。", 5, 3, "mission_to_japan", ("OR = { any_known_country = { capital_scope = { OR = { region = north_china_region region = south_china_region } } } any_owned_province = { OR = { region = north_china_region region = south_china_region } } }",), ("add_dip_power = 50", "add_country_modifier = { name = jxp_a_buddhist_diplomatic_cloisters duration = 7300 }")),
    _mission("ryukyu_dharma_lamp", "琉球法灯", "以琉球为海路节点，让法灯、经卷和医药知识跨越岛链。", 5, 5, "mission_trade_with_japan", ("OR = { owns = 1015 any_known_country = { owns = 1015 } }", "num_of_ports = 5"), ("add_dip_power = 40", "add_navy_tradition = 5")),
    _mission("south_seas_temples", "南海佛寺网络", "为南海航路上的佛寺、商人和译僧建立互保文书。", 5, 7, "mission_trade_company_region_abroad", ("num_of_ports = 8", "jxp_oceanic_opening_at_least_25 = yes"), ("add_dip_power = 50", "add_country_modifier = { name = jxp_a_buddhist_diplomatic_cloisters duration = -1 }")),
    _mission("four_seas_dharma", "四海法灯", "使朝鲜、中国、琉球与南海的佛教交往形成稳定而非征服性的外交网络。", 5, 9, "mission_establish_high_seas_navy", ("num_of_ports = 10", "dip_tech = 12", "jxp_oceanic_opening_at_least_50 = yes"), ("jxp_a_mark_buddhist_diplomacy_ready_effect = yes", "add_dip_power = 75")),
    _mission("buddhist_constitution", "佛国之宪", "在三席和议、王法佛法、施济教育与四海法灯之间选择国家的最终制度。", 5, 11, "mission_monarch_in_throne_room", ("mission_completed = jxp_a_buddhist_sectarian_accord", "mission_completed = jxp_a_buddhist_royal_buddhist_law", "mission_completed = jxp_a_buddhist_town_temple_credit", f"has_country_flag = {INTERFACE_FLAG}", "stability = 2"), ("country_event = { id = jxp_buddhist_state.200 }",)),
)


SEATS = (
    Seat("tendai_shingon", "天台／真言席", "护国仪礼、圣地网络与传教能力", "大寺院土地要求压低国家税收", (("global_missionary_strength", "0.01"), ("prestige", "0.5"), ("global_tax_modifier", "-0.03"))),
    Seat("zen_gozan", "禅林／五山席", "顾问、文书、学术与东亚外交", "精英化使乡村人力动员减弱", (("advisor_cost", "-0.05"), ("diplomatic_reputation", "1"), ("global_manpower_modifier", "-0.05"))),
    Seat("jodo_shinshu", "净土／净土真宗席", "民众动员、施济与乡村稳定", "讲众自治削弱中央税收", (("global_unrest", "-1"), ("global_manpower_modifier", "0.10"), ("global_tax_modifier", "-0.05"))),
    Seat("lotus", "法华宗席", "町众商业、热忱与民兵组织", "排他性降低对异端宗派的宽容", (("trade_efficiency", "0.10"), ("manpower_recovery_speed", "0.05"), ("tolerance_heretic", "-1"))),
    Seat("nanto_old", "南都旧宗席", "朝廷礼仪、法统、学问与畿内经济", "保守寺领提高建设成本", (("legitimacy", "1"), ("idea_cost", "-0.03"), ("build_cost", "0.05"))),
)


FINALES = (
    Finale("mutual_law", "王法佛法相依体制", "国家直接组织护国寺院，换取强大统合力，也承担寺社反弹。", "asian_scripture", (("governing_capacity_modifier", "0.10"), ("global_missionary_strength", "0.02"), ("global_unrest", "1"))),
    Finale("mountain_council", "诸山公议国制", "多宗派会议主导教育与外交，代价是中央财赋让步。", "ballot_box", (("tolerance_heretic", "2"), ("diplomatic_reputation", "1"), ("advisor_cost", "-0.05"), ("global_tax_modifier", "-0.05"))),
    Finale("clerical_temporal", "僧俗分治法度", "国家掌财政军司法，宗派保有限自治；制度稳定但直接传教较弱。", "crown", (("governing_capacity_modifier", "0.10"), ("stability_cost_modifier", "-0.10"), ("global_missionary_strength", "-0.01"))),
)


CRISES = (
    Crisis(10, "寺领检地危机", "检地役人要求丈量寺领，诸山则援引旧朱印与施主文书。", ("mission_completed = jxp_a_buddhist_temple_land_survey",), "坚持逐笔检地", ("add_adm_power = -50", "change_government_reform_progress = 15", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }"), "承认凭据并议定折衷", ("add_treasury = -150", "add_stability = 1", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }")),
    Crisis(11, "僧兵拒绝解散", "部分僧兵拒绝交械，声称护院之责不能交给远方奉行。", ("mission_completed = jxp_a_buddhist_warrior_monk_service",), "编入受限护院军役", ("add_mil_power = -50", "add_army_tradition = 5", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }"), "以寺领负担换取裁军", ("add_treasury = -150", "add_legitimacy = -5", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }")),
    Crisis(12, "法华与净土冲突", "町众讲席与乡村讲众争夺布教、救济和市场空间。", ("has_country_flag = jxp_a_buddhist_seat_lotus_recognized", "has_country_flag = jxp_a_buddhist_seat_jodo_shinshu_recognized"), "由诸宗评议调停", ("add_dip_power = -50", "add_prestige = 10", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "划定各自讲席范围", ("add_adm_power = -50", "add_stability = -1", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
    Crisis(13, "大寺院与地方坊舍竞争", "名山本寺要求统辖地方坊舍，地方僧团则要求保留施济与会计自主。", ("check_variable = { which = jxp_a_buddhist_seat_count value = 2 }",), "保护地方坊舍申诉权", ("add_dip_power = -50", "add_legitimacy = 5", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "确认本寺层级责任", ("add_adm_power = -50", "change_government_reform_progress = 10", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
    Crisis(14, "国家任命住持", "寺社奉行提出审核住持任命，诸山担心法脉被政治恩赏取代。", ("mission_completed = jxp_a_buddhist_temple_magistrate",), "保留推举、国家核准", ("add_dip_power = -50", "add_prestige = 10", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "由国家直接任命", ("add_adm_power = -50", "add_legitimacy = 10", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
    Crisis(15, "经卷版本争议", "各寺版木在章句和校勘上互不相让，学寮要求建立共同底本。", ("mission_completed = jxp_a_buddhist_woodblocks_scriptures",), "资助诸本对校", ("add_treasury = -150", "add_adm_power = 25", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "颁行公仪校本", ("add_adm_power = -50", "add_prestige = 10", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
    Crisis(16, "神佛习合与排佛倾向", "部分武家要求切断神社与寺院旧有联系，另一些人主张维持习合秩序。", ("OR = { religion = shinto has_country_flag = jxp_a_buddhist_shinbutsu_prepared }",), "维护成文习合国制", ("add_dip_power = -50", "add_stability = 1", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "统一公仪礼次", ("add_adm_power = -50", "add_prestige = 15", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
    Crisis(17, "净土真宗自治危机", "讲众要求自行管理义仓与寺内町，奉行担心形成不受裁判的权力。", ("has_country_flag = jxp_a_buddhist_seat_jodo_shinshu_recognized",), "以章程承认有限自治", ("add_legitimacy = -5", "add_stability = 1", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "把义仓纳入奉行账册", ("add_adm_power = -50", "change_government_reform_progress = 10", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
    Crisis(18, "町众支持某宗派", "城镇会所公开资助一宗讲席，引发其他寺院对市场偏袒的控诉。", ("OR = { has_country_flag = jxp_a_buddhist_seat_lotus_recognized has_country_flag = jxp_a_buddhist_seat_zen_gozan_recognized }",), "公开会计并允许多宗捐助", ("add_dip_power = -50", "add_prestige = 10", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "禁止宗派控制町会", ("add_adm_power = -50", "add_treasury = 100", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
    Crisis(19, "寺院债务和德政", "寺院债券、町众借款与饥年欠租交织，债务人要求施行德政。", ("mission_completed = jxp_a_buddhist_town_temple_credit",), "由义仓分担并减记债务", ("add_treasury = -200", "add_stability = 1", "add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 }"), "维护契约并分期清偿", ("add_adm_power = -50", "add_treasury = 150", "add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 }")),
)


def _load_escape_module():
    spec = importlib.util.spec_from_file_location("jxp_escape_localisation", ESCAPE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical EU4SpecialEscape converter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_b115_builder():
    spec = importlib.util.spec_from_file_location("jxp_b_external_route_builder", B115_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the B115 external-route overlay builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_design() -> None:
    if len(MISSIONS) != 32:
        raise ValueError(f"expected 32 missions, found {len(MISSIONS)}")
    if len({mission.mission_id for mission in MISSIONS}) != 32:
        raise ValueError("duplicate Buddhist mission id")
    expected_counts = {1: 6, 2: 6, 3: 7, 4: 7, 5: 6}
    counts = {slot: sum(mission.slot == slot for mission in MISSIONS) for slot in range(1, 6)}
    if counts != expected_counts:
        raise ValueError(f"unexpected five-column mission counts: {counts}")
    for slot in range(1, 6):
        rows = [mission.position for mission in MISSIONS if mission.slot == slot]
        if rows != sorted(rows) or len(rows) != len(set(rows)):
            raise ValueError(f"slot {slot} is not source-monotonic")
        parity = 1 if slot in {1, 3, 5} else 0
        if any(row % 2 != parity for row in rows):
            raise ValueError(f"slot {slot} violates canonical parity")
        if any(right - left != 2 for left, right in zip(rows, rows[1:])):
            raise ValueError(f"slot {slot} has a noncanonical vertical gap")
    if len(SEATS) != 5 or len(FINALES) != 3 or len(CRISES) != 10:
        raise ValueError("seat/finale/crisis cardinality drift")
    for seat in SEATS:
        values = [float(value) for _, value in seat.modifiers]
        if not any(value > 0 for value in values) or not any(value < 0 for value in values):
            raise ValueError(f"seat {seat.key} must carry a benefit and a cost")


def _indent(lines: Iterable[str], level: int) -> list[str]:
    prefix = "\t" * level
    output: list[str] = []
    for line in lines:
        output.extend(prefix + part if part else "" for part in line.splitlines())
    return output


def render_triggers() -> str:
    other = " ".join(f"has_country_flag = {flag}" for flag in OTHER_ROUTE_FLAGS)
    return f"""# Generated by jxp_a_96_buddhist_builder.py. Do not edit.
jxp_a_96_buddhist_exact_route_trigger = {{
\ttag = JAP
\thas_country_flag = {ROUTE_FLAG}
\tNOT = {{ OR = {{ {other} }} }}
}}

jxp_a_96_can_enter_buddhist_route_trigger = {{
\ttag = JAP
\tjxp_is_unified_japan_state_trigger = yes
\tNOT = {{ has_country_flag = {ROUTE_FLAG} }}
\tNOT = {{ OR = {{ {other} }} }}
\towns = 1020
\tOR = {{
\t\treligion = buddhism
\t\treligion = vajrayana
\t\treligion = mahayana
\t\treligion = jodo_shinshu
\t\tAND = {{
\t\t\treligion = shinto
\t\t\thas_country_flag = jxp_a_buddhist_shinbutsu_prepared
\t\t\tnum_of_owned_provinces_with = {{
\t\t\t\tvalue = 10
\t\t\t\tOR = {{ has_building = temple has_building = cathedral }}
\t\t\t}}
\t\t}}
\t}}
}}
"""


def _potential() -> list[str]:
    lines = [
        "NOT = { map_setup = map_setup_random }",
        "tag = JAP",
        f"has_country_flag = {ROUTE_FLAG}",
        "NOT = {",
        "\tOR = {",
    ]
    lines.extend(f"\t\thas_country_flag = {flag}" for flag in OTHER_ROUTE_FLAGS)
    lines.extend(("\t}", "}"))
    return lines


def render_missions() -> str:
    lines = ["# Generated by jxp_a_96_buddhist_builder.py. Do not edit."]
    # The socioeconomic reconstruction owns the unified domestic columns
    # (slots 1-3). Keep this builder authoritative for the frozen Buddhist
    # learning/diplomacy columns only, instead of emitting superseded series
    # and relying on a second generator to strip them afterwards.
    for slot in RUNTIME_MISSION_SLOTS:
        series = [mission for mission in MISSIONS if mission.slot == slot]
        lines.extend(
            (
                f"jxp_a_96_buddhist_slot_{slot}_missions = {{",
                f"\tslot = {slot}",
                "\tgeneric = no",
                "\tai = yes",
                "\tpotential = {",
                *_indent(_potential(), 2),
                "\t}",
                "\thas_country_shield = yes",
                "",
            )
        )
        previous: Mission | None = None
        for mission in series:
            lines.extend(
                (
                    f"\t{mission.mission_id} = {{",
                    f"\t\ticon = {mission.icon}",
                    f"\t\tposition = {mission.position}",
                )
            )
            if previous is not None:
                lines.append(f"\t\trequired_missions = {{ {previous.mission_id} }}")
            lines.extend(("\t\ttrigger = {", *_indent(mission.trigger, 3), "\t\t}", "\t\teffect = {", *_indent(mission.effect, 3), "\t\t}", "\t}", ""))
            previous = mission
        lines.extend(("}", ""))
    return "\n".join(lines)


def render_modifiers() -> str:
    definitions: list[tuple[str, tuple[tuple[str, str], ...]]] = [
        ("jxp_a_buddhist_shinbutsu_preparation", (("stability_cost_modifier", "-0.05"), ("tolerance_heretic", "1"))),
        ("jxp_a_buddhist_route_constitution", (("stability_cost_modifier", "-0.05"), ("tolerance_heretic", "1"))),
        ("jxp_a_buddhist_sanctuary_guarantees", (("prestige_decay", "-0.01"), ("state_maintenance_modifier", "0.05"))),
        ("jxp_a_buddhist_capital_temples", (("development_cost", "-0.05"), ("build_cost", "-0.05"))),
        ("jxp_a_buddhist_gozan_register", (("advisor_cost", "-0.05"), ("diplomatic_reputation", "1"))),
        ("jxp_a_buddhist_shinbutsu_compact", (("tolerance_heretic", "2"), ("global_missionary_strength", "-0.005"))),
        ("jxp_a_buddhist_temple_magistracy", (("governing_capacity_modifier", "0.05"), ("state_maintenance_modifier", "-0.05"))),
        ("jxp_a_buddhist_exemption_ledger", (("global_tax_modifier", "0.05"), ("global_unrest", "1"))),
        ("jxp_a_buddhist_public_works", (("build_cost", "-0.05"), ("development_cost", "-0.03"))),
        ("jxp_a_buddhist_royal_law", (("legitimacy", "1"), ("stability_cost_modifier", "-0.05"))),
        ("jxp_a_buddhist_three_seat_accord", (("tolerance_heretic", "2"), ("global_tax_modifier", "-0.03"))),
        ("jxp_a_buddhist_printing_houses", (("idea_cost", "-0.03"), ("institution_spread_from_true_faith", "0.10"))),
        ("jxp_a_buddhist_school_network", (("technology_cost", "-0.03"), ("advisor_cost", "-0.05"))),
        ("jxp_a_buddhist_relief_network", (("global_unrest", "-1"), ("manpower_recovery_speed", "0.05"))),
        ("jxp_a_buddhist_pilgrimage_circuit", (("global_trade_power", "0.05"), ("movement_speed", "0.05"))),
        ("jxp_a_buddhist_temple_credit", (("interest", "-0.5"), ("trade_efficiency", "0.05"))),
        ("jxp_a_buddhist_diplomatic_cloisters", (("diplomatic_reputation", "1"), ("improve_relation_modifier", "0.10"))),
        ("jxp_a_buddhist_state_directive", (("reform_progress_growth", "0.10"), ("global_unrest", "1"))),
        ("jxp_a_buddhist_negotiated_compact", (("global_unrest", "-1"), ("global_tax_modifier", "-0.03"))),
        ("jxp_a_buddhist_crisis_recent", (("stability_cost_modifier", "0.05"),)),
    ]
    definitions.extend((f"jxp_a_buddhist_seat_{seat.key}", seat.modifiers) for seat in SEATS)
    lines = ["# Generated by jxp_a_96_buddhist_builder.py. Do not edit."]
    for key, modifiers in definitions:
        lines.append(f"{key} = {{")
        lines.extend(f"\t{name} = {value}" for name, value in modifiers)
        lines.extend(("}", ""))
    return "\n".join(lines)


def render_reforms() -> str:
    lines = ["# Generated by jxp_a_96_buddhist_builder.py. Do not edit."]
    for finale in FINALES:
        final_flag = f"jxp_a_buddhist_final_{finale.key}"
        lines.extend(
            (
                f"{finale.reform_id} = {{",
                f'\ticon = "{finale.icon}"',
                "\tallow_normal_conversion = yes",
                "\tvalid_for_nation_designer = no",
                "\tpotential = {",
                "\t\tOR = {",
                f"\t\t\thas_reform = {finale.reform_id}",
                "\t\t\tAND = {",
                "\t\t\t\tjxp_a_96_buddhist_exact_route_trigger = yes",
                f"\t\t\t\thas_country_flag = {final_flag}",
                "\t\t\t}",
                "\t\t}",
                "\t}",
                "\ttrigger = {",
                "\t\tjxp_a_96_buddhist_exact_route_trigger = yes",
                f"\t\thas_country_flag = {final_flag}",
                "\t}",
                "\tmodifiers = {",
            )
        )
        lines.extend(f"\t\t{name} = {value}" for name, value in finale.modifiers)
        lines.extend(
            (
                "\t}",
                "\tcustom_attributes = { cannot_become_dictatorship = yes }",
                "}",
                "",
            )
        )
    return "\n".join(lines)


def _private_flags() -> tuple[str, ...]:
    flags = [
        "jxp_a_buddhist_shinbutsu_prepared",
        "jxp_a_buddhist_dynamic_name_applied",
        "jxp_a_buddhist_council_opened",
        "jxp_a_buddhist_shinshu_candidate",
        "jxp_a_buddhist_shinshu_tolerated",
        "jxp_a_buddhist_shinshu_restricted",
        "jxp_a_buddhist_final_mutual_law",
        "jxp_a_buddhist_final_mountain_council",
        "jxp_a_buddhist_final_clerical_temporal",
    ]
    for seat in SEATS:
        flags.extend((
            f"jxp_a_buddhist_seat_{seat.key}_recognized",
            f"jxp_a_buddhist_seat_{seat.key}_tolerated",
            f"jxp_a_buddhist_seat_{seat.key}_restricted",
        ))
    return tuple(flags)


def render_effects() -> str:
    modifier_names = [
        "jxp_a_buddhist_shinbutsu_preparation",
        "jxp_a_buddhist_route_constitution",
        "jxp_a_buddhist_sanctuary_guarantees",
        "jxp_a_buddhist_capital_temples",
        "jxp_a_buddhist_gozan_register",
        "jxp_a_buddhist_shinbutsu_compact",
        "jxp_a_buddhist_temple_magistracy",
        "jxp_a_buddhist_exemption_ledger",
        "jxp_a_buddhist_public_works",
        "jxp_a_buddhist_royal_law",
        "jxp_a_buddhist_three_seat_accord",
        "jxp_a_buddhist_printing_houses",
        "jxp_a_buddhist_school_network",
        "jxp_a_buddhist_relief_network",
        "jxp_a_buddhist_pilgrimage_circuit",
        "jxp_a_buddhist_temple_credit",
        "jxp_a_buddhist_diplomatic_cloisters",
        "jxp_a_buddhist_state_directive",
        "jxp_a_buddhist_negotiated_compact",
        "jxp_a_buddhist_crisis_recent",
    ]
    modifier_names.extend(f"jxp_a_buddhist_seat_{seat.key}" for seat in SEATS)
    lines = [
        "# Generated by jxp_a_96_buddhist_builder.py. Do not edit.",
        "jxp_a_96_clear_buddhist_route_effect = {",
        f"\tclr_country_flag = {ROUTE_FLAG}",
        f"\tclr_country_flag = {INTERFACE_FLAG}",
        f"\tset_variable = {{ which = {SEAT_VARIABLE} value = 0 }}",
        "\tif = {",
        "\t\tlimit = { has_country_flag = jxp_a_buddhist_dynamic_name_applied }",
        "\t\trestore_country_name = yes",
        "\t}",
    ]
    lines.extend(f"\tclr_country_flag = {flag}" for flag in _private_flags())
    lines.extend(f"\tremove_country_modifier = {name}" for name in modifier_names)
    for finale in FINALES:
        lines.extend(
            (
                "\tif = {",
                f"\t\tlimit = {{ has_reform = {finale.reform_id} }}",
                f"\t\tremove_government_reform = {finale.reform_id}",
                "\t}",
            )
        )
    lines.extend(("}", "", "jxp_a_96_choose_buddhist_finale_effect = {", "\t# The caller sets exactly one final flag and reform after this reset."))
    for finale in FINALES:
        lines.extend(
            (
                f"\tclr_country_flag = jxp_a_buddhist_final_{finale.key}",
                "\tif = {",
                f"\t\tlimit = {{ has_reform = {finale.reform_id} }}",
                f"\t\tremove_government_reform = {finale.reform_id}",
                "\t}",
            )
        )
    lines.extend(
        (
            "}",
            "",
            "jxp_a_96_reconcile_buddhist_finale_effect = {",
            "\thidden_effect = {",
            "\t\tif = {",
            "\t\t\tlimit = { NOT = { jxp_a_96_buddhist_exact_route_trigger = yes } }",
            "\t\t\tjxp_a_96_clear_buddhist_route_effect = yes",
            "\t\t}",
            "\t\telse = {",
            "\t\t\tif = {",
            "\t\t\t\tlimit = { NOT = { has_country_flag = jxp_a_buddhist_dynamic_name_applied } }",
            f"\t\t\t\toverride_country_name = {DYNAMIC_NAME}",
            "\t\t\t\tset_country_flag = jxp_a_buddhist_dynamic_name_applied",
            "\t\t\t}",
        )
    )
    for index, finale in enumerate(FINALES):
        branch = "if" if index == 0 else "else_if"
        lines.extend(
            (
                f"\t\t\t{branch} = {{",
                f"\t\t\t\tlimit = {{ has_country_flag = jxp_a_buddhist_final_{finale.key} }}",
            )
        )
        for other in FINALES:
            if other is finale:
                continue
            lines.extend(
                (
                    f"\t\t\t\tclr_country_flag = jxp_a_buddhist_final_{other.key}",
                    "\t\t\t\tif = {",
                    f"\t\t\t\t\tlimit = {{ has_reform = {other.reform_id} }}",
                    f"\t\t\t\t\tremove_government_reform = {other.reform_id}",
                    "\t\t\t\t}",
                )
            )
        lines.extend(
            (
                "\t\t\t\tif = {",
                f"\t\t\t\t\tlimit = {{ NOT = {{ has_reform = {finale.reform_id} }} }}",
                f"\t\t\t\t\tadd_government_reform = {finale.reform_id}",
                "\t\t\t\t}",
                "\t\t\t}",
            )
        )
    lines.extend(("\t\t\telse = {",))
    for finale in FINALES:
        lines.extend(
            (
                "\t\t\t\tif = {",
                f"\t\t\t\t\tlimit = {{ has_reform = {finale.reform_id} }}",
                f"\t\t\t\t\tremove_government_reform = {finale.reform_id}",
                "\t\t\t\t}",
            )
        )
    lines.extend(("\t\t\t}", "\t\t}", "\t}", "}", ""))
    return "\n".join(lines)


def render_decisions() -> str:
    other = " ".join(f"has_country_flag = {flag}" for flag in OTHER_ROUTE_FLAGS)
    return f"""# Generated by jxp_a_96_buddhist_builder.py. Do not edit.
country_decisions = {{
\tjxp_a_decision_prepare_shinbutsu_constitution = {{
\t\tmajor = yes
\t\tpotential = {{
\t\t\ttag = JAP
\t\t\treligion = shinto
\t\t\tNOT = {{ has_country_flag = {ROUTE_FLAG} }}
\t\t\tNOT = {{ has_country_flag = jxp_a_buddhist_shinbutsu_prepared }}
\t\t\tNOT = {{ OR = {{ {other} }} }}
\t\t}}
\t\tallow = {{
\t\t\towns = 1020
\t\t\tstability = 1
\t\t\tadm_power = 150
\t\t\tnum_of_owned_provinces_with = {{
\t\t\t\tvalue = 10
\t\t\t\tOR = {{ has_building = temple has_building = cathedral }}
\t\t\t}}
\t\t}}
\t\teffect = {{
\t\t\tadd_adm_power = -150
\t\t\tset_country_flag = jxp_a_buddhist_shinbutsu_prepared
\t\t\tadd_country_modifier = {{ name = jxp_a_buddhist_shinbutsu_preparation duration = 7300 }}
\t\t}}
\t\tai_will_do = {{ factor = 0.05 modifier = {{ factor = 0 NOT = {{ adm_power = 250 }} }} }}
\t}}

\tjxp_a_decision_establish_buddhist_japan = {{
\t\tmajor = yes
\t\tpotential = {{
\t\t\ttag = JAP
\t\t\tNOT = {{ has_country_flag = {ROUTE_FLAG} }}
\t\t\tNOT = {{ OR = {{ {other} }} }}
\t\t}}
\t\tallow = {{
\t\t\tjxp_a_96_can_enter_buddhist_route_trigger = yes
\t\t\tis_at_war = no
\t\t\tstability = 1
\t\t\tadm_power = 100
\t\t\tdip_power = 100
\t\t}}
\t\teffect = {{
\t\t\tadd_adm_power = -100
\t\t\tadd_dip_power = -100
\t\t\tjxp_clear_all_route_flags_effect = yes
\t\t\tset_country_flag = {ROUTE_FLAG}
\t\t\toverride_country_name = {DYNAMIC_NAME}
\t\t\tset_country_flag = jxp_a_buddhist_dynamic_name_applied
\t\t\tset_variable = {{ which = {SEAT_VARIABLE} value = 0 }}
\t\t\tadd_country_modifier = {{ name = jxp_a_buddhist_route_constitution duration = -1 }}
\t\t\tcountry_event = {{ id = jxp_buddhist_state.1 }}
\t\t\tif = {{ limit = {{ religion = jodo_shinshu }} country_event = {{ id = jxp_buddhist_state.2 days = 1 }} }}
\t\t\tjxp_refresh_route_missions_effect = yes
\t\t}}
\t\tai_will_do = {{
\t\t\tfactor = 0.05
\t\t\tmodifier = {{ factor = 5 religion = jodo_shinshu }}
\t\t\tmodifier = {{ factor = 3 religion = mahayana }}
\t\t\tmodifier = {{ factor = 0 religion = shinto NOT = {{ adm_power = 300 }} }}
\t\t}}
\t}}
}}
"""


def _render_seat_events() -> list[str]:
    lines: list[str] = []
    for index, seat in enumerate(SEATS):
        event_id = 100 + index
        recognized = f"jxp_a_buddhist_seat_{seat.key}_recognized"
        tolerated = f"jxp_a_buddhist_seat_{seat.key}_tolerated"
        restricted = f"jxp_a_buddhist_seat_{seat.key}_restricted"
        lines.extend((
            "country_event = {",
            f"\tid = jxp_buddhist_state.{event_id}",
            f"\ttitle = \"jxp_buddhist_state.{event_id}.t\"",
            f"\tdesc = \"jxp_buddhist_state.{event_id}.d\"",
            "\tpicture = COURT_eventPicture",
            "\tis_triggered_only = yes",
            "\ttrigger = {",
            "\t\tjxp_a_96_buddhist_exact_route_trigger = yes",
            "\t\thas_country_flag = jxp_a_buddhist_council_opened",
            "\t\tNOT = {",
            "\t\t\tOR = {",
            f"\t\t\t\thas_country_flag = {recognized}",
            f"\t\t\t\thas_country_flag = {tolerated}",
            f"\t\t\t\thas_country_flag = {restricted}",
            "\t\t\t}",
            "\t\t}",
            "\t}",
            "\toption = {",
            f"\t\tname = \"jxp_buddhist_state.{event_id}.a\"",
            "\t\ttrigger = {",
            f"\t\t\tNOT = {{ check_variable = {{ which = {SEAT_VARIABLE} value = 3 }} }}",
        ))
        if seat.key == "jodo_shinshu":
            lines.append("\t\t\tNOT = { has_country_flag = jxp_a_buddhist_shinshu_restricted }")
        lines.append("\t\t}")
        if seat.key == "jodo_shinshu":
            lines.append(
                "\t\tai_chance = { factor = 1 modifier = { factor = 3 "
                "has_country_flag = jxp_a_buddhist_shinshu_candidate } }"
            )
        lines.extend((
            f"\t\tset_country_flag = {recognized}",
            f"\t\tclr_country_flag = {tolerated}",
            f"\t\tclr_country_flag = {restricted}",
            f"\t\tchange_variable = {{ which = {SEAT_VARIABLE} value = 1 }}",
            f"\t\tadd_country_modifier = {{ name = jxp_a_buddhist_seat_{seat.key} duration = -1 }}",
            "\t}",
            "\toption = {",
            f"\t\tname = \"jxp_buddhist_state.{event_id}.b\"",
        ))
        if seat.key == "jodo_shinshu":
            lines.append(
                "\t\tai_chance = { factor = 1 modifier = { factor = 3 "
                "has_country_flag = jxp_a_buddhist_shinshu_tolerated } }"
            )
        lines.extend((
            f"\t\tset_country_flag = {tolerated}",
            f"\t\tclr_country_flag = {recognized}",
            f"\t\tclr_country_flag = {restricted}",
            "\t\tadd_prestige = 5",
            "\t}",
            "\toption = {",
            f"\t\tname = \"jxp_buddhist_state.{event_id}.c\"",
            f"\t\tset_country_flag = {restricted}",
            f"\t\tclr_country_flag = {recognized}",
            f"\t\tclr_country_flag = {tolerated}",
            "\t\tadd_adm_power = 25",
            "\t\tadd_prestige = -5",
            "\t}",
            "}",
            "",
        ))
    return lines


def render_events() -> str:
    lines = [
        "# Generated by jxp_a_96_buddhist_builder.py. Do not edit.",
        "namespace = jxp_buddhist_state",
        "",
        "country_event = {",
        "\tid = jxp_buddhist_state.1",
        "\ttitle = \"jxp_buddhist_state.1.t\"",
        "\tdesc = \"jxp_buddhist_state.1.d\"",
        "\tpicture = COURT_eventPicture",
        "\tis_triggered_only = yes",
        "\toption = { name = \"jxp_buddhist_state.1.a\" add_adm_power = -50 add_country_modifier = { name = jxp_a_buddhist_state_directive duration = 3650 } }",
        "\toption = { name = \"jxp_buddhist_state.1.b\" add_dip_power = -50 add_country_modifier = { name = jxp_a_buddhist_negotiated_compact duration = 3650 } }",
        "}",
        "",
        "country_event = {",
        "\tid = jxp_buddhist_state.2",
        "\ttitle = \"jxp_buddhist_state.2.t\"",
        "\tdesc = \"jxp_buddhist_state.2.d\"",
        "\tpicture = COURT_eventPicture",
        "\tis_triggered_only = yes",
        "\toption = { name = \"jxp_buddhist_state.2.a\" set_country_flag = jxp_a_buddhist_shinshu_candidate clr_country_flag = jxp_a_buddhist_shinshu_tolerated clr_country_flag = jxp_a_buddhist_shinshu_restricted }",
        "\toption = { name = \"jxp_buddhist_state.2.b\" clr_country_flag = jxp_a_buddhist_shinshu_candidate set_country_flag = jxp_a_buddhist_shinshu_tolerated clr_country_flag = jxp_a_buddhist_shinshu_restricted }",
        "\toption = { name = \"jxp_buddhist_state.2.c\" clr_country_flag = jxp_a_buddhist_shinshu_candidate clr_country_flag = jxp_a_buddhist_shinshu_tolerated set_country_flag = jxp_a_buddhist_shinshu_restricted add_prestige = 5 }",
        "}",
        "",
    ]
    lines.extend(_render_seat_events())
    for crisis in CRISES:
        lines.extend((
            "country_event = {",
            f"\tid = jxp_buddhist_state.{crisis.event_id}",
            f"\ttitle = \"jxp_buddhist_state.{crisis.event_id}.t\"",
            f"\tdesc = \"jxp_buddhist_state.{crisis.event_id}.d\"",
            "\tpicture = COURT_eventPicture",
            "\tis_triggered_only = yes",
            "\ttrigger = {",
            "\t\tjxp_a_96_buddhist_exact_route_trigger = yes",
            *_indent(crisis.trigger, 2),
            "\t}",
            "\timmediate = { add_country_modifier = { name = jxp_a_buddhist_crisis_recent duration = 1825 } }",
            "\toption = {",
            f"\t\tname = \"jxp_buddhist_state.{crisis.event_id}.a\"",
            *_indent(crisis.first_effect, 2),
            "\t}",
            "\toption = {",
            f"\t\tname = \"jxp_buddhist_state.{crisis.event_id}.b\"",
            *_indent(crisis.second_effect, 2),
            "\t}",
            "}",
            "",
        ))
    lines.extend((
        "country_event = {",
        "\tid = jxp_buddhist_state.200",
        "\ttitle = \"jxp_buddhist_state.200.t\"",
        "\tdesc = \"jxp_buddhist_state.200.d\"",
        "\tpicture = COURT_eventPicture",
        "\tis_triggered_only = yes",
    ))
    for index, finale in enumerate(FINALES):
        lines.extend((
            "\toption = {",
            f"\t\tname = \"jxp_buddhist_state.200.{chr(ord('a') + index)}\"",
            "\t\tjxp_a_96_choose_buddhist_finale_effect = yes",
            f"\t\tset_country_flag = jxp_a_buddhist_final_{finale.key}",
            f"\t\tadd_government_reform = {finale.reform_id}",
            "\t\tchange_government_reform_progress = 50",
            "\t}",
        ))
    lines.extend(("}", "", "country_event = {", "\tid = jxp_buddhist_state.900", "\ttitle = \"jxp_buddhist_state.900.t\"", "\tdesc = \"jxp_buddhist_state.900.d\"", "\tpicture = COURT_eventPicture", "\thidden = yes", "\ttrigger = { jxp_a_96_buddhist_exact_route_trigger = yes NOT = { has_country_modifier = jxp_a_buddhist_crisis_recent } }", "\timmediate = {", "\t\trandom_list = {"))
    for crisis in CRISES:
        lines.append(f"\t\t\t10 = {{ country_event = {{ id = jxp_buddhist_state.{crisis.event_id} }} }}")
    lines.extend(("\t\t\t900 = { add_prestige = 0 }", "\t\t}", "\t}", "\toption = { name = \"OK\" }", "}", "", "country_event = {", "\tid = jxp_buddhist_state.901", "\ttitle = \"jxp_buddhist_state.901.t\"", "\tdesc = \"jxp_buddhist_state.901.d\"", "\tpicture = COURT_eventPicture", "\thidden = yes", f"\ttrigger = {{ has_country_flag = {ROUTE_FLAG} }}", "\timmediate = {", "\t\tif = {", "\t\t\tlimit = { NOT = { jxp_a_96_buddhist_exact_route_trigger = yes } }", "\t\t\tjxp_a_96_clear_buddhist_route_effect = yes", "\t\t}", "\t\telse = {", "\t\t\tjxp_a_96_reconcile_buddhist_finale_effect = yes", "\t\t\tif = {", "\t\t\t\tlimit = { NOT = { has_mission = jxp_a_buddhist_nanto_garan } }", "\t\t\t\tjxp_refresh_route_missions_effect = yes", "\t\t\t}", "\t\t}", "\t}", "\toption = { name = \"OK\" }", "}", ""))
    return "\n".join(lines)


def render_on_actions() -> str:
    lines = [
        "# Generated by jxp_a_96_buddhist_builder.py. Do not edit.",
        "on_startup = {",
        "\tevents = { jxp_buddhist_state.901 }",
        "}",
        "",
        "on_government_change = {",
        "\tif = {",
        "\t\tlimit = {",
        "\t\t\tOR = {",
        f"\t\t\t\thas_country_flag = {ROUTE_FLAG}",
    ]
    lines.extend(f"\t\t\t\thas_reform = {finale.reform_id}" for finale in FINALES)
    lines.extend(
        (
            "\t\t\t}",
            "\t\t}",
            "\t\tjxp_a_96_reconcile_buddhist_finale_effect = yes",
            "\t}",
            "}",
            "",
            "on_yearly_pulse = {",
            "\tevents = {",
            "\t\tjxp_buddhist_state.900",
            "\t\tjxp_buddhist_state.901",
            "\t}",
            "}",
            "",
        )
    )
    return "\n".join(lines)


MODIFIER_LOC = {
    "jxp_a_buddhist_shinbutsu_preparation": ("神佛习合国制准备", "朝廷、神社与寺院正在核定礼仪和财赋边界。"),
    "jxp_a_buddhist_route_constitution": ("佛教日本国制", "国家开始制度化诸宗、寺院、教育、施济与佛教外交。"),
    "jxp_a_buddhist_sanctuary_guarantees": ("诸山安堵状", "大寺院获得成文保护，也承担国家规定的责任。"),
    "jxp_a_buddhist_capital_temples": ("京都诸寺普请", "京都寺院的修复成为首都建设的一部分。"),
    "jxp_a_buddhist_gozan_register": ("五山名籍", "住持履历、文书能力与海外往来均受名籍管理。"),
    "jxp_a_buddhist_shinbutsu_compact": ("神佛习合之议", "神祇礼仪与佛教制度在成文边界内共存。"),
    "jxp_a_buddhist_temple_magistracy": ("寺社奉行制", "寺社诉讼、寺领与任官归入专责奉行。"),
    "jxp_a_buddhist_exemption_ledger": ("免税地名簿", "免税权获得核定，但检地也引起地方反弹。"),
    "jxp_a_buddhist_public_works": ("勧进普请账", "勧进款项被用于可核销的公共工程。"),
    "jxp_a_buddhist_royal_law": ("王法与佛法", "王法统辖政务，佛法为护国与施济提供合法性。"),
    "jxp_a_buddhist_three_seat_accord": ("三席诸宗和议", "三宗正式入席，其余宗派获得明确的宽容或限制地位。"),
    "jxp_a_buddhist_printing_houses": ("寺院版木所", "校勘和印刷网络加快经卷与学问传播。"),
    "jxp_a_buddhist_school_network": ("学寮寺子网络", "寺院教育培养文书官并向城镇乡村扩展。"),
    "jxp_a_buddhist_relief_network": ("施药义仓网络", "施药院与义仓共同缓和饥馑和疾病。"),
    "jxp_a_buddhist_pilgrimage_circuit": ("参诣道路网", "参诣道路同时服务信众、商旅与国家交通。"),
    "jxp_a_buddhist_temple_credit": ("寺院町众信用", "寺院借贷与町众信用受到公开账册约束。"),
    "jxp_a_buddhist_diplomatic_cloisters": ("佛法外交僧院", "译僧和寺院文书维系不以征服为目的的海外关系。"),
    "jxp_a_buddhist_state_directive": ("公仪直裁", "国家以成文命令推动寺院改革，效率提高但反弹加剧。"),
    "jxp_a_buddhist_negotiated_compact": ("诸山议定", "国家以让步换取宗派合作，稳定提高但财赋受损。"),
    "jxp_a_buddhist_crisis_recent": ("诸宗余波", "最近的宗派争议仍在影响国家。"),
}


def render_localisation() -> str:
    lines = ["l_english:"]
    for mission in MISSIONS:
        lines.extend((f" {mission.mission_id}_title:0 \"{mission.title}\"", f" {mission.mission_id}_desc:0 \"{mission.description}\""))
    lines.extend((
        " jxp_a_decision_prepare_shinbutsu_constitution_title:0 \"议定神佛习合国制\"",
        " jxp_a_decision_prepare_shinbutsu_constitution_desc:0 \"在统一后的日本核定神社、寺院和朝廷礼仪的共同边界，为一条不要求全国瞬间改宗的佛教国制做准备。\"",
        " jxp_a_decision_establish_buddhist_japan_title:0 \"建立佛教日本国制\"",
        " jxp_a_decision_establish_buddhist_japan_desc:0 \"保持日本国号，以诸宗席位、寺社奉行、施济教育和佛法外交重组统一国家。该路线与既有日本终局路线互斥。\"",
        f" {DYNAMIC_NAME}:0 \"佛教日本\"",
        " jxp_path_buddhist:0 \"佛教日本路线\"",
        " jxp_iface_buddhist_diplomacy_ready:0 \"佛法外交准备完成\"",
        " jxp_buddhist_state.1.t:0 \"护国与公议\"",
        " jxp_buddhist_state.1.d:0 \"统一日本如今必须决定，国家是先以奉行和法令整顿寺院，还是先让诸山代表共同议定责任。两者都承认佛教制度的政治力量，也都要求国家承担代价。\"",
        " jxp_buddhist_state.1.a:0 \"先确立公仪护持\"",
        " jxp_buddhist_state.1.b:0 \"先召开诸山公议\"",
        " jxp_buddhist_state.2.t:0 \"净土真宗在诸宗中的位置\"",
        " jxp_buddhist_state.2.d:0 \"净土真宗已是国教，但佛教日本并非一向门徒国家。我们必须决定，本愿寺与讲众是竞争正式席位、作为无席宗派受宽容，还是先受限制。\"",
        " jxp_buddhist_state.2.a:0 \"允许其竞争正式席位\"",
        " jxp_buddhist_state.2.b:0 \"宽容讲众，但暂不授席\"",
        " jxp_buddhist_state.2.c:0 \"先限制寺内町自治\"",
    ))
    for index, seat in enumerate(SEATS):
        event_id = 100 + index
        lines.extend((
            f" jxp_buddhist_state.{event_id}.t:0 \"{seat.title}\"",
            f" jxp_buddhist_state.{event_id}.d:0 \"承认此席可获得{seat.benefit}；代价是{seat.cost}。正式席位总数不得超过三席。\"",
            f" jxp_buddhist_state.{event_id}.a:0 \"正式承认{seat.title}\"",
            f" jxp_buddhist_state.{event_id}.b:0 \"宽容其活动，但不授席\"",
            f" jxp_buddhist_state.{event_id}.c:0 \"限制其政治与寺领要求\"",
        ))
    for crisis in CRISES:
        lines.extend((
            f" jxp_buddhist_state.{crisis.event_id}.t:0 \"{crisis.title}\"",
            f" jxp_buddhist_state.{crisis.event_id}.d:0 \"{crisis.description}\"",
            f" jxp_buddhist_state.{crisis.event_id}.a:0 \"{crisis.first_title}\"",
            f" jxp_buddhist_state.{crisis.event_id}.b:0 \"{crisis.second_title}\"",
        ))
    lines.extend((
        " jxp_buddhist_state.200.t:0 \"佛国之宪\"",
        " jxp_buddhist_state.200.d:0 \"诸宗席位、寺社奉行、施济教育与佛法外交已经成形。现在必须在国家护持、诸山公议与僧俗分治之间作出互斥的最终制度选择。\"",
        " jxp_buddhist_state.200.a:0 \"颁行王法佛法相依体制\"",
        " jxp_buddhist_state.200.b:0 \"颁行诸山公议国制\"",
        " jxp_buddhist_state.200.c:0 \"颁行僧俗分治法度\"",
        " jxp_buddhist_state.900.t:0 \"诸宗议事调度\"",
        " jxp_buddhist_state.900.d:0 \"诸宗年度议事正在调度。\"",
        " jxp_buddhist_state.901.t:0 \"佛教日本国制校验\"",
        " jxp_buddhist_state.901.d:0 \"佛教日本的互斥路线与任务状态正在校验。\"",
    ))
    for key, (title, desc) in MODIFIER_LOC.items():
        lines.extend((f" {key}:0 \"{title}\"", f" {key}_desc:0 \"{desc}\""))
    for seat in SEATS:
        key = f"jxp_a_buddhist_seat_{seat.key}"
        lines.extend((f" {key}:0 \"正式席位：{seat.title}\"", f" {key}_desc:0 \"收益：{seat.benefit}。代价：{seat.cost}。\""))
    for finale in FINALES:
        key = finale.reform_id
        lines.extend((f" {key}:0 \"{finale.title}\"", f" {key}_desc:0 \"{finale.description}\""))
    return "\n".join(lines) + "\n"


def render_outputs() -> dict[Path, str | bytes]:
    source = render_localisation()
    escape = _load_escape_module()
    missions = _load_b115_builder().render_mission_overlay(
        "missions/jxp_a_96_buddhist_missions.txt", render_missions()
    )
    return {
        MAIN_ROOT / "common" / "scripted_triggers" / "jxp_a_96_buddhist_triggers.txt": render_triggers(),
        MAIN_ROOT / "missions" / "jxp_a_96_buddhist_missions.txt": missions,
        MAIN_ROOT / "common" / "event_modifiers" / "jxp_a_96_buddhist_modifiers.txt": render_modifiers(),
        MAIN_ROOT / "common" / "government_reforms" / "jxp_a_96_buddhist_government_reforms.txt": render_reforms(),
        MAIN_ROOT / "common" / "scripted_effects" / "jxp_a_96_buddhist_effects.txt": render_effects(),
        MAIN_ROOT / "decisions" / "jxp_a_96_buddhist_decisions.txt": render_decisions(),
        MAIN_ROOT / "events" / "jxp_a_96_buddhist_events.txt": render_events(),
        MAIN_ROOT / "common" / "on_actions" / "jxp_a_96_buddhist_on_actions.txt": render_on_actions(),
        MAIN_ROOT / "localisation_source" / "jxp_a_96_buddhist_l_english_utf8_source.yml": source,
        MAIN_ROOT / "localisation" / "jxp_a_96_buddhist_l_english.yml": escape.escape_text(source).encode("utf-8-sig"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when generated outputs drift")
    args = parser.parse_args()
    validate_design()
    outputs = render_outputs()
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
        print(f"PASS: {len(outputs)} Buddhist-Japan outputs are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
