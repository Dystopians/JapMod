#!/usr/bin/env python3
"""Build EU4-ready flags, mission icons, event pictures, previews, and GFX."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
PLAN_PATH = SCRIPT_DIR / "asset_plan.json"
FLAG_SOURCE = MOD_ROOT / "gfx" / "flags" / "source"
FLAG_PREVIEW = MOD_ROOT / "gfx" / "flags" / "preview"
MISSION_ROOT = MOD_ROOT / "gfx" / "interface" / "missions"
MISSION_SOURCE = MISSION_ROOT / "source"
MISSION_ALPHA = MISSION_SOURCE / "alpha"
MISSION_PREVIEW = MISSION_SOURCE / "preview"
EVENT_ROOT = MOD_ROOT / "gfx" / "event_pictures" / "jxp_map"
EVENT_SOURCE = EVENT_ROOT / "source"
EVENT_PREVIEW = EVENT_SOURCE / "preview"
PREVIEW_ROOT = SCRIPT_DIR / "previews"
MANIFEST_PATH = SCRIPT_DIR / "generated_asset_manifest.json"
GFX_PATH = MOD_ROOT / "interface" / "jxp_map_assets.gfx"
THUMBNAIL_SOURCE = SCRIPT_DIR / "source" / "thumbnail_imagegen.png"
THUMBNAIL_PATH = MOD_ROOT / "thumbnail.png"


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_source(path: Path, minimum: tuple[int, int] = (512, 512)) -> Image.Image:
    if not path.exists():
        raise RuntimeError(f"Missing ImageGen source: {path}")
    image = Image.open(path)
    if image.width < minimum[0] or image.height < minimum[1]:
        raise RuntimeError(f"ImageGen source is too small: {path} is {image.size}")
    return image


def centered_flag_mask(image: Image.Image) -> Image.Image:
    fitted = ImageOps.fit(image.convert("RGB"), (768, 768), method=Image.Resampling.LANCZOS)
    array = np.asarray(fitted, dtype=np.float32)
    border = np.concatenate((array[:48].reshape(-1, 3), array[-48:].reshape(-1, 3), array[:, :48].reshape(-1, 3), array[:, -48:].reshape(-1, 3)))
    background = np.median(border, axis=0)
    distance = np.linalg.norm(array - background.reshape(1, 1, 3), axis=2)
    mask = Image.fromarray(np.where(distance >= 42.0, 255, 0).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MedianFilter(7))
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    guard = Image.new("L", mask.size, 0)
    ImageDraw.Draw(guard).rounded_rectangle((46, 46, 721, 721), radius=24, fill=255)
    mask = Image.composite(mask, Image.new("L", mask.size, 0), guard)
    bbox = mask.getbbox()
    if not bbox:
        raise RuntimeError("Could not isolate a centered mon from the ImageGen source")
    cropped = mask.crop(bbox)
    if cropped.width * cropped.height < 768 * 768 * 0.025:
        raise RuntimeError("Isolated mon is too small")
    cropped.thumbnail((560, 560), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (768, 768), 0)
    canvas.paste(cropped, ((768 - cropped.width) // 2, (768 - cropped.height) // 2))
    return canvas


def build_flag(entry: dict) -> dict:
    tag = entry["tag"]
    source_path = FLAG_SOURCE / f"{tag}_source.png"
    image = require_source(source_path)
    mask = centered_flag_mask(image)
    background = np.array(rgb(entry["background"]), dtype=np.float32)
    ink = np.array(rgb(entry["ink"]), dtype=np.float32)
    alpha = np.asarray(mask, dtype=np.float32)[..., None] / 255.0
    rendered = background.reshape(1, 1, 3) * (1.0 - alpha) + ink.reshape(1, 1, 3) * alpha
    rendered = Image.fromarray(np.clip(rendered, 0, 255).astype(np.uint8), "RGB")
    final = rendered.resize((128, 128), Image.Resampling.LANCZOS)
    final_path = MOD_ROOT / "gfx" / "flags" / f"{tag}.tga"
    preview_path = FLAG_PREVIEW / f"{tag}.png"
    final.save(final_path, format="TGA")
    final.save(preview_path)
    return {"source": str(source_path.relative_to(MOD_ROOT)), "file": str(final_path.relative_to(MOD_ROOT)), "sha256": sha256(final_path)}


def build_mission(entry: dict) -> dict:
    mission_id = entry["id"]
    source_path = MISSION_SOURCE / f"{mission_id}_imagegen.png"
    source = require_source(source_path)
    final = ImageOps.fit(source.convert("RGBA"), (59, 63), method=Image.Resampling.LANCZOS)
    final_path = MISSION_ROOT / f"{mission_id}.dds"
    preview_path = MISSION_PREVIEW / f"{mission_id}.png"
    final.save(final_path, format="DDS")
    final.save(preview_path)
    return {"source": str(source_path.relative_to(MOD_ROOT)), "file": str(final_path.relative_to(MOD_ROOT)), "sha256": sha256(final_path)}


def crop_event_band(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    target_ratio = 512 / 132
    current_ratio = image.width / image.height
    if current_ratio < target_ratio:
        crop_height = int(round(image.width / target_ratio))
        top = max(0, (image.height - crop_height) // 2)
        image = image.crop((0, top, image.width, top + crop_height))
    else:
        crop_width = int(round(image.height * target_ratio))
        left = max(0, (image.width - crop_width) // 2)
        image = image.crop((left, 0, left + crop_width, image.height))
    return image.resize((512, 132), Image.Resampling.LANCZOS)


def build_event(entry: dict) -> dict:
    asset = entry["asset"]
    source_path = EVENT_SOURCE / f"{asset}_imagegen.png"
    image = require_source(source_path)
    final = crop_event_band(image)
    final_path = EVENT_ROOT / f"{asset}.dds"
    preview_path = EVENT_PREVIEW / f"{asset}.png"
    final.save(final_path, format="DDS", pixel_format="DXT1")
    final.save(preview_path)
    return {"source": str(source_path.relative_to(MOD_ROOT)), "file": str(final_path.relative_to(MOD_ROOT)), "sha256": sha256(final_path)}


def build_thumbnail(entry: dict) -> dict:
    source_path = MOD_ROOT / entry["source"]
    source = require_source(source_path)
    final = ImageOps.fit(
        source.convert("RGB"),
        (entry["width"], entry["height"]),
        method=Image.Resampling.LANCZOS,
    )
    final_path = MOD_ROOT / entry["file"]
    final.save(final_path, format="PNG", optimize=True)
    return {
        "source": str(source_path.relative_to(MOD_ROOT)),
        "file": str(final_path.relative_to(MOD_ROOT)),
        "sha256": sha256(final_path),
    }


def write_gfx(plan: dict):
    lines = ["spriteTypes = {", ""]
    for mission in plan["missions"]:
        mission_id = mission["id"]
        lines.extend([
            "\tspriteType = {",
            f'\t\tname = "{mission_id}"',
            f'\t\ttexturefile = "gfx/interface/missions/{mission_id}.dds"',
            "\t}",
            "",
        ])
    for event in plan["events"]:
        sprite = f'{event["asset"]}_eventPicture'
        lines.extend([
            "\tspriteType = {",
            f'\t\tname = "{sprite}"',
            f'\t\ttexturefile = "gfx/event_pictures/jxp_map/{event["asset"]}.dds"',
            "\t\talwaystransparent = yes",
            "\t}",
            "",
        ])
    lines.append("}")
    GFX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def labeled_sheet(items: list[tuple[str, Image.Image]], columns: int, cell: tuple[int, int], path: Path, background=(28, 31, 34)):
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell[0], rows * cell[1]), background)
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(items):
        x = (index % columns) * cell[0]
        y = (index // columns) * cell[1]
        image = image.convert("RGBA")
        max_width, max_height = cell[0] - 20, cell[1] - 28
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        px = x + (cell[0] - image.width) // 2
        py = y + 6 + (max_height - image.height) // 2
        sheet.paste(image.convert("RGB"), (px, py), image.getchannel("A"))
        draw.text((x + 8, y + cell[1] - 18), label, fill=(235, 235, 230))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    for directory in (FLAG_SOURCE, FLAG_PREVIEW, MISSION_SOURCE, MISSION_ALPHA, MISSION_PREVIEW, EVENT_SOURCE, EVENT_PREVIEW, PREVIEW_ROOT, GFX_PATH.parent):
        directory.mkdir(parents=True, exist_ok=True)

    manifest = {
        "plan_version": plan["version"],
        "thumbnail": build_thumbnail(plan["thumbnail"]),
        "flags": {},
        "missions": {},
        "events": {},
    }
    for entry in plan["flags"]:
        manifest["flags"][entry["tag"]] = build_flag(entry)
    for entry in plan["missions"]:
        manifest["missions"][entry["id"]] = build_mission(entry)
    for entry in plan["events"]:
        manifest["events"][entry["event"]] = build_event(entry)

    write_gfx(plan)
    labeled_sheet([(entry["tag"], Image.open(FLAG_PREVIEW / f'{entry["tag"]}.png')) for entry in plan["flags"]], 6, (160, 156), PREVIEW_ROOT / "flags_imagegen_contact_sheet.png")
    labeled_sheet([(entry["id"].replace("jxp_map_mission_", ""), Image.open(MISSION_PREVIEW / f'{entry["id"]}.png')) for entry in plan["missions"]], 5, (170, 118), PREVIEW_ROOT / "mission_icons_contact_sheet.png")
    labeled_sheet([(entry["event"], Image.open(EVENT_PREVIEW / f'{entry["asset"]}.png')) for entry in plan["events"]], 2, (540, 174), PREVIEW_ROOT / "event_pictures_contact_sheet.png")
    manifest["gfx"] = {"file": str(GFX_PATH.relative_to(MOD_ROOT)), "sha256": sha256(GFX_PATH)}
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built 1 thumbnail, {len(plan['flags'])} flags, {len(plan['missions'])} mission icons, and {len(plan['events'])} event pictures")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
