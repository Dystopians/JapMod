#!/usr/bin/env python3
"""Generate the twenty-event Shinshu chronicle and its readable localisation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
EVENT_PATH = MOD_ROOT / "events" / "jxp_a_95_shinshu_events.txt"
LOC_PATH = MOD_ROOT / "localisation_source" / "jxp_a_95_shinshu_l_english_utf8_source.yml"


EVENTS = (
    ("莲如的御文章", "法主的书信以日常语言解释信心与念佛，并沿商路传入新的讲。", "派遣抄写人，先稳固教义", ("add_dip_power = -25", "add_prestige = 5", "jxp_a_shinshu_subtract_militancy_5_effect = yes"), "让各讲自行传抄", ("add_prestige = 10", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("吉崎坊舍", "吉崎的坊舍吸引北陆门徒，也让领主担忧一个不受守护控制的新中心。", "出资修筑并登记坊舍", ("add_treasury = -75", "add_adm_power = 25", "jxp_a_shinshu_subtract_militancy_5_effect = yes"), "依靠门徒自筹", ("add_treasury = 25", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("门徒讲的扩张", "讲把信仰、互助和地方议事结合起来，其网络已经越过一国边界。", "承认讲长并建立名册", ("add_adm_power = -25", "add_prestige = 5", "jxp_a_shinshu_subtract_militancy_5_effect = yes"), "鼓励讲众自行组织", ("add_mil_power = 25", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("寺内町市场", "围绕坊舍形成的寺内町要求市场特权与安全保证。", "颁给有期限的市场朱印", ("add_treasury = -50", "add_country_modifier = { name = jxp_a_shinshu_temple_town_charter duration = 1825 }", "jxp_a_shinshu_add_militancy_5_effect = yes"), "由町众承担防务与税收", ("add_treasury = 50", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("惣村与年贡", "惣村愿意按共同体分摊年贡，但拒绝层层加派。", "接受惣村的集体契约", ("add_adm_power = -25", "add_country_modifier = { name = jxp_a_shinshu_petition_compromise duration = 1825 }", "jxp_a_shinshu_subtract_militancy_10_effect = yes"), "坚持逐户征收", ("add_adm_power = 25", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("共同粮仓", "门徒与村众提议建立粮仓，在歉收时赈济信众。", "国主与讲众共同出资", ("add_treasury = -50", "add_prestige = 5", "jxp_a_shinshu_subtract_militancy_5_effect = yes"), "允许讲众独自经营", ("add_treasury = 50", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("本愿寺坊官", "坊官希望把分散的末寺、讲与寺内町纳入统一文书网络。", "让坊官接受国法审计", ("add_adm_power = -25", "jxp_a_shinshu_subtract_militancy_5_effect = yes"), "授权坊官整顿门徒", ("add_dip_power = 25", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("加贺门徒的政治要求", "加贺门徒要求在守护裁判和年贡安排中拥有正式席位。", "召开守护、国人与门徒会议", ("add_adm_power = -50", "add_dip_power = -25", "jxp_a_shinshu_subtract_militancy_10_effect = yes"), "以法主权威支持请愿", ("add_prestige = 10", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("三河一向一揆", "三河门徒拒绝检地与军役，地方武士也被卷入冲突。", "由寺社奉行调停", ("add_mil_power = -50", "add_stability = 1", "jxp_a_shinshu_subtract_militancy_15_effect = yes"), "动员忠实门徒自卫", ("add_country_modifier = { name = jxp_a_shinshu_armed_oath duration = 1825 }", "add_mil_power = 25", "jxp_a_shinshu_add_militancy_15_effect = yes")),
    ("长岛轮中与防御", "长岛的堤防、河道和轮中聚落既抵御洪水，也构成难攻的共同防线。", "把防务纳入国主军役", ("add_treasury = -75", "add_country_modifier = { name = jxp_a_shinshu_armed_oath duration = 1825 }", "jxp_a_shinshu_add_militancy_10_effect = yes"), "保持民政优先", ("add_adm_power = -25", "jxp_a_shinshu_subtract_militancy_10_effect = yes")),
    ("石山本愿寺", "石山的地势与商路足以承载一座宏伟坊舍，也足以成为长期围攻的焦点。", "建设城塞化坊舍", ("add_treasury = -100", "add_army_tradition = 5", "jxp_a_shinshu_add_militancy_15_effect = yes"), "建设开放的讲学与市场中心", ("add_dip_power = -50", "add_prestige = 10", "jxp_a_shinshu_subtract_militancy_10_effect = yes")),
    ("杂贺铁炮众", "纪伊的门徒与地侍愿以铁炮守卫寺内町，但他们坚持保留地方议事权。", "签订有期限的防卫契约", ("add_mil_power = -50", "add_country_modifier = { name = jxp_a_shinshu_armed_oath duration = 1825 }", "jxp_a_shinshu_add_militancy_10_effect = yes"), "优先维持町众自治", ("add_dip_power = -50", "jxp_a_shinshu_subtract_militancy_10_effect = yes")),
    ("参诣道路", "朝圣道路带来旅人、工匠和布施，也使教义传播更快。", "修路并设公共宿坊", ("add_dip_power = -25", "add_prestige = 5", "jxp_a_shinshu_subtract_militancy_5_effect = yes"), "交给沿路讲众维护", ("add_treasury = 50", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("寺院印刷", "木版印刷能让御文章与劝化文本迅速流通，也会削弱坊官对解释权的控制。", "刊行经过校定的版本", ("add_adm_power = -50", "add_prestige = 10", "jxp_a_shinshu_subtract_militancy_10_effect = yes"), "允许地方讲众自行刊刻", ("add_dip_power = 25", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("法主与地方讲众", "地方讲众认为坊官不了解村社负担，法主则担心网络分裂。", "让双方在惣门公议中申辩", ("add_dip_power = -50", "jxp_a_shinshu_subtract_militancy_10_effect = yes"), "确认法主最终裁断权", ("add_prestige = 10", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("和平信仰还是武装动员", "外敌逼近时，门徒争论念佛共同体是否应承担常备军役。", "限制武装，只守寺内町", ("add_mil_power = -25", "jxp_a_shinshu_subtract_militancy_15_effect = yes"), "敲响战钟，全面动员", ("add_country_modifier = { name = jxp_a_shinshu_armed_oath duration = 1825 }", "jxp_a_shinshu_add_militancy_15_effect = yes")),
    ("大名要求寺领检地", "领主要求把寺领纳入检地，而末寺担心赈济与布施土地被征收。", "由寺社奉行联合丈量", ("add_treasury = -50", "add_adm_power = 25", "jxp_a_shinshu_subtract_militancy_10_effect = yes"), "强制执行统一检地", ("add_adm_power = 50", "jxp_a_shinshu_add_militancy_15_effect = yes")),
    ("町众要求自治", "寺内町的商人与工匠要求自行选举年寄并审理市场纠纷。", "批准受监督的町法", ("add_treasury = -75", "add_country_modifier = { name = jxp_a_shinshu_temple_town_charter duration = 1825 }", "jxp_a_shinshu_add_militancy_5_effect = yes"), "派奉行接管市场", ("add_dip_power = -25", "jxp_a_shinshu_subtract_militancy_10_effect = yes")),
    ("门徒拒绝外征", "门徒认为战钟只应用于保卫讲众，不应为远方领土扩张而敲响。", "承诺限制外征军役", ("add_mil_power = -25", "add_prestige = -5", "jxp_a_shinshu_subtract_militancy_10_effect = yes"), "坚持国主拥有征发权", ("add_mil_power = 25", "jxp_a_shinshu_add_militancy_10_effect = yes")),
    ("本愿寺继承与派系", "新法主继承使坊官、亲族与地方讲众重新争夺网络的方向。", "召开公开继承会议", ("add_adm_power = -50", "add_stability = 1", "jxp_a_shinshu_subtract_militancy_15_effect = yes"), "由内廷坊官迅速裁定", ("add_prestige = 10", "jxp_a_shinshu_add_militancy_15_effect = yes")),
)


EXTRA_LOC = {
    "jodo_shinshu": "净土真宗",
    "jodo_shinshu_religion_desc": "净土真宗以阿弥陀佛本愿、念佛与信心为中心。亲鸾奠立的教团经莲如的御文章、讲与坊舍扩展，并在寺内町、惣村和本愿寺网络中形成多样的社会组织；日常门徒共同体并不等同于武装一揆。",
    "jodo_shinshu_rebels_demand": "承认$RELIGION$",
    "jodo_shinshu_rebels_demand_desc": "这些门徒要求停止强迫改宗，并承认净土真宗共同体的信仰空间。",
    "jodo_shinshu_rebels_title": "净土真宗门徒",
    "jodo_shinshu_rebels_name": "$RELIGION$门徒",
    "jodo_shinshu_rebels_desc": "受压迫的讲众和门徒可能结成宗教反抗，但净土真宗省份并不会自动成为武装一揆。",
    "jodo_shinshu_rebels_army": "$RELIGION$门徒军",
    "jxp_a_shinshu_peaceful_congregations": "和平讲众",
    "jxp_a_shinshu_peaceful_congregations_desc": "讲众以互助、施济和日常念佛为重，社会稳定而军事动员有限。",
    "jxp_a_shinshu_temple_town_community": "寺内町共同体",
    "jxp_a_shinshu_temple_town_community_desc": "讲、惣村、坊舍和市场在自治与国法之间形成平衡。",
    "jxp_a_shinshu_armed_followers": "武装门徒",
    "jxp_a_shinshu_armed_followers_desc": "战钟能够迅速动员门徒并固守坊舍，但会损害税收、服从与对外信誉。",
    "jxp_a_shinshu_petition_compromise": "德政请愿的调停",
    "jxp_a_shinshu_temple_town_charter": "寺内町特许",
    "jxp_a_shinshu_armed_oath": "武装起请",
    "jxp_a_shinshu_reconciled_order": "国法保障的和议",
    "jxp_a_shinshu_reconciled_order_desc": "寺内町、惣村与门徒组织获得有限保障，同时接受国法审计与共同军役。",
    "jxp_a_shinshu_suppression_aftershock": "镇压后的余波",
    "jxp_a_shinshu_suppression_aftershock_desc": "武装组织已经解体，但强制检地与寺领处置仍在地方留下不满。",
    "jxp_a_ijp_hoshu_state": "法主国家",
    "jxp_a_ijp_somon_council": "惣门公议",
    "jxp_a_ijp_secular_commonwealth": "世俗共同体",
    "jxp_a_95_decision_hoshu_state_title": "确立法主国家",
    "jxp_a_95_decision_hoshu_state_desc": "让法主、坊官与本愿寺网络成为共同体国家的中枢。",
    "jxp_a_95_decision_somon_council_title": "召开惣门公议",
    "jxp_a_95_decision_somon_council_desc": "把寺内町、惣村、町众与讲众代表纳入常设议事。",
    "jxp_a_95_decision_secular_commonwealth_title": "建立世俗共同体",
    "jxp_a_95_decision_secular_commonwealth_desc": "保留净土真宗国教，同时解除法主与武装门徒的政治垄断。",
    "jxp_a_shinshu_terminal_exclusive_tt": "这将固定一项互斥的共同体终局，并清理其他终局与一向危机状态。",
    "jxp_a_shinshu_militancy_rises_5_tt": "门徒武装化提高§R5§!。",
    "jxp_a_shinshu_militancy_rises_10_tt": "门徒武装化提高§R10§!。",
    "jxp_a_shinshu_militancy_falls_5_tt": "门徒武装化降低§G5§!。",
    "jxp_a_shinshu_militancy_falls_10_tt": "门徒武装化降低§G10§!。",
    "jxp_shinshu.100.t": "讲众增长",
    "jxp_shinshu.100.d": "越来越多的讲把念佛、互助与地方议事联系起来。一向危机已经进入第一阶段。",
    "jxp_shinshu.100.a": "记录讲长并承认日常信仰",
    "jxp_shinshu.100.b": "先观察这些新讲",
    "jxp_shinshu.101.t": "德政、税役与寺领请愿",
    "jxp_shinshu.101.d": "门徒要求减轻加派、确认寺领并限制军役，一向危机进入第二阶段。",
    "jxp_shinshu.101.a": "由寺社奉行调停",
    "jxp_shinshu.101.b": "拒绝集体请愿",
    "jxp_shinshu.102.t": "寺内町自治",
    "jxp_shinshu.102.d": "坊舍周围的町众要求市场、警备和裁判自治，一向危机进入第三阶段。",
    "jxp_shinshu.102.a": "颁给受监督的町法",
    "jxp_shinshu.102.b": "把寺内町纳入检地",
    "jxp_shinshu.103.t": "武装起请",
    "jxp_shinshu.103.d": "门徒在佛前立誓并敲响战钟，一向危机进入第四阶段。",
    "jxp_shinshu.103.a": "以和议约束战钟",
    "jxp_shinshu.103.b": "认可共同防卫",
    "jxp_shinshu.104.t": "大规模一揆与政权抉择",
    "jxp_shinshu.104.d": "国主、法主、坊官、町众与惣村必须决定共同体的最终秩序。",
    "jxp_shinshu.104.a": "达成受国法保障的和议",
    "jxp_shinshu.104.b": "镇压武装组织",
    "jxp_shinshu.104.c": "让共同体接管政权",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def render_events() -> str:
    lines = ["namespace = jxp_shinshu", ""]
    for index, (title, desc, a_name, a_effects, b_name, b_effects) in enumerate(EVENTS, start=1):
        next_id = index + 1
        lines.extend([
            "country_event = {",
            f"\tid = jxp_shinshu.{index}",
            f'\ttitle = "jxp_shinshu.{index}.t"',
            f'\tdesc = "jxp_shinshu.{index}.d"',
            "\tpicture = RELIGIOUS_CONVERSION_eventPicture",
            "\tis_triggered_only = yes",
            "\ttrigger = {",
            "\t\tjxp_a_shinshu_country_trigger = yes",
            "\t\thas_country_flag = jxp_a_shinshu_event_chain_active",
            f"\t\tNOT = {{ has_country_flag = jxp_a_shinshu_event_{index:02d}_seen }}",
            "\t}",
            "\toption = {",
            f'\t\tname = "jxp_shinshu.{index}.a"',
            f"\t\tset_country_flag = jxp_a_shinshu_event_{index:02d}_seen",
        ])
        lines.extend(f"\t\t{effect}" for effect in a_effects)
        if index < len(EVENTS):
            lines.append(f"\t\tcountry_event = {{ id = jxp_shinshu.{next_id} days = 540 }}")
        else:
            lines.append("\t\tclr_country_flag = jxp_a_shinshu_event_chain_active")
        lines.extend(["\t}", "\toption = {", f'\t\tname = "jxp_shinshu.{index}.b"', f"\t\tset_country_flag = jxp_a_shinshu_event_{index:02d}_seen"])
        lines.extend(f"\t\t{effect}" for effect in b_effects)
        if index < len(EVENTS):
            lines.append(f"\t\tcountry_event = {{ id = jxp_shinshu.{next_id} days = 540 }}")
        else:
            lines.append("\t\tclr_country_flag = jxp_a_shinshu_event_chain_active")
        lines.extend(["\t}", "}", ""])

    lines.extend([
        "country_event = {",
        "\tid = jxp_shinshu.90",
        "\ttitle = none",
        "\tdesc = none",
        "\tpicture = RELIGIOUS_CONVERSION_eventPicture",
        "\thidden = yes",
        "\tis_triggered_only = yes",
        "\timmediate = {",
        "\t\tjxp_a_shinshu_migrate_v029_effect = yes",
        "\t\tif = {",
        "\t\t\tlimit = {",
        "\t\t\t\tjxp_a_shinshu_country_trigger = yes",
        "\t\t\t\tNOT = { has_country_flag = jxp_a_shinshu_event_chain_active }",
        "\t\t\t\tNOT = { has_country_flag = jxp_a_shinshu_event_20_seen }",
        "\t\t\t}",
        "\t\t\tset_country_flag = jxp_a_shinshu_event_chain_active",
        "\t\t\tcountry_event = { id = jxp_shinshu.1 days = 365 }",
        "\t\t}",
        "\t}",
        "\toption = { name = \"OK\" }",
        "}",
        "",
        "country_event = {",
        "\tid = jxp_shinshu.100",
        '\ttitle = "jxp_shinshu.100.t"',
        '\tdesc = "jxp_shinshu.100.d"',
        "\tpicture = RELIGIOUS_CONVERSION_eventPicture",
        "\tis_triggered_only = yes",
        "\timmediate = {",
        "\t\tset_country_flag = jxp_ikko_rising_active",
        "\t\tjxp_a_shinshu_initialize_effect = yes",
        "\t\tjxp_a_shinshu_set_stage_1_effect = yes",
        "\t}",
        "\toption = {",
        '\t\tname = "jxp_shinshu.100.a"',
        "\t\tadd_adm_power = -25",
        "\t\tjxp_a_shinshu_subtract_militancy_5_effect = yes",
        "\t\tcountry_event = { id = jxp_shinshu.101 days = 365 }",
        "\t}",
        "\toption = {",
        '\t\tname = "jxp_shinshu.100.b"',
        "\t\tjxp_a_shinshu_add_militancy_5_effect = yes",
        "\t\tcountry_event = { id = jxp_shinshu.101 days = 365 }",
        "\t}",
        "}",
        "",
    ])
    stages = (
        (101, "jxp_a_shinshu_stage_1_congregations", "jxp_a_shinshu_set_stage_2_effect", "add_country_modifier = { name = jxp_a_shinshu_petition_compromise duration = 1825 }", "jxp_a_shinshu_subtract_militancy_10_effect = yes", "add_adm_power = 25", "jxp_a_shinshu_add_militancy_10_effect = yes"),
        (102, "jxp_a_shinshu_stage_2_petitions", "jxp_a_shinshu_set_stage_3_effect", "add_country_modifier = { name = jxp_a_shinshu_temple_town_charter duration = 1825 }", "jxp_a_shinshu_add_militancy_5_effect = yes", "add_adm_power = -50", "jxp_a_shinshu_subtract_militancy_10_effect = yes"),
        (103, "jxp_a_shinshu_stage_3_temple_town", "jxp_a_shinshu_set_stage_4_effect", "add_dip_power = -50", "jxp_a_shinshu_subtract_militancy_15_effect = yes", "add_country_modifier = { name = jxp_a_shinshu_armed_oath duration = 1825 }", "jxp_a_shinshu_add_militancy_15_effect = yes"),
    )
    for event_id, required_stage_flag, stage_effect, a1, a2, b1, b2 in stages:
        next_id = event_id + 1
        lines.extend([
            "country_event = {", f"\tid = jxp_shinshu.{event_id}", f'\ttitle = "jxp_shinshu.{event_id}.t"', f'\tdesc = "jxp_shinshu.{event_id}.d"', "\tpicture = RELIGIOUS_CONVERSION_eventPicture", "\tis_triggered_only = yes", f"\ttrigger = {{ has_disaster = jxp_ikko_rising has_country_flag = jxp_ikko_rising_active has_country_flag = {required_stage_flag} }}", f"\timmediate = {{ {stage_effect} = yes }}", "\toption = {", f'\t\tname = "jxp_shinshu.{event_id}.a"', f"\t\t{a1}", f"\t\t{a2}", f"\t\tcountry_event = {{ id = jxp_shinshu.{next_id} days = 365 }}", "\t}", "\toption = {", f'\t\tname = "jxp_shinshu.{event_id}.b"', f"\t\t{b1}", f"\t\t{b2}", f"\t\tcountry_event = {{ id = jxp_shinshu.{next_id} days = 365 }}", "\t}", "}", "",
        ])
    lines.extend([
        "country_event = {",
        "\tid = jxp_shinshu.104",
        '\ttitle = "jxp_shinshu.104.t"',
        '\tdesc = "jxp_shinshu.104.d"',
        "\tpicture = RELIGIOUS_CONVERSION_eventPicture",
        "\tis_triggered_only = yes",
        "\ttrigger = { has_disaster = jxp_ikko_rising has_country_flag = jxp_ikko_rising_active has_country_flag = jxp_a_shinshu_stage_4_armed_oath }",
        "\timmediate = { jxp_a_shinshu_set_stage_5_effect = yes }",
        "\toption = {",
        '\t\tname = "jxp_shinshu.104.a"',
        "\t\tset_country_flag = jxp_ikko_rising_resolved",
        "\t\tadd_country_modifier = { name = jxp_a_shinshu_reconciled_order duration = 7300 }",
        "\t\tjxp_a_shinshu_subtract_militancy_20_effect = yes",
        "\t\tend_disaster = jxp_ikko_rising",
        "\t}",
        "\toption = {",
        '\t\tname = "jxp_shinshu.104.b"',
        "\t\tset_country_flag = jxp_ikko_rising_resolved",
        "\t\tadd_mil_power = -100",
        "\t\tadd_country_modifier = { name = jxp_a_shinshu_suppression_aftershock duration = 3650 }",
        "\t\tjxp_a_shinshu_subtract_militancy_40_effect = yes",
        "\t\tend_disaster = jxp_ikko_rising",
        "\t}",
        "\toption = {",
        '\t\tname = "jxp_shinshu.104.c"',
        "\t\ttrigger = { jxp_can_form_ikko_commonwealth_trigger = yes }",
        "\t\tai_chance = {",
        "\t\t\tfactor = 1",
        "\t\t\tmodifier = { factor = 100 has_country_flag = jxp_map_origin_hng }",
        "\t\t\tmodifier = { factor = 0.05 NOT = { has_country_flag = jxp_map_origin_hng } }",
        "\t\t}",
        "\t\tset_country_flag = jxp_ikko_rising_resolved",
        "\t\tend_disaster = jxp_ikko_rising",
        "\t\tjxp_clear_all_route_flags_effect = yes",
        "\t\tset_country_flag = jxp_path_ikko",
        "\t\tjxp_change_to_ijp_effect = yes",
        "\t\tjxp_grant_ikko_heartland_claims_effect = yes",
        "\t}",
        "}",
        "",
        "country_event = {",
        "\tid = jxp_shinshu.190",
        "\ttitle = none",
        "\tdesc = none",
        "\tpicture = RELIGIOUS_CONVERSION_eventPicture",
        "\thidden = yes",
        "\tis_triggered_only = yes",
        "\timmediate = {",
        "\t\tset_country_flag = jxp_ikko_rising_resolved",
        "\t\tclr_country_flag = jxp_ikko_rising_active",
        "\t\tjxp_a_shinshu_cleanup_crisis_effect = yes",
        "\t}",
        "\toption = { name = \"OK\" }",
        "}",
        "",
    ])
    return "\n".join(lines)


def render_localisation() -> str:
    lines = ["l_english:"]
    for index, (title, desc, a_name, _a, b_name, _b) in enumerate(EVENTS, start=1):
        lines.extend([
            f' jxp_shinshu.{index}.t:0 "{title}"',
            f' jxp_shinshu.{index}.d:0 "{desc}"',
            f' jxp_shinshu.{index}.a:0 "{a_name}"',
            f' jxp_shinshu.{index}.b:0 "{b_name}"',
        ])
    lines.extend(f' {key}:0 "{value}"' for key, value in EXTRA_LOC.items())
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    expected = {
        EVENT_PATH: render_events().encode("utf-8"),
        LOC_PATH: render_localisation().encode("utf-8-sig"),
    }
    drift = []
    for path, data in expected.items():
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                drift.append(path.relative_to(MOD_ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if drift:
        raise RuntimeError("Generated Shinshu content drift: " + ", ".join(drift))
    print("Shinshu content check passed" if args.check else "Generated 20-event Shinshu chronicle and source localisation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
