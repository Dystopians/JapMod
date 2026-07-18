from __future__ import annotations

from pathlib import Path
import re


MOD = Path(__file__).resolve().parents[2]


def write(relative: str, text: str) -> None:
    path = MOD / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def block_end(text: str, key: str) -> int:
    start = text.index(f"{key} = {{")
    brace = text.index("{", start)
    depth = 0
    quoted = False
    escaped = False
    for index in range(brace, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise RuntimeError(f"unterminated {key}")


def inject(text: str, series: str, rendered: str, sentinel: str) -> str:
    if sentinel in text:
        return text
    end = block_end(text, series)
    return text[:end] + "\n" + rendered.rstrip() + "\n" + text[end:]


def set_mission_position(text: str, mission_id: str, position: int) -> str:
    start = text.index(f"\t{mission_id} = {{")
    end = block_end(text, mission_id)
    block = text[start:end]
    updated, count = re.subn(r"(^\s*position\s*=\s*)\d+", rf"\g<1>{position}", block, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"missing mission position: {mission_id}")
    return text[:start] + updated + text[end:]


def strip_generated_completion_flags(text: str) -> str:
    return re.sub(
        r"(?m)^\s*set_country_flag\s*=\s*(?:jxp_b_94_mission_[A-Za-z0-9_]+_completed|jxp_b_95_(?:hkk|njf|oia)_depth_\d+_completed)\s*\n",
        "",
        text,
    )


def mission(mid: str, position: int, required: str, event: str, axis: int) -> str:
    requirement = f"\n\t\trequired_missions = {{ {required} }}" if required else ""
    power = ("adm", "dip", "mil")[axis % 3]
    trigger = (
        "stability = 1 total_development = 100",
        "num_of_ports = 5 navy_size_percentage = 0.60",
        "monthly_income = 12 prestige = 10",
        "manpower_percentage = 0.40 army_size_percentage = 0.60",
    )[axis % 4]
    return f'''\t{mid} = {{
\t\ticon = mission_empire
\t\tposition = {position}{requirement}
\t\ttrigger = {{ {trigger} }}
\t\teffect = {{
\t\t\tadd_{power}_power = {25 + (axis % 3) * 5}
\t\t\tadd_prestige = 3
\t\t\tcountry_event = {{ id = {event} days = 1 }}
\t\t}}
\t}}
'''


NYA_ADDITIONS = [
    ("jxp_b_94_nya_west_coast_missions", "jxp_b_94_mission_chartered_capital", 7, "jxp_b_94_mission_continental_horizon", "jxp_new_yamato.11", "总督城、自治城与公司城"),
    ("jxp_b_94_nya_civic_compact_missions", "jxp_b_94_mission_federal_nation", 9, "jxp_b_94_mission_union_fulfilled", "jxp_new_yamato.12", "联邦国民"),
    ("jxp_b_94_nya_transpacific_economy_missions", "jxp_b_94_mission_pacific_credit_union", 10, "jxp_b_94_mission_pacific_common_market", "jxp_new_yamato.13", "太平洋信用"),
    ("jxp_b_94_nya_republican_state_missions", "jxp_b_94_mission_new_yamato_constitution", 11, "jxp_b_94_mission_enduring_constitution", "jxp_new_yamato.14", "新大和宪法"),
    ("jxp_b_94_nya_independence_return_missions", "jxp_b_94_mission_eastward_or_federation", 12, "jxp_b_94_mission_commonwealth_of_two_shores", "jxp_new_yamato.15", "东归或两洋联邦"),
]


SECONDARY_ADDITIONS = {
    "HKK": [
        ("jxp_b_95_hkk_cold_frontier_missions", ["救难站", "季节航线", "北洋首府"]),
        ("jxp_b_95_hkk_peoples_missions", ["鲑鱼与渔场", "双语通事", "北方共同体"]),
        ("jxp_b_95_hkk_north_pacific_missions", ["樺太据点", "阿拉斯加会所", "俄国边界"]),
        ("jxp_b_95_hkk_rivalry_missions", ["公司总管", "公司审计", "军屯与商社"]),
        ("jxp_b_95_hkk_constitution_missions", ["北方海国"]),
    ],
    "NJF": [
        ("jxp_b_95_njf_port_network_missions", ["马尼拉日本町", "暹罗日本町", "诸港总名簿"]),
        ("jxp_b_95_njf_society_missions", ["清真商区", "地方信仰保护", "混合家庭法"]),
        ("jxp_b_95_njf_commerce_missions", ["公司舰队", "欧洲公司竞争", "南洋商权"]),
        ("jxp_b_95_njf_security_missions", ["王权保护", "宫廷通事", "联合防御"]),
        ("jxp_b_95_njf_federation_missions", ["共同关税", "拒绝本土总管", "日本町联邦"]),
    ],
    "OIA": [
        ("jxp_b_95_oia_navigation_missions", ["淡水泊地", "大洋海图", "航海学宫"]),
        ("jxp_b_95_oia_society_missions", ["婚姻盟约", "共同祭礼", "双语学校"]),
        ("jxp_b_95_oia_ocean_economy_missions", ["远洋船厂", "岛屿商品", "海军基地"]),
        ("jxp_b_95_oia_defense_missions", ["护航会所", "共同舰队", "大洋舰队"]),
        ("jxp_b_95_oia_polity_missions", ["大洋诸岛盟"]),
    ],
}


TPF_COLUMNS = [
    ("old_world", 1, ["日本诸州席位", "旧大名安置", "京都地位", "江户财政", "日本地方自治", "朝廷与联邦", "旧大陆成员国"]),
    ("overseas", 2, ["新大和代表", "北辰代表", "南洋代表", "大洋诸岛代表", "海外州权", "地方公民", "海外成员国"]),
    ("treasury", 3, ["联邦关税", "舰队预算", "跨洋补贴", "公司监管", "联邦公债", "两洋清算", "共同财政"]),
    ("constitution", 4, ["京都与新大和", "固定首都", "双都制", "轮都制", "两院议会", "行政分权", "两洋宪法"]),
    ("survival", 5, ["保皇派", "日本本土分离派", "海外州权派", "公司势力", "联邦军队", "宪制危机", "两洋共同国"]),
]


def slug(text: str) -> str:
    aliases = {
        "日本诸州席位": "japanese_seats", "旧大名安置": "former_daimyo", "京都地位": "kyoto_status", "江户财政": "edo_finance", "日本地方自治": "home_autonomy", "朝廷与联邦": "court_and_federation", "旧大陆成员国": "old_world_member",
        "新大和代表": "nya_delegation", "北辰代表": "hkk_delegation", "南洋代表": "njf_delegation", "大洋诸岛代表": "oia_delegation", "海外州权": "overseas_states", "地方公民": "local_citizens", "海外成员国": "overseas_members",
        "联邦关税": "federal_tariffs", "舰队预算": "fleet_budget", "跨洋补贴": "ocean_subsidies", "公司监管": "company_oversight", "联邦公债": "federal_bonds", "两洋清算": "two_ocean_clearing", "共同财政": "common_treasury",
        "京都与新大和": "kyoto_and_nya", "固定首都": "fixed_capital", "双都制": "dual_capitals", "轮都制": "rotating_capital", "两院议会": "two_chambers", "行政分权": "administrative_devolution", "两洋宪法": "two_ocean_constitution",
        "保皇派": "royalists", "日本本土分离派": "home_separatists", "海外州权派": "overseas_rights", "公司势力": "company_bloc", "联邦军队": "federal_army", "宪制危机": "constitutional_crisis", "两洋共同国": "common_country",
    }
    return aliases[text]


def build_missions() -> dict[str, tuple[str, str]]:
    loc: dict[str, tuple[str, str]] = {}
    path = MOD / "missions/jxp_b_94_new_yamato_missions.txt"
    text = strip_generated_completion_flags(path.read_text(encoding="utf-8-sig")).replace("potential = { OR = { tag = NYA tag = TPF } }", "potential = { tag = NYA }")
    for index, (series, mid, pos, req, event, title) in enumerate(NYA_ADDITIONS):
        text = inject(text, series, mission(mid, pos, req, event, index), mid)
        text = set_mission_position(text, mid, pos)
        loc[mid] = (title, f"以成文约章处理{title}，在地方自治、本土遗产与共同财政之间建立可长期维持的制度。")
    path.write_text(text, encoding="utf-8", newline="\n")

    path = MOD / "missions/jxp_b_95_secondary_colonial_states_missions.txt"
    text = strip_generated_completion_flags(path.read_text(encoding="utf-8-sig"))
    event_bases = {"HKK": 9, "NJF": 109, "OIA": 209}
    counters = {tag: 0 for tag in SECONDARY_ADDITIONS}
    for tag, columns in SECONDARY_ADDITIONS.items():
        prefix = tag.lower()
        for series, titles in columns:
            series_text = text[text.index(series):block_end(text, series)]
            current = [line.split("=")[0].strip() for line in series_text.splitlines() if line.startswith("\tjxp_b_95_") and "=" in line]
            base_series_text = series_text.split(f"\tjxp_b_95_{prefix}_depth_", 1)[0]
            last_position = max(int(value) for value in re.findall(r"^\s*position\s*=\s*(\d+)", base_series_text, re.MULTILINE))
            required = current[-1]
            blocks = ""
            for offset, title in enumerate(titles):
                ordinal = counters[tag]
                mid = f"jxp_b_95_{prefix}_depth_{ordinal + 1:02d}"
                pos = last_position + (offset + 1) * 2
                eid = f"jxp_secondary_colonies.{event_bases[tag] + (ordinal % ({'HKK':8,'NJF':10,'OIA':8}[tag]))}"
                blocks += mission(mid, pos, required, eid, ordinal)
                required = mid
                loc[mid] = (title, f"令{title}不只是远方据点的口号，而成为当地居民、港市与国家共同承担的长期制度。")
                counters[tag] += 1
            text = inject(text, series, blocks, f"jxp_b_95_{prefix}_depth_{counters[tag]:02d}")
            for local_offset in range(len(titles)):
                ordinal = counters[tag] - len(titles) + local_offset + 1
                text = set_mission_position(text, f"jxp_b_95_{prefix}_depth_{ordinal:02d}", last_position + (local_offset + 1) * 2)
    path.write_text(text, encoding="utf-8", newline="\n")

    out = ["# TPF owns an independent five-column mission tree; it never reuses NYA series.\n"]
    event_id = 11
    for column, slot, titles in TPF_COLUMNS:
        series = f"jxp_b_114_tpf_{column}_missions"
        out += [f"{series} = {{", f"\tslot = {slot}", "\tgeneric = no", "\tai = yes", "\tpotential = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_federation_dissolved } }", "\thas_country_shield = yes", ""]
        previous = ""
        for row, title in enumerate(titles):
            mid = f"jxp_b_114_tpf_{slug(title)}"
            pos = 1 + row * 2 if slot % 2 else 2 + row * 2
            out.append(mission(mid, pos, previous, f"jxp_transpacific_state.{event_id + (row % 17)}", row + slot).rstrip())
            previous = mid
            loc[mid] = (title, f"联邦必须通过公开协商落实{title}，使旧大陆与海外诸州在承担共同代价的同时保留真实代表权。")
        out += ["}", ""]
        event_id += 3
    write("missions/jxp_b_114_transpacific_federation_missions.txt", "\n".join(out))
    return loc


STATE_EVENTS = {
    "NYA": ("jxp_new_yamato", list(range(11, 21)), ["城市宪章之争", "联邦国民名簿", "太平洋信用会议", "新大和制宪日", "东归派与联邦派", "独立战争老兵", "保皇派报章", "当地首领大会", "州界测量争议", "公司旧债清算"]),
    "HKK": ("jxp_secondary_colonies", list(range(9, 17)), ["强制劳役争议", "海獭价格暴跌", "樺太通事请愿", "军屯要求", "船员冻伤", "地方议席扩充", "北方边界条约", "公司私兵政变"]),
    "NJF": ("jxp_secondary_colonies", list(range(109, 119)), ["日本町自治章程", "当地王权更替", "日本佣兵干政", "多宗教婚姻", "港市法冲突", "欧洲公司要求", "当地商人议席", "日本移民减少", "诸港关税争议", "联邦首席之争"]),
    "OIA": ("jxp_secondary_colonies", list(range(209, 217)), ["失踪船队", "岛屿王族婚姻", "土地边界", "淡水危机", "公司征地", "岛屿间关税", "远方岛屿自治", "航路重建"]),
    "TPF": ("jxp_transpacific_state", list(range(11, 28)), ["京都代表团", "新大和州权", "北辰补贴", "南洋关税", "岛屿舰队", "公司游说", "联邦公债", "朝廷席位", "旧大名请愿", "海外当地代表", "双都行政", "轮都争议", "联邦军指挥", "日本分离派", "海外独立派", "共同国籍", "联邦解体大会"]),
}


def build_events() -> dict[str, tuple[str, str]]:
    loc: dict[str, tuple[str, str]] = {}
    by_namespace: dict[str, list[str]] = {}
    pictures = {
        "NYA": "jxp_b_new_yamato_assembly_eventPicture",
        "HKK": "jxp_b_north_pacific_frontier_eventPicture",
        "NJF": "jxp_b_southern_port_league_eventPicture",
        "OIA": "jxp_b_oceanic_league_eventPicture",
        "TPF": "jxp_b_transpacific_federation_eventPicture",
    }
    for tag, (namespace, ids, titles) in STATE_EVENTS.items():
        by_namespace.setdefault(namespace, [f"namespace = {namespace}", ""])
        for ordinal, (eid, title) in enumerate(zip(ids, titles)):
            key = f"{namespace}.{eid}"
            by_namespace[namespace].append(f'''country_event = {{
\tid = {key}
\ttitle = "{key}.t"
\tdesc = "{key}.d"
\tpicture = {pictures[tag]}
\tis_triggered_only = yes
\toption = {{
\t\tname = "{key}.a"
\t\tadd_prestige = 2
\t\tadd_dip_power = -20
\t\tjxp_b_91_add_compact_5_effect = yes
\t\tai_chance = {{ factor = 3 }}
\t}}
\toption = {{
\t\tname = "{key}.b"
\t\tadd_treasury = -40
\t\tadd_adm_power = 15
\t\tjxp_b_91_add_identity_5_effect = yes
\t\tai_chance = {{ factor = 2 modifier = {{ factor = 0.25 num_of_loans = 4 }} }}
\t}}
}}
''')
            loc[key] = (title, f"围绕“{title}”的争论迫使国家承认：跨海国家的制度不能只由旧总督、军官或公司单方面决定。")
    write("events/jxp_b_110_colonial_state_depth_events.txt", "\n".join(by_namespace["jxp_new_yamato"]))
    write("events/jxp_b_111_secondary_state_depth_events.txt", "\n".join(by_namespace["jxp_secondary_colonies"]))
    write("events/jxp_b_114_transpacific_depth_events.txt", "\n".join(by_namespace["jxp_transpacific_state"]))
    return loc


LEGACIES = ["undecided", "closed_country", "open_country", "commercial_council", "buddhist", "kirishitan", "confucian", "imperial", "reformed", "sultanate", "ikko", "wakou", "toyotomi"]


def build_legacy_effects() -> None:
    clears = "\n".join(f"\tclr_country_flag = jxp_b_legacy_{x}" for x in LEGACIES)
    selectors = [
        ("tag = TOY", "toyotomi"),
        ("OR = { has_country_flag = jxp_iface_a_company_state_route has_country_flag = jxp_path_commercial_council }", "commercial_council"),
        ("has_country_flag = jxp_path_sakoku", "closed_country"), ("has_country_flag = jxp_path_open_trade", "open_country"),
        ("has_country_flag = jxp_path_buddhist", "buddhist"), ("OR = { tag = KJP has_country_flag = jxp_path_kirishitan }", "kirishitan"),
        ("OR = { tag = CJP has_country_flag = jxp_path_confucian }", "confucian"), ("OR = { tag = EJP has_country_flag = jxp_path_imperial }", "imperial"),
        ("OR = { tag = RFJ has_country_flag = jxp_path_reformed }", "reformed"), ("OR = { tag = SJP has_country_flag = jxp_path_kaikyo }", "sultanate"),
        ("OR = { tag = IJP has_country_flag = jxp_path_ikko }", "ikko"), ("OR = { tag = WAK has_country_flag = jxp_path_wokou }", "wakou"),
    ]
    chain = []
    for i, (condition, legacy) in enumerate(selectors):
        keyword = "if" if i == 0 else "else_if"
        chain.append(f"\t\t{keyword} = {{ limit = {{ {condition} }} set_country_flag = jxp_b_legacy_{legacy} }}")
    chain.append("\t\telse = { set_country_flag = jxp_b_legacy_undecided }")
    reconcile = []
    for i, legacy in enumerate(reversed(LEGACIES)):
        keyword = "if" if i == 0 else "else_if"
        reconcile.append(f"\t{keyword} = {{ limit = {{ has_country_flag = jxp_b_legacy_{legacy} }} jxp_b_clear_all_metropole_legacies_effect = yes set_country_flag = jxp_b_legacy_{legacy} }}")
    text = f'''jxp_b_clear_all_metropole_legacies_effect = {{
{clears}
}}

jxp_b_record_metropole_legacy = {{
\tif = {{
\t\tlimit = {{ NOT = {{ has_country_flag = jxp_iface_b_metropole_legacy_recorded }} }}
\t\tjxp_b_clear_all_metropole_legacies_effect = yes
{chr(10).join(chain)}
\t\tset_country_flag = jxp_iface_b_metropole_legacy_recorded
\t}}
}}

jxp_b_clear_duplicate_metropole_legacies = {{
{chr(10).join(reconcile)}
}}

jxp_b_reconcile_metropole_legacy = {{
\tif = {{ limit = {{ has_country_flag = jxp_iface_b_metropole_legacy_recorded }} jxp_b_clear_duplicate_metropole_legacies = yes }}
\telse = {{ jxp_b_record_metropole_legacy = yes }}
}}

jxp_b_clear_colonial_factions_effect = {{
\tclr_country_flag = jxp_b_faction_dominant_assembly
\tclr_country_flag = jxp_b_faction_dominant_company
\tclr_country_flag = jxp_b_faction_dominant_military
\tclr_country_flag = jxp_b_faction_dominant_local
\tclr_country_flag = jxp_b_faction_dominant_royalist
}}

jxp_b_set_colonial_faction_balance_effect = {{
\tjxp_b_clear_colonial_factions_effect = yes
\tif = {{ limit = {{ jxp_b_91_local_compact_at_least_60_trigger = yes }} set_country_flag = jxp_b_faction_dominant_local }}
\telse_if = {{ limit = {{ jxp_b_91_metropole_control_at_least_60_trigger = yes }} set_country_flag = jxp_b_faction_dominant_royalist }}
\telse_if = {{ limit = {{ has_reform = jxp_b_94_merchant_commonwealth_reform }} set_country_flag = jxp_b_faction_dominant_company }}
\telse_if = {{ limit = {{ OR = {{ has_reform = jxp_b_94_frontier_military_republic_reform has_reform = jxp_b_95_hkk_frontier_bakufu_reform }} }} set_country_flag = jxp_b_faction_dominant_military }}
\telse = {{ set_country_flag = jxp_b_faction_dominant_assembly }}
}}
'''
    write("common/scripted_effects/jxp_b_110_colonial_depth_effects.txt", text)


SHARED_DECISIONS = [
    ("local_assembly", "召开地方议会"), ("land_commission", "设立土地委员会"), ("citizen_roll", "改订公民名簿"),
    ("renegotiate_charter", "重新谈判公司章程"), ("petition_autonomy", "请求母国自治"), ("colonial_militia", "组织殖民民兵"),
    ("foreign_mediation", "邀请外国调停"), ("local_shipyards", "建立本地船厂"), ("religious_toleration", "颁布宗教宽容"),
    ("independence_convention", "准备独立大会"),
]


STATE_DECISIONS = {
    "NYA": ["召开大陆会议", "制定土地条约", "设立联邦首都", "发行独立公债", "请求外国承认", "港口抵制", "民兵联防", "解放殖民请愿", "准备东归", "召开两洋制宪会议"],
    "HKK": ["扩建冬仓", "审计北海会社", "召集北方议席", "缔结边界条约", "终结公司专政"],
    "NJF": ["登记诸港日本町", "制定共同关税", "保护多宗教街区", "审计朱印商社", "召集当地王权", "整编港市民兵", "终结诸港离心"],
    "OIA": ["重绘大洋海图", "确认王统议席", "维持共同舰队", "救济远方岛屿", "重建断裂航路"],
    "TPF": ["召开两洋议会", "确认旧大陆席位", "确认海外州权", "编列共同财政", "发行联邦公债", "选择双都制度", "整编联邦军", "调停公司游说", "解决宪制危机", "依法解散联邦"],
}


def build_decisions() -> dict[str, tuple[str, str]]:
    loc: dict[str, tuple[str, str]] = {}
    lines = ["country_decisions = {"]
    lines.append('''\tjxp_b_110_open_state_guide = {
\t\tmajor = yes
\t\tpotential = { OR = { tag = NYA tag = HKK tag = NJF tag = OIA tag = TPF } }
\t\tallow = { always = yes }
\t\teffect = { country_event = { id = jxp_colonial_depth.1 days = 1 } }
\t\tai_will_do = { factor = 0 }
\t}''')
    loc["jxp_b_110_open_state_guide"] = ("阅览海外国体图志", "查阅母国遗产、殖民社会状态、当前派系、宪章、独立道路、当地社会与两洋联邦资格。")
    for idx, (slug_name, title) in enumerate(SHARED_DECISIONS):
        key = f"jxp_b_110_{slug_name}"
        lines.append(f'''\t{key} = {{
\t\tpotential = {{ OR = {{ tag = NYA tag = HKK tag = NJF tag = OIA tag = TPF has_country_flag = jxp_b_colonial_society_active }} }}
\t\tallow = {{ is_at_war = no stability = 0 adm_power = 50 dip_power = 50 }}
\t\teffect = {{ add_adm_power = -50 add_dip_power = -50 add_prestige = 2 jxp_b_91_add_compact_5_effect = yes jxp_b_set_colonial_faction_balance_effect = yes }}
\t\tai_will_do = {{ factor = 0.15 modifier = {{ factor = 0 has_any_disaster = yes }} }}
\t}}''')
        loc[key] = (title, f"以公开支出和政治协商{title}。此举会强化地方盟约，但不会凭空消除公司、军队或母国留下的利益冲突。")
    lines.append("}")
    write("decisions/jxp_b_110_colonial_state_decisions.txt", "\n\n".join(lines))

    lines = ["country_decisions = {"]
    tag_bases = {"NYA": 16, "HKK": 9, "NJF": 109, "OIA": 209, "TPF": 11}
    crisis_bases = {"NYA": 1, "HKK": 11, "NJF": 21, "OIA": 31, "TPF": 41}
    for tag, titles in STATE_DECISIONS.items():
        prefix = tag.lower()
        for idx, title in enumerate(titles, 1):
            key = f"jxp_b_111_{prefix}_action_{idx:02d}"
            event_ns = "jxp_new_yamato" if tag == "NYA" else "jxp_secondary_colonies" if tag != "TPF" else "jxp_transpacific_state"
            event_count = len(STATE_EVENTS[tag][1])
            event = f"{event_ns}.{tag_bases[tag] + ((idx - 1) % event_count)}"
            resolve = ""
            if idx == len(titles):
                resolve = (
                    f" set_country_flag = jxp_b_{prefix}_crisis_resolved"
                    f" country_event = {{ id = jxp_colonial_state_crisis.{crisis_bases[tag] + 1} days = 1 }}"
                )
            if tag == "TPF" and idx == len(titles):
                resolve += " set_country_flag = jxp_b_tpf_federation_dissolved remove_country_modifier = jxp_b_98_two_ocean_federal_burdens remove_government_reform = jxp_b_two_ocean_federation_reform remove_government_reform = jxp_b_114_old_world_directed_federation_reform remove_government_reform = jxp_b_114_overseas_rights_confederation_reform remove_government_reform = jxp_b_114_two_ocean_directorate_reform every_subject_country = { add_liberty_desire = 100 } add_stability = -2 add_prestige = -25"
                resolve += " if = { limit = { has_country_flag = jxp_b_114_tpf_origin_nya NOT = { exists = NYA } } change_tag = NYA } else_if = { limit = { has_country_flag = jxp_b_114_tpf_origin_hkk NOT = { exists = HKK } } change_tag = HKK } else_if = { limit = { has_country_flag = jxp_b_114_tpf_origin_njf NOT = { exists = NJF } } change_tag = NJF } else_if = { limit = { has_country_flag = jxp_b_114_tpf_origin_oia NOT = { exists = OIA } } change_tag = OIA } on_change_tag_effect = yes jxp_refresh_route_missions_effect = yes"
            lines.append(f'''\t{key} = {{
\t\tpotential = {{ tag = {tag} }}
\t\tallow = {{ is_at_war = no stability = 0 treasury = {100 + idx * 20} }}
\t\teffect = {{ add_treasury = -{100 + idx * 20} add_prestige = 3 jxp_b_91_add_identity_5_effect = yes{resolve} country_event = {{ id = {event} days = 1 }} }}
\t\tai_will_do = {{ factor = 0.10 modifier = {{ factor = 0 num_of_loans = 4 }} }}
\t}}''')
            loc[key] = (title, f"动用国库并经过代表会议落实{title}。政治成果依赖持续协商，不能以一次决议抹去跨洋距离和地方权利。")
    lines.append("}")
    write("decisions/jxp_b_111_colonial_state_actions.txt", "\n\n".join(lines))
    return loc


def build_tpf_reforms() -> dict[str, tuple[str, str]]:
    path = MOD / "common/government_reforms/jxp_b_98_transpacific_state_reform.txt"
    text = path.read_text(encoding="utf-8-sig")
    additions = '''

jxp_b_114_old_world_directed_federation_reform = {
\ticon = "ballot_box" republic = yes allow_normal_conversion = no lock_level_when_selected = yes valid_for_nation_designer = no
\tpotential = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_federation_dissolved } } trigger = { tag = TPF has_country_flag = jxp_iface_transpacific_state_created }
\tmodifiers = { global_tax_modifier = 0.10 governing_capacity_modifier = -0.05 global_unrest = 1 }
}

jxp_b_114_overseas_rights_confederation_reform = {
\ticon = "ballot_box" republic = yes allow_normal_conversion = no lock_level_when_selected = yes valid_for_nation_designer = no
\tpotential = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_federation_dissolved } } trigger = { tag = TPF has_country_flag = jxp_iface_transpacific_state_created }
\tmodifiers = { diplomatic_reputation = 1 global_trade_power = 0.10 land_forcelimit_modifier = -0.10 }
}

jxp_b_114_two_ocean_directorate_reform = {
\ticon = "ballot_box" republic = yes allow_normal_conversion = no lock_level_when_selected = yes valid_for_nation_designer = no
\tpotential = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_federation_dissolved } } trigger = { tag = TPF has_country_flag = jxp_iface_transpacific_state_created }
\tmodifiers = { land_forcelimit_modifier = 0.15 army_tradition = 0.5 reform_progress_growth = -0.10 global_unrest = 2 }
}
'''
    if "jxp_b_114_old_world_directed_federation_reform" not in text:
        text = text.rstrip() + additions
    text = text.replace('icon = "parliament_hall"', 'icon = "ballot_box"').replace('icon = "military_council"', 'icon = "ballot_box"')
    text = text.replace("modifiers = { administrative_efficiency = 0.05 discipline = 0.025 global_unrest = 2 }", "modifiers = { land_forcelimit_modifier = 0.15 army_tradition = 0.5 reform_progress_growth = -0.10 global_unrest = 2 }")
    text = text.replace("potential = { tag = TPF }", "potential = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_federation_dissolved } }")
    path.write_text(text, encoding="utf-8", newline="\n")
    return {
        "jxp_b_114_old_world_directed_federation_reform": ("旧大陆主导联邦", "以日本本土财政和官署统摄两洋；中央动员更强，但海外州权派会把每次征发视为旧统治的回归。"),
        "jxp_b_114_overseas_rights_confederation_reform": ("海外州权邦联", "海外诸州保留广泛税制与民兵权，共同外交依靠协商维系；贸易活跃，却难以迅速组织大陆战争。"),
        "jxp_b_114_two_ocean_directorate_reform": ("两洋执政府", "跨洋危机催生由军政执政府统筹财政与舰队的强势政体；效率以议会不满和地方动荡为代价。"),
    }


def build_crisis_events() -> dict[str, tuple[str, str]]:
    specs = [
        ("nya", "NYA", "新大和国体危机", 1),
        ("hkk", "HKK", "北辰海国边疆危机", 11),
        ("njf", "NJF", "诸港离心", 21),
        ("oia", "OIA", "航路断裂", 31),
        ("tpf", "TPF", "两洋宪制危机", 41),
    ]
    event_lines = ["namespace = jxp_colonial_state_crisis", "", r'''country_event = {
	id = jxp_colonial_state_crisis.50
	title = none
	desc = none
	picture = DEBATE_REPUBLICAN_eventPicture
	hidden = yes
	is_triggered_only = yes
	trigger = {
		normal_or_historical_nations = yes
		is_year = 1500
		has_any_disaster = no
		OR = { NOT = { stability = 0 } num_of_loans = 4 war_exhaustion = 6 }
		OR = {
			AND = { tag = NYA NOT = { has_country_flag = jxp_b_nya_crisis_active } NOT = { has_country_flag = jxp_b_nya_crisis_resolved } }
			AND = { tag = HKK NOT = { has_country_flag = jxp_b_hkk_crisis_active } NOT = { has_country_flag = jxp_b_hkk_crisis_resolved } }
			AND = { tag = NJF NOT = { has_country_flag = jxp_b_njf_crisis_active } NOT = { has_country_flag = jxp_b_njf_crisis_resolved } }
			AND = { tag = OIA NOT = { has_country_flag = jxp_b_oia_crisis_active } NOT = { has_country_flag = jxp_b_oia_crisis_resolved } }
			AND = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_crisis_active } NOT = { has_country_flag = jxp_b_tpf_crisis_resolved } }
		}
	}
	immediate = {
		if = { limit = { tag = NYA } country_event = { id = jxp_colonial_state_crisis.1 days = 1 } }
		else_if = { limit = { tag = HKK } country_event = { id = jxp_colonial_state_crisis.11 days = 1 } }
		else_if = { limit = { tag = NJF } country_event = { id = jxp_colonial_state_crisis.21 days = 1 } }
		else_if = { limit = { tag = OIA } country_event = { id = jxp_colonial_state_crisis.31 days = 1 } }
		else_if = { limit = { tag = TPF } country_event = { id = jxp_colonial_state_crisis.41 days = 1 } }
	}
	option = { name = "OK" }
}
''']
    loc: dict[str, tuple[str, str]] = {}
    for slug_name, tag, title, base in specs:
        event_lines.append(f'''country_event = {{
\tid = jxp_colonial_state_crisis.{base}
\ttitle = "jxp_colonial_state_crisis.{base}.t"
\tdesc = "jxp_colonial_state_crisis.{base}.d"
\tpicture = DEBATE_REPUBLICAN_eventPicture
\thidden = yes
\tis_triggered_only = yes
\toption = {{ name = "jxp_colonial_state_crisis.{base}.a" set_country_flag = jxp_b_{slug_name}_crisis_active set_country_flag = jxp_b_{slug_name}_crisis_pulse_scheduled country_event = {{ id = jxp_colonial_state_crisis.{base + 2} days = 365 }} }}
}}

country_event = {{
\tid = jxp_colonial_state_crisis.{base + 1}
\ttitle = "jxp_colonial_state_crisis.{base + 1}.t"
\tdesc = "jxp_colonial_state_crisis.{base + 1}.d"
\tpicture = DEBATE_REPUBLICAN_eventPicture
\thidden = yes
\tis_triggered_only = yes
\toption = {{ name = "jxp_colonial_state_crisis.{base + 1}.a" clr_country_flag = jxp_b_{slug_name}_crisis_active clr_country_flag = jxp_b_{slug_name}_crisis_pulse_scheduled }}
}}

country_event = {{
\tid = jxp_colonial_state_crisis.{base + 2}
\ttitle = "jxp_colonial_state_crisis.{base + 2}.t"
\tdesc = "jxp_colonial_state_crisis.{base + 2}.d"
\tpicture = DEBATE_REPUBLICAN_eventPicture
\thidden = yes
\tis_triggered_only = yes
\ttrigger = {{ tag = {tag} has_country_flag = jxp_b_{slug_name}_crisis_active }}
\timmediate = {{ clr_country_flag = jxp_b_{slug_name}_crisis_pulse_scheduled }}
\toption = {{ name = "jxp_colonial_state_crisis.{base + 2}.a" add_treasury = -75 add_prestige = 2 jxp_b_91_add_compact_5_effect = yes }}
\toption = {{ name = "jxp_colonial_state_crisis.{base + 2}.b" add_stability = -1 add_treasury = 75 jxp_b_91_subtract_compact_5_effect = yes }}
\tafter = {{ if = {{ limit = {{ has_country_flag = jxp_b_{slug_name}_crisis_active NOT = {{ has_country_flag = jxp_b_{slug_name}_crisis_pulse_scheduled }} }} set_country_flag = jxp_b_{slug_name}_crisis_pulse_scheduled country_event = {{ id = jxp_colonial_state_crisis.{base + 2} days = 365 }} }} }}
}}
''')
        for offset, label in enumerate(("危机开始", "危机结束", "年度调停")):
            key = f"jxp_colonial_state_crisis.{base + offset}"
            loc[key] = (
                f"{title}：{label}",
                f"围绕{title}的各方再次集会。任何一方都无法在不承担财政、稳定或代表权代价的情况下单独获胜。",
            )
    write("events/jxp_b_111_colonial_state_crisis_events.txt", "\n".join(event_lines))
    write("common/on_actions/jxp_b_110_colonial_state_crisis_on_actions.txt", '''on_yearly_pulse = {
\tevents = { jxp_colonial_state_crisis.50 }
}
''')
    return loc


def guide_event() -> dict[str, tuple[str, str]]:
    write("events/jxp_b_110_colonial_state_guide_events.txt", '''namespace = jxp_colonial_depth

country_event = {
\tid = jxp_colonial_depth.1
\ttitle = "jxp_colonial_depth.1.t"
\tdesc = { trigger = { has_country_flag = jxp_b_faction_dominant_assembly } desc = "jxp_colonial_depth.1.assembly.d" }
\tdesc = { trigger = { has_country_flag = jxp_b_faction_dominant_company } desc = "jxp_colonial_depth.1.company.d" }
\tdesc = { trigger = { has_country_flag = jxp_b_faction_dominant_military } desc = "jxp_colonial_depth.1.military.d" }
\tdesc = { trigger = { has_country_flag = jxp_b_faction_dominant_local } desc = "jxp_colonial_depth.1.local.d" }
\tdesc = { trigger = { has_country_flag = jxp_b_faction_dominant_royalist } desc = "jxp_colonial_depth.1.royalist.d" }
\tdesc = { trigger = { NOT = { OR = { has_country_flag = jxp_b_faction_dominant_assembly has_country_flag = jxp_b_faction_dominant_company has_country_flag = jxp_b_faction_dominant_military has_country_flag = jxp_b_faction_dominant_local has_country_flag = jxp_b_faction_dominant_royalist } } } desc = "jxp_colonial_depth.1.d" }
\tpicture = COURT_eventPicture
\tis_triggered_only = yes
\timmediate = { jxp_b_reconcile_metropole_legacy = yes jxp_b_set_colonial_faction_balance_effect = yes }
\toption = { name = "jxp_colonial_depth.1.a" }
}
''')
    return {"jxp_colonial_depth.1": ("海外国体图志", "本图志记录建国时已经封存的母国遗产、海外共同身份、本土控制、地方盟约、当前宪章与主导派系，并说明独立、对日关系及两洋联邦所需的政治条件。母国日后改道，不会改写这一历史起源。")}


def patch_formation_effects() -> None:
    targets = [
        ("common/scripted_effects/jxp_b_94_new_yamato_effects.txt", "\tjxp_b_94_clear_japanese_home_paths_effect = yes", "\tjxp_b_record_metropole_legacy = yes\n\tjxp_b_94_clear_japanese_home_paths_effect = yes"),
        ("common/scripted_effects/jxp_b_95_secondary_states_effects.txt", "\tjxp_b_95_clear_japanese_home_paths_effect = yes", "\tjxp_b_record_metropole_legacy = yes\n\tjxp_b_95_clear_japanese_home_paths_effect = yes"),
        ("common/scripted_effects/jxp_b_98_transpacific_state_effects.txt", "jxp_b_98_form_two_ocean_federation_effect = {\n\tjxp_b_reconcile_metropole_legacy = yes\n\tchange_tag = TPF", "jxp_b_98_form_two_ocean_federation_effect = {\n\tjxp_b_reconcile_metropole_legacy = yes\n\tif = { limit = { tag = NYA } set_country_flag = jxp_b_114_tpf_origin_nya }\n\telse_if = { limit = { tag = HKK } set_country_flag = jxp_b_114_tpf_origin_hkk }\n\telse_if = { limit = { tag = NJF } set_country_flag = jxp_b_114_tpf_origin_njf }\n\telse_if = { limit = { tag = OIA } set_country_flag = jxp_b_114_tpf_origin_oia }\n\tchange_tag = TPF"),
    ]
    for relative, old, new in targets:
        path = MOD / relative
        text = path.read_text(encoding="utf-8-sig")
        if new not in text:
            if old not in text:
                raise RuntimeError(f"formation anchor drift: {relative}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def build_localisation(parts: list[dict[str, tuple[str, str]]]) -> None:
    labels = {
        "undecided": "公议未定遗产", "closed_country": "锁国遗产", "open_country": "开国遗产", "commercial_council": "商议会社国家遗产", "buddhist": "佛教诸宗遗产",
        "kirishitan": "吉利支丹遗产", "confucian": "礼制经世遗产", "imperial": "王政复古遗产", "reformed": "会众契约遗产",
        "sultanate": "海峡诸法遗产", "ikko": "门徒共同体遗产", "wakou": "自由港船主遗产", "toyotomi": "太阁奉行遗产",
    }
    entries: dict[str, tuple[str, str]] = {}
    for part in parts:
        entries.update(part)
    lines = ["l_english:"]
    for legacy, title in labels.items():
        lines.append(f' jxp_b_legacy_{legacy}:0 "{title}"')
        lines.append(f' jxp_b_legacy_{legacy}_desc:0 "此遗产只记录建国时的母国制度起源，并影响事件、改革与外交选择；它不会无代价提供永久全国增益。"')
    for flag, title in [("assembly", "议会派"), ("company", "公司派"), ("military", "军务派"), ("local", "地方盟约派"), ("royalist", "保皇派")]:
        lines.append(f' jxp_b_faction_dominant_{flag}:0 "{title}主导"')
    lines += [
        ' jxp_colonial_depth.1.assembly.d:0 "议会派目前主导国体。母国遗产、三项殖民社会状态、现行约章与对日终局都必须经过代表会议复议。"',
        ' jxp_colonial_depth.1.company.d:0 "公司派目前主导国体。港务资本仍具分量，但地方居民、债权人与议会保留否决和退出渠道。"',
        ' jxp_colonial_depth.1.military.d:0 "军务派目前主导国体。边疆防务压过日常议政，继续动员会增加财政负担与地方反弹。"',
        ' jxp_colonial_depth.1.local.d:0 "地方盟约派目前主导国体。当地社群、港市和原有王统已取得制度席位，对外扩张必须尊重既定约章。"',
        ' jxp_colonial_depth.1.royalist.d:0 "保皇派目前主导国体。来自日本本土的官署与旧法仍有号召力，却不能抹去跨海社会已经形成的权利。"',
    ]
    lines += [
        ' jxp_b_nya_crisis_resolved:0 "新大和国体危机已经平息"',
        ' jxp_b_hkk_crisis_resolved:0 "北辰海国边疆危机已经平息"',
        ' jxp_b_njf_crisis_resolved:0 "南洋联邦港市危机已经平息"',
        ' jxp_b_oia_crisis_resolved:0 "诸岛盟航路危机已经平息"',
        ' jxp_b_tpf_crisis_resolved:0 "两洋联邦宪制危机已经平息"',
        ' jxp_b_tpf_federation_dissolved:0 "两洋联邦已经依法解体"',
        ' jxp_b_114_tpf_origin_nya:0 "联邦源自新大和合众国"',
        ' jxp_b_114_tpf_origin_hkk:0 "联邦源自北辰海国"',
        ' jxp_b_114_tpf_origin_njf:0 "联邦源自南洋日本町联邦"',
        ' jxp_b_114_tpf_origin_oia:0 "联邦源自大洋诸岛盟"',
        ' jxp_b_110_colonial_depth_migrated:0 "殖民继承国制度已经完成迁移"',
    ]
    for key, (title, desc) in sorted(entries.items()):
        if key.startswith("jxp_b_") and ("mission_" in key or "_depth_" in key or key.startswith("jxp_b_114_tpf_")):
            lines.append(f' {key}_title:0 "{title}"')
            lines.append(f' {key}_desc:0 "{desc}"')
        elif key.startswith("jxp_b_") and ("action_" in key or key.startswith("jxp_b_110_")):
            lines.append(f' {key}_title:0 "{title}"')
            lines.append(f' {key}_desc:0 "{desc}"')
        elif key.startswith("jxp_b_"):
            lines.append(f' {key}:0 "{title}"')
            lines.append(f' {key}_desc:0 "{desc}"')
        else:
            lines.append(f' {key}.t:0 "{title}"')
            lines.append(f' {key}.d:0 "{desc}"')
            lines.append(f' {key}.a:0 "以公开协商承担代价。"')
            lines.append(f' {key}.b:0 "优先维持国家动员。"')
    source = "localisation_source/jxp_b_110_colonial_state_depth_l_english_utf8_source.yml"
    write(source, "\n".join(lines))


def main() -> None:
    mission_loc = build_missions()
    event_loc = build_events()
    build_legacy_effects()
    decision_loc = build_decisions()
    reform_loc = build_tpf_reforms()
    crisis_loc = build_crisis_events()
    guide_loc = guide_event()
    patch_formation_effects()
    build_localisation([mission_loc, event_loc, decision_loc, reform_loc, crisis_loc, guide_loc])


if __name__ == "__main__":
    main()
