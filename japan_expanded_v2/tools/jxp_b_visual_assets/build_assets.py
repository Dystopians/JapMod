#!/usr/bin/env python3
"""Build and reproducibly verify Agent B custom EU4 event pictures."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
PLAN_PATH = SCRIPT_DIR / "asset_plan.json"
EVENT_ROOT = MOD_ROOT / "gfx" / "event_pictures" / "jxp_b"
EVENT_SOURCE = EVENT_ROOT / "source"
EVENT_PREVIEW = EVENT_SOURCE / "preview"
PREVIEW_ROOT = SCRIPT_DIR / "previews"
CONTACT_SHEET = PREVIEW_ROOT / "event_pictures_contact_sheet.png"
GFX_PATH = MOD_ROOT / "interface" / "jxp_b_event_pictures.gfx"
MANIFEST_PATH = SCRIPT_DIR / "generated_asset_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan() -> dict:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    events = plan.get("events", [])
    assets = [entry.get("asset") for entry in events]
    if not events or len(assets) != len(set(assets)) or any(not asset for asset in assets):
        raise RuntimeError("asset_plan.json must contain unique, non-empty event assets")
    event_ids = [event_id for entry in events for event_id in entry.get("event_ids", [])]
    if any(not entry.get("event_ids") for entry in events):
        raise RuntimeError("every event asset must be assigned to at least one event")
    if len(event_ids) != len(set(event_ids)):
        raise RuntimeError("an event id is assigned to more than one event picture")
    return plan


def require_source(asset: str) -> tuple[Path, Image.Image]:
    path = EVENT_SOURCE / f"{asset}_imagegen.png"
    if not path.is_file():
        raise RuntimeError(f"missing ImageGen source: {path}")
    image = Image.open(path)
    image.load()
    if image.width < 1024 or image.height < 512:
        image.close()
        raise RuntimeError(f"ImageGen source is too small: {path} is {image.size}")
    return path, image


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


def gfx_payload(plan: dict) -> str:
    lines = ["spriteTypes = {", ""]
    for entry in plan["events"]:
        asset = entry["asset"]
        lines.extend(
            [
                "\tspriteType = {",
                f'\t\tname = "{asset}_eventPicture"',
                f'\t\ttexturefile = "gfx/event_pictures/jxp_b/{asset}.dds"',
                "\t\talwaystransparent = yes",
                "\t}",
                "",
            ]
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_contact_sheet(plan: dict, preview_root: Path, target: Path) -> None:
    columns = 2
    cell_width, cell_height = 540, 174
    rows = (len(plan["events"]) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (28, 31, 34))
    draw = ImageDraw.Draw(sheet)
    for index, entry in enumerate(plan["events"]):
        asset = entry["asset"]
        with Image.open(preview_root / f"{asset}.png") as source:
            image = source.convert("RGB")
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        sheet.paste(image, (x + 14, y + 10))
        draw.text((x + 14, y + 148), asset.removeprefix("jxp_b_"), fill=(235, 235, 230))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, format="PNG", optimize=True)


def build(plan: dict, output_mod_root: Path, output_script_dir: Path) -> list[Path]:
    output_event_root = output_mod_root / "gfx" / "event_pictures" / "jxp_b"
    output_preview = output_event_root / "source" / "preview"
    output_gfx = output_mod_root / "interface" / "jxp_b_event_pictures.gfx"
    output_contact = output_script_dir / "previews" / "event_pictures_contact_sheet.png"
    output_manifest = output_script_dir / "generated_asset_manifest.json"
    output_event_root.mkdir(parents=True, exist_ok=True)
    output_preview.mkdir(parents=True, exist_ok=True)
    output_gfx.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "plan_version": plan["version"],
        "plan_sha256": sha256(PLAN_PATH),
        "generator": plan["generator"],
        "events": {},
    }
    generated: list[Path] = []
    for entry in plan["events"]:
        asset = entry["asset"]
        source_path, source = require_source(asset)
        try:
            final = crop_event_band(source)
        finally:
            source.close()
        final_path = output_event_root / f"{asset}.dds"
        preview_path = output_preview / f"{asset}.png"
        final.save(final_path, format="DDS", pixel_format="DXT1")
        final.save(preview_path, format="PNG", optimize=True)
        generated.extend((final_path, preview_path))
        manifest["events"][asset] = {
            "source": source_path.relative_to(MOD_ROOT).as_posix(),
            "source_sha256": sha256(source_path),
            "file": final_path.relative_to(output_mod_root).as_posix(),
            "sha256": sha256(final_path),
            "preview": preview_path.relative_to(output_mod_root).as_posix(),
            "preview_sha256": sha256(preview_path),
            "event_ids": entry["event_ids"],
        }

    output_gfx.write_text(gfx_payload(plan), encoding="utf-8", newline="\n")
    write_contact_sheet(plan, output_preview, output_contact)
    generated.extend((output_gfx, output_contact))
    manifest["gfx"] = {
        "file": output_gfx.relative_to(output_mod_root).as_posix(),
        "sha256": sha256(output_gfx),
    }
    manifest["contact_sheet"] = {
        "file": output_contact.relative_to(output_script_dir).as_posix(),
        "sha256": sha256(output_contact),
    }
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    generated.append(output_manifest)
    return generated


def check(plan: dict) -> None:
    temp_root = SCRIPT_DIR / ".tmp_check"
    if temp_root.parent.resolve() != SCRIPT_DIR.resolve():
        raise RuntimeError(f"refusing unsafe temporary path: {temp_root}")
    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir()
    try:
        temp_mod = temp_root / "japan_expanded_v2"
        temp_script = temp_mod / "tools" / "jxp_b_visual_assets"
        generated = build(plan, temp_mod, temp_script)
        for expected in generated:
            if expected.is_relative_to(temp_mod):
                actual = MOD_ROOT / expected.relative_to(temp_mod)
            else:
                raise RuntimeError(f"generated file escaped temporary mod root: {expected}")
            if not actual.is_file():
                raise RuntimeError(f"generated asset is missing: {actual}")
            if actual.read_bytes() != expected.read_bytes():
                raise RuntimeError(f"generated asset is stale: {actual}")
    finally:
        if temp_root.exists():
            shutil.rmtree(temp_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="rebuild in a temporary directory and compare bytes"
    )
    args = parser.parse_args()
    plan = load_plan()
    if args.check:
        check(plan)
        print(f"Verified {len(plan['events'])} reproducible Agent B event pictures")
    else:
        generated = build(plan, MOD_ROOT, SCRIPT_DIR)
        print(f"Built {len(plan['events'])} Agent B event pictures ({len(generated)} files)")
        print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
