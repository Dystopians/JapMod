#!/usr/bin/env python3
"""Rewrite JXP route/founder reforms for stable EU4 1.37 government-tree loading."""

from __future__ import annotations

from pathlib import Path
import re
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reflow_missions_v023 import matching_brace


ROUTE_CONDITIONS = {
    "sakoku": (None, "jxp_path_sakoku"),
    "open": (None, "jxp_path_open_trade"),
    "kirishitan": ("KJP", "jxp_path_kirishitan"),
    "confucian": ("CJP", "jxp_path_confucian"),
    "imperial": ("EJP", "jxp_path_imperial"),
    "reformed": ("RFJ", "jxp_path_reformed"),
    "kaikyo": ("SJP", "jxp_path_kaikyo"),
    "ikko": ("IJP", "jxp_path_ikko"),
    "wokou": ("WAK", "jxp_path_wokou"),
}


def top_level_blocks(text: str) -> tuple[tuple[str, int, int], ...]:
    pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)[ \t]*=[ \t]*\{")
    blocks: list[tuple[str, int, int]] = []
    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        closing = matching_brace(text, opening)
        blocks.append((match.group(1), match.start(), closing + 1))
    return tuple(blocks)


def replace_object(block: str, key: str, replacement: str) -> str:
    match = re.search(rf"(?m)^\t{re.escape(key)}[ \t]*=[ \t]*\{{", block)
    if match is None:
        raise ValueError(f"missing {key} object")
    opening = block.find("{", match.start(), match.end())
    closing = matching_brace(block, opening)
    return block[: match.start()] + replacement + block[closing + 1 :]


def remove_objects(block: str, key: str) -> str:
    pattern = re.compile(rf"(?m)^\t{re.escape(key)}[ \t]*=[ \t]*\{{")
    while True:
        match = pattern.search(block)
        if match is None:
            return block
        opening = block.find("{", match.start(), match.end())
        closing = matching_brace(block, opening)
        end = closing + 1
        if end < len(block) and block[end] == "\n":
            end += 1
        block = block[: match.start()] + block[end:]


def normalize_common_fields(block: str) -> str:
    block = re.sub(r"(?m)^\t(?:monarchy|republic)\s*=\s*yes\s*\r?\n", "", block)
    if re.search(r"(?m)^\tallow_normal_conversion\s*=", block) is None:
        icon = re.search(r'(?m)^\ticon\s*=\s*"[^"]+"\s*$' , block)
        if icon is None:
            raise ValueError("reform is missing icon")
        block = block[: icon.end()] + "\n\tallow_normal_conversion = yes" + block[icon.end() :]
    return block


def route_key(reform_id: str) -> str:
    stem = reform_id.removeprefix("jxp_reform_")
    key = stem.split("_", 1)[0]
    if key not in ROUTE_CONDITIONS:
        raise ValueError(f"unknown route prefix in {reform_id}")
    return key


def route_trigger(route: str) -> str:
    tag, flag = ROUTE_CONDITIONS[route]
    if tag is None:
        return f"\ttrigger = {{\n\t\thas_country_flag = {flag}\n\t}}"
    return (
        "\ttrigger = {\n"
        "\t\tOR = {\n"
        f"\t\t\ttag = {tag}\n"
        f"\t\t\thas_country_flag = {flag}\n"
        "\t\t}\n"
        "\t}"
    )


def rewrite_route_file(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8-sig")
    rewritten = text
    ids: list[str] = []
    for reform_id, start, end in reversed(top_level_blocks(text)):
        if not reform_id.startswith("jxp_reform_"):
            continue
        ids.append(reform_id)
        block = normalize_common_fields(rewritten[start:end])
        potential = (
            "\tpotential = {\n"
            "\t\tOR = {\n"
            "\t\t\tjxp_is_japanese_polity_trigger = yes\n"
            f"\t\t\thas_reform = {reform_id}\n"
            "\t\t}\n"
            "\t}"
        )
        block = replace_object(block, "potential", potential)
        block = remove_objects(block, "trigger")
        potential_match = re.search(r"(?m)^\tpotential[ \t]*=[ \t]*\{", block)
        if potential_match is None:
            raise ValueError(f"rewritten {reform_id} is missing potential")
        opening = block.find("{", potential_match.start(), potential_match.end())
        closing = matching_brace(block, opening)
        block = (
            block[: closing + 1]
            + "\n"
            + route_trigger(route_key(reform_id))
            + block[closing + 1 :]
        )
        rewritten = rewritten[:start] + block + rewritten[end:]
    path.write_text(rewritten, encoding="utf-8", newline="")
    return tuple(reversed(ids))


def rewrite_founder_file(path: Path) -> tuple[tuple[str, str | None], ...]:
    text = path.read_text(encoding="utf-8-sig")
    rewritten = text
    mappings: list[tuple[str, str | None]] = []
    for reform_id, start, end in reversed(top_level_blocks(text)):
        if not reform_id.startswith("jxp_reform_founder_"):
            continue
        block = normalize_common_fields(rewritten[start:end])
        potential_match = re.search(r"(?m)^\tpotential[ \t]*=[ \t]*\{", block)
        if potential_match is None:
            raise ValueError(f"{reform_id} is missing potential")
        opening = block.find("{", potential_match.start(), potential_match.end())
        closing = matching_brace(block, opening)
        current_potential = block[potential_match.start() : closing + 1]
        if re.search(rf"\bhas_reform\s*=\s*{re.escape(reform_id)}\b", current_potential) is None:
            inner = block[opening + 1 : closing].strip("\r\n")
            nested = "\n".join(
                ("\t" + line if line.strip() else line) for line in inner.splitlines()
            )
            potential = (
                "\tpotential = {\n"
                "\t\tOR = {\n"
                f"\t\t\thas_reform = {reform_id}\n"
                "\t\t\tAND = {\n"
                f"{nested}\n"
                "\t\t\t}\n"
                "\t\t}\n"
                "\t}"
            )
            block = replace_object(block, "potential", potential)
        origin_match = re.search(r"has_country_flag\s*=\s*(jxp_origin_[A-Za-z0-9_]+)", block)
        mappings.append((reform_id, origin_match.group(1) if origin_match else None))
        rewritten = rewritten[:start] + block + rewritten[end:]
    path.write_text(rewritten, encoding="utf-8", newline="")
    return tuple(reversed(mappings))


def legacy_route_ids(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8-sig")
    return tuple(
        reform_id
        for reform_id, _, _ in top_level_blocks(text)
        if reform_id.startswith("jxp_reform_")
    )


def write_effect_file(
    path: Path,
    legacy_ids: tuple[str, ...],
    founder_mappings: tuple[tuple[str, str | None], ...],
) -> None:
    generic = [reform_id for reform_id, origin in founder_mappings if origin is None]
    if len(generic) != 1:
        raise ValueError(f"expected one generic founder reform, found {len(generic)}")

    lines = ["jxp_remove_legacy_autogranted_route_reforms_effect = {"]
    for reform_id in legacy_ids:
        lines.append(
            "\tif = { limit = { has_reform = "
            f"{reform_id} }} remove_government_reform = {reform_id} }}"
        )
    lines.extend(["}", "", "jxp_unlock_founder_house_reform_effect = {"])
    lines.append("\tif = {")
    lines.append("\t\tlimit = { jxp_is_unified_japan_state_trigger = yes }")
    lines.append("\t\tset_country_flag = jxp_founder_reform_unlocked_v0234")
    lines.append("\t\tregenerate_government_mechanics = yes")
    lines.extend(["\t}", "}", "", "jxp_migrate_visible_government_reforms_v0232_effect = {"])
    lines.append("\tjxp_remove_legacy_autogranted_route_reforms_effect = yes")
    lines.append("\tif = {")
    lines.append("\t\tlimit = { jxp_is_unified_japan_state_trigger = yes }")
    lines.append("\t\tjxp_unlock_founder_house_reform_effect = yes")
    lines.append("\t}")
    lines.append("\tregenerate_government_mechanics = yes")
    lines.append("\tset_country_flag = jxp_reform_visibility_migration_v0232")
    lines.extend(
        [
            "}",
            "",
            "jxp_reclassify_founder_house_reforms_v0234_effect = {",
            "\tif = {",
            "\t\tlimit = { jxp_is_unified_japan_state_trigger = yes }",
            "\t\tif = {",
            "\t\t\tlimit = { jxp_has_any_founder_house_reform_trigger = yes }",
            "\t\t\tjxp_clear_founder_house_reforms_effect = yes",
            "\t\t\tadd_government_reform = quash_noble_power_reform",
            "\t\t\tchange_government_reform_progress = 100",
            "\t\t}",
            "\t\tclr_country_flag = jxp_founder_reform_assigned_v0232",
            "\t\tjxp_unlock_founder_house_reform_effect = yes",
            "\t}",
            "\tset_country_flag = jxp_founder_reform_reclassified_v0234",
            "}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="")


def main() -> int:
    mod_root = Path(__file__).resolve().parents[2]
    reform_root = mod_root / "common" / "government_reforms"
    route_ids = rewrite_route_file(reform_root / "jxp_18_route_reforms_extra.txt")
    founder_mappings = rewrite_founder_file(reform_root / "jxp_28_founder_house_reforms.txt")
    legacy_ids = legacy_route_ids(reform_root / "jxp_14_route_reforms.txt")
    effect_path = (
        mod_root
        / "common"
        / "scripted_effects"
        / "jxp_54_government_reform_visibility_effects.txt"
    )
    write_effect_file(effect_path, legacy_ids, founder_mappings)
    print(
        f"Rewrote {len(route_ids)} visible route reforms, "
        f"{len(founder_mappings)} founder reforms, and {len(legacy_ids)} legacy removals."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
