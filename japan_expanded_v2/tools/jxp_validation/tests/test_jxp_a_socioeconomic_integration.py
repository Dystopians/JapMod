from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

from jxp_validation.clausewitz import parse_file


MAIN_ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = (
    MAIN_ROOT
    / "tools"
    / "jxp_a_socioeconomic_builder"
    / "build_integration.py"
)


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "jxp_a_build_socioeconomic_integration", BUILDER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load build_integration.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


class SocioeconomicIntegrationTests(unittest.TestCase):
    def test_generated_outputs_are_current_and_gameplay_parses(self) -> None:
        for relative, expected in BUILDER.payloads().items():
            path = MAIN_ROOT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file())
                self.assertEqual(expected, path.read_bytes())
                if path.suffix == ".txt":
                    parse_file(path)

    def test_migration_is_ordered_and_only_commits_after_postconditions(self) -> None:
        text = (
            MAIN_ROOT
            / "common/scripted_effects/jxp_a_106_socioeconomic_integration_effects.txt"
        ).read_text(encoding="utf-8")
        ordered = (
            "jxp_a_105_capture_legacy_mission_progress_effect = yes",
            "jxp_a_105_reconcile_founder_legacy_effect = yes",
            "jxp_a_105_reconcile_unification_method_effect = yes",
            "jxp_a_reconcile_japanese_estates_effect = yes",
            "jxp_a_reconcile_market_stage = yes",
            "jxp_a_reconcile_companies_effect = yes",
            "jxp_a_105_migrate_mission_schema_effect = yes",
            "jxp_a_106_socioeconomic_migration_postconditions_trigger = yes",
        )
        positions = [text.index(token, text.index("jxp_a_run_socioeconomic_migration_effect")) for token in ordered]
        self.assertEqual(sorted(positions), positions)
        postcondition = positions[-1]
        self.assertGreater(
            text.index("set_country_flag = jxp_a_socioeconomic_migration_v110", postcondition),
            postcondition,
        )
        self.assertIn("country_event = { id = jxp_a_socioeconomic_integration.2 days = 1 }", text)
        capture = text.index(
            "jxp_a_105_capture_legacy_mission_progress_effect = yes",
            text.index("jxp_a_run_socioeconomic_migration_effect"),
        )
        guard = text.rfind(
            "NOT = { has_country_flag = jxp_a_socioeconomic_legacy_snapshot_ready }",
            0,
            capture,
        )
        self.assertNotEqual(-1, guard)
        self.assertLess(guard, capture)
        self.assertGreater(
            text.index(
                "clr_country_flag = jxp_a_socioeconomic_legacy_snapshot_ready",
                postcondition,
            ),
            postcondition,
        )

    def test_dispatch_is_bounded_and_colonial_successors_are_cleaned(self) -> None:
        on_actions = (
            MAIN_ROOT
            / "common/on_actions/jxp_a_106_socioeconomic_integration_on_actions.txt"
        ).read_text(encoding="utf-8")
        effects = (
            MAIN_ROOT
            / "common/scripted_effects/jxp_a_106_socioeconomic_integration_effects.txt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("on_monthly_pulse", on_actions)
        self.assertNotIn("every_country", on_actions + effects)
        self.assertNotIn("every_province", on_actions + effects)
        self.assertIn("on_startup", on_actions)
        self.assertIn("on_yearly_pulse", on_actions)
        self.assertIn(
            "jxp_a_106_convert_legacy_permanent_rewards_effect = yes", on_actions
        )
        self.assertIn("jxp_is_colonial_successor_tag_trigger = yes", effects)
        self.assertIn("jxp_a_106_full_socioeconomic_cleanup_effect = yes", effects)
        cleanup = effects.split(
            "jxp_a_106_full_socioeconomic_cleanup_effect = {", 1
        )[1].split("\n}\n", 1)[0]
        self.assertIn("jxp_a_105_full_cleanup_effect = yes", cleanup)
        self.assertIn("remove_country_modifier = jxp_three_capitals_ledgers", cleanup)
        self.assertIn("remove_country_modifier = jxp_a_buddhist_temple_credit", cleanup)

    def test_company_core_postcondition_matches_actual_initializer(self) -> None:
        triggers = (
            MAIN_ROOT
            / "common/scripted_triggers/jxp_a_106_socioeconomic_integration_triggers.txt"
        ).read_text(encoding="utf-8")
        block = triggers.split(
            "jxp_a_106_should_initialize_company_core_trigger = {", 1
        )[1].split("\n}\n", 1)[0]
        self.assertIn("jxp_is_unified_japan_state_trigger = yes", block)
        self.assertIn("jxp_a_market_stage_at_least_3_trigger = yes", block)
        self.assertNotIn("has_country_flag = jxp_a_market_stage_2", block)
        self.assertIn("jxp_a_any_socioeconomic_persistent_state_trigger = yes", triggers)
        self.assertIn("jxp_a_105_any_persistent_state_trigger = yes", triggers)
        self.assertIn("jxp_a_105_founder_legacy_consistent_trigger = yes", triggers)
        self.assertIn("jxp_a_105_unification_method_consistent_trigger = yes", triggers)
        self.assertIn("jxp_a_105_profile_state_consistent_trigger = yes", triggers)

    def test_frozen_permanent_rewards_are_converted_once_to_twenty_years(self) -> None:
        effects = (
            MAIN_ROOT
            / "common/scripted_effects/jxp_a_106_socioeconomic_integration_effects.txt"
        ).read_text(encoding="utf-8")
        block = effects.split(
            "jxp_a_106_convert_legacy_permanent_rewards_effect = {", 1
        )[1].split("\n}\n", 1)[0]
        for modifier, marker in (
            (
                "jxp_three_capitals_ledgers",
                "jxp_a_106_three_capitals_ledgers_converted",
            ),
            (
                "jxp_a_buddhist_temple_credit",
                "jxp_a_106_buddhist_temple_credit_converted",
            ),
        ):
            self.assertIn(f"has_country_modifier = {modifier}", block)
            self.assertIn(f"NOT = {{ has_country_flag = {marker} }}", block)
            self.assertIn(
                f"add_country_modifier = {{ name = {modifier} duration = 7300 }}",
                block,
            )
            self.assertIn(f"set_country_flag = {marker}", block)
        self.assertNotIn("duration = -1", block)

    def test_gazetteer_exposes_required_read_only_state(self) -> None:
        events = (
            MAIN_ROOT / "events/jxp_a_106_socioeconomic_integration_events.txt"
        ).read_text(encoding="utf-8")
        for token in (
            "jxp_a_socioeconomic_integration.credit.ready",
            "jxp_a_socioeconomic_integration.director.state",
            "jxp_a_socioeconomic_integration.director.merchant",
            "jxp_a_socioeconomic_integration.director.warrior",
            "jxp_a_socioeconomic_integration.director.religious",
            "jxp_a_socioeconomic_integration.director.mixed",
            "jxp_a_socioeconomic_integration.estate.communes",
            "jxp_a_socioeconomic_integration.company.mining.nationalized",
            "jxp_a_socioeconomic_integration.company.state.distressed",
            "jxp_a_socioeconomic_integration.request.red_seal",
            "jxp_a_socioeconomic_integration.request.continental",
            "jxp_a_socioeconomic_integration.capstone.complete",
            "jxp_a_socioeconomic_integration.identity.commercial",
            "jxp_a_socioeconomic_integration.branch.merchant",
            "jxp_a_socioeconomic_integration.founder.bureaucratic",
            "jxp_a_socioeconomic_integration.unification.league",
            "jxp_a_socioeconomic_integration.era.ocean.high",
        ):
            self.assertIn(token, events)

    def test_readable_localisation_matches_escaped_active_mirror(self) -> None:
        source = (
            MAIN_ROOT
            / "localisation_source/jxp_a_106_socioeconomic_guide_l_english_utf8_source.yml"
        ).read_text(encoding="utf-8")
        active = (
            MAIN_ROOT
            / "localisation/jxp_a_106_socioeconomic_guide_l_english.yml"
        ).read_bytes()
        self.assertTrue(active.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(
            BUILDER.load_escape_text()(source).encode("utf-8-sig"), active
        )
        for stage in range(1, 5):
            self.assertNotIn(f"\n jxp_a_market_stage_{stage}:0 ", source)

    def test_toyotomi_tag_transaction_reconciles_the_central_system(self) -> None:
        effects = (
            MAIN_ROOT / "common/scripted_effects/jxp_70_toyotomi_effects.txt"
        ).read_text(encoding="utf-8")
        start = effects.index("jxp_establish_toyotomi_identity_effect = {")
        change = effects.index("change_tag = TOY", start)
        reconcile = effects.index(
            "jxp_a_reconcile_socioeconomic_system_effect = yes", start
        )
        refresh = effects.index("jxp_refresh_route_missions_effect = yes", start)
        self.assertLess(change, reconcile)
        self.assertLess(reconcile, refresh)

    def test_master_builder_passes_the_pinned_game_root_to_estates(self) -> None:
        master = (
            MAIN_ROOT
            / "tools/jxp_a_socioeconomic_builder/build_socioeconomic_system.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"--game-root"', master)
        self.assertIn('required=True', master)
        self.assertIn('if name == "build_estates.py"', master)
        self.assertIn('command.extend(("--game-root", str(args.game_root)))', master)

    def test_commercial_route_cannot_fall_into_legacy_route_formations(self) -> None:
        paths = (
            "common/scripted_triggers/jxp_scripted_triggers.txt",
            "decisions/jxp_polity_decisions.txt",
            "decisions/jxp_10_popular_maritime_decisions.txt",
            "events/jxp_realm_events.txt",
            "events/jxp_reformed_events.txt",
            "events/jxp_kaikyo_events.txt",
            "events/jxp_ikko_events.txt",
            "events/jxp_wokou_events.txt",
        )
        for relative in paths:
            with self.subTest(path=relative):
                text = (MAIN_ROOT / relative).read_text(encoding="utf-8-sig")
                self.assertIn(
                    "NOT = { has_country_flag = jxp_path_commercial_council }",
                    text,
                )

        government = (MAIN_ROOT / "common/governments/00_governments.txt").read_text(
            encoding="utf-8-sig"
        )
        for reform in (
            "jxp_a_105_commercial_council_state_reform",
            "jxp_a_105_commercial_shogunate_reform",
            "jxp_a_105_commercial_merchant_council_reform",
            "jxp_a_105_commercial_company_empire_reform",
        ):
            self.assertIn(reform, government)


if __name__ == "__main__":
    unittest.main()
