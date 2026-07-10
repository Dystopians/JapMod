#!/usr/bin/env python3
"""Project-specific static checks for JXP map missions, events, decisions, and debug state."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
BUILDER_DIR = MOD_ROOT / "tools" / "jxp_map_builder"


class Report:
    def __init__(self):
        self.errors = []
        self.notes = []

    def error(self, message):
        self.errors.append(message)

    def note(self, message):
        self.notes.append(message)

    def emit(self):
        for message in self.notes:
            print(f"NOTE: {message}")
        for message in self.errors:
            print(f"ERROR: {message}")
        print(f"SUMMARY: {len(self.errors)} error(s), 0 warning(s)")
        return 1 if self.errors else 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--main-mod", type=Path, required=True)
    return parser.parse_args()


def extract_block(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        return None
    cursor = match.end() - 1
    depth = 0
    in_quote = False
    escaped = False
    while cursor < len(text):
        char = text[cursor]
        if escaped:
            escaped = False
        elif char == "\\" and in_quote:
            escaped = True
        elif char == '"':
            in_quote = not in_quote
        elif not in_quote and char == "#":
            newline = text.find("\n", cursor)
            cursor = len(text) if newline < 0 else newline
            continue
        elif not in_quote and char == "{":
            depth += 1
        elif not in_quote and char == "}":
            depth -= 1
            if depth == 0:
                return text[match.start():cursor + 1]
        cursor += 1
    return None


def load_visualizer(path: Path):
    spec = importlib.util.spec_from_file_location("jxp_content_visualizer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    args = parse_args()
    report = Report()
    history_plan = json.loads((BUILDER_DIR / "history_plan.json").read_text(encoding="utf-8"))
    plan = json.loads((BUILDER_DIR / "province_plan.json").read_text(encoding="utf-8"))
    tags = {country["tag"] for country in history_plan["countries"]}
    trigger_text = (MOD_ROOT / "common" / "scripted_triggers" / "jxp_map_triggers.txt").read_text(encoding="cp1252")
    effect_text = (MOD_ROOT / "common" / "scripted_effects" / "jxp_map_effects.txt").read_text(encoding="cp1252")
    mission_text = (MOD_ROOT / "missions" / "jxp_map_new_daimyo_missions.txt").read_text(encoding="cp1252")
    event_text = (MOD_ROOT / "events" / "jxp_map_events.txt").read_text(encoding="cp1252")
    decision_text = (MOD_ROOT / "decisions" / "jxp_map_decisions.txt").read_text(encoding="cp1252")
    debug_text = (MOD_ROOT / "decisions" / "jxp_map_debug_decisions.txt").read_text(encoding="cp1252")
    modifier_text = (MOD_ROOT / "common" / "event_modifiers" / "jxp_map_modifiers.txt").read_text(encoding="cp1252")

    tag_block = extract_block(trigger_text, "jxp_map_is_new_daimyo_tag_trigger") or ""
    trigger_tags = re.findall(r"\btag\s*=\s*([A-Z0-9]{3})", tag_block)
    if set(trigger_tags) != tags or len(trigger_tags) != len(tags):
        report.error(f"New-daimyo trigger coverage differs from country plan: {Counter(trigger_tags)}")

    group_keys = [
        "jxp_map_is_warrior_house_trigger", "jxp_map_is_court_house_trigger",
        "jxp_map_is_sea_house_trigger", "jxp_map_is_frontier_house_trigger",
        "jxp_map_is_temple_market_house_trigger",
    ]
    group_members = []
    for key in group_keys:
        block = extract_block(trigger_text, key) or ""
        group_members.extend(re.findall(r"\btag\s*=\s*([A-Z0-9]{3})", block))
    counts = Counter(group_members)
    bad_group_coverage = {tag: counts[tag] for tag in sorted(tags) if counts[tag] != 1}
    if bad_group_coverage:
        report.error(f"Tags must belong to exactly one house group: {bad_group_coverage}")

    mission_tags = re.findall(r"\btag\s*=\s*([A-Z0-9]{3})", mission_text)
    mission_counts = Counter(mission_tags)
    bad_mission_coverage = {tag: mission_counts[tag] for tag in sorted(tags) if mission_counts[tag] != 1}
    if bad_mission_coverage:
        report.error(f"Mission potentials must explicitly cover each new tag once: {bad_mission_coverage}")

    for tag in tags:
        flag = f"jxp_map_origin_{tag.lower()}"
        if f"set_country_flag = {flag}" not in effect_text:
            report.error(f"Origin recorder does not set {flag}")
        if f"clr_country_flag = {flag}" not in effect_text:
            report.error(f"Origin reset does not clear {flag}")

    set_flags = set(re.findall(r"set_country_flag\s*=\s*(jxp_map_(?:policy_[a-z_]+|[a-z0-9]+_seen))", event_text + decision_text))
    cleared_flags = set(re.findall(r"clr_country_flag\s*=\s*(jxp_map_[a-z0-9_]+)", effect_text))
    missing_cleanup = set_flags - cleared_flags
    if missing_cleanup:
        report.error(f"Debug cleanup misses one-time content flags: {sorted(missing_cleanup)}")

    defined_modifiers = set(re.findall(r"(?m)^\s*(jxp_map_[a-z0-9_]+)\s*=\s*\{", modifier_text))
    referenced_modifiers = set(re.findall(r"name\s*=\s*(jxp_map_[a-z0-9_]+)", event_text + mission_text + effect_text))
    referenced_modifiers.update(re.findall(r"remove_(?:country|province)_modifier\s*=\s*(jxp_map_[a-z0-9_]+)", effect_text))
    missing_modifiers = referenced_modifiers - defined_modifiers
    if missing_modifiers:
        report.error(f"Content references undefined modifiers: {sorted(missing_modifiers)}")

    event_ids = re.findall(r"\bid\s*=\s*(jxp_map\.\d+)", event_text)
    duplicates = [key for key, count in Counter(event_ids).items() if count != 1]
    if duplicates:
        report.error(f"Duplicate event IDs: {duplicates}")
    if "namespace = jxp_map" not in event_text:
        report.error("jxp_map event namespace is missing")
    if "tag = ARI" not in event_text or "year = 1543" not in event_text:
        report.error("Arima overseas-contact event lacks the 1543 chronology gate")

    debug_decisions = re.findall(r"(?m)^\s*(jxp_map_debug_[a-z0-9_]+)\s*=\s*\{", debug_text)
    for key in debug_decisions:
        block = extract_block(debug_text, key) or ""
        if "has_country_flag = jxp_debug_enabled" not in block:
            report.error(f"Debug decision {key} is not gated by the main debug flag")
        if key not in {"jxp_map_debug_show_panel"} and "has_country_flag = jxp_map_debug_panel" not in block:
            report.error(f"Debug decision {key} is not gated by the map debug panel")

    main_debug = (args.main_mod.resolve() / "common" / "scripted_effects" / "jxp_debug_effects.txt").read_text(encoding="cp1252")
    unify = extract_block(main_debug, "jxp_debug_unify_japan_effect") or ""
    if "every_province" not in unify or "region = japan_region" not in unify:
        report.error("Main one-click unification effect does not scope over japan_region")

    valid_provinces = set(plan["existing_japan_ids"]) | {item["id"] for item in plan["new_provinces"]}
    hardcoded_new = {int(value) for value in re.findall(r"\b(49(?:4[2-9]|[5-7]\d|8[01]))\b", event_text + mission_text + decision_text + debug_text)}
    invalid_provinces = hardcoded_new - valid_provinces
    if invalid_provinces:
        report.error(f"Content references unknown new province IDs: {sorted(invalid_provinces)}")

    visualizer_path = args.main_mod.resolve() / "tools" / "jxp_visualizer" / "generate_visualizer.py"
    visualizer = load_visualizer(visualizer_path)
    data = visualizer.build_data(MOD_ROOT, args.game_root.resolve())
    if data["counts"]["missingLocalisation"]:
        report.error(f"Visualizer reports {data['counts']['missingLocalisation']} missing localisation keys")
    if data["warnings"]:
        report.error(f"Visualizer parse warnings: {data['warnings']}")
    expected_counts = {"missionGroups": 5, "missions": 30, "decisions": 26, "events": 19}
    for key, expected in expected_counts.items():
        if data["counts"][key] != expected:
            report.error(f"Visualizer count {key}={data['counts'][key]}, expected {expected}")
    report.note(
        f"Content inventory: {data['counts']['missionGroups']} mission groups, {data['counts']['missions']} missions, "
        f"{data['counts']['decisions']} decisions, {data['counts']['events']} events"
    )
    report.note(f"Origin and house-group coverage: {len(tags)} / {len(tags)} tags")
    report.note(f"Debug cleanup covers {len(set_flags)} one-time flags and {len(referenced_modifiers)} modifiers")
    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
