from __future__ import annotations

from pathlib import Path
import re
import unittest

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


class KoreaCampaignContractTests(unittest.TestCase):
    def test_korea_campaign_files_parse(self) -> None:
        for relative in (
            "common/cb_types/jxp_b_101_korea_campaign_cb.txt",
            "common/event_modifiers/jxp_b_101_korea_campaign_modifiers.txt",
            "common/scripted_effects/jxp_b_101_korea_campaign_effects.txt",
            "common/scripted_triggers/jxp_b_101_korea_campaign_triggers.txt",
            "common/wargoal_types/jxp_b_101_korea_campaign_wargoal.txt",
            "decisions/jxp_b_101_korea_campaign_decisions.txt",
            "events/jxp_b_101_korea_campaign_events.txt",
        ):
            parse_text(_read(relative))

    def test_ten_costly_sequential_prewar_stages(self) -> None:
        decisions = _read("decisions/jxp_b_101_korea_campaign_decisions.txt")
        ids = re.findall(r"^\s*(jxp_b_101_\w+_decision)\s*=", decisions, re.MULTILINE)
        self.assertEqual(10, len(ids))
        self.assertEqual(10, decisions.count("ai_will_do ="))
        for stage in range(1, 11):
            self.assertIn(f"jxp_b_101_korea_stage_{stage:02d}_done", decisions)
        for cost in ("add_treasury = -", "add_dip_power = -", "add_mil_power = -"):
            self.assertIn(cost, decisions)
        self.assertIn("num_of_transport = 12", decisions)
        self.assertIn("num_of_artillery = 3", decisions)
        self.assertIn("jxp_iface_b99_korea_campaign_requested", decisions)

    def test_five_bounded_preparation_variables_are_cleaned(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_101_korea_campaign_effects.txt")
        expected = {
            "jxp_b_korea_transport_capacity",
            "jxp_b_korea_grain_reserve",
            "jxp_b_korea_expedition_support",
            "jxp_b_korea_daimyo_compliance",
            "jxp_b_korea_sea_control",
        }
        actual = set(re.findall(r"which\s*=\s*(jxp_b_korea_\w+)", effects))
        self.assertEqual(expected, actual)
        for variable in expected:
            self.assertIn(f"which = {variable} value = 0", effects)
            self.assertIn(f"which = {variable} value = 100", effects)
        self.assertIn("jxp_b_101_korea_campaign_active_cleanup_effect", effects)

    def test_eighteen_wartime_events_cover_required_campaign_pressures(self) -> None:
        events = _read("events/jxp_b_101_korea_campaign_events.txt")
        self.assertNotIn("hide_window = yes", events)
        self.assertGreaterEqual(events.count("hidden = yes"), 2)
        ids = set(
            re.findall(
                r"^\s*id\s*=\s*jxp_korea_campaign\.(\d+)\s*$",
                events,
                re.MULTILINE,
            )
        )
        self.assertTrue({str(value) for value in range(100, 118)}.issubset(ids))
        self.assertTrue({"180", "940", "941"}.issubset(ids))
        self.assertNotIn("mean_time_to_happen", events)
        self.assertIn("war_with = KOR", events)
        self.assertIn("exists = MNG", events)
        self.assertIn("exists = QNG", events)

    def test_atrocity_is_never_a_free_positive_reward(self) -> None:
        events = _read("events/jxp_b_101_korea_campaign_events.txt")
        modifiers = _read("common/event_modifiers/jxp_b_101_korea_campaign_modifiers.txt")
        self.assertIn("set_country_flag = jxp_b_101_korea_atrocity_committed", events)
        self.assertIn("add_stability = -1", events)
        self.assertIn("add_war_exhaustion = 2", events)
        self.assertIn("diplomatic_reputation = -2", modifiers)
        self.assertIn("jxp_b_101_korean_reprisals", events)

    def test_six_postwar_outcomes_do_not_create_land_or_cores(self) -> None:
        events = _read("events/jxp_b_101_korea_campaign_events.txt")
        effects = _read("common/scripted_effects/jxp_b_101_korea_campaign_effects.txt")
        outcome_block = events.rsplit("id = jxp_korea_campaign.180", 1)[1]
        self.assertEqual(6, len(re.findall(r"^\s*option\s*=", outcome_block, re.MULTILINE)))
        for effect in (
            "trade",
            "southern_protectorate",
            "puppet",
            "direct_rule",
            "strategic_retreat",
            "disaster",
        ):
            self.assertIn(f"jxp_b_101_korea_outcome_{effect}_effect", events)
        payload = events + effects
        for forbidden in ("add_core", "add_permanent_claim", "add_claim", "cede_province", "create_subject"):
            self.assertNotIn(forbidden, payload)
        self.assertIn("add_local_autonomy = 25", effects)
        self.assertIn("jxp_b_101_korea_direct_rule_resistance", effects)

    def test_expedition_cb_keeps_normal_conquest_costs(self) -> None:
        cb = _read("common/cb_types/jxp_b_101_korea_campaign_cb.txt")
        wargoal = _read("common/wargoal_types/jxp_b_101_korea_campaign_wargoal.txt")
        self.assertIn("is_triggered_only = yes", cb)
        self.assertIn("tag = KOR", cb)
        self.assertIn("badboy_factor = 1.50", wargoal)
        self.assertIn("peace_cost_factor = 1.25", wargoal)
        self.assertIn("po_demand_provinces", wargoal)
        self.assertNotIn("add_permanent_claim", cb + wargoal)

    def test_localisation_names_every_stage_event_outcome_and_modifier(self) -> None:
        source = _read("localisation_source/jxp_b_101_korea_campaign_l_english_utf8_source.yml")
        for concept in (
            "对马通事",
            "名护屋兵站",
            "运输船",
            "朝鲜水军",
            "大陆援军",
            "军纪与暴行",
            "战略撤退",
            "渡海役崩溃",
        ):
            self.assertIn(concept, source)
        for event_id in range(100, 118):
            self.assertIn(f"jxp_korea_campaign.{event_id}.t:0", source)
            self.assertIn(f"jxp_korea_campaign.{event_id}.d:0", source)

        source_keys = set(re.findall(r"^\s+([^#\s][^:]*):\d+", source, re.MULTILINE))
        active_path = MOD_ROOT / "localisation/jxp_b_101_korea_campaign_l_english.yml"
        active = active_path.read_text(encoding="utf-8-sig")
        active_keys = set(re.findall(r"^\s+([^#\s][^:]*):\d+", active, re.MULTILINE))
        self.assertEqual(source_keys, active_keys)
        self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
