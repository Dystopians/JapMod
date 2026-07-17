from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import re
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
BUILDER_ROOT = MAIN_ROOT / "tools" / "jxp_a_content_builder"
sys.path.insert(0, str(BUILDER_ROOT))
try:
    import build_daimyo_depth_runtime
finally:
    sys.path.remove(str(BUILDER_ROOT))


class AgentADaimyoDepthRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan, cls.exact = build_daimyo_depth_runtime.load_inputs()
        cls.records = [
            row
            for row in cls.plan["daimyo"]
            if row["tag"] not in build_daimyo_depth_runtime.EXTERNALLY_OWNED
        ]

    def test_generator_owns_exactly_65_non_oda_img_identities(self) -> None:
        build_daimyo_depth_runtime.validate(self.plan, self.exact)
        self.assertEqual(65, len(self.records))
        self.assertEqual({"main": 35, "map": 30}, Counter(row["surface"] for row in self.records))
        self.assertEqual({"S": 14, "A": 13, "B": 38}, Counter(row["tier"] for row in self.records))

    def test_net_new_mission_and_event_counts_match_design(self) -> None:
        for surface in ("main", "map"):
            text = build_daimyo_depth_runtime.render_missions(surface, self.plan["daimyo"], self.exact)
            events = build_daimyo_depth_runtime.render_events(surface, self.plan["daimyo"])
            surface_records = [row for row in self.records if row["surface"] == surface]
            for record_index, row in enumerate(surface_records):
                tag = row["tag"].lower()
                missions = set(re.findall(rf"\bjxp_a_mission_{tag}_depth_\d+\b", text))
                expected_missions = build_daimyo_depth_runtime.new_count(row, self.exact)
                self.assertEqual(expected_missions, len(missions), row["tag"])
                base = build_daimyo_depth_runtime.EVENT_BASE[surface] + record_index * 20
                ids = set(int(value) for value in re.findall(r"id = jxp_daimyo_depth\.(\d+)", events))
                self.assertTrue(set(range(base, base + row["planned_events"])) <= ids, row["tag"])

    def test_slot_replacement_contract_preserves_five_columns(self) -> None:
        main_common = (MAIN_ROOT / "missions" / "jxp_04_daimyo_missions.txt").read_text(encoding="utf-8")
        main_shared = (MAIN_ROOT / "missions" / "jxp_21_daimyo_house_missions.txt").read_text(encoding="utf-8")
        map_shared = (MAP_ROOT / "missions" / "jxp_map_new_daimyo_missions.txt").read_text(encoding="utf-8")
        self.assertEqual(1, main_common.count("jxp_a_uses_depth_slot_2_trigger = yes"))
        self.assertEqual(1, main_common.count("jxp_a_uses_depth_slot_4_trigger = yes"))
        self.assertEqual(5, main_shared.count("jxp_a_uses_depth_slot_3_trigger = yes"))
        self.assertEqual(5, map_shared.count("jxp_a_uses_depth_slot_3_trigger = yes"))
        for row in self.records:
            layout = build_daimyo_depth_runtime._series_layout(row, self.exact)
            slots = {slot for slot, _, _ in layout}
            expected = {"S": {2, 4}, "A": {4}, "B": {3}}[row["tier"]]
            self.assertEqual(expected, slots, row["tag"])
            self.assertTrue(all(count <= 5 for _, _, count in layout), row["tag"])

    def test_generated_outputs_are_byte_current(self) -> None:
        outputs = build_daimyo_depth_runtime.render_outputs(self.plan, self.exact)
        self.assertEqual(17, len(outputs))
        for path, expected in outputs.items():
            self.assertTrue(path.is_file(), path)
            actual = path.read_bytes() if isinstance(expected, bytes) else path.read_text(encoding="utf-8")
            self.assertEqual(expected, actual, path)

    def test_private_state_and_interface_boundary(self) -> None:
        outputs = build_daimyo_depth_runtime.render_outputs(self.plan, self.exact)
        gameplay = "\n".join(
            payload
            for path, payload in outputs.items()
            if isinstance(payload, str) and "localisation" not in path.parts
        )
        self.assertNotIn("add_permanent_claim", gameplay)
        self.assertNotIn("create_subject", gameplay)
        self.assertNotRegex(gameplay, r"set_country_flag = jxp_b_")
        self.assertNotRegex(gameplay, r"set_country_flag = jxp_iface_")
        self.assertIn("jxp_a_mark_house_", gameplay)
        private_flags = re.findall(r"(?:set|clr)_country_flag = (jxp_[a-z0-9_]+)", gameplay)
        self.assertTrue(private_flags)
        for flag in private_flags:
            self.assertTrue(flag.startswith("jxp_a_") or flag.startswith("jxp_iface_"), flag)

    def test_generated_effects_and_mission_ids_are_safe(self) -> None:
        for surface in ("main", "map"):
            missions = build_daimyo_depth_runtime.render_missions(
                surface, self.plan["daimyo"], self.exact
            )
            events = build_daimyo_depth_runtime.render_events(surface, self.plan["daimyo"])
            declarations = re.findall(
                r"^\s*(jxp_a_mission_[a-z0-9_]+)\s*=\s*\{",
                missions,
                flags=re.MULTILINE,
            )
            self.assertEqual(len(declarations), len(set(declarations)), surface)
            self.assertNotIn("required_missions = {  }", missions)
            self.assertNotIn("add_reform_progress", missions + events)
            self.assertNotIn("add_manpower = 5", missions + events)

    def test_each_house_has_a_distinct_legacy_modifier_signature(self) -> None:
        signatures: list[tuple[str, ...]] = []
        for surface in ("main", "map"):
            rendered = build_daimyo_depth_runtime.render_modifiers(
                surface, self.plan["daimyo"]
            )
            bodies = re.findall(
                r"^jxp_a_[a-z0-9]+_legacy_modifier\s*=\s*\{\n(.*?)^\}",
                rendered,
                flags=re.MULTILINE | re.DOTALL,
            )
            signatures.extend(
                tuple(sorted(line.strip() for line in body.splitlines() if line.strip()))
                for body in bodies
            )
        self.assertEqual(65, len(signatures))
        self.assertEqual(len(signatures), len(set(signatures)))


if __name__ == "__main__":
    unittest.main()
