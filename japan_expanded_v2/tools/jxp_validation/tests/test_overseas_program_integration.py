from __future__ import annotations

import re
import unittest
from pathlib import Path

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


class OverseasProgramIntegrationTests(unittest.TestCase):
    def test_b16_startup_migration_is_parseable_and_idempotent(self) -> None:
        trigger = _read("common/scripted_triggers/jxp_b_102_overseas_program_triggers.txt")
        depth_trigger = _read("common/scripted_triggers/jxp_b_110_colonial_depth_triggers.txt")
        effect = _read("common/scripted_effects/jxp_b_102_overseas_program_effects.txt")
        registry_event = _read("events/jxp_a_97_colonial_registry_events.txt")
        migration_event = _read("events/jxp_b_110_colonial_migration_events.txt")
        parse_text(trigger)
        parse_text(depth_trigger)
        parse_text(effect)
        parse_text(registry_event)
        parse_text(migration_event)
        self.assertIn("NOT = { has_country_flag = jxp_b_102_overseas_program_migrated }", trigger)
        self.assertEqual(1, effect.count("set_country_flag = jxp_b_102_overseas_program_migrated"))
        self.assertIn("jxp_a_consume_colonial_registry_interfaces_effect = yes", registry_event)
        self.assertIn("jxp_b_102_finalize_overseas_program_startup_migration_effect = yes", registry_event)
        self.assertLess(
            registry_event.index("jxp_a_consume_colonial_registry_interfaces_effect = yes"),
            registry_event.index("jxp_b_102_finalize_overseas_program_startup_migration_effect = yes"),
        )
        self.assertIn("jxp_b_110_colonial_depth_postcondition_trigger = yes", migration_event)
        self.assertIn("jxp_b_102_finalize_overseas_program_startup_migration_effect = yes", migration_event)
        self.assertIn("jxp_b_110_colonial_depth_postcondition_trigger = yes", effect)
        self.assertIn("has_country_flag = jxp_b_110_colonial_depth_migration_pending", effect)
        self.assertIn("set_country_flag = jxp_b_110_colonial_depth_migrated", effect)
        for anchor in (
            "jxp_b_94_mission_pacific_shore_foundation",
            "jxp_b_95_hkk_cold_harbors",
            "jxp_b_95_njf_japan_town_registers",
            "jxp_b_95_oia_star_paths",
            "jxp_b_114_tpf_japanese_seats",
        ):
            self.assertIn(f"has_mission = {anchor}", depth_trigger)
        self.assertIn("has_country_flag = jxp_b_tpf_federation_dissolved", depth_trigger)
        self.assertNotIn("every_country", effect)
        self.assertNotIn("every_province", effect)
        self.assertNotIn("mean_time_to_happen", effect)

    def test_non_successor_startup_migration_has_a_commit_point(self) -> None:
        effect = _read("common/scripted_effects/jxp_b_102_overseas_program_effects.txt")
        registry_event = _read("events/jxp_a_97_colonial_registry_events.txt")
        self.assertIn("NOT = { jxp_b_102_is_colonial_successor_trigger = yes }", effect)
        self.assertIn(
            "jxp_b_102_finalize_overseas_program_startup_migration_effect = yes",
            registry_event,
        )

    def test_all_five_colonial_successors_recover_identity_and_refresh_interfaces(self) -> None:
        trigger = _read("common/scripted_triggers/jxp_b_102_overseas_program_triggers.txt")
        effect = _read("common/scripted_effects/jxp_b_102_overseas_program_effects.txt")
        for tag in ("NYA", "HKK", "NJF", "OIA", "TPF"):
            self.assertIn(f"tag = {tag}", trigger + effect)
        for family in ("nya", "secondary", "tpf"):
            for refresh in ("mission", "idea"):
                self.assertIn(f"jxp_iface_b_{family}_needs_{refresh}_refresh", effect)
            self.assertIn(f"jxp_iface_b_{family}_needs_government_registry", effect)

    def test_recurring_systems_are_rearmed_without_monthly_world_scans(self) -> None:
        effect = _read("common/scripted_effects/jxp_b_102_overseas_program_effects.txt")
        self.assertIn("jxp_b_91_schedule_colonial_pulse_effect = yes", effect)
        self.assertIn("jxp_b_98_schedule_federal_council_effect = yes", effect)
        self.assertIn("country_event = { id = jxp_korea_campaign.941 days = 30 }", effect)
        society = _read("common/scripted_effects/jxp_b_91_colonial_society_effects.txt")
        federation = _read("common/scripted_effects/jxp_b_98_transpacific_state_effects.txt")
        self.assertIn("days = 365", society)
        self.assertIn("days = 1095", federation)

    def test_cleanup_covers_colonial_continental_korean_and_legacy_loops(self) -> None:
        effect = _read("common/scripted_effects/jxp_b_102_overseas_program_effects.txt")
        for cleanup in (
            "jxp_b_92_regional_colonial_cleanup_effect",
            "jxp_b_91_clear_colonial_charter_effect",
            "jxp_b_91_colonial_society_cleanup_effect",
            "jxp_b_99_clear_campaign_theater_effect",
            "jxp_b_101_korea_campaign_active_cleanup_effect",
            "jxp_76_pacific_network_cleanup_effect",
        ):
            self.assertIn(f"{cleanup} = yes", effect)

    def test_ai_entry_points_have_financial_and_route_brakes(self) -> None:
        regional = _read("decisions/jxp_b_92_regional_colonial_decisions.txt")
        secondary = _read("decisions/jxp_b_95_secondary_colonial_states_decisions.txt")
        continental = _read("decisions/jxp_b_99_continental_strategy_decisions.txt")
        korea = _read("decisions/jxp_b_101_korea_campaign_decisions.txt")
        china = _read("decisions/jxp_b_100_china_endgames_decisions.txt")
        self.assertGreaterEqual(regional.count("is_bankrupt = yes"), 6)
        self.assertEqual(3, secondary.count("factor = 0.01"))
        self.assertGreaterEqual(continental.count("is_bankrupt = yes"), 6)
        self.assertIn("factor = 0.10", korea)
        self.assertGreaterEqual(china.count("is_bankrupt = yes"), 4)

    def test_all_b_source_localisation_keys_are_unique_and_generated(self) -> None:
        key_pattern = re.compile(r"^\s+([^#\s][^:]*):\d+", re.MULTILINE)
        seen: dict[str, Path] = {}
        for source_path in sorted((MOD_ROOT / "localisation_source").glob("jxp_b_*.yml")):
            source = source_path.read_text(encoding="utf-8-sig")
            keys = key_pattern.findall(source)
            self.assertEqual(len(keys), len(set(keys)), source_path.name)
            for key in keys:
                self.assertNotIn(key, seen, f"duplicate key {key}: {seen.get(key)} and {source_path}")
                seen[key] = source_path
            active_name = source_path.name.replace("_utf8_source", "")
            active_path = MOD_ROOT / "localisation" / active_name
            self.assertTrue(active_path.is_file(), active_name)
            active = active_path.read_text(encoding="utf-8-sig")
            self.assertEqual(set(keys), set(key_pattern.findall(active)), active_name)
            self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"), active_name)


if __name__ == "__main__":
    unittest.main()
