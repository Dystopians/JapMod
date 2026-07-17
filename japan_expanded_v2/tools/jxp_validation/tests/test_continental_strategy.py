from __future__ import annotations

import re
import unittest
from pathlib import Path

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


class ContinentalStrategyContractTests(unittest.TestCase):
    def test_b13_files_parse(self) -> None:
        for relative in (
            "common/scripted_triggers/jxp_b_99_continental_strategy_triggers.txt",
            "common/scripted_effects/jxp_b_99_continental_strategy_effects.txt",
            "common/event_modifiers/jxp_b_99_continental_strategy_modifiers.txt",
            "common/opinion_modifiers/jxp_b_99_continental_strategy_opinions.txt",
            "common/cb_types/jxp_b_99_continental_strategy_cb.txt",
            "common/wargoal_types/jxp_b_99_continental_strategy_wargoal.txt",
            "decisions/jxp_b_99_continental_strategy_decisions.txt",
            "events/jxp_b_99_continental_strategy_events.txt",
        ):
            parse_text(_read(relative))

    def test_six_theaters_each_expose_four_policies(self) -> None:
        decisions = _read("decisions/jxp_b_99_continental_strategy_decisions.txt")
        events = _read("events/jxp_b_99_continental_strategy_events.txt")
        theaters = (
            "ryukyu",
            "korea",
            "northern",
            "taiwan_fujian",
            "china",
            "southeast_asia",
        )
        for theater in theaters:
            self.assertIn(f"jxp_b_99_convene_{theater}_strategy", decisions)
        for mode in ("mode_trade", "mode_protection", "mode_treaty_port", "mode_conquest"):
            self.assertEqual(6, events.count(f"name = jxp_b_continental_strategy.{mode}"))

    def test_korea_and_china_direct_campaigns_exclude_daimyo(self) -> None:
        events = _read("events/jxp_b_99_continental_strategy_events.txt")
        for event_id in (2, 5):
            start = events.index(f"id = jxp_b_continental_strategy.{event_id}\n")
            end = events.index("\ncountry_event = {", start + 1)
            block = events[start:end]
            conquest = block.split("name = jxp_b_continental_strategy.mode_conquest", 1)[1]
            self.assertIn("NOT = { jxp_b_99_daimyo_stage_trigger = yes }", conquest)

    def test_direct_campaign_has_real_cost_and_no_free_claims(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_99_continental_strategy_effects.txt")
        wargoal = _read("common/wargoal_types/jxp_b_99_continental_strategy_wargoal.txt")
        payload = effects + wargoal + _read("events/jxp_b_99_continental_strategy_events.txt")
        for cost in (
            "add_adm_power = -150",
            "add_mil_power = -150",
            "add_treasury = -500",
            "add_sailors = -1000",
        ):
            self.assertIn(cost, effects)
        self.assertIn("badboy_factor = 1.50", wargoal)
        self.assertIn("peace_cost_factor = 1.25", wargoal)
        self.assertNotIn("add_permanent_claim", payload)
        self.assertNotIn("add_core", payload)

    def test_four_postwar_governance_modes_are_costly_and_finite(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_99_continental_strategy_effects.txt")
        events = _read("events/jxp_b_99_continental_strategy_events.txt")
        for mode in (
            "military_commission",
            "local_dynasty",
            "tribute_trade",
            "direct_governor",
        ):
            self.assertIn(f"jxp_b_99_apply_{mode}_governance_effect", effects)
        self.assertIn("add_adm_power = -200", events)
        self.assertIn("add_dip_power = -150", events)
        self.assertIn("add_mil_power = -100", events)
        self.assertIn("duration = 7300", effects)

    def test_source_and_active_localisation_match(self) -> None:
        source = _read("localisation_source/jxp_b_99_continental_strategy_l_english_utf8_source.yml")
        active_path = MOD_ROOT / "localisation/jxp_b_99_continental_strategy_l_english.yml"
        active = active_path.read_text(encoding="utf-8-sig")
        key_pattern = re.compile(r"^\s+([^#\s][^:]*):\d+", re.MULTILINE)
        self.assertEqual(set(key_pattern.findall(source)), set(key_pattern.findall(active)))
        self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
