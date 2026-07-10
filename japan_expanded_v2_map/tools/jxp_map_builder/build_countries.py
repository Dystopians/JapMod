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
    dynasty = country["dynasty"]
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
\t"{country['ruler']} #0" = 80
\t"Yoshihisa #0" = 40
\t"Harunobu #0" = 40
\t"Takamasa #0" = 40
\t"Masanobu #0" = 40
\t"Toku #0" = -5
\t"Aya #0" = -5
}}

leader_names = {{ {dynasty} Saito Watanabe Mori Kondo Hattori Sakai Abe Ito Naito Okubo Honda Torii }}
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
\t\tname = "{country['ruler']}"
\t\tdynasty = "{country['dynasty']}"
\t\tbirth_date = {max(1, start_year - 30)}.1.1
\t\tadm = {adm}
\t\tdip = {dip}
\t\tmil = {mil}
\t}}
\tclear_scripted_personalities = yes
\tadd_ruler_personality = careful_personality
}}
'''


def ideas_file(tags: list[str]) -> str:
    tag_lines = "\n".join(f"\t\t\ttag = {tag}" for tag in tags)
    return f'''jxp_map_new_daimyo_ideas = {{
\tstart = {{
\t\tland_morale = 0.05
\t\tglobal_manpower_modifier = 0.10
\t}}
\tbonus = {{
\t\tdiscipline = 0.05
\t}}
\ttrigger = {{
\t\tOR = {{
{tag_lines}
\t\t}}
\t}}
\tfree = yes

\tjxp_map_castle_network = {{ fort_defense = 0.15 }}
\tjxp_map_land_survey = {{ global_tax_modifier = 0.10 }}
\tjxp_map_kokujin_compacts = {{ infantry_power = 0.10 }}
\tjxp_map_market_towns = {{ development_cost = -0.10 }}
\tjxp_map_coastal_routes = {{ trade_efficiency = 0.10 }}
\tjxp_map_house_codes = {{ legitimacy = 1 }}
\tjxp_map_provincial_identity = {{ core_creation = -0.10 }}
}}
'''


def write_localisation(countries: list[dict], loc_plan: dict):
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
    for key in (
        "jxp_map_castle_network", "jxp_map_land_survey", "jxp_map_kokujin_compacts",
        "jxp_map_market_towns", "jxp_map_coastal_routes", "jxp_map_house_codes",
        "jxp_map_provincial_identity",
    ):
        lines.append(f' {key}:0 "{ideas[key]}"')
        lines.append(f' {key}_desc:0 "{ideas[key + "_desc"]}"')
    (source_dir / "jxp_map_l_english_utf8_source.yml").write_text("\n".join(lines) + "\n", encoding="utf-8-sig", newline="\n")


def main() -> int:
    args = parse_args()
    history_plan = json.loads(HISTORY_PLAN_PATH.read_text(encoding="utf-8"))
    loc_plan = json.loads(LOCALISATION_PLAN_PATH.read_text(encoding="utf-8"))
    countries = history_plan["countries"]
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
        (country_dir / filename).write_text(country_definition(country, colors[tag]), encoding="cp1252", newline="\n")
        (history_dir / f"{tag} - {country['name']}.txt").write_text(country_history(country, index), encoding="cp1252", newline="\n")
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
    (ideas_dir / "jxp_map_new_daimyo_ideas.txt").write_text(ideas_file(sorted(proposed)), encoding="cp1252", newline="\n")
    write_localisation(countries, loc_plan)

    manifest = {
        "schema_version": 1,
        "tags": sorted(proposed),
        "country_count": len(countries),
        "colors": colors,
        "subject_interval_count": len(history_plan["subject_intervals"]),
        "flag_files": {tag: f"gfx/flags/{tag}.tga" for tag in sorted(proposed)},
        "flag_sources": {tag: f"gfx/flags/source/{tag}_source.png" for tag in sorted(proposed)},
    }
    (SCRIPT_DIR / "generated_countries_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated {len(countries)} country tags, histories, and subject timelines; verified ImageGen flags")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
