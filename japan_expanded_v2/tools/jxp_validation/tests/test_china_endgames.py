from __future__ import annotations

import re
import unittest
from pathlib import Path

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


class ChinaEndgamesContractTests(unittest.TestCase):
    def test_b15_gameplay_files_parse(self) -> None:
        for relative in (
            "common/cb_types/jxp_08_cb_types.txt",
            "common/cb_types/jxp_b_100_china_endgames_cb_types.txt",
            "common/imperial_reforms/jxp_08_celestial_reforms.txt",
            "common/scripted_effects/jxp_03_overseas_effects.txt",
            "common/scripted_effects/jxp_b_100_china_endgames_effects.txt",
            "common/scripted_triggers/jxp_b_100_china_endgames_triggers.txt",
            "common/triggered_modifiers/jxp_b_100_hakko_burdens.txt",
            "common/wargoal_types/jxp_08_wargoal_types.txt",
            "common/wargoal_types/jxp_b_100_china_endgames_wargoals.txt",
            "decisions/jxp_03_overseas_decisions.txt",
            "decisions/jxp_b_100_china_endgames_decisions.txt",
            "events/jxp_b_100_china_endgames_events.txt",
            "events/jxp_eastasia_events.txt",
            "missions/jxp_03_overseas_missions.txt",
        ):
            parse_text(_read(relative))

    def test_three_mutually_exclusive_endgames_have_complete_capstones(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_100_china_endgames_triggers.txt")
        effects = _read("common/scripted_effects/jxp_b_100_china_endgames_effects.txt")
        decisions = _read("decisions/jxp_b_100_china_endgames_decisions.txt")
        for path in ("mandate", "rites", "break"):
            self.assertIn(f"jxp_b_100_china_path_{path}", triggers + effects)
            self.assertIn(f"jxp_b_100_china_endgame_{path}_complete", effects + decisions)
            self.assertIn(f"jxp_b_100_decision_complete_{path}_endgame", decisions)
        self.assertNotIn("set_emperor_of_china", triggers + effects + decisions)

    def test_mandate_path_uses_the_vanilla_mandate_peace_only(self) -> None:
        wargoals = _read("common/wargoal_types/jxp_b_100_china_endgames_wargoals.txt")
        mandate = wargoals.split("jxp_b_100_take_mandate_wargoal =", 1)[1].split(
            "jxp_b_100_rites_sphere_wargoal =", 1
        )[0]
        attacker = mandate.split("attacker =", 1)[1].split("defender =", 1)[0]
        self.assertIn("po_take_mandate", attacker)
        self.assertNotIn("po_demand_provinces", attacker)
        self.assertIn("deny_annex = yes", attacker)

    def test_hakko_only_discounts_eight_claimed_strategic_ports(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_100_china_endgames_triggers.txt")
        wargoal = _read("common/wargoal_types/jxp_08_wargoal_types.txt")
        port_block = triggers.split("jxp_b_100_limited_strategic_port_trigger =", 1)[1].split("\n}\n", 1)[0]
        self.assertEqual(8, len(re.findall(r"province_id\s*=\s*\d+", port_block)))
        self.assertIn("badboy_factor = 0.75", wargoal)
        self.assertIn("peace_cost_factor = 1.0", wargoal)
        self.assertIn("deny_annex = yes", wargoal)
        self.assertIn("jxp_b_100_limited_strategic_port_trigger = yes", wargoal)
        self.assertIn("is_claim = ROOT", wargoal)
        for option in (
            "po_subjugate_tributary_state",
            "po_release_vassals",
            "po_return_cores",
            "po_trade_power",
            "po_demand_provinces",
        ):
            self.assertIn(option, wargoal)

    def test_ordinary_overseas_rewards_no_longer_grant_broad_permanent_claims(self) -> None:
        payload = _read("common/scripted_effects/jxp_03_overseas_effects.txt") + _read(
            "missions/jxp_03_overseas_missions.txt"
        )
        self.assertNotIn("add_permanent_claim", payload)
        effects = _read("common/scripted_effects/jxp_b_100_china_endgames_effects.txt")
        self.assertEqual(8, effects.count("add_claim = ROOT"))

    def test_b13_china_request_is_consumed_without_an_empty_paid_route(self) -> None:
        continental = _read("common/scripted_effects/jxp_b_99_continental_strategy_effects.txt")
        china = _read("common/scripted_effects/jxp_b_100_china_endgames_effects.txt")
        self.assertIn("jxp_b_100_accept_b99_china_campaign_effect = yes", continental)
        self.assertIn("clr_country_flag = jxp_iface_b99_china_campaign_requested", china)
        self.assertIn("set_country_flag = jxp_b_100_b99_direct_campaign_authorized", china)
        self.assertIn("jxp_b_100_choose_break_path_effect = yes", china)

    def test_hakko_keeps_historical_phrase_and_has_internal_costs(self) -> None:
        source = _read("localisation_source/jxp_08_l_english_utf8_source.yml")
        reform = _read("common/imperial_reforms/jxp_08_celestial_reforms.txt")
        burden = _read("common/triggered_modifiers/jxp_b_100_hakko_burdens.txt")
        self.assertIn("开拓万里波涛，布国威于四方", source)
        self.assertIn("add_stability = -1", reform)
        self.assertIn("governing_capacity_modifier = -0.10", reform)
        self.assertIn("jxp_b_100_hakko_unintegrated_littoral", burden)

    def test_changed_localisation_sources_match_generated_active_files(self) -> None:
        pairs = (
            ("localisation_source/jxp_03_l_english_utf8_source.yml", "localisation/jxp_03_l_english.yml"),
            ("localisation_source/jxp_08_l_english_utf8_source.yml", "localisation/jxp_08_l_english.yml"),
            (
                "localisation_source/jxp_82_player_status_labels_l_english_utf8_source.yml",
                "localisation/jxp_82_player_status_labels_l_english.yml",
            ),
            (
                "localisation_source/jxp_b_100_china_endgames_l_english_utf8_source.yml",
                "localisation/jxp_b_100_china_endgames_l_english.yml",
            ),
        )
        pattern = re.compile(r"^\s+([^#\s][^:]*):\d+", re.MULTILINE)
        for source_name, active_name in pairs:
            source = _read(source_name)
            active_path = MOD_ROOT / active_name
            active = active_path.read_text(encoding="utf-8-sig")
            self.assertEqual(set(pattern.findall(source)), set(pattern.findall(active)))
            self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
