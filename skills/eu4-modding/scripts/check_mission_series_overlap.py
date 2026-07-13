#!/usr/bin/env python3
"""Check active EU4 mission series and cells in representative route profiles.

This is a conservative static check for Japan-route style trees. It evaluates
mission group `potential` blocks against representative route profiles. For
independently authored custom trees, two simultaneously active series in one
slot are treated as unsafe even when their occupied rows are disjoint, so both
series-slot overlaps and duplicate `(slot, row)` cells are rejected.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CORE_TAGS = {"JAP", "KJP", "CJP", "EJP", "RFJ", "SJP", "IJP", "WAK"}
ROUTE_FLAGS = {
    "jxp_path_sakoku",
    "jxp_path_open_trade",
    "jxp_path_kirishitan",
    "jxp_path_confucian",
    "jxp_path_imperial",
    "jxp_path_reformed",
    "jxp_path_kaikyo",
    "jxp_path_ikko",
    "jxp_path_wokou",
}

ROUTE_PROFILES = {
    "sakoku": {
        "tag": "JAP",
        "flags": {"jxp_path_sakoku"},
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": False,
    },
    "open": {
        "tag": "JAP",
        "flags": {"jxp_path_open_trade"},
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": False,
    },
    "kirishitan": {
        "tag": "KJP",
        "flags": {"jxp_path_kirishitan"},
        "religion": "catholic",
        "religion_group": "christian",
        "daimyo": False,
    },
    "reformed": {
        "tag": "RFJ",
        "flags": {"jxp_path_reformed"},
        "religion": "reformed",
        "religion_group": "christian",
        "daimyo": False,
    },
    "confucian": {
        "tag": "CJP",
        "flags": {"jxp_path_confucian", "jxp_confucian_shinto_syncretism"},
        "religion": "confucianism",
        "religion_group": "eastern",
        "daimyo": False,
    },
    "imperial": {
        "tag": "EJP",
        "flags": {"jxp_path_imperial"},
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": False,
    },
    "kaikyo": {
        "tag": "SJP",
        "flags": {"jxp_path_kaikyo"},
        "religion": "sunni",
        "religion_group": "muslim",
        "daimyo": False,
    },
    "ikko": {
        "tag": "IJP",
        "flags": {"jxp_path_ikko"},
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": False,
    },
    "wokou": {
        "tag": "WAK",
        "flags": {"jxp_path_wokou"},
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": False,
    },
    "daimyo_warrior": {
        "tag": "ODA",
        "flags": set(),
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": True,
    },
    "daimyo_court": {
        "tag": "ASK",
        "flags": set(),
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": True,
    },
    "daimyo_maritime": {
        "tag": "OTM",
        "flags": set(),
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": True,
    },
    "daimyo_frontier": {
        "tag": "DTE",
        "flags": set(),
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": True,
    },
    "daimyo_temple_market": {
        "tag": "IMG",
        "flags": set(),
        "religion": "shinto",
        "religion_group": "eastern",
        "daimyo": True,
    },
}


def strip_comments(text: str) -> str:
    return re.sub(r"#.*", "", text)


def tokenize(text: str) -> list[str]:
    return re.findall(r'"[^"]*"|[{}=]|[A-Za-z0-9_\.\:-]+', strip_comments(text))


def parse_sequence(tokens: list[str], index: int = 0) -> tuple[list[tuple[str, object]], int]:
    nodes: list[tuple[str, object]] = []
    while index < len(tokens) and tokens[index] != "}":
        key = tokens[index]
        index += 1
        if index < len(tokens) and tokens[index] == "=":
            index += 1
            if index < len(tokens) and tokens[index] == "{":
                child, index = parse_sequence(tokens, index + 1)
                if index < len(tokens) and tokens[index] == "}":
                    index += 1
                nodes.append((key, child))
            elif index < len(tokens):
                nodes.append((key, tokens[index].strip('"')))
                index += 1
        else:
            nodes.append((key, "yes"))
    return nodes, index


def eval_sequence(nodes: list[tuple[str, object]], profile: dict[str, object]) -> bool:
    return all(eval_node(node, profile) for node in nodes)


def eval_node(node: tuple[str, object], profile: dict[str, object]) -> bool:
    key, value = node
    if key == "OR" and isinstance(value, list):
        return any(eval_node(child, profile) for child in value)
    if key == "AND" and isinstance(value, list):
        return eval_sequence(value, profile)
    if key == "NOT" and isinstance(value, list):
        return not eval_sequence(value, profile)
    if key == "always":
        return value == "yes"
    if key == "tag":
        return profile["tag"] == value
    if key == "has_country_flag":
        return value in profile["flags"]
    if key == "religion":
        return profile["religion"] == value
    if key == "religion_group":
        return profile["religion_group"] == value
    if key == "map_setup":
        return False
    if key == "has_harmonized_with":
        return profile["religion"] == "confucianism" and value == "shinto"
    if key == "jxp_is_daimyo_stage_trigger":
        return bool(profile["daimyo"])
    if key == "jxp_is_japanese_polity_trigger":
        return True
    if key == "jxp_has_any_route_trigger":
        return bool(profile["flags"] & ROUTE_FLAGS)
    if key == "jxp_not_sakoku_locked_trigger":
        return "jxp_path_sakoku" not in profile["flags"]
    if key == "jxp_can_use_overseas_expansion_trigger":
        return "jxp_path_sakoku" not in profile["flags"] and (
            profile["tag"] in CORE_TAGS or bool(profile["flags"] & ROUTE_FLAGS)
        )

    # Unknown predicates are treated as true so this check errs toward finding
    # possible overlaps instead of silently missing them.
    return True


def split_top_level_groups(text: str) -> list[tuple[str, str]]:
    groups: list[tuple[str, str]] = []
    depth = 0
    start: int | None = None
    name: str | None = None
    index = 0
    while index < len(text):
        if depth == 0:
            match = re.match(r"\s*([A-Za-z0-9_\ufeff]+)\s*=\s*\{", text[index:])
            if match:
                name = match.group(1).lstrip("\ufeff")
                start = index + match.end() - 1
                depth = 1
                index = start + 1
                continue
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and name is not None and start is not None:
                groups.append((name, text[start + 1 : index]))
                name = None
                start = None
        index += 1
    return groups


def first_named_block(body: str, key: str) -> str:
    match = re.search(r"\b" + re.escape(key) + r"\s*=\s*\{", body)
    if not match:
        return ""
    start = match.end() - 1
    depth = 1
    index = start + 1
    while index < len(body):
        if body[index] == "{":
            depth += 1
        elif body[index] == "}":
            depth -= 1
            if depth == 0:
                return body[start + 1 : index]
        index += 1
    return ""


def mission_groups(mod_path: Path) -> list[tuple[str, str, int, tuple[int, ...], list[tuple[str, object]]]]:
    groups: list[tuple[str, str, int, tuple[int, ...], list[tuple[str, object]]]] = []
    for path in sorted((mod_path / "missions").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        for name, body in split_top_level_groups(text):
            if re.search(r"^\s*generic\s*=\s*yes\b", body, re.MULTILINE):
                continue
            slot_match = re.search(r"^\s*slot\s*=\s*(\d+)", body, re.MULTILINE)
            if not slot_match:
                continue
            potential = first_named_block(body, "potential")
            nodes, _ = parse_sequence(tokenize(potential))
            positions = tuple(
                int(value)
                for value in re.findall(r"(?m)^\s*position\s*=\s*(\d+)\b", body)
            )
            groups.append((name, path.name, int(slot_match.group(1)), positions, nodes))
    return groups


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mod_path", type=Path)
    args = parser.parse_args()

    groups = mission_groups(args.mod_path)
    failed = False
    for route, profile in ROUTE_PROFILES.items():
        by_cell: dict[tuple[int, int], list[str]] = {}
        by_slot: dict[int, list[str]] = {}
        for name, file_name, slot, positions, potential in groups:
            if eval_sequence(potential, profile):
                by_slot.setdefault(slot, []).append(f"{name} ({file_name})")
                for position in positions:
                    by_cell.setdefault((slot, position), []).append(f"{name} ({file_name})")
        series_overlaps = {
            slot: names for slot, names in by_slot.items() if len(names) > 1
        }
        if series_overlaps:
            failed = True
            print(f"SERIES OVERLAP: {route}")
            for slot, names in sorted(series_overlaps.items()):
                print(f"  slot {slot}: " + " ; ".join(names))
        overlaps = {cell: names for cell, names in by_cell.items() if len(names) > 1}
        if overlaps:
            failed = True
            print(f"OVERLAP: {route}")
            for (slot, position), names in sorted(overlaps.items()):
                print(f"  slot {slot}, row {position}: " + " ; ".join(names))

    if failed:
        return 1
    print("OK: no route-profile mission series or cell overlaps found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
