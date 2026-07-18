#!/usr/bin/env python3
"""Build the JXP Japanese estate layer from pinned EU4 1.37.5 sources.

The three vanilla estates are complete top-level objects and therefore cannot
be extended safely from an additive file.  This builder reconstructs their
exact-path files from byte-pinned vanilla inputs, then adds one fourth estate,
Japanese privileges/agendas, and decision-driven interaction menus.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
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

VANILLA_PINS = {
    Path("common/estates/01_church.txt"): (
        "CCA37F3F5B30595CC2A2DB9FB833A53F1F4551C188EB6341CD0C2FB54C6BF42B"
    ),
    Path("common/estates/02_nobility.txt"): (
        "78BEB182B60985A46E99F8BFF84A46CCCE274CC3944031C7366FE9A71428D9BE"
    ),
    Path("common/estates/03_burghers.txt"): (
        "2DD634CEF4522EE8E43E6E34005779B90A806735A6C88B11831BCC30F7034DCD"
    ),
    Path("events/EstatePrivilegesAndAgendasEvents.txt"): (
        "D4E2CA0225356737A7D8660E6AAD6C93BBD6AEB53538A24D26A5E4CEBD9DC994"
    ),
    Path("common/scripted_effects/01_scripted_effects_for_estates.txt"): (
        "FA3F71509F86EA6B137E104336280F7B8EB49A712EECED918D670829DC04A8F1"
    ),
}

ESTATE_FILES = {
    "estate_church": Path("common/estates/01_church.txt"),
    "estate_nobles": Path("common/estates/02_nobility.txt"),
    "estate_burghers": Path("common/estates/03_burghers.txt"),
}

ESTATE_SHORT = {
    "estate_nobles": "nobles",
    "estate_church": "church",
    "estate_burghers": "burghers",
    "jxp_estate_village_communes": "villages",
}


@dataclass(frozen=True)
class Privilege:
    estate: str
    slug: str
    name: str
    desc: str
    benefit: tuple[str, str]
    penalty: tuple[str, str]
    icon: str
    land_share: int = 3
    loyalty: str = "0.05"
    influence: str = "0.05"
    valid_extra: str = "always = yes"

    @property
    def key(self) -> str:
        return f"jxp_a_{ESTATE_SHORT[self.estate]}_{self.slug}"


@dataclass(frozen=True)
class Agenda:
    estate: str
    slug: str
    name: str
    desc: str
    requirement: str
    power: str

    @property
    def key(self) -> str:
        return f"jxp_a_{ESTATE_SHORT[self.estate]}_agenda_{self.slug}"


def _p(
    estate: str,
    slug: str,
    name: str,
    desc: str,
    benefit: tuple[str, str],
    penalty: tuple[str, str],
    icon: str,
    *,
    land_share: int = 3,
    loyalty: str = "0.05",
    influence: str = "0.05",
    valid_extra: str = "always = yes",
) -> Privilege:
    return Privilege(
        estate,
        slug,
        name,
        desc,
        benefit,
        penalty,
        icon,
        land_share,
        loyalty,
        influence,
        valid_extra,
    )


PRIVILEGES = (
    # Warrior households / vanilla Nobles.
    _p("estate_nobles", "kokujin_oaths", "国人众起请", "以连署起请确认国人与被官的旧知行及守城军役。誓纸能使新附诸众暂安，却也承认地方武家的议价之权。", ("manpower_recovery_speed", "0.10"), ("min_autonomy_in_territories", "0.05"), "privilege_land_rights", land_share=5),
    _p("estate_nobles", "chigyo_confirmation", "知行安堵", "对旧臣、降将与在地武士逐一发给安堵状，使征服后的土地关系有案可循。国家由此少一分纷争，也少一分任意转封的余地。", ("governing_capacity", "50"), ("global_tax_modifier", "-0.05"), "privilege_legitimacy"),
    _p("estate_nobles", "yorioya_yoriko", "寄亲—寄子认可", "承认寄亲统率寄子的军役链条，并令奉行定期核验名簿。此制便于动员，却使陪臣政治更为盘根错节。", ("land_forcelimit_modifier", "0.10"), ("state_maintenance_modifier", "0.10"), "privilege_raise_host"),
    _p("estate_nobles", "castle_town_residences", "城下屋敷", "命主要家臣在城下营造屋敷，使人质、消费与政务都聚于主城。城下因之兴盛，营造负担亦随之加重。", ("advisor_cost", "-0.05"), ("build_cost", "0.05"), "privilege_fort"),
    _p("estate_nobles", "war_levy_assessment", "军役段钱", "按田段预定战时军役与段钱，免去临阵逐家催征。动员更为迅捷，但乡里与国库都须供养这套常备名簿。", ("reinforce_speed", "0.10"), ("land_maintenance_modifier", "0.05"), "privilege_demand_more_troops"),
    _p("estate_nobles", "fudai_magistrates", "谱代奉行制", "以谱代家臣充任常设奉行，专理诉讼、军粮与转封账册。政令较能贯彻，外样与新附诸家却难免疑惧。", ("yearly_corruption", "-0.05"), ("advisor_cost", "0.05"), "privilege_investigate_corruption"),
    _p("estate_nobles", "tozama_transfer_guarantees", "外样转封保障", "约定无大罪不夺外样旧领，以换取他们承认天下裁定。地方因此安静，中央收回土地的手段却受成文约束。", ("global_unrest", "-1"), ("min_autonomy_in_territories", "0.05"), "privilege_grant_autonomy", land_share=5),
    _p("estate_nobles", "overseas_service_rolls", "海外军役名簿", "把船手、铁炮众与诸家远征份额编入专册，为越海军役预置次第。海军动员得益，国内兵役负担亦更为沉重。", ("naval_forcelimit_modifier", "0.10"), ("global_manpower_modifier", "-0.05"), "privilege_marines", valid_extra="has_country_flag = jxp_iface_overseas_charter_ready"),
    _p("estate_nobles", "hatamoto_direct_service", "旗本直臣化", "从诸家枝族与旧国人中选取旗本，令其越过地方家门直接奉公。直属军势由此精强，俸禄与家中摩擦也一并增加。", ("discipline", "0.025"), ("global_tax_modifier", "-0.05"), "privilege_royal_authority", valid_extra="OR = { jxp_is_daimyo_stage_trigger = yes jxp_final_state_uncommitted_trigger = yes tag = TOY }"),
    _p("estate_nobles", "monetised_stipends", "武家俸禄货币化", "以金银和定期兑付替代部分实米俸禄，使武家不再完全受一时米价牵制。新制倚赖国家信用，也会把利息风险带入家中。", ("inflation_reduction", "0.05"), ("interest", "0.25"), "privilege_aged_paper", valid_extra="has_country_flag = jxp_iface_a_public_credit_ready"),
    _p("estate_nobles", "branch_castle_cadasters", "支城与军役检册", "将支城、兵粮库与守备知行一并登记，令地方防线不再只凭旧家传说。要塞更坚，维持诸城的费用也更高。", ("defensiveness", "0.10"), ("fort_maintenance_modifier", "0.10"), "privilege_fort"),
    _p("estate_nobles", "house_council_seats", "家中评定常席", "准许重臣按席次参与家中评定，以共同背书继承、转封和大战。决策较为稳妥，却不能再由主君独断速行。", ("stability_cost_modifier", "-0.05"), ("advisor_cost", "0.05"), "privilege_government"),

    # Religious establishments / vanilla Church.
    _p("estate_church", "temple_land_confirmation", "寺社领安堵", "确认旧寺社领、祭田与门前役免，使祈祷和地方救济不因战火中断。免税地扩大，也会削弱公仪直接财源。", ("tolerance_own", "1"), ("global_tax_modifier", "-0.05"), "privilege_land_rights", land_share=5),
    _p("estate_church", "kanjin_exemptions", "勧进免税", "准许寺社为桥梁、堂塔与赈济募集勧进，并免除部分关津课役。公共营造得以兴办，征收体系却留下例外。", ("build_cost", "-0.05"), ("global_tax_modifier", "-0.025"), "privilege_make_generous_donation"),
    _p("estate_church", "doctrinal_arbitration", "宗论裁许", "由公仪召集宗论并裁定传教界限，使教义争端不至先诉诸兵火。裁判可安人心，也会让宗门更深介入政务。", ("global_unrest", "-1"), ("idea_cost", "0.025"), "privilege_religious"),
    _p("estate_church", "jinaimachi_autonomy", "寺内町自治", "承认寺内町在市法、夜警与仓廪上的旧例，以换取按期输纳和不开兵门。门前商业繁荣，地方自治也更难收回。", ("production_efficiency", "0.05"), ("min_autonomy_in_territories", "0.05"), "privilege_grant_autonomy", land_share=5),
    _p("estate_church", "academies_and_terakoya", "学寮与寺子教育", "令寺院学寮和乡里寺子承担书算教习，为奉行与町役培养能读账册之人。教育渐广，国家须容纳宗门的解释之权。", ("technology_cost", "-0.025"), ("stability_cost_modifier", "0.05"), "privilege_technology"),
    _p("estate_church", "charity_hospitals", "施药院与义仓", "以寺社网络经营施药、义仓与灾年粥场，使饥病不至立刻化为流民。维持此举需要稳定的免役和施入。", ("manpower_recovery_speed", "0.05"), ("global_tax_modifier", "-0.025"), "privilege_seek_support_of_clergy"),
    _p("estate_church", "warrior_monks", "僧兵保有", "准许诸山保留有限僧兵，担负山门、道路与圣地守备。其兵可助国防，也可能在宗门不满时反噬公仪。", ("fort_maintenance_modifier", "-0.10"), ("global_unrest", "1"), "privilege_manpower_of_true_faith", influence="0.10"),
    _p("estate_church", "overseas_dharma", "海外法灯许可", "准许受册僧侣和教士随商舶往来，并由奉行核验书信与财货。远方知识由此流入，异端争论也更频繁。", ("improve_relation_modifier", "0.10"), ("stability_cost_modifier", "0.05"), "privilege_new_world_mission", valid_extra="jxp_oceanic_opening_at_least_50 = yes"),
    _p("estate_church", "temple_credit_offices", "寺院信用会所", "允许富寺以寄进米、祠堂金和町中存银周转短期信用。国用得一缓手，免税资产却会乘机增长。", ("interest", "-0.25"), ("global_tax_modifier", "-0.05"), "privilege_aged_paper", valid_extra="has_country_flag = jxp_iface_a_public_credit_ready"),
    _p("estate_church", "state_appointed_abbots", "国家任命住持", "由公仪确认大寺住持与神职首座，阻止山门私斗和世袭。任命权加强控制，也会伤及宗门自治。", ("yearly_corruption", "-0.05"), ("tolerance_own", "-1"), "privilege_royal_rule", loyalty="-0.05"),
    _p("estate_church", "sect_council_seats", "诸宗公议席", "按宗派、寺格和地方贡献分配公议席，使教门争端先在席上裁定。诸宗有言路，国家也必须承认他们的集体地位。", ("stability_cost_modifier", "-0.075"), ("advisor_cost", "0.05"), "privilege_government", valid_extra="OR = { jxp_a_96_buddhist_exact_route_trigger = yes jxp_final_state_ikko_trigger = yes }"),
    _p("estate_church", "confessional_schools", "宗门会众学校", "准许受国家承认的教门设立会众学校，教授经义、书算和外语。人才来源扩大，宗派界线也随之凝固。", ("advisor_cost", "-0.05"), ("religious_unity", "-0.05"), "privilege_recruit_minister", valid_extra="OR = { jxp_final_state_kirishitan_trigger = yes jxp_final_state_reformed_trigger = yes jxp_final_state_kaikyo_trigger = yes }"),

    # Urban merchants / vanilla Burghers.
    _p("estate_burghers", "free_markets", "乐市乐座", "废除旧座对若干市日与货物的专断，让来往商贩凭公仪法度交易。市税更广，旧商权的忠诚却会受损。", ("trade_efficiency", "0.10"), ("global_tax_modifier", "-0.025"), "privilege_comission_merchant_ships_for_war"),
    _p("estate_burghers", "town_council_autonomy", "会合众自治", "承认主要都市会合众处理街区、水火与夜警，以定额税换取自治。城町活力上升，中央命令则须先经过商议。", ("development_cost", "-0.05"), ("min_autonomy_in_territories", "0.05"), "privilege_grant_autonomy", land_share=5),
    _p("estate_burghers", "guild_charters", "株仲间特许", "为同业株仲间发给期限章程，责令其保质、输税并备荒。经营更有秩序，垄断价格也可能随之出现。", ("production_efficiency", "0.075"), ("global_trade_power", "-0.05"), "privilege_monopoly_of_goods_cloth"),
    _p("estate_burghers", "mint_management", "金座与银座经营", "委任受审计的金银座收购矿料、铸造货币并公布成色。币制更稳，座商却会要求优先经营权。", ("inflation_reduction", "0.05"), ("global_tax_modifier", "-0.025"), "privilege_monopoly_of_goods_iron"),
    _p("estate_burghers", "warehouse_rice_notes", "藏屋敷与米切手", "认可藏屋敷凭入仓年贡米签发可转让的米切手，使诸藩不必尽待实米售出。周转加快，也放大了米价与信用的牵连。", ("interest", "-0.25"), ("inflation_reduction", "-0.05"), "privilege_aged_paper", valid_extra="has_country_flag = jxp_iface_a_public_credit_ready"),
    _p("estate_burghers", "red_seal_trade", "朱印贸易", "以朱印状登记船主、船员与航路，使海外交易受公仪保护和约束。远洋收益增加，护航与外交开支也随之而来。", ("global_trade_power", "0.10"), ("naval_maintenance_modifier", "0.05"), "privilege_comission_merchant_ships_for_war", valid_extra="jxp_oceanic_opening_at_least_50 = yes"),
    _p("estate_burghers", "company_incorporation", "会社发起权", "允许豪商依章程合本经营，明确出资、分红与审计期限。大业得以聚资，町众也会要求在国政中有更重的声音。", ("global_trade_goods_size_modifier", "0.05"), ("advisor_cost", "0.05"), "privilege_government", valid_extra="OR = { has_country_flag = jxp_iface_a_market_stage_3 has_country_flag = jxp_iface_a_market_stage_4 }"),
    _p("estate_burghers", "port_militias", "港口民兵", "授权港町组织夜警、火消与有限民兵，守护仓库和泊地。海岸防备增强，商人私兵也更难完全裁撤。", ("defensiveness", "0.075"), ("global_unrest", "0.5"), "privilege_comission_merchant_ships_for_war"),
    _p("estate_burghers", "courier_houses", "飞脚问屋", "让飞脚问屋承揽公文、汇兑和行情传递，并按驿程接受检查。价格消息流通更快，维持全国线路亦非无费。", ("trade_efficiency", "0.05"), ("state_maintenance_modifier", "0.05"), "privilege_diplomat"),
    _p("estate_burghers", "marine_insurance", "海运保险", "许可廻船问屋共同分担海难、劫掠与货损，以账簿和见证确定赔付。航运更敢远行，欺诈与串谋也须严查。", ("global_ship_cost", "-0.05"), ("yearly_corruption", "0.05"), "privilege_sailors"),
    _p("estate_burghers", "public_bond_subscription", "国家公债认购", "允许町众以定期公债承接军费与营造，换取明确兑付次第。国库获得缓冲，债权人也会要求稳定的政策。", ("interest", "-0.25"), ("global_tax_modifier", "-0.025"), "privilege_aged_paper", valid_extra="has_country_flag = jxp_iface_a_public_credit_ready"),
    _p("estate_burghers", "commercial_courts", "商事法庭", "由奉行、町年寄与通晓账法者合议商债、海损和合本纠纷。契约更可信，商人自治则进一步制度化。", ("yearly_corruption", "-0.05"), ("advisor_cost", "0.05"), "privilege_government"),

    # Village communes / fourth custom estate.
    _p("jxp_estate_village_communes", "village_tax_compacts", "惣村请负", "以村为单位承诺年贡、治安与失踪户追补，由惣代在内部摊派。征收趋稳，国家却不易直接触及每一户。", ("global_tax_modifier", "0.05"), ("min_autonomy_in_territories", "0.05"), "privilege_land_rights", land_share=5),
    _p("jxp_estate_village_communes", "fixed_land_tax", "年贡定免", "按数年平均收成固定年贡率，免去代官临时增派。农户更敢积蓄，丰年时公仪所得也不会随产量尽增。", ("production_efficiency", "0.05"), ("global_tax_modifier", "-0.025"), "privilege_aged_paper"),
    _p("jxp_estate_village_communes", "irrigation_works", "灌溉普请", "由数村共同修堤、开渠并分担水利役，奉行只核工程与账目。田地收成提高，营造费也要由国家补助。", ("global_trade_goods_size_modifier", "0.05"), ("build_cost", "0.05"), "privilege_dev_cost_desert"),
    _p("jxp_estate_village_communes", "relief_granaries", "常平义仓", "准许乡村在丰年积谷、灾年平粜，由寺社与惣代共同封验仓门。饥荒冲击减轻，平日可征之粮亦有所减少。", ("global_unrest", "-1"), ("global_tax_modifier", "-0.025"), "privilege_make_generous_donation"),
    _p("jxp_estate_village_communes", "separate_soldiers_farmers", "兵农分离", "逐步解除农户常备军役，以专职足轻和俸禄武士承担征战。耕作更加稳定，征兵来源则不如旧时宽广。", ("production_efficiency", "0.075"), ("global_manpower_modifier", "-0.075"), "privilege_peasant"),
    _p("jxp_estate_village_communes", "village_militias", "乡兵动员", "保留由惣村编组的乡兵，仅用于守堤、护仓和本国防御。地方守备增强，农时与治安却可能受武装化拖累。", ("defensiveness", "0.10"), ("production_efficiency", "-0.05"), "privilege_raise_host"),
    _p("jxp_estate_village_communes", "debt_relief_petitions", "德政请求", "承认灾年由惣代呈请延期、减息或重订旧债，但须经奉行逐案核验。乡里可免崩散，债权信用也会受损。", ("global_unrest", "-1"), ("interest", "0.25"), "privilege_aged_paper"),
    _p("jxp_estate_village_communes", "new_field_reclamation", "新田开拓", "把荒地、水边与山麓新田交由数村合力开垦，并给予限期减免。土地利用提高，国家短期税入有所让渡。", ("development_cost", "-0.05"), ("global_tax_modifier", "-0.025"), "privilege_development_efficiency"),
    _p("jxp_estate_village_communes", "rural_industry", "农村手工业", "允许农闲纺织、制纸与小规模加工由村落共同承揽，使乡里分享城市市场。货物增加，也会冲击旧座与年贡秩序。", ("production_efficiency", "0.075"), ("trade_efficiency", "-0.025"), "privilege_monopoly_of_goods_cloth", valid_extra="OR = { has_country_flag = jxp_iface_a_market_stage_2 has_country_flag = jxp_iface_a_market_stage_3 has_country_flag = jxp_iface_a_market_stage_4 }"),
    _p("jxp_estate_village_communes", "village_charters", "村落自治文书", "把入会地、水利、山林与惣代选任写成公认文书，使代官裁断有例可循。乡里争讼减少，自治权也更加牢固。", ("stability_cost_modifier", "-0.05"), ("min_autonomy_in_territories", "0.05"), "privilege_grant_autonomy", land_share=5),
    _p("jxp_estate_village_communes", "common_workshops", "共同工场", "由数村合资设置织场、窑场或作事小屋，按出工与原料分配收益。原工业更成规模，国家须防止新豪强垄断。", ("global_trade_goods_size_modifier", "0.05"), ("global_unrest", "0.5"), "privilege_government", valid_extra="OR = { has_country_flag = jxp_iface_a_market_stage_3 has_country_flag = jxp_iface_a_market_stage_4 }"),
    _p("jxp_estate_village_communes", "overseas_service_exemption", "免除海外军役", "约定惣村不承担越海远征的人丁征发，只供应有定额的粮秣与船具。乡里得以保全劳力，远征军的人力来源因而收窄。", ("global_manpower_modifier", "0.05"), ("naval_forcelimit_modifier", "-0.10"), "privilege_peasant", valid_extra="has_country_flag = jxp_iface_overseas_charter_ready"),
)


# The repository had no pre-110 JXP estate-privilege IDs.  These are the only
# pinned vanilla privileges whose subject is close enough to one of the new
# Japanese privileges to constitute a duplicate.  Old saves keep the vanilla
# privilege (and therefore its exact mechanics); the Japanese equivalent is
# hidden while it is present.  If an interrupted migration serialized both,
# the JXP side is removed through the controlled loyalty transition below.
LEGACY_PRIVILEGE_EQUIVALENTS = (
    ("estate_nobles_land_rights", "jxp_a_nobles_chigyo_confirmation", "estate_nobles"),
    ("estate_nobles_levies", "jxp_a_nobles_war_levy_assessment", "estate_nobles"),
    ("estate_nobles_right_of_counsel", "jxp_a_nobles_house_council_seats", "estate_nobles"),
    ("estate_church_land_rights", "jxp_a_church_temple_land_confirmation", "estate_church"),
    ("estate_burghers_land_rights", "jxp_a_burghers_town_council_autonomy", "estate_burghers"),
)

CONTROLLED_TRANSITION_KEYS = tuple(
    dict.fromkeys(
        [new for _old, new, _estate in LEGACY_PRIVILEGE_EQUIVALENTS]
        + [row.key for row in PRIVILEGES if row.valid_extra != "always = yes"]
    )
)
PRIVILEGE_TRANSITION_FLAGS = {
    key: f"{key}_transition_recent"
    for key in CONTROLLED_TRANSITION_KEYS
}


def _agenda_rows(estate: str, power: str, rows: Iterable[tuple[str, str, str, str]]) -> tuple[Agenda, ...]:
    return tuple(Agenda(estate, slug, name, desc, requirement, power) for slug, name, desc, requirement in rows)


AGENDAS = (
    *_agenda_rows("estate_nobles", "mil", (
        ("compile_land_rolls", "编制知行账", "武家要求把散见于安堵状与旧牒的知行重新汇为一册。", "num_of_cities = 8"),
        ("settle_old_retainers", "安堵旧臣", "武家希望以稳定国势证明新附与旧臣均已各安其所。", "stability = 1"),
        ("order_service_rolls", "整顿军役", "家中评定要求在下次动员前备足可用兵员。", "manpower_percentage = 0.5"),
        ("appoint_magistrates", "建立谱代奉行", "重臣请求为常设奉行预留足够军政资源。", "mil_power = 150"),
        ("repair_branch_castles", "修筑战略支城", "武家要求国库留出一笔足以修城备粮的款项。", "treasury = 200"),
        ("order_castle_residences", "整理城下屋敷", "诸家愿移居城下，但要求主君先恢复威望。", "prestige = 25"),
        ("strengthen_frontier_roads", "强化边疆道路", "家臣希望领国规模足以支撑一套常设道路军役。", "num_of_cities = 12"),
        ("protect_yoriko", "保护寄子", "寄亲诸家要求停止无休止征战，使寄子编制得以整顿。", "is_at_war = no"),
        ("settle_dispossessed_lords", "安置失国武家", "武家要求以充足军务预算安置流寓诸士。", "mil_power = 200"),
        ("resolve_succession_petitions", "裁断家督争议", "评定众要求主君在国势稳定时完成家督裁断。", "stability = 2"),
    )),
    *_agenda_rows("estate_church", "adm", (
        ("convene_debate", "召开宗论", "寺社请求在国中安定时召开公开宗论。", "stability = 1"),
        ("register_temple_lands", "登记寺社领", "宗门愿提交寺领文书，但要求中央先备妥行政人手。", "adm_power = 150"),
        ("found_academy", "建立学寮", "寺社希望国家保留足够财力兴办学寮。", "treasury = 150"),
        ("open_charity_hospital", "设立施药院", "宗门请求在国库充裕时设立施药与赈济机构。", "treasury = 250"),
        ("restore_holy_places", "修复圣地", "寺社要求以国家威望主持一处重要修复。", "prestige = 25"),
        ("secure_pilgrim_roads", "整顿巡礼道路", "宗门希望领国先恢复和平，再疏通巡礼道路。", "is_at_war = no"),
        ("develop_temple_towns", "发展寺内町", "寺社希望国家拥有足够城市来承载门前町网络。", "num_of_cities = 10"),
        ("protect_the_faithful", "保护同宗", "宗门要求恢复足以保护信众的宗教一致。", "religious_unity = 0.90"),
        ("recover_scriptures", "取得经卷", "学僧请求为搜求、刊刻与校勘预留行政资源。", "adm_power = 200"),
        ("relieve_famine", "赈济饥民", "寺社希望在低通胀的国用中筹措赈济。", "NOT = { inflation = 3 }"),
    )),
    *_agenda_rows("estate_burghers", "dip", (
        ("charter_guilds", "建立株仲间", "町众要求在主要城市中推行有期限的同业章程。", "num_of_cities = 8"),
        ("unify_tolls", "统一关津税", "豪商希望国家恢复安定，以便裁撤层层关津。", "stability = 1"),
        ("open_exchange", "设立兑换所", "町众请求准备足够外交与商事人手开办兑换所。", "dip_power = 150"),
        ("issue_trade_notes", "发行商票", "商人希望国库保有足以兑现第一批商票的现金。", "treasury = 200"),
        ("expand_ports", "扩建港口", "海商要求国家至少拥有两处港口以形成廻船线路。", "num_of_ports = 2"),
        ("build_workshops", "兴办工场", "町众希望扩大城市网络，承接各地原料。", "num_of_cities = 12"),
        ("obtain_trade_rights", "取得贸易特权", "商人要求以国家威望为契约背书。", "prestige = 25"),
        ("settle_domain_debt", "清理藩债", "豪商要求把贷款压到可控范围。", "NOT = { num_of_loans = 3 }"),
        ("steady_currency", "平抑米价与钱价", "町众要求把通胀控制在不致破坏日常交易的程度。", "NOT = { inflation = 3 }"),
        ("audit_company_books", "清理会社账目", "会合众要求在和平时期集中审计商事账册。", "is_at_war = no"),
    )),
    *_agenda_rows("jxp_estate_village_communes", "adm", (
        ("fix_land_tax", "固定年贡", "惣代请求在国家安定时议定数年不变的年贡率。", "stability = 1"),
        ("compile_village_registers", "建立村账", "惣村愿整理户口、田亩和入会地，但需要行政人手。", "adm_power = 100"),
        ("build_common_granaries", "建设共同仓", "乡里请求国库备款设立共同仓。", "treasury = 100"),
        ("repair_dikes", "修堤与灌溉", "百姓希望在和平时期集中完成水利普请。", "is_at_war = no"),
        ("reclaim_new_fields", "开垦新田", "惣村要求领国达到足以组织跨村普请的规模。", "num_of_cities = 8"),
        ("expand_rural_workshops", "发展农村工场", "乡里希望国家进入较大的城市市场网络。", "num_of_cities = 12"),
        ("reduce_service_burdens", "减免军役", "百姓要求军役不再耗尽农时与壮丁。", "manpower_percentage = 0.5"),
        ("settle_refugees", "安置流民", "惣代要求先抑制通胀，再安置逃散人口。", "NOT = { inflation = 3 }"),
        ("end_requisitions", "停止掠夺征发", "乡里请求把厌战降到可承受的范围。", "NOT = { war_exhaustion = 2 }"),
        ("grant_relief", "施行德政赈济", "百姓要求清理过度贷款，为灾年留下余地。", "NOT = { num_of_loans = 3 }"),
    )),
)


NAME_MATRIX = (
    ("commercial", "has_country_flag = jxp_iface_a_company_state_route", ("国家武备承包众", "公认宗门", "株主会合众", "自治乡社")),
    ("toyotomi", "tag = TOY", ("五大老家门", "寺社·公家", "大坂豪商", "藏入地百姓")),
    ("sakoku", "jxp_final_state_sakoku_trigger = yes", ("谱代·外样诸家", "宗门改役众", "御用商人", "村请百姓")),
    ("open", "jxp_final_state_open_trigger = yes", ("海军奉行·诸家", "译馆宗门", "朱印豪商", "港乡百姓")),
    ("buddhist", "jxp_a_96_buddhist_exact_route_trigger = yes", ("护法武家", "诸山宗门", "寺町豪商", "施主惣村")),
    ("kirishitan", "jxp_final_state_kirishitan_trigger = yes", ("受洗武家", "日本教会", "教会港市町众", "教区乡民")),
    ("confucian", "jxp_final_state_confucian_trigger = yes", ("武家官僚", "学宫诸生", "礼制商户", "编户齐民")),
    ("imperial", "jxp_final_state_imperial_trigger = yes", ("朝臣武家", "公卿官人", "禁里御用商", "国司编户")),
    ("reformed", "jxp_final_state_reformed_trigger = yes", ("盟约武备众", "御言总会", "港市会众", "自耕町村")),
    ("kaikyo", "jxp_final_state_kaikyo_trigger = yes", ("侍卫·船将", "乌里玛·卡迪", "牙人商团", "田庄共同体")),
    ("ikko", "jxp_final_state_ikko_trigger = yes", ("坊官·门徒武备", "法主·讲中", "寺内町众", "惣门百姓")),
    ("wokou", "jxp_final_state_wokou_trigger = yes", ("船将·岛主", "港浦社寺", "牙人·船主", "岛民渔户")),
    ("uncommitted", "jxp_final_state_uncommitted_trigger = yes", ("诸州武家议众", "公家·宗门议席", "诸市会合众", "国中惣代")),
    ("daimyo", "jxp_is_daimyo_stage_trigger = yes", ("国人·被官众", "寺社众", "町众·座众", "惣村百姓")),
    ("ordinary", "jxp_is_japanese_polity_trigger = yes", ("武家奉公众", "寺社宗门", "町众豪商", "国中百姓")),
)

ESTATE_ORDER = (
    "estate_nobles",
    "estate_church",
    "estate_burghers",
    "jxp_estate_village_communes",
)


def _escape_module():
    spec = importlib.util.spec_from_file_location("jxp_escape_localisation", ESCAPE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical EU4SpecialEscape converter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _loc_line(key: str, value: str) -> str:
    return f' {key}:0 "{value.replace(chr(34), chr(92) + chr(34))}"'


def _indent(text: str, tabs: int = 1) -> str:
    prefix = "\t" * tabs
    return "\n".join(prefix + line if line else "" for line in text.splitlines())


def _matching_brace(text: str, opening: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    comment = False
    for index in range(opening, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unterminated Clausewitz block")


def _named_blocks(text: str, key: str) -> list[tuple[int, int]]:
    pattern = re.compile(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=[ \t]*\{{")
    result = []
    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        result.append((match.start(), _matching_brace(text, opening) + 1))
    return result


def _unique_replace(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def _insert_before_block_close(text: str, start: int, end: int, payload: str) -> str:
    close = end - 1
    return text[:close] + payload.rstrip() + "\n" + text[close:]


def _event_block(text: str, event_id: str) -> tuple[int, int]:
    matches = []
    needle = re.compile(rf"(?m)^[ \t]*id[ \t]*=[ \t]*{re.escape(event_id)}[ \t]*$")
    for start, end in _named_blocks(text, "country_event"):
        if needle.search(text[start:end]):
            matches.append((start, end))
    if len(matches) != 1:
        raise ValueError(f"event {event_id}: expected one block, found {len(matches)}")
    return matches[0]


def _privileges_for(estate: str) -> tuple[Privilege, ...]:
    return tuple(row for row in PRIVILEGES if row.estate == estate)


def _agendas_for(estate: str) -> tuple[Agenda, ...]:
    return tuple(row for row in AGENDAS if row.estate == estate)


def _custom_name_blocks(estate: str) -> str:
    index = ESTATE_ORDER.index(estate)
    blocks = []
    for state, trigger, names in NAME_MATRIX:
        blocks.append(
            "\n".join(
                (
                    "\tcustom_name = {",
                    f"\t\tdesc = jxp_a_estate_name_{ESTATE_SHORT[estate]}_{state}",
                    "\t\ttrigger = {",
                    _indent(trigger, 3),
                    "\t\t}",
                    "\t}",
                )
            )
        )
        if not names[index]:
            raise ValueError(f"missing name matrix value for {estate}/{state}")
    return "\n".join(blocks) + "\n"


def _build_estate_override(vanilla: str, estate: str, digest: str) -> str:
    marker = (
        "# Generated by build_estates.py from EU4 1.37.5; do not edit.\n"
        f"# Pinned vanilla SHA-256: {digest}\n"
    )
    output = marker + vanilla
    first_custom = output.find("\tcustom_name = {")
    if first_custom < 0:
        raise ValueError(f"{estate}: custom_name anchor not found")
    output = output[:first_custom] + _custom_name_blocks(estate) + output[first_custom:]
    privileges = "".join(f"\t\t{row.key}\n" for row in _privileges_for(estate))
    agendas = "".join(f"\t\t{row.key}\n" for row in _agendas_for(estate))
    output = _unique_replace(
        output,
        "\tprivileges = {\n",
        "\tprivileges = {\n" + privileges,
        f"{estate} privileges",
    )
    output = _unique_replace(
        output,
        "\tagendas = {\n",
        "\tagendas = {\n" + agendas,
        f"{estate} agendas",
    )
    return output


def _village_call_diet_option() -> str:
    return """

\toption = {
\t\tname = estate_privileges_and_agendas_events.3.q
\t\ttrigger = { has_country_flag = jxp_estate_village_communes_present_agenda }
\t\tstart_estate_agenda = jxp_estate_village_communes
\t\tgoto = jxp_estate_village_communes
\t\tai_chance = {
\t\t\tfactor = 1
\t\t\tmodifier = {
\t\t\t\tfactor = 2
\t\t\t\tNOT = { estate_loyalty = { estate = jxp_estate_village_communes loyalty = 30 } }
\t\t\t}
\t\t\tmodifier = {
\t\t\t\tfactor = 1.5
\t\t\t\testate_influence = { estate = jxp_estate_village_communes influence = 70 }
\t\t\t}
\t\t}
\t}
"""


def _village_seize_option() -> str:
    return """

\t# Seize from Japanese village communes.
\toption = {
\t\tname = estate_privileges_and_agendas_events.7.q
\t\ttrigger = {
\t\t\thas_estate = jxp_estate_village_communes
\t\t\tNOT = { estate_has_exempt_from_seize_land_privilege = { estate = jxp_estate_village_communes } }
\t\t\testate_territory = { estate = jxp_estate_village_communes territory = 5 }
\t\t}
\t\tseize_land_estate_effect = { estate = jxp_estate_village_communes }
\t\tai_chance = { factor = 0 }
\t}
"""


def _build_estate_event_override(vanilla: str, digest: str) -> str:
    output = (
        "# Generated by build_estates.py from EU4 1.37.5; do not edit.\n"
        f"# Pinned vanilla SHA-256: {digest}\n" + vanilla
    )
    start, end = _event_block(output, "estate_privileges_and_agendas_events.3")
    block = output[start:end]
    block = _unique_replace(
        block,
        "\t\tclr_country_flag = estate_church_present_agenda\n",
        "\t\tclr_country_flag = estate_church_present_agenda\n"
        "\t\tclr_country_flag = jxp_estate_village_communes_present_agenda\n",
        "Call Diet village flag cleanup",
    )
    output = output[:start] + block + output[end:]
    start, end = _event_block(output, "estate_privileges_and_agendas_events.3")
    output = _insert_before_block_close(output, start, end, _village_call_diet_option())
    start, end = _event_block(output, "estate_privileges_and_agendas_events.7")
    output = _insert_before_block_close(output, start, end, _village_seize_option())
    return output


def _picker_branch() -> str:
    return """
\t\t1 = {
\t\t\ttrigger = {
\t\t\t\thas_estate = jxp_estate_village_communes
\t\t\t\tNOT = { has_country_flag = jxp_estate_village_communes_$flag$ }
\t\t\t}
\t\t\tset_country_flag = jxp_estate_village_communes_$flag$
\t\t\t[[estate_action]
\t\t\t$estate_action$ = jxp_estate_village_communes
\t\t\t]
\t\t}
"""


def _rebel_branch() -> str:
    return """
\t\t\t1 = {
\t\t\t\ttrigger = {
\t\t\t\t\towner = {
\t\t\t\t\t\tNOT = { disabled_rebels_from_seized_land_for_estate = { estate = jxp_estate_village_communes } }
\t\t\t\t\t\thas_estate = jxp_estate_village_communes
\t\t\t\t\t\tNOT = { estate_loyalty = { estate = jxp_estate_village_communes loyalty = 30 } }
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\tspawn_rebels = {
\t\t\t\t\ttype = peasant_rebels
\t\t\t\t\tsize = $size$
\t\t\t\t\testate = jxp_estate_village_communes
\t\t\t\t\tas_if_faction = yes
\t\t\t\t}
\t\t\t}
"""


def _insert_into_nested_random_list(text: str, effect: str, payload: str) -> str:
    blocks = [
        bounds
        for bounds in _named_blocks(text, effect)
        if _named_blocks(text[bounds[0] : bounds[1]], "random_list")
    ]
    if len(blocks) != 1:
        raise ValueError(f"{effect}: expected one block, found {len(blocks)}")
    start, end = blocks[0]
    block = text[start:end]
    nested = _named_blocks(block, "random_list")
    if len(nested) != 1:
        raise ValueError(f"{effect}: expected one random_list, found {len(nested)}")
    nstart, nend = nested[0]
    block = _insert_before_block_close(block, nstart, nend, payload)
    return text[:start] + block + text[end:]


def _build_estate_helper_override(vanilla: str, digest: str) -> str:
    output = (
        "# Generated by build_estates.py from EU4 1.37.5; do not edit.\n"
        f"# Pinned vanilla SHA-256: {digest}\n" + vanilla
    )
    output = _insert_into_nested_random_list(output, "pick_random_estate_if_present", _picker_branch())
    output = _insert_into_nested_random_list(output, "spawn_rebels_from_unhappy_estate", _rebel_branch())
    output = _unique_replace(
        output,
        "\t\tclr_country_flag = auto_complete_estate_agenda_estate_ghulams\n",
        "\t\tclr_country_flag = auto_complete_estate_agenda_estate_ghulams\n"
        "\t\tclr_country_flag = auto_complete_estate_agenda_jxp_estate_village_communes\n",
        "village agenda auto-completion cleanup",
    )
    output = _unique_replace(
        output,
        "on_completed_agenda_effect = {\n",
        "on_completed_agenda_effect_jxp_estate_village_communes = {}\n\n"
        "on_completed_agenda_effect = {\n",
        "village agenda completion hook",
    )
    return output


def render_custom_estate() -> str:
    privileges = "".join(f"\t\t{row.key}\n" for row in _privileges_for("jxp_estate_village_communes"))
    agendas = "".join(f"\t\t{row.key}\n" for row in _agendas_for("jxp_estate_village_communes"))
    return (
        "# Generated by build_estates.py. Do not edit.\n"
        "jxp_estate_village_communes = {\n"
        "\ticon = 9\n"
        "\ttrigger = {\n"
        "\t\tjxp_is_japanese_polity_trigger = yes\n"
        "\t\tNOT = { has_disabled_estate = { estate = jxp_estate_village_communes } }\n"
        "\t}\n"
        "\tcountry_modifier_happy = { production_efficiency = 0.10 global_unrest = -1 }\n"
        "\tcountry_modifier_neutral = { production_efficiency = 0.05 }\n"
        "\tcountry_modifier_angry = { production_efficiency = -0.10 global_unrest = 2 }\n"
        "\tland_ownership_modifier = {}\n"
        "\tprovince_independence_weight = {\n"
        "\t\tfactor = 1\n"
        "\t\tmodifier = { factor = 1.25 development = 12 }\n"
        "\t\tmodifier = { factor = 1.20 has_building = workshop }\n"
        "\t}\n"
        "\tbase_influence = 10\n"
        "\tinfluence_modifier = {\n"
        "\t\tdesc = jxp_a_estate_val_large_rural_realm\n"
        "\t\ttrigger = { num_of_cities = 15 }\n"
        "\t\tinfluence = 10\n"
        "\t}\n"
        "\tinfluence_modifier = {\n"
        "\t\tdesc = EST_VAL_OTHER_ESTATE_IN_POWER\n"
        "\t\ttrigger = { has_any_estate_disaster_active = yes has_not_own_estate_disaster_active = { estate = jxp_estate_village_communes } }\n"
        "\t\tinfluence = -40\n"
        "\t}\n"
        "\tloyalty_modifier = { desc = EST_VAL_HIGH_STABILITY trigger = { stability = 3 } loyalty = 5 }\n"
        "\tloyalty_modifier = { desc = EST_VAL_LOW_STABILITY trigger = { NOT = { stability = 0 } } loyalty = -5 }\n"
        "\tloyalty_modifier = {\n"
        "\t\tdesc = EST_VAL_OTHER_ESTATE_IN_POWER_LOY\n"
        "\t\ttrigger = { has_any_estate_disaster_active = yes has_not_own_estate_disaster_active = { estate = jxp_estate_village_communes } }\n"
        "\t\tloyalty = -20\n"
        "\t}\n"
        + _custom_name_blocks("jxp_estate_village_communes")
        + "\tcolor = { 70 145 70 }\n"
        "\tprivileges = {\n" + privileges + "\t}\n"
        "\tagendas = {\n" + agendas + "\t}\n"
        "\tinfluence_from_dev_modifier = 1.0\n"
        "}\n"
    )


def _legacy_equivalents_for(privilege_key: str) -> tuple[str, ...]:
    return tuple(
        old
        for old, new, _estate in LEGACY_PRIVILEGE_EQUIVALENTS
        if new == privilege_key
    )


def _privilege_ai_modifiers(row: Privilege) -> tuple[str, ...]:
    """Return context-sensitive grant/revoke weights for one privilege.

    The common safety factors are intentionally followed by subject-specific
    factors.  This keeps the AI from evaluating 48 distinct bargains as one
    generic crown-land purchase while staying entirely event-driven.
    """

    modifiers = [
        "modifier = { factor = 0 is_bankrupt = yes }",
        (
            "modifier = { factor = 0.20 NOT = { crown_land_share = 25 } "
            f"NOT = {{ has_estate_privilege = {row.key} }} }}"
        ),
        (
            "modifier = { factor = 0.25 "
            f"estate_influence = {{ estate = {row.estate} influence = 70 }} "
            f"NOT = {{ has_estate_privilege = {row.key} }} }}"
        ),
        (
            f"modifier = {{ factor = 2 has_estate_privilege = {row.key} "
            f"NOT = {{ estate_loyalty = {{ estate = {row.estate} loyalty = 35 }} }} }}"
        ),
    ]

    military_benefits = {
        "manpower_recovery_speed",
        "land_forcelimit_modifier",
        "reinforce_speed",
        "discipline",
        "defensiveness",
        "fort_maintenance_modifier",
        "global_manpower_modifier",
        "naval_forcelimit_modifier",
    }
    fiscal_benefits = {
        "global_tax_modifier",
        "production_efficiency",
        "trade_efficiency",
        "interest",
        "inflation_reduction",
        "global_trade_power",
        "global_trade_goods_size_modifier",
    }
    early_institutions = {
        "kokujin_oaths",
        "chigyo_confirmation",
        "yorioya_yoriko",
        "war_levy_assessment",
        "temple_land_confirmation",
        "jinaimachi_autonomy",
        "village_tax_compacts",
        "village_militias",
    }
    late_institutions = {
        "monetised_stipends",
        "temple_credit_offices",
        "mint_management",
        "warehouse_rice_notes",
        "company_incorporation",
        "courier_houses",
        "marine_insurance",
        "public_bond_subscription",
        "commercial_courts",
        "rural_industry",
        "common_workshops",
    }
    market_institutions = {
        "free_markets",
        "town_council_autonomy",
        "guild_charters",
        "mint_management",
        "warehouse_rice_notes",
        "red_seal_trade",
        "company_incorporation",
        "courier_houses",
        "marine_insurance",
        "public_bond_subscription",
        "commercial_courts",
        "irrigation_works",
        "new_field_reclamation",
        "rural_industry",
        "common_workshops",
    }
    company_institutions = {
        "company_incorporation",
        "courier_houses",
        "marine_insurance",
        "public_bond_subscription",
        "common_workshops",
    }

    if row.benefit[0] in military_benefits:
        modifiers.append("modifier = { factor = 1.75 is_at_war = yes }")
    if row.penalty[0] in {"global_manpower_modifier", "naval_forcelimit_modifier"}:
        modifiers.append("modifier = { factor = 0.35 is_at_war = yes }")
    if row.benefit[0] in fiscal_benefits:
        modifiers.append("modifier = { factor = 1.20 monthly_income = 20 }")
    if row.penalty[0] in {
        "global_tax_modifier",
        "build_cost",
        "state_maintenance_modifier",
        "land_maintenance_modifier",
        "fort_maintenance_modifier",
        "naval_maintenance_modifier",
    }:
        modifiers.append("modifier = { factor = 0.65 num_of_loans = 3 }")
    if row.benefit == ("interest", "-0.25"):
        modifiers.append("modifier = { factor = 2.25 num_of_loans = 3 }")
    if row.penalty == ("interest", "0.25"):
        modifiers.append("modifier = { factor = 0.40 num_of_loans = 3 }")

    if row.slug in early_institutions:
        modifiers.append(
            "modifier = { factor = 1.30 OR = { current_age = age_of_discovery current_age = age_of_reformation } }"
        )
    if row.slug in late_institutions:
        modifiers.append(
            "modifier = { factor = 1.45 OR = { current_age = age_of_absolutism current_age = age_of_revolutions } }"
        )
    if row.slug in market_institutions:
        modifiers.append("modifier = { factor = 1.50 jxp_a_market_stage_at_least_2_trigger = yes }")
    if row.slug in company_institutions:
        modifiers.append("modifier = { factor = 1.60 jxp_a_company_has_at_least_1_trigger = yes }")
    if row.slug == "company_incorporation":
        modifiers.append("modifier = { factor = 1.75 has_country_flag = jxp_iface_a_company_state_route }")

    rebel_type = {
        "estate_nobles": "noble_rebels",
        "estate_church": "shinto_rebels",
        "estate_burghers": "particularist_rebels",
        "jxp_estate_village_communes": "anti_tax_rebels",
    }[row.estate]
    if row.benefit[0] in {"global_unrest", "stability_cost_modifier"}:
        modifiers.append(
            "modifier = { factor = 1.80 OR = { NOT = { stability = 0 } "
            f"has_spawned_rebels = {rebel_type} has_any_estate_disaster_active = yes }} }}"
        )
    elif row.penalty[0] == "global_unrest":
        modifiers.append(
            "modifier = { factor = 0.35 OR = { NOT = { stability = 0 } "
            f"has_spawned_rebels = {rebel_type} has_any_estate_disaster_active = yes }} }}"
        )

    if row.estate == "estate_church":
        modifiers.append(
            "modifier = { factor = 1.25 OR = { religion = shinto "
            "jxp_a_96_buddhist_exact_route_trigger = yes jxp_final_state_ikko_trigger = yes } }"
        )
    if row.slug in {"overseas_service_rolls", "overseas_dharma", "red_seal_trade", "overseas_service_exemption"}:
        modifiers.append(
            "modifier = { factor = 1.50 OR = { jxp_final_state_open_trigger = yes "
            "jxp_final_state_wokou_trigger = yes has_country_flag = jxp_iface_overseas_charter_ready } }"
        )
    if row.slug == "fudai_magistrates":
        modifiers.append(
            "modifier = { factor = 2 has_government_attribute = jxp_toyotomi_regents_council "
            f"NOT = {{ has_estate_privilege = {row.key} }} }}"
        )

    return tuple(modifiers)


def render_privileges() -> str:
    blocks = ["# Generated by build_estates.py. Do not edit.\n"]
    for row in PRIVILEGES:
        legacy_equivalents = _legacy_equivalents_for(row.key)
        legacy_validity = ""
        if legacy_equivalents:
            absence = " ".join(
                f"NOT = {{ has_estate_privilege = {old} }}"
                for old in legacy_equivalents
            )
            legacy_validity = (
                "\n\t\tOR = {\n"
                f"\t\t\thas_estate_privilege = {row.key}\n"
                f"\t\t\tAND = {{ {absence} }}\n"
                "\t\t}"
            )
        valid = (
            f"jxp_is_japanese_polity_trigger = yes\n\t\t{row.valid_extra}"
            f"{legacy_validity}"
        )
        legacy_guards = "".join(
            f"\t\tNOT = {{ has_estate_privilege = {old} }}\n"
            for old in legacy_equivalents
        )
        ai_modifiers = "".join(f"\t\t{line}\n" for line in _privilege_ai_modifiers(row))
        blocks.append(
            f"{row.key} = {{\n"
            f"\ticon = {row.icon}\n"
            f"\tland_share = {row.land_share}\n"
            "\tmax_absolutism = -5\n"
            f"\tloyalty = {row.loyalty}\n"
            f"\tinfluence = {row.influence}\n"
            f"\tis_valid = {{\n\t\t{valid}\n\t}}\n"
            "\tcan_select = {\n"
            "\t\tis_bankrupt = no\n"
            "\t\tcrown_land_share = 15\n"
            f"{legacy_guards}"
            "\t}\n"
            "\tcan_revoke = { always = yes }\n"
            "\ton_granted = {}\n"
            "\ton_revoked = {}\n"
            "\ton_invalid = {}\n"
            f"\tbenefits = {{ {row.benefit[0]} = {row.benefit[1]} }}\n"
            f"\tpenalties = {{ {row.penalty[0]} = {row.penalty[1]} }}\n"
            "\tcooldown_years = 10\n"
            "\tai_will_do = {\n"
            "\t\tfactor = 1\n"
            f"{ai_modifiers}"
            "\t}\n"
            "}\n"
        )
    return "\n".join(blocks)


def render_agendas() -> str:
    blocks = ["# Generated by build_estates.py. Do not edit.\n"]
    for row in AGENDAS:
        blocks.append(
            f"{row.key} = {{\n"
            "\tmax_days_active = 3650\n"
            "\tcan_select = {\n"
            "\t\tjxp_is_japanese_polity_trigger = yes\n"
            "\t\tis_bankrupt = no\n"
            "\t\tOR = {\n"
            f"\t\t\thas_estate_agenda_auto_completion = {{ estate = {row.estate} }}\n"
            f"\t\t\tNOT = {{ {row.requirement} }}\n"
            "\t\t}\n"
            "\t}\n"
            "\tselection_weight = {\n"
            "\t\tfactor = 1\n"
            "\t\tmodifier = { factor = 0.50 is_at_war = yes }\n"
            "\t}\n"
            "\ttask_requirements = {\n"
            f"\t\tif = {{ limit = {{ has_estate_agenda_auto_completion = {{ estate = {row.estate} }} }} has_estate_agenda_auto_completion = {{ estate = {row.estate} }} }}\n"
            f"\t\telse = {{ {row.requirement} }}\n"
            "\t}\n"
            "\ttask_completed_effect = {\n"
            f"\t\ton_completed_agenda_effect = {{ estate = {row.estate} }}\n"
            f"\t\tadd_estate_loyalty = {{ estate = {row.estate} loyalty = 10 }}\n"
            f"\t\tadd_{row.power}_power = 15\n"
            "\t}\n"
            "\tfail_if = { is_bankrupt = yes }\n"
            "\tfailing_effect = {\n"
            "\t\ton_failed_agenda_effect = yes\n"
            "\t\tclr_auto_complete_flag = yes\n"
            f"\t\tadd_estate_loyalty_modifier = {{ estate = {row.estate} desc = EST_VAL_AGENDA_DENIED loyalty = -5 duration = 3650 }}\n"
            "\t}\n"
            "\tinvalid_trigger = { NOT = { jxp_is_japanese_polity_trigger = yes } }\n"
            "\ton_invalid = { clr_auto_complete_flag = yes }\n"
            "}\n"
        )
    return "\n".join(blocks)


INTERACTIONS = (
    ("nobles", "estate_nobles", "jxp_estates.1", "召开家中评定", "召集谱代、外样与奉行同席，裁定军役和知行。", "LAND_MILITARY_eventPicture"),
    ("church", "estate_church", "jxp_estates.2", "召开宗门公议", "命诸寺社与宗门代表入席，在兵火以前陈述争端。", "RELIGIOUS_CONVERSION_eventPicture"),
    ("burghers", "estate_burghers", "jxp_estates.3", "召开町众评议", "召集会合众、问屋与豪商，议定国用和航路。", "MERCHANTS_TALKING_eventPicture"),
    ("villages", "jxp_estate_village_communes", "jxp_estates.4", "召开惣村评定", "令惣代、庄屋与百姓代表陈述年贡、水利和赈济。", "COURT_eventPicture"),
)


VISIBLE_STATE_LOCALISATION = (
    (
        "jxp_a_nobles_estate_interaction_recent",
        "近期已召开家中评定",
        "武家奉公众的前议仍在施行，五年期满以前不得重复召开家中评定。",
    ),
    (
        "jxp_a_church_estate_interaction_recent",
        "近期已召开宗门公议",
        "寺社宗门的前议仍在施行，五年期满以前不得重复召开宗门公议。",
    ),
    (
        "jxp_a_burghers_estate_interaction_recent",
        "近期已召开町众评议",
        "町众豪商的前议仍在施行，五年期满以前不得重复召开町众评议。",
    ),
    (
        "jxp_a_villages_estate_interaction_recent",
        "近期已召开惣村评定",
        "百姓惣村的前议仍在施行，五年期满以前不得重复召开惣村评定。",
    ),
)


def _interaction_decision_ai(short: str, estate: str) -> tuple[str, ...]:
    common = (
        "modifier = { factor = 0 is_bankrupt = yes }",
        f"modifier = {{ factor = 2 NOT = {{ estate_loyalty = {{ estate = {estate} loyalty = 35 }} }} }}",
    )
    contextual = {
        "nobles": (
            "modifier = { factor = 1.75 is_at_war = yes }",
            "modifier = { factor = 0.55 num_of_loans = 3 }",
            "modifier = { factor = 1.35 OR = { current_age = age_of_discovery current_age = age_of_reformation } }",
            "modifier = { factor = 1.75 OR = { NOT = { stability = 0 } has_spawned_rebels = noble_rebels } }",
            "modifier = { factor = 2 has_government_attribute = jxp_toyotomi_regents_council }",
        ),
        "church": (
            "modifier = { factor = 0.65 is_at_war = yes }",
            "modifier = { factor = 1.75 OR = { NOT = { stability = 0 } has_spawned_rebels = shinto_rebels } }",
            "modifier = { factor = 1.50 OR = { religion = shinto jxp_a_96_buddhist_exact_route_trigger = yes jxp_final_state_ikko_trigger = yes } }",
            "modifier = { factor = 1.30 OR = { current_age = age_of_discovery current_age = age_of_reformation } }",
        ),
        "burghers": (
            "modifier = { factor = 1.60 num_of_loans = 3 }",
            "modifier = { factor = 1.25 monthly_income = 20 }",
            "modifier = { factor = 1.75 jxp_a_market_stage_at_least_2_trigger = yes }",
            "modifier = { factor = 1.50 jxp_a_company_has_at_least_1_trigger = yes }",
            "modifier = { factor = 1.35 OR = { current_age = age_of_absolutism current_age = age_of_revolutions } }",
            "modifier = { factor = 1.40 has_spawned_rebels = particularist_rebels }",
        ),
        "villages": (
            "modifier = { factor = 0.70 is_at_war = yes }",
            "modifier = { factor = 1.75 OR = { war_exhaustion = 2 NOT = { stability = 0 } has_spawned_rebels = anti_tax_rebels } }",
            "modifier = { factor = 0.60 num_of_loans = 3 }",
            "modifier = { factor = 1.25 jxp_a_market_stage_at_least_2_trigger = yes }",
            "modifier = { factor = 1.25 OR = { current_age = age_of_discovery current_age = age_of_reformation } }",
        ),
    }[short]
    return common + contextual


def render_decisions() -> str:
    rows = ["# Generated by build_estates.py. Do not edit.", "country_decisions = {"]
    power_by = {"nobles": "mil", "church": "adm", "burghers": "dip", "villages": "adm"}
    for short, estate, event_id, _name, _desc, _picture in INTERACTIONS:
        key = f"jxp_a_convene_{short}_estate_council"
        flag = f"jxp_a_{short}_estate_interaction_recent"
        power = power_by[short]
        ai_modifiers = _interaction_decision_ai(short, estate)
        rows.extend((
            f"\t{key} = {{",
            "\t\tmajor = no",
            "\t\tpotential = { normal_or_historical_nations = yes jxp_is_japanese_polity_trigger = yes " + f"has_estate = {estate}" + " }",
            "\t\tallow = {",
            "\t\t\tis_bankrupt = no",
            f"\t\t\t{power}_power = 50",
            f"\t\t\tOR = {{ NOT = {{ has_country_flag = {flag} }} had_country_flag = {{ flag = {flag} days = 1825 }} }}",
            "\t\t}",
            f"\t\teffect = {{ country_event = {{ id = {event_id} }} }}",
            "\t\tai_will_do = {",
            "\t\t\tfactor = 0.5",
            *(_indent(line, 3) for line in ai_modifiers),
            "\t\t}",
            "\t}",
            "",
        ))
    rows.append("}")
    return "\n".join(rows) + "\n"


def _interaction_options(short: str, estate: str) -> tuple[tuple[str, str], ...]:
    flag = f"jxp_a_{short}_estate_interaction_recent"
    common = f"set_country_flag = {flag}"
    options = {
        "nobles": (
            ("a", f"add_mil_power = -50\nadd_prestige = -5\nadd_estate_loyalty = {{ estate = {estate} loyalty = 10 }}\nadd_estate_influence_modifier = {{ estate = {estate} desc = jxp_a_estate_val_recent_council influence = 5 duration = 1825 }}\n{common}"),
            ("b", f"add_estate_loyalty = {{ estate = {estate} loyalty = -10 }}\nadd_yearly_manpower = 1\nadd_war_exhaustion = 1\n{common}"),
            ("c", f"add_adm_power = -50\nchange_estate_land_share = {{ estate = {estate} share = 2 }}\nadd_estate_loyalty = {{ estate = {estate} loyalty = 5 }}\n{common}"),
        ),
        "church": (
            ("a", f"add_adm_power = -50\nadd_prestige = 5\nadd_estate_loyalty = {{ estate = {estate} loyalty = 10 }}\n{common}"),
            ("b", f"add_years_of_income = -0.25\nevery_owned_province = {{ limit = {{ devastation = 1 }} add_devastation = -2 }}\nadd_estate_loyalty = {{ estate = {estate} loyalty = 10 }}\n{common}"),
            ("c", f"add_adm_power = 50\nchange_estate_land_share = {{ estate = {estate} share = -2 }}\nadd_estate_loyalty = {{ estate = {estate} loyalty = -10 }}\n{common}"),
        ),
        "burghers": (
            ("a", f"add_inflation = 0.5\nadd_years_of_income = 0.5\nadd_estate_loyalty = {{ estate = {estate} loyalty = 5 }}\nadd_estate_influence_modifier = {{ estate = {estate} desc = jxp_a_estate_val_recent_council influence = 5 duration = 1825 }}\n{common}"),
            ("b", f"add_dip_power = -50\nadd_mercantilism = 1\nadd_estate_loyalty = {{ estate = {estate} loyalty = 10 }}\n{common}"),
            ("c", f"add_dip_power = -50\nadd_navy_tradition = 5\nadd_war_exhaustion = -0.5\n{common}"),
        ),
        "villages": (
            ("a", f"add_adm_power = -50\nrandom_owned_province = {{ add_base_production = 1 }}\nadd_estate_loyalty = {{ estate = {estate} loyalty = 5 }}\n{common}"),
            ("b", f"add_years_of_income = -0.25\nadd_inflation = -0.25\nadd_estate_loyalty = {{ estate = {estate} loyalty = 10 }}\n{common}"),
            ("c", f"add_years_of_income = -0.25\nadd_war_exhaustion = -0.5\nadd_estate_loyalty = {{ estate = {estate} loyalty = 15 }}\nadd_estate_influence_modifier = {{ estate = {estate} desc = jxp_a_estate_val_recent_council influence = 5 duration = 1825 }}\n{common}"),
        ),
    }
    return options[short]


def _interaction_option_ai(short: str, suffix: str) -> tuple[str, ...]:
    rows = {
        ("nobles", "a"): (
            "factor = 1",
            "modifier = { factor = 2 has_government_attribute = jxp_toyotomi_regents_council }",
            "modifier = { factor = 1.30 is_at_war = no }",
        ),
        ("nobles", "b"): (
            "factor = 0.70",
            "modifier = { factor = 2 is_at_war = yes }",
            "modifier = { factor = 2 NOT = { manpower_percentage = 0.5 } }",
            "modifier = { factor = 0.35 war_exhaustion = 4 }",
        ),
        ("nobles", "c"): (
            "factor = 0.50",
            "modifier = { factor = 2 crown_land_share = 40 }",
            "modifier = { factor = 1.50 has_government_attribute = jxp_toyotomi_regents_council }",
            "modifier = { factor = 1.30 current_age = age_of_discovery }",
        ),
        ("church", "a"): (
            "factor = 1",
            "modifier = { factor = 1.80 OR = { religion = shinto jxp_a_96_buddhist_exact_route_trigger = yes jxp_final_state_ikko_trigger = yes } }",
            "modifier = { factor = 1.50 NOT = { stability = 0 } }",
        ),
        ("church", "b"): (
            "factor = 0.80",
            "modifier = { factor = 3 any_owned_province = { devastation = 10 } }",
            "modifier = { factor = 1.60 war_exhaustion = 2 }",
            "modifier = { factor = 0.40 num_of_loans = 3 }",
        ),
        ("church", "c"): (
            "factor = 0.40",
            "modifier = { factor = 2 OR = { current_age = age_of_absolutism current_age = age_of_revolutions } }",
            "modifier = { factor = 1.50 estate_loyalty = { estate = estate_church loyalty = 60 } }",
            "modifier = { factor = 0.35 NOT = { stability = 0 } }",
        ),
        ("burghers", "a"): (
            "factor = 0.60",
            "modifier = { factor = 2 num_of_loans = 3 }",
            "modifier = { factor = 1.50 NOT = { monthly_income = 20 } }",
            "modifier = { factor = 0.25 inflation = 5 }",
        ),
        ("burghers", "b"): (
            "factor = 1",
            "modifier = { factor = 2 jxp_a_market_stage_at_least_2_trigger = yes }",
            "modifier = { factor = 1.50 jxp_a_company_has_at_least_1_trigger = yes }",
            "modifier = { factor = 1.50 has_country_flag = jxp_iface_a_company_state_route }",
        ),
        ("burghers", "c"): (
            "factor = 0.60",
            "modifier = { factor = 2 is_at_war = yes }",
            "modifier = { factor = 2 war_exhaustion = 2 }",
            "modifier = { factor = 1.50 OR = { jxp_final_state_open_trigger = yes jxp_final_state_wokou_trigger = yes } }",
        ),
        ("villages", "a"): (
            "factor = 1",
            "modifier = { factor = 1.50 is_at_war = no }",
            "modifier = { factor = 1.50 jxp_a_market_stage_at_least_2_trigger = yes }",
            "modifier = { factor = 1.25 OR = { current_age = age_of_discovery current_age = age_of_reformation } }",
        ),
        ("villages", "b"): (
            "factor = 0.80",
            "modifier = { factor = 1.75 inflation = 2 }",
            "modifier = { factor = 0.40 num_of_loans = 3 }",
            "modifier = { factor = 1.30 has_spawned_rebels = anti_tax_rebels }",
        ),
        ("villages", "c"): (
            "factor = 0.80",
            "modifier = { factor = 2.50 war_exhaustion = 2 }",
            "modifier = { factor = 2 OR = { NOT = { stability = 0 } has_spawned_rebels = anti_tax_rebels } }",
            "modifier = { factor = 0.50 num_of_loans = 3 }",
        ),
    }
    if suffix == "z":
        return (
            "factor = 0.20",
            "modifier = { factor = 4 num_of_loans = 5 }",
            "modifier = { factor = 2 is_at_war = yes }",
        )
    return rows[(short, suffix)]


def render_interaction_events() -> str:
    rows = ["# Generated by build_estates.py. Do not edit.", "namespace = jxp_estates", ""]
    for short, estate, event_id, _name, _desc, picture in INTERACTIONS:
        rows.extend((
            "country_event = {",
            f"\tid = {event_id}",
            f"\ttitle = {event_id}.t",
            f"\tdesc = {event_id}.d",
            f"\tpicture = {picture}",
            "\tis_triggered_only = yes",
            "",
        ))
        for suffix, effects in _interaction_options(short, estate):
            option_ai = _interaction_option_ai(short, suffix)
            power_trigger = {
                ("nobles", "a"): "mil_power = 50",
                ("nobles", "b"): "always = yes",
                ("nobles", "c"): "adm_power = 50",
                ("church", "a"): "adm_power = 50",
                ("church", "b"): "treasury = 50",
                ("church", "c"): "always = yes",
                ("burghers", "a"): "always = yes",
                ("burghers", "b"): "dip_power = 50",
                ("burghers", "c"): "dip_power = 50",
                ("villages", "a"): "adm_power = 50",
                ("villages", "b"): "treasury = 50",
                ("villages", "c"): "treasury = 50",
            }[(short, suffix)]
            rows.extend((
                "\toption = {",
                f"\t\tname = {event_id}.{suffix}",
                f"\t\ttrigger = {{ {power_trigger} }}",
                _indent(effects, 2),
                "\t\tai_chance = {",
                *(_indent(line, 3) for line in option_ai),
                "\t\t}",
                "\t}",
            ))
        fallback_ai = _interaction_option_ai(short, "z")
        rows.extend((
            "\toption = {",
            f"\t\tname = {event_id}.z",
            "\t\tai_chance = {",
            *(_indent(line, 3) for line in fallback_ai),
            "\t\t}",
            "\t}",
            "}",
            "",
        ))
    return "\n".join(rows)


def render_estate_effects() -> str:
    rows = ["# Generated by build_estates.py. Do not edit.", ""]
    rows.append("jxp_a_clear_japanese_estates_effect = {")
    for privilege in PRIVILEGES:
        rows.append(f"\tif = {{ limit = {{ has_estate_privilege = {privilege.key} }} remove_estate_privilege = {privilege.key} }}")
    for short, *_rest in INTERACTIONS:
        rows.append(f"\tclr_country_flag = jxp_a_{short}_estate_interaction_recent")
    for transition_flag in PRIVILEGE_TRANSITION_FLAGS.values():
        rows.append(f"\tclr_country_flag = {transition_flag}")
    rows.extend((
        "\tclr_country_flag = jxp_a_estate_privilege_migration_v2",
        "\tclr_country_flag = jxp_iface_a_estates_ready",
        "\tclr_country_flag = jxp_estate_village_communes_present_agenda",
        "\tclr_country_flag = auto_complete_estate_agenda_jxp_estate_village_communes",
        "}",
        "",
        "# Preserve semantically equivalent vanilla privileges from old saves.",
        "# If both versions were serialized, remove only the JXP duplicate and",
        "# bridge its lost loyalty equilibrium once per privilege per five years.",
        "jxp_a_clear_legacy_duplicate_japanese_estate_privileges_effect = {",
    ))
    privilege_by_key = {row.key: row for row in PRIVILEGES}
    for old, new, estate in LEGACY_PRIVILEGE_EQUIVALENTS:
        row = privilege_by_key[new]
        transition_flag = PRIVILEGE_TRANSITION_FLAGS[new]
        loyalty_bridge = max(0, round(float(row.loyalty) * 100))
        rows.extend((
            "\tif = {",
            f"\t\tlimit = {{ has_estate_privilege = {old} has_estate_privilege = {new} }}",
            f"\t\tremove_estate_privilege = {new}",
        ))
        if loyalty_bridge:
            rows.extend((
                "\t\tif = {",
                "\t\t\tlimit = {",
                f"\t\t\t\thas_estate = {estate}",
                "\t\t\t\tOR = {",
                f"\t\t\t\t\tNOT = {{ has_country_flag = {transition_flag} }}",
                f"\t\t\t\t\thad_country_flag = {{ flag = {transition_flag} days = 1825 }}",
                "\t\t\t\t}",
                "\t\t\t}",
                f"\t\t\tadd_estate_loyalty_modifier = {{ estate = {estate} desc = jxp_a_estate_val_privilege_transition loyalty = {loyalty_bridge} duration = 1825 }}",
                f"\t\t\tclr_country_flag = {transition_flag}",
                f"\t\t\tset_country_flag = {transition_flag}",
                "\t\t}",
            ))
        rows.append("\t}")
    duplicate_conditions = " ".join(
        f"AND = {{ has_estate_privilege = {old} has_estate_privilege = {new} }}"
        for old, new, _estate in LEGACY_PRIVILEGE_EQUIVALENTS
    )
    rows.extend((
        "}",
        "",
        "# One-shot transactional schema migration.  The flag is committed only",
        "# after every legacy/JXP duplicate has actually disappeared; interrupted",
        "# startup reconciliation therefore retries without duplicating rewards.",
        "jxp_a_migrate_legacy_estate_privileges_effect = {",
        "\tif = {",
        "\t\tlimit = { NOT = { has_country_flag = jxp_a_estate_privilege_migration_v2 } }",
        "\t\tjxp_a_clear_legacy_duplicate_japanese_estate_privileges_effect = yes",
        "\t\tif = {",
        f"\t\t\tlimit = {{ NOT = {{ OR = {{ {duplicate_conditions} }} }} }}",
        "\t\t\tset_country_flag = jxp_a_estate_privilege_migration_v2",
        "\t\t}",
        "\t}",
        "}",
        "",
        "jxp_a_clear_illegal_japanese_estate_privileges_effect = {",
        "\tjxp_a_clear_legacy_duplicate_japanese_estate_privileges_effect = yes",
    ))
    for privilege in PRIVILEGES:
        if privilege.valid_extra == "always = yes":
            continue
        rows.extend((
            "\tif = {",
            f"\t\tlimit = {{ has_estate_privilege = {privilege.key} NOT = {{ AND = {{ jxp_is_japanese_polity_trigger = yes {privilege.valid_extra} }} }} }}",
            f"\t\tremove_estate_privilege = {privilege.key}",
        ))
        loyalty_bridge = max(0, round(float(privilege.loyalty) * 100))
        if loyalty_bridge:
            transition_flag = PRIVILEGE_TRANSITION_FLAGS[privilege.key]
            rows.extend((
                "\t\tif = {",
                "\t\t\tlimit = {",
                f"\t\t\t\thas_estate = {privilege.estate}",
                "\t\t\t\tOR = {",
                f"\t\t\t\t\tNOT = {{ has_country_flag = {transition_flag} }}",
                f"\t\t\t\t\thad_country_flag = {{ flag = {transition_flag} days = 1825 }}",
                "\t\t\t\t}",
                "\t\t\t}",
                f"\t\t\tadd_estate_loyalty_modifier = {{ estate = {privilege.estate} desc = jxp_a_estate_val_privilege_transition loyalty = {loyalty_bridge} duration = 1825 }}",
                f"\t\t\tclr_country_flag = {transition_flag}",
                f"\t\t\tset_country_flag = {transition_flag}",
                "\t\t}",
            ))
        rows.append("\t}")
    rows.extend((
        "}",
        "",
        "jxp_a_reconcile_japanese_estates_effect = {",
        "\tif = {",
        "\t\tlimit = { jxp_is_japanese_polity_trigger = yes }",
        "\t\tjxp_a_migrate_legacy_estate_privileges_effect = yes",
        "\t\tjxp_a_clear_illegal_japanese_estate_privileges_effect = yes",
        "\t\tset_country_flag = jxp_iface_a_estates_ready",
        "\t}",
        "\telse = { jxp_a_clear_japanese_estates_effect = yes }",
        "}",
        "",
        "# Public route-transition alias required by the socioeconomic contract.",
        "# The delegated reconcile is itself idempotent and owns all cleanup.",
        "jxp_a_reconcile_estates_for_route = {",
        "\tjxp_a_reconcile_japanese_estates_effect = yes",
        "}",
        "",
    ))
    return "\n".join(rows)


def render_localisation() -> str:
    lines = ["l_english:"]
    lines.extend((
        _loc_line("jxp_estate_village_communes", "百姓惣村"),
        _loc_line("jxp_estate_village_communes_desc", "耕作者、庄屋、惣代与村落共同体。他们承担年贡、水利、乡役与粮食生产，也会在负担失衡时以德政请求和惣动迫使国家回应。"),
        _loc_line("jxp_estate_village_communes_ownership", "百姓惣村所掌土地"),
        _loc_line("jxp_a_estate_val_large_rural_realm", "广土众村"),
        _loc_line("jxp_a_estate_val_recent_council", "近期获准参与评定"),
        _loc_line("jxp_a_estate_val_privilege_transition", "旧权改制的五年忠诚过渡"),
    ))
    for key, title, desc in VISIBLE_STATE_LOCALISATION:
        lines.append(_loc_line(key, title))
        lines.append(_loc_line(f"{key}_desc", desc))
    for state, _trigger, names in NAME_MATRIX:
        for estate, value in zip(ESTATE_ORDER, names, strict=True):
            lines.append(_loc_line(f"jxp_a_estate_name_{ESTATE_SHORT[estate]}_{state}", value))
    for row in PRIVILEGES:
        lines.append(_loc_line(row.key, row.name))
        lines.append(_loc_line(f"{row.key}_desc", row.desc))
    for row in AGENDAS:
        lines.append(_loc_line(row.key, row.name))
        lines.append(_loc_line(f"{row.key}_desc", row.desc))
    for short, _estate, event_id, name, desc, _picture in INTERACTIONS:
        decision = f"jxp_a_convene_{short}_estate_council"
        lines.append(_loc_line(f"{decision}_title", name))
        lines.append(_loc_line(f"{decision}_desc", desc + "此项评定经由决议开启，每五年方可再次举行，并非原生阶层面板上的无代价按钮。"))
        lines.append(_loc_line(f"{event_id}.t", name))
        lines.append(_loc_line(f"{event_id}.d", desc + "席上诸众各有所求；无论允准哪一议，都须付出国用、威望或阶层均衡的代价。"))
    event_options = {
        "jxp_estates.1": ("以军略换取重臣背书", "追加军役，先应眼前之急", "重申知行，以土地换取服从"),
        "jxp_estates.2": ("准其公开宗论", "命寺社开仓施药", "登记寺领，收回部分免役"),
        "jxp_estates.3": ("发行短期公债", "议定商法与市舶章程", "组织廻船护运"),
        "jxp_estates.4": ("发动共同普请", "开仓平粜", "减免年贡与军役"),
    }
    for event_id, values in event_options.items():
        for suffix, value in zip(("a", "b", "c"), values, strict=True):
            lines.append(_loc_line(f"{event_id}.{suffix}", value))
        lines.append(_loc_line(f"{event_id}.z", "暂不更动旧例"))
    lines.extend((
        _loc_line("estate_privileges_and_agendas_events.3.q", "听取[Root.GetJxpVillageCommunesName]的议程"),
        _loc_line("estate_privileges_and_agendas_events.7.q", "仅从[Root.GetJxpVillageCommunesName]收回土地"),
    ))
    return "\n".join(lines) + "\n"


def render_customisable_localisation() -> str:
    # Keep the two exact-override event options aligned with the estate panel's
    # priority-ordered dynamic name rather than falling back to a static label.
    rows = [
        "# Generated by build_estates.py. Do not edit.",
        "defined_text = {",
        "\tname = GetJxpVillageCommunesName",
        "\trandom = no",
    ]
    for state, trigger, _names in NAME_MATRIX:
        rows.append(
            "\ttext = { "
            f"localisation_key = jxp_a_estate_name_villages_{state} "
            f"trigger = {{ {trigger} }} "
            "}"
        )
    rows.extend((
        "\ttext = { localisation_key = jxp_estate_village_communes trigger = { always = yes } }",
        "}",
        "",
    ))
    return "\n".join(rows)


def validate_design() -> None:
    if len(PRIVILEGES) != 48:
        raise ValueError(f"expected 48 privileges, found {len(PRIVILEGES)}")
    if Counter(row.estate for row in PRIVILEGES) != Counter({estate: 12 for estate in ESTATE_ORDER}):
        raise ValueError("each estate must own exactly 12 JXP privileges")
    if len({row.key for row in PRIVILEGES}) != len(PRIVILEGES):
        raise ValueError("duplicate privilege key")
    if len(AGENDAS) != 40:
        raise ValueError(f"expected 40 agendas, found {len(AGENDAS)}")
    if Counter(row.estate for row in AGENDAS) != Counter({estate: 10 for estate in ESTATE_ORDER}):
        raise ValueError("each estate must own exactly 10 JXP agendas")
    if len({row.key for row in AGENDAS}) != len(AGENDAS):
        raise ValueError("duplicate agenda key")
    if len(NAME_MATRIX) != 15:
        raise ValueError("dynamic estate name matrix must cover 15 Japanese profiles")
    privilege_keys = {row.key: row.estate for row in PRIVILEGES}
    old_keys = [old for old, _new, _estate in LEGACY_PRIVILEGE_EQUIVALENTS]
    new_keys = [new for _old, new, _estate in LEGACY_PRIVILEGE_EQUIVALENTS]
    if len(set(old_keys)) != len(old_keys) or len(set(new_keys)) != len(new_keys):
        raise ValueError("legacy privilege mappings must be one-to-one")
    for _old, new, estate in LEGACY_PRIVILEGE_EQUIVALENTS:
        if privilege_keys.get(new) != estate:
            raise ValueError(f"legacy privilege mapping has wrong estate: {new}")
        row = next(item for item in PRIVILEGES if item.key == new)
        if row.valid_extra != "always = yes":
            raise ValueError(f"legacy equivalent must remain broadly valid: {new}")


def render_outputs(game_root: Path) -> dict[Path, bytes]:
    validate_design()
    vanilla: dict[Path, str] = {}
    for relative, expected_digest in VANILLA_PINS.items():
        source = game_root / relative
        if not source.is_file():
            raise ValueError(f"missing pinned vanilla source: {source}")
        payload = source.read_bytes()
        actual = sha256(payload).hexdigest().upper()
        if actual != expected_digest:
            raise ValueError(f"vanilla source drift: {relative.as_posix()} -> {actual}")
        # Several pinned vanilla files retain legacy single-byte comments.
        # latin-1 is used only as a byte-preserving transform for the exact
        # overrides; every injected token is ASCII and round-trips exactly.
        vanilla[relative] = payload.decode("latin-1")

    outputs: dict[Path, bytes] = {}
    for estate, relative in ESTATE_FILES.items():
        outputs[MAIN_ROOT / relative] = _build_estate_override(
            vanilla[relative], estate, VANILLA_PINS[relative]
        ).encode("latin-1")
    event_relative = Path("events/EstatePrivilegesAndAgendasEvents.txt")
    outputs[MAIN_ROOT / event_relative] = _build_estate_event_override(
        vanilla[event_relative], VANILLA_PINS[event_relative]
    ).encode("latin-1")
    helper_relative = Path("common/scripted_effects/01_scripted_effects_for_estates.txt")
    outputs[MAIN_ROOT / helper_relative] = _build_estate_helper_override(
        vanilla[helper_relative], VANILLA_PINS[helper_relative]
    ).encode("latin-1")

    source = render_localisation()
    escape = _escape_module()
    outputs.update({
        MAIN_ROOT / "common/estates/jxp_a_110_japanese_estates.txt": render_custom_estate().encode("utf-8"),
        MAIN_ROOT / "common/estate_privileges/jxp_a_110_japanese_privileges.txt": render_privileges().encode("utf-8"),
        MAIN_ROOT / "common/estate_agendas/jxp_a_110_japanese_agendas.txt": render_agendas().encode("utf-8"),
        MAIN_ROOT / "common/scripted_effects/jxp_a_110_estate_effects.txt": render_estate_effects().encode("utf-8"),
        MAIN_ROOT / "customizable_localization/jxp_a_110_estate_names.txt": render_customisable_localisation().encode("utf-8"),
        MAIN_ROOT / "decisions/jxp_a_110_estate_interactions.txt": render_decisions().encode("utf-8"),
        MAIN_ROOT / "events/jxp_a_110_estate_interactions.txt": render_interaction_events().encode("utf-8"),
        MAIN_ROOT / "localisation_source/jxp_a_110_estates_l_english_utf8_source.yml": source.encode("utf-8"),
        MAIN_ROOT / "localisation/jxp_a_110_estates_l_english.yml": escape.escape_text(source).encode("utf-8-sig"),
    })
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--mod-root", type=Path, default=MAIN_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    canonical_outputs = render_outputs(args.game_root)
    outputs = {
        args.mod_root / path.relative_to(MAIN_ROOT): payload
        for path, payload in canonical_outputs.items()
    }
    drift = []
    for path, payload in outputs.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != payload:
                drift.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        print(f"WROTE {path}")

    summary = {
        "schema": "jxp_a_estates/v1",
        "mode": "check" if args.check else "write",
        "outputs": len(outputs),
        "privileges": len(PRIVILEGES),
        "agendas": len(AGENDAS),
        "dynamic_name_profiles": len(NAME_MATRIX),
        "drift": [path.as_posix() for path in drift],
        "output_sha256": {
            path.relative_to(args.mod_root).as_posix(): sha256(payload).hexdigest()
            for path, payload in sorted(outputs.items())
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
