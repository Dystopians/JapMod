"""Build the B115 external-route mission additions and their support surface.

The established route trees remain authoritative.  This generator inserts only
the B8 gaps into their live slot-4/5 series and emits the shared event,
interaction, modifier, and readable-localisation sources.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def _write_utf8_lf(path: Path, text: str) -> None:
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def _records_from_text(text: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for raw in text.splitlines(keepends=True):
        if raw.endswith("\r\n"):
            records.append((raw[:-2], "\r\n"))
        elif raw.endswith("\n"):
            records.append((raw[:-1], "\n"))
        else:
            records.append((raw, ""))
    return records


def _read_preserved_lines(path: Path) -> list[tuple[str, str]]:
    return _records_from_text(path.read_bytes().decode("utf-8-sig"))


def _write_preserved_lines(path: Path, records: list[tuple[str, str]]) -> None:
    path.write_bytes("".join(line + ending for line, ending in records).encode("utf-8"))


@dataclass(frozen=True)
class Lane:
    series: str
    source: str
    tail: str
    positions: tuple[int, ...]
    titles: tuple[str, ...]
    descriptions: tuple[str, ...]
    kind: str


@dataclass(frozen=True)
class Route:
    key: str
    name: str
    potential: str
    lanes: tuple[Lane, ...]
    modifier: tuple[tuple[str, str], ...]
    principle: str


def lane(series: str, source: str, tail: str, positions, titles, kind, principle) -> Lane:
    titles = tuple(titles)
    descriptions: list[str] = []
    lane_cost = {
        "mainland": "使团必须尊重海东各地既有法统，不能把会盟偷换成无期限占领",
        "overseas": "越海财政、住民席位与撤回程序必须同时入册",
        "trade": "商馆须接受互惠税则和当地裁判，不能只索取单向特权",
        "navy": "海军预算必须对应护航责任，舰队不得借巡弋之名无限扩战",
        "settlement": "移民章程必须给当地住民留下土地、议席与返航保障",
    }[kind]
    for index, title in enumerate(titles):
        if len(titles) == 1:
            descriptions.append(f"围绕“{title}”汇总旧例并正式成典；{principle}由此获得明确边界，而{lane_cost}。")
        elif index == 0:
            descriptions.append(f"以“{title}”发出首批训令。先查明港市、社群与邻国的真实条件，再决定如何推进{principle}。")
        elif index == len(titles) - 1:
            descriptions.append(f"“{title}”将前述试行汇为可复议的总章程。其收益属于整个航路，但代价同样明载：{lane_cost}。")
        elif index == 1:
            descriptions.append(f"当地使者对“{title}”提出了条件。我们可以继续推进{principle}，但必须把税则、司法与代表权逐项写清。")
        elif index == len(titles) - 2:
            descriptions.append(f"“{title}”进入最昂贵的一段：港务、护航和地方补偿都要有稳定财源；若不接受这一代价，计划便应及时收束。")
        else:
            descriptions.append(f"围绕“{title}”建立常设账册和年度复议，让{principle}从临时使团变成能被地方检验的制度。")
    return Lane(
        series,
        source,
        tail,
        tuple(positions),
        titles,
        tuple(descriptions),
        kind,
    )


ROUTES = (
    Route(
        "uncommitted", "诸州公议", "\t\ttag = JAP\n\t\tNOT = { jxp_has_any_route_trigger = yes }",
        (
            lane("jxp_shinto_branch_missions", "missions/jxp_11_branching_missions.txt", "jxp_mission_sacred_isles", (12, 13, 14, 15, 16),
                 ("对马议使与通事", "琉球观察与保护", "海东公议与缓冲", "通商约与四口船籍", "海疆共同守护"), "mainland", "公议与锁国都可继承、但会作出不同裁断的神道海疆制度"),
            lane("jxp_japan_uncommitted_horizon_missions", "missions/jxp_40_final_state_completion_missions.txt", "jxp_mission_uncommitted_keep_all_courses_open", (11, 12, 13, 14, 15),
                 ("诸州共同商馆", "海外代表请愿", "共同殖民预算", "殖民地议席", "万国公议"), "overseas", "殖民代表权与共同财政"),
        ),
        (("diplomatic_reputation", "0.5"), ("improve_relation_modifier", "0.10")),
        "诸州共议、弱国保护与殖民代表权",
    ),
    Route(
        "sakoku", "锁国公仪", "\t\ttag = JAP\n\t\thas_country_flag = jxp_path_sakoku",
        (lane("jxp_japan_sakoku_horizon_missions", "missions/jxp_40_final_state_completion_missions.txt", "jxp_mission_sakoku_bakuhan_constitution", (17, 18, 19),
              ("漂流民送还约", "近海排他巡检", "四海锁钥"), "overseas", "四口通事、送还惯例与近海防卫"),),
        (("defensiveness", "0.10"), ("fort_maintenance_modifier", "-0.10")),
        "有限互市、漂流民送还与近海缓冲",
    ),
    Route(
        "open", "开国海政", "\t\ttag = JAP\n\t\thas_country_flag = jxp_path_open_trade",
        (
            lane("jxp_japan_eastasia_missions", "missions/jxp_03_overseas_missions.txt", "jxp_mission_eastasia_rite_sphere", (16, 17),
                 ("朱印商权筹议", "朱印商权章程"), "trade", "条约港、公司与互惠商权"),
            lane("jxp_japan_pacific_missions", "missions/jxp_03_overseas_missions.txt", "jxp_mission_eastasia_break_mandate", (15, 16),
                 ("开拓海疆筹议", "开拓海疆章程"), "settlement", "岛链补给、移民自治与殖民问责"),
        ),
        (("trade_efficiency", "0.10"), ("global_ship_trade_power", "0.10")),
        "朱印商贸、远洋海军或殖民开拓的有限选择",
    ),
    Route(
        "buddhist", "佛法海路", "\t\ttag = JAP\n\t\thas_country_flag = jxp_path_buddhist",
        (
            lane("jxp_a_96_buddhist_slot_4_missions", "missions/jxp_a_96_buddhist_missions.txt", "jxp_a_buddhist_town_temple_credit", (15, 16),
                 ("佛教保护国约", "诸宗海外席位"), "mainland", "护法外交与诸宗共席"),
            lane("jxp_a_96_buddhist_slot_5_missions", "missions/jxp_a_96_buddhist_missions.txt", "jxp_a_buddhist_buddhist_constitution", (12, 13, 14, 15),
                 ("寺院移民约", "施药院航路", "护法海路", "四海法灯"), "overseas", "寺院移民、施药与非征服护法"),
        ),
        (("tolerance_heretic", "1"), ("improve_relation_modifier", "0.10")),
        "不以征服为条件的法灯、施药和宗派共存",
    ),
    Route(
        "kirishitan", "东方教会", "\t\ttag = KJP\n\t\thas_country_flag = jxp_path_kirishitan",
        (
            lane("jxp_kirishitan_deep_missions", "missions/jxp_09_religious_route_missions.txt", "jxp_mission_kjp_estates_concordat", (17, 18, 19),
                 ("保护朝鲜教徒", "中华教会港", "东方主教会议"), "mainland", "日本国家教会、罗马与地方教友之间的三方协商"),
            lane("jxp_christian_branch_missions", "missions/jxp_11_branching_missions.txt", "jxp_mission_cross_sun_commonwealth", (14, 15, 16, 17, 18),
                 ("菲律宾教会", "澳门与罗马", "教会殖民地", "本地神职班", "东方教会同盟"), "overseas", "本地神职与反保护权依附"),
        ),
        (("tolerance_own", "1"), ("diplomatic_reputation", "0.5")),
        "国家教会、本地神职与反伊比利亚保护权",
    ),
    Route(
        "confucian", "经世礼仪圈", "\t\ttag = CJP\n\t\thas_country_flag = jxp_path_confucian",
        (
            lane("jxp_cjp_syncretic_missions", "missions/jxp_56_final_tag_identity_missions.txt", "jxp_mission_cjp_censorate_charter", (14, 15),
                 ("学宫使节", "日本国王名分"), "mainland", "不夺天命的礼聘、贡贸与名分外交"),
            lane("jxp_japan_confucian_imperial_missions", "missions/jxp_japan_missions.txt", "jxp_mission_three_capitals_ledgers", (15,),
                 ("经世礼仪圈",), "overseas", "礼仪互认与海上经世网络"),
        ),
        (("diplomatic_reputation", "0.5"), ("global_institution_spread", "0.10")),
        "不夺天命的礼制外交与经世商馆",
    ),
    Route(
        "imperial", "太政官外朝", "\t\ttag = EJP\n\t\thas_country_flag = jxp_path_imperial",
        (
            lane("jxp_ejp_court_rite_missions", "missions/jxp_56_final_tag_identity_missions.txt", "jxp_mission_ejp_rites_of_restoration", (13, 15),
                 ("朝廷海东使节", "国司海疆"), "mainland", "朝廷使节、国司任期与边疆问责"),
            lane("jxp_ejp_imperial_seas_missions", "missions/jxp_56_final_tag_identity_missions.txt", "jxp_mission_ejp_sun_over_eastern_seas", (13, 14, 15, 16, 17),
                 ("神祇海外使", "皇室殖民章程", "海外国司", "亲征或外朝", "太政官外朝"), "overseas", "皇室殖民章程与外朝裁断"),
        ),
        (("yearly_legitimacy", "1"), ("governing_capacity_modifier", "0.05")),
        "朝廷仪礼、国司任期与外朝裁断",
    ),
    Route(
        "reformed", "自由海契", "\t\ttag = RFJ\n\t\thas_country_flag = jxp_path_reformed",
        (
            lane("jxp_reformed_deep_missions", "missions/jxp_09_religious_route_missions.txt", "jxp_mission_covenant_commonwealth", (14, 15),
                 ("海外会众", "自由海洋法"), "mainland", "城市契约、会众自治与反垄断"),
            lane("jxp_rfj_covenant_horizon_missions", "missions/jxp_56_final_tag_identity_missions.txt", "jxp_mission_rfj_synodic_constitution", (15,),
                 ("盟约舰队",), "overseas", "会众殖民自治与盟约护航"),
        ),
        (("trade_steering", "0.10"), ("global_institution_spread", "0.10")),
        "地方契约、会众自治和反垄断海法",
    ),
    Route(
        "kaikyo", "两洋朝觐路", "\t\ttag = SJP\n\t\thas_country_flag = jxp_path_kaikyo",
        (
            lane("jxp_muslim_branch_missions", "missions/jxp_11_branching_missions.txt", "jxp_mission_south_sea_maritime_law", (12, 13, 14),
                 ("海峡协定", "穆斯林港保护", "季风护航"), "mainland", "卡迪、牙人与日本本地法域共治"),
        ),
        (("caravan_power", "0.10"), ("global_trade_power", "0.05")),
        "多法域港市、瓦合甫和非穆斯林社群保障",
    ),
    Route(
        "ikko", "同行诸国盟", "\t\ttag = IJP\n\t\thas_country_flag = jxp_path_ikko",
        (
            lane("jxp_popular_branch_missions", "missions/jxp_11_branching_missions.txt", "jxp_mission_commonwealth_covenant", (13, 15, 17, 19),
                 ("同行海路", "寺内町侨民", "共同粮仓援助", "支援受压门徒"), "mainland", "惣村互助、粮仓援助与非征服共同体"),
            lane("jxp_ikko_common_economy_missions", "missions/jxp_40_final_state_completion_missions.txt", "jxp_mission_ijp_somon_constitution", (17, 18, 19),
                 ("海外惣村", "合作殖民地", "同行诸国盟"), "overseas", "合作殖民、门徒船团与地方惣议"),
        ),
        (("global_unrest", "-1"), ("production_efficiency", "0.05")),
        "粮仓援助、合作殖民和惣村自治",
    ),
    Route(
        "wokou", "东海船盟", "\t\ttag = WAK\n\t\thas_country_flag = jxp_path_wokou",
        (
            lane("jxp_wak_black_current_missions", "missions/jxp_56_final_tag_identity_missions.txt", "jxp_mission_wak_admiralty_articles", (15, 17, 19),
                 ("破除海禁", "沿海岛主", "海上保护费"), "mainland", "自由港保护与沿海责任而非内陆兼并"),
            lane("jxp_frontier_diplomacy_missions", "missions/jxp_11_branching_missions.txt", "jxp_mission_east_sea_protocol", (15, 17, 19),
                 ("黑潮自由港", "私掠札", "东海船盟"), "overseas", "船主自治、私掠问责与自由港联盟"),
        ),
        (("privateer_efficiency", "0.15"), ("naval_forcelimit_modifier", "0.10")),
        "自由港、私掠问责与避免内陆过度扩张",
    ),
    Route(
        "toyotomi", "太阁大陆经略", "\t\ttag = TOY",
        (),
        (("land_forcelimit_modifier", "0.10"), ("reinforce_speed", "0.10")),
        "兵站、有限保护、贸易和解与撤军问责",
    ),
)


def _safe_id(text: str) -> str:
    return text.replace("settlement", "settlement")


def _gate(route: Route, lane_: Lane, index: int) -> tuple[str, ...]:
    if route.key != "open":
        return ()
    main = f"jxp_b_115_open_main_{lane_.kind}"
    secondary = f"jxp_b_115_open_secondary_{lane_.kind}"
    if index == 1:
        return (
            "\t\t\tcustom_trigger_tooltip = {",
            f"\t\t\t\ttooltip = jxp_b_115_open_{lane_.kind}_preparation_tt",
            "\t\t\t\tOR = {",
            f"\t\t\t\t\thas_country_flag = {main}",
            f"\t\t\t\t\thas_country_flag = {secondary}",
            "\t\t\t\t}",
            "\t\t\t}",
        )
    return (
        "\t\t\tcustom_trigger_tooltip = {",
        f"\t\t\t\ttooltip = jxp_b_115_open_{lane_.kind}_mainline_tt",
        f"\t\t\t\thas_country_flag = {main}",
        "\t\t\t}",
    )


def _mission_block(route: Route, lane_: Lane, lane_number: int) -> tuple[str, list[tuple[str, str]]]:
    blocks: list[str] = []
    loc: list[tuple[str, str]] = []
    previous = lane_.tail
    for index, (position, title, desc) in enumerate(zip(lane_.positions, lane_.titles, lane_.descriptions), 1):
        mission_id = f"jxp_b_115_{route.key}_{lane_.kind}_{index:02d}"
        event_number = ROUTES.index(route) * 10
        is_first = index == 1
        is_last = index == len(lane_.titles)
        is_capstone = (lane_number == len(route.lanes) and is_last) or (route.key == "open" and is_last)
        trigger_lines = ["\t\ttrigger = {"]
        trigger_lines.extend(_gate(route, lane_, index))
        trigger_lines.append(("\t\t\tdip_tech = 10", "\t\t\tnum_of_ports = 5", "\t\t\tprestige = 25", "\t\t\tnavy_tradition = 15", "\t\t\tadm_tech = 12")[min(index, 5) - 1])
        if index >= 5:
            trigger_lines.append("\t\t\tstability = 1")
        trigger_lines.append("\t\t}")
        effects = ["\t\teffect = {"]
        if index == 1:
            effects.append("\t\t\tadd_prestige = 5")
            if route.key != "open":
                effects.append(f"\t\t\tset_country_flag = jxp_b_115_{route.key}_interaction_unlocked")
            event = 1 if lane_number == 1 else 3
            if route.key == "open":
                event = {"trade": 1, "navy": 2, "settlement": 3}[lane_.kind]
            if route.key == "uncommitted" and lane_.kind == "mainland":
                effects.extend((
                    "\t\t\tif = {",
                    "\t\t\t\tlimit = { has_country_flag = jxp_path_sakoku }",
                    "\t\t\t\tset_country_flag = jxp_b_115_sakoku_interaction_unlocked",
                    "\t\t\t\tcountry_event = { id = jxp_b_115_routes.11 days = 1 }",
                    "\t\t\t}",
                    "\t\t\telse = { country_event = { id = jxp_b_115_routes.1 days = 1 } }",
                ))
            else:
                effects.append(f"\t\t\tcountry_event = {{ id = jxp_b_115_routes.{event_number + event} days = 1 }}")
        elif is_last and lane_number == 1:
            effects.append("\t\t\tchange_government_reform_progress = 15")
            if route.key == "uncommitted" and lane_.kind == "mainland":
                effects.extend((
                    "\t\t\tif = {",
                    "\t\t\t\tlimit = { has_country_flag = jxp_path_sakoku }",
                    "\t\t\t\tcountry_event = { id = jxp_b_115_routes.12 days = 1 }",
                    "\t\t\t}",
                    "\t\t\telse = { country_event = { id = jxp_b_115_routes.2 days = 1 } }",
                ))
            else:
                effects.append(f"\t\t\tcountry_event = {{ id = jxp_b_115_routes.{event_number + 2} days = 1 }}")
        else:
            reward = ("add_dip_power = 25", "add_navy_tradition = 2", "add_prestige = 5", "change_government_reform_progress = 10")[(index - 2) % 4]
            effects.append(f"\t\t\t{reward}")
        if is_capstone:
            effects.extend((
                "\t\t\tset_country_flag = jxp_iface_b_external_capstone_complete",
                "\t\t\tadd_country_modifier = {",
                f"\t\t\t\tname = jxp_b_115_{route.key}_external_capstone",
                "\t\t\t\tduration = 7300",
                "\t\t\t}",
                f"\t\t\tcountry_event = {{ id = jxp_b_115_routes.{event_number + 4} days = 1 }}",
            ))
        effects.append("\t\t}")
        block = [
            f"\t{mission_id} = {{",
            "\t\ticon = mission_diplomatic_relation",
            f"\t\tposition = {position}",
            f"\t\trequired_missions = {{ {previous} }}",
            *trigger_lines,
            *effects,
            "\t}",
        ]
        blocks.append("\n".join(block))
        loc.extend(((mission_id + "_title", title), (mission_id + "_desc", desc)))
        previous = mission_id
    return "\n\n".join(blocks), loc


def _series_bounds(lines: list[str], series: str) -> tuple[int, int]:
    start = next(i for i, line in enumerate(lines) if line == f"{series} = {{")
    depth = 0
    for index in range(start, len(lines)):
        depth += lines[index].count("{") - lines[index].count("}")
        if index > start and depth == 0:
            return start, index
    raise RuntimeError(f"cannot find end of {series}")


def _mission_segments(block: str) -> tuple[tuple[int, list[str]], ...]:
    lines = block.splitlines()
    segments: list[tuple[int, list[str]]] = []
    cursor = 0
    while cursor < len(lines):
        if not lines[cursor].startswith("\tjxp_b_115_"):
            cursor += 1
            continue
        start = cursor
        depth = 0
        while cursor < len(lines):
            depth += lines[cursor].count("{") - lines[cursor].count("}")
            cursor += 1
            if depth == 0:
                break
        segment = lines[start:cursor]
        position_line = next(line for line in segment if line.startswith("\t\tposition = "))
        segments.append((int(position_line.rsplit(" ", 1)[1]), segment))
    return tuple(segments)


def _direct_mission_positions(lines: list[str], series: str) -> tuple[tuple[int, int], ...]:
    start, end = _series_bounds(lines, series)
    result: list[tuple[int, int]] = []
    depth = 1
    index = start + 1
    while index < end:
        line = lines[index]
        if depth == 1 and line.startswith("\t") and not line.startswith("\t\t") and line.rstrip().endswith("= {"):
            block_start = index
            local_depth = line.count("{") - line.count("}")
            index += 1
            while index < end and local_depth:
                local_depth += lines[index].count("{") - lines[index].count("}")
                index += 1
            position = next((int(item.rsplit(" ", 1)[1]) for item in lines[block_start:index] if item.startswith("\t\tposition = ")), None)
            if position is not None:
                result.append((position, block_start))
            continue
        depth += line.count("{") - line.count("}")
        index += 1
    return tuple(result)


def _insert_into_records(
    records: list[tuple[str, str]], series: str, block: str, sentinel: str
) -> list[tuple[str, str]]:
    lines = [line for line, _ending in records]
    text = "\n".join(lines)
    if sentinel in text:
        return records
    first = True
    for position, segment in _mission_segments(block):
        _start, end = _series_bounds(lines, series)
        later = [index for current, index in _direct_mission_positions(lines, series) if current > position]
        target = min(later) if later else end
        insertion = [("", "\n")]
        if first:
            insertion.append(("\t# B115 external-route additions.", "\n"))
            first = False
        insertion.extend((line, "\n") for line in (*segment, ""))
        records[target:target] = insertion
        lines[target:target] = [line for line, _ending in insertion]
    return records


def _insert_into_series(relative: str, series: str, block: str, sentinel: str) -> None:
    path = ROOT / relative
    records = _insert_into_records(_read_preserved_lines(path), series, block, sentinel)
    _write_preserved_lines(path, records)


def _strip_generated_records(
    records: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    lines = [line for line, _ending in records]
    output: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == "# B115 external-route additions.":
            index += 1
            continue
        if line.startswith("\tjxp_b_115_") and line.rstrip().endswith("= {"):
            depth = 0
            while index < len(lines):
                depth += lines[index].count("{") - lines[index].count("}")
                index += 1
                if depth == 0:
                    break
            while output and output[-1][0] == "":
                output.pop()
            continue
        output.append(records[index])
        index += 1
    return output


def _remove_generated_missions() -> None:
    generated_sources = {lane_.source for route in ROUTES for lane_ in route.lanes}
    generated_sources.add("missions/jxp_70_oda_toyotomi_missions.txt")
    for relative in sorted(generated_sources):
        path = ROOT / relative
        records = _read_preserved_lines(path)
        output = _strip_generated_records(records)
        if output != records:
            _write_preserved_lines(path, output)


def render_mission_overlay(relative: str, base_text: str) -> str:
    """Apply this generator's B115 blocks to an authoritative mission payload."""

    records = _strip_generated_records(_records_from_text(base_text))
    for route in ROUTES:
        for lane_ in route.lanes:
            if lane_.source != relative:
                continue
            block, _localisation = _mission_block(route, lane_, route.lanes.index(lane_) + 1)
            sentinel = f"jxp_b_115_{route.key}_{lane_.kind}_01"
            records = _insert_into_records(records, lane_.series, block, sentinel)
    return "".join(line + ending for line, ending in records)


def _events() -> tuple[str, list[tuple[str, str]]]:
    lines = ["namespace = jxp_b_115_routes", ""]
    loc: list[tuple[str, str]] = []
    stages = (
        ("大陆问议", "第一批使节带回了沿岸诸国、港市和社群的条件。"),
        ("海东章程", "大陆经略的原则已经写入可撤回、可复议的正式章程。"),
        ("越海议席", "海外住民要求在航路、税赋和防务中拥有明确席位。"),
        ("对外经略成典", "经略并未止于宣称；港务、地方权利与撤回程序已经成典。"),
        ("特别外交会议", "一次特别会议将路线原则用于眼前争端，并留下十年复议期限。"),
    )
    for route_index, route in enumerate(ROUTES):
        base = route_index * 10
        for number, (title, desc) in enumerate(stages, 1):
            event_id = base + number
            key = f"jxp_b_115_routes.{event_id}"
            lines.extend((
                "country_event = {",
                f"\tid = {key}",
                f"\ttitle = {key}.t",
                f"\tdesc = {key}.d",
                "\tpicture = DIPLOMACY_eventPicture",
                "\tis_triggered_only = yes",
            ))
            if route.key == "open" and number == 5:
                for kind, label in (("trade", "以朱印商贸为主线"), ("navy", "以远洋海军为主线"), ("settlement", "以殖民开拓为主线")):
                    lines.extend((
                        "\toption = {",
                        f"\t\tname = {key}.{kind}",
                        f"\t\tset_country_flag = jxp_b_115_open_main_{kind}",
                        f"\t\tcountry_event = {{ id = jxp_b_115_routes.{base + 6} days = 1 }}",
                    ))
                    if kind == "trade":
                        lines.extend(("\t\tai_chance = {", "\t\t\tfactor = 10", "\t\t\tmodifier = { factor = 3 trade_efficiency = 0.25 }", "\t\t}"))
                    elif kind == "navy":
                        lines.extend(("\t\tai_chance = {", "\t\t\tfactor = 10", "\t\t\tmodifier = { factor = 3 navy_size_percentage = 0.8 }", "\t\t}"))
                    else:
                        lines.extend(("\t\tai_chance = {", "\t\t\tfactor = 5", "\t\t\tmodifier = { factor = 4 num_of_colonists = 1 }", "\t\t\tmodifier = { factor = 3 has_idea_group = exploration_ideas }", "\t\t}"))
                    lines.append("\t}")
                    loc.append((f"{key}.{kind}", label))
            else:
                lines.extend(("\toption = {", f"\t\tname = {key}.a", "\t\tadd_prestige = 2", "\t}"))
                loc.append((f"{key}.a", "依章办理"))
            lines.extend(("}", ""))
            loc.extend(((f"{key}.t", route.name + title), (f"{key}.d", desc + "其尺度是" + route.principle + "。")))
        if route.key == "open":
            key = f"jxp_b_115_routes.{base + 6}"
            lines.extend(("country_event = {", f"\tid = {key}", f"\ttitle = {key}.t", f"\tdesc = {key}.d", "\tpicture = DIPLOMACY_eventPicture", "\tis_triggered_only = yes"))
            kinds = (("trade", "navy", "以远洋海军为有限副线"), ("trade", "settlement", "以殖民开拓为有限副线"), ("navy", "trade", "以朱印商贸为有限副线"), ("navy", "settlement", "以殖民开拓为有限副线"), ("settlement", "trade", "以朱印商贸为有限副线"), ("settlement", "navy", "以远洋海军为有限副线"))
            for main, secondary, label in kinds:
                option = f"{key}.{main}_{secondary}"
                lines.extend(("\toption = {", f"\t\tname = {option}", f"\t\ttrigger = {{ has_country_flag = jxp_b_115_open_main_{main} }}", f"\t\tset_country_flag = jxp_b_115_open_secondary_{secondary}", "\t}"))
                loc.append((option, label))
            lines.extend(("\toption = {", f"\t\tname = {key}.none", "\t}", "}", ""))
            loc.extend(((f"{key}.t", "有限副线"), (f"{key}.d", "主方向之外，只能批准另一方向的共同准备与一次专门筹议；其最终章程仍须服从主线。"), (f"{key}.none", "不另设副线")))
    return "\n".join(lines), loc


def _decisions() -> tuple[str, list[tuple[str, str]]]:
    lines = ["country_decisions = {"]
    loc: list[tuple[str, str]] = []
    for index, route in enumerate(ROUTES):
        decision = f"jxp_b_115_{route.key}_external_interaction"
        lines.extend((
            f"\t{decision} = {{",
            "\t\tmajor = yes",
            "\t\tpotential = {",
            route.potential,
            "\t\t}",
            "\t\tallow = {",
        ))
        if route.key == "open":
            lines.append("\t\t\tNOT = { has_country_flag = jxp_b_115_open_strategy_chosen }")
        else:
            if route.key in {"uncommitted", "sakoku"}:
                lines.extend(("\t\t\tOR = {", f"\t\t\t\thas_country_flag = jxp_b_115_{route.key}_interaction_unlocked", "\t\t\t\tmission_completed = jxp_b_115_uncommitted_mainland_01", "\t\t\t}"))
            elif route.key == "toyotomi":
                lines.append("\t\t\tmission_completed = jxp_mission_toyotomi_taiko_testament")
            else:
                lines.append(f"\t\t\thas_country_flag = jxp_b_115_{route.key}_interaction_unlocked")
            lines.extend(("\t\t\tNOT = { has_country_modifier = jxp_b_115_external_interaction_cooldown }", "\t\t\tdip_power = 25"))
        lines.extend(("\t\t}", "\t\teffect = {"))
        if route.key == "open":
            lines.extend(("\t\t\tset_country_flag = jxp_b_115_open_strategy_chosen", f"\t\t\tcountry_event = {{ id = jxp_b_115_routes.{index * 10 + 5} }}"))
        else:
            lines.extend(("\t\t\tadd_dip_power = -25", "\t\t\tadd_country_modifier = {", "\t\t\t\tname = jxp_b_115_external_interaction_cooldown", "\t\t\t\tduration = 3650", "\t\t\t}", f"\t\t\tcountry_event = {{ id = jxp_b_115_routes.{index * 10 + 5} }}"))
        lines.extend((
            "\t\t}",
            "\t\tai_will_do = {",
            "\t\t\tfactor = 1",
            "\t\t\tmodifier = { factor = 0 is_bankrupt = yes }",
            "\t\t\tmodifier = { factor = 0 is_at_war = yes }",
            "\t\t\tmodifier = { factor = 0 num_of_loans = 3 }",
            "\t\t\tmodifier = { factor = 0 NOT = { stability = 0 } }",
            "\t\t\tmodifier = { factor = 0.25 war_exhaustion = 2 }",
            "\t\t}",
            "\t}",
            "",
        ))
        loc.extend(((decision + "_title", route.name + "特别对外会议"), (decision + "_desc", "召集掌握港务、使节和地方约章者，在十年复议期内处理一次对外争端。")))
    lines.extend((
        "\tjxp_b_115_open_naval_charter = {",
        "\t\tmajor = yes",
        "\t\tpotential = {",
        "\t\t\ttag = JAP",
        "\t\t\thas_country_flag = jxp_path_open_trade",
        "\t\t\thas_country_flag = jxp_b_115_open_main_navy",
        "\t\t\tNOT = { has_country_flag = jxp_iface_b_external_capstone_complete }",
        "\t\t}",
        "\t\tallow = {",
        "\t\t\tmission_completed = jxp_mission_eastasia_hegemon_of_the_seas",
        "\t\t\tnavy_size_percentage = 0.8",
        "\t\t\tnavy_tradition = 25",
        "\t\t\tdip_power = 100",
        "\t\t\ttreasury = 300",
        "\t\t}",
        "\t\teffect = {",
        "\t\t\tadd_dip_power = -100",
        "\t\t\tadd_treasury = -300",
        "\t\t\tset_country_flag = jxp_iface_b_external_capstone_complete",
        "\t\t\tadd_country_modifier = {",
        "\t\t\t\tname = jxp_b_115_open_external_capstone",
        "\t\t\t\tduration = 7300",
        "\t\t\t}",
        "\t\t\tcountry_event = { id = jxp_b_115_routes.24 days = 1 }",
        "\t\t}",
        "\t\tai_will_do = {",
        "\t\t\tfactor = 1",
        "\t\t\tmodifier = { factor = 0 is_bankrupt = yes }",
        "\t\t\tmodifier = { factor = 0 is_at_war = yes }",
        "\t\t\tmodifier = { factor = 0 num_of_loans = 3 }",
        "\t\t\tmodifier = { factor = 0 NOT = { stability = 0 } }",
        "\t\t\tmodifier = { factor = 0.25 war_exhaustion = 2 }",
        "\t\t}",
        "\t}",
        "",
    ))
    lines.extend((
        "\tjxp_b_115_open_naval_patrol = {",
        "\t\tmajor = no",
        "\t\tpotential = {",
        "\t\t\ttag = JAP",
        "\t\t\thas_country_flag = jxp_path_open_trade",
        "\t\t\thas_country_flag = jxp_b_115_open_secondary_navy",
        "\t\t}",
        "\t\tallow = {",
        "\t\t\tmission_completed = jxp_mission_eastasia_taiwan_lanes",
        "\t\t\tNOT = { has_country_modifier = jxp_b_115_external_interaction_cooldown }",
        "\t\t\tnavy_size_percentage = 0.6",
        "\t\t\tdip_power = 50",
        "\t\t\ttreasury = 150",
        "\t\t}",
        "\t\teffect = {",
        "\t\t\tadd_dip_power = -50",
        "\t\t\tadd_treasury = -150",
        "\t\t\tadd_navy_tradition = 2",
        "\t\t\tadd_country_modifier = { name = jxp_b_115_open_naval_patrol duration = 3650 }",
        "\t\t\tadd_country_modifier = { name = jxp_b_115_external_interaction_cooldown duration = 3650 }",
        "\t\t\tcountry_event = { id = jxp_b_115_routes.22 days = 1 }",
        "\t\t}",
        "\t\tai_will_do = {",
        "\t\t\tfactor = 1",
        "\t\t\tmodifier = { factor = 0 is_bankrupt = yes }",
        "\t\t\tmodifier = { factor = 0 is_at_war = yes }",
        "\t\t\tmodifier = { factor = 0 num_of_loans = 3 }",
        "\t\t\tmodifier = { factor = 0 NOT = { stability = 0 } }",
        "\t\t\tmodifier = { factor = 0.25 war_exhaustion = 2 }",
        "\t\t}",
        "\t}",
        "",
    ))
    lines.extend((
        "\tjxp_b_115_toyotomi_external_charter = {",
        "\t\tmajor = yes",
        "\t\tpotential = {",
        "\t\t\ttag = TOY",
        "\t\t\tNOT = { has_country_flag = jxp_iface_b_external_capstone_complete }",
        "\t\t}",
        "\t\tallow = {",
        "\t\t\tmission_completed = jxp_mission_toyotomi_taiko_testament",
        "\t\t\tmission_completed = jxp_mission_toyotomi_peace_beneath_heaven",
        "\t\t\tis_at_war = no",
        "\t\t\tstability = 1",
        "\t\t\tadm_power = 100",
        "\t\t\tdip_power = 100",
        "\t\t\ttreasury = 400",
        "\t\t}",
        "\t\teffect = {",
        "\t\t\tadd_adm_power = -100",
        "\t\t\tadd_dip_power = -100",
        "\t\t\tadd_treasury = -400",
        "\t\t\tset_country_flag = jxp_iface_b_external_capstone_complete",
        "\t\t\tadd_country_modifier = { name = jxp_b_115_toyotomi_external_capstone duration = 7300 }",
        "\t\t\tcountry_event = { id = jxp_b_115_routes.114 days = 1 }",
        "\t\t}",
        "\t\tai_will_do = {",
        "\t\t\tfactor = 1",
        "\t\t\tmodifier = { factor = 0 is_bankrupt = yes }",
        "\t\t\tmodifier = { factor = 0 is_at_war = yes }",
        "\t\t\tmodifier = { factor = 0 num_of_loans = 3 }",
        "\t\t\tmodifier = { factor = 0 NOT = { stability = 0 } }",
        "\t\t\tmodifier = { factor = 0.25 war_exhaustion = 2 }",
        "\t\t}",
        "\t}",
        "",
    ))
    loc.extend((
        ("jxp_b_115_open_naval_charter_title", "议定制海奉行章程"),
        ("jxp_b_115_open_naval_charter_desc", "以既有东亚制海任务为制度基础，为远洋舰队、海峡护航和海外补给写定二十年章程；海军主线不另挤占第三条任务列。"),
        ("jxp_b_115_open_naval_patrol_title", "派遣有限制海巡检"),
        ("jxp_b_115_open_naval_patrol_desc", "以有限副线的资格派出十年巡检，护送商船并核查海峡补给；它不会取代既定主线，也不会授予总章。"),
        ("jxp_b_115_toyotomi_external_charter_title", "颁布东亚总和议章程"),
        ("jxp_b_115_toyotomi_external_charter_desc", "在太阁遗命与天下静谧两条既有任务支柱之上，结清军役、遣返和战后交涉，形成二十年有效的东亚总和议。"),
    ))
    lines.append("}")
    return "\n".join(lines) + "\n", loc


def _modifiers() -> str:
    lines = [
        "jxp_b_115_external_interaction_cooldown = {", "\tdiplomatic_upkeep = 1", "}", "",
        "jxp_b_115_open_naval_patrol = {", "\tglobal_ship_trade_power = 0.05", "\tnaval_maintenance_modifier = 0.05", "}", "",
    ]
    for route in ROUTES:
        lines.append(f"jxp_b_115_{route.key}_external_capstone = {{")
        lines.extend(f"\t{key} = {value}" for key, value in route.modifier)
        lines.extend(("}", ""))
    return "\n".join(lines)


def _build() -> None:
    _remove_generated_missions()
    localisation: list[tuple[str, str]] = []
    for route in ROUTES:
        for lane_number, lane_ in enumerate(route.lanes, 1):
            block, lane_loc = _mission_block(route, lane_, lane_number)
            sentinel = f"jxp_b_115_{route.key}_{lane_.kind}_01"
            _insert_into_series(lane_.source, lane_.series, block, sentinel)
            localisation.extend(lane_loc)
    events, event_loc = _events()
    decisions, decision_loc = _decisions()
    localisation.extend(event_loc)
    localisation.extend(decision_loc)
    localisation.append(("jxp_b_115_external_interaction_cooldown", "对外会议复议期"))
    localisation.append(("jxp_b_115_open_naval_patrol", "有限制海巡检"))
    for route in ROUTES:
        localisation.append((f"jxp_b_115_{route.key}_external_capstone", route.name + "对外章程"))
        if route.key not in {"open", "toyotomi"}:
            localisation.append((f"jxp_b_115_{route.key}_interaction_unlocked", route.name + "特别会议资格"))
    localisation.extend((
        ("jxp_iface_b_external_capstone_complete", "对外经略总章已经完成"),
        ("jxp_b_115_open_strategy_chosen", "开国对外主方向已经议定"),
        ("jxp_b_115_open_main_trade", "朱印商贸主线"),
        ("jxp_b_115_open_main_navy", "远洋海军主线"),
        ("jxp_b_115_open_main_settlement", "殖民开拓主线"),
        ("jxp_b_115_open_secondary_trade", "朱印商贸有限副线"),
        ("jxp_b_115_open_secondary_navy", "远洋海军有限副线"),
        ("jxp_b_115_open_secondary_settlement", "殖民开拓有限副线"),
        ("jxp_b_115_open_trade_preparation_tt", "已将朱印商贸定为主线或有限副线"),
        ("jxp_b_115_open_navy_preparation_tt", "已将远洋海军定为主线或有限副线"),
        ("jxp_b_115_open_settlement_preparation_tt", "已将殖民开拓定为主线或有限副线"),
        ("jxp_b_115_open_trade_mainline_tt", "朱印商贸是唯一主线"),
        ("jxp_b_115_open_navy_mainline_tt", "远洋海军是唯一主线"),
        ("jxp_b_115_open_settlement_mainline_tt", "殖民开拓是唯一主线"),
    ))

    _write_utf8_lf(ROOT / "events/jxp_b_115_external_route_events.txt", events)
    _write_utf8_lf(ROOT / "decisions/jxp_b_115_external_route_interactions.txt", decisions)
    _write_utf8_lf(ROOT / "common/event_modifiers/jxp_b_115_external_route_modifiers.txt", _modifiers())
    source = ["l_english:"]
    source.extend(f' {key}:0 "{value}"' for key, value in localisation)
    _write_utf8_lf(ROOT / "localisation_source/jxp_b_115_external_routes_l_english_utf8_source.yml", "\n".join(source) + "\n")


def _generated_paths() -> tuple[str, ...]:
    mission_sources = {lane_.source for route in ROUTES for lane_ in route.lanes}
    mission_sources.add("missions/jxp_70_oda_toyotomi_missions.txt")
    return tuple(sorted(mission_sources)) + (
        "events/jxp_b_115_external_route_events.txt",
        "decisions/jxp_b_115_external_route_interactions.txt",
        "common/event_modifiers/jxp_b_115_external_route_modifiers.txt",
        "localisation_source/jxp_b_115_external_routes_l_english_utf8_source.yml",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="rebuild in isolation and compare bytes")
    args = parser.parse_args()
    if not args.check:
        _build()
        return 0

    global ROOT
    original_root = ROOT
    with tempfile.TemporaryDirectory(prefix=".jxp-b115-check-") as raw_temp:
        temp_root = Path(raw_temp) / "japan_expanded_v2"
        shutil.copytree(original_root / "missions", temp_root / "missions")
        for relative in (
            "events",
            "decisions",
            "common/event_modifiers",
            "localisation_source",
        ):
            (temp_root / relative).mkdir(parents=True, exist_ok=True)
        try:
            ROOT = temp_root
            _build()
        finally:
            ROOT = original_root

        drift = [
            relative
            for relative in _generated_paths()
            if not (temp_root / relative).is_file()
            or (temp_root / relative).read_bytes() != (original_root / relative).read_bytes()
        ]
    if drift:
        for relative in drift:
            print(f"DRIFT {relative}")
        return 1
    print(f"PASS: {len(_generated_paths())} B115 external-route outputs are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
