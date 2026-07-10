#!/usr/bin/env python3
"""Generate balanced province histories and continuous ownership audits."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
PLAN_PATH = SCRIPT_DIR / "province_plan.json"
HISTORY_PLAN_PATH = SCRIPT_DIR / "history_plan.json"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("jxp_build_map", SCRIPT_DIR / "build_map.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    return parser.parse_args()


def date_tuple(value: str) -> tuple[int, int, int]:
    year, month, day = (int(part) for part in value.split("."))
    return year, month, day


def province_history_file(directory: Path, pid: int) -> Path:
    matches = sorted(directory.glob(f"{pid} - *.txt"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one vanilla history file for {pid}, found {matches}")
    return matches[0]


def root_value(text: str, key: str, default: str | None = None) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\"?([^\s\"#}}]+)\"?", text)
    if match:
        return match.group(1)
    if default is not None:
        return default
    raise RuntimeError(f"Missing root province-history key: {key}")


def root_values(text: str, key: str) -> list[str]:
    return re.findall(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\s#}}]+)", text)


def root_int(text: str, key: str) -> int:
    return int(root_value(text, key))


def replace_root_int(text: str, key: str, value: int) -> str:
    updated, count = re.subn(rf"(?m)^(\s*{re.escape(key)}\s*=\s*)\d+", rf"\g<1>{value}", text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not replace {key} in an existing province history")
    return updated


def allocate_attribute(
    pids: list[int],
    weights: dict[int, float],
    target: int,
    floors: dict[int, int],
) -> dict[int, int]:
    allocation = {pid: max(1, int(floors.get(pid, 1))) for pid in pids}
    remaining = target - sum(allocation.values())
    if remaining < 0:
        raise RuntimeError(f"Development floors exceed target {target}: {sum(allocation.values())}")
    positive_total = sum(max(weights.get(pid, 0.0), 0.000001) for pid in pids)
    quotas = {
        pid: remaining * max(weights.get(pid, 0.0), 0.000001) / positive_total
        for pid in pids
    }
    for pid in pids:
        addition = int(math.floor(quotas[pid]))
        allocation[pid] += addition
        remaining -= addition
    for pid in sorted(pids, key=lambda item: (quotas[item] - math.floor(quotas[item]), weights.get(item, 0.0), -item), reverse=True):
        if remaining <= 0:
            break
        allocation[pid] += 1
        remaining -= 1
    if sum(allocation.values()) != target:
        raise RuntimeError("Largest-remainder allocation did not close")
    return allocation


def complete_development_floors(
    pids: list[int],
    weights: dict[str, dict[int, float]],
    targets: dict[str, int],
    history_plan: dict,
) -> dict[str, dict[int, int]]:
    attributes = tuple(targets)
    floors = {
        pid: {attribute: 1 for attribute in attributes}
        for pid in pids
    }
    for pid_text, values in history_plan.get("development_floors", {}).items():
        pid = int(pid_text)
        if pid not in floors:
            raise RuntimeError(f"Development floor references unknown province {pid}")
        for attribute, value in values.items():
            if attribute not in targets:
                raise RuntimeError(f"Unknown development attribute in floor: {attribute}")
            floors[pid][attribute] = max(1, int(value))

    default_total = int(history_plan.get("minimum_total_development", 3))
    total_overrides = {
        int(pid): int(value)
        for pid, value in history_plan.get("minimum_total_development_overrides", {}).items()
    }
    while True:
        pending = [
            pid for pid in pids
            if sum(floors[pid].values()) < total_overrides.get(pid, default_total)
        ]
        if not pending:
            break
        global_floor = {
            attribute: sum(floors[pid][attribute] for pid in pids)
            for attribute in attributes
        }
        progressed = False
        for pid in sorted(
            pending,
            key=lambda item: (sum(weights[attribute].get(item, 0.0) for attribute in attributes), -item),
            reverse=True,
        ):
            required_total = total_overrides.get(pid, default_total)
            if sum(floors[pid].values()) >= required_total:
                continue
            local_total = sum(weights[attribute].get(pid, 0.0) for attribute in attributes) or 1.0
            candidates = []
            for attribute in attributes:
                slack = targets[attribute] - global_floor[attribute]
                if slack <= 0:
                    continue
                local_share = weights[attribute].get(pid, 0.0) / local_total
                score = (
                    local_share
                    * (slack / targets[attribute])
                    / (floors[pid][attribute] ** 1.5)
                )
                candidates.append((score, slack, attribute))
            if not candidates:
                raise RuntimeError(
                    f"Development targets cannot satisfy the total floor for province {pid}"
                )
            attribute = max(candidates)[2]
            floors[pid][attribute] += 1
            global_floor[attribute] += 1
            progressed = True
        if not progressed:
            raise RuntimeError("Development-floor completion stalled")

    per_attribute = {
        attribute: {pid: floors[pid][attribute] for pid in pids}
        for attribute in attributes
    }
    for attribute in attributes:
        floor_sum = sum(per_attribute[attribute].values())
        if floor_sum > targets[attribute]:
            raise RuntimeError(
                f"{attribute} floors exceed target {targets[attribute]}: {floor_sum}"
            )
    return per_attribute


def build_development(game_root: Path, plan: dict, history_plan: dict, builder):
    vanilla_history_dir = game_root / "history" / "provinces"
    old_dev = {}
    for pid in plan["existing_japan_ids"]:
        text = province_history_file(vanilla_history_dir, int(pid)).read_text(encoding="cp1252")
        old_dev[int(pid)] = {
            "base_tax": root_int(text, "base_tax"),
            "base_production": root_int(text, "base_production"),
            "base_manpower": root_int(text, "base_manpower"),
        }
    vanilla_rows, vanilla_colors = builder.parse_definition(game_root / "map" / "definition.csv")
    mod_rows, mod_colors = builder.parse_definition(MOD_ROOT / "map" / "definition.csv")
    vanilla_ids = builder.id_array(Image.open(game_root / "map" / "provinces.bmp"), vanilla_colors)
    final_ids = builder.id_array(Image.open(MOD_ROOT / "map" / "provinces.bmp"), mod_colors)
    pids = sorted(set(plan["existing_japan_ids"]) | {item["id"] for item in plan["new_provinces"]})
    weights = {attribute: defaultdict(float) for attribute in plan["target_development"]}
    for old_pid in plan["existing_japan_ids"]:
        mask = vanilla_ids == int(old_pid)
        pixel_total = int(mask.sum())
        if pixel_total == 0:
            raise RuntimeError(f"Vanilla Japanese province {old_pid} has no pixels")
        overlaps = Counter(int(value) for value in final_ids[mask])
        for final_pid, pixels in overlaps.items():
            if final_pid not in pids:
                raise RuntimeError(f"Old province {old_pid} overlaps unexpected final ID {final_pid}")
            share = pixels / pixel_total
            for attribute in weights:
                weights[attribute][final_pid] += old_dev[int(old_pid)][attribute] * share
    targets = {attribute: int(value) for attribute, value in plan["target_development"].items()}
    floors_by_attribute = complete_development_floors(
        pids, weights, targets, history_plan
    )
    allocation = {}
    for attribute, target in targets.items():
        per_pid = allocate_attribute(
            pids, weights[attribute], target, floors_by_attribute[attribute]
        )
        for pid, value in per_pid.items():
            allocation.setdefault(pid, {})[attribute] = value
    total_distribution = Counter(sum(values.values()) for values in allocation.values())
    diagnostics = {
        "totals": {attribute: sum(values[attribute] for values in allocation.values()) for attribute in weights},
        "weighted_inputs": {attribute: round(sum(weights[attribute].values()), 6) for attribute in weights},
        "vanilla_total": sum(sum(values.values()) for values in old_dev.values()),
        "uplift": sum(targets.values()) - sum(sum(values.values()) for values in old_dev.values()),
        "minimum_total_default": int(history_plan.get("minimum_total_development", 3)),
        "minimum_total_overrides": {
            str(pid): value
            for pid, value in sorted(
                (int(pid), int(value))
                for pid, value in history_plan.get("minimum_total_development_overrides", {}).items()
            )
        },
        "floor_components": {
            attribute: sum(floors_by_attribute[attribute].values())
            for attribute in weights
        },
        "total_distribution": {
            str(total): count for total, count in sorted(total_distribution.items())
        },
    }
    return allocation, diagnostics


def transition_blocks(timeline: dict, dated_effects: list[list[str]] | None = None) -> str:
    previous = timeline["root"]
    entries = []
    for date, owner in timeline.get("changes", []):
        entries.append((date_tuple(date), date, [
            f"owner = {owner}", f"controller = {owner}", f"add_core = {owner}", f"remove_core = {previous}",
        ]))
        previous = owner
    for date, effect in dated_effects or []:
        entries.append((date_tuple(date), date, [effect]))
    entries.sort(key=lambda item: item[0])
    return "\n".join(
        f"{date} = {{\n" + "\n".join(f"\t{effect}" for effect in effects) + "\n}"
        for _, date, effects in entries
    )


def scrub_ownership(text: str) -> str:
    return re.sub(r"\b(?:owner|controller)\s*=\s*[A-Z0-9_]+", "", text)


def generate_new_history(province: dict, timeline: dict, dev: dict, parent_text: str, history_plan: dict) -> str:
    pid = int(province["id"])
    culture = root_value(parent_text, "culture")
    religion = root_value(parent_text, "religion")
    trade_goods = history_plan.get("root_trade_goods", {}).get(str(pid), province["trade_goods"])
    discovered = root_values(parent_text, "discovered_by")
    lines = [
        f"#{pid} - {province['name']}", "", f"owner = {timeline['root']}", f"controller = {timeline['root']}",
        f"culture = {culture}", f"religion = {religion}", f"capital = \"{province['capital']}\"",
        f"trade_goods = {trade_goods}", "hre = no", f"base_tax = {dev['base_tax']}",
        f"base_manpower = {dev['base_manpower']}", f"base_production = {dev['base_production']}",
        "is_city = yes", f"add_core = {timeline['root']}",
    ]
    lines.extend(f"discovered_by = {group}" for group in discovered)
    lines.extend(["", "1542.1.1 = { discovered_by = POR }"])
    blocks = transition_blocks(timeline, history_plan.get("dated_effects", {}).get(str(pid)))
    if blocks:
        lines.extend(["", blocks])
    return "\n".join(lines).rstrip() + "\n"


def generate_existing_history(source_text: str, pid: int, dev: dict, history_plan: dict) -> str:
    text = source_text
    for attribute, value in dev.items():
        text = replace_root_int(text, attribute, value)
    timeline = history_plan["province_timelines"].get(str(pid))
    if timeline:
        text = scrub_ownership(text)
        owner_header = f"owner = {timeline['root']}\ncontroller = {timeline['root']}\nadd_core = {timeline['root']}\n"
        first_newline = text.find("\n")
        text = text[:first_newline + 1] + owner_header + text[first_newline + 1:]
        blocks = transition_blocks(timeline, history_plan.get("dated_effects", {}).get(str(pid)))
        if blocks:
            text = text.rstrip() + "\n\n# JXP 88-province continuous ownership overlay\n" + blocks + "\n"
    return text


def parse_generated_owner_history(text: str):
    root_match = re.search(r"(?m)^\s*owner\s*=\s*([A-Z0-9_]+)", text)
    if not root_match:
        raise RuntimeError("Generated province history has no root owner")
    changes = []
    for match in re.finditer(r"(?m)^(\d+\.\d+\.\d+)\s*=\s*\{", text):
        cursor = match.end() - 1
        depth = 0
        in_quote = False
        escaped = False
        end = None
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
                    end = cursor + 1
                    break
            cursor += 1
        if end is None:
            raise RuntimeError(f"Unclosed dated block {match.group(1)}")
        owners = re.findall(r"\bowner\s*=\s*([A-Z0-9_]+)", text[match.end():end])
        if owners:
            changes.append((date_tuple(match.group(1)), owners[-1]))
    return root_match.group(1), sorted(changes)


def owner_at(parsed, date: str):
    owner, changes = parsed
    target = date_tuple(date)
    for change_date, new_owner in changes:
        if change_date <= target:
            owner = new_owner
    return owner


def date_text(value: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in value)


def ownership_intervals(parsed, campaign_start: str, campaign_end: str):
    start = date_tuple(campaign_start)
    end = date_tuple(campaign_end)
    owner = owner_at(parsed, campaign_start)
    cursor = start
    intervals = []
    for changed, new_owner in parsed[1]:
        if changed <= start or changed >= end:
            continue
        if new_owner == owner:
            continue
        intervals.append((date_text(cursor), date_text(changed), owner))
        cursor = changed
        owner = new_owner
    intervals.append((date_text(cursor), date_text(end), owner))
    return intervals


def main() -> int:
    args = parse_args()
    game_root = args.game_root.resolve()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    history_plan = json.loads(HISTORY_PLAN_PATH.read_text(encoding="utf-8"))
    builder = load_builder_module()
    allocation, diagnostics = build_development(game_root, plan, history_plan, builder)
    expected_totals = {key: int(value) for key, value in plan["target_development"].items()}
    if diagnostics["totals"] != expected_totals:
        raise RuntimeError(f"Development total mismatch: {diagnostics['totals']} != {expected_totals}")

    vanilla_dir = game_root / "history" / "provinces"
    output_dir = MOD_ROOT / "history" / "provinces"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_files = {}
    for pid in plan["existing_japan_ids"]:
        source = province_history_file(vanilla_dir, int(pid))
        text = generate_existing_history(source.read_text(encoding="cp1252"), int(pid), allocation[int(pid)], history_plan)
        output = output_dir / source.name
        output.write_text(text, encoding="cp1252", newline="\n")
        output_files[int(pid)] = output

    for province in plan["new_provinces"]:
        pid = int(province["id"])
        parent_path = province_history_file(vanilla_dir, int(province["parent"]))
        parent_text = parent_path.read_text(encoding="cp1252")
        timeline = history_plan["province_timelines"][str(pid)]
        text = generate_new_history(province, timeline, allocation[pid], parent_text, history_plan)
        output = output_dir / f"{pid} - {province['name']}.txt"
        output.write_text(text, encoding="cp1252", newline="\n")
        output_files[pid] = output

    audit_dir = MOD_ROOT / "tools" / "jxp_map_validation" / "generated"
    audit_dir.mkdir(parents=True, exist_ok=True)
    with (audit_dir / "development_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["province_id", "base_tax", "base_production", "base_manpower", "total"])
        for pid in sorted(allocation):
            values = allocation[pid]
            writer.writerow([pid, values["base_tax"], values["base_production"], values["base_manpower"], sum(values.values())])
        writer.writerow(["TOTAL", diagnostics["totals"]["base_tax"], diagnostics["totals"]["base_production"], diagnostics["totals"]["base_manpower"], sum(diagnostics["totals"].values())])

    parsed = {pid: parse_generated_owner_history(path.read_text(encoding="cp1252")) for pid, path in output_files.items()}
    campaign_start = history_plan["campaign_start"]
    campaign_end = history_plan["campaign_end_exclusive"]
    new_ids = {int(province["id"]) for province in plan["new_provinces"]}
    planned_ids = {int(pid) for pid in history_plan["province_timelines"]}
    parents = {int(province["id"]): int(province["parent"]) for province in plan["new_provinces"]}
    interval_rows = []
    for pid in sorted(parsed):
        if pid in new_ids:
            source = "curated_split_timeline"
        elif pid in planned_ids:
            source = "curated_existing_override"
        else:
            source = "vanilla_1.37.5_inherited"
        for start, end, owner in ownership_intervals(
            parsed[pid], campaign_start, campaign_end
        ):
            interval_rows.append([
                pid,
                source,
                parents.get(pid, ""),
                start,
                end,
                owner,
            ])
    interval_path = audit_dir / "ownership_intervals.csv"
    with interval_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "province_id",
            "timeline_source",
            "vanilla_parent_id",
            "start_inclusive",
            "end_exclusive",
            "owner",
        ])
        writer.writerows(interval_rows)

    snapshots = {
        date: {str(pid): owner_at(parsed[pid], date) for pid in sorted(parsed)}
        for date in history_plan["bookmark_dates"]
    }
    owner_counts = {
        date: dict(sorted(Counter(snapshot.values()).items()))
        for date, snapshot in snapshots.items()
    }
    history_manifest = {
        "schema_version": 2,
        "development": diagnostics,
        "campaign_start": campaign_start,
        "campaign_end_exclusive": campaign_end,
        "bookmarks": history_plan["bookmark_dates"],
        "ownership_snapshots": snapshots,
        "owner_counts": owner_counts,
        "ownership_interval_count": len(interval_rows),
        "ownership_interval_file": str(interval_path.relative_to(MOD_ROOT)).replace("\\", "/"),
        "province_files": {str(pid): path.name for pid, path in sorted(output_files.items())},
    }
    (audit_dir / "history_manifest.json").write_text(json.dumps(history_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated {len(output_files)} province histories")
    print(f"Development totals: {diagnostics['totals']} (total {sum(diagnostics['totals'].values())})")
    print(f"Ownership audit: {len(interval_rows)} continuous intervals across {len(snapshots)} bookmarks")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
