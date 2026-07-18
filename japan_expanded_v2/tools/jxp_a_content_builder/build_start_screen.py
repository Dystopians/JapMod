#!/usr/bin/env python3
"""Generate the JXP Japanese start-screen chronicle for EU4 1.37.5.

The vanilla start screen exposes nine customizable-localisation functions.  We
wrap those functions under unique JXP names, preserve the vanilla result for
non-Japanese countries, and compose Japanese text from one house chronicle,
one current-age chronicle, and one government-role chronicle.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
MAIN_ROOT = SCRIPT_DIR.parents[1]
REPO_ROOT = MAIN_ROOT.parent
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
PLAN_PATH = SCRIPT_DIR / "daimyo_depth_plan.json"
ESCAPE_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "eu4-modding"
    / "scripts"
    / "escape_eu4_special_localisation.py"
)

CUSTOMISABLE_PATH = (
    MAIN_ROOT / "customizable_localization" / "jxp_a_98_start_screen.txt"
)
SOURCE_PATH = (
    MAIN_ROOT
    / "localisation_source"
    / "jxp_a_98_start_screen_l_english_utf8_source.yml"
)
ACTIVE_PATH = MAIN_ROOT / "localisation" / "jxp_a_98_start_screen_l_english.yml"

VANILLA_CUSTOMISABLE_RELATIVE = Path("customizable_localization/00_start_screen.txt")
VANILLA_LOCALISATION_RELATIVE = Path("localisation/startup_screen_l_english.yml")
PINNED_VANILLA_CUSTOMISABLE_SHA256 = (
    "ece24874ed6214971a6e34c46fdaee4f9a782c15c43a62b865bc05df9ae36c21"
)
PINNED_VANILLA_LOCALISATION_SHA256 = (
    "5f852385d191fee6f6b1baf0566e4cb90af22e88381564298f3251acefb7bc45"
)

UI_FIELDS = (
    ("START_SCREEN_TITLE", "JxpStartScreenTitle", "StartScreenTitle", "title"),
    (
        "START_SCREEN_UP_LEFT_TITLE",
        "JxpStartScreenUpLeftTitle",
        "StartScreenUpLeftTitle",
        "up_left_title",
    ),
    (
        "START_SCREEN_UP_RIGHT_TITLE",
        "JxpStartScreenUpRightTitle",
        "StartScreenUpRightTitle",
        "up_right_title",
    ),
    (
        "START_SCREEN_DOWN_LEFT_TITLE",
        "JxpStartScreenDownLeftTitle",
        "StartScreenDownLeftTitle",
        "down_left_title",
    ),
    (
        "START_SCREEN_DOWN_RIGHT_TITLE",
        "JxpStartScreenDownRightTitle",
        "StartScreenDownRightTitle",
        "down_right_title",
    ),
    (
        "START_SCREEN_UP_LEFT_DESC",
        "JxpStartScreenUpLeftDesc",
        "StartScreenUpLeftDesc",
        "up_left_desc",
    ),
    (
        "START_SCREEN_UP_RIGHT_DESC",
        "JxpStartScreenUpRightDesc",
        "StartScreenUpRightDesc",
        "up_right_desc",
    ),
    (
        "START_SCREEN_DOWN_LEFT_DESC",
        "JxpStartScreenDownLeftDesc",
        "StartScreenDownLeftDesc",
        "down_left_desc",
    ),
    (
        "START_SCREEN_DOWN_RIGHT_DESC",
        "JxpStartScreenDownRightDesc",
        "StartScreenDownRightDesc",
        "down_right_desc",
    ),
)

DAIMYO_REFORM_TRIGGER = (
    "OR = { has_reform = daimyo has_reform = indep_daimyo }"
)

PROSE_REPLACEMENTS = (
    (
        "讲网络、寺内町法与宗门动员的可控全国遗产",
        "讲网络、寺内町法与受国法约束的宗门动员",
    ),
    (
        "法主国、惣村议会或世俗共同体三项互斥终局",
        "可在法主国、惣村议会与世俗共同体之间择定国制",
    ),
    ("可能引爆第二次应仁之乱", "足以再启京都大乱"),
    ("militancy", "武装动员"),
    ("动态替代强邻", "继起的强邻"),
    ("动态强邻", "当时最强的邻邦"),
    ("历史盟友灭亡时可选同文化强邻", "旧盟若亡，便转与同风俗的邻邦缔约"),
    ("伙伴灭亡时动态替代", "旧盟若绝，仍可另结近国"),
    ("三项互斥终局", "三种相殊的国制"),
    ("可控全国遗产", "可约束而行于天下的成法"),
    ("三选一", "三者各成一制"),
    ("后果长期不同", "三途各有久远之报"),
    ("本能寺式政变风险", "重臣乘隙弑逆的风险"),
    ("桶狭间败退后", "若遭桶狭间一类的挫败，可"),
)

ERAS = (
    {
        "id": "discovery",
        "trigger": "age_of_discovery",
        "name": "群雄草创之世",
        "lead": (
            "旧守护之名分尚存，兵粮、年贡与城砦却渐归诸家之手。今日所选的每一道"
            "安堵与盟誓，都会写进本家此后的兴亡。"
        ),
        "overview": (
            "此时旧守护秩序将裂未裂。京都的御教书尚能裁定名分，却未必能越过山川，"
            "把军粮与年贡送到每一座山城；守护代、国人、寺社、惣村与港町各握一端。"
            "主君今日发下的安堵，明日便可能成为邻家举兵的口实。欲图天下，先须使家中"
            "奉行能记账、道路能通兵、盟誓能经得住一次败阵。"
        ),
        "faith": (
            "神社与佛寺共同护持国土，权门、山门和门徒却也各有庄园、兵众与诉讼。"
            "祭礼能聚民，勧进能兴工，宗论亦能焚城。治者若只问教义而不问寺领、町座与"
            "百姓负担，祈祷之声很快便会化作一揆的钟鼓。"
        ),
        "shogunate": (
            "§Y[Root.GetName]幕府§!居武家名分之上，然而将军御内书未必足以驱动远国。"
            "管领、奉公众、守护与寺社都能借公仪之名争夺裁断。应先重整侍所与政所，"
            "使上洛、安堵和停战皆有可执行的次第；否则幕府每一次调停，都会暴露一次虚弱。"
        ),
        "daimyo": (
            "§Y[Root.GetName]家§!虽受幕府名分，真正维持领国的却是城砦、军役账与家臣"
            "起请。你须在旧守护权、在地国人与新兴被官之间裁定知行，并判断何时奉公、"
            "何时上洛、何时以兵威改写公议。小国可因一纸盟约得生，也可因一次迟疑而亡。"
        ),
        "realm": (
            "§Y[Root.GetName]§!已越过一国一郡的旧限，却仍背负群雄时代的盟誓与私怨。"
            "若要使征服不在主君身后崩散，便须把临时军令改为奉行制度，把降服之众改编为"
            "可核算的军役，并让朝廷、武家与町众都在新秩序中看见自己的位置。"
        ),
    },
    {
        "id": "reformation",
        "trigger": "age_of_reformation",
        "name": "法统改易之世",
        "lead": (
            "应仁余烬已化为诸国争衡，火器、异舶与新教说亦在这一时代渐次叩海。"
            "旧家格不再足恃，能治城、治军、治民者方能立国。"
        ),
        "overview": (
            "应仁余烬已化为诸国争衡，火器、异舶与天主教在这一时代渐次叩海：或已至"
            "港津，或尚在远方传闻，所到之处都令旧有权威重新估价。检地把隐田写进账册，"
            "城下町把商贾迁到大道，讲众与寺内町也显示信仰足以动员乡里。此世的强者不只"
            "善战，更须使铳炮、兵粮、商税和人质沿同一套命令运转。"
        ),
        "faith": (
            "净土真宗的讲、法华众的结社、旧寺社的门前町与南蛮传来的切支丹教门并立。"
            "改宗可以换来海外商路，也可能撕裂家臣团；护法可以安定乡里，也可能纵成"
            "门徒国。主君必须区分内心之信与公法之责，使寺社、教会和町众都不能越过军政。"
        ),
        "shogunate": (
            "§Y[Root.GetName]幕府§!面对的已非只求安堵的旧守护，而是掌握铁炮、商港和"
            "常备军的战国诸侯。将军若只凭先例，御所便会沦为强家挟持的印玺；若能把"
            "上洛诸军编入公仪、控制京都财赋并逐家奖惩，大乱反可成为重建幕政的机会。"
        ),
        "daimyo": (
            "§Y[Root.GetName]家§!必须从战时联盟变成能治民的领国。每下一城，都要回答"
            "旧臣如何安堵、军团如何得粮、宗教争端由谁裁断、市场由谁治理。你既可奉将军"
            "而争天下名分，也可另立权威；无论选择何路，都须先使家臣团不因继承而分裂。"
        ),
        "realm": (
            "§Y[Root.GetName]§!正把战国的动员力锻成统一政权。天下人的命令必须穿过"
            "奉行、检地册和城郭网络，而不能只依靠宿将私恩。朝廷名分、寺社处置、"
            "南蛮贸易与诸侯转封皆须纳入一套可继承的法度，方能使统一不止于一代威名。"
        ),
    },
    {
        "id": "absolutism",
        "trigger": "age_of_absolutism",
        "name": "公仪成法之世",
        "lead": (
            "兵火多已收束，城郭、石高、军役、寺社与海路日益纳入公仪成法。盛世的"
            "胜负不只在阵前，更在仓廪、驿路、救荒与奉行账册之间。"
        ),
        "overview": (
            "兵乱渐远，天下的胜负转入法度、仓廪与驿路。武家诸法度约束诸侯，城郭与"
            "参勤消耗藩力，朱印船、矿山和都市则把财富送入奉行账册。表面的太平并不等于"
            "静止：饥馑、浪人、米价和外样怨望都在考验公仪。能否把救荒、裁判与海防做成"
            "常制，将决定这份和平是盛世根基，还是下一场大乱的薄冰。"
        ),
        "faith": (
            "寺请与宗门改把信仰写入户籍，朱子学为君臣名分提供言辞，寺社仍掌握教育、"
            "赈济与地方记忆。秩序若只靠禁令，隐秘教门与被压抑的乡村便会在灾年合流；"
            "若只图宽纵，公法又会被寺领和门阀掏空。敬神礼佛之外，更须使教门承担公共责任。"
        ),
        "shogunate": (
            "§Y[Root.GetName]幕府§!须以公仪统摄诸藩，而非日日诉诸征伐。领地转封、"
            "武家法度、参勤、直辖财源和海路警固应彼此咬合；对亲藩、谱代与外样的尺度"
            "若失其平，太平便会养出新的割据。将军真正的威权，是让万事有例而仍能救急。"
        ),
        "daimyo": (
            "在公仪成法之世，§Y[Root.GetName]家§!的生存不只靠兵数。藩政须经营新田、"
            "专卖、学问与救荒，同时在幕府役务和本国财计之间保存余力。过度积兵招来猜忌，"
            "只求恭顺又会使家中空虚；一藩之治，正是对天下秩序最严厉的试卷。"
        ),
        "realm": (
            "§Y[Root.GetName]§!的权威已深入诸国，今后之难在于使广土众民不因例法繁密"
            "而窒息。中央奉行、地方代官、诸侯议席与商人资本必须互相制衡；盛世的国库既要"
            "供养海防与赈济，也要防止官僚把安定变成因循。"
        ),
    },
    {
        "id": "revolutions",
        "trigger": "age_of_revolutions",
        "name": "海国问政之世",
        "lead": (
            "久安使城下町繁盛，也使石高旧制与货殖新势相龃龉。藩债、乡诉、饥馑、"
            "书院之论与北海异船，都在追问本家是否仍有应世之法。"
        ),
        "overview": (
            "旧法外严而内弛，米价、百姓一揆与藩债不断追问谁应承担太平的代价。兰学、"
            "国学与实学争论天下之本，北海异船与外洋警讯又使海防不再只是边地之务。朝廷名分重新"
            "进入政治，町人财富却早已越过旧身分。此世的改革若只补一处账目，必在另一处"
            "裂开；唯有重订军政、财赋与对外之法，方能免于被时代推倒。"
        ),
        "faith": (
            "国学重寻神代与王统，兰学打开异国知识，寺院教育和民间讲社仍维系乡里。"
            "信仰已不能只由禁制裁定：朝廷、幕府、藩校与町众都在争夺解释天下的语言。"
            "主君须容纳学问而守住公法，使尊王不沦为私斗，使开智不成为无根的仿效。"
        ),
        "shogunate": (
            "§Y[Root.GetName]幕府§!面对的敌手不只在诸藩，也在债册、海防与日渐高涨的"
            "朝廷名分之中。沿用旧例可以延缓争端，却不能回答异国通商与全国军备。将军若"
            "不能让改革成为公议，任何一次饥馑或叩关都可能使诸藩与公仪渐生离心。"
        ),
        "daimyo": (
            "§Y[Root.GetName]家§!可在一藩之内先行试法：整顿债务、兴办藩校、修习译书、"
            "整饬海岸军备，并与朝廷和幕府周旋。改革越快，旧臣反弹越烈；改革越迟，财政与外患"
            "越难挽回。你必须决定，本家要成为旧秩序的柱石，还是新天下的先声。"
        ),
        "realm": (
            "§Y[Root.GetName]§!已站在海国与世界相接之处。中央集权若不能容纳地方议论，"
            "便会催生反叛；开放贸易若没有关税、海军与条法，又会使国门受制于人。此刻所定"
            "的成宪、军制与学政，将决定日轮之国以何种姿态面对外洋诸国。"
        ),
    },
)


def _load_escape_module():
    spec = importlib.util.spec_from_file_location(
        "jxp_escape_localisation",
        ESCAPE_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical EU4SpecialEscape converter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plan() -> dict[str, Any]:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _normalise_sentence(text: str) -> str:
    value = text.strip().rstrip("。！？!?")
    for old, new in PROSE_REPLACEMENTS:
        value = value.replace(old, new)
    return value


def _house_records(plan: dict[str, Any]) -> list[dict[str, Any]]:
    records = [dict(record) for record in plan["daimyo"]]
    toyotomi = dict(plan["unified_state_appendix"]["TOY"])
    toyotomi.update(
        {
            "tag": "TOY",
            "keywords": ["关白宣下", "太阁检地", "奉行与大老"],
        }
    )
    records.append(toyotomi)
    return records


def house_chronicle(record: dict[str, Any]) -> str:
    context = _normalise_sentence(record["political_context"])
    crisis = _normalise_sentence(record["internal_crisis"])
    name = record["name"]
    templates = (
        (
            "§Y{name}家§!之谱有云：{context}。家门所倚，往往亦是家门所困；眼前"
            "最险的一结，正在{crisis}。若只争一城一战而不辨名分、知行与旧约，"
            "军势虽盛，也难使降服者久安。主君当在兵马未动之前，先定家中可守百年"
            "的次第。"
        ),
        (
            "论§Y{name}家§!今日之势，不可只数城郭与兵众：{context}。旧牒之下，"
            "尚伏有{crisis}之患。此患逢继承则争名，逢败阵则争责，逢饥馑则争粮；"
            "故善为国者，既须威服外敌，也须使奉行有簿、家臣有分、百姓知其所纳。"
        ),
        (
            "若翻§Y{name}家§!旧牒，其兴衰皆系于一事：{context}。而今最难裁断者，"
            "莫过于{crisis}。一纸安堵可暂息众议，却不能代替长久之法；一场大捷可"
            "振家名，却不能消解积年的利害。主君若能把军役、裁判和在地旧约编为成例，"
            "方可使家运不随一人而终。"
        ),
        (
            "山川形胜之外，§Y{name}家§!另有一重难处：{context}。其根柢未稳，"
            "又遇{crisis}，外敌每可乘隙而入，近臣亦可能借名分相争。此时用兵固不可"
            "迟，用法更不可乱；应先辨谁守城、谁输粮、谁得议政，再以赏罚维系家中，"
            "使一次胜负不至于改易全部秩序。"
        ),
        (
            "§Y{name}家§!所守，不独是一国一郡，亦是一套尚待成形的约束：{context}。"
            "其中最易使上下离心者，正是{crisis}。倘以私恩代替公议，以临时征发代替"
            "军役定额，盛时或可无事，衰时必然俱发。主君须把家法写进账册、道路与城制，"
            "令远国之命也能落到乡里。"
        ),
        (
            "当此乱离，§Y{name}家§!的名分与实力并不总在一处：{context}。家中"
            "众议尤以{crisis}为忧，若处置失宜，旧臣、新附与在地势力都会各执一辞。"
            "故今日之策，不应只问如何取胜，也须问胜后由谁裁判、由谁征收、由谁守土；"
            "能答此三问，方有资格把一时霸业化为长治。"
        ),
    )
    variant = sum(ord(character) for character in record["tag"]) % len(templates)
    return templates[variant].format(name=name, context=context, crisis=crisis)


def house_counsel(record: dict[str, Any]) -> str:
    keywords = "、".join(f"§Y{word}§!" for word in record["keywords"][:3])
    alternative = _normalise_sentence(record["alternate_success"])
    legacy = _normalise_sentence(record["unified_legacy"])
    templates = (
        (
            "执政之柄，可从{keywords}三端入手。{alternative}。此策若成，便可将"
            "§Y{legacy}§!写入日后的国法；若只恃一时兵威，则继承一变，今日受命之人"
            "仍可能各拥其城。"
        ),
        (
            "欲存家名，先整{keywords}三务。眼前并非只有一条胜路：{alternative}。"
            "所求不只是扩土，而是使§Y{legacy}§!成为上下共守的旧例。如此纵有败阵，"
            "家政仍有凭据；纵遇强邻，也不至临事失序。"
        ),
        (
            "可奉{keywords}为三项先务，再依时势行此策：{alternative}。若能使"
            "§Y{legacy}§!不因主君更替而废，本家便有从分国走向天下的根基。反之，"
            "军令出于私恩、财赋不入公簿，所得越广，裂隙也越深。"
        ),
        (
            "今后用事，宜先察{keywords}。{alternative}。待内外有序，便把"
            "§Y{legacy}§!定为可传诸国的成法，使旧臣不失其所、新附不疑其命、百姓"
            "不困于无常征发；这才是本家真正的胜势。"
        ),
        (
            "衡其本末，{keywords}乃本家三根柱石。可循此途转危为机：{alternative}。"
            "终局所贵，在令§Y{legacy}§!既能约束强臣，也能安顿在地旧族。倘舍本逐末，"
            "纵得京都一纸名位，也难使远国长久奉行。"
        ),
        (
            "执政之始，先令{keywords}各得其序。{alternative}。兵威用以开路，"
            "§Y{legacy}§!才是守成之器；二者相济，方能让盟誓经得起败阵、让法度经得起"
            "继承，也让本家的名声不只留在战场。"
        ),
    )
    variant = (sum(ord(character) for character in record["tag"]) + 3) % len(
        templates
    )
    return templates[variant].format(
        keywords=keywords,
        alternative=alternative,
        legacy=legacy,
    )


def _defined_text(
    name: str,
    variants: Iterable[tuple[str, tuple[str, ...]]],
) -> str:
    lines = ["defined_text = {", f"\tname = {name}", "\trandom = no", ""]
    for localisation_key, triggers in variants:
        lines.extend(
            (
                "\ttext = {",
                f"\t\tlocalisation_key = {localisation_key}",
                "\t\ttrigger = {",
            )
        )
        lines.extend(f"\t\t\t{trigger}" for trigger in triggers)
        lines.extend(("\t\t}", "\t}", ""))
    lines.extend(("}", ""))
    return "\n".join(lines)


def _japanese_then_fallback(
    function_name: str,
    localisation_key: str,
    fallback_key: str,
) -> str:
    return _defined_text(
        function_name,
        (
            (
                localisation_key,
                ("jxp_is_japanese_polity_trigger = yes",),
            ),
            (fallback_key, ("always = yes",)),
        ),
    )


def _house_variants(
    records: list[dict[str, Any]],
    suffix: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    variants: list[tuple[str, tuple[str, ...]]] = []
    for record in records:
        key = f"jxp_start_house_{record['tag'].lower()}_{suffix}"
        if record["surface"] == "main":
            trigger = (f"tag = {record['tag']}",)
        else:
            trigger = (
                f"has_country_flag = jxp_map_origin_{record['tag'].lower()}",
            )
        variants.append((key, trigger))
    variants.append((f"jxp_start_house_generic_{suffix}", ("always = yes",)))
    return tuple(variants)


def _age_variants(suffix: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    variants = [
        (
            f"jxp_start_age_{era['id']}_{suffix}",
            (f"current_age = {era['trigger']}",),
        )
        for era in ERAS
    ]
    variants.append((f"jxp_start_age_fallback_{suffix}", ("always = yes",)))
    return tuple(variants)


def _role_variants() -> tuple[tuple[str, tuple[str, ...]], ...]:
    variants: list[tuple[str, tuple[str, ...]]] = []
    for era in ERAS:
        age = f"current_age = {era['trigger']}"
        variants.extend(
            (
                (
                    f"jxp_start_age_{era['id']}_role_shogunate",
                    (age, "has_reform = shogunate"),
                ),
                (
                    f"jxp_start_age_{era['id']}_role_daimyo",
                    (
                        age,
                        DAIMYO_REFORM_TRIGGER,
                        "NOT = { has_reform = shogunate }",
                    ),
                ),
                (f"jxp_start_age_{era['id']}_role_realm", (age,)),
            )
        )
    variants.append(("jxp_start_age_fallback_role_realm", ("always = yes",)))
    return tuple(variants)


def render_customisable(plan: dict[str, Any]) -> str:
    records = _house_records(plan)
    sections = [
        "# Generated by build_start_screen.py. Do not edit.",
        "# Pinned vanilla 1.37.5 start-screen SHA-256:",
        f"# {PINNED_VANILLA_CUSTOMISABLE_SHA256}",
        "",
        _defined_text(
            "JxpStartScreenTitle",
            (
                (
                    "jxp_start_screen_title_shogunate",
                    (
                        "jxp_is_japanese_polity_trigger = yes",
                        "has_reform = shogunate",
                    ),
                ),
                (
                    "jxp_start_screen_title_daimyo",
                    (
                        "jxp_is_japanese_polity_trigger = yes",
                        DAIMYO_REFORM_TRIGGER,
                        "NOT = { has_reform = shogunate }",
                    ),
                ),
                (
                    "jxp_start_screen_title_realm",
                    ("jxp_is_japanese_polity_trigger = yes",),
                ),
                ("jxp_start_vanilla_title", ("always = yes",)),
            ),
        ),
    ]
    for _ui_key, function_name, _vanilla_name, suffix in UI_FIELDS[1:]:
        sections.append(
            _japanese_then_fallback(
                function_name,
                f"jxp_start_screen_{suffix}",
                f"jxp_start_vanilla_{suffix}",
            )
        )
    sections.extend(
        (
            _defined_text(
                "JxpStartIdentityTitle",
                (
                    (
                        "jxp_start_identity_title_shogunate",
                        ("has_reform = shogunate",),
                    ),
                    (
                        "jxp_start_identity_title_daimyo",
                        (
                            DAIMYO_REFORM_TRIGGER,
                            "NOT = { has_reform = shogunate }",
                        ),
                    ),
                    ("jxp_start_identity_title_realm", ("always = yes",)),
                ),
            ),
            _defined_text(
                "JxpStartRoleTitle",
                (
                    (
                        "jxp_start_role_title_shogunate",
                        ("has_reform = shogunate",),
                    ),
                    (
                        "jxp_start_role_title_daimyo",
                        (
                            DAIMYO_REFORM_TRIGGER,
                            "NOT = { has_reform = shogunate }",
                        ),
                    ),
                    ("jxp_start_role_title_realm", ("always = yes",)),
                ),
            ),
            _defined_text(
                "JxpStartHouseChronicle",
                _house_variants(records, "chronicle"),
            ),
            _defined_text(
                "JxpStartHouseCounsel",
                _house_variants(records, "counsel"),
            ),
            _defined_text("JxpStartAgeName", _age_variants("name")),
            _defined_text("JxpStartAgeLead", _age_variants("lead")),
            _defined_text("JxpStartAgeChronicle", _age_variants("overview")),
            _defined_text("JxpStartFaithChronicle", _age_variants("faith")),
            _defined_text(
                "JxpStartDoctrineChronicle",
                (
                    (
                        "jxp_start_doctrine_jodo_shinshu",
                        ("religion = jodo_shinshu",),
                    ),
                    ("jxp_start_doctrine_vanilla", ("always = yes",)),
                ),
            ),
            _defined_text("JxpStartRoleChronicle", _role_variants()),
        )
    )
    return "\n".join(sections).rstrip() + "\n"


def _loc_line(key: str, value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f' {key}:0 "{escaped}"'


def render_localisation(plan: dict[str, Any]) -> str:
    lines = ["l_english:"]
    for ui_key, function_name, vanilla_name, suffix in UI_FIELDS:
        lines.append(_loc_line(ui_key, f"[{function_name}]"))
        lines.append(
            _loc_line(
                f"jxp_start_vanilla_{suffix}",
                f"[Root.{vanilla_name}]",
            )
        )

    lines.extend(
        (
            _loc_line(
                "jxp_start_screen_title_shogunate",
                "日轮之下·[Root.GetName]幕府　[GetYear]年",
            ),
            _loc_line(
                "jxp_start_screen_title_daimyo",
                "日轮之下·[Root.GetName]家　[GetYear]年",
            ),
            _loc_line(
                "jxp_start_screen_title_realm",
                "日轮之下·[Root.GetName]　[GetYear]年",
            ),
            _loc_line(
                "jxp_start_screen_up_left_title",
                "[Root.JxpStartIdentityTitle]",
            ),
            _loc_line("jxp_start_screen_up_right_title", "信仰与世道"),
            _loc_line(
                "jxp_start_screen_down_left_title",
                "[Root.JxpStartRoleTitle]",
            ),
            _loc_line(
                "jxp_start_screen_down_right_title",
                "天下形势·[Root.JxpStartAgeName]",
            ),
            _loc_line(
                "jxp_start_screen_up_left_desc",
                "[Root.JxpStartAgeLead]\\n\\n[Root.JxpStartHouseChronicle]",
            ),
            _loc_line(
                "jxp_start_screen_up_right_desc",
                "[Root.JxpStartFaithChronicle]\\n\\n§Y教法提要§!\\n[Root.JxpStartDoctrineChronicle]",
            ),
            _loc_line(
                "jxp_start_screen_down_left_desc",
                "[Root.JxpStartRoleChronicle]\\n\\n§Y国制提要§!\\n[Root.StartScreenDownLeftDesc]",
            ),
            _loc_line(
                "jxp_start_screen_down_right_desc",
                "[Root.JxpStartAgeChronicle]\\n\\n[Root.JxpStartHouseCounsel]",
            ),
            _loc_line(
                "jxp_start_identity_title_shogunate",
                "[Root.GetName]幕府之世",
            ),
            _loc_line(
                "jxp_start_identity_title_daimyo",
                "[Root.GetName]家之世",
            ),
            _loc_line(
                "jxp_start_identity_title_realm",
                "[Root.GetName]治下",
            ),
            _loc_line("jxp_start_role_title_shogunate", "幕府执政之纲"),
            _loc_line("jxp_start_role_title_daimyo", "分国经营之要"),
            _loc_line("jxp_start_role_title_realm", "天下经纶之策"),
        )
    )

    for record in _house_records(plan):
        prefix = f"jxp_start_house_{record['tag'].lower()}"
        lines.append(_loc_line(f"{prefix}_chronicle", house_chronicle(record)))
        lines.append(_loc_line(f"{prefix}_counsel", house_counsel(record)))

    lines.extend(
        (
            _loc_line(
                "jxp_start_house_generic_chronicle",
                "§Y[Root.GetName]§!已不再只是旧日一国一郡之名。今日所承者，是诸家法、"
                "寺社、町众与军役交织而成的天下；旧姓虽可更易，统治仍须回答如何把战时"
                "军令化为可传后世的法度。",
            ),
            _loc_line(
                "jxp_start_house_generic_counsel",
                "先核田土与军役，再定朝廷、武家、寺社和町众之分。若能使征服者受法、"
                "降服者有席、百姓知所输纳，新天下方不至于随一代雄主而散。",
            ),
            _loc_line(
                "jxp_start_doctrine_jodo_shinshu",
                "§Y净土真宗§!以阿弥陀佛本愿、念佛与信心为宗，讲、坊舍与寺内町既能"
                "施济乡里，也可能形成独立的政治力量。本宗沿用§Y业力§!：一味征伐会"
                "使业力偏低，一味退让则会使业力偏高；守其中道，方能得到最厚的教法助益。",
            ),
            _loc_line(
                "jxp_start_doctrine_vanilla",
                "[Root.StartScreenUpRightDesc]",
            ),
        )
    )

    for era in ERAS:
        prefix = f"jxp_start_age_{era['id']}"
        lines.extend(
            (
                _loc_line(f"{prefix}_name", era["name"]),
                _loc_line(f"{prefix}_lead", era["lead"]),
                _loc_line(f"{prefix}_overview", era["overview"]),
                _loc_line(f"{prefix}_faith", era["faith"]),
                _loc_line(f"{prefix}_role_shogunate", era["shogunate"]),
                _loc_line(f"{prefix}_role_daimyo", era["daimyo"]),
                _loc_line(f"{prefix}_role_realm", era["realm"]),
            )
        )

    lines.extend(
        (
            _loc_line("jxp_start_age_fallback_name", "日轮流转之世"),
            _loc_line(
                "jxp_start_age_fallback_lead",
                "岁序虽越旧史，名分、财赋、军役与民生之问仍在眼前。",
            ),
            _loc_line(
                "jxp_start_age_fallback_overview",
                "岁序虽越旧史，天下之务仍在名分、财赋、军役与民生。请从眼前国情出发，"
                "为[Root.GetName]另定一代之法。",
            ),
            _loc_line(
                "jxp_start_age_fallback_faith",
                "祭政与教法须能安民而不越公议；敬畏传统，也要为当世之变留下余地。",
            ),
            _loc_line(
                "jxp_start_age_fallback_role_realm",
                "[Root.GetName]须在旧例与新政之间作出自己的裁断。",
            ),
        )
    )
    return "\n".join(lines) + "\n"


def validate_plan(plan: dict[str, Any]) -> None:
    daimyo_records = plan.get("daimyo", [])
    if len(daimyo_records) != 67:
        raise ValueError(f"expected 67 daimyo records, found {len(daimyo_records)}")
    if Counter(record.get("surface") for record in daimyo_records) != {
        "main": 37,
        "map": 30,
    }:
        raise ValueError("start-screen plan must contain 37 main and 30 map houses")
    records = _house_records(plan)
    if Counter(record.get("surface") for record in records) != {
        "main": 38,
        "map": 30,
    }:
        raise ValueError("start screen must add TOY to the 67 daimyo identities")
    tags = [record.get("tag") for record in records]
    if len(tags) != len(set(tags)):
        raise ValueError("start-screen plan contains duplicate tags")

    chronicle_values: set[str] = set()
    counsel_values: set[str] = set()
    for record in records:
        for key in (
            "tag",
            "name",
            "political_context",
            "internal_crisis",
            "alternate_success",
            "unified_legacy",
        ):
            if not record.get(key):
                raise ValueError(f"{record.get('tag', '?')} lacks {key}")
        if len(record.get("keywords", [])) < 3:
            raise ValueError(f"{record['tag']} needs at least three house keywords")
        chronicle = house_chronicle(record)
        counsel = house_counsel(record)
        if chronicle in chronicle_values or counsel in counsel_values:
            raise ValueError(f"{record['tag']} start-screen prose is not unique")
        chronicle_values.add(chronicle)
        counsel_values.add(counsel)

        if record["surface"] == "map":
            history = tuple(
                sorted((MAP_ROOT / "history" / "countries").glob(f"{record['tag']} - *.txt"))
            )
            if len(history) != 1:
                raise ValueError(f"{record['tag']} map history shell is not unique")
            marker = (
                f"set_country_flag = jxp_map_origin_{record['tag'].lower()}".encode(
                    "ascii"
                )
            )
            if marker not in history[0].read_bytes():
                raise ValueError(f"{record['tag']} lacks its fresh-start origin flag")

    customisable = render_customisable(plan)
    for record in records:
        if record["surface"] == "main":
            if f"tag = {record['tag']}" not in customisable:
                raise ValueError(f"{record['tag']} lacks a main-tag start-screen branch")
        else:
            marker = f"has_country_flag = jxp_map_origin_{record['tag'].lower()}"
            if marker not in customisable:
                raise ValueError(f"{record['tag']} lacks a map-origin start-screen branch")
            if f"tag = {record['tag']}" in customisable:
                raise ValueError(f"main start-screen file hard-references map tag {record['tag']}")


def validate_vanilla(game_root: Path) -> None:
    expected = (
        (
            VANILLA_CUSTOMISABLE_RELATIVE,
            PINNED_VANILLA_CUSTOMISABLE_SHA256,
        ),
        (
            VANILLA_LOCALISATION_RELATIVE,
            PINNED_VANILLA_LOCALISATION_SHA256,
        ),
    )
    for relative, digest in expected:
        path = game_root / relative
        if not path.is_file():
            raise ValueError(f"missing pinned vanilla source: {path}")
        actual = sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"vanilla source drift: {relative} -> {actual}")
    vanilla = (game_root / VANILLA_CUSTOMISABLE_RELATIVE).read_text(encoding="utf-8-sig")
    for _ui_key, _jxp_name, vanilla_name, _suffix in UI_FIELDS:
        if f"name = {vanilla_name}" not in vanilla:
            raise ValueError(f"pinned vanilla start screen lacks {vanilla_name}")


def render_outputs(plan: dict[str, Any]) -> dict[Path, str | bytes]:
    source = render_localisation(plan)
    escape = _load_escape_module()
    return {
        CUSTOMISABLE_PATH: render_customisable(plan),
        SOURCE_PATH: source,
        ACTIVE_PATH: escape.escape_text(source).encode("utf-8-sig"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on generated drift")
    parser.add_argument(
        "--game-root",
        type=Path,
        help="optionally verify the pinned EU4 1.37.5 start-screen sources",
    )
    args = parser.parse_args()

    plan = load_plan()
    validate_plan(plan)
    if args.game_root is not None:
        validate_vanilla(args.game_root)
    outputs = render_outputs(plan)
    drift: list[Path] = []
    for path, payload in outputs.items():
        if args.check:
            if not path.is_file():
                drift.append(path)
                continue
            actual = (
                path.read_bytes()
                if isinstance(payload, bytes)
                else path.read_text(encoding="utf-8")
            )
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
        print(f"PASS: {len(outputs)} Japanese start-screen outputs are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
