#!/usr/bin/env python3
"""Validate ImageGen sources and EU4-ready JXP map visual assets."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageStat


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
PLAN_PATH = MOD_ROOT / "tools" / "jxp_asset_builder" / "asset_plan.json"
GFX_PATH = MOD_ROOT / "interface" / "jxp_map_assets.gfx"


class Audit:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def error(self, message): self.errors.append(message)
    def warning(self, message): self.warnings.append(message)
    def note(self, message): self.notes.append(message)

    def finish(self):
        for message in self.notes: print(f"NOTE: {message}")
        for message in self.warnings: print(f"WARNING: {message}")
        for message in self.errors: print(f"ERROR: {message}")
        print(f"SUMMARY: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


def image_hash(image: Image.Image) -> str:
    gray = image.convert("L").resize((16, 16), Image.Resampling.LANCZOS)
    values = np.asarray(gray, dtype=np.float32)
    bits = values >= values.mean()
    return "".join("1" if bit else "0" for bit in bits.flat)


def inspect_tga(path: Path, audit: Audit):
    data = path.read_bytes()
    if len(data) < 18:
        audit.error(f"TGA header is truncated: {path}")
        return
    width = int.from_bytes(data[12:14], "little")
    height = int.from_bytes(data[14:16], "little")
    if data[1] != 0 or data[2] not in (2, 10) or (width, height) != (128, 128) or data[16] != 24:
        audit.error(f"Flag TGA format mismatch: {path} type={data[2]} size={width}x{height} depth={data[16]}")


def inspect_dds(path: Path, expected_size: tuple[int, int], fourcc: bytes | None, audit: Audit):
    data = path.read_bytes()
    if len(data) < 128 or data[:4] != b"DDS ":
        audit.error(f"DDS header is invalid: {path}")
        return
    height = int.from_bytes(data[12:16], "little")
    width = int.from_bytes(data[16:20], "little")
    actual_fourcc = data[84:88]
    if (width, height) != expected_size:
        audit.error(f"DDS dimensions mismatch: {path} is {width}x{height}, expected {expected_size[0]}x{expected_size[1]}")
    if fourcc is not None and actual_fourcc != fourcc:
        audit.error(f"DDS compression mismatch: {path} has {actual_fourcc!r}, expected {fourcc!r}")


def check_nonblank(path: Path, audit: Audit, minimum_stddev=8.0):
    image = Image.open(path).convert("RGB")
    if max(ImageStat.Stat(image).stddev) < minimum_stddev:
        audit.error(f"Asset appears blank or nearly uniform: {path}")
    return image


def main():
    audit = Audit()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    seen_sources = {}
    seen_final_hashes = {}

    thumbnail_source = MOD_ROOT / plan["thumbnail"]["source"]
    thumbnail_final = MOD_ROOT / plan["thumbnail"]["file"]
    if not thumbnail_source.exists(): audit.error(f"Missing thumbnail ImageGen source: {thumbnail_source}")
    if not thumbnail_final.exists(): audit.error(f"Missing launcher thumbnail: {thumbnail_final}")
    if thumbnail_source.exists() and thumbnail_final.exists():
        source_image = Image.open(thumbnail_source)
        final_image = check_nonblank(thumbnail_final, audit, 12.0)
        if source_image.width < 512 or source_image.height < 512: audit.error(f"Thumbnail source below 512px: {thumbnail_source}")
        if final_image.size != (plan["thumbnail"]["width"], plan["thumbnail"]["height"]): audit.error(f"Thumbnail dimensions mismatch: {final_image.size}")
        if Image.open(thumbnail_final).format != "PNG": audit.error("Launcher thumbnail is not PNG")
        descriptor = (MOD_ROOT / "descriptor.mod").read_text(encoding="utf-8-sig")
        if f'picture="{plan["thumbnail"]["file"]}"' not in descriptor: audit.error("descriptor.mod does not reference the generated thumbnail")

    for entry in plan["flags"]:
        tag = entry["tag"]
        source = MOD_ROOT / "gfx" / "flags" / "source" / f"{tag}_source.png"
        final = MOD_ROOT / "gfx" / "flags" / f"{tag}.tga"
        for path in (source, final):
            if not path.exists(): audit.error(f"Missing flag asset: {path}")
        if not source.exists() or not final.exists(): continue
        source_image = Image.open(source)
        if source_image.width < 512 or source_image.height < 512: audit.error(f"Flag source below 512px: {source}")
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if source_digest in seen_sources: audit.error(f"Duplicate ImageGen flag source: {tag} and {seen_sources[source_digest]}")
        seen_sources[source_digest] = tag
        inspect_tga(final, audit)
        image = check_nonblank(final, audit)
        border = np.concatenate((np.asarray(image)[:4].reshape(-1, 3), np.asarray(image)[-4:].reshape(-1, 3), np.asarray(image)[:, :4].reshape(-1, 3), np.asarray(image)[:, -4:].reshape(-1, 3)))
        if float(border.std(axis=0).max()) > 2.0: audit.error(f"Flag field is not flat at the border: {tag}")
        digest = image_hash(image)
        if digest in seen_final_hashes: audit.error(f"Perceptually duplicate final flag: {tag} and {seen_final_hashes[digest]}")
        seen_final_hashes[digest] = tag

    mission_hashes = {}
    for entry in plan["missions"]:
        mission_id = entry["id"]
        source = MOD_ROOT / "gfx" / "interface" / "missions" / "source" / f"{mission_id}_imagegen.png"
        final = MOD_ROOT / "gfx" / "interface" / "missions" / f"{mission_id}.dds"
        if not source.exists(): audit.error(f"Missing mission ImageGen source: {source}")
        if not final.exists(): audit.error(f"Missing mission DDS: {final}")
        if not source.exists() or not final.exists(): continue
        inspect_dds(final, (59, 63), None, audit)
        image = Image.open(final).convert("RGBA")
        alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
        coverage = float((alpha > 16).mean())
        if coverage < 0.99: audit.error(f"Mission icon is not fully opaque like vanilla: {mission_id} = {coverage:.3f}")
        if any(alpha[y, x] < 250 for x, y in ((0, 0), (58, 0), (0, 62), (58, 62))): audit.error(f"Mission icon corners are unexpectedly transparent: {mission_id}")
        digest = image_hash(image)
        if digest in mission_hashes: audit.error(f"Perceptually duplicate mission icon: {mission_id} and {mission_hashes[digest]}")
        mission_hashes[digest] = mission_id

    event_hashes = {}
    for entry in plan["events"]:
        asset = entry["asset"]
        source = MOD_ROOT / "gfx" / "event_pictures" / "jxp_map" / "source" / f"{asset}_imagegen.png"
        final = MOD_ROOT / "gfx" / "event_pictures" / "jxp_map" / f"{asset}.dds"
        if not source.exists(): audit.error(f"Missing event ImageGen source: {source}")
        if not final.exists(): audit.error(f"Missing event DDS: {final}")
        if not source.exists() or not final.exists(): continue
        inspect_dds(final, (512, 132), b"DXT1", audit)
        image = check_nonblank(final, audit, 10.0)
        digest = image_hash(image)
        if digest in event_hashes: audit.error(f"Perceptually duplicate event picture: {asset} and {event_hashes[digest]}")
        event_hashes[digest] = asset

    if not GFX_PATH.exists():
        audit.error(f"Missing GFX registry: {GFX_PATH}")
    else:
        gfx = GFX_PATH.read_text(encoding="utf-8")
        registered = set(re.findall(r'(?m)^\s*name\s*=\s*"([^"]+)"', gfx))
        expected = {entry["id"] for entry in plan["missions"]} | {f'{entry["asset"]}_eventPicture' for entry in plan["events"]}
        missing = sorted(expected - registered)
        extra = sorted(registered - expected)
        if missing: audit.error(f"GFX registry is missing sprites: {missing}")
        if extra: audit.error(f"GFX registry has unplanned sprites: {extra}")

    mission_text = (MOD_ROOT / "missions" / "jxp_map_new_daimyo_missions.txt").read_text(encoding="utf-8")
    mission_refs = set(re.findall(r'(?m)^\s*icon\s*=\s*(jxp_map_mission_[a-z0-9_]+)', mission_text))
    expected_missions = {entry["id"] for entry in plan["missions"]}
    if mission_refs != expected_missions: audit.error(f"Mission icon references do not match plan: missing={sorted(expected_missions - mission_refs)}, extra={sorted(mission_refs - expected_missions)}")

    event_text = (MOD_ROOT / "events" / "jxp_map_events.txt").read_text(encoding="utf-8")
    event_refs = set(re.findall(r'(?m)^\s*picture\s*=\s*(jxp_map_[a-z0-9_]+_eventPicture)', event_text))
    expected_events = {f'{entry["asset"]}_eventPicture' for entry in plan["events"]}
    if event_refs != expected_events: audit.error(f"Event picture references do not match plan: missing={sorted(expected_events - event_refs)}, extra={sorted(event_refs - expected_events)}")

    audit.note(f"Asset inventory: 1 thumbnail, {len(plan['flags'])} flags, {len(plan['missions'])} mission icons, {len(plan['events'])} event pictures")
    audit.note("Flag style gate: flat border fields, unique ImageGen sources, 128x128 24-bit TGA")
    audit.note("Mission/event format gate: opaque 59x63 RGBA DDS and 512x132 DXT1 DDS")
    return audit.finish()


if __name__ == "__main__":
    raise SystemExit(main())
