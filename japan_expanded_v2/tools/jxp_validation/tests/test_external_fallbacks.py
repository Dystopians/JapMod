from __future__ import annotations

import json
import importlib.util
import re
import unittest
from pathlib import Path

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


def _escape_source(text: str) -> str:
    script = MOD_ROOT.parent / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py"
    spec = importlib.util.spec_from_file_location("jxp_b118_eu4_escape", script)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load localisation converter: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.escape_text(text)


class ExternalFallbackContractTests(unittest.TestCase):
    def test_b15_ai_guardrail_vocabulary_and_costs_are_parseable(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_118_external_fallback_triggers.txt")
        parse_text(triggers)
        for trigger in (
            "jxp_b_118_ai_colonial_state_formation_ready_trigger",
            "jxp_b_118_ai_company_ready_trigger",
            "jxp_b_118_ai_independence_war_ready_trigger",
            "jxp_b_118_ai_end_metropole_rule_ready_trigger",
            "jxp_b_118_ai_eastward_revolution_ready_trigger",
            "jxp_b_118_ai_strategy_council_ready_trigger",
            "jxp_b_118_ai_continental_campaign_ready_trigger",
            "jxp_b_118_ai_korea_expedition_ready_trigger",
            "jxp_b_118_ai_china_policy_ready_trigger",
            "jxp_b_118_ai_rites_war_ready_trigger",
            "jxp_b_118_ai_mandate_war_ready_trigger",
        ):
            self.assertIn(f"{trigger} = {{", triggers)
        for brake in (
            "is_bankrupt = yes",
            "num_of_loans",
            "treasury",
            "manpower_percentage",
            "num_of_transport",
            "army_strength = { who = FROM",
            "naval_strength = { who = FROM",
        ):
            self.assertIn(brake, triggers)
        self.assertIn("value = 90", triggers)
        self.assertIn("treasury = 2000", triggers)
        self.assertIn("num_of_transport = 30", triggers)
        self.assertNotIn("every_country", triggers)
        self.assertNotIn("every_province", triggers)
        self.assertNotIn("mean_time_to_happen", triggers)

    def test_players_bypass_ai_only_war_brakes(self) -> None:
        contracts = {
            "common/cb_types/jxp_b_96_colonial_independence_cb.txt": "jxp_b_118_ai_independence_war_ready_trigger",
            "common/cb_types/jxp_b_97_end_metropole_rule_cb.txt": "jxp_b_118_ai_end_metropole_rule_ready_trigger",
            "common/cb_types/jxp_b_98_eastward_revolution_cb.txt": "jxp_b_118_ai_eastward_revolution_ready_trigger",
            "common/cb_types/jxp_b_99_continental_strategy_cb.txt": "jxp_b_118_ai_continental_campaign_ready_trigger",
            "common/cb_types/jxp_b_101_korea_campaign_cb.txt": "jxp_b_118_ai_korea_expedition_ready_trigger",
        }
        for relative, trigger in contracts.items():
            text = _read(relative)
            parse_text(text)
            self.assertIn("ai = no", text, relative)
            self.assertIn(f"{trigger} = yes", text, relative)
        china = _read("common/cb_types/jxp_b_100_china_endgames_cb_types.txt")
        parse_text(china)
        self.assertEqual(3, china.count("ai = no"))
        self.assertEqual(2, china.count("jxp_b_118_ai_mandate_war_ready_trigger = yes"))
        self.assertEqual(1, china.count("jxp_b_118_ai_rites_war_ready_trigger = yes"))
        hakko = _read("common/cb_types/jxp_08_cb_types.txt")
        parse_text(hakko)
        self.assertIn("ai = no", hakko)
        self.assertIn("jxp_b_118_ai_mandate_war_ready_trigger = yes", hakko)

    def test_state_company_and_strategy_ai_entries_consume_b15_brakes(self) -> None:
        nya = _read("decisions/jxp_b_94_new_yamato_decisions.txt")
        secondary = _read("decisions/jxp_b_95_secondary_colonial_states_decisions.txt")
        companies = _read("decisions/jxp_b_112_overseas_company_decisions.txt")
        strategy = _read("decisions/jxp_b_99_continental_strategy_decisions.txt")
        china = _read("decisions/jxp_b_100_china_endgames_decisions.txt")
        for text in (nya, secondary, companies, strategy, china):
            parse_text(text)
        self.assertEqual(1, nya.count("jxp_b_118_ai_colonial_state_formation_ready_trigger = yes"))
        self.assertEqual(3, secondary.count("jxp_b_118_ai_colonial_state_formation_ready_trigger = yes"))
        self.assertEqual(5, companies.count("jxp_b_118_ai_company_ready_trigger = yes"))
        self.assertEqual(6, strategy.count("jxp_b_118_ai_strategy_council_ready_trigger = yes"))
        self.assertIn("jxp_b_118_ai_china_policy_ready_trigger = yes", china)

    def test_rnw_and_no_colonist_fallbacks_do_not_depend_on_fixed_america(self) -> None:
        nya = _read("common/scripted_triggers/jxp_b_94_new_yamato_triggers.txt")
        secondary = _read("common/scripted_triggers/jxp_b_95_secondary_states_triggers.txt")
        companies = _read("common/scripted_triggers/jxp_b_112_external_triggers.txt")
        company_decisions = _read("decisions/jxp_b_112_overseas_company_decisions.txt")
        for text in (nya, secondary, companies, company_decisions):
            parse_text(text)
        for text in (nya, secondary):
            self.assertIn("is_random_new_world = yes", text)
            self.assertIn("continent = new_world", text)
        self.assertIn("continent = new_world", companies)
        self.assertIn("jxp_b_92_rnw_western_anchor_trigger = yes", companies)
        self.assertRegex(
            company_decisions,
            r"OR\s*=\s*\{\s*num_of_colonists\s*=\s*1\s+tag\s*=\s*NYA\s+tag\s*=\s*TPF\s+jxp_b_92_rnw_western_anchor_trigger\s*=\s*yes\s*\}",
        )

    def test_mandate_dlc_off_is_diplomatic_fallback_not_fake_emperorship(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_100_china_endgames_triggers.txt")
        effects = _read("common/scripted_effects/jxp_b_100_china_endgames_effects.txt")
        localisation = _read("localisation_source/jxp_b_100_china_endgames_l_english_utf8_source.yml")
        self.assertIn('has_dlc = "Mandate of Heaven"', triggers)
        self.assertIn('NOT = { has_dlc = "Mandate of Heaven" }', triggers)
        self.assertIn("has_country_flag = jxp_mandate_claim_fallback", triggers)
        self.assertIn("name = jxp_b_100_mandate_fallback_endgame", effects)
        self.assertIn("不会伪称日本已成为天朝皇帝", localisation)
        self.assertIn("不授予天命或天朝皇帝身份", localisation)

    def test_main_only_and_missing_optional_a_interfaces_have_local_fallbacks(self) -> None:
        runtime_dirs = ("common", "decisions", "events", "missions")
        b_files: list[Path] = []
        for runtime_dir in runtime_dirs:
            b_files.extend((MOD_ROOT / runtime_dir).rglob("jxp_b_*.txt"))
        combined = "\n".join(path.read_text(encoding="utf-8-sig") for path in b_files)
        self.assertNotIn("jxp_map_", combined)
        self.assertIsNone(re.search(r"\bjxp_a_[a-z0-9_]+\s*=\s*yes\b", combined))
        self.assertIsNone(
            re.search(r"\b(?:province_id|owns|set_capital)\s*=\s*(?:49(?:4[2-9]|[5-7][0-9]|8[01]))\b", combined)
        )
        company_triggers = _read("common/scripted_triggers/jxp_b_112_external_triggers.txt")
        self.assertNotIn("jxp_iface_a_company_core_ready", company_triggers)
        self.assertNotIn("jxp_iface_a_company_charter_active", company_triggers)
        self.assertIn("dip_tech = 9", company_triggers)
        self.assertIn("num_of_ports = 8", company_triggers)
        self.assertIn("treasury = 500", company_triggers)

    def test_scenario_matrix_is_pending_runtime_and_contains_no_results(self) -> None:
        matrix_path = MOD_ROOT / "tools/jxp_validation/jxp_b_external_fallback_scenarios.json"
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        self.assertEqual("jxp_b_external_fallback_scenarios/v1", matrix["schema"])
        self.assertEqual("PENDING_RUNTIME", matrix["evidence_class"])
        self.assertTrue(matrix["rules"]["eu4_launch_forbidden_in_this_slice"])
        self.assertTrue(matrix["rules"]["runtime_results_must_not_be_inferred_from_static_checks"])
        scenarios = matrix["scenarios"]
        self.assertGreaterEqual(len(scenarios), 13)
        self.assertEqual(len(scenarios), len({scenario["id"] for scenario in scenarios}))
        self.assertTrue(all(scenario["status"] == "PENDING_RUNTIME" for scenario in scenarios))
        forbidden_result_keys = {"passed", "result", "observed", "runtime_pass"}
        self.assertTrue(all(not forbidden_result_keys.intersection(scenario) for scenario in scenarios))

    def test_fallback_guide_localisation_is_generated_and_bom_safe(self) -> None:
        decision = _read("decisions/jxp_b_118_external_fallback_decisions.txt")
        event = _read("events/jxp_b_118_external_fallback_events.txt")
        source_path = MOD_ROOT / "localisation_source/jxp_b_118_external_fallback_l_english_utf8_source.yml"
        active_path = MOD_ROOT / "localisation/jxp_b_118_external_fallback_l_english.yml"
        parse_text(decision)
        parse_text(event)
        self.assertTrue(active_path.is_file())
        self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        source = source_path.read_text(encoding="utf-8-sig")
        active = active_path.read_text(encoding="utf-8-sig")
        key_pattern = re.compile(r"^\s+([^#\s][^:]*):\d+", re.MULTILINE)
        self.assertEqual(set(key_pattern.findall(source)), set(key_pattern.findall(active)))
        self.assertEqual(_escape_source(source), active)
        self.assertIn("未曾记载的新大陆", source)
        self.assertIn("不作虚名", source)


if __name__ == "__main__":
    unittest.main()
