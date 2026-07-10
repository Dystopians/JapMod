#!/usr/bin/env python3
"""Generate new daimyo tags, histories, diplomacy, flags, ideas, and source localisation."""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
HISTORY_PLAN_PATH = SCRIPT_DIR / "history_plan.json"
LOCALISATION_PLAN_PATH = SCRIPT_DIR / "localisation_plan.json"
DAIMYO_IDENTITY_PLAN_PATH = SCRIPT_DIR / "daimyo_identity_plan.json"
COMPATIBILITY_CONTRACT_PATH = (
    MOD_ROOT / "tools" / "jxp_map_validation" / "main_compatibility_contract.json"
)
NATIONAL_IDEA_COUNT = 7
LEGACY_MAP_NATIONAL_IDEAS = (
    ("jxp_map_castle_network", "defensiveness = 0.15"),
    ("jxp_map_land_survey", "global_tax_modifier = 0.10"),
    ("jxp_map_kokujin_compacts", "infantry_power = 0.10"),
    ("jxp_map_market_towns", "development_cost = -0.10"),
    ("jxp_map_coastal_routes", "trade_efficiency = 0.10"),
    ("jxp_map_house_codes", "legitimacy = 1"),
    ("jxp_map_provincial_identity", "core_creation = -0.10"),
)
MAP_IDEA_ARCHETYPES = {
    "warrior": {
        "start": (("land_morale", "0.05"), ("global_manpower_modifier", "0.10")),
        "bonus": (("discipline", "0.05"),),
        "ideas": (
            (("defensiveness", "0.15"),),
            (("global_tax_modifier", "0.10"),),
            (("infantry_power", "0.10"),),
            (("manpower_recovery_speed", "0.10"),),
            (("land_maintenance_modifier", "-0.05"),),
            (("army_tradition_decay", "-0.01"),),
            (("core_creation", "-0.10"),),
        ),
        "secondary": (
            ("land_forcelimit_modifier", "0.10"),
            ("production_efficiency", "0.10"),
            ("leader_land_shock", "1"),
            ("discipline", "0.025"),
        ),
    },
    "court": {
        "start": (("prestige", "1"), ("legitimacy", "1")),
        "bonus": (("diplomatic_reputation", "1"),),
        "ideas": (
            (("advisor_cost", "-0.10"),),
            (("improve_relation_modifier", "0.20"),),
            (("global_tax_modifier", "0.10"),),
            (("diplomatic_upkeep", "1"),),
            (("stability_cost_modifier", "-0.10"),),
            (("development_cost", "-0.05"),),
            (("core_creation", "-0.10"),),
        ),
        "secondary": (
            ("advisor_pool", "1"),
            ("prestige_decay", "-0.01"),
            ("production_efficiency", "0.10"),
            ("diplomatic_reputation", "1"),
        ),
    },
    "maritime": {
        "start": (("naval_morale", "0.10"), ("trade_efficiency", "0.10")),
        "bonus": (("ship_durability", "0.05"),),
        "ideas": (
            (("global_ship_trade_power", "0.15"),),
            (("global_sailors_modifier", "0.15"),),
            (("naval_forcelimit_modifier", "0.15"),),
            (("production_efficiency", "0.10"),),
            (("privateer_efficiency", "0.15"),),
            (("navy_tradition_decay", "-0.01"),),
            (("core_creation", "-0.10"),),
        ),
        "secondary": (
            ("trade_steering", "0.10"),
            ("global_trade_power", "0.10"),
            ("ship_durability", "0.05"),
            ("navy_tradition", "0.50"),
        ),
    },
    "frontier": {
        "start": (("land_morale", "0.05"), ("hostile_attrition", "0.50")),
        "bonus": (("discipline", "0.05"),),
        "ideas": (
            (("defensiveness", "0.15"),),
            (("global_manpower_modifier", "0.15"),),
            (("land_forcelimit_modifier", "0.10"),),
            (("production_efficiency", "0.10"),),
            (("movement_speed", "0.10"),),
            (("leader_land_shock", "1"),),
            (("core_creation", "-0.10"),),
        ),
        "secondary": (
            ("fort_maintenance_modifier", "-0.10"),
            ("manpower_recovery_speed", "0.10"),
            ("leader_land_fire", "1"),
            ("leader_land_shock", "1"),
        ),
    },
    "temple_market": {
        "start": (("global_tax_modifier", "0.10"), ("religious_unity", "0.15")),
        "bonus": (("development_cost", "-0.10"),),
        "ideas": (
            (("global_unrest", "-1"),),
            (("production_efficiency", "0.10"),),
            (("advisor_cost", "-0.10"),),
            (("tolerance_own", "1"),),
            (("improve_relation_modifier", "0.15"),),
            (("manpower_recovery_speed", "0.10"),),
            (("core_creation", "-0.10"),),
        ),
        "secondary": (
            ("stability_cost_modifier", "-0.10"),
            ("global_tax_modifier", "0.10"),
            ("advisor_pool", "1"),
            ("religious_unity", "0.15"),
        ),
    },
}
TIER_SECONDARY_COUNTS = {"A": 4, "B": 2, "C": 1}
MAP_IDEA_LOCALISATION = {
    "warrior": (
        ("{name}山城网", "{name}家把山城、狼烟台与谷口砦连成互相支援的防线。"),
        ("{name}领国检地", "田亩与军役一并登记，使{name}家能准确掌握兵粮与年贡。"),
        ("{name}国人军役", "以誓纸重订国人众义务，把地方武力纳入{name}家的旗本编制。"),
        ("{name}城下兵站", "道路、宿驿与城下仓储让{name}军势能够持续远征。"),
        ("{name}旗本誓纸", "直属家臣以共同法度与恩赏维系对{name}当主的忠诚。"),
        ("{name}边路奉行", "专任奉行巡察边路、渡口与支城，压缩敌军可乘之隙。"),
        ("{name}一国法度", "从诉讼到征发均依{name}家法裁断，旧国遂成一体。"),
    ),
    "court": (
        ("{name}家门谱", "重修谱牒与公验，使{name}家在朝廷与旧国间获得可援引的名分。"),
        ("{name}奏请使节", "常驻京都的使者以礼物、书状与斡旋经营{name}家的声望。"),
        ("{name}庄园奉行", "厘清寺社、庄园与武家领之间的权利，充实{name}家财政。"),
        ("{name}奉公众", "熟悉礼法与诉讼的奉公众将{name}命令落实到各地。"),
        ("{name}调停状", "以调停和誓约终止争端，比无休止的私斗更能扩大{name}影响。"),
        ("{name}京畿学问", "公家、僧侣与书吏带来的学问成为{name}治理领国的工具。"),
        ("{name}旧国公法", "名分与实务合为公开法度，使{name}家支配不再依赖一时威望。"),
    ),
    "maritime": (
        ("{name}浦津名册", "登记船头、问丸与泊税，使{name}家看清沿岸财富的流向。"),
        ("{name}水主役", "以稳定役法召集水主和船匠，为{name}舰队维持可靠人力。"),
        ("{name}船厂法度", "统一木料、铁钉和修造规制，扩大{name}家的海上动员。"),
        ("{name}港市仓屋", "受保护的仓屋与市町把海贸收益留在{name}领内。"),
        ("{name}潮路众", "熟悉暗礁和季风的潮路众替{name}家控制海峡与远航通道。"),
        ("{name}船盟誓约", "浦众以共同誓约接受{name}家的裁断，同时保留航海经验。"),
        ("{name}海路公法", "港札、救难与护航规则合为{name}家可以公开执行的海法。"),
    ),
    "frontier": (
        ("{name}关隘网", "山口、河谷与冬道的关砦构成{name}家守卫边地的骨架。"),
        ("{name}新田役", "开渠安民与新田丈量让{name}领地供养更多军势。"),
        ("{name}边民军役", "猎户、马户与山民依地势编入{name}家的边防体系。"),
        ("{name}盆地市", "边地市町把粮、马与木材集中到{name}家可控的节点。"),
        ("{name}冬道向导", "熟悉雪岭与险谷的向导让{name}军队比敌军更快通过边境。"),
        ("{name}界碑誓约", "以界碑、人质与婚盟重订国人关系，稳固{name}家的外缘。"),
        ("{name}边国法度", "守备、开垦与诉讼均纳入{name}家法，边疆由此成为领国。"),
    ),
    "temple_market": (
        ("{name}寺社账", "清点名田、香火与借贷，使{name}家掌握寺社经济的真实规模。"),
        ("{name}门前町", "保护仓屋、手工业者与定期市，让{name}领内形成稳定町场。"),
        ("{name}学问所", "僧侣与书吏培养的人才为{name}家提供治理所需的文书能力。"),
        ("{name}寺市调停", "在武家、寺社与座商之间调停，维持{name}领国的信仰秩序。"),
        ("{name}德政奉行", "以成文尺度处理债务与荒年救济，避免{name}领内反复动荡。"),
        ("{name}共同仓", "寺町共同仓在歉收和战时支撑{name}家的民生与军粮。"),
        ("{name}寺市公法", "寺社惯例与市场规条合为{name}家能够公开执行的领国法。"),
    ),
}
MAP_MONARCH_NAME_FALLBACKS = (
    ("义久", 40),
    ("晴信", 40),
    ("隆正", 40),
    ("正信", 40),
    ("德", -5),
    ("绫", -5),
)
MAP_LEADER_NAMES = (
    "斋藤",
    "渡边",
    "森",
    "近藤",
    "服部",
    "酒井",
    "阿部",
    "伊藤",
    "内藤",
    "大久保",
    "本多",
    "鸟居",
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--main-mod", type=Path, required=True)
    return parser.parse_args()


def scan_tags(root: Path) -> dict[str, Path]:
    found = {}
    directory = root / "common" / "country_tags"
    if not directory.exists():
        return found
    for path in directory.glob("*.txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for tag in re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*=", text):
            found[tag] = path
    return found


def heraldic_color(index: int) -> tuple[int, int, int]:
    hue = (index * 0.618033988749895 + 0.03) % 1.0
    saturation = 0.48 + (index % 3) * 0.08
    lightness = 0.30 + (index % 4) * 0.045
    r, g, b = colorsys.hls_to_rgb(hue, lightness, min(saturation, 0.72))
    return int(r * 255), int(g * 255), int(b * 255)


def textured_background(size: int, color: tuple[int, int, int], seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 5.0, (size, size, 1))
    base = np.asarray(color, dtype=float).reshape(1, 1, 3)
    vignette_y, vignette_x = np.ogrid[-1:1:size * 1j, -1:1:size * 1j]
    vignette = (vignette_x ** 2 + vignette_y ** 2)[..., None] * 10.0
    pixels = np.clip(base + noise - vignette, 0, 255).astype(np.uint8)
    return Image.fromarray(pixels, "RGB")


def draw_petal_rosette(draw: ImageDraw.ImageDraw, center, radius, count, fill, width=0):
    cx, cy = center
    for index in range(count):
        angle = 2 * math.pi * index / count
        px = cx + math.cos(angle) * radius * 0.58
        py = cy + math.sin(angle) * radius * 0.58
        r = radius * 0.35
        draw.ellipse((px - r, py - r, px + r, py + r), fill=fill)
    draw.ellipse((cx - radius * 0.26, cy - radius * 0.26, cx + radius * 0.26, cy + radius * 0.26), fill=fill)


def draw_mon(image: Image.Image, index: int):
    draw = ImageDraw.Draw(image)
    size = image.width
    center = size // 2
    ink = (232, 224, 191)
    shadow = (35, 31, 28)
    pattern = index % 10
    outer = int(size * 0.34)
    draw.ellipse((center - outer, center - outer, center + outer, center + outer), outline=shadow, width=max(3, size // 80))
    if pattern == 0:
        for dx, dy in ((0, -70), (-62, 40), (62, 40)):
            r = 70
            draw.ellipse((center + dx - r, center + dy - r, center + dx + r, center + dy + r), outline=ink, width=26)
    elif pattern == 1:
        draw_petal_rosette(draw, (center, center), 128, 5, ink)
        draw.ellipse((center - 44, center - 44, center + 44, center + 44), fill=image.getpixel((20, 20)))
    elif pattern == 2:
        for shift in (-90, 0, 90):
            points = [(center + shift, center - 120), (center + shift + 70, center), (center + shift, center + 120), (center + shift - 70, center)]
            draw.polygon(points, outline=ink)
            draw.line(points + [points[0]], fill=ink, width=24, joint="curve")
    elif pattern == 3:
        draw.line((center - 125, center + 125, center + 125, center - 125), fill=ink, width=42)
        draw.line((center - 125, center - 125, center + 125, center + 125), fill=ink, width=42)
        for offset in (-100, -45, 10, 65):
            draw.line((center + offset - 42, center - offset - 42, center + offset + 42, center - offset + 42), fill=shadow, width=9)
    elif pattern == 4:
        draw.ellipse((center - 132, center - 132, center + 132, center + 132), outline=ink, width=30)
        for y in (center - 62, center, center + 62):
            draw.rounded_rectangle((center - 115, y - 18, center + 115, y + 18), radius=18, fill=ink)
    elif pattern == 5:
        for start in range(0, 360, 60):
            draw.pieslice((center - 140, center - 140, center + 140, center + 140), start=start + 7, end=start + 45, fill=ink)
        draw.ellipse((center - 42, center - 42, center + 42, center + 42), fill=shadow)
    elif pattern == 6:
        for dx, dy in ((-70, -70), (70, -70), (-70, 70), (70, 70), (0, 0), (0, -132)):
            draw.ellipse((center + dx - 42, center + dy - 42, center + dx + 42, center + dy + 42), outline=ink, width=18)
    elif pattern == 7:
        draw.polygon([(center - 150, center + 100), (center - 35, center - 120), (center + 35, center + 15), (center + 90, center - 75), (center + 155, center + 100)], fill=ink)
        draw.rectangle((center - 155, center + 100, center + 155, center + 135), fill=ink)
    elif pattern == 8:
        draw.ellipse((center - 138, center - 138, center + 138, center + 138), outline=ink, width=28)
        for angle in (0, 120, 240):
            radians = math.radians(angle)
            x = center + math.cos(radians) * 72
            y = center + math.sin(radians) * 72
            draw.arc((x - 88, y - 88, x + 88, y + 88), angle + 25, angle + 270, fill=ink, width=28)
    else:
        draw_petal_rosette(draw, (center, center + 35), 118, 7, ink)
        draw.line((center, center - 150, center, center + 155), fill=ink, width=22)
        draw.line((center - 85, center - 75, center + 85, center - 75), fill=ink, width=20)


def write_flags(countries: list[dict]) -> dict[str, list[int]]:
    flag_dir = MOD_ROOT / "gfx" / "flags"
    source_dir = flag_dir / "source"
    preview_dir = flag_dir / "preview"
    colors = {}
    for index, country in enumerate(countries):
        tag = country["tag"]
        color = heraldic_color(index)
        colors[tag] = list(color)
        source_path = source_dir / f"{tag}_source.png"
        preview_path = preview_dir / f"{tag}.png"
        final_path = flag_dir / f"{tag}.tga"
        for path in (source_path, preview_path, final_path):
            if not path.exists():
                raise RuntimeError(
                    "ImageGen flag asset is missing; run "
                    f"tools/jxp_asset_builder/build_assets.py first: {path}"
                )
        source = Image.open(source_path)
        final = Image.open(final_path)
        if source.width < 512 or source.height < 512:
            raise RuntimeError(f"ImageGen flag source is too small: {source_path} is {source.size}")
        if final.size != (128, 128) or final.mode != "RGB":
            raise RuntimeError(f"EU4 flag format mismatch: {final_path} is {final.size} {final.mode}")
    return colors


def country_definition(country: dict, color: list[int]) -> str:
    dynasty = country["dynasty_zh"]
    ruler = country["ruler_zh"]
    monarch_fallbacks = "\n".join(
        f'\t"{name} #0" = {weight}' for name, weight in MAP_MONARCH_NAME_FALLBACKS
    )
    leader_names = " ".join((dynasty, *MAP_LEADER_NAMES))
    r, g, b = color
    return f'''# Generated historical daimyo country definition.
graphical_culture = asiangfx
color = {{ {r} {g} {b} }}
revolutionary_colors = {{ 8 1 8 }}

historical_idea_groups = {{
\toffensive_ideas
\tdefensive_ideas
\ttrade_ideas
\tquality_ideas
\tdiplomatic_ideas
\tadministrative_ideas
}}

historical_units = {{
\tjapanese_archer
\teastern_bow
\tjapanese_footsoldier
\tjapanese_samurai
\tasian_arquebusier
\tasian_charge_cavalry
\tasian_mass_infantry
\tasian_musketeer
\treformed_asian_musketeer
\treformed_asian_cavalry
}}

monarch_names = {{
\t"{ruler} #0" = 80
{monarch_fallbacks}
}}

leader_names = {{ {leader_names} }}
ship_names = {{
\t"{dynasty} Maru" "Nippon Maru" "$PROVINCE$ Maru" "Asahi Maru" "Akatsuki Maru"
\t"Hachiman Maru" "Sumiyoshi Maru" "Kasuga Maru" "Matsukaze Maru" "Wakaba Maru"
\t"Shiranui Maru" "Chihaya Maru"
}}
army_names = {{
\t"{dynasty} Gun" "$PROVINCE$ Gun" "$PROVINCE$ Zei" "$PROVINCE$ Dan"
\t"Ichi no Te" "Ni no Te" "San no Te" "Hata Bugyo Shu" "Kiba Shu" "Teppo Shu"
}}
fleet_names = {{
\t"{dynasty} Suigun" "$PROVINCE$ Suigun" "$PROVINCE$ Sendan" "Ichi no Fune"
\t"Ni no Fune" "San no Fune" "Ura Shu" "Oki Shu" "Hayafune Shu" "Sekibune Shu"
}}
'''


def country_history(country: dict, index: int) -> str:
    start_year, start_month, start_day = (int(part) for part in country["start"].split("."))
    ruler_year = 1440 if start_year <= 1444 else start_year
    ruler_date = f"{ruler_year}.{start_month}.{start_day}"
    adm = 2 + index % 3
    dip = 2 + (index + 1) % 3
    mil = 2 + (index + 2) % 3
    return f'''government = monarchy
add_government_reform = daimyo
government_rank = 1
primary_culture = {country['culture']}
religion = shinto
technology_group = chinese
capital = {country['capital']}

{ruler_date} = {{
\tmonarch = {{
\t\tname = "{country['ruler_zh']}"
\t\tdynasty = "{country['dynasty_zh']}"
\t\tbirth_date = {max(1, start_year - 30)}.1.1
\t\tadm = {adm}
\t\tdip = {dip}
\t\tmil = {mil}
\t}}
\tclear_scripted_personalities = yes
\tadd_ruler_personality = careful_personality
}}
'''


def identity_records(countries: list[dict], identity_plan: dict, contract: dict) -> list[dict]:
    country_by_tag = {country["tag"]: country for country in countries}
    plan_by_tag = identity_plan["tags"]
    group_by_tag = {
        tag: group_name
        for group_name, group in contract["groups"].items()
        for tag in group["tags"]
    }
    expected = set(country_by_tag)
    for label, actual in (("identity plan", set(plan_by_tag)), ("house contract", set(group_by_tag))):
        if actual != expected:
            raise RuntimeError(
                f"{label} differs from generated country tags: "
                f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
            )

    records = []
    for tag in sorted(expected):
        planned = plan_by_tag[tag]
        origin = group_by_tag[tag]
        tier = planned["tier"]
        if origin not in MAP_IDEA_ARCHETYPES:
            raise RuntimeError(f"Unknown idea origin {origin!r} for {tag}")
        if tier not in TIER_SECONDARY_COUNTS:
            raise RuntimeError(f"Unknown idea tier {tier!r} for {tag}")
        focus = tuple(planned["focus"])
        if len(focus) != 2:
            raise RuntimeError(f"Identity focus for {tag} must be [modifier, value]")
        records.append(
            {
                "tag": tag,
                "country": country_by_tag[tag],
                "origin": origin,
                "tier": tier,
                "focus": focus,
                "historical_role": planned["historical_role"],
            }
        )
    return records


def _render_modifier_block(modifiers: tuple[tuple[str, str], ...], indent: str) -> list[str]:
    keys = [key for key, _value in modifiers]
    if len(keys) != len(set(keys)):
        raise RuntimeError(f"Idea block repeats modifier keys: {modifiers}")
    return [f"{indent}{key} = {value}" for key, value in modifiers]


def ideas_file(records: list[dict]) -> str:
    legacy_keys = [key for key, _ in LEGACY_MAP_NATIONAL_IDEAS]
    if len(legacy_keys) != NATIONAL_IDEA_COUNT or len(set(legacy_keys)) != NATIONAL_IDEA_COUNT:
        raise RuntimeError(
            "Companion legacy idea tombstone must retain exactly "
            f"{NATIONAL_IDEA_COUNT} unique ideas"
        )

    lines = [
        "# Compatibility tombstone for pre-identity companion saves.",
        "jxp_map_new_daimyo_ideas = {",
        "\tstart = {",
        "\t\tland_morale = 0.05",
        "\t\tglobal_manpower_modifier = 0.10",
        "\t}",
        "\tbonus = { discipline = 0.05 }",
        "\ttrigger = { always = no }",
        "\tfree = yes",
        "",
    ]
    lines.extend(
        f"\t{key} = {{ {modifier} }}" for key, modifier in LEGACY_MAP_NATIONAL_IDEAS
    )
    lines.extend(["}", ""])

    for record in records:
        tag = record["tag"]
        archetype = MAP_IDEA_ARCHETYPES[record["origin"]]
        ideas = []
        for index, base in enumerate(archetype["ideas"]):
            modifiers = list(base)
            if index == 0:
                modifiers.append(record["focus"])
            if index < TIER_SECONDARY_COUNTS[record["tier"]]:
                modifiers.append(archetype["secondary"][index])
            ideas.append(tuple(modifiers))
        if len(ideas) != NATIONAL_IDEA_COUNT:
            raise RuntimeError(f"{tag} must define exactly {NATIONAL_IDEA_COUNT} ideas")

        lines.extend(
            [
                f"{tag}_ideas = {{",
                "\tstart = {",
                *_render_modifier_block(archetype["start"], "\t\t"),
                "\t}",
                "\tbonus = {",
                *_render_modifier_block(archetype["bonus"], "\t\t"),
                "\t}",
                f"\ttrigger = {{ tag = {tag} }}",
                "\tfree = yes",
                "",
            ]
        )
        for index, modifiers in enumerate(ideas, start=1):
            idea_key = f"jxp_map_{tag.lower()}_identity_{index}"
            lines.append(f"\t{idea_key} = {{")
            lines.extend(_render_modifier_block(modifiers, "\t\t"))
            lines.append("\t}")
        lines.extend(["}", ""])
    return "\n".join(lines)


def write_localisation(countries: list[dict], loc_plan: dict, records: list[dict]):
    source_dir = MOD_ROOT / "localisation_source"
    source_dir.mkdir(parents=True, exist_ok=True)
    lines = ["l_english:"]
    for pid, name in sorted(loc_plan["provinces"].items(), key=lambda item: int(item[0])):
        lines.append(f' PROV{pid}:0 "{name}"')
        lines.append(f' PROV_ADJ{pid}:0 "{name}"')
    for key, name in loc_plan["areas"].items():
        lines.append(f' {key}:0 "{name}"')
    for country in countries:
        lines.append(f' {country["tag"]}:0 "{country["name_zh"]}"')
        lines.append(f' {country["tag"]}_ADJ:0 "{country["adj_zh"]}"')
    ideas = loc_plan["ideas"]
    lines.extend([
        f' jxp_map_new_daimyo_ideas:0 "{ideas["group"]}"',
        f' jxp_map_new_daimyo_ideas_start:0 "{ideas["start"]}"',
        f' jxp_map_new_daimyo_ideas_bonus:0 "{ideas["bonus"]}"',
    ])
    for key, _ in LEGACY_MAP_NATIONAL_IDEAS:
        lines.append(f' {key}:0 "{ideas[key]}"')
        lines.append(f' {key}_desc:0 "{ideas[key + "_desc"]}"')
    for record in records:
        tag = record["tag"]
        name = record["country"]["name_zh"]
        lines.extend(
            [
                f' {tag}_ideas:0 "{name}理念"',
                f' {tag}_ideas_start:0 "{name}的传统"',
                f' {tag}_ideas_bonus:0 "{name}的抱负"',
            ]
        )
        templates = MAP_IDEA_LOCALISATION[record["origin"]]
        if len(templates) != NATIONAL_IDEA_COUNT:
            raise RuntimeError(
                f"{record['origin']} idea localisation must contain {NATIONAL_IDEA_COUNT} rows"
            )
        for index, (title, description) in enumerate(templates, start=1):
            idea_key = f"jxp_map_{tag.lower()}_identity_{index}"
            lines.append(f' {idea_key}:0 "{title.format(name=name)}"')
            lines.append(f' {idea_key}_desc:0 "{description.format(name=name)}"')
    (source_dir / "jxp_map_l_english_utf8_source.yml").write_text("\n".join(lines) + "\n", encoding="utf-8-sig", newline="\n")


def main() -> int:
    args = parse_args()
    history_plan = json.loads(HISTORY_PLAN_PATH.read_text(encoding="utf-8"))
    loc_plan = json.loads(LOCALISATION_PLAN_PATH.read_text(encoding="utf-8"))
    identity_plan = json.loads(DAIMYO_IDENTITY_PLAN_PATH.read_text(encoding="utf-8"))
    contract = json.loads(COMPATIBILITY_CONTRACT_PATH.read_text(encoding="utf-8"))
    countries = history_plan["countries"]
    records = identity_records(countries, identity_plan, contract)
    proposed = {country["tag"] for country in countries}
    occupied = scan_tags(args.game_root.resolve())
    occupied.update(scan_tags(args.main_mod.resolve()))
    collisions = {tag: str(occupied[tag]) for tag in sorted(proposed & set(occupied))}
    if collisions:
        raise RuntimeError(f"Country tag collision(s): {collisions}")

    colors = write_flags(countries)
    tag_dir = MOD_ROOT / "common" / "country_tags"
    country_dir = MOD_ROOT / "common" / "countries"
    history_dir = MOD_ROOT / "history" / "countries"
    tag_dir.mkdir(parents=True, exist_ok=True)
    country_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    tag_lines = []
    for index, country in enumerate(countries):
        tag = country["tag"]
        filename = f"JXP {country['name']}.txt"
        tag_lines.append(f'{tag} = "countries/{filename}"')
        (country_dir / filename).write_text(
            country_definition(country, colors[tag]), encoding="utf-8", newline="\n"
        )
        (history_dir / f"{tag} - {country['name']}.txt").write_text(
            country_history(country, index), encoding="utf-8", newline="\n"
        )
    (tag_dir / "00_jxp_map_countries.txt").write_text("\n".join(tag_lines) + "\n", encoding="cp1252", newline="\n")

    diplomacy_dir = MOD_ROOT / "history" / "diplomacy"
    diplomacy_dir.mkdir(parents=True, exist_ok=True)
    diplomacy_lines = ["# Generated continuous subject intervals for the 88-province map.", ""]
    for overlord, subject, start, end in history_plan["subject_intervals"]:
        diplomacy_lines.extend([
            "vassal = {", f"\tfirst = {overlord}", f"\tsecond = {subject}",
            f"\tstart_date = {start}", f"\tend_date = {end}", "}", "",
        ])
    (diplomacy_dir / "JXP_map_daimyo_relations.txt").write_text("\n".join(diplomacy_lines), encoding="cp1252", newline="\n")

    ideas_dir = MOD_ROOT / "common" / "ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "jxp_map_new_daimyo_ideas.txt").write_text(
        ideas_file(records), encoding="cp1252", newline="\n"
    )
    write_localisation(countries, loc_plan, records)

    manifest = {
        "schema_version": 1,
        "tags": sorted(proposed),
        "country_count": len(countries),
        "colors": colors,
        "subject_interval_count": len(history_plan["subject_intervals"]),
        "flag_files": {tag: f"gfx/flags/{tag}.tga" for tag in sorted(proposed)},
        "flag_sources": {tag: f"gfx/flags/source/{tag}_source.png" for tag in sorted(proposed)},
        "idea_groups": {record["tag"]: f"{record['tag']}_ideas" for record in records},
        "idea_tiers": {record["tag"]: record["tier"] for record in records},
    }
    (SCRIPT_DIR / "generated_countries_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Generated {len(countries)} country tags, histories, and subject timelines; verified ImageGen flags")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
