#!/usr/bin/env python3
"""Static release gate for the JXP 88-province companion map."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
PLAN_PATH = MOD_ROOT / "tools" / "jxp_map_builder" / "province_plan.json"
MANIFEST_PATH = MOD_ROOT / "tools" / "jxp_map_builder" / "generated_manifest.json"


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, message: str):
        self.errors.append(message)

    def warn(self, message: str):
        self.warnings.append(message)

    def note(self, message: str):
        self.notes.append(message)

    def emit(self) -> int:
        for message in self.notes:
            print(f"NOTE: {message}")
        for message in self.warnings:
            print(f"WARNING: {message}")
        for message in self.errors:
            print(f"ERROR: {message}")
        print(f"SUMMARY: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--strict-history", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_definition(path: Path, report: Report):
    ids = {}
    colors = {}
    color_ids = defaultdict(list)
    rows = []
    with path.open("r", encoding="cp1252", newline="") as handle:
        for line_number, row in enumerate(csv.reader(handle, delimiter=";"), 1):
            if not row or not row[0].strip().isdigit():
                continue
            try:
                pid = int(row[0])
                rgb = tuple(int(value) for value in row[1:4])
            except (ValueError, IndexError):
                report.error(f"definition.csv:{line_number} is malformed")
                continue
            if pid in ids:
                report.error(f"definition.csv duplicates province ID {pid}")
            ids[pid] = rgb
            colors[rgb] = pid
            color_ids[rgb].append(pid)
            rows.append(row)
    duplicates = {rgb: pids for rgb, pids in color_ids.items() if len(pids) > 1}
    return ids, colors, rows, duplicates


def image_ids(image: Image.Image, rgb_to_id: dict, report: Report):
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint32)
    packed = (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]
    lookup = np.full(1 << 24, -1, dtype=np.int32)
    for color, pid in rgb_to_id.items():
        lookup[(color[0] << 16) | (color[1] << 8) | color[2]] = pid
    ids = lookup[packed]
    unknown = ids < 0
    if np.any(unknown):
        unknown_colors = np.unique(packed[unknown])
        preview = [((int(value) >> 16) & 255, (int(value) >> 8) & 255, int(value) & 255) for value in unknown_colors[:10]]
        report.error(f"provinces.bmp has {len(unknown_colors)} undefined RGB colors, first: {preview}")
    return ids


def extract_top_block(text: str, key: str) -> str | None:
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


def component_sizes(mask: np.ndarray) -> list[int]:
    visited = np.zeros(mask.shape, dtype=bool)
    sizes = []
    for y, x in zip(*np.where(mask)):
        if visited[y, x]:
            continue
        queue = deque([(int(y), int(x))])
        visited[y, x] = True
        size = 0
        while queue:
            cy, cx = queue.popleft()
            size += 1
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def parse_sea_ids(default_text: str, report: Report) -> set[int]:
    match = re.search(r"sea_starts\s*=\s*\{([^}]*)\}", default_text, flags=re.S)
    if not match:
        report.error("default.map is missing sea_starts")
        return set()
    return {int(token) for token in re.findall(r"\b\d+\b", match.group(1))}


def parse_positions(text: str):
    positions = {}
    for match in re.finditer(r"(?m)^\s*(\d+)\s*=\s*\{", text):
        pid = int(match.group(1))
        block = extract_top_block(text[match.start():], str(pid))
        if not block:
            continue
        position_match = re.search(r"position\s*=\s*\{([^}]*)\}", block, flags=re.S)
        if position_match:
            numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", position_match.group(1))]
            positions[pid] = list(zip(numbers[0::2], numbers[1::2]))
    return positions


def near_province(ids: np.ndarray, pid: int, x: int, y: int, radius: int = 2) -> bool:
    return np.any(ids[max(0, y - radius):y + radius + 1, max(0, x - radius):x + radius + 1] == pid)


def validate_positions(plan, ids, sea_ids, report):
    path = MOD_ROOT / "map" / "positions.txt"
    positions = parse_positions(path.read_text(encoding="cp1252"))
    affected = set(plan["editable_old_ids"]) | {item["id"] for item in plan["new_provinces"]}
    for pid in sorted(affected):
        pairs = positions.get(pid)
        if not pairs or len(pairs) < 7:
            report.error(f"positions.txt lacks seven coordinate pairs for province {pid}")
            continue
        for index in (0, 1, 2, 4, 5, 6):
            x = int(round(pairs[index][0]))
            y = ids.shape[0] - int(round(pairs[index][1]))
            if not (0 <= x < ids.shape[1] and 0 <= y < ids.shape[0] and ids[y, x] == pid):
                report.error(f"Province {pid} position pair {index} lies outside its province: ({x}, {y})")
        port_x, port_y_bottom = pairs[3]
        if port_x or port_y_bottom:
            x = int(round(port_x))
            y = ids.shape[0] - int(round(port_y_bottom))
            if not (0 <= x < ids.shape[1] and 0 <= y < ids.shape[0]):
                report.error(f"Province {pid} port position is outside the bitmap")
            elif int(ids[y, x]) not in sea_ids:
                report.error(f"Province {pid} port is not in a sea province: ID {int(ids[y, x])}")
            elif not near_province(ids, pid, x, y, 2):
                report.error(f"Province {pid} port is not adjacent to its land mask")


def parse_area_memberships(text: str, area_keys: list[str], report: Report):
    memberships = defaultdict(list)
    for key in area_keys:
        block = extract_top_block(text, key)
        if not block:
            report.error(f"area.txt is missing {key}")
            continue
        block = re.sub(r"color\s*=\s*\{[^}]*\}", "", block, flags=re.S)
        for pid in map(int, re.findall(r"\b\d+\b", block)):
            memberships[pid].append(key)
    return memberships


def validate_memberships(plan, report):
    expected = set(plan["existing_japan_ids"]) | {item["id"] for item in plan["new_provinces"]}
    area_text = (MOD_ROOT / "map" / "area.txt").read_text(encoding="cp1252")
    memberships = parse_area_memberships(area_text, list(plan["areas"]), report)
    for pid in sorted(expected):
        areas = memberships.get(pid, [])
        if len(areas) != 1:
            report.error(f"Province {pid} belongs to {len(areas)} planned Japanese areas: {areas}")
    listed = {pid for ids in plan["areas"].values() for pid in ids}
    if listed != expected:
        report.error(f"province_plan area union differs from the 88 expected IDs: missing={sorted(expected-listed)}, extra={sorted(listed-expected)}")

    region_text = (MOD_ROOT / "map" / "region.txt").read_text(encoding="cp1252")
    region = extract_top_block(region_text, "japan_region")
    if not region:
        report.error("region.txt is missing japan_region")
    else:
        present_areas = set(re.findall(r"\b(?:jxp_[a-z0-9_]+|[a-z][a-z0-9_]+_area|northern_kyushu)\b", region))
        missing = set(plan["areas"]) - present_areas
        if missing:
            report.error(f"japan_region is missing areas: {sorted(missing)}")

    child_parent = {int(child): int(parent) for child, parent in plan["new_id_parent"].items()}
    for filename in ("climate.txt", "continent.txt"):
        text = (MOD_ROOT / "map" / filename).read_text(encoding="cp1252")
        counts = Counter(int(token) for token in re.findall(r"\b\d+\b", re.sub(r"#.*", "", text)))
        for child, parent in child_parent.items():
            if counts[child] != counts[parent]:
                report.error(f"{filename}: child {child} occurs {counts[child]} time(s), parent {parent} occurs {counts[parent]}")

    trade_text = (MOD_ROOT / "common" / "tradenodes" / "00_tradenodes.txt").read_text(encoding="cp1252")
    nippon = extract_top_block(trade_text, "nippon")
    if not nippon:
        report.error("00_tradenodes.txt is missing nippon")
    else:
        members_match = re.search(r"members\s*=\s*\{([^}]*)\}", nippon, flags=re.S)
        members = set(map(int, re.findall(r"\b\d+\b", members_match.group(1)))) if members_match else set()
        missing = expected - members
        if missing:
            report.error(f"Nippon trade node is missing Japanese provinces: {sorted(missing)}")


def validate_adjacencies(plan, report):
    rows = []
    with (MOD_ROOT / "map" / "adjacencies.csv").open("r", encoding="cp1252", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=";"))
    pairs = {(int(row[0]), int(row[1])) for row in rows if len(row) >= 4 and row[0].lstrip("-").isdigit() and row[1].lstrip("-").isdigit()}
    for item in plan["straits"]:
        pair = (int(item["from"]), int(item["to"]))
        if pair not in pairs and tuple(reversed(pair)) not in pairs:
            report.error(f"adjacencies.csv is missing planned strait {pair}")


def validate_hash_lock(game_root: Path, manifest: dict, report: Report):
    for relative, expected in manifest.get("input_sha256", {}).items():
        path = game_root / Path(relative)
        if not path.exists():
            report.error(f"Pinned vanilla input disappeared: {relative}")
        elif sha256(path) != expected:
            report.error(f"Pinned vanilla input changed since generation: {relative}")
    if manifest.get("plan_sha256") != sha256(PLAN_PATH):
        report.error("province_plan.json changed after the generated map; rebuild required")


def validate_cartographic_expansion(plan, ids, vanilla_ids, edit_mask, manifest, report):
    planned = {
        int(entry["province"]): {
            "target_pixels": int(entry["target_pixels"]),
            "allowed_sea_ids": {int(value) for value in entry["allowed_sea_ids"]},
            "max_radius": int(entry["max_radius"]),
        }
        for entry in plan.get("island_cartographic_expansion", [])
    }
    outside_changes = (ids != vanilla_ids) & ~edit_mask
    expected_mask = np.zeros(ids.shape, dtype=bool)
    counts = Counter()
    for pid, rule in planned.items():
        mask = outside_changes & (ids == pid) & np.isin(vanilla_ids, list(rule["allowed_sea_ids"]))
        expected_mask |= mask
        counts[pid] = int(mask.sum())
        if int(np.count_nonzero(ids == pid)) < rule["target_pixels"]:
            report.error(
                f"Cartographically expanded island {pid} has fewer than "
                f"{rule['target_pixels']} pixels"
            )
    unexpected = outside_changes & ~expected_mask
    if np.any(unexpected):
        examples = [
            (int(x), int(y), int(vanilla_ids[y, x]), int(ids[y, x]))
            for y, x in list(zip(*np.where(unexpected)))[:10]
        ]
        report.error(f"Unplanned province changes outside the original Japan land mask: {examples}")

    manifest_rows = {
        int(entry["province"]): int(entry["added_pixel_count"])
        for entry in manifest.get("island_cartographic_expansion", [])
    }
    if dict(counts) != manifest_rows:
        report.error(
            f"Cartographic expansion counts differ from manifest: actual={dict(counts)}, "
            f"manifest={manifest_rows}"
        )
    if int(outside_changes.sum()) != int(manifest.get("cartographic_expansion_pixels", -1)):
        report.error("Cartographic expansion pixel total differs from generated manifest")
    return expected_mask, set(planned)


def validate_support_maps(game_root, ids, expansion_mask, island_ids, manifest, report):
    expected_size = ids.shape[1], ids.shape[0]
    support = {}
    specifications = {
        "heightmap.bmp": ("L", expected_size),
        "terrain.bmp": ("P", expected_size),
        "rivers.bmp": ("P", expected_size),
        "world_normal.bmp": ("RGB", (expected_size[0] // 2, expected_size[1] // 2)),
    }
    for filename, (mode, size) in specifications.items():
        path = MOD_ROOT / "map" / filename
        if not path.exists():
            report.error(f"Missing cartographic support map: map/{filename}")
            continue
        image = Image.open(path)
        support[filename] = image
        if image.mode != mode or image.size != size:
            report.error(
                f"map/{filename} has {image.mode}/{image.size}, expected {mode}/{size}"
            )
        vanilla = Image.open(game_root / "map" / filename)
        if mode == "P" and image.getpalette() != vanilla.getpalette():
            report.error(f"map/{filename} does not preserve the vanilla indexed palette")

    if len(support) != len(specifications):
        return
    height = np.asarray(support["heightmap.bmp"], dtype=np.uint8)
    height_base = np.asarray(Image.open(game_root / "map" / "heightmap.bmp").convert("L"), dtype=np.uint8)
    terrain = np.asarray(support["terrain.bmp"], dtype=np.uint8)
    terrain_base = np.asarray(Image.open(game_root / "map" / "terrain.bmp"), dtype=np.uint8)
    rivers = np.asarray(support["rivers.bmp"], dtype=np.uint8)
    rivers_base = np.asarray(Image.open(game_root / "map" / "rivers.bmp"), dtype=np.uint8)
    normal = np.asarray(support["world_normal.bmp"].convert("RGB"), dtype=np.uint8)
    normal_base = np.asarray(Image.open(game_root / "map" / "world_normal.bmp").convert("RGB"), dtype=np.uint8)

    island_mask = np.isin(ids, list(island_ids))
    height_changes = height != height_base
    if np.any(height_changes & ~island_mask):
        report.error("heightmap.bmp changes pixels outside the planned island masks")
    if np.any(height[island_mask] < 96):
        report.error("Cartographically expanded islands retain sub-coastal heightmap pixels")
    for filename, changed in (
        ("terrain.bmp", terrain != terrain_base),
        ("rivers.bmp", rivers != rivers_base),
    ):
        if np.any(changed & ~expansion_mask):
            report.error(f"{filename} changes pixels outside the planned island expansion")

    half_mask = np.zeros(normal.shape[:2], dtype=bool)
    for y, x in zip(*np.where(island_mask)):
        half_mask[int(y) // 2, int(x) // 2] = True
    normal_changes = np.any(normal != normal_base, axis=2)
    if np.any(normal_changes & ~half_mask):
        report.error("world_normal.bmp changes pixels outside the planned island support cells")

    actual_counts = {
        "heightmap_changed_pixels": int(height_changes.sum()),
        "terrain_changed_pixels": int((terrain != terrain_base).sum()),
        "rivers_changed_pixels": int((rivers != rivers_base).sum()),
        "world_normal_changed_pixels": int(normal_changes.sum()),
    }
    if actual_counts != manifest.get("cartographic_support_maps"):
        report.error(
            f"Cartographic support-map counts differ from manifest: "
            f"actual={actual_counts}, manifest={manifest.get('cartographic_support_maps')}"
        )


def validate_history_presence(plan, strict, report):
    history_dir = MOD_ROOT / "history" / "provinces"
    missing = []
    for province in plan["new_provinces"]:
        pattern = f"{province['id']} - *.txt"
        exists = history_dir.exists() and bool(list(history_dir.glob(pattern)))
        if not exists:
            missing.append(province["id"])
    if missing:
        message = f"New province histories not generated yet: {missing}"
        (report.error if strict else report.warn)(message)


def main() -> int:
    args = parse_args()
    report = Report()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if not MANIFEST_PATH.exists():
        report.error("generated_manifest.json is missing; run build_map.py")
        return report.emit()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    definition_ids, rgb_to_id, _, mod_duplicates = read_definition(MOD_ROOT / "map" / "definition.csv", report)
    image = Image.open(MOD_ROOT / "map" / "provinces.bmp")
    if image.size != tuple(plan["bitmap_size"]):
        report.error(f"provinces.bmp has size {image.size}, expected {tuple(plan['bitmap_size'])}")
    if image.mode != "RGB":
        report.error(f"provinces.bmp mode is {image.mode}, expected RGB")
    ids = image_ids(image, rgb_to_id, report)

    vanilla_rows, vanilla_rgb, _, vanilla_duplicates = read_definition(args.game_root / "map" / "definition.csv", report)
    for rgb, pids in mod_duplicates.items():
        if set(pids) != set(vanilla_duplicates.get(rgb, [])):
            report.error(f"definition.csv introduces duplicate RGB {rgb} for IDs {pids}")
    if vanilla_duplicates:
        report.note(f"Inherited {len(vanilla_duplicates)} vanilla duplicate RGB reservations without adding any")
    vanilla_image = Image.open(args.game_root / "map" / "provinces.bmp").convert("RGB")
    vanilla_ids = image_ids(vanilla_image, {rgb: pid for pid, rgb in vanilla_rows.items()}, report)
    edit_mask = np.isin(vanilla_ids, plan["editable_old_ids"])
    expansion_mask, island_ids = validate_cartographic_expansion(
        plan, ids, vanilla_ids, edit_mask, manifest, report
    )
    validate_support_maps(
        args.game_root.resolve(), ids, expansion_mask, island_ids, manifest, report
    )

    max_match = re.search(r"(?m)^max_provinces\s*=\s*(\d+)", (MOD_ROOT / "map" / "default.map").read_text(encoding="cp1252"))
    if not max_match or int(max_match.group(1)) != int(plan["max_provinces"]):
        report.error(f"default.map max_provinces is not {plan['max_provinces']}")

    expected = set(plan["existing_japan_ids"]) | {item["id"] for item in plan["new_provinces"]}
    allowed_multi = set(plan["multi_component_allowed"])
    counts = {}
    for pid in sorted(expected):
        count = int(np.count_nonzero(ids == pid))
        counts[pid] = count
        if count == 0:
            report.error(f"Province {pid} has no pixels")
            continue
        if count < int(plan["minimum_province_pixels"]):
            report.error(
                f"Province {pid} has only {count} pixels; minimum is "
                f"{plan['minimum_province_pixels']}"
            )
        sizes = component_sizes(ids == pid)
        meaningful = [size for size in sizes if size > 1]
        baseline_sizes = component_sizes(vanilla_ids == pid) if pid in plan["existing_japan_ids"] else []
        baseline_meaningful = [size for size in baseline_sizes if size > 1]
        if len(meaningful) > max(1, len(baseline_meaningful)) and pid not in allowed_multi:
            report.error(f"Province {pid} is more disconnected than vanilla: final={sizes}, vanilla={baseline_sizes}")
        if any(size == 1 for size in sizes) and pid not in allowed_multi and 1 not in baseline_sizes:
            report.error(f"Province {pid} contains an introduced one-pixel speckle: {sizes}")
        if len(sizes) > 1 and pid in allowed_multi:
            report.note(f"Whitelisted multi-island province {pid}: components {sizes}")
    report.note(f"Japanese province pixels: {sum(counts.values())}; provinces: {len(counts)}")
    report.note(f"Smallest provinces: {sorted(counts.items(), key=lambda item: item[1])[:10]}")
    report.note(
        f"Province clickability floor: {plan['minimum_province_pixels']} pixels; "
        f"cartographic island growth: {int(expansion_mask.sum())} pixels"
    )

    new_ids = {item["id"] for item in plan["new_provinces"]}
    missing_definitions = new_ids - set(definition_ids)
    if missing_definitions:
        report.error(f"definition.csv lacks new IDs: {sorted(missing_definitions)}")
    missing_bitmap = [pid for pid in new_ids if not np.any(ids == pid)]
    if missing_bitmap:
        report.error(f"New definitions have no bitmap pixels: {sorted(missing_bitmap)}")

    default_text = (MOD_ROOT / "map" / "default.map").read_text(encoding="cp1252")
    sea_ids = parse_sea_ids(default_text, report)
    validate_positions(plan, ids, sea_ids, report)
    validate_memberships(plan, report)
    validate_adjacencies(plan, report)
    validate_hash_lock(args.game_root, manifest, report)
    validate_history_presence(plan, args.strict_history, report)
    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
