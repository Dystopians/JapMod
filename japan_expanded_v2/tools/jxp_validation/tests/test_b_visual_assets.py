from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageStat

from jxp_validation.clausewitz import Object, Scalar, parse_file


MOD_ROOT = Path(__file__).resolve().parents[3]
TOOL_ROOT = MOD_ROOT / "tools" / "jxp_b_visual_assets"
PLAN_PATH = TOOL_ROOT / "asset_plan.json"
EVENT_ROOT = MOD_ROOT / "gfx" / "event_pictures" / "jxp_b"
GFX_PATH = MOD_ROOT / "interface" / "jxp_b_event_pictures.gfx"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_scalar(obj: Object, key: str) -> str | None:
    for entry in obj.entries:
        if entry.key == key and isinstance(entry.value, Scalar):
            return entry.value.text
    return None


class AgentBVisualAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        cls.entries = cls.plan["events"]
        cls.assignments = {
            event_id: f"{entry['asset']}_eventPicture"
            for entry in cls.entries
            for event_id in entry["event_ids"]
        }

    def test_plan_has_twelve_unique_used_event_families(self) -> None:
        assets = [entry["asset"] for entry in self.entries]
        event_ids = [event_id for entry in self.entries for event_id in entry["event_ids"]]
        self.assertEqual(12, len(assets))
        self.assertEqual(len(assets), len(set(assets)))
        self.assertEqual(len(event_ids), len(set(event_ids)))
        self.assertTrue(all(entry["prompt"] and entry["theme"] for entry in self.entries))
        self.assertTrue(all(entry["event_ids"] for entry in self.entries))

    def test_reserved_ui_sprites_are_classified_instead_of_stretched_into_events(self) -> None:
        registry = (MOD_ROOT / "interface" / "jxp_government_mechanics.gfx").read_text(
            encoding="utf-8-sig"
        )
        reserved = self.plan["reserved_non_event_sprites"]
        self.assertEqual(3, len(reserved))
        for entry in reserved:
            self.assertIn(f'name = "{entry["sprite"]}"', registry)
            path = MOD_ROOT / entry["file"]
            with Image.open(path) as image:
                self.assertEqual((82, 82), image.size)
            self.assertNotIn(entry["sprite"], set(self.assignments.values()))
            self.assertIn("保留", entry["disposition"])

    def test_imagegen_sources_are_large_distinct_and_nonblank(self) -> None:
        hashes: set[str] = set()
        expected_names = set()
        for entry in self.entries:
            source = EVENT_ROOT / "source" / f"{entry['asset']}_imagegen.png"
            expected_names.add(source.name)
            self.assertTrue(source.is_file(), source)
            with Image.open(source) as image:
                self.assertGreaterEqual(image.width, 1024)
                self.assertGreaterEqual(image.height, 512)
                extrema = ImageStat.Stat(image.convert("L").resize((128, 128))).extrema[0]
                self.assertGreater(extrema[1] - extrema[0], 80, source)
            hashes.add(sha256(source))
        self.assertEqual(12, len(hashes))
        actual_names = {
            path.name for path in (EVENT_ROOT / "source").glob("*_imagegen.png")
        }
        self.assertEqual(expected_names, actual_names)

    def test_dds_files_are_exact_eu4_event_picture_class(self) -> None:
        hashes: set[str] = set()
        expected_names = {f"{entry['asset']}.dds" for entry in self.entries}
        for entry in self.entries:
            path = EVENT_ROOT / f"{entry['asset']}.dds"
            payload = path.read_bytes()
            self.assertEqual(b"DDS ", payload[:4], path)
            self.assertEqual(132, struct.unpack_from("<I", payload, 12)[0], path)
            self.assertEqual(512, struct.unpack_from("<I", payload, 16)[0], path)
            self.assertEqual(b"DXT1", payload[84:88], path)
            hashes.add(hashlib.sha256(payload).hexdigest())
        self.assertEqual(12, len(hashes))
        self.assertEqual(expected_names, {path.name for path in EVENT_ROOT.glob("*.dds")})

    def test_gfx_registry_is_complete_and_has_no_orphan_event_sprite(self) -> None:
        payload = GFX_PATH.read_text(encoding="utf-8-sig")
        expected = {f"{entry['asset']}_eventPicture" for entry in self.entries}
        registered = {
            token.strip('"')
            for token in payload.split()
            if token.strip('"').startswith("jxp_b_")
            and token.strip('"').endswith("_eventPicture")
        }
        self.assertEqual(expected, registered)
        for entry in self.entries:
            asset = entry["asset"]
            self.assertIn(
                f'texturefile = "gfx/event_pictures/jxp_b/{asset}.dds"', payload
            )
        referenced = set(self.assignments.values())
        self.assertEqual(registered, referenced)

    def test_every_planned_visible_event_uses_its_assigned_picture(self) -> None:
        found: dict[str, list[tuple[str | None, str | None, Path]]] = {}
        unexpected_custom_pictures: list[tuple[str | None, str, Path]] = []
        for path in sorted((MOD_ROOT / "events").glob("*.txt")):
            document = parse_file(path)
            for entry in document.root.entries:
                if entry.key not in {"country_event", "province_event"} or not isinstance(
                    entry.value, Object
                ):
                    continue
                event_id = direct_scalar(entry.value, "id")
                picture = direct_scalar(entry.value, "picture")
                if event_id in self.assignments:
                    found.setdefault(event_id, []).append(
                        (picture, direct_scalar(entry.value, "hidden"), path)
                    )
                if (
                    picture is not None
                    and picture.startswith("jxp_b_")
                    and picture.endswith("_eventPicture")
                    and event_id not in self.assignments
                ):
                    unexpected_custom_pictures.append((event_id, picture, path))
        self.assertEqual(set(self.assignments), set(found))
        self.assertEqual([], unexpected_custom_pictures)
        for event_id, expected_picture in self.assignments.items():
            self.assertEqual(1, len(found[event_id]), f"duplicate definition for {event_id}")
            picture, hidden, path = found[event_id][0]
            self.assertNotEqual("yes", hidden, f"{event_id} in {path}")
            self.assertEqual(expected_picture, picture, f"{event_id} in {path}")

    def test_manifest_matches_files_and_generator_check_is_clean(self) -> None:
        manifest = json.loads(
            (TOOL_ROOT / "generated_asset_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.plan["version"], manifest["plan_version"])
        self.assertEqual(sha256(PLAN_PATH), manifest["plan_sha256"])
        self.assertEqual({entry["asset"] for entry in self.entries}, set(manifest["events"]))
        for asset, record in manifest["events"].items():
            self.assertEqual(record["sha256"], sha256(MOD_ROOT / record["file"]))
            self.assertEqual(
                record["source_sha256"], sha256(MOD_ROOT / record["source"])
            )
            self.assertEqual(
                record["preview_sha256"], sha256(MOD_ROOT / record["preview"])
            )
        completed = subprocess.run(
            [sys.executable, str(TOOL_ROOT / "build_assets.py"), "--check"],
            cwd=MOD_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
