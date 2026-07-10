#!/usr/bin/env python3
"""UI guardrails for the local japan_expanded_v2 EU4 mod.

This checker focuses on bugs that normal syntax validation will not catch:
mission slots hidden beyond the EU4 UI, non-forward mission arrows, national
idea groups with more than seven ideas, dense debug decision states, and custom
route reform layers appended after the vanilla government tiers.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


CORE_ROUTE_LEVELS = {
    "jxp_route_institution_foundations",
    "jxp_route_institution_administration",
    "jxp_route_institution_command",
}

PARKED_ROUTE_LEVELS = {
    "jxp_route_institution_society",
    "jxp_route_institution_arms",
    "jxp_route_institution_horizon",
    "jxp_route_institution_state_doctrine",
    "jxp_route_institution_capstone",
    "jxp_route_institution_special_bureaus",
    "jxp_route_institution_secretariats",
    "jxp_route_institution_grand_design",
    "jxp_route_institution_branch_programs",
    "jxp_route_institution_privy_councils",
    "jxp_route_institution_sovereign_projects",
    "jxp_route_institution_high_offices",
}

DEBUG_EVENT_CATEGORIES = {
    "jxp_debug_event_category_early",
    "jxp_debug_event_category_kirishitan",
    "jxp_debug_event_category_confucian",
    "jxp_debug_event_category_reformed_kaikyo",
    "jxp_debug_event_category_popular_maritime",
}

DEBUG_CORE_PANELS = {
    "cleanup": "jxp_debug_panel_cleanup",
    "values": "jxp_debug_panel_values",
    "routes": "jxp_debug_panel_routes",
    "seeds": "jxp_debug_panel_seeds",
}

DEBUG_PANEL_KEY_PATTERNS = (
    (re.compile(r"jxp_debug_(?:open_route_chooser|force_[A-Za-z0-9_]+_route)$"), "routes"),
    (re.compile(r"jxp_debug_seed_[A-Za-z0-9_]+$"), "seeds"),
    (re.compile(r"jxp_debug_values_[A-Za-z0-9_]+$"), "values"),
    (re.compile(r"jxp_debug_(?:clear_cooldowns|clear_event_state|return_jap_baseline)$"), "cleanup"),
)

MAX_DEBUG_CORE_VISIBLE = 12
MAX_DEBUG_PANEL_VISIBLE = 14
MAX_DEBUG_EVENT_CATEGORY_VISIBLE = 24
MAX_FIRE_DECISIONS_PER_EVENT_CATEGORY = 16
MAX_VISIBLE_DEBUG_EFFECT_OPS = 6


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def line_no(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def extract_braced(text: str, open_brace_idx: int) -> tuple[int, str]:
    depth = 0
    for idx in range(open_brace_idx, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return idx + 1, text[open_brace_idx : idx + 1]
    return len(text), text[open_brace_idx:]


def child_block(block: str, key: str) -> str:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\{{", block)
    if not match:
        return ""
    open_idx = block.find("{", match.start())
    _, child = extract_braced(block, open_idx)
    return child


def has_positive_flag(block: str, flag: str) -> bool:
    without_negative_checks = re.sub(
        rf"NOT\s*=\s*\{{\s*has_country_flag\s*=\s*{re.escape(flag)}\s*\}}",
        "",
        block,
    )
    return f"has_country_flag = {flag}" in without_negative_checks


def top_level_blocks(text: str, name_re: str) -> list[tuple[str, int, str]]:
    blocks: list[tuple[str, int, str]] = []
    pattern = re.compile(rf"(?m)^({name_re})\s*=\s*\{{")
    for match in pattern.finditer(text):
        open_idx = text.find("{", match.start())
        _, block = extract_braced(text, open_idx)
        blocks.append((match.group(1), line_no(text, match.start()), block))
    return blocks


def indented_blocks(text: str, name_re: str, parent_start_line: int) -> list[tuple[str, int, str]]:
    blocks: list[tuple[str, int, str]] = []
    pattern = re.compile(rf"(?m)^[ \t]+({name_re})\s*=\s*\{{")
    for match in pattern.finditer(text):
        open_idx = text.find("{", match.start())
        _, block = extract_braced(text, open_idx)
        blocks.append((match.group(1), parent_start_line + line_no(text, match.start()) - 1, block))
    return blocks


def direct_child_block_keys(block: str) -> list[str]:
    keys: list[str] = []
    depth = 0
    for line in block.splitlines():
        stripped = line.strip()
        if depth == 1:
            match = re.match(r"([A-Za-z0-9_]+)\s*=\s*\{", stripped)
            if match:
                keys.append(match.group(1))
        depth += line.count("{") - line.count("}")
    return keys


def direct_child_assignment_keys(block: str) -> list[str]:
    keys: list[str] = []
    depth = 0
    for line in block.splitlines():
        stripped = line.strip()
        if depth == 1:
            match = re.match(r"([A-Za-z0-9_]+)\s*=", stripped)
            if match:
                keys.append(match.group(1))
        depth += line.count("{") - line.count("}")
    return keys


def direct_visible_effect_ops(effect_block: str) -> list[str]:
    ignored = {"custom_tooltip", "hidden_effect", "ai_chance"}
    return [key for key in direct_child_assignment_keys(effect_block) if key not in ignored]


def count_reforms(level_block: str) -> int:
    reforms_block_match = re.search(r"reforms\s*=\s*\{", level_block)
    if not reforms_block_match:
        return 0
    open_idx = level_block.find("{", reforms_block_match.start())
    _, reforms_block = extract_braced(level_block, open_idx)
    return len(re.findall(r"\bjxp_reform_[A-Za-z0-9_]+\b", reforms_block))


def mission_guardrails(mod: Path) -> tuple[list[str], list[str]]:
    rows = ["Mission UI guardrails:"]
    issues: list[str] = []
    missions: dict[str, dict[str, object]] = {}
    mission_defs: dict[str, list[str]] = {}

    for path in sorted((mod / "missions").glob("*.txt")):
        text = read_text(path)
        for group, group_line, group_block in top_level_blocks(text, r"jxp_[A-Za-z0-9_]+"):
            slot_match = re.search(r"(?m)^\s*slot\s*=\s*(\d+)\b", group_block)
            if not slot_match:
                continue
            slot = int(slot_match.group(1))
            if slot > 5:
                issues.append(f"{path.name}:{group_line}: {group} uses hidden mission slot {slot}")
            for key, mission_line, mission_block in indented_blocks(
                group_block, r"jxp_mission_[A-Za-z0-9_]+", group_line
            ):
                pos_match = re.search(r"(?m)^\s*position\s*=\s*(\d+)\b", mission_block)
                if not pos_match:
                    continue
                required_match = re.search(r"required_missions\s*=\s*\{([^{}]*)\}", mission_block, re.S)
                required = required_match.group(1).split() if required_match else []
                mission_defs.setdefault(key, []).append(f"{path.name}:{mission_line}")
                missions[key] = {
                    "file": path.name,
                    "line": mission_line,
                    "group": group,
                    "slot": slot,
                    "position": int(pos_match.group(1)),
                    "required": required,
                }

    for key, locations in sorted(mission_defs.items()):
        if len(locations) > 1:
            issues.append(f"{key} is defined multiple times: {', '.join(locations)}")

    cross_edges = 0
    for key, data in missions.items():
        child_slot = int(data["slot"])
        child_pos = int(data["position"])
        for parent_key in data["required"]:  # type: ignore[index]
            parent = missions.get(parent_key)
            if not parent:
                continue
            parent_slot = int(parent["slot"])
            parent_pos = int(parent["position"])
            if parent_slot != child_slot:
                cross_edges += 1
            if child_pos <= parent_pos:
                issues.append(
                    f"{data['file']}:{data['line']}: {key} slot {child_slot} pos {child_pos} "
                    f"requires {parent_key} slot {parent_slot} pos {parent_pos}; "
                    "required_missions arrows must point to a strictly larger row"
                )

    rows.append(f"missions={len(missions)} cross_slot_edges={cross_edges}")
    return rows, issues


def idea_guardrails(mod: Path) -> tuple[list[str], list[str]]:
    rows = ["Idea UI guardrails:"]
    issues: list[str] = []
    count = 0
    idea_defs: dict[str, list[str]] = {}
    for path in sorted((mod / "common" / "ideas").glob("*.txt")):
        text = read_text(path)
        for key, start_line, block in top_level_blocks(text, r"[A-Za-z0-9_]+_ideas"):
            block_keys = direct_child_block_keys(block)
            assignment_keys = direct_child_assignment_keys(block)
            idea_keys = [item for item in block_keys if item not in {"start", "bonus", "trigger", "ai_will_do"}]
            count += 1
            idea_defs.setdefault(key, []).append(f"{path.name}:{start_line}")
            if len(idea_keys) != 7:
                issues.append(f"{path.name}:{start_line}: {key} has {len(idea_keys)} ideas, expected 7")
            for required in ("start", "bonus", "trigger"):
                if required not in block_keys:
                    issues.append(f"{path.name}:{start_line}: {key} is missing top-level {required} block")
            if "free" not in assignment_keys:
                issues.append(f"{path.name}:{start_line}: {key} is missing top-level free = yes")
            elif not re.search(r"(?m)^[ \t]+free\s*=\s*yes\b", block):
                issues.append(f"{path.name}:{start_line}: {key} has free assignment but not free = yes")
    for key, locations in sorted(idea_defs.items()):
        if len(locations) > 1:
            issues.append(f"{key} is defined multiple times in the mod: {', '.join(locations)}")
    rows.append(f"idea_groups={count}")
    return rows, issues


def debug_guardrails(mod: Path) -> tuple[list[str], list[str]]:
    rows = ["Debug decision UI guardrails:"]
    issues: list[str] = []
    path = mod / "decisions" / "jxp_debug_decisions.txt"
    text = read_text(path)
    fire_count = 0
    gated_count = 0
    fire_event_ids: set[str] = set()
    fire_by_category = {flag: 0 for flag in DEBUG_EVENT_CATEGORIES}
    for key, start_line, block in indented_blocks(text, r"jxp_debug_fire_[A-Za-z0-9_]+", 1):
        fire_count += 1
        has_panel = has_positive_flag(block, "jxp_debug_events_enabled")
        categories = [flag for flag in DEBUG_EVENT_CATEGORIES if has_positive_flag(block, flag)]
        if has_panel and len(categories) == 1:
            gated_count += 1
            fire_by_category[categories[0]] += 1
        else:
            issues.append(f"{path.name}:{start_line}: {key} is not gated by event panel and category")
        if len(categories) > 1:
            issues.append(f"{path.name}:{start_line}: {key} is visible in multiple event categories: {categories}")
        effect = child_block(block, "effect")
        event_match = re.search(
            r"\bcountry_event\s*=\s*\{\s*id\s*=\s*([A-Za-z0-9_.-]+)", effect
        )
        if event_match:
            fire_event_ids.add(event_match.group(1))
        else:
            issues.append(f"{path.name}:{start_line}: {key} does not dispatch a concrete country event id")
        visible_ops = direct_visible_effect_ops(effect)
        if len(visible_ops) > MAX_VISIBLE_DEBUG_EFFECT_OPS and "hidden_effect" not in effect:
            issues.append(
                f"{path.name}:{start_line}: {key} exposes {len(visible_ops)} effect lines in tooltip; "
                "wrap debug internals in hidden_effect"
            )

    root_only_visible = 0
    persistent_core_visible = 0
    event_panel_controls = 0
    panel_visible = {name: 0 for name in DEBUG_CORE_PANELS}
    tooltip_hidden_count = 0
    for key, start_line, block in indented_blocks(text, r"jxp_debug_[A-Za-z0-9_]+", 1):
        if key.startswith("jxp_debug_fire_"):
            continue
        potential = child_block(block, "potential")
        if not has_positive_flag(potential, "jxp_debug_enabled"):
            continue
        effect = child_block(block, "effect")
        visible_ops = direct_visible_effect_ops(effect)
        if "hidden_effect" in effect:
            tooltip_hidden_count += 1
        elif len(visible_ops) > MAX_VISIBLE_DEBUG_EFFECT_OPS:
            issues.append(
                f"{path.name}:{start_line}: {key} exposes {len(visible_ops)} effect lines in tooltip; "
                "wrap debug internals in hidden_effect"
            )
        has_event_panel = has_positive_flag(potential, "jxp_debug_events_enabled")
        event_categories = [flag for flag in DEBUG_EVENT_CATEGORIES if has_positive_flag(potential, flag)]
        has_any_event_category = bool(event_categories)
        panel_hits = [
            name for name, flag in DEBUG_CORE_PANELS.items() if has_positive_flag(potential, flag)
        ]
        expected_panel = next(
            (panel_name for pattern, panel_name in DEBUG_PANEL_KEY_PATTERNS if pattern.fullmatch(key)),
            None,
        )
        if expected_panel and panel_hits != [expected_panel]:
            issues.append(
                f"{path.name}:{start_line}: {key} belongs in the {expected_panel} panel, "
                f"found panel gates {panel_hits or ['none']}"
            )
        if has_any_event_category and key != "jxp_debug_events_hide_categories":
            issues.append(f"{path.name}:{start_line}: {key} should not be gated by an event category")
        if len(panel_hits) > 1:
            if key == "jxp_debug_hide_core_panels":
                for panel_name in panel_hits:
                    panel_visible[panel_name] += 1
            else:
                issues.append(f"{path.name}:{start_line}: {key} is visible in multiple debug core panels: {panel_hits}")
        elif panel_hits:
            panel_visible[panel_hits[0]] += 1
        elif has_event_panel:
            event_panel_controls += 1
        else:
            if key == "jxp_debug_disable_menu":
                persistent_core_visible += 1
            elif re.search(r"\bjxp_debug_root_menu_trigger\s*=\s*yes\b", potential):
                root_only_visible += 1
            else:
                issues.append(
                    f"{path.name}:{start_line}: {key} is a root debug decision but does not use "
                    "jxp_debug_root_menu_trigger = yes"
                )

    rows.append(f"fire_decisions={fire_count} gated={gated_count}")
    for flag, count in sorted(fire_by_category.items()):
        short = flag.replace("jxp_debug_event_category_", "")
        rows.append(f"event_category_{short}_fire_decisions={count}")
        if count > MAX_FIRE_DECISIONS_PER_EVENT_CATEGORY:
            issues.append(
                f"{path.name}: event category {short} exposes {count} fire decisions, "
                f"expected <= {MAX_FIRE_DECISIONS_PER_EVENT_CATEGORY}"
            )
    core_visible = persistent_core_visible + root_only_visible
    rows.append(f"debug_root_only_visible={root_only_visible}")
    rows.append(f"debug_persistent_core_visible={persistent_core_visible}")
    rows.append(f"debug_root_visible_total={core_visible}")
    if core_visible > MAX_DEBUG_CORE_VISIBLE:
        issues.append(
            f"{path.name}: debug core exposes {core_visible} decisions, expected <= {MAX_DEBUG_CORE_VISIBLE}"
        )
    rows.append(f"debug_event_panel_controls={event_panel_controls}")
    rows.append(f"debug_tooltip_hidden_decisions={tooltip_hidden_count}")
    for flag, count in sorted(fire_by_category.items()):
        short = flag.replace("jxp_debug_event_category_", "")
        category_total = persistent_core_visible + event_panel_controls + count
        rows.append(f"debug_event_category_{short}_visible_total={category_total}")
        if category_total > MAX_DEBUG_EVENT_CATEGORY_VISIBLE:
            issues.append(
                f"{path.name}: event category {short} exposes {category_total} decisions with controls, "
                f"expected <= {MAX_DEBUG_EVENT_CATEGORY_VISIBLE}"
            )
    for name, count in sorted(panel_visible.items()):
        panel_total = persistent_core_visible + count
        rows.append(f"debug_panel_{name}_visible_total={panel_total}")
        if panel_total > MAX_DEBUG_PANEL_VISIBLE:
            issues.append(
                f"{path.name}: debug panel {name} exposes {panel_total} decisions, "
                f"expected <= {MAX_DEBUG_PANEL_VISIBLE}"
            )

    debug_effect_count = 0
    debug_effect_hidden_count = 0
    for effects_path in sorted((mod / "common" / "scripted_effects").glob("*.txt")):
        effects_text = read_text(effects_path)
        for effect_key, effect_line, effect_block in top_level_blocks(effects_text, r"jxp_debug_[A-Za-z0-9_]+_effect"):
            debug_effect_count += 1
            visible_ops = direct_visible_effect_ops(effect_block)
            has_hidden = "hidden_effect" in effect_block
            if has_hidden:
                debug_effect_hidden_count += 1
            if len(visible_ops) > MAX_VISIBLE_DEBUG_EFFECT_OPS and not has_hidden:
                issues.append(
                    f"{effects_path.name}:{effect_line}: {effect_key} exposes {len(visible_ops)} effect lines; "
                    "large debug scripted effects should use custom_tooltip plus hidden_effect"
                )
    rows.append(f"debug_scripted_effects={debug_effect_count}")
    rows.append(f"debug_scripted_effects_with_hidden_effect={debug_effect_hidden_count}")

    event_blocks: dict[str, tuple[str, int, str]] = {}
    for events_path in sorted((mod / "events").glob("*.txt")):
        events_text = read_text(events_path)
        for _, event_line, event_block in top_level_blocks(
            events_text, r"(?:country|province)_event"
        ):
            event_id_match = re.search(
                r"(?m)^\s*id\s*=\s*([A-Za-z0-9_.-]+)\b", event_block
            )
            if event_id_match:
                event_blocks[event_id_match.group(1)] = (events_path.name, event_line, event_block)

    preview_modifiers: set[str] = set()
    for event_id in sorted(fire_event_ids):
        event_data = event_blocks.get(event_id)
        if not event_data:
            issues.append(f"{path.name}: debug event decision references missing event {event_id}")
            continue
        preview_modifiers.update(
            modifier
            for modifier in re.findall(
                r"add_country_modifier\s*=\s*\{\s*name\s*=\s*([A-Za-z0-9_.-]+)",
                event_data[2],
            )
            if not modifier.startswith("jxp_route_")
        )

    debug_effects_path = mod / "common" / "scripted_effects" / "jxp_debug_effects.txt"
    debug_effects_text = read_text(debug_effects_path)
    preview_cleanup_block = ""
    prepare_block = ""
    for effect_key, _, effect_block in top_level_blocks(
        debug_effects_text, r"jxp_debug_[A-Za-z0-9_]+_effect"
    ):
        if effect_key == "jxp_debug_clear_preview_modifiers_effect":
            preview_cleanup_block = effect_block
        elif effect_key == "jxp_debug_prepare_polity_effect":
            prepare_block = effect_block
    removed_preview_modifiers = set(
        re.findall(r"remove_country_modifier\s*=\s*([A-Za-z0-9_.-]+)", preview_cleanup_block)
    )
    missing_preview_cleanup = sorted(preview_modifiers - removed_preview_modifiers)
    if missing_preview_cleanup:
        issues.append(
            f"{debug_effects_path.name}: debug event previews add modifiers missing from "
            f"jxp_debug_clear_preview_modifiers_effect: {', '.join(missing_preview_cleanup)}"
        )
    if not re.search(r"\bjxp_debug_clear_preview_modifiers_effect\s*=\s*yes\b", prepare_block):
        issues.append(
            f"{debug_effects_path.name}: jxp_debug_prepare_polity_effect must clear the previous "
            "event preview modifiers"
        )
    rows.append(
        f"debug_preview_modifiers={len(preview_modifiers)} "
        f"cleanup_covered={len(preview_modifiers & removed_preview_modifiers)}"
    )
    return rows, issues


def government_guardrails(mod: Path) -> tuple[list[str], list[str]]:
    rows = ["Government reform UI guardrails:"]
    issues: list[str] = []
    text = "\n".join(read_text(path) for path in sorted((mod / "common" / "governments").glob("*.txt")))
    visible_levels = []
    for key, start_line, block in indented_blocks(text, r"jxp_route_institution_[A-Za-z0-9_]+", 1):
        reforms = count_reforms(block)
        rows.append(f"{key} reforms={reforms}")
        visible_levels.append(key)
        issues.append(
            f"{key}:{start_line}: custom route reform level remains registered; "
            "place player-facing reforms inside vanilla monarchy levels 1-11"
        )
    rows.append(f"visible_route_levels={len(visible_levels)}")

    return rows, issues


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: check_jxp_ui_guardrails.py <mod_path>", file=sys.stderr)
        return 2
    mod = Path(argv[1])
    if not mod.is_dir():
        print(f"Mod path does not exist: {mod}", file=sys.stderr)
        return 2

    rows: list[str] = []
    issues: list[str] = []
    for checker in (mission_guardrails, idea_guardrails, debug_guardrails, government_guardrails):
        checker_rows, checker_issues = checker(mod)
        rows.extend(checker_rows)
        rows.append("")
        issues.extend(checker_issues)

    print("\n".join(rows).rstrip())
    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("\nOK: JXP UI guardrails passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
