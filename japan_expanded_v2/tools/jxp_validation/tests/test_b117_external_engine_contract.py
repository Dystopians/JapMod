from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import unittest

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]
VANILLA_1375_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
PLAYER_SWITCH_RUNTIME_STATUS = "PENDING_RUNTIME"

VANILLA_1375_EVIDENCE = {
    "events/disaster_ming_crisis.txt": "f7e62ae17dc865f76168b880367394659feaf49153420180f3b701465261faf8",
    "common/peace_treaties/00_peace_treaties.txt": "19837dba0daf9d7910b39aa20ca1e34779f12e39eab95f9e3b6801bd763c2fe5",
    "common/peace_treaties/00_claim_norwegian_throne.txt": "cadec3763721290d006a563e6b9f50680c0e283ac3d2a97de2ea758b05529583",
}


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


def _escape_source(text: str) -> str:
    script = MOD_ROOT.parent / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py"
    spec = importlib.util.spec_from_file_location("jxp_b117_eu4_escape", script)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load localisation converter: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.escape_text(text)


class ExternalEngineContractTests(unittest.TestCase):
    def test_b117_files_parse(self) -> None:
        for relative in (
            "common/on_actions/jxp_b_117_external_reconcile_on_actions.txt",
            "common/scripted_effects/jxp_b_117_external_reconcile_effects.txt",
            "common/scripted_triggers/jxp_b_117_external_reconcile_triggers.txt",
            "events/jxp_b_117_external_reconcile_events.txt",
            "common/scripted_effects/jxp_b_97_end_metropole_rule_effects.txt",
            "common/scripted_triggers/jxp_b_97_end_metropole_rule_triggers.txt",
        ):
            parse_text(_read(relative))

    def test_vanilla_1375_player_switch_evidence_is_exact_but_runtime_remains_pending(self) -> None:
        if not VANILLA_1375_ROOT.is_dir():
            self.skipTest(f"EU4 1.37.5 reference install unavailable: {VANILLA_1375_ROOT}")
        for relative, expected_sha in VANILLA_1375_EVIDENCE.items():
            with self.subTest(path=relative):
                payload = (VANILLA_1375_ROOT / relative).read_bytes()
                self.assertEqual(expected_sha, hashlib.sha256(payload).hexdigest())
        source = (VANILLA_1375_ROOT / "events/disaster_ming_crisis.txt").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("trigger = {\n\t\t\tai = no", source)
        self.assertIn("switch_tag = CSH", source)
        self.assertEqual("PENDING_RUNTIME", PLAYER_SWITCH_RUNTIME_STATUS)

    def test_rnw_dlc_and_ai_entry_contracts_are_table_driven(self) -> None:
        cases = (
            (
                "RNW normal and generated branches",
                "common/scripted_triggers/jxp_b_92_regional_colonial_triggers.txt",
                ("is_random_new_world = no", "is_random_new_world = yes", "continent = new_world"),
            ),
            (
                "Mandate DLC and fallback",
                "common/scripted_triggers/jxp_b_100_china_endgames_triggers.txt",
                ('has_dlc = "Mandate of Heaven"', 'NOT = { has_dlc = "Mandate of Heaven" }'),
            ),
            (
                "regional colonial AI brakes",
                "decisions/jxp_b_92_regional_colonial_decisions.txt",
                ("ai_will_do =", "factor = 0 is_bankrupt = yes"),
            ),
            (
                "continental strategy AI brakes",
                "decisions/jxp_b_99_continental_strategy_decisions.txt",
                ("ai_will_do =", "factor = 0 is_bankrupt = yes"),
            ),
            (
                "China endgame AI brakes",
                "decisions/jxp_b_100_china_endgames_decisions.txt",
                ("ai_will_do =", "is_bankrupt = yes"),
            ),
            (
                "Korea campaign AI brakes",
                "decisions/jxp_b_101_korea_campaign_decisions.txt",
                ("ai_will_do =", "factor = 0.10", "num_of_loans = 3"),
            ),
        )
        for name, relative, required in cases:
            with self.subTest(case=name):
                payload = _read(relative)
                for token in required:
                    self.assertIn(token, payload)

    def test_reconcile_and_korea_paths_have_no_global_or_monthly_scan(self) -> None:
        cases = (
            "common/scripted_effects/jxp_b_97_end_metropole_rule_effects.txt",
            "common/on_actions/jxp_b_117_external_reconcile_on_actions.txt",
            "common/scripted_effects/jxp_b_117_external_reconcile_effects.txt",
            "common/scripted_effects/jxp_b_101_korea_campaign_effects.txt",
            "events/jxp_b_101_korea_campaign_events.txt",
        )
        for relative in cases:
            with self.subTest(path=relative):
                payload = _read(relative)
                self.assertNotIn("every_country", payload)
                self.assertNotIn("every_province", payload)
                self.assertNotIn("on_monthly", payload)
                self.assertNotIn("mean_time_to_happen", payload)

    def test_new_localisation_is_exact_canonical_source_to_active_output(self) -> None:
        cases = (
            (
                "localisation_source/jxp_b_101_korea_campaign_l_english_utf8_source.yml",
                "localisation/jxp_b_101_korea_campaign_l_english.yml",
            ),
            (
                "localisation_source/jxp_b_117_external_reconcile_l_english_utf8_source.yml",
                "localisation/jxp_b_117_external_reconcile_l_english.yml",
            ),
        )
        for source_relative, active_relative in cases:
            with self.subTest(source=source_relative):
                source = _read(source_relative)
                active_path = MOD_ROOT / active_relative
                self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))
                self.assertEqual(_escape_source(source), active_path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
