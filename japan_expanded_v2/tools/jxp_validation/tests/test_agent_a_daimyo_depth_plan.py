from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
BUILDER_ROOT = MAIN_ROOT / "tools" / "jxp_a_content_builder"
sys.path.insert(0, str(BUILDER_ROOT))
try:
    import build_daimyo_depth
finally:
    sys.path.remove(str(BUILDER_ROOT))


class AgentADaimyoDepthPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = json.loads(
            (BUILDER_ROOT / "daimyo_depth_plan.json").read_text(encoding="utf-8")
        )

    def test_exact_67_tag_and_surface_contract(self) -> None:
        build_daimyo_depth.validate(self.plan)
        rows = self.plan["daimyo"]
        self.assertEqual(67, len(rows))
        self.assertEqual({"main": 37, "map": 30}, Counter(row["surface"] for row in rows))
        self.assertIn("ASK", {row["tag"] for row in rows})
        self.assertNotIn("TOY", {row["tag"] for row in rows})
        self.assertEqual("S", self.plan["unified_state_appendix"]["TOY"]["tier"])

    def test_content_tiers_and_minimums_are_closed(self) -> None:
        rows = self.plan["daimyo"]
        self.assertEqual({"S": 16, "A": 13, "B": 38}, Counter(row["tier"] for row in rows))
        self.assertEqual(
            {("main", "S"): 13, ("main", "A"): 1, ("main", "B"): 23,
             ("map", "S"): 3, ("map", "A"): 12, ("map", "B"): 15},
            Counter((row["surface"], row["tier"]) for row in rows),
        )
        build_daimyo_depth.validate(self.plan)

    def test_source_and_interface_references_resolve(self) -> None:
        source_ids = set(self.plan["sources"])
        for row in self.plan["daimyo"]:
            self.assertTrue(set(row["sources"]) <= source_ids, row["tag"])
            self.assertTrue(
                set(row["interface_flags"]) <= build_daimyo_depth.ALLOWED_FLAGS,
                row["tag"],
            )
            self.assertGreaterEqual(len(row["keywords"]), 3, row["tag"])

    def test_generated_report_is_byte_current(self) -> None:
        expected = build_daimyo_depth.render(self.plan)
        actual = build_daimyo_depth.REPORT_PATH.read_text(encoding="utf-8")
        self.assertEqual(expected, actual)

    def test_duplicate_tag_mutation_is_rejected(self) -> None:
        mutated = deepcopy(self.plan)
        mutated["daimyo"][1]["tag"] = mutated["daimyo"][0]["tag"]
        with self.assertRaisesRegex(ValueError, "duplicate tag"):
            build_daimyo_depth.validate(mutated)


if __name__ == "__main__":
    unittest.main()
