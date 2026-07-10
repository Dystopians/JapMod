#!/usr/bin/env python3
"""Generate a self-contained visual review page for the Japan Expanded EU4 mod."""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_HTML = SCRIPT_DIR / "jxp_visualizer.html"
MISSION_OVERRIDE_FILES = {"Japanese_Missions.txt", "DOM_Japanese_Missions.txt"}


@dataclass
class Token:
    kind: str
    value: str
    line: int


@dataclass
class Scalar:
    text: str
    quoted: bool = False


@dataclass
class Item:
    key: str | None
    value: object
    line: int


@dataclass
class CwObject:
    entries: list[Item]


@dataclass
class VisualContext:
    loc: dict[str, str]
    modifiers: dict[str, CwObject]
    scripted_effects: dict[str, CwObject]
    scripted_triggers: dict[str, CwObject]
    province_names: dict[str, str]


class ClausewitzParseError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    length = len(text)
    while i < length:
        ch = text[i]
        if ch in " \t\r":
            i += 1
            continue
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch == "#":
            while i < length and text[i] != "\n":
                i += 1
            continue
        if ch in "{}=":
            tokens.append(Token(ch, ch, line))
            i += 1
            continue
        if ch == '"':
            start_line = line
            i += 1
            buf: list[str] = []
            while i < length:
                ch = text[i]
                if ch == "\\" and i + 1 < length:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                if ch == '"':
                    i += 1
                    break
                if ch == "\n":
                    line += 1
                buf.append(ch)
                i += 1
            tokens.append(Token("STRING", "".join(buf), start_line))
            continue

        start = i
        start_line = line
        while i < length and text[i] not in " \t\r\n{}=#":
            i += 1
        tokens.append(Token("ATOM", text[start:i], start_line))
    return tokens


class Parser:
    def __init__(self, tokens: list[Token], source: Path):
        self.tokens = tokens
        self.source = source
        self.i = 0

    def peek(self) -> Token | None:
        if self.i >= len(self.tokens):
            return None
        return self.tokens[self.i]

    def pop(self) -> Token:
        if self.i >= len(self.tokens):
            raise ClausewitzParseError(f"{self.source}: unexpected end of file")
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def parse(self) -> CwObject:
        return self.parse_items(stop_kind=None)

    def parse_items(self, stop_kind: str | None) -> CwObject:
        entries: list[Item] = []
        while self.peek() is not None:
            tok = self.peek()
            if stop_kind and tok and tok.kind == stop_kind:
                self.pop()
                break
            if tok and tok.kind in ("}", "="):
                raise ClausewitzParseError(f"{self.source}:{tok.line}: unexpected {tok.value}")
            key_tok = self.pop()
            if self.peek() and self.peek().kind == "=":
                self.pop()
                value = self.parse_value()
                entries.append(Item(key_tok.value, value, key_tok.line))
            else:
                entries.append(Item(None, Scalar(key_tok.value, key_tok.kind == "STRING"), key_tok.line))
        return CwObject(entries)

    def parse_value(self) -> object:
        tok = self.pop()
        if tok.kind == "{":
            return self.parse_items(stop_kind="}")
        if tok.kind in ("ATOM", "STRING"):
            return Scalar(tok.value, tok.kind == "STRING")
        raise ClausewitzParseError(f"{self.source}:{tok.line}: unexpected value {tok.value}")


def parse_clausewitz(path: Path) -> CwObject:
    return Parser(tokenize(read_text(path)), path).parse()


def as_text(value: object | None) -> str | None:
    if isinstance(value, Scalar):
        return value.text
    return None


def first(obj: CwObject | None, key: str) -> object | None:
    if not isinstance(obj, CwObject):
        return None
    for item in obj.entries:
        if item.key == key:
            return item.value
    return None


def all_items(obj: CwObject | None, key: str) -> list[Item]:
    if not isinstance(obj, CwObject):
        return []
    return [item for item in obj.entries if item.key == key]


def scalar_list(value: object | None) -> list[str]:
    if isinstance(value, Scalar):
        return [value.text]
    if isinstance(value, CwObject):
        values = []
        for item in value.entries:
            if item.key is None and isinstance(item.value, Scalar):
                values.append(item.value.text)
        return values
    return []


def int_value(value: object | None, default: int = 0) -> int:
    text = as_text(value)
    if text is None:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def bool_text(value: object | None) -> str:
    text = as_text(value)
    return text if text is not None else ""


def render_value(value: object, depth: int = 0) -> str:
    tab = "\t"
    if isinstance(value, Scalar):
        if value.quoted or re.search(r"\s|[{}=#]", value.text):
            escaped = value.text.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return value.text
    if not isinstance(value, CwObject):
        return ""
    if not value.entries:
        return "{ }"
    if all(item.key is None and isinstance(item.value, Scalar) for item in value.entries):
        inline = " ".join(render_value(item.value, depth) for item in value.entries)
        if len(inline) <= 96:
            return "{ " + inline + " }"

    inner_indent = tab * (depth + 1)
    outer_indent = tab * depth
    lines = ["{"]
    for item in value.entries:
        if item.key is None:
            lines.append(f"{inner_indent}{render_value(item.value, depth + 1)}")
        else:
            rendered = render_value(item.value, depth + 1)
            if "\n" in rendered:
                lines.append(f"{inner_indent}{item.key} = {rendered}")
            else:
                lines.append(f"{inner_indent}{item.key} = {rendered}")
    lines.append(f"{outer_indent}}}")
    return "\n".join(lines)


def object_without_keys(obj: CwObject | None, keys: set[str]) -> CwObject | None:
    if not isinstance(obj, CwObject):
        return None
    return CwObject([item for item in obj.entries if item.key not in keys])


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def maybe_repair_mojibake(text: str) -> str:
    suspicious = ("銆", "€", "鍚", "澶", "鏃", "绉", "瀹", "涓", "鐨", "涔", "鍥")
    if not any(marker in text for marker in suspicious):
        return text
    try:
        fixed = text.encode("gb18030").decode("utf-8")
    except UnicodeError:
        return text
    if fixed.count("\ufffd") > text.count("\ufffd"):
        return text
    normal_hits = sum(fixed.count(ch) for ch in "的一是在不中日本天下国海城军政")
    old_hits = sum(text.count(marker) for marker in suspicious)
    if "。" in fixed or "，" in fixed or normal_hits >= max(2, old_hits // 3):
        return fixed
    return text


LOC_RE = re.compile(r'^\s*([^:#\s][^:]*?):\d+\s+"(.*)"\s*$')


def load_localisation(mod_root: Path) -> tuple[dict[str, str], list[str], dict[str, int]]:
    loc: dict[str, str] = {}
    files: list[str] = []
    stats = {"keys": 0, "repaired": 0}
    source_dir = mod_root / "localisation_source"
    if not source_dir.exists():
        return loc, files, stats
    for path in sorted(source_dir.glob("*.yml")):
        files.append(rel(path, mod_root))
        for line in read_text(path).splitlines():
            match = LOC_RE.match(line)
            if not match:
                continue
            key = match.group(1).strip()
            raw_value = match.group(2).replace('\\"', '"')
            value = maybe_repair_mojibake(raw_value)
            if value != raw_value:
                stats["repaired"] += 1
            loc[key] = value
            stats["keys"] += 1
    return loc, files, stats


def loc_value(loc: dict[str, str], key: str | None, fallback: str = "") -> str:
    if not key or key == "none":
        return fallback
    return loc.get(key, fallback or key)


def is_likely_loc_key(key: str | None) -> bool:
    if not key or key == "none":
        return False
    if key in {"OK"}:
        return False
    return bool(
        key.startswith("jxp_")
        or re.match(r"^[A-Za-z0-9_]+\.\d+\.[A-Za-z0-9_]+$", key)
        or key.endswith(("_title", "_desc"))
    )


def loc_key_from_value(value: object | None) -> str | None:
    text = as_text(value)
    if text is None:
        return None
    return text


def find_event_refs(value: object) -> list[str]:
    refs: list[str] = []
    if isinstance(value, CwObject):
        for item in value.entries:
            if item.key in {"country_event", "province_event"} and isinstance(item.value, CwObject):
                event_id = as_text(first(item.value, "id"))
                if event_id:
                    refs.append(event_id)
            refs.extend(find_event_refs(item.value))
    return refs


def find_flag_refs(value: object) -> list[str]:
    refs: list[str] = []
    flag_keys = {"has_country_flag", "set_country_flag", "clr_country_flag", "had_country_flag"}
    if isinstance(value, CwObject):
        for item in value.entries:
            if item.key in flag_keys:
                text = as_text(item.value)
                if text:
                    refs.append(text)
            refs.extend(find_flag_refs(item.value))
    return refs


def load_named_common_objects(mod_root: Path, folder: str, warnings: list[str]) -> dict[str, CwObject]:
    objects: dict[str, CwObject] = {}
    base = mod_root / "common" / folder
    if not base.exists():
        return objects
    for path in sorted(base.glob("*.txt")):
        try:
            root = parse_clausewitz(path)
        except ClausewitzParseError as exc:
            warnings.append(str(exc))
            continue
        for item in root.entries:
            if item.key and isinstance(item.value, CwObject):
                objects[item.key] = item.value
    return objects


def detect_game_root() -> Path | None:
    cwd = Path.cwd()
    if (cwd / "launcher-settings.json").exists():
        return cwd
    for parent in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (parent / "launcher-settings.json").exists():
            return parent
    return None


def load_province_names(game_root: Path | None) -> dict[str, str]:
    if not game_root:
        return {}
    names: dict[str, str] = {}
    candidates = [
        game_root / "localisation" / "prov_names_l_english.yml",
        game_root / "localisation" / "prov_names_adj_l_english.yml",
    ]
    pattern = re.compile(r'^\s*PROV(\d+):\d+\s+"(.*?)"')
    for path in candidates:
        if not path.exists():
            continue
        for line in read_text(path).splitlines():
            match = pattern.match(line)
            if match:
                names[match.group(1)] = match.group(2)
    return names


def make_tip(text: str, tone: str = "info", details: str = "", children: list[dict] | None = None) -> dict:
    return {
        "text": text,
        "tone": tone,
        "details": details,
        "children": children or [],
    }


def humanize_id(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"^(jxp_|has_|add_|set_|clr_|remove_|change_)", "", value)
    cleaned = cleaned.replace("_", " ")
    return cleaned[:1].upper() + cleaned[1:]


def loc_name(ctx: VisualContext, key: str | None, fallback: str = "") -> str:
    if not key:
        return fallback
    return loc_value(ctx.loc, key, fallback or humanize_id(key))


def province_name(ctx: VisualContext, value: str | None) -> str:
    if not value:
        return "当前省份"
    return f"{ctx.province_names.get(value, '省份 ' + value)} ({value})"


def country_name(ctx: VisualContext, value: str | None) -> str:
    if not value:
        return "目标国家"
    return loc_value(ctx.loc, value, value)


def format_days(days_text: str | None) -> str:
    if not days_text:
        return ""
    try:
        days = int(float(days_text))
    except ValueError:
        return days_text
    if days < 0:
        return "永久"
    if days == 0:
        return "立即"
    if days % 365 == 0:
        years = days // 365
        return f"{years} 年"
    if days % 30 == 0:
        months = days // 30
        return f"{months} 个月"
    return f"{days} 天"


def format_signed(value_text: str | None, percent: bool = False, decimals: int = 0) -> str:
    if value_text is None:
        return ""
    try:
        value = float(value_text)
    except ValueError:
        return value_text
    if percent:
        value *= 100
    if decimals:
        rendered = f"{value:+.{decimals}f}"
    elif abs(value - round(value)) < 0.0001:
        rendered = f"{int(round(value)):+d}"
    else:
        rendered = f"{value:+.2f}".rstrip("0").rstrip(".")
    return rendered + ("%" if percent else "")


MODIFIER_LABELS: dict[str, tuple[str, str]] = {
    "advisor_cost": ("顾问花费", "percent"),
    "artillery_power": ("炮兵作战能力", "percent"),
    "build_cost": ("建造花费", "percent"),
    "capture_ship_chance": ("俘获敌舰几率", "percent"),
    "church_power_modifier": ("教会力量修正", "percent"),
    "development_cost": ("发展成本", "percent"),
    "diplomatic_reputation": ("外交声誉", "flat1"),
    "envoy_travel_time": ("使节行程时间", "percent"),
    "galley_power": ("桨帆船作战能力", "percent"),
    "global_colonial_growth": ("全球殖民增长", "flat"),
    "global_institution_spread": ("思潮传播速度", "percent"),
    "global_manpower_modifier": ("全国人力", "percent"),
    "global_missionary_strength": ("传教强度", "percent"),
    "global_sailors_modifier": ("全国水手", "percent"),
    "global_ship_trade_power": ("船只贸易竞争力", "percent"),
    "global_tariffs": ("关税", "percent"),
    "global_tax_modifier": ("全国税收", "percent"),
    "global_trade_power": ("全球贸易竞争力", "percent"),
    "global_unrest": ("全国叛乱度", "flat"),
    "governing_capacity_modifier": ("治理容量修正", "percent"),
    "idea_cost": ("理念花费", "percent"),
    "improve_relation_modifier": ("改善关系", "percent"),
    "infantry_power": ("步兵作战能力", "percent"),
    "land_morale": ("陆军士气", "percent"),
    "legitimacy": ("年度正统性", "flat1"),
    "liberty_desire_from_subject_development": ("来自属国发展的独立倾向", "percent"),
    "local_defensiveness": ("本地防御效率", "percent"),
    "local_development_cost": ("本地发展成本", "percent"),
    "local_manpower_modifier": ("本地人力", "percent"),
    "local_missionary_maintenance_cost": ("本地传教维护费", "percent"),
    "local_missionary_strength": ("本地传教强度", "percent"),
    "local_production_efficiency": ("本地生产效率", "percent"),
    "local_sailors_modifier": ("本地水手", "percent"),
    "local_tax_modifier": ("本地税收", "percent"),
    "local_unrest": ("本地叛乱度", "flat"),
    "manpower_recovery_speed": ("人力恢复速度", "percent"),
    "missionary_maintenance_cost": ("传教士维护费", "percent"),
    "naval_forcelimit_modifier": ("海军上限", "percent"),
    "naval_morale": ("海军士气", "percent"),
    "navy_tradition": ("年度海军传统", "flat1"),
    "num_accepted_cultures": ("可接受文化数量", "flat"),
    "prestige": ("年度威望", "flat1"),
    "prestige_decay": ("威望衰减", "percent"),
    "privateer_efficiency": ("私掠效率", "percent"),
    "production_efficiency": ("生产效率", "percent"),
    "province_trade_power_modifier": ("省份贸易竞争力", "percent"),
    "range": ("殖民距离", "percent"),
    "religious_unity": ("宗教统一度", "percent"),
    "ship_power_propagation": ("船只贸易力传播", "percent"),
    "spy_offence": ("间谍网建设", "percent"),
    "stability_cost_modifier": ("稳定度花费", "percent"),
    "technology_cost": ("科技花费", "percent"),
    "tolerance_heathen": ("异教容忍", "flat"),
    "tolerance_heretic": ("异端容忍", "flat"),
    "tolerance_own": ("正统信仰容忍", "flat"),
    "trade_efficiency": ("贸易效率", "percent"),
    "trade_range_modifier": ("贸易距离", "percent"),
    "trade_steering": ("贸易引导", "percent"),
    "yearly_harmony": ("年度和谐度", "flat1"),
}


EFFECT_LABELS: dict[str, tuple[str, str]] = {
    "add_adm_power": ("行政点数", "flat"),
    "add_dip_power": ("外交点数", "flat"),
    "add_mil_power": ("军事点数", "flat"),
    "add_treasury": ("国库", "flat"),
    "add_prestige": ("威望", "flat"),
    "add_legitimacy": ("正统性", "flat"),
    "add_stability": ("稳定度", "flat"),
    "add_mercantilism": ("重商主义", "flat"),
    "add_army_tradition": ("陆军传统", "flat"),
    "add_navy_tradition": ("海军传统", "flat"),
    "add_harmony": ("和谐度", "flat"),
    "add_inflation": ("通货膨胀", "flat"),
    "add_corruption": ("腐败", "flat"),
    "add_years_of_income": ("年收入", "flat"),
    "add_base_tax": ("基础税收", "flat"),
    "add_base_production": ("基础生产", "flat"),
    "add_base_manpower": ("基础人力", "flat"),
}


TRIGGER_LABELS: dict[str, str] = {
    "adm_power": "行政点数至少",
    "dip_power": "外交点数至少",
    "mil_power": "军事点数至少",
    "treasury": "国库至少",
    "stability": "稳定度至少",
    "prestige": "威望至少",
    "legitimacy": "正统性至少",
    "adm_tech": "行政科技至少",
    "dip_tech": "外交科技至少",
    "mil_tech": "军事科技至少",
    "num_of_cities": "城市数量至少",
    "num_of_ports": "港口数量至少",
    "num_of_colonists": "殖民者数量至少",
    "army_tradition": "陆军传统至少",
    "navy_tradition": "海军传统至少",
    "religious_unity": "宗教统一度至少",
    "is_year": "年份至少",
}


AREA_LABELS: dict[str, str] = {
    "region": "区域",
    "area": "地区",
    "superregion": "大区",
    "colonial_region": "殖民区域",
}


RELIGION_LABELS: dict[str, str] = {
    "shinto": "神道教",
    "confucianism": "儒教",
    "catholic": "天主教",
    "protestant": "新教",
    "reformed": "改革宗",
    "sunni": "逊尼派",
}


def format_modifier_line(key: str, value: str | None) -> dict:
    label, kind = MODIFIER_LABELS.get(key, (humanize_id(key), "flat"))
    percent = kind == "percent"
    decimals = 1 if kind == "flat1" else 0
    rendered = format_signed(value, percent=percent, decimals=decimals)
    tone = "good"
    if rendered.startswith("-"):
        tone = "bad"
    if key in {"advisor_cost", "build_cost", "development_cost", "idea_cost", "technology_cost",
               "stability_cost_modifier", "global_unrest", "local_unrest", "envoy_travel_time",
               "prestige_decay", "missionary_maintenance_cost", "local_missionary_maintenance_cost"}:
        tone = "good" if rendered.startswith("-") else "bad"
    return make_tip(f"{label} {rendered}", tone)


def modifier_effect_tips(ctx: VisualContext, modifier_id: str | None) -> list[dict]:
    if not modifier_id:
        return []
    obj = ctx.modifiers.get(modifier_id)
    if not isinstance(obj, CwObject):
        return []
    tips: list[dict] = []
    for item in obj.entries:
        if item.key and isinstance(item.value, Scalar):
            tips.append(format_modifier_line(item.key, item.value.text))
    return tips


def polity_effect_tip(key: str, ctx: VisualContext) -> dict | None:
    match = re.match(r"^jxp_(add|subtract)_(tenka_order|imperial_sanction|oceanic_opening)_(\d+)_effect$", key)
    if not match:
        return None
    direction, variable, amount = match.groups()
    signed = int(amount) * (1 if direction == "add" else -1)
    label = loc_name(ctx, f"jxp_{variable}", humanize_id(variable))
    return make_tip(f"{label} {signed:+d}", "good" if signed > 0 else "bad")


def trim_tips(tips: list[dict], limit: int = 80) -> list[dict]:
    if len(tips) <= limit:
        return tips
    return tips[:limit] + [make_tip(f"还有 {len(tips) - limit} 条脚本效果未展开，可查看原文。", "muted")]


def summarize_script(value: object | None, ctx: VisualContext, mode: str, depth: int = 0,
                     seen: tuple[str, ...] = ()) -> list[dict]:
    if not isinstance(value, CwObject):
        return []
    tips: list[dict] = []
    for item in value.entries:
        tips.extend(summarize_item(item, ctx, mode, depth, seen))
    return trim_tips(tips)


def summarize_item(item: Item, ctx: VisualContext, mode: str, depth: int,
                   seen: tuple[str, ...]) -> list[dict]:
    key = item.key or ""
    value = item.value
    text = as_text(value)

    if mode == "effect" and key in ctx.scripted_effects and text == "yes":
        direct_polity_tip = polity_effect_tip(key, ctx)
        if direct_polity_tip:
            return [direct_polity_tip]
        if key in {"jxp_clamp_polity_values_effect", "jxp_sync_polity_mechanic_from_variables_effect"}:
            return [make_tip("后台同步（游戏中隐藏）", "muted")]
        if key in seen:
            return [make_tip(f"执行脚本效果：{humanize_id(key)}", "muted")]
        expanded = summarize_script(ctx.scripted_effects[key], ctx, "effect", depth + 1, (*seen, key))
        if expanded:
            return expanded
        return [make_tip(f"执行脚本效果：{humanize_id(key)}", "info")]

    if mode == "trigger" and key in ctx.scripted_triggers and text == "yes":
        label = loc_name(ctx, key, humanize_id(key))
        children = summarize_script(ctx.scripted_triggers[key], ctx, "trigger", depth + 1, (*seen, key))
        return [make_tip(f"满足：{label}", "need", children=children[:12])]

    if key == "OR" and isinstance(value, CwObject):
        return [make_tip("以下条件至少满足一项：", "need", children=summarize_script(value, ctx, mode, depth + 1, seen))]
    if key == "AND" and isinstance(value, CwObject):
        return [make_tip("以下条件全部满足：", "need", children=summarize_script(value, ctx, mode, depth + 1, seen))]
    if key == "NOT" and isinstance(value, CwObject):
        return [make_tip("不能满足以下条件：", "bad", children=summarize_script(value, ctx, mode, depth + 1, seen))]
    if key == "hidden_effect" and isinstance(value, CwObject):
        return [make_tip("后台同步（游戏中隐藏）", "muted")]
    if key == "if" and isinstance(value, CwObject):
        limit = first(value, "limit")
        rest = object_without_keys(value, {"limit"})
        children = []
        if limit:
            children.append(make_tip("条件：", "need", children=summarize_script(limit, ctx, "trigger", depth + 1, seen)))
        if rest:
            children.extend(summarize_script(rest, ctx, mode, depth + 1, seen))
        return [make_tip("如果满足条件，则：", "info", children=children)]
    if key == "else_if" and isinstance(value, CwObject):
        return [make_tip("否则如果：", "info", children=summarize_script(value, ctx, mode, depth + 1, seen))]
    if key == "else" and isinstance(value, CwObject):
        return [make_tip("否则：", "info", children=summarize_script(value, ctx, mode, depth + 1, seen))]
    if key in {"ROOT", "FROM", "overlord", "capital_scope"} and isinstance(value, CwObject):
        scope = {"ROOT": "我国", "FROM": "来源国家", "overlord": "宗主国", "capital_scope": "首都"}.get(key, key)
        return [make_tip(f"{scope}满足：", "info", children=summarize_script(value, ctx, mode, depth + 1, seen))]
    if key.isdigit() and isinstance(value, CwObject):
        return [make_tip(f"在{province_name(ctx, key)}：", "info", children=summarize_script(value, ctx, mode, depth + 1, seen))]

    if mode == "effect":
        return summarize_effect_item(key, value, text, ctx, depth, seen)
    return summarize_trigger_item(key, value, text, ctx, depth, seen)


def summarize_effect_item(key: str, value: object, text: str | None, ctx: VisualContext,
                          depth: int, seen: tuple[str, ...]) -> list[dict]:
    if key in EFFECT_LABELS and text is not None:
        label, kind = EFFECT_LABELS[key]
        rendered = format_signed(text, decimals=1 if kind == "flat1" else 0)
        tone = "good" if not rendered.startswith("-") else "bad"
        return [make_tip(f"{label} {rendered}", tone)]

    if key in {"add_country_modifier", "add_province_modifier"} and isinstance(value, CwObject):
        modifier_id = as_text(first(value, "name"))
        duration = format_days(as_text(first(value, "duration")))
        target = "国家修正" if key == "add_country_modifier" else "省份修正"
        children = modifier_effect_tips(ctx, modifier_id)
        desc = loc_value(ctx.loc, f"{modifier_id}_desc", "") if modifier_id else ""
        details = f"持续 {duration}" if duration else ""
        if desc:
            details = f"{details}。{desc}" if details else desc
        return [make_tip(f"获得{target}：{loc_name(ctx, modifier_id, modifier_id or target)}", "good", details, children)]

    if key in {"remove_country_modifier", "remove_province_modifier"} and text:
        target = "国家修正" if key == "remove_country_modifier" else "省份修正"
        return [make_tip(f"移除{target}：{loc_name(ctx, text, text)}", "bad")]

    if key in {"country_event", "province_event"} and isinstance(value, CwObject):
        event_id = as_text(first(value, "id"))
        days = as_text(first(value, "days"))
        delay = f"（{format_days(days)}后）" if days else ""
        title = loc_value(ctx.loc, f"{event_id}.t", event_id or "事件")
        return [make_tip(f"触发事件：{title} {event_id or ''}{delay}", "event")]

    if key in {"set_country_flag", "clr_country_flag"} and text:
        verb = "记录剧情状态" if key == "set_country_flag" else "清除剧情状态"
        return [make_tip(f"{verb}：{humanize_id(text)}", "muted")]

    if key in {"set_variable", "change_variable"} and isinstance(value, CwObject):
        which = as_text(first(value, "which"))
        amount = as_text(first(value, "value"))
        label = loc_name(ctx, which, humanize_id(which or "variable"))
        if key == "set_variable":
            return [make_tip(f"将 {label} 设为 {amount}", "muted")]
        return [make_tip(f"{label} {format_signed(amount)}", "good" if not (amount or "").startswith("-") else "bad")]

    if key in {"add_government_power", "set_government_power"} and isinstance(value, CwObject):
        power = as_text(first(value, "power_type"))
        amount = as_text(first(value, "value"))
        label = loc_name(ctx, power, humanize_id(power or "government power"))
        if key == "set_government_power":
            return [make_tip(f"将 {label} 设为 {amount}", "info")]
        return [make_tip(f"{label} {format_signed(amount)}", "good" if not (amount or "").startswith("-") else "bad")]

    if key in {"add_permanent_claim", "add_claim", "add_core", "remove_core"} and text:
        verbs = {
            "add_permanent_claim": "获得永久宣称",
            "add_claim": "获得宣称",
            "add_core": "获得核心",
            "remove_core": "移除核心",
        }
        return [make_tip(f"{verbs[key]}：{province_name(ctx, text)}", "good")]

    if key in {"change_tag", "change_religion", "set_ruler_religion", "set_heir_religion"} and text:
        if key == "change_tag":
            return [make_tip(f"国家变为：{country_name(ctx, text)}", "event")]
        religion = RELIGION_LABELS.get(text, humanize_id(text))
        label = {"change_religion": "国教改为", "set_ruler_religion": "统治者信仰改为", "set_heir_religion": "继承人信仰改为"}[key]
        return [make_tip(f"{label}：{religion}", "event")]

    if key == "add_harmonized_religion" and text:
        return [make_tip(f"融合宗教：{RELIGION_LABELS.get(text, humanize_id(text))}", "good")]
    if key == "swap_non_generic_missions" and text == "yes":
        return [make_tip("切换为对应的非通用任务树", "event")]
    if key == "on_change_tag_effect" and text == "yes":
        return [make_tip("执行变更国家后的标准刷新", "muted")]
    if key == "restore_country_name_effect" and text == "yes":
        return [make_tip("刷新国家名称与形容词", "muted")]
    if key == "custom_tooltip" and text:
        return [make_tip(loc_name(ctx, text, humanize_id(text)), "info")]

    if isinstance(value, CwObject):
        children = summarize_script(value, ctx, "effect", depth + 1, seen)
        return [make_tip(f"脚本效果：{humanize_id(key)}", "muted", children=children[:12])]
    if text is not None and text != "no":
        return [make_tip(f"{humanize_id(key)}：{text}", "muted")]
    return []


def summarize_trigger_item(key: str, value: object, text: str | None, ctx: VisualContext,
                           depth: int, seen: tuple[str, ...]) -> list[dict]:
    if key in TRIGGER_LABELS and text is not None:
        suffix = text
        if key == "religious_unity":
            suffix = format_signed(text, percent=True).lstrip("+")
        return [make_tip(f"{TRIGGER_LABELS[key]} {suffix}", "need")]

    if key == "always" and text == "yes":
        return [make_tip("总是允许", "good")]
    if key == "ai" and text in {"yes", "no"}:
        return [make_tip("仅 AI 使用" if text == "yes" else "仅玩家使用", "need")]
    if key == "owns" and text:
        return [make_tip(f"拥有：{province_name(ctx, text)}", "need")]
    if key == "owns_or_non_sovereign_subject_of" and text:
        return [make_tip(f"自己或直属属国拥有：{province_name(ctx, text)}", "need")]
    if key == "tag" and text:
        return [make_tip(f"国家是：{country_name(ctx, text)}", "need")]
    if key == "religion" and text:
        return [make_tip(f"国教是：{RELIGION_LABELS.get(text, humanize_id(text))}", "need")]
    if key == "has_country_flag" and text:
        return [make_tip(f"已进入剧情状态：{humanize_id(text)}", "muted")]
    if key in {"has_country_modifier", "has_province_modifier"} and text:
        target = "国家修正" if key == "has_country_modifier" else "省份修正"
        return [make_tip(f"拥有{target}：{loc_name(ctx, text, text)}", "need", children=modifier_effect_tips(ctx, text))]
    if key == "has_reform" and text:
        return [make_tip(f"拥有政府改革：{loc_name(ctx, text, humanize_id(text))}", "need")]
    if key == "has_dlc" and text:
        return [make_tip(f"启用 DLC：{text}", "need")]
    if key == "is_emperor_of_china" and text == "yes":
        return [make_tip("是中华天子", "need")]
    if key == "has_port" and text == "yes":
        return [make_tip("是港口省份", "need")]
    if key == "is_city" and text == "yes":
        return [make_tip("是城市", "need")]
    if key in AREA_LABELS and text:
        return [make_tip(f"{AREA_LABELS[key]}：{loc_name(ctx, text, humanize_id(text))}", "need")]
    if key == "has_discovered" and text:
        who = "我国" if text == "ROOT" else text
        return [make_tip(f"已被{who}发现", "need")]

    if key == "check_variable" and isinstance(value, CwObject):
        which = as_text(first(value, "which"))
        amount = as_text(first(value, "value"))
        return [make_tip(f"{loc_name(ctx, which, humanize_id(which or '变量'))}至少 {amount}", "need")]

    if key == "has_government_power" and isinstance(value, CwObject):
        power = as_text(first(value, "power_type"))
        amount = as_text(first(value, "value"))
        return [make_tip(f"{loc_name(ctx, power, humanize_id(power or '政府能力'))}至少 {amount}", "need")]

    if key in {"any_owned_province", "any_known_country", "any_subject_country", "any_neighbor_country"} and isinstance(value, CwObject):
        label = {
            "any_owned_province": "任一拥有省份满足：",
            "any_known_country": "任一已知国家满足：",
            "any_subject_country": "任一属国满足：",
            "any_neighbor_country": "任一邻国满足：",
        }[key]
        return [make_tip(label, "need", children=summarize_script(value, ctx, "trigger", depth + 1, seen))]

    if key == "num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with" and isinstance(value, CwObject):
        amount = as_text(first(value, "value")) or "1"
        filters = object_without_keys(value, {"value"})
        return [make_tip(f"自己或直属属国拥有符合条件的省份至少 {amount} 个：", "need",
                         children=summarize_script(filters, ctx, "trigger", depth + 1, seen) if filters else [])]

    if key == "custom_trigger_tooltip" and isinstance(value, CwObject):
        tooltip = as_text(first(value, "tooltip"))
        rest = object_without_keys(value, {"tooltip"})
        return [make_tip(loc_name(ctx, tooltip, humanize_id(tooltip or "条件")), "need",
                         children=summarize_script(rest, ctx, "trigger", depth + 1, seen) if rest else [])]

    if isinstance(value, CwObject):
        children = summarize_script(value, ctx, "trigger", depth + 1, seen)
        return [make_tip(f"条件块：{humanize_id(key)}", "muted", children=children[:12])]
    if text is not None and text != "no":
        return [make_tip(f"{humanize_id(key)}：{text}", "muted")]
    return []


def summarize_mtth(value: object | None, ctx: VisualContext) -> list[dict]:
    if not isinstance(value, CwObject):
        return []
    tips: list[dict] = []
    for item in value.entries:
        text = as_text(item.value)
        if item.key in {"days", "months", "years"} and text is not None:
            unit = {"days": "天", "months": "个月", "years": "年"}[item.key]
            tips.append(make_tip(f"平均触发时间：{text} {unit}", "need"))
        elif item.key == "modifier" and isinstance(item.value, CwObject):
            factor = as_text(first(item.value, "factor")) or "1"
            conditions = object_without_keys(item.value, {"factor"})
            tips.append(make_tip(
                f"触发时间倍率：x{factor}",
                "info",
                children=summarize_script(conditions, ctx, "trigger") if conditions else [],
            ))
    return tips


def extract_mission_groups(mod_root: Path, ctx: VisualContext, missing_loc: set[str], warnings: list[str]) -> list[dict]:
    groups: list[dict] = []
    for path in sorted((mod_root / "missions").glob("*.txt")):
        if path.name in MISSION_OVERRIDE_FILES:
            continue
        try:
            root = parse_clausewitz(path)
        except ClausewitzParseError as exc:
            warnings.append(str(exc))
            continue
        for group_item in root.entries:
            if not group_item.key or not isinstance(group_item.value, CwObject):
                continue
            group_obj = group_item.value
            if first(group_obj, "slot") is None:
                continue
            mission_items = [
                item for item in group_obj.entries
                if item.key
                and isinstance(item.value, CwObject)
                and first(item.value, "position") is not None
            ]
            if not mission_items:
                continue
            slot = int_value(first(group_obj, "slot"))
            group = {
                "id": group_item.key,
                "slot": slot,
                "generic": bool_text(first(group_obj, "generic")),
                "ai": bool_text(first(group_obj, "ai")),
                "hasCountryShield": bool_text(first(group_obj, "has_country_shield")),
                "potential": render_value(first(group_obj, "potential"), 0) if first(group_obj, "potential") else "",
                "potentialTips": summarize_script(first(group_obj, "potential"), ctx, "trigger") if first(group_obj, "potential") else [],
                "file": rel(path, mod_root),
                "line": group_item.line,
                "missions": [],
            }
            for item in mission_items:
                mission_obj = item.value
                position = int_value(first(mission_obj, "position"))
                title_key = f"{item.key}_title"
                desc_key = f"{item.key}_desc"
                if title_key not in ctx.loc:
                    missing_loc.add(title_key)
                if desc_key not in ctx.loc:
                    missing_loc.add(desc_key)
                required = scalar_list(first(mission_obj, "required_missions"))
                trigger = first(mission_obj, "trigger")
                effect = first(mission_obj, "effect")
                mission = {
                    "id": item.key,
                    "title": loc_value(ctx.loc, title_key, item.key),
                    "desc": loc_value(ctx.loc, desc_key, ""),
                    "titleKey": title_key,
                    "descKey": desc_key,
                    "icon": as_text(first(mission_obj, "icon")) or "",
                    "position": position,
                    "row": ((position - 1) % 5) + 1 if position > 0 else 1,
                    "column": ((position - 1) // 5) + 1 if position > 0 else 1,
                    "requiredMissions": required,
                    "trigger": render_value(trigger, 0) if trigger else "",
                    "triggerTips": summarize_script(trigger, ctx, "trigger") if trigger else [],
                    "effect": render_value(effect, 0) if effect else "",
                    "effectTips": summarize_script(effect, ctx, "effect") if effect else [],
                    "eventRefs": sorted(set(find_event_refs(effect))) if effect else [],
                    "flagRefs": sorted(set(find_flag_refs(mission_obj))),
                    "file": rel(path, mod_root),
                    "line": item.line,
                }
                group["missions"].append(mission)
            group["missions"].sort(key=lambda m: (m["column"], m["row"], m["id"]))
            groups.append(group)
    groups.sort(key=lambda g: (g["slot"], g["file"], g["id"]))
    return groups


def extract_decisions(mod_root: Path, ctx: VisualContext, missing_loc: set[str], warnings: list[str]) -> list[dict]:
    decisions: list[dict] = []
    decisions_dir = mod_root / "decisions"
    if not decisions_dir.exists():
        return decisions
    for path in sorted(decisions_dir.glob("*.txt")):
        try:
            root = parse_clausewitz(path)
        except ClausewitzParseError as exc:
            warnings.append(str(exc))
            continue
        for top in root.entries:
            if top.key != "country_decisions" or not isinstance(top.value, CwObject):
                continue
            for item in top.value.entries:
                if not item.key or not isinstance(item.value, CwObject):
                    continue
                obj = item.value
                title_key = f"{item.key}_title"
                desc_key = f"{item.key}_desc"
                if title_key not in ctx.loc:
                    missing_loc.add(title_key)
                if desc_key not in ctx.loc:
                    missing_loc.add(desc_key)
                effect = first(obj, "effect")
                potential = first(obj, "potential")
                allow = first(obj, "allow")
                ai_will_do = first(obj, "ai_will_do")
                decision = {
                    "id": item.key,
                    "title": loc_value(ctx.loc, title_key, item.key),
                    "desc": loc_value(ctx.loc, desc_key, ""),
                    "titleKey": title_key,
                    "descKey": desc_key,
                    "major": bool_text(first(obj, "major")),
                    "potential": render_value(potential, 0) if potential else "",
                    "potentialTips": summarize_script(potential, ctx, "trigger") if potential else [],
                    "allow": render_value(allow, 0) if allow else "",
                    "allowTips": summarize_script(allow, ctx, "trigger") if allow else [],
                    "effect": render_value(effect, 0) if effect else "",
                    "effectTips": summarize_script(effect, ctx, "effect") if effect else [],
                    "aiWillDo": render_value(ai_will_do, 0) if ai_will_do else "",
                    "aiWillDoTips": summarize_script(ai_will_do, ctx, "trigger") if ai_will_do else [],
                    "eventRefs": sorted(set(find_event_refs(effect))) if effect else [],
                    "flagRefs": sorted(set(find_flag_refs(obj))),
                    "file": rel(path, mod_root),
                    "line": item.line,
                    "category": path.stem,
                }
                decisions.append(decision)
    decisions.sort(key=lambda d: (d["category"], d["id"]))
    return decisions


def extract_events(mod_root: Path, ctx: VisualContext, missing_loc: set[str], warnings: list[str]) -> list[dict]:
    events: list[dict] = []
    events_dir = mod_root / "events"
    if not events_dir.exists():
        return events
    event_types = {"country_event", "province_event"}
    for path in sorted(events_dir.glob("*.txt")):
        try:
            root = parse_clausewitz(path)
        except ClausewitzParseError as exc:
            warnings.append(str(exc))
            continue
        namespaces = [as_text(item.value) for item in root.entries if item.key == "namespace"]
        for item in root.entries:
            if item.key not in event_types or not isinstance(item.value, CwObject):
                continue
            obj = item.value
            event_id = as_text(first(obj, "id")) or f"{path.stem}:{item.line}"
            title_key = loc_key_from_value(first(obj, "title"))
            desc_key = loc_key_from_value(first(obj, "desc"))
            if is_likely_loc_key(title_key) and title_key not in ctx.loc:
                missing_loc.add(title_key)
            if is_likely_loc_key(desc_key) and desc_key not in ctx.loc:
                missing_loc.add(desc_key)
            options = []
            for opt in all_items(obj, "option"):
                if not isinstance(opt.value, CwObject):
                    continue
                option_key = loc_key_from_value(first(opt.value, "name"))
                if is_likely_loc_key(option_key) and option_key not in ctx.loc:
                    missing_loc.add(option_key)
                option_effect_obj = object_without_keys(opt.value, {"name"})
                options.append({
                    "nameKey": option_key or "",
                    "name": loc_value(ctx.loc, option_key, option_key or "OK"),
                    "script": render_value(option_effect_obj, 0) if option_effect_obj else "",
                    "tips": summarize_script(option_effect_obj, ctx, "effect") if option_effect_obj else [],
                    "eventRefs": sorted(set(find_event_refs(option_effect_obj))) if option_effect_obj else [],
                })
            immediate = first(obj, "immediate")
            trigger = first(obj, "trigger")
            mtth = first(obj, "mean_time_to_happen")
            event = {
                "id": event_id,
                "type": item.key,
                "namespace": event_id.split(".", 1)[0] if "." in event_id else (namespaces[0] or ""),
                "titleKey": title_key or "",
                "descKey": desc_key or "",
                "title": loc_value(ctx.loc, title_key, "Hidden event" if title_key == "none" else event_id),
                "desc": loc_value(ctx.loc, desc_key, "" if desc_key == "none" else ""),
                "picture": as_text(first(obj, "picture")) or "",
                "hidden": bool_text(first(obj, "hidden")) == "yes" or title_key == "none",
                "triggeredOnly": bool_text(first(obj, "is_triggered_only")) == "yes",
                "trigger": render_value(trigger, 0) if trigger else "",
                "triggerTips": summarize_script(trigger, ctx, "trigger") if trigger else [],
                "mtth": render_value(mtth, 0) if mtth else "",
                "mtthTips": summarize_mtth(mtth, ctx) if mtth else [],
                "immediate": render_value(immediate, 0) if immediate else "",
                "immediateTips": summarize_script(immediate, ctx, "effect") if immediate else [],
                "options": options,
                "eventRefs": sorted(set(find_event_refs(obj))),
                "flagRefs": sorted(set(find_flag_refs(obj))),
                "file": rel(path, mod_root),
                "line": item.line,
                "category": path.stem,
            }
            events.append(event)
    events.sort(key=lambda e: event_sort_key(e["id"]))
    return events


def event_sort_key(event_id: str) -> tuple[str, int, str]:
    match = re.match(r"^([A-Za-z0-9_]+)\.(\d+)$", event_id)
    if match:
        return match.group(1), int(match.group(2)), ""
    return event_id, 0, event_id


def build_reverse_event_refs(data: dict) -> dict[str, list[dict[str, str]]]:
    refs: dict[str, list[dict[str, str]]] = {}
    for group in data["missionGroups"]:
        for mission in group["missions"]:
            for event_id in mission["eventRefs"]:
                refs.setdefault(event_id, []).append({
                    "kind": "mission",
                    "id": mission["id"],
                    "title": mission["title"],
                    "group": group["id"],
                })
    for decision in data["decisions"]:
        for event_id in decision["eventRefs"]:
            refs.setdefault(event_id, []).append({
                "kind": "decision",
                "id": decision["id"],
                "title": decision["title"],
                "group": decision["category"],
            })
    for event in data["events"]:
        for event_id in event["eventRefs"]:
            if event_id == event["id"]:
                continue
            refs.setdefault(event_id, []).append({
                "kind": "event",
                "id": event["id"],
                "title": event["title"],
                "group": event["category"],
            })
    return refs


def load_descriptor(mod_root: Path) -> dict[str, str]:
    descriptor = mod_root / "descriptor.mod"
    values: dict[str, str] = {}
    if not descriptor.exists():
        return values
    for line in read_text(descriptor).splitlines():
        match = re.match(r'\s*([A-Za-z0-9_]+)\s*=\s*"?([^"]+)"?\s*$', line)
        if match:
            values[match.group(1)] = maybe_repair_mojibake(match.group(2))
    return values


def collect_files(mod_root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for folder in ("missions", "decisions", "events", "localisation_source"):
        base = mod_root / folder
        result[folder] = [rel(path, mod_root) for path in sorted(base.glob("*.txt" if folder != "localisation_source" else "*.yml"))] if base.exists() else []
    return result


def build_data(mod_root: Path, game_root: Path | None = None) -> dict:
    loc, loc_files, loc_stats = load_localisation(mod_root)
    missing_loc: set[str] = set()
    warnings: list[str] = []
    if game_root is None:
        game_root = detect_game_root()
    ctx = VisualContext(
        loc=loc,
        modifiers=load_named_common_objects(mod_root, "event_modifiers", warnings),
        scripted_effects=load_named_common_objects(mod_root, "scripted_effects", warnings),
        scripted_triggers=load_named_common_objects(mod_root, "scripted_triggers", warnings),
        province_names=load_province_names(game_root),
    )
    mission_groups = extract_mission_groups(mod_root, ctx, missing_loc, warnings)
    decisions = extract_decisions(mod_root, ctx, missing_loc, warnings)
    events = extract_events(mod_root, ctx, missing_loc, warnings)
    data = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "modRoot": str(mod_root),
        "gameRoot": str(game_root) if game_root else "",
        "descriptor": load_descriptor(mod_root),
        "files": collect_files(mod_root),
        "localisation": {
            "files": loc_files,
            "stats": loc_stats,
            "missing": sorted(missing_loc),
        },
        "missionGroups": mission_groups,
        "decisions": decisions,
        "events": events,
        "warnings": warnings,
    }
    data["counts"] = {
        "missionGroups": len(mission_groups),
        "missions": sum(len(group["missions"]) for group in mission_groups),
        "decisions": len(decisions),
        "events": len(events),
        "localisationKeys": loc_stats["keys"],
        "missingLocalisation": len(missing_loc),
        "modifiers": len(ctx.modifiers),
        "scriptedEffects": len(ctx.scripted_effects),
        "scriptedTriggers": len(ctx.scripted_triggers),
        "provinceNames": len(ctx.province_names),
    }
    data["eventInboundRefs"] = build_reverse_event_refs(data)
    return data


def html_page(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    generated = html.escape(data["generatedAt"])
    title = html.escape(data["descriptor"].get("name", "Japan Expanded Visualizer"))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - 内容审阅器</title>
<style>
:root {{
  color-scheme: dark;
  --ink: #28190f;
  --paper: #e3c991;
  --paper-2: #f3dfaa;
  --paper-3: #b99050;
  --red: #7d2422;
  --red-2: #a93a2f;
  --gold: #d4a949;
  --green: #315a44;
  --blue: #284c67;
  --night: #17110d;
  --night-2: #241710;
  --muted: #7a6142;
  --line: rgba(76, 43, 22, .32);
  --shadow: 0 12px 28px rgba(0, 0, 0, .28);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  font-family: "Microsoft YaHei", "Noto Sans SC", "Segoe UI", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at 15% 12%, rgba(212, 169, 73, .20), transparent 30rem),
    linear-gradient(135deg, #1d120d 0%, #3c2014 42%, #15212a 100%);
}}
button, input, select {{
  font: inherit;
}}
.shell {{
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr;
}}
.topbar {{
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 16px;
  align-items: center;
  padding: 14px 18px;
  color: #f9eac9;
  background: linear-gradient(90deg, rgba(36, 18, 11, .96), rgba(91, 33, 25, .94));
  border-bottom: 2px solid rgba(212, 169, 73, .55);
  position: sticky;
  top: 0;
  z-index: 20;
}}
.crest {{
  width: 58px;
  height: 58px;
  object-fit: cover;
  border: 2px solid var(--gold);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, .3);
  background: #120b08;
}}
.brand h1 {{
  margin: 0;
  font-size: 20px;
  line-height: 1.15;
  letter-spacing: 0;
}}
.brand .sub {{
  margin-top: 5px;
  font-size: 12px;
  color: #d7c399;
}}
.tabs {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}}
.tab {{
  border: 1px solid rgba(212, 169, 73, .5);
  color: #fbe6bd;
  background: rgba(0, 0, 0, .24);
  padding: 9px 12px;
  cursor: pointer;
  min-height: 36px;
}}
.tab.active {{
  background: var(--red);
  border-color: var(--gold);
}}
.content {{
  padding: 18px;
}}
.panel {{
  background:
    linear-gradient(180deg, rgba(255, 247, 218, .88), rgba(222, 193, 134, .94)),
    repeating-linear-gradient(90deg, rgba(94, 58, 29, .04) 0 1px, transparent 1px 6px);
  border: 1px solid #856236;
  box-shadow: var(--shadow);
}}
.toolbar {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}}
.search {{
  flex: 1 1 280px;
  min-width: 180px;
  color: var(--ink);
  background: #fff2c8;
  border: 1px solid #8a693d;
  padding: 10px 12px;
  outline: none;
}}
.badge-row {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}}
.badge {{
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 4px 8px;
  background: rgba(255, 249, 222, .58);
  border: 1px solid rgba(96, 63, 35, .35);
  color: #452814;
  font-size: 12px;
}}
.stats {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}}
.stat {{
  min-height: 92px;
  padding: 14px;
  border: 1px solid rgba(89, 54, 28, .35);
  background: rgba(255, 244, 206, .52);
}}
.stat strong {{
  display: block;
  font-size: 26px;
  line-height: 1;
  color: #6f1f1c;
}}
.stat span {{
  display: block;
  margin-top: 8px;
  color: #654727;
}}
.split {{
  display: grid;
  grid-template-columns: minmax(220px, 300px) 1fr;
  gap: 14px;
  align-items: start;
}}
.side {{
  max-height: calc(100vh - 150px);
  overflow: auto;
  padding: 10px;
}}
.list-button {{
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: rgba(255, 246, 216, .58);
  color: var(--ink);
  padding: 9px 10px;
  cursor: pointer;
  margin-bottom: 6px;
}}
.list-button:hover, .list-button.active {{
  border-color: var(--red-2);
  background: #fff0bd;
}}
.list-button .small {{
  display: block;
  margin-top: 3px;
  color: #765939;
  font-size: 11px;
  overflow-wrap: anywhere;
}}
.mission-stage {{
  overflow: auto;
  padding: 14px;
}}
.mission-board {{
  position: relative;
  min-height: 690px;
  background:
    linear-gradient(90deg, rgba(110, 70, 35, .10) 1px, transparent 1px),
    linear-gradient(0deg, rgba(110, 70, 35, .10) 1px, transparent 1px),
    rgba(255, 240, 190, .46);
  background-size: 210px 130px, 210px 130px, auto;
  border: 1px solid rgba(92, 58, 30, .35);
}}
.mission-links {{
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
}}
.mission-node {{
  position: absolute;
  width: 178px;
  min-height: 88px;
  border: 2px solid #6b4121;
  background: linear-gradient(180deg, #8b2c25, #4f1c18);
  color: #ffe7b5;
  box-shadow: 0 8px 16px rgba(50, 27, 14, .28);
  cursor: pointer;
  padding: 8px 9px;
}}
.mission-node.active {{
  outline: 3px solid var(--gold);
}}
.mission-icon {{
  font-size: 11px;
  color: #f5cf76;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.mission-title {{
  margin-top: 5px;
  font-size: 13px;
  line-height: 1.28;
  font-weight: 700;
}}
.mission-id {{
  margin-top: 5px;
  color: #d7bd85;
  font-size: 10px;
  overflow-wrap: anywhere;
}}
.detail {{
  padding: 14px;
  border-top: 1px solid var(--line);
  background: rgba(255, 248, 221, .62);
}}
.detail h2, .detail h3 {{
  margin: 0 0 8px;
  color: #61251b;
  letter-spacing: 0;
}}
.detail p {{
  margin: 6px 0 12px;
  line-height: 1.55;
}}
.script-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}}
.script-box {{
  min-width: 0;
}}
.script-box h4 {{
  margin: 0;
  padding: 8px 10px;
  color: #f7e4b9;
  background: #51311d;
  font-size: 13px;
}}
.tooltip-list {{
  border: 1px solid rgba(63, 38, 20, .55);
  background: linear-gradient(180deg, #1d1510, #2a1b13);
  color: #f4dfad;
  padding: 9px;
}}
.tip-line {{
  border-left: 3px solid #8f6d3e;
  padding: 6px 8px;
  margin: 4px 0;
  background: rgba(255, 238, 190, .06);
}}
.tip-line.good {{
  border-left-color: #5fa45d;
  color: #bdf0a9;
}}
.tip-line.bad {{
  border-left-color: #b4473f;
  color: #ffb5a9;
}}
.tip-line.need {{
  border-left-color: #d3aa4b;
  color: #ffe3a3;
}}
.tip-line.event {{
  border-left-color: #6aa5cf;
  color: #c7e7ff;
}}
.tip-line.muted {{
  border-left-color: #766552;
  color: #c9b893;
}}
.tip-main {{
  font-size: 13px;
  line-height: 1.42;
}}
.tip-detail {{
  margin-top: 3px;
  color: #c9b893;
  font-size: 12px;
  line-height: 1.42;
}}
.tip-children {{
  margin: 5px 0 0 12px;
}}
.game-preview {{
  margin: 12px 0;
  border: 2px solid rgba(95, 64, 34, .7);
  background: linear-gradient(180deg, rgba(39, 24, 15, .96), rgba(24, 17, 12, .97));
  color: #f6dfad;
  box-shadow: inset 0 0 0 1px rgba(245, 209, 130, .16);
}}
.game-preview-title {{
  padding: 9px 12px;
  color: #ffe4a4;
  background: linear-gradient(90deg, #5c251e, #3b2117);
  border-bottom: 1px solid rgba(212, 169, 73, .5);
  font-weight: 700;
}}
.game-preview-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
  padding: 10px;
}}
.game-section {{
  min-width: 0;
  border: 1px solid rgba(200, 162, 88, .35);
  background: rgba(255, 236, 180, .05);
}}
.game-section-title {{
  padding: 7px 9px;
  color: #e6c878;
  background: rgba(0, 0, 0, .23);
  border-bottom: 1px solid rgba(200, 162, 88, .22);
  font-size: 12px;
  font-weight: 700;
}}
.game-section-body {{
  padding: 8px;
}}
.mini-tips {{
  margin-top: 8px;
  border-top: 1px solid rgba(95, 64, 34, .3);
  padding-top: 7px;
}}
.mini-tip {{
  color: #614225;
  font-size: 12px;
  line-height: 1.35;
  margin-top: 3px;
}}
.option-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
  margin-top: 8px;
}}
.option-choice {{
  border: 1px solid rgba(118, 83, 42, .62);
  background: rgba(255, 240, 197, .72);
}}
.option-choice-title {{
  padding: 9px 10px;
  background: linear-gradient(90deg, #7b2a22, #5f231d);
  color: #ffe7ba;
  font-weight: 700;
}}
.option-choice .script-box {{
  padding: 8px;
}}
details.raw-script {{
  border: 1px solid rgba(92, 58, 30, .35);
  background: #fff0c0;
}}
details.raw-script summary {{
  cursor: pointer;
  padding: 8px 10px;
  color: #5c3720;
}}
details.raw-script pre {{
  border-left: 0;
  border-right: 0;
  border-bottom: 0;
}}
pre {{
  margin: 0;
  max-height: 420px;
  overflow: auto;
  padding: 10px;
  color: #1c140f;
  background: #fff4cd;
  border: 1px solid rgba(92, 58, 30, .35);
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 12px;
  line-height: 1.42;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}}
.cards {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}}
.item-card {{
  border: 1px solid rgba(88, 56, 30, .38);
  background: rgba(255, 246, 215, .58);
  padding: 12px;
  cursor: pointer;
  min-height: 150px;
}}
.item-card:hover, .item-card.active {{
  border-color: var(--red-2);
  background: #fff1c5;
}}
.item-card h3 {{
  margin: 0;
  color: #64251c;
  font-size: 16px;
  line-height: 1.3;
}}
.item-card p {{
  margin: 8px 0 0;
  color: #4f3822;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.event-window {{
  padding: 0;
  overflow: hidden;
}}
.event-picture {{
  min-height: 112px;
  display: flex;
  align-items: end;
  padding: 14px;
  color: #ffe9bd;
  background:
    linear-gradient(135deg, rgba(36, 17, 12, .2), rgba(19, 42, 56, .38)),
    linear-gradient(90deg, #5e2d22, #1f3c4d);
  border-bottom: 2px solid #80562c;
}}
.event-picture strong {{
  font-size: 13px;
  background: rgba(0, 0, 0, .35);
  padding: 4px 7px;
}}
.event-body {{
  padding: 14px;
}}
.option {{
  margin-top: 10px;
  border: 1px solid #8a6736;
  background: rgba(255, 242, 198, .68);
}}
.option-title {{
  padding: 9px 10px;
  background: #7b2a22;
  color: #ffe7ba;
  font-weight: 700;
}}
.option pre {{
  border: 0;
  border-top: 1px solid rgba(92, 58, 30, .35);
}}
.file-list {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  margin-top: 14px;
}}
.file-list h3 {{
  margin: 0 0 8px;
  color: #64251c;
}}
.file-list ul {{
  margin: 0;
  padding-left: 18px;
}}
.file-list li {{
  margin: 4px 0;
  overflow-wrap: anywhere;
}}
.muted {{
  color: var(--muted);
}}
.empty {{
  padding: 16px;
  color: var(--muted);
}}
@media (max-width: 860px) {{
  .topbar {{
    grid-template-columns: auto 1fr;
  }}
  .tabs {{
    grid-column: 1 / -1;
    justify-content: flex-start;
  }}
  .split {{
    grid-template-columns: 1fr;
  }}
  .side {{
    max-height: 280px;
  }}
}}
</style>
</head>
<body>
<div class="shell">
  <header class="topbar">
    <img class="crest" src="../../thumbnail.png" alt="">
    <div class="brand">
      <h1>{title}</h1>
      <div class="sub">任务、决议、事件可视化审阅器 · 生成时间 {generated}</div>
    </div>
    <nav class="tabs" id="tabs"></nav>
  </header>
  <main class="content" id="app"></main>
</div>
<script>
const DATA = {data_json};

const TABS = [
  ["overview", "总览"],
  ["missions", "任务树"],
  ["decisions", "决议"],
  ["events", "事件"],
  ["links", "触发链"]
];

let state = {{
  tab: "overview",
  query: "",
  missionGroup: DATA.missionGroups[0]?.id || "",
  mission: "",
  decision: "",
  event: DATA.events[0]?.id || ""
}};

function esc(value) {{
  return String(value ?? "").replace(/[&<>"']/g, ch => ({{
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }}[ch]));
}}

function renderTips(tips, depth = 0) {{
  if (!tips || !tips.length) return "";
  return `<div class="tooltip-list">${{tips.map(tip => `
    <div class="tip-line ${{esc(tip.tone || "info")}}">
      <div class="tip-main">${{esc(tip.text)}}</div>
      ${{tip.details ? `<div class="tip-detail">${{esc(tip.details)}}</div>` : ""}}
      ${{tip.children && tip.children.length ? `<div class="tip-children">${{renderTips(tip.children, depth + 1)}}</div>` : ""}}
    </div>
  `).join("")}}</div>`;
}}

function rawScript(value) {{
  if (!value) return "";
  return `<details class="raw-script"><summary>查看脚本原文</summary><pre>${{esc(value)}}</pre></details>`;
}}

function gameBlock(title, tips, script) {{
  if ((!tips || !tips.length) && !script) return "";
  const readable = tips && tips.length
    ? renderTips(tips)
    : `<div class="tooltip-list"><div class="tip-line muted"><div class="tip-main">暂无可自动解释的游戏提示。</div></div></div>`;
  return `<div class="script-box"><h4>${{esc(title)}}</h4>${{readable}}${{rawScript(script)}}</div>`;
}}

function gameSection(title, tips, script = "") {{
  if ((!tips || !tips.length) && !script) return "";
  const body = tips && tips.length
    ? renderTips(tips)
    : `<div class="tooltip-list"><div class="tip-line muted"><div class="tip-main">无额外游戏提示。</div></div></div>`;
  return `<section class="game-section">
    <div class="game-section-title">${{esc(title)}}</div>
    <div class="game-section-body">${{body}}${{rawScript(script)}}</div>
  </section>`;
}}

function gamePreview(title, sections) {{
  const visible = sections.filter(section => (section.tips && section.tips.length) || section.script);
  if (!visible.length) return "";
  return `<div class="game-preview">
    <div class="game-preview-title">${{esc(title)}}</div>
    <div class="game-preview-grid">${{visible.map(section => gameSection(section.title, section.tips, section.script)).join("")}}</div>
  </div>`;
}}

function optionPreview(options) {{
  if (!options || !options.length) return `<div class="empty">无 option。</div>`;
  return `<div class="option-grid">${{options.map(opt => `
    <article class="option-choice">
      <div class="option-choice-title">${{esc(opt.name)}}</div>
      ${{gameSection("选择此项后", opt.tips, opt.script)}}
    </article>
  `).join("")}}</div>`;
}}

function flattenTipTexts(tips, limit = 3) {{
  const lines = [];
  const visit = (items) => {{
    for (const tip of items || []) {{
      if (tip.tone !== "muted" && tip.text) lines.push(tip.text);
      if (lines.length >= limit) return;
      if (tip.children && tip.children.length) visit(tip.children);
      if (lines.length >= limit) return;
    }}
  }};
  visit(tips || []);
  return lines.slice(0, limit);
}}

function miniTips(label, tips, limit = 3) {{
  const lines = flattenTipTexts(tips, limit);
  if (!lines.length) return "";
  return `<div class="mini-tips"><strong>${{esc(label)}}</strong>${{lines.map(line => `<div class="mini-tip">${{esc(line)}}</div>`).join("")}}</div>`;
}}

function badge(value) {{
  return value ? `<span class="badge">${{esc(value)}}</span>` : "";
}}

function fileLine(item) {{
  return `${{item.file}}:${{item.line}}`;
}}

function textMatches(item, query) {{
  if (!query) return true;
  const hay = [
    item.id, item.title, item.desc, item.file, item.category,
    item.titleKey, item.descKey, item.picture, item.icon,
    ...(item.eventRefs || []), ...(item.flagRefs || [])
  ].join(" ").toLowerCase();
  return hay.includes(query.toLowerCase());
}}

function setTab(tab) {{
  state.tab = tab;
  render();
}}

function renderTabs() {{
  document.getElementById("tabs").innerHTML = TABS.map(([id, label]) =>
    `<button class="tab ${{state.tab === id ? "active" : ""}}" onclick="setTab('${{id}}')">${{label}}</button>`
  ).join("");
}}

function renderSearch() {{
  return `<input class="search" value="${{esc(state.query)}}" placeholder="搜索标题、ID、文件、flag、事件引用" oninput="state.query=this.value; render()">`;
}}

function renderOverview() {{
  const c = DATA.counts;
  const missing = DATA.localisation.missing.slice(0, 60);
  return `
    <section class="panel detail">
      <div class="toolbar">
        <div class="badge-row">
          ${{badge(DATA.descriptor.version ? "Mod 版本 " + DATA.descriptor.version : "")}}
          ${{badge(DATA.descriptor.supported_version ? "支持 EU4 " + DATA.descriptor.supported_version : "")}}
          ${{badge("路径 " + DATA.modRoot)}}
        </div>
      </div>
      <div class="stats">
        <div class="stat"><strong>${{c.missionGroups}}</strong><span>任务组</span></div>
        <div class="stat"><strong>${{c.missions}}</strong><span>任务节点</span></div>
        <div class="stat"><strong>${{c.decisions}}</strong><span>决议</span></div>
        <div class="stat"><strong>${{c.events}}</strong><span>事件</span></div>
        <div class="stat"><strong>${{c.localisationKeys}}</strong><span>本地化键</span></div>
        <div class="stat"><strong>${{c.missingLocalisation}}</strong><span>疑似缺失文本</span></div>
      </div>
      <p class="muted">本页是静态审阅器；重新运行 <code>generate_visualizer.py</code> 可刷新所有数据。</p>
      ${{DATA.warnings.length ? `<h3>解析警告</h3><pre>${{esc(DATA.warnings.join("\\n"))}}</pre>` : ""}}
      ${{missing.length ? `<h3>疑似缺失本地化</h3><pre>${{esc(missing.join("\\n"))}}${{DATA.localisation.missing.length > missing.length ? "\\n..." : ""}}</pre>` : ""}}
      <div class="file-list">
        ${{Object.entries(DATA.files).map(([kind, files]) => `
          <div>
            <h3>${{esc(kind)}}</h3>
            <ul>${{files.map(file => `<li>${{esc(file)}}</li>`).join("")}}</ul>
          </div>
        `).join("")}}
      </div>
    </section>
  `;
}}

function selectedGroup() {{
  return DATA.missionGroups.find(group => group.id === state.missionGroup) || DATA.missionGroups[0];
}}

function missionCoords(mission) {{
  const cellW = 210;
  const cellH = 130;
  return {{
    x: (mission.column - 1) * cellW + 18,
    y: (mission.row - 1) * cellH + 18,
    w: 178,
    h: 88
  }};
}}

function renderMissionBoard(group) {{
  const missions = group.missions.filter(m => textMatches(m, state.query));
  const allById = new Map(group.missions.map(m => [m.id, m]));
  const cols = Math.max(1, ...group.missions.map(m => m.column));
  const width = cols * 210 + 34;
  const height = 5 * 130 + 34;
  const paths = [];
  for (const mission of missions) {{
    for (const req of mission.requiredMissions || []) {{
      const prev = allById.get(req);
      if (!prev || !textMatches(prev, state.query)) continue;
      const a = missionCoords(prev);
      const b = missionCoords(mission);
      const x1 = a.x + a.w / 2;
      const y1 = a.y + a.h;
      const x2 = b.x + b.w / 2;
      const y2 = b.y;
      const mid = (y1 + y2) / 2;
      paths.push(`<path d="M ${{x1}} ${{y1}} C ${{x1}} ${{mid}}, ${{x2}} ${{mid}}, ${{x2}} ${{y2}}" fill="none" stroke="#5a321b" stroke-width="3" opacity=".65"/>`);
    }}
  }}
  const nodes = missions.map(m => {{
    const p = missionCoords(m);
    return `<button class="mission-node ${{state.mission === m.id ? "active" : ""}}" style="left:${{p.x}}px;top:${{p.y}}px" onclick="state.mission='${{m.id}}'; render()">
      <div class="mission-icon">${{esc(m.icon || "mission")}}</div>
      <div class="mission-title">${{esc(m.title)}}</div>
      <div class="mission-id">${{esc(m.id)}}</div>
    </button>`;
  }}).join("");
  return `<div class="mission-board" style="width:${{width}}px;height:${{height}}px">
    <svg class="mission-links" width="${{width}}" height="${{height}}">${{paths.join("")}}</svg>
    ${{nodes}}
  </div>`;
}}

function renderMissionDetail(group) {{
  const mission = group.missions.find(m => m.id === state.mission) || group.missions[0];
  if (!mission) return `<div class="detail empty">这个任务组没有节点。</div>`;
  state.mission = mission.id;
  return `<section class="detail">
    <h2>${{esc(mission.title)}}</h2>
    <div class="badge-row">
      ${{badge(mission.id)}}
      ${{badge("slot " + group.slot)}}
      ${{badge("position " + mission.position)}}
      ${{badge(mission.icon)}}
      ${{badge(fileLine(mission))}}
    </div>
    <p>${{esc(mission.desc || "无描述文本。")}}</p>
    <div class="badge-row">
      ${{(mission.requiredMissions || []).map(req => badge("前置 " + req)).join("")}}
      ${{(mission.eventRefs || []).map(ref => badge("触发事件 " + ref)).join("")}}
    </div>
    ${{gamePreview("游戏内预览", [
      {{ title: "完成条件", tips: mission.triggerTips, script: mission.trigger }},
      {{ title: "奖励 / 加成", tips: mission.effectTips, script: mission.effect }}
    ])}}
  </section>`;
}}

function renderMissions() {{
  const group = selectedGroup();
  if (!group) return `<section class="panel empty">没有读取到任务树。</section>`;
  if (!state.mission || !group.missions.some(m => m.id === state.mission)) {{
    state.mission = group.missions[0]?.id || "";
  }}
  return `<div class="toolbar">${{renderSearch()}}<div class="badge-row">${{badge("任务组 " + DATA.missionGroups.length)}}${{badge("任务 " + DATA.counts.missions)}}</div></div>
    <div class="split">
      <aside class="panel side">
        ${{DATA.missionGroups.map(g => `<button class="list-button ${{g.id === group.id ? "active" : ""}}" onclick="state.missionGroup='${{g.id}}'; state.mission=''; render()">
          <strong>${{esc(g.id)}}</strong>
          <span class="small">slot ${{g.slot}} · ${{g.missions.length}} 个任务 · ${{esc(g.file)}}</span>
        </button>`).join("")}}
      </aside>
      <section class="panel">
        <div class="detail">
          <h2>${{esc(group.id)}}</h2>
          <div class="badge-row">${{badge("slot " + group.slot)}}${{badge("generic " + group.generic)}}${{badge("ai " + group.ai)}}${{badge(group.file + ":" + group.line)}}</div>
          ${{gameBlock("任务组显示条件", group.potentialTips, group.potential)}}
        </div>
        <div class="mission-stage">${{renderMissionBoard(group)}}</div>
        ${{renderMissionDetail(group)}}
      </section>
    </div>`;
}}

function renderDecisions() {{
  const filtered = DATA.decisions.filter(item => textMatches(item, state.query));
  const selected = DATA.decisions.find(d => d.id === state.decision) || filtered[0] || DATA.decisions[0];
  if (selected) state.decision = selected.id;
  return `<div class="toolbar">${{renderSearch()}}<div class="badge-row">${{badge(filtered.length + " / " + DATA.decisions.length + " 决议")}}</div></div>
    <div class="split">
      <section class="cards">
        ${{filtered.map(d => `<article class="item-card ${{d.id === state.decision ? "active" : ""}}" onclick="state.decision='${{d.id}}'; render()">
          <h3>${{esc(d.title)}}</h3>
          <div class="badge-row">${{badge(d.id)}}${{badge(d.category)}}${{badge(d.major === "yes" ? "major" : "")}}</div>
          <p>${{esc(d.desc || "无描述文本。")}}</p>
          ${{miniTips("条件", d.allowTips.length ? d.allowTips : d.potentialTips, 2)}}
          ${{miniTips("执行后", d.effectTips, 2)}}
        </article>`).join("") || `<div class="panel empty">没有匹配的决议。</div>`}}
      </section>
      <section class="panel detail">
        ${{selected ? renderDecisionDetail(selected) : ""}}
      </section>
    </div>`;
}}

function renderDecisionDetail(d) {{
  return `<h2>${{esc(d.title)}}</h2>
    <div class="badge-row">${{badge(d.id)}}${{badge(fileLine(d))}}${{(d.eventRefs || []).map(ref => badge("触发事件 " + ref)).join("")}}</div>
    <p>${{esc(d.desc || "无描述文本。")}}</p>
    ${{gamePreview("游戏内预览", [
      {{ title: "出现条件", tips: d.potentialTips, script: d.potential }},
      {{ title: "可执行条件", tips: d.allowTips, script: d.allow }},
      {{ title: "执行后加成 / 效果", tips: d.effectTips, script: d.effect }},
      {{ title: "AI 倾向", tips: d.aiWillDoTips, script: d.aiWillDo }}
    ])}}`;
}}

function renderEvents() {{
  const filtered = DATA.events.filter(item => textMatches(item, state.query));
  const selected = DATA.events.find(e => e.id === state.event) || filtered[0] || DATA.events[0];
  if (selected) state.event = selected.id;
  return `<div class="toolbar">${{renderSearch()}}<div class="badge-row">${{badge(filtered.length + " / " + DATA.events.length + " 事件")}}</div></div>
    <div class="split">
      <aside class="panel side">
        ${{filtered.map(e => `<button class="list-button ${{e.id === state.event ? "active" : ""}}" onclick="state.event='${{e.id}}'; render()">
          <strong>${{esc(e.id)}} · ${{esc(e.title)}}</strong>
          <span class="small">${{esc(e.category)}} · ${{e.hidden ? "hidden" : e.type}} · ${{esc(e.picture || "no picture")}}</span>
          ${{miniTips("触发", e.triggerTips, 2)}}
        </button>`).join("") || `<div class="empty">没有匹配的事件。</div>`}}
      </aside>
      <section class="panel event-window">
        ${{selected ? renderEventDetail(selected) : ""}}
      </section>
    </div>`;
}}

function renderEventDetail(e) {{
  const inbound = DATA.eventInboundRefs[e.id] || [];
  return `<div class="event-picture"><strong>${{esc(e.picture || (e.hidden ? "hidden event" : "event picture"))}}</strong></div>
    <div class="event-body">
      <h2>${{esc(e.title)}}</h2>
      <div class="badge-row">${{badge(e.id)}}${{badge(e.type)}}${{badge(e.triggeredOnly ? "triggered only" : "MTTH")}}${{badge(fileLine(e))}}</div>
      <p>${{esc(e.desc || (e.hidden ? "隐藏事件，无玩家文本。" : "无描述文本。"))}}</p>
      <div class="badge-row">
        ${{inbound.map(ref => badge("来源 " + ref.kind + " · " + ref.id)).join("")}}
        ${{(e.eventRefs || []).filter(ref => ref !== e.id).map(ref => badge("后续 " + ref)).join("")}}
      </div>
      ${{gamePreview("事件触发", [
        {{ title: "触发条件", tips: e.triggerTips, script: e.trigger }},
        {{ title: "平均触发时间", tips: e.mtthTips, script: e.mtth }},
        {{ title: "立即加成 / 效果", tips: e.immediateTips, script: e.immediate }}
      ])}}
      <h3>选项</h3>
      ${{optionPreview(e.options)}}
    </div>`;
}}

function renderLinks() {{
  const rows = Object.entries(DATA.eventInboundRefs)
    .filter(([eventId, refs]) => !state.query || eventId.toLowerCase().includes(state.query.toLowerCase()) || refs.some(ref => textMatches(ref, state.query)))
    .sort((a, b) => a[0].localeCompare(b[0]));
  return `<div class="toolbar">${{renderSearch()}}<div class="badge-row">${{badge(rows.length + " 个被触发事件")}}</div></div>
    <section class="panel detail">
      <h2>事件触发链</h2>
      <p class="muted">这里列出任务、决议、事件脚本中直接调用的 <code>country_event/province_event</code>。</p>
      <div class="cards">
        ${{rows.map(([eventId, refs]) => {{
          const event = DATA.events.find(e => e.id === eventId);
          return `<article class="item-card" onclick="state.tab='events'; state.event='${{eventId}}'; render()">
            <h3>${{esc(eventId)}}${{event ? " · " + esc(event.title) : ""}}</h3>
            <div class="badge-row">${{refs.map(ref => badge(ref.kind + " · " + ref.id)).join("")}}</div>
            <p>${{event ? esc(event.desc || event.file) : "脚本引用了这个事件，但当前 events 文件中没有读取到同名事件。"}} </p>
          </article>`;
        }}).join("") || `<div class="empty">没有直接事件调用。</div>`}}
      </div>
    </section>`;
}}

function render() {{
  renderTabs();
  const app = document.getElementById("app");
  if (state.tab === "overview") app.innerHTML = renderOverview();
  if (state.tab === "missions") app.innerHTML = renderMissions();
  if (state.tab === "decisions") app.innerHTML = renderDecisions();
  if (state.tab === "events") app.innerHTML = renderEvents();
  if (state.tab === "links") app.innerHTML = renderLinks();
}}

render();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Japan Expanded mod visual review page.")
    parser.add_argument("--mod-root", type=Path, default=MOD_ROOT, help="Path to the EU4 mod root.")
    parser.add_argument("--game-root", type=Path, default=None, help="Path to the EU4 game root, for province names.")
    parser.add_argument("--output", type=Path, default=OUTPUT_HTML, help="Output HTML file.")
    args = parser.parse_args()
    mod_root = args.mod_root.resolve()
    game_root = args.game_root.resolve() if args.game_root else None
    data = build_data(mod_root, game_root)
    args.output.write_text(html_page(data), encoding="utf-8", newline="\r\n")
    print(f"Wrote {args.output}")
    print(
        "Counts: "
        f"{data['counts']['missionGroups']} mission groups, "
        f"{data['counts']['missions']} missions, "
        f"{data['counts']['decisions']} decisions, "
        f"{data['counts']['events']} events, "
        f"{data['counts']['missingLocalisation']} missing localisation keys"
    )
    if data["warnings"]:
        print("Warnings:")
        for warning in data["warnings"]:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
