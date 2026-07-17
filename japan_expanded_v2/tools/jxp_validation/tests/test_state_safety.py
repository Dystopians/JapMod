from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.state_safety import check_state_safety


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
LIVE_COMPANION_ROOT = LIVE_MOD_ROOT.parent / "japan_expanded_v2_map"


def _write(root: Path, relative: str, text: str) -> None:
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def _write_main_debug_roots(root: Path, event_cleanup: str = "") -> None:
    _write(
        root,
        "common/scripted_effects/debug.txt",
        "jxp_debug_clear_event_state_effect = {\n"
        f"{event_cleanup}"
        "}\n"
        "jxp_debug_clear_cooldowns_effect = { }\n"
        "jxp_debug_clear_route_state_effect = { }\n",
    )


def _codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


class StateLifecycleTests(unittest.TestCase):
    def test_transitive_debug_cleanup_closes_flag_and_modifier_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root,
                "events/content.txt",
                "country_event = {\n"
                " id = jxp_test.1\n"
                " trigger = { NOT = { has_country_flag = jxp_test_seen } }\n"
                " option = {\n"
                "  set_country_flag = jxp_test_seen\n"
                "  add_country_modifier = { name = jxp_test_reward duration = 30 }\n"
                " }\n"
                "}\n",
            )
            _write(
                root,
                "common/event_modifiers/test.txt",
                "jxp_test_reward = { prestige = 0.1 }\n",
            )
            _write_main_debug_roots(
                root,
                " jxp_nested_cleanup_effect = yes\n",
            )
            with (root / "common/scripted_effects/debug.txt").open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write(
                    "jxp_nested_cleanup_effect = {\n"
                    " clr_country_flag = jxp_test_seen\n"
                    " remove_country_modifier = jxp_test_reward\n"
                    "}\n"
                )

            result = check_state_safety(
                ValidationContext(root), minimum_disasters=0
            )
            safety_codes = {
                code
                for code in _codes(result)
                if code.startswith("state.") or code.startswith("modifier.")
            }
            self.assertEqual(safety_codes, set())

    def test_orphan_write_and_dangling_read_are_hard_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root,
                "events/content.txt",
                "country_event = {\n"
                " id = jxp_test.1\n"
                " trigger = { has_country_flag = jxp_missing_writer }\n"
                " option = { set_country_flag = jxp_orphan_writer }\n"
                "}\n",
            )
            _write_main_debug_roots(
                root, " clr_country_flag = jxp_orphan_writer\n"
            )
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=0
            )
            self.assertIn("state.flag_orphan_write", _codes(result))
            self.assertIn("state.flag_dangling_read", _codes(result))

    def test_dynamic_modifier_requires_lifecycle_and_debug_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root,
                "events/content.txt",
                "country_event = {\n"
                " id = jxp_test.1\n"
                " option = {\n"
                "  add_country_modifier = { name = jxp_unreset_reward duration = -1 }\n"
                " }\n"
                "}\n",
            )
            _write(
                root,
                "common/event_modifiers/test.txt",
                "jxp_unreset_reward = { prestige = 0.1 }\n",
            )
            _write_main_debug_roots(root)
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=0
            )
            self.assertIn("state.lifecycle_cleanup_missing", _codes(result))
            self.assertIn("state.debug_cleanup_missing", _codes(result))

    def test_companion_geography_contract_is_the_only_persistent_exception(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            main = workspace / "main"
            companion = workspace / "map"
            _write_main_debug_roots(main)
            _write(
                companion,
                "common/scripted_effects/map.txt",
                "jxp_map_debug_full_reset_effect = { }\n"
                "jxp_map_initialize_geography_contract_effect = {\n"
                " set_global_flag = jxp_map_geography_contract_v011\n"
                " set_global_flag = jxp_map_geography_contract_v012\n"
                " set_global_flag = jxp_map_geography_contract_v013\n"
                " set_province_flag = jxp_map_compat_ikko_heartland\n"
                " set_province_flag = jxp_map_compat_ryukyu_gateway\n"
                " set_province_flag = jxp_map_compat_setouchi\n"
                " set_province_flag = jxp_map_compat_shimabara_belt\n"
                " set_province_flag = jxp_map_compat_tsushima_channel\n"
                " set_province_flag = jxp_map_compat_wokou_waters\n"
                "}\n",
            )
            _write(
                companion,
                "common/scripted_triggers/map.txt",
                "jxp_map_contract_present_trigger = {\n"
                " has_global_flag = jxp_map_geography_contract_v011\n"
                " has_global_flag = jxp_map_geography_contract_v012\n"
                " has_global_flag = jxp_map_geography_contract_v013\n"
                " has_province_flag = jxp_map_compat_ikko_heartland\n"
                " has_province_flag = jxp_map_compat_ryukyu_gateway\n"
                " has_province_flag = jxp_map_compat_setouchi\n"
                " has_province_flag = jxp_map_compat_shimabara_belt\n"
                " has_province_flag = jxp_map_compat_tsushima_channel\n"
                " has_province_flag = jxp_map_compat_wokou_waters\n"
                "}\n",
            )
            result = check_state_safety(
                ValidationContext(main),
                ValidationContext(companion),
                minimum_disasters=0,
            )
            self.assertNotIn("state.lifecycle_cleanup_missing", _codes(result))
            self.assertNotIn("state.debug_cleanup_missing", _codes(result))

    def test_mutation_removing_nested_clearer_reopens_lifecycle_debt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root,
                "events/content.txt",
                "country_event = {\n"
                " id = jxp_test.1\n"
                " trigger = { NOT = { has_country_flag = jxp_test_persistent } }\n"
                " option = {\n"
                "  set_country_flag = jxp_test_persistent\n"
                "  add_country_modifier = { name = jxp_test_permanent duration = -1 }\n"
                " }\n"
                "}\n",
            )
            _write(
                root,
                "common/event_modifiers/test.txt",
                "jxp_test_permanent = { prestige = 0.1 }\n",
            )
            cleanup = (
                "jxp_debug_clear_event_state_effect = { jxp_debt_cleanup_effect = yes }\n"
                "jxp_debug_clear_cooldowns_effect = { }\n"
                "jxp_debug_clear_route_state_effect = { }\n"
                "jxp_debt_cleanup_effect = {\n"
                " clr_country_flag = jxp_test_persistent\n"
                " remove_country_modifier = jxp_test_permanent\n"
                "}\n"
            )
            _write(root, "common/scripted_effects/debug.txt", cleanup)
            baseline = check_state_safety(
                ValidationContext(root), minimum_disasters=0
            )
            self.assertNotIn("state.lifecycle_cleanup_missing", _codes(baseline))
            self.assertNotIn("state.debug_cleanup_missing", _codes(baseline))

            for clearer in (
                " clr_country_flag = jxp_test_persistent\n",
                " remove_country_modifier = jxp_test_permanent\n",
            ):
                with self.subTest(removed=clearer.strip()):
                    _write(
                        root,
                        "common/scripted_effects/debug.txt",
                        cleanup.replace(clearer, "", 1),
                    )
                    mutated = check_state_safety(
                        ValidationContext(root), minimum_disasters=0
                    )
                    self.assertIn(
                        "state.lifecycle_cleanup_missing", _codes(mutated)
                    )
                    self.assertIn("state.debug_cleanup_missing", _codes(mutated))

    def test_mutation_reintroducing_removed_marker_is_an_orphan_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = (
                "country_event = {\n"
                " id = jxp_test.1\n"
                " trigger = { NOT = { has_country_flag = jxp_test_seen } }\n"
                " option = { set_country_flag = jxp_test_seen }\n"
                "}\n"
            )
            _write(root, "events/content.txt", content)
            _write_main_debug_roots(
                root, " clr_country_flag = jxp_test_seen\n"
            )
            baseline = check_state_safety(
                ValidationContext(root), minimum_disasters=0
            )
            self.assertNotIn("state.flag_orphan_write", _codes(baseline))

            _write(
                root,
                "events/content.txt",
                content.replace(
                    " option = { set_country_flag = jxp_test_seen }\n",
                    " option = {\n"
                    "  set_country_flag = jxp_test_seen\n"
                    "  set_country_flag = jxp_removed_legacy_seen\n"
                    " }\n",
                    1,
                ),
            )
            mutated = check_state_safety(
                ValidationContext(root), minimum_disasters=0
            )
            self.assertTrue(
                any(
                    issue.code == "state.flag_orphan_write"
                    and "jxp_removed_legacy_seen" in issue.message
                    for issue in mutated.issues
                )
            )

    def test_live_release_surface_has_zero_state_lifecycle_issues(self) -> None:
        result = check_state_safety(
            ValidationContext(LIVE_MOD_ROOT),
            ValidationContext(LIVE_COMPANION_ROOT),
        )
        state_issues = [
            f"{issue.code}: {issue.message}"
            for issue in result.issues
            if issue.code.startswith("state.") or issue.code.startswith("modifier.")
        ]
        self.assertEqual(state_issues, [])
        self.assertEqual(result.metrics["flag_orphan_writes"], 0)
        self.assertEqual(result.metrics["flag_dangling_reads"], 0)
        self.assertEqual(result.metrics["lifecycle_cleanup_missing"], 0)
        self.assertEqual(result.metrics["debug_cleanup_missing"], 0)


class SwordHuntSafetyTests(unittest.TestCase):
    VALID_DECISION = (
        "country_decisions = {\n"
        " jxp_decision_issue_sword_hunt = {\n"
        "  potential = {\n"
        "   jxp_is_japanese_polity_trigger = yes\n"
        "   NOT = { is_subject_of_type = daimyo_vassal }\n"
        "   NOT = { has_country_modifier = subject_sword_hunt }\n"
        "   NOT = { has_country_modifier = overlord_sword_hunt }\n"
        "  }\n"
        "  allow = { always = yes }\n"
        "  effect = { }\n"
        " }\n"
        "}\n"
    )

    def _check(self, text: str):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        _write_main_debug_roots(root)
        _write(root, "decisions/jxp_polity_decisions.txt", text)
        return check_state_safety(ValidationContext(root), minimum_disasters=0)

    def test_valid_sword_hunt_gate_matches_identity_and_vanilla_exclusions(self) -> None:
        self.assertNotIn(
            "safety.sword_hunt_gate",
            _codes(self._check(self.VALID_DECISION)),
        )

    def test_mutating_any_sword_hunt_exclusion_is_a_hard_failure(self) -> None:
        required_lines = (
            "   jxp_is_japanese_polity_trigger = yes\n",
            "   NOT = { is_subject_of_type = daimyo_vassal }\n",
            "   NOT = { has_country_modifier = subject_sword_hunt }\n",
            "   NOT = { has_country_modifier = overlord_sword_hunt }\n",
        )
        for line in required_lines:
            with self.subTest(removed=line.strip()):
                mutated = self.VALID_DECISION.replace(line, "", 1)
                self.assertNotEqual(mutated, self.VALID_DECISION)
                self.assertIn(
                    "safety.sword_hunt_gate",
                    _codes(self._check(mutated)),
                )


class DisasterSafetyTests(unittest.TestCase):
    def _write_generic_disaster(
        self,
        root: Path,
        *,
        japanese_gate: bool = True,
        resolve_on_start: bool = False,
    ) -> None:
        japanese = " jxp_is_japanese_polity_trigger = yes\n" if japanese_gate else ""
        _write(
            root,
            "common/disasters/test.txt",
            "jxp_test_crisis = {\n"
            " potential = {\n"
            "  normal_or_historical_nations = yes\n"
            f"{japanese}"
            "  is_free_or_tributary_trigger = yes\n"
            "  NOT = { has_country_flag = jxp_test_crisis_resolved }\n"
            " }\n"
            " can_start = {\n"
            "  has_any_disaster = no\n"
            "  is_year = 1500\n"
            "  OR = { NOT = { stability = 1 } war_exhaustion = 3 }\n"
            "  any_owned_province = { religion = catholic }\n"
            " }\n"
            " can_stop = { has_country_flag = jxp_test_crisis_resolved }\n"
            " progress = {\n"
            "  modifier = { factor = 1 war_exhaustion = 3 }\n"
            "  modifier = { factor = -1 stability = 1 }\n"
            " }\n"
            " can_end = { OR = {\n"
            "  has_country_flag = jxp_test_crisis_resolved\n"
            "  AND = { stability = 1 religious_unity = 0.9 }\n"
            " } }\n"
            " modifier = { global_unrest = 1 }\n"
            " on_start = jxp_test.1\n"
            " on_end = jxp_test.2\n"
            "}\n",
        )
        start_effect = (
            " set_country_flag = jxp_test_crisis_resolved\n"
            if resolve_on_start
            else " add_prestige = -1\n"
        )
        _write(
            root,
            "events/test.txt",
            "country_event = {\n"
            " id = jxp_test.1\n"
            " is_triggered_only = yes\n"
            f" option = {{ name = jxp_test.1.a {start_effect} }}\n"
            "}\n"
            "country_event = {\n"
            " id = jxp_test.2\n"
            " title = none desc = none picture = none hidden = yes\n"
            " is_triggered_only = yes\n"
            " immediate = {\n"
            "  set_country_flag = jxp_test_crisis_resolved\n"
            "  remove_country_modifier = jxp_test_crisis_state\n"
            " }\n"
            " option = { name = OK }\n"
            "}\n",
        )
        _write(
            root,
            "common/event_modifiers/test.txt",
            "jxp_test_crisis_state = { global_unrest = 1 }\n",
        )
        _write_main_debug_roots(
            root,
            " clr_country_flag = jxp_test_crisis_resolved\n"
            " remove_country_modifier = jxp_test_crisis_state\n",
        )

    def test_disaster_false_positive_gate_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_generic_disaster(root, japanese_gate=False)
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=1
            )
            self.assertIn("disaster.false_positive_gate", _codes(result))

    def test_on_start_cannot_resolve_every_disaster_choice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_generic_disaster(root, resolve_on_start=True)
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=1
            )
            self.assertIn("disaster.instant_resolution", _codes(result))

    def test_disaster_on_end_must_reference_an_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_generic_disaster(root)
            source = root / "common" / "disasters" / "test.txt"
            text = source.read_text(encoding="utf-8")
            source.write_text(
                text.replace(
                    " on_end = jxp_test.2\n",
                    " on_end = { set_country_flag = jxp_test_crisis_resolved }\n",
                    1,
                ),
                encoding="utf-8",
            )
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=1
            )
            self.assertIn("disaster.end_event_reference", _codes(result))

    def test_hidden_event_requires_complete_engine_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_generic_disaster(root)
            source = root / "events" / "test.txt"
            text = source.read_text(encoding="utf-8")
            source.write_text(
                text.replace(" title = none", "", 1),
                encoding="utf-8",
            )
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=1
            )
            self.assertIn("event.hidden_contract", _codes(result))

    def test_engine_rejected_modifier_alias_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_generic_disaster(root)
            source = root / "common" / "event_modifiers" / "test.txt"
            source.write_text(
                "jxp_test_crisis_state = { goods_produced_modifier = 0.1 }\n",
                encoding="utf-8",
            )
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=1
            )
            self.assertIn("modifier.engine_alias", _codes(result))

    def test_known_disaster_requires_dedicated_debug_seed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write(
                root,
                "common/disasters/ikko.txt",
                "jxp_ikko_rising = {\n"
                " potential = {\n"
                "  normal_or_historical_nations = yes\n"
                "  jxp_is_japanese_polity_trigger = yes\n"
                "  is_free_or_tributary_trigger = yes\n"
                "  NOT = { has_country_flag = jxp_ikko_rising_resolved }\n"
                "  NOT = { jxp_has_any_route_trigger = yes }\n"
                "  NOT = { tag = IJP }\n"
                " }\n"
                " can_start = {\n"
                "  has_any_disaster = no is_year = 1470 num_of_cities = 8\n"
                "  NOT = { jxp_tenka_order_at_least_50 = yes }\n"
                "  OR = { NOT = { stability = 1 } war_exhaustion = 3 }\n"
                "  any_owned_province = {\n"
                "   has_province_flag = jxp_map_compat_ikko_heartland\n"
                "  }\n"
                " }\n"
                " can_stop = { has_country_flag = jxp_ikko_rising_resolved }\n"
                " progress = {\n"
                "  modifier = { factor = 1 war_exhaustion = 3 }\n"
                "  modifier = { factor = -1 stability = 1 }\n"
                " }\n"
                " can_end = { OR = {\n"
                "  has_country_flag = jxp_ikko_rising_resolved\n"
                "  AND = { stability = 1 religious_unity = 0.9 }\n"
                " } }\n"
                " modifier = { global_unrest = 1 }\n"
                " on_start = jxp_ikko.6\n"
                " on_end = jxp_ikko.7\n"
                "}\n",
            )
            _write(
                root,
                "events/ikko.txt",
                "country_event = {\n"
                " id = jxp_ikko.6 is_triggered_only = yes\n"
                " option = { name = jxp_ikko.6.a add_prestige = -1 }\n"
                "}\n"
                "country_event = {\n"
                " id = jxp_ikko.7\n"
                " title = none desc = none picture = none hidden = yes\n"
                " is_triggered_only = yes\n"
                " immediate = {\n"
                "  set_country_flag = jxp_ikko_rising_resolved\n"
                "  remove_country_modifier = jxp_ikko_disaster_modifier\n"
                " }\n"
                " option = { name = OK }\n"
                "}\n",
            )
            _write(
                root,
                "decisions/debug.txt",
                "country_decisions = {\n"
                " jxp_debug_fire_ikko_6 = {\n"
                "  effect = { country_event = { id = jxp_ikko.6 } }\n"
                " }\n"
                "}\n",
            )
            _write(
                root,
                "common/event_modifiers/ikko.txt",
                "jxp_ikko_disaster_modifier = { global_unrest = 1 }\n",
            )
            _write_main_debug_roots(
                root,
                " clr_country_flag = jxp_ikko_rising_resolved\n"
                " remove_country_modifier = jxp_ikko_disaster_modifier\n",
            )
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=1
            )
            self.assertIn("disaster.debug_seed_missing", _codes(result))

    def test_custom_disaster_progress_cannot_compile_in_scripted_effects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_main_debug_roots(root)
            with (root / "common/scripted_effects/debug.txt").open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write(
                    "jxp_debug_seed_test_pressure_effect = {\n"
                    " add_disaster_progress = {\n"
                    "  disaster = jxp_test_crisis\n"
                    "  value = 100\n"
                    " }\n"
                    "}\n"
                )
            result = check_state_safety(
                ValidationContext(root), minimum_disasters=0
            )
            self.assertIn("disaster.debug_seed_load_order", _codes(result))

    def test_live_disaster_contracts_are_closed(self) -> None:
        result = check_state_safety(
            ValidationContext(LIVE_MOD_ROOT),
            ValidationContext(LIVE_COMPANION_ROOT),
        )
        disaster_issues = [
            f"{issue.code}: {issue.message}"
            for issue in result.issues
            if issue.code.startswith("disaster.")
        ]
        self.assertEqual(disaster_issues, [])
        self.assertEqual(result.metrics["disasters"], 4)
        self.assertEqual(result.metrics["disaster_contracts"], 4)
        self.assertEqual(result.metrics["disaster_debug_progress_scripted"], 0)
        self.assertEqual(result.metrics["disaster_debug_progress_events"], 4)

    def test_tenmei_scale_gate_requires_semantic_capacity(self) -> None:
        live_text = (
            LIVE_MOD_ROOT
            / "common"
            / "disasters"
            / "jxp_japanese_disasters.txt"
        ).read_text(encoding="utf-8")
        needle = "\t\ttotal_development = 250\n"
        self.assertEqual(live_text.count(needle), 1)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_main_debug_roots(root)
            _write(
                root,
                "common/disasters/jxp_japanese_disasters.txt",
                live_text.replace(needle, "", 1),
            )
            result = check_state_safety(ValidationContext(root))
            self.assertTrue(
                any(
                    issue.code == "disaster.false_positive_gate"
                    and "jxp_tenmei_famine" in issue.message
                    and "total_development = 250" in issue.message
                    for issue in result.issues
                )
            )


if __name__ == "__main__":
    unittest.main()
