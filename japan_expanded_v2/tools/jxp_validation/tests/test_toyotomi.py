from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.toyotomi import audit_companion_plan, check_toyotomi_history


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_PLAN = REPO_ROOT / "japan_expanded_v2_map/tools/jxp_map_builder/history_plan.json"
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
ENCODER_PATH = REPO_ROOT / "skills/eu4-modding/scripts/encode_eu4_special_gameplay.py"


def _load_encoder():
    spec = importlib.util.spec_from_file_location("_test_gameplay_encoder", ENCODER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ENCODER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _codes(result: CheckResult) -> set[str]:
    return {issue.code for issue in result.issues}


class ToyotomiContractTests(unittest.TestCase):
    def test_live_identity_and_history_contract_is_clean(self) -> None:
        if not (GAME_ROOT / "launcher-settings.json").is_file():
            self.skipTest("pinned EU4 1.37.5 game root is not available")
        result = check_toyotomi_history(ValidationContext(MAIN_ROOT), GAME_ROOT)
        self.assertEqual(result.issues, [], result.to_dict())

    def test_live_toyotomi_dates_share_unique_monarchy_reform(self) -> None:
        source = (
            MAIN_ROOT
            / "tools/jxp_history_builder/source/history/countries/TOY - Toyotomi.txt"
        ).read_text(encoding="utf-8-sig")
        reform = "add_government_reform = jxp_toyotomi_kampaku_taiko_reform"
        self.assertEqual(1, source.count(reform))
        self.assertNotIn("add_government_reform = shogunate", source)
        self.assertNotIn("add_government_reform = daimyo", source)
        self.assertNotIn("government = republic", source)

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

    def test_dual_landed_map_identity_is_rejected(self) -> None:
        plan = json.loads(MAP_PLAN.read_text(encoding="utf-8"))
        mutated = deepcopy(plan)
        mutated["province_timelines"]["1030"]["changes"].insert(
            -1, ["1590.1.1", "ODA"]
        )
        result = CheckResult("mutation")
        audit_companion_plan(mutated, result)
        self.assertIn("toyotomi.map_dual_landed_identity", _codes(result))

    def test_gameplay_name_encoder_round_trips_without_utf8_cjk(self) -> None:
        encoder = _load_encoder()
        source = 'name = "秀吉"\ndynasty = "丰臣"\n'
        active = encoder.encode_gameplay_text(source)
        self.assertFalse(active.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn("秀吉".encode("utf-8"), active)
        self.assertEqual(encoder.decode_gameplay_bytes(active), source)

    def test_raw_utf8_toyotomi_history_is_rejected(self) -> None:
        if not (GAME_ROOT / "launcher-settings.json").is_file():
            self.skipTest("pinned EU4 1.37.5 game root is not available")
        active = MAIN_ROOT / "history/countries/TOY - Toyotomi.txt"
        source = (
            MAIN_ROOT
            / "tools/jxp_history_builder/source/history/countries/TOY - Toyotomi.txt"
        )
        original = active.read_bytes()
        try:
            active.write_bytes(source.read_bytes())
            result = check_toyotomi_history(ValidationContext(MAIN_ROOT), GAME_ROOT)
            self.assertTrue(
                {"toyotomi.gameplay_name_encoding", "toyotomi.gameplay_name_raw_cjk"}
                & _codes(result)
            )
        finally:
            active.write_bytes(original)

    def test_toyotomi_profile_losing_shared_slot_is_rejected(self) -> None:
        if not (GAME_ROOT / "launcher-settings.json").is_file():
            self.skipTest("pinned EU4 1.37.5 game root is not available")
        mission_file = MAIN_ROOT / "missions/jxp_japan_missions.txt"
        original = mission_file.read_text(encoding="utf-8")
        marker = "\t\t\ttag = TOY\n"
        self.assertIn(marker, original)
        try:
            mission_file.write_text(original.replace(marker, "", 1), encoding="utf-8")
            result = check_toyotomi_history(ValidationContext(MAIN_ROOT), GAME_ROOT)
            self.assertIn("toyotomi.mission_profile", _codes(result))
        finally:
            mission_file.write_text(original, encoding="utf-8", newline="")


if __name__ == "__main__":
    unittest.main()
