#!/usr/bin/env python3
"""Build the JXP 88-province companion map from a version-pinned plan.

The builder never writes to the EU4 installation. It transforms CODH historical
boundaries into the existing 1.37.5 Japan land mask, then emits full map-file
overrides and machine-readable metadata under the companion mod.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import time
import urllib.request
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
PLAN_PATH = SCRIPT_DIR / "province_plan.json"
SOURCE_DIR = SCRIPT_DIR / "sources" / "codh"
PREVIEW_DIR = SCRIPT_DIR / "previews"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", help="Reject missing cached CODH files")
    parser.add_argument("--skip-download", action="store_true", help="Alias for --offline")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_source(code: str, url_template: str, offline: bool) -> Path:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    path = SOURCE_DIR / f"{code}.geojson"
    if path.exists() and path.stat().st_size > 100:
        return path
    if offline:
        raise RuntimeError(f"Missing cached source in offline mode: {path}")
    url = url_template.format(code=code)
    request = urllib.request.Request(url, headers={"User-Agent": "JXP-map-builder/0.1"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
            if len(payload) < 100:
                raise RuntimeError(f"Short response ({len(payload)} bytes) from {url}")
            path.write_bytes(payload)
            return path
        except Exception as exc:  # pragma: no cover - network retry path
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not download {url}: {last_error}")


def load_geojson(code: str, template: str, offline: bool) -> dict:
    path = ensure_source(code, template, offline)
    return json.loads(path.read_text(encoding="utf-8"))


def iter_geometries(payload: dict):
    if payload.get("type") == "FeatureCollection":
        for feature in payload.get("features", []):
            geometry = feature.get("geometry")
            if geometry:
                yield geometry
    elif payload.get("type") == "Feature":
        geometry = payload.get("geometry")
        if geometry:
            yield geometry
    else:
        yield payload


def iter_polygons(geometry: dict):
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if kind == "Polygon":
        yield coordinates
    elif kind == "MultiPolygon":
        yield from coordinates
    else:
        raise ValueError(f"Unsupported GeoJSON geometry: {kind}")


def ring_area_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    if len(ring) < 3:
        xs = [point[0] for point in ring] or [0.0]
        ys = [point[1] for point in ring] or [0.0]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    twice_area = 0.0
    cx_acc = 0.0
    cy_acc = 0.0
    for first, second in zip(ring, ring[1:] + ring[:1]):
        cross = first[0] * second[1] - second[0] * first[1]
        twice_area += cross
        cx_acc += (first[0] + second[0]) * cross
        cy_acc += (first[1] + second[1]) * cross
    if abs(twice_area) < 1e-12:
        xs = [point[0] for point in ring]
        ys = [point[1] for point in ring]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return twice_area / 2.0, cx_acc / (3.0 * twice_area), cy_acc / (3.0 * twice_area)


def polygon_centroid(polygon: list[list[list[float]]]) -> tuple[float, float, float]:
    if not polygon:
        return 0.0, 0.0, 0.0
    total_area = 0.0
    cx_total = 0.0
    cy_total = 0.0
    for index, ring in enumerate(polygon):
        area, cx, cy = ring_area_centroid(ring)
        weight = abs(area) * (1.0 if index == 0 else -1.0)
        total_area += weight
        cx_total += cx * weight
        cy_total += cy * weight
    if abs(total_area) < 1e-12:
        _, cx, cy = ring_area_centroid(polygon[0])
        return 0.0, cx, cy
    return abs(total_area), cx_total / total_area, cy_total / total_area


def payload_centroid(payload: dict) -> tuple[float, float]:
    weighted_x = 0.0
    weighted_y = 0.0
    weight_total = 0.0
    fallback: list[tuple[float, float]] = []
    for geometry in iter_geometries(payload):
        for polygon in iter_polygons(geometry):
            area, cx, cy = polygon_centroid(polygon)
            fallback.append((cx, cy))
            weight = max(area, 1e-12)
            weighted_x += cx * weight
            weighted_y += cy * weight
            weight_total += weight
    if weight_total:
        return weighted_x / weight_total, weighted_y / weight_total
    if fallback:
        return tuple(np.mean(np.array(fallback), axis=0))
    raise ValueError("GeoJSON contains no polygons")


def parse_definition(path: Path) -> tuple[list[list[str]], dict[int, tuple[int, int, int]]]:
    rows: list[list[str]] = []
    colors: dict[int, tuple[int, int, int]] = {}
    with path.open("r", encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row or not row[0].strip().isdigit():
                continue
            pid = int(row[0])
            rgb = tuple(int(value) for value in row[1:4])
            rows.append(row)
            colors[pid] = rgb
    return rows, colors


def id_array(image: Image.Image, colors: dict[int, tuple[int, int, int]]) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint32)
    packed = (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]
    lookup = np.zeros(1 << 24, dtype=np.int32)
    for pid, (r, g, b) in colors.items():
        lookup[(r << 16) | (g << 8) | b] = pid
    return lookup[packed]


def province_centroid(ids: np.ndarray, pid: int, height: int) -> tuple[float, float]:
    ys, xs = np.where(ids == pid)
    if not len(xs):
        raise RuntimeError(f"Projection anchor province has no pixels: {pid}")
    return float(xs.mean()), float(height - ys.mean())


def fit_projection(
    plan: dict,
    vanilla_ids: np.ndarray,
    height: int,
    source_payloads: dict[str, dict],
) -> tuple[np.ndarray, dict]:
    source_points = []
    target_x = []
    target_y = []
    residual_rows = []
    for code, pid in plan["projection_anchors"].items():
        lon, lat = payload_centroid(source_payloads[code])
        x, y_bottom = province_centroid(vanilla_ids, int(pid), height)
        source_points.append([lon, lat, 1.0])
        target_x.append(x)
        target_y.append(y_bottom)
    matrix = np.asarray(source_points, dtype=float)
    coeff_x, *_ = np.linalg.lstsq(matrix, np.asarray(target_x), rcond=None)
    coeff_y, *_ = np.linalg.lstsq(matrix, np.asarray(target_y), rcond=None)
    coefficients = np.vstack([coeff_x, coeff_y])
    predicted_x = matrix @ coeff_x
    predicted_y = matrix @ coeff_y
    errors = np.sqrt((predicted_x - np.asarray(target_x)) ** 2 + (predicted_y - np.asarray(target_y)) ** 2)
    for (code, pid), error in zip(plan["projection_anchors"].items(), errors):
        residual_rows.append({"source": code, "province": int(pid), "error_pixels": round(float(error), 4)})
    diagnostics = {
        "coefficients": coefficients.tolist(),
        "rmse_pixels": round(float(np.sqrt(np.mean(errors ** 2))), 4),
        "median_error_pixels": round(float(np.median(errors)), 4),
        "max_error_pixels": round(float(np.max(errors)), 4),
        "anchors": residual_rows,
    }
    return coefficients, diagnostics


def transform_point(point: list[float], coefficients: np.ndarray, height: int) -> tuple[int, int]:
    vector = np.asarray([point[0], point[1], 1.0])
    x, y_bottom = coefficients @ vector
    return int(round(x)), int(round(height - y_bottom))


def transformed_ring(ring, coefficients, height):
    points = []
    previous = None
    for point in ring:
        converted = transform_point(point, coefficients, height)
        if converted != previous:
            points.append(converted)
            previous = converted
    return points


def draw_polygon(draw: ImageDraw.ImageDraw, polygon, pid: int, coefficients, height, clear_holes: bool):
    if not polygon:
        return
    exterior = transformed_ring(polygon[0], coefficients, height)
    if len(exterior) >= 3:
        draw.polygon(exterior, fill=int(pid))
    if clear_holes:
        for hole in polygon[1:]:
            points = transformed_ring(hole, coefficients, height)
            if len(points) >= 3:
                draw.polygon(points, fill=0)


def draw_payload(canvas, payload, pid, coefficients, height, clear_holes=True):
    draw = ImageDraw.Draw(canvas)
    for geometry in iter_geometries(payload):
        for polygon in iter_polygons(geometry):
            draw_polygon(draw, polygon, pid, coefficients, height, clear_holes)


def classify_ryukyu_polygon(polygon, rules):
    _, lon, lat = polygon_centroid(polygon)
    for rule in rules:
        condition = rule["when"]
        if condition == "centroid_lat_gt" and lat > float(rule["value"]):
            return int(rule["province"])
        if condition == "centroid_lon_lt" and lon < float(rule["value"]):
            return int(rule["province"])
        if condition == "otherwise":
            return int(rule["province"])
    raise RuntimeError(f"No Ryukyu component rule matched ({lon}, {lat})")


def fill_unlabelled_land(labels: np.ndarray, edit_mask: np.ndarray, vanilla_ids: np.ndarray) -> np.ndarray:
    ys, xs = np.where(edit_mask)
    min_y, max_y = int(ys.min()), int(ys.max())
    min_x, max_x = int(xs.min()), int(xs.max())
    crop = labels[min_y:max_y + 1, min_x:max_x + 1].copy()
    mask = edit_mask[min_y:max_y + 1, min_x:max_x + 1]
    old = vanilla_ids[min_y:max_y + 1, min_x:max_x + 1]
    queue: deque[tuple[int, int]] = deque()
    visited = np.zeros(mask.shape, dtype=bool)
    labelled = mask & (crop > 0)
    for y, x in zip(*np.where(labelled)):
        visited[y, x] = True
        queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        value = crop[y, x]
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < crop.shape[0] and 0 <= nx < crop.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                crop[ny, nx] = value
                queue.append((ny, nx))
    # Tiny island components outside the transformed source retain their old ID.
    crop[mask & ~visited] = old[mask & ~visited]
    result = labels.copy()
    result[min_y:max_y + 1, min_x:max_x + 1] = crop
    return result


def split_stylized_ryukyu(labels: np.ndarray, vanilla_ids: np.ndarray) -> dict:
    """Split vanilla 1015's compressed island chain without changing coastline.

    The vanilla raster omits the real-distance Sakishima geometry. Its 1015 mask
    instead contains three dominant island groups. Their north-to-south order is
    stable and maps to Amami, Okinawa, and Sakishima.
    """
    mask = vanilla_ids == 1015
    visited = np.zeros(mask.shape, dtype=bool)
    components = []
    for y, x in zip(*np.where(mask)):
        if visited[y, x]:
            continue
        queue = deque([(int(y), int(x))])
        visited[y, x] = True
        pixels = []
        while queue:
            cy, cx = queue.popleft()
            pixels.append((cy, cx))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        components.append(pixels)
    if len(components) < 3:
        raise RuntimeError(f"Vanilla province 1015 has only {len(components)} island components")
    dominant = sorted(components, key=len, reverse=True)[:3]
    anchors = []
    for component in dominant:
        anchors.append((
            float(np.mean([x for _, x in component])),
            float(np.mean([y for y, _ in component])),
            component,
        ))
    anchors.sort(key=lambda item: item[1])
    target_by_anchor = [4980, 1015, 4981]
    assignments = []
    for component in components:
        cx = float(np.mean([x for _, x in component]))
        cy = float(np.mean([y for y, _ in component]))
        anchor_index = int(np.argmin([(cx - ax) ** 2 + (cy - ay) ** 2 for ax, ay, _ in anchors]))
        target = target_by_anchor[anchor_index]
        for py, px in component:
            labels[py, px] = target
        assignments.append({
            "pixels": len(component),
            "centroid": [round(cx, 3), round(cy, 3)],
            "province": target,
        })
    return {"method": "three_dominant_vanilla_1015_components", "components": assignments}


def pixel_components(ids: np.ndarray, pid: int) -> list[list[tuple[int, int]]]:
    mask = ids == pid
    ys, xs = np.where(mask)
    if not len(xs):
        return []
    min_y, max_y = int(ys.min()), int(ys.max())
    min_x, max_x = int(xs.min()), int(xs.max())
    crop = mask[min_y:max_y + 1, min_x:max_x + 1]
    visited = np.zeros(crop.shape, dtype=bool)
    components = []
    for y, x in zip(*np.where(crop)):
        if visited[y, x]:
            continue
        queue = deque([(int(y), int(x))])
        visited[y, x] = True
        component = []
        while queue:
            cy, cx = queue.popleft()
            component.append((cy + min_y, cx + min_x))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < crop.shape[0] and 0 <= nx < crop.shape[1] and crop[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        components.append(component)
    return sorted(components, key=len, reverse=True)


def clean_new_disconnections(final_ids: np.ndarray, vanilla_ids: np.ndarray, plan: dict) -> list[dict]:
    """Remove mainland fragments while preserving baseline and declared islands."""
    expected = set(plan["existing_japan_ids"]) | {item["id"] for item in plan["new_provinces"]}
    explicitly_allowed = set(plan["multi_component_allowed"])
    changes = []
    for pid in sorted(expected - explicitly_allowed):
        components = pixel_components(final_ids, pid)
        if pid in plan["existing_japan_ids"]:
            baseline_components = pixel_components(vanilla_ids, pid)
            keep_count = max(1, len(baseline_components))
            baseline_has_speckle = any(len(part) == 1 for part in baseline_components)
        else:
            keep_count = 1
            baseline_has_speckle = False
        removable = [
            component for index, component in enumerate(components)
            if index >= keep_count or (len(component) == 1 and not baseline_has_speckle)
        ]
        if not removable:
            continue
        for component in removable:
            neighbors = Counter()
            for y, x in component:
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < final_ids.shape[0] and 0 <= nx < final_ids.shape[1]:
                        neighbor = int(final_ids[ny, nx])
                        if neighbor != pid and neighbor in expected:
                            neighbors[neighbor] += 1
            if not neighbors:
                continue
            replacement = neighbors.most_common(1)[0][0]
            for y, x in component:
                final_ids[y, x] = replacement
            changes.append({"province": pid, "pixels": len(component), "assigned_to": replacement})
    return changes


def neighboring_cells(shape: tuple[int, int], y: int, x: int, diagonals: bool = False):
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonals:
        offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    for dy, dx in offsets:
        ny, nx = y + dy, x + dx
        if 0 <= ny < shape[0] and 0 <= nx < shape[1]:
            yield ny, nx


def rebalance_small_land_provinces(final_ids: np.ndarray, plan: dict) -> list[dict]:
    """Grow undersized mainland provinces from explicit adjacent donors.

    Every transferred pixel is four-neighbour connected to the recipient. A
    candidate is rejected if removing it would split its donor or push the
    donor below the global province-size floor.
    """
    changes = []
    global_floor = int(plan["minimum_province_pixels"])
    for entry in plan.get("pixel_rebalance", []):
        target = int(entry["province"])
        target_pixels = int(entry["target_pixels"])
        donors = [int(value) for value in entry["donors"]]
        transferred = Counter()
        while int(np.count_nonzero(final_ids == target)) < target_pixels:
            target_points = np.argwhere(final_ids == target)
            centroid_y, centroid_x = target_points.mean(axis=0)
            candidates = []
            for donor_order, donor in enumerate(donors):
                donor_count = int(np.count_nonzero(final_ids == donor))
                if donor_count <= global_floor:
                    continue
                before_components = len(pixel_components(final_ids, donor))
                for y, x in np.argwhere(final_ids == donor):
                    y, x = int(y), int(x)
                    direct_target_neighbors = sum(
                        int(final_ids[ny, nx] == target)
                        for ny, nx in neighboring_cells(final_ids.shape, y, x)
                    )
                    if not direct_target_neighbors:
                        continue
                    broad_target_neighbors = sum(
                        int(final_ids[ny, nx] == target)
                        for ny, nx in neighboring_cells(final_ids.shape, y, x, diagonals=True)
                    )
                    distance = (y - centroid_y) ** 2 + (x - centroid_x) ** 2
                    candidates.append((
                        -direct_target_neighbors,
                        -broad_target_neighbors,
                        donor_order,
                        distance,
                        y,
                        x,
                        donor,
                        before_components,
                    ))
            accepted = False
            for _, _, _, _, y, x, donor, before_components in sorted(candidates):
                final_ids[y, x] = target
                donor_count = int(np.count_nonzero(final_ids == donor))
                after_components = len(pixel_components(final_ids, donor))
                if donor_count >= global_floor and after_components == before_components:
                    transferred[donor] += 1
                    accepted = True
                    break
                final_ids[y, x] = donor
            if not accepted:
                raise RuntimeError(
                    f"Could not grow province {target} to {target_pixels} pixels "
                    f"without disconnecting donors {donors}"
                )
        changes.append({
            "province": target,
            "target_pixels": target_pixels,
            "final_pixels": int(np.count_nonzero(final_ids == target)),
            "transferred_from": {str(pid): count for pid, count in sorted(transferred.items())},
        })
    return changes


def expand_small_islands(final_ids: np.ndarray, plan: dict) -> list[dict]:
    """Apply tightly bounded cartographic exaggeration to isolated islands."""
    changes = []
    for entry in plan.get("island_cartographic_expansion", []):
        target = int(entry["province"])
        target_pixels = int(entry["target_pixels"])
        allowed_sea = {int(value) for value in entry["allowed_sea_ids"]}
        max_radius = int(entry["max_radius"])
        source_pixels = [(int(y), int(x)) for y, x in np.argwhere(final_ids == target)]
        if not source_pixels:
            raise RuntimeError(f"Island province {target} has no source pixels")
        centroid_y = sum(y for y, _ in source_pixels) / len(source_pixels)
        centroid_x = sum(x for _, x in source_pixels) / len(source_pixels)
        added = []
        while int(np.count_nonzero(final_ids == target)) < target_pixels:
            candidates = {}
            for y, x in np.argwhere(final_ids == target):
                for ny, nx in neighboring_cells(final_ids.shape, int(y), int(x)):
                    old_id = int(final_ids[ny, nx])
                    if old_id not in allowed_sea:
                        continue
                    distance_to_source = min(abs(ny - sy) + abs(nx - sx) for sy, sx in source_pixels)
                    if distance_to_source > max_radius:
                        continue
                    direct_neighbors = sum(
                        int(final_ids[ay, ax] == target)
                        for ay, ax in neighboring_cells(final_ids.shape, ny, nx)
                    )
                    broad_neighbors = sum(
                        int(final_ids[ay, ax] == target)
                        for ay, ax in neighboring_cells(final_ids.shape, ny, nx, diagonals=True)
                    )
                    centroid_distance = (ny - centroid_y) ** 2 + (nx - centroid_x) ** 2
                    score = (
                        distance_to_source,
                        -direct_neighbors,
                        -broad_neighbors,
                        centroid_distance,
                        ny,
                        nx,
                    )
                    candidates[(ny, nx)] = (score, old_id)
            if not candidates:
                raise RuntimeError(
                    f"Could not grow island province {target} to {target_pixels} pixels "
                    f"within radius {max_radius} and sea IDs {sorted(allowed_sea)}"
                )
            (y, x), (_, old_id) = min(candidates.items(), key=lambda item: item[1][0])
            final_ids[y, x] = target
            added.append((y, x, old_id))
        changes.append({
            "province": target,
            "target_pixels": target_pixels,
            "final_pixels": int(np.count_nonzero(final_ids == target)),
            "allowed_sea_ids": sorted(allowed_sea),
            "max_radius": max_radius,
            "source_pixels": source_pixels,
            "added_pixels": added,
        })
    return changes


def nearest_source_pixel(y: int, x: int, source_pixels: list[tuple[int, int]]) -> tuple[int, int]:
    return min(source_pixels, key=lambda point: ((point[0] - y) ** 2 + (point[1] - x) ** 2, point))


def write_cartographic_support_maps(
    game_root: Path,
    map_dir: Path,
    final_ids: np.ndarray,
    island_expansions: list[dict],
) -> dict:
    """Extend vanilla terrain support only around exaggerated island masks."""
    height_source = Image.open(game_root / "map" / "heightmap.bmp").convert("L")
    terrain_source = Image.open(game_root / "map" / "terrain.bmp")
    rivers_source = Image.open(game_root / "map" / "rivers.bmp")
    normal_source = Image.open(game_root / "map" / "world_normal.bmp").convert("RGB")
    height = np.asarray(height_source, dtype=np.uint8).copy()
    terrain = np.asarray(terrain_source, dtype=np.uint8).copy()
    rivers = np.asarray(rivers_source, dtype=np.uint8).copy()
    normal = np.asarray(normal_source, dtype=np.uint8).copy()
    height_before = height.copy()
    terrain_before = terrain.copy()
    rivers_before = rivers.copy()
    normal_before = normal.copy()

    for entry in island_expansions:
        target = int(entry["province"])
        source_pixels = [tuple(point) for point in entry["source_pixels"]]
        target_pixels = [(int(y), int(x)) for y, x in np.argwhere(final_ids == target)]
        for y, x in target_pixels:
            height[y, x] = max(int(height[y, x]), 96)
        for y, x, _ in entry["added_pixels"]:
            sy, sx = nearest_source_pixel(int(y), int(x), source_pixels)
            terrain[int(y), int(x)] = terrain[sy, sx]
            rivers[int(y), int(x)] = rivers[sy, sx]

        source_half = sorted({(y // 2, x // 2) for y, x in source_pixels})
        target_half = sorted({(y // 2, x // 2) for y, x in target_pixels})
        for y, x in target_half:
            sy, sx = nearest_source_pixel(y, x, source_half)
            normal[y, x] = normal_before[sy, sx]

    Image.fromarray(height, mode="L").save(map_dir / "heightmap.bmp", format="BMP")
    terrain_output = terrain_source.copy()
    terrain_output.putdata(terrain.ravel())
    terrain_output.save(map_dir / "terrain.bmp", format="BMP")
    rivers_output = rivers_source.copy()
    rivers_output.putdata(rivers.ravel())
    rivers_output.save(map_dir / "rivers.bmp", format="BMP")
    Image.fromarray(normal, mode="RGB").save(map_dir / "world_normal.bmp", format="BMP")

    return {
        "heightmap_changed_pixels": int(np.count_nonzero(height != height_before)),
        "terrain_changed_pixels": int(np.count_nonzero(terrain != terrain_before)),
        "rivers_changed_pixels": int(np.count_nonzero(rivers != rivers_before)),
        "world_normal_changed_pixels": int(np.any(normal != normal_before, axis=2).sum()),
    }


def deterministic_color(pid: int, used: set[tuple[int, int, int]]) -> tuple[int, int, int]:
    seed = pid * 2654435761 & 0xFFFFFFFF
    for step in range(10000):
        value = (seed + step * 2246822519) & 0xFFFFFFFF
        rgb = (32 + (value & 0xBF), 32 + ((value >> 8) & 0xBF), 32 + ((value >> 16) & 0xBF))
        if rgb not in used and rgb != (0, 0, 0):
            used.add(rgb)
            return rgb
    raise RuntimeError(f"Could not allocate RGB for province {pid}")


def write_definition(output: Path, source_rows, colors, new_provinces):
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="cp1252", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        for row in source_rows:
            writer.writerow(row)
        for province in sorted(new_provinces, key=lambda item: item["id"]):
            pid = int(province["id"])
            r, g, b = colors[pid]
            writer.writerow([pid, r, g, b, province["name"], "x"])


def replace_top_level_block(text: str, key: str, replacement: str) -> str:
    pattern = re.compile(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{")
    match = pattern.search(text)
    if not match:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    start = match.start()
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
                end = cursor + 1
                while end < len(text) and text[end] in " \t\r":
                    end += 1
                if end < len(text) and text[end] == "\n":
                    end += 1
                return text[:start] + replacement.rstrip() + "\n" + text[end:]
        cursor += 1
    raise RuntimeError(f"Unclosed top-level block: {key}")


def area_color(index: int) -> tuple[int, int, int]:
    palette = [
        (176, 95, 83), (79, 132, 178), (105, 153, 93), (197, 151, 61),
        (132, 101, 168), (70, 155, 151), (202, 109, 146), (147, 130, 75),
    ]
    base = palette[index % len(palette)]
    cycle = index // len(palette)
    return tuple(max(30, min(225, channel + (cycle * 17 if cycle % 2 == 0 else -cycle * 13))) for channel in base)


def build_areas(game_root: Path, plan: dict, output: Path):
    text = (game_root / "map" / "area.txt").read_text(encoding="cp1252")
    for index, (key, ids) in enumerate(plan["areas"].items()):
        r, g, b = area_color(index)
        id_line = " ".join(str(pid) for pid in ids)
        block = f"{key} = {{\n\tcolor = {{ {r} {g} {b} }}\n\t{id_line}\n}}"
        text = replace_top_level_block(text, key, block)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="cp1252", newline="\n")


def build_region(game_root: Path, plan: dict, output: Path):
    text = (game_root / "map" / "region.txt").read_text(encoding="cp1252")
    area_lines = "\n".join(f"\t\t{key}" for key in plan["areas"])
    block = (
        "japan_region = {\n\tareas = {\n" + area_lines +
        "\n\t}\n\tmonsoon = {\n\t\t00.06.01\n\t\t00.07.30\n\t}\n}"
    )
    text = replace_top_level_block(text, "japan_region", block)
    output.write_text(text, encoding="cp1252", newline="\n")


def inherit_numeric_membership(text: str, child_to_parent: dict[int, int]) -> str:
    output_lines = []
    for line in text.splitlines():
        body, separator, comment = line.partition("#")
        present = {int(token) for token in re.findall(r"\b\d+\b", body)}
        additions = [child for child, parent in child_to_parent.items() if parent in present and child not in present]
        if additions:
            body = body.rstrip() + " " + " ".join(str(value) for value in sorted(additions)) + " "
        output_lines.append(body + (separator + comment if separator else ""))
    return "\n".join(output_lines) + "\n"


def build_membership_file(source: Path, output: Path, child_to_parent: dict[int, int]):
    text = source.read_text(encoding="cp1252")
    output.write_text(inherit_numeric_membership(text, child_to_parent), encoding="cp1252", newline="\n")


def add_to_named_members_block(text: str, top_key: str, ids: list[int]) -> str:
    top_pattern = re.compile(rf"(?m)^\s*{re.escape(top_key)}\s*=\s*\{{")
    match = top_pattern.search(text)
    if not match:
        raise RuntimeError(f"Missing top-level block: {top_key}")
    start = match.start()
    probe = replace_top_level_block(text, top_key, "__JXP_PLACEHOLDER__")
    placeholder = probe.index("__JXP_PLACEHOLDER__")
    suffix_start = len(text) - (len(probe) - placeholder - len("__JXP_PLACEHOLDER__"))
    block = text[start:suffix_start]
    members_match = re.search(r"(?m)^\s*members\s*=\s*\{", block)
    if not members_match:
        raise RuntimeError(f"Missing members block in {top_key}")
    brace = members_match.end() - 1
    depth = 0
    cursor = brace
    while cursor < len(block):
        if block[cursor] == "{":
            depth += 1
        elif block[cursor] == "}":
            depth -= 1
            if depth == 0:
                current = {int(token) for token in re.findall(r"\b\d+\b", block[brace + 1:cursor])}
                missing = [pid for pid in ids if pid not in current]
                insertion = "\n\t\t" + " ".join(str(pid) for pid in missing) + " " if missing else ""
                block = block[:cursor] + insertion + block[cursor:]
                return text[:start] + block + text[suffix_start:]
        cursor += 1
    raise RuntimeError(f"Unclosed members block in {top_key}")


def largest_component(mask: np.ndarray) -> np.ndarray:
    visited = np.zeros(mask.shape, dtype=bool)
    best: list[tuple[int, int]] = []
    for y, x in zip(*np.where(mask)):
        if visited[y, x]:
            continue
        component = []
        queue = deque([(int(y), int(x))])
        visited[y, x] = True
        while queue:
            cy, cx = queue.popleft()
            component.append((cy, cx))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        if len(component) > len(best):
            best = component
    result = np.zeros(mask.shape, dtype=bool)
    for y, x in best:
        result[y, x] = True
    return result


def interior_point(ids: np.ndarray, pid: int) -> tuple[int, int]:
    full_mask = ids == pid
    ys, xs = np.where(full_mask)
    if not len(xs):
        raise RuntimeError(f"Province {pid} has no pixels")
    min_y, max_y = int(ys.min()), int(ys.max())
    min_x, max_x = int(xs.min()), int(xs.max())
    mask = full_mask[min_y:max_y + 1, min_x:max_x + 1]
    mask = largest_component(mask)
    distance = np.full(mask.shape, -1, dtype=np.int16)
    queue = deque()
    for y, x in zip(*np.where(mask)):
        boundary = any(
            ny < 0 or nx < 0 or ny >= mask.shape[0] or nx >= mask.shape[1] or not mask[ny, nx]
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
        )
        if boundary:
            distance[y, x] = 0
            queue.append((int(y), int(x)))
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and distance[ny, nx] < 0:
                distance[ny, nx] = distance[y, x] + 1
                queue.append((ny, nx))
    max_distance = int(distance.max())
    candidates_y, candidates_x = np.where(distance == max_distance)
    centroid_x = candidates_x.mean()
    centroid_y = candidates_y.mean()
    index = int(np.argmin((candidates_x - centroid_x) ** 2 + (candidates_y - centroid_y) ** 2))
    return int(candidates_x[index] + min_x), int(candidates_y[index] + min_y)


def parse_sea_ids(default_map_text: str) -> set[int]:
    match = re.search(r"sea_starts\s*=\s*\{([^}]*)\}", default_map_text, flags=re.S)
    if not match:
        raise RuntimeError("Could not parse sea_starts from default.map")
    return {int(token) for token in re.findall(r"\b\d+\b", match.group(1))}


def coastal_port(ids: np.ndarray, pid: int, sea_ids: set[int], city: tuple[int, int]) -> tuple[int, int] | None:
    ys, xs = np.where(ids == pid)
    candidates = []
    height, width = ids.shape
    for y, x in zip(ys, xs):
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and int(ids[ny, nx]) in sea_ids:
                score = (x - city[0]) ** 2 + (y - city[1]) ** 2
                candidates.append((score, int(nx), int(ny)))
    if not candidates:
        return None
    _, x, y = min(candidates)
    return x, y


def position_block(pid: int, name: str, city, port, height: int) -> str:
    x, image_y = city
    y = height - image_y
    if port:
        port_x, port_image_y = port
        port_y = height - port_image_y
        port_pair = f"{port_x:.3f} {port_y:.3f}"
    else:
        port_pair = "0.000 0.000"
    pairs = [
        f"{x:.3f} {y:.3f}", f"{x:.3f} {y:.3f}", f"{x:.3f} {y:.3f}",
        port_pair, f"{x:.3f} {y:.3f}", f"{x:.3f} {y:.3f}", f"{x:.3f} {y:.3f}",
    ]
    return (
        f"#{name}\n{pid}={{\n\tposition={{\n\t\t{' '.join(pairs)} \n\t}}\n"
        "\trotation={\n\t\t0.000 0.000 0.000 0.000 0.000 0.000 0.000 \n\t}\n"
        "\theight={\n\t\t0.000 0.000 1.000 0.000 0.000 0.000 0.000 \n\t}\n}"
    )


def build_positions(game_root: Path, plan: dict, ids: np.ndarray, sea_ids: set[int], output: Path, names: dict[int, str]):
    source = (game_root / "map" / "positions.txt").read_text(encoding="cp1252")
    affected = [pid for pid in plan["editable_old_ids"]] + [item["id"] for item in plan["new_provinces"]]
    for pid in affected:
        city = interior_point(ids, int(pid))
        port = coastal_port(ids, int(pid), sea_ids, city)
        block = position_block(int(pid), names[int(pid)], city, port, ids.shape[0])
        source = replace_top_level_block(source, str(pid), block)
    output.write_text(source, encoding="cp1252", newline="\n")


def nearest_pixel_pair(ids: np.ndarray, first: int, second: int):
    y1, x1 = np.where(ids == first)
    y2, x2 = np.where(ids == second)
    if not len(x1) or not len(x2):
        raise RuntimeError(f"Cannot build strait {first}-{second}: missing pixels")
    points1 = np.column_stack([x1, y1])
    points2 = np.column_stack([x2, y2])
    best = None
    for start in range(0, len(points1), 256):
        chunk = points1[start:start + 256]
        distances = ((chunk[:, None, :] - points2[None, :, :]) ** 2).sum(axis=2)
        flat = int(np.argmin(distances))
        local_i, j = np.unravel_index(flat, distances.shape)
        value = int(distances[local_i, j])
        if best is None or value < best[0]:
            best = (value, tuple(chunk[local_i]), tuple(points2[j]))
    return best[1], best[2]


def line_points(first, second):
    x1, y1 = first
    x2, y2 = second
    steps = max(abs(x2 - x1), abs(y2 - y1), 1)
    for index in range(steps + 1):
        ratio = index / steps
        yield int(round(x1 + (x2 - x1) * ratio)), int(round(y1 + (y2 - y1) * ratio))


def through_sea(ids: np.ndarray, first, second, sea_ids: set[int]) -> int:
    found = [int(ids[y, x]) for x, y in line_points(first, second) if int(ids[y, x]) in sea_ids]
    if found:
        return Counter(found).most_common(1)[0][0]
    midpoint = ((first[0] + second[0]) // 2, (first[1] + second[1]) // 2)
    for radius in range(1, 40):
        candidates = []
        for y in range(max(0, midpoint[1] - radius), min(ids.shape[0], midpoint[1] + radius + 1)):
            for x in range(max(0, midpoint[0] - radius), min(ids.shape[1], midpoint[0] + radius + 1)):
                value = int(ids[y, x])
                if value in sea_ids:
                    candidates.append(value)
        if candidates:
            return Counter(candidates).most_common(1)[0][0]
    raise RuntimeError(f"No sea zone found between strait endpoints {first} and {second}")


def build_adjacencies(game_root: Path, plan: dict, ids: np.ndarray, sea_ids: set[int], output: Path):
    source = (game_root / "map" / "adjacencies.csv").read_text(encoding="cp1252")
    lines = source.splitlines()
    insertion = next((index for index, line in enumerate(lines) if line.startswith("-1;-1;")), len(lines))
    rows = []
    for item in plan["straits"]:
        first_id, second_id = int(item["from"]), int(item["to"])
        first, second = nearest_pixel_pair(ids, first_id, second_id)
        sea = through_sea(ids, first, second, sea_ids)
        y1 = ids.shape[0] - first[1]
        y2 = ids.shape[0] - second[1]
        rows.append(f"{first_id};{second_id};sea;{sea};{first[0]};{y1};{second[0]};{y2};{item['comment']}")
    lines[insertion:insertion] = rows
    output.write_text("\n".join(lines) + "\n", encoding="cp1252", newline="\n")


def render_preview(ids: np.ndarray, colors: dict[int, tuple[int, int, int]], plan: dict):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    edit_mask = np.isin(ids, plan["editable_old_ids"] + [item["id"] for item in plan["new_provinces"]])
    ys, xs = np.where(edit_mask)
    margin = 10
    box = (max(0, xs.min() - margin), max(0, ys.min() - margin), min(ids.shape[1], xs.max() + margin), min(ids.shape[0], ys.max() + margin))
    rgb = np.zeros((ids.shape[0], ids.shape[1], 3), dtype=np.uint8)
    for pid in np.unique(ids[edit_mask]):
        rgb[ids == pid] = colors[int(pid)]
    crop_ids = ids[box[1]:box[3], box[0]:box[2]]
    crop_rgb = rgb[box[1]:box[3], box[0]:box[2]].copy()
    boundary = np.zeros(crop_ids.shape, dtype=bool)
    boundary[1:, :] |= crop_ids[1:, :] != crop_ids[:-1, :]
    boundary[:, 1:] |= crop_ids[:, 1:] != crop_ids[:, :-1]
    boundary &= crop_ids > 0
    crop_rgb[boundary] = (12, 12, 12)
    crop = Image.fromarray(crop_rgb, "RGB")
    crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.NEAREST).save(PREVIEW_DIR / "japan_88_colors.png")
    draw = ImageDraw.Draw(crop)
    font = ImageFont.load_default()
    target_ids = [pid for pid in plan["editable_old_ids"]] + [item["id"] for item in plan["new_provinces"]]
    for pid in target_ids:
        try:
            x, y = interior_point(ids, int(pid))
        except RuntimeError:
            continue
        local_x, local_y = x - box[0], y - box[1]
        label = str(pid)
        bounds = draw.textbbox((local_x, local_y), label, font=font, anchor="mm")
        draw.rectangle(bounds, fill=(15, 15, 15))
        draw.text((local_x, local_y), label, fill=(255, 255, 255), font=font, anchor="mm")
    crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.NEAREST).save(PREVIEW_DIR / "japan_88_ids.png")


def render_small_province_preview(
    ids: np.ndarray,
    colors: dict[int, tuple[int, int, int]],
    plan: dict,
):
    targets = []
    for entry in plan.get("island_cartographic_expansion", []) + plan.get("pixel_rebalance", []):
        pid = int(entry["province"])
        if pid not in targets:
            targets.append(pid)
    columns, cell_width, cell_height = 4, 220, 220
    rows = math.ceil(len(targets) / columns)
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (24, 26, 28))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, pid in enumerate(targets):
        ys, xs = np.where(ids == pid)
        padding = 5
        min_y, max_y = max(0, int(ys.min()) - padding), min(ids.shape[0], int(ys.max()) + padding + 1)
        min_x, max_x = max(0, int(xs.min()) - padding), min(ids.shape[1], int(xs.max()) + padding + 1)
        crop_ids = ids[min_y:max_y, min_x:max_x]
        crop_rgb = np.zeros((*crop_ids.shape, 3), dtype=np.uint8)
        for visible_pid in np.unique(crop_ids):
            if int(visible_pid) in colors:
                crop_rgb[crop_ids == visible_pid] = colors[int(visible_pid)]
        crop_rgb = (crop_rgb * 0.35).astype(np.uint8)
        crop_rgb[crop_ids == pid] = (242, 205, 76)
        image = Image.fromarray(crop_rgb, mode="RGB").resize(
            (180, 160), Image.Resampling.NEAREST
        )
        left = (index % columns) * cell_width + 20
        top = (index // columns) * cell_height + 28
        sheet.paste(image, (left, top))
        draw.text(
            (left, (index // columns) * cell_height + 6),
            f"{pid}  {len(xs)} px",
            fill="white",
            font=font,
        )
    sheet.save(PREVIEW_DIR / "small_province_shapes.png")


def main() -> int:
    args = parse_args()
    game_root = args.game_root.resolve()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    offline = args.offline or args.skip_download
    required = [game_root / "map" / name for name in (
        "provinces.bmp", "definition.csv", "default.map", "positions.txt", "area.txt",
        "region.txt", "climate.txt", "continent.txt", "adjacencies.csv",
        "heightmap.bmp", "terrain.bmp", "rivers.bmp", "world_normal.bmp",
    )]
    required.append(game_root / "common" / "tradenodes" / "00_tradenodes.txt")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Missing EU4 1.37.5 inputs:\n" + "\n".join(missing))

    source_rows, colors = parse_definition(game_root / "map" / "definition.csv")
    province_image = Image.open(game_root / "map" / "provinces.bmp").convert("RGB")
    if list(province_image.size) != plan["bitmap_size"]:
        raise RuntimeError(f"Unexpected provinces.bmp size: {province_image.size}")
    vanilla_ids = id_array(province_image, colors)

    source_template = plan["source_dataset"]["province_url"]
    source_payloads = {
        code: load_geojson(code, source_template, offline)
        for code in sorted(set(plan["base_sources"]) | set(plan["projection_anchors"]))
    }
    district_codes = [code for entry in plan["district_overrides"] for code in entry["codes"]]
    district_payloads = {
        code: load_geojson(code, plan["source_dataset"]["district_url"], offline)
        for code in sorted(set(district_codes))
    }

    coefficients, projection_diagnostics = fit_projection(plan, vanilla_ids, province_image.height, source_payloads)
    canvas = Image.new("I", province_image.size, 0)
    for code, pid in plan["base_sources"].items():
        if code == "K74":
            draw = ImageDraw.Draw(canvas)
            for geometry in iter_geometries(source_payloads[code]):
                for polygon in iter_polygons(geometry):
                    target = classify_ryukyu_polygon(polygon, plan["ryukyu_components"])
                    draw_polygon(draw, polygon, target, coefficients, province_image.height, True)
        else:
            draw_payload(canvas, source_payloads[code], int(pid), coefficients, province_image.height)
    for override in plan["district_overrides"]:
        for code in override["codes"]:
            draw_payload(canvas, district_payloads[code], int(override["province"]), coefficients, province_image.height, False)

    editable_old_ids = [int(value) for value in plan["editable_old_ids"]]
    edit_mask = np.isin(vanilla_ids, editable_old_ids)
    rendered = np.asarray(canvas, dtype=np.int32).copy()
    rendered[~edit_mask] = 0
    labels = fill_unlabelled_land(rendered, edit_mask, vanilla_ids)
    ryukyu_fallback = split_stylized_ryukyu(labels, vanilla_ids)
    final_ids = vanilla_ids.copy()
    final_ids[edit_mask] = labels[edit_mask]
    topology_cleanup = clean_new_disconnections(final_ids, vanilla_ids, plan)
    pixel_rebalance = rebalance_small_land_provinces(final_ids, plan)
    island_expansions = expand_small_islands(final_ids, plan)
    cartographic_mask = np.zeros(final_ids.shape, dtype=bool)
    for entry in island_expansions:
        for y, x, _ in entry["added_pixels"]:
            cartographic_mask[int(y), int(x)] = True

    used_colors = set(colors.values())
    for province in plan["new_provinces"]:
        pid = int(province["id"])
        colors[pid] = deterministic_color(pid, used_colors)
    rgb = np.asarray(province_image, dtype=np.uint8).copy()
    id_changes = final_ids != vanilla_ids
    for pid in sorted({int(value) for value in np.unique(final_ids[id_changes])}):
        rgb[id_changes & (final_ids == pid)] = colors[pid]

    expected_ids = set(editable_old_ids) | {int(item["id"]) for item in plan["new_provinces"]}
    missing_pixels = sorted(pid for pid in expected_ids if not np.any(final_ids == pid))
    if missing_pixels:
        raise RuntimeError(f"Generated provinces with no pixels: {missing_pixels}")
    allowed_change_mask = edit_mask | cartographic_mask
    outside_changes = np.any(rgb != np.asarray(province_image), axis=2) & ~allowed_change_mask
    if np.any(outside_changes):
        raise RuntimeError(f"Builder changed {int(outside_changes.sum())} pixels outside the planned map masks")

    map_dir = MOD_ROOT / "map"
    map_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, "RGB").save(map_dir / "provinces.bmp", format="BMP")
    write_definition(map_dir / "definition.csv", source_rows, colors, plan["new_provinces"])
    support_maps = write_cartographic_support_maps(game_root, map_dir, final_ids, island_expansions)

    default_text = (game_root / "map" / "default.map").read_text(encoding="cp1252")
    default_text, count = re.subn(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {plan['max_provinces']}", default_text, count=1)
    if count != 1:
        raise RuntimeError("Could not update max_provinces")
    (map_dir / "default.map").write_text(default_text, encoding="cp1252", newline="\n")
    sea_ids = parse_sea_ids(default_text)

    build_areas(game_root, plan, map_dir / "area.txt")
    build_region(game_root, plan, map_dir / "region.txt")
    child_to_parent = {int(child): int(parent) for child, parent in plan["new_id_parent"].items()}
    build_membership_file(game_root / "map" / "climate.txt", map_dir / "climate.txt", child_to_parent)
    build_membership_file(game_root / "map" / "continent.txt", map_dir / "continent.txt", child_to_parent)

    trade_output = MOD_ROOT / "common" / "tradenodes" / "00_tradenodes.txt"
    trade_output.parent.mkdir(parents=True, exist_ok=True)
    trade_text = (game_root / "common" / "tradenodes" / "00_tradenodes.txt").read_text(encoding="cp1252")
    trade_text = add_to_named_members_block(trade_text, "nippon", [item["id"] for item in plan["new_provinces"]])
    trade_output.write_text(trade_text, encoding="cp1252", newline="\n")

    names = {int(row[0]): row[4] for row in source_rows}
    names.update({int(item["id"]): item["name"] for item in plan["new_provinces"]})
    build_positions(game_root, plan, final_ids, sea_ids, map_dir / "positions.txt", names)
    build_adjacencies(game_root, plan, final_ids, sea_ids, map_dir / "adjacencies.csv")
    render_preview(final_ids, colors, plan)
    render_small_province_preview(final_ids, colors, plan)

    input_hashes = {str(path.relative_to(game_root)).replace("\\", "/"): sha256(path) for path in required}
    pixel_counts = {str(pid): int(np.count_nonzero(final_ids == pid)) for pid in sorted(expected_ids | set(plan["unchanged_hokkaido_ids"]))}
    metadata = {
        "schema_version": 2,
        "game_version": plan["game_version"],
        "plan_sha256": sha256(PLAN_PATH),
        "input_sha256": input_hashes,
        "source_sha256": {path.name: sha256(path) for path in sorted(SOURCE_DIR.glob("*.geojson"))},
        "projection": projection_diagnostics,
        "ryukyu_fallback": ryukyu_fallback,
        "topology_cleanup": topology_cleanup,
        "pixel_rebalance": pixel_rebalance,
        "island_cartographic_expansion": [
            {
                key: value for key, value in entry.items()
                if key not in {"source_pixels", "added_pixels"}
            } | {
                "added_pixel_count": len(entry["added_pixels"]),
                "added_pixels": [
                    {"x": int(x), "y": int(y), "from_sea": int(old_id)}
                    for y, x, old_id in entry["added_pixels"]
                ],
            }
            for entry in island_expansions
        ],
        "cartographic_support_maps": support_maps,
        "edit_mask_pixels": int(edit_mask.sum()),
        "cartographic_expansion_pixels": int(cartographic_mask.sum()),
        "changed_pixels": int(np.any(rgb != np.asarray(province_image), axis=2).sum()),
        "outside_edit_mask_changes": int(outside_changes.sum()),
        "province_pixel_counts": pixel_counts,
    }
    (SCRIPT_DIR / "generated_manifest.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Built {len(expected_ids) + len(plan['unchanged_hokkaido_ids'])} Japanese provinces")
    print(f"Projection RMSE: {projection_diagnostics['rmse_pixels']} px")
    print(f"Changed province-map pixels: {metadata['changed_pixels']}")
    print(f"Cartographic island growth: {metadata['cartographic_expansion_pixels']} pixels")
    print(f"Preview: {PREVIEW_DIR / 'japan_88_ids.png'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
