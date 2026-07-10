from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.toyotomi import audit_companion_plan, check_toyotomi_history


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_PLAN = REPO_ROOT / "japan_expanded_v2_map/tools/jxp_map_builder/history_plan.json"
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")


def _codes(result: CheckResult) -> set[str]:
    return {issue.code for issue in result.issues}


class ToyotomiContractTests(unittest.TestCase):
    def test_live_identity_and_history_contract_is_clean(self) -> None:
        if not (GAME_ROOT / "launcher-settings.json").is_file():
            self.skipTest("pinned EU4 1.37.5 game root is not available")
        result = check_toyotomi_history(ValidationContext(MAIN_ROOT), GAME_ROOT)
        self.assertEqual(result.issues, [], result.to_dict())

    def test_settsu_early_handoff_is_rejected(self) -> None:
        plan = json.loads(MAP_PLAN.read_text(encoding="utf-8"))
        mutated = deepcopy(plan)
        mutated["province_timelines"]["1021"]["changes"][-1] = [
            "1600.10.21",
            "TKG",
        ]
        result = CheckResult("mutation")
        audit_companion_plan(mutated, result)
        self.assertIn("toyotomi.map_settsu_interval", _codes(result))

    def test_post_1586_oda_restoration_is_rejected(self) -> None:
        plan = json.loads(MAP_PLAN.read_text(encoding="utf-8"))
        mutated = deepcopy(plan)
        mutated["province_timelines"]["1030"]["changes"].insert(
            -1, ["1590.1.1", "ODA"]
        )
        result = CheckResult("mutation")
        audit_companion_plan(mutated, result)
        self.assertIn("toyotomi.map_post_start_oda", _codes(result))

    def test_oda_subject_surviving_past_succession_is_rejected(self) -> None:
        plan = json.loads(MAP_PLAN.read_text(encoding="utf-8"))
        mutated = deepcopy(plan)
        for interval in mutated["subject_intervals"]:
            if interval[0] == "ODA" and interval[3] == "1586.1.1":
                interval[3] = "1587.1.1"
                break
        result = CheckResult("mutation")
        audit_companion_plan(mutated, result)
        self.assertIn("toyotomi.map_post_start_oda_subject", _codes(result))


if __name__ == "__main__":
    unittest.main()
