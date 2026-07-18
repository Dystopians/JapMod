from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest


MOD_ROOT = Path(__file__).resolve().parents[3]
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
BUILDER_PATH = (
    MOD_ROOT
    / "tools"
    / "jxp_b_province_name_builder"
    / "build_america_province_names.py"
)
PLAN_PATH = BUILDER_PATH.with_name("america_japanese_names.json")
ACTIVE_PATH = MOD_ROOT / "common" / "province_names" / "japanese_g.txt"
SOURCE_PATH = (
    MOD_ROOT
    / "tools"
    / "jxp_b_province_name_builder"
    / "generated_japanese_g_america_utf8_source.txt"
)


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "_jxp_b_america_province_names",
        BUILDER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load province-name builder: {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()
ENCODER = BUILDER._load_encoder()


def _id_hash(ids: set[int]) -> str:
    payload = ",".join(str(value) for value in sorted(ids)).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


class JapaneseAmericaProvinceNameTests(unittest.TestCase):
    def test_live_registry_matches_pinned_eu4_1375_inputs(self) -> None:
        expected_source, expected, stats = BUILDER.build_artifacts(GAME_ROOT)
        self.assertEqual(expected, ACTIVE_PATH.read_bytes())
        self.assertEqual(expected_source, SOURCE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(11, stats["regions"])
        self.assertEqual(778, stats["american_provinces"])
        self.assertEqual(2, stats["inherited_vanilla"])
        self.assertEqual(102, stats["curated_exonyms"])
        self.assertEqual(674, stats["generated_regional_names"])
        self.assertEqual(776, stats["added_entries"])
        self.assertEqual(778, stats["han_names"])
        self.assertEqual("EU4SpecialEscape-CP1252-no-BOM", stats["encoding"])

    def test_registry_covers_every_american_colonial_province_once(self) -> None:
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        active = ACTIVE_PATH.read_bytes()
        self.assertFalse(active.startswith(b"\xef\xbb\xbf"))
        readable = ENCODER.decode_gameplay_bytes(active)
        self.assertEqual(SOURCE_PATH.read_text(encoding="utf-8"), readable)
        marker = BUILDER.MARKER.encode("ascii")
        self.assertEqual(1, active.count(marker))
        vanilla, generated = readable.split(BUILDER.MARKER, 1)
        pinned_vanilla = (
            GAME_ROOT / "common/province_names/japanese_g.txt"
        ).read_bytes().decode("cp1252")
        for raw_id, han_name in plan["preserved_han_names"].items():
            pinned_vanilla = re.sub(
                rf'^(\s*{raw_id}\s*=\s*)"[^"]+"',
                lambda match: f'{match.group(1)}"{han_name}"',
                pinned_vanilla,
                count=1,
                flags=re.MULTILINE,
            )
        self.assertEqual(pinned_vanilla.rstrip("\r\n"), vanilla.rstrip("\r\n"))

        entries = re.findall(
            r'^\s*(\d+)\s*=\s*"([^"]+)"',
            generated,
            re.MULTILINE,
        )
        ids = [int(raw_id) for raw_id, _ in entries]
        names = [name for _, name in entries]
        self.assertEqual(776, len(ids))
        self.assertEqual(776, len(set(ids)))
        self.assertEqual(plan["added_id_set_sha256"], _id_hash(set(ids)))
        all_ids = set(ids) | set(plan["preserved_vanilla_ids"])
        self.assertEqual(plan["america_id_set_sha256"], _id_hash(all_ids))
        self.assertEqual(len(names), len({name.casefold() for name in names}))
        self.assertTrue(all(BUILDER.VALID_HAN_NAME.fullmatch(name) for name in names))

        headers = re.findall(
            r"^# JXP_REGION (colonial_[a-z_]+) "
            r"total=(\d+) inherited=(\d+) added=(\d+)$",
            generated,
            flags=re.MULTILINE,
        )
        self.assertEqual(11, len(headers))
        self.assertEqual(
            plan["expected_region_counts"],
            {key: int(total) for key, total, _, _ in headers},
        )
        self.assertEqual(2, sum(int(inherited) for _, _, inherited, _ in headers))
        self.assertEqual(776, sum(int(added) for _, _, _, added in headers))

    def test_curated_exonyms_and_vanilla_new_world_names_are_stable(self) -> None:
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        active = ACTIVE_PATH.read_bytes()
        text = ENCODER.decode_gameplay_bytes(active)
        direct_entries = {
            int(raw_id): name
            for raw_id, name in re.findall(
                r'^\s*(\d+)\s*=\s*"([^"]+)"',
                text,
                flags=re.MULTILINE,
            )
        }
        for raw_id, name in plan["preserved_han_names"].items():
            self.assertEqual(name, direct_entries[int(raw_id)])
        for raw_id, name in plan["curated_han_names"].items():
            self.assertEqual(name, direct_entries[int(raw_id)])
        self.assertEqual("新江户", direct_entries[965])
        self.assertEqual("华府", direct_entries[953])
        self.assertEqual("桑港", direct_entries[4637])
        self.assertEqual("罗府", direct_entries[868])
        self.assertEqual("新长崎", direct_entries[763])
        self.assertNotIn("新江户".encode("utf-8"), active)

        american_ids = set(plan["preserved_vanilla_ids"]) | {
            int(value) for value in plan["curated_han_names"]
        }
        generated = text.split(BUILDER.MARKER, 1)[1]
        american_ids.update(
            int(value)
            for value in re.findall(r'^\s*(\d+)\s*=', generated, re.MULTILINE)
        )
        american_names = [direct_entries[value] for value in american_ids]
        self.assertEqual(778, len(american_names))
        self.assertEqual(778, len(set(american_names)))
        self.assertTrue(
            all(BUILDER.VALID_HAN_NAME.fullmatch(name) for name in american_names)
        )

    def test_duplicate_curated_exonym_is_rejected(self) -> None:
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(plan)
        mutated["overrides"]["965"]["name"] = mutated["overrides"]["953"][
            "name"
        ]
        with self.assertRaisesRegex(RuntimeError, "duplicated"):
            BUILDER._validate_plan(mutated, "duplicate-exonym mutation")

    def test_duplicate_curated_han_name_is_rejected(self) -> None:
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(plan)
        mutated["curated_han_names"]["965"] = mutated["curated_han_names"][
            "953"
        ]
        with self.assertRaisesRegex(RuntimeError, "duplicated"):
            BUILDER._validate_plan(mutated, "duplicate-Han-exonym mutation")


if __name__ == "__main__":
    unittest.main()
