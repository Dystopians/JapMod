from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.ijp_loop import (
    ACTIVE_LOC_FILE,
    DEBUG_DECISION_FILE,
    DECISION_FILE,
    DISASTER_FILE,
    EFFECT_FILE,
    EVENT_FILE,
    LEGACY_EVENT_FILE,
    MODIFIER_FILE,
    SOURCE_LOC_FILE,
    TRIGGER_FILE,
    check_ijp_loop,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_FILES = (
    TRIGGER_FILE,
    EFFECT_FILE,
    MODIFIER_FILE,
    DECISION_FILE,
    DEBUG_DECISION_FILE,
    EVENT_FILE,
    LEGACY_EVENT_FILE,
    DISASTER_FILE,
    SOURCE_LOC_FILE,
    ACTIVE_LOC_FILE,
)


def _copy_contract(root: Path) -> None:
    for relative in CONTRACT_FILES:
        source = LIVE_MOD_ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _mutate(root: Path, relative: Path, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8-sig")
    if old not in text:
        raise AssertionError(f"mutation needle not found in {relative}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _codes(root: Path) -> set[str]:
    return {issue.code for issue in check_ijp_loop(ValidationContext(root)).issues}


class IjpCommonwealthLoopTests(unittest.TestCase):
    def _temporary_contract(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        _copy_contract(root)
        return directory, root

    def test_live_ijp_loop_is_closed(self) -> None:
        result = check_ijp_loop(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(8, result.metrics["route_pressure_triggers"])
        self.assertEqual(3, result.metrics["repeatable_governance_choices"])
        self.assertEqual(2, result.metrics["exit_paths"])
        self.assertEqual(9, result.metrics["ai_weighted_options"])
        self.assertEqual(11, result.metrics["modifiers"])
        self.assertEqual(1, result.metrics["legacy_entry_hardened"])
        self.assertEqual(1, result.metrics["disaster_isolation"])
        self.assertEqual(1, result.metrics["map_contract"])

    def test_rejects_route_trigger_without_all_foreign_exclusions(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\t\t\thas_country_flag = jxp_path_wokou\n",
            "",
        )
        codes = _codes(root)
        self.assertIn("ijp_loop.trigger_contract", codes)
        self.assertIn("ijp_loop.route_exclusivity", codes)

    def test_rejects_production_route_without_shinto_gate(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(root, TRIGGER_FILE, "\treligion = shinto\n", "")
        codes = _codes(root)
        self.assertIn("ijp_loop.trigger_contract", codes)
        self.assertIn("ijp_loop.religion_gate", codes)

    def test_rejects_commons_without_both_estates(self) -> None:
        for estate in ("estate_church", "estate_burghers"):
            with self.subTest(estate=estate):
                _directory, root = self._temporary_contract()
                _mutate(root, TRIGGER_FILE, f"\thas_estate = {estate}\n", "")
                codes = _codes(root)
                self.assertIn("ijp_loop.trigger_contract", codes)
                self.assertIn("ijp_loop.estate_gate", codes)

    def test_rejects_active_cycle_without_disaster_isolation(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(root, TRIGGER_FILE, "\thas_any_disaster = no\n", "")
        codes = _codes(root)
        self.assertIn("ijp_loop.trigger_contract", codes)
        self.assertIn("ijp_loop.disaster_isolation", codes)

    def test_rejects_active_cycle_without_live_charter(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\thas_country_modifier = jxp_74_ijp_temple_market_charter\n",
            "",
        )
        codes = _codes(root)
        self.assertIn("ijp_loop.trigger_contract", codes)
        self.assertIn("ijp_loop.charter_lifecycle", codes)

    def test_rejects_entry_during_pending_route_reconcile(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\t\tNOT = { has_country_flag = jxp_74_ijp_route_guard_pending }\n",
            "",
        )
        self.assertIn("ijp_loop.entry_contract", _codes(root))

    def test_rejects_pressure_clamp_without_upper_bound(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\t\t\tset_variable = { which = jxp_74_ijp_pressure value = 100 }\n",
            "",
        )
        self.assertIn("ijp_loop.pressure_bounds", _codes(root))

    def test_rejects_permanent_governance_cooldown(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\t\t\tname = jxp_74_ijp_machishu_investment\n"
            "\t\t\t\tduration = 1825\n",
            "\t\t\t\tname = jxp_74_ijp_machishu_investment\n"
            "\t\t\t\tduration = -1\n",
        )
        codes = _codes(root)
        self.assertIn("ijp_loop.investment_contract", codes)
        self.assertIn("ijp_loop.modifier_duration", codes)

    def test_rejects_missing_player_transformation_exit(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\t\t\tjxp_74_ijp_transform_commonwealth_effect = yes\n",
            "",
        )
        self.assertIn("ijp_loop.exit_path", _codes(root))

    def test_rejects_player_decision_without_ai_policy(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\tai_will_do = {\n",
            "\t\tai_policy_removed = {\n",
        )
        self.assertIn("ijp_loop.ai_decision", _codes(root))

    def test_rejects_map_semantic_flag_substitution(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "jxp_map_compat_ikko_heartland",
            "jxp_map_compat_wokou_waters",
        )
        self.assertIn("ijp_loop.map_contract", _codes(root))

    def test_rejects_missing_vanilla_geography_fallback(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(root, TRIGGER_FILE, "\t\t\t\tarea = kinai_area\n", "")
        codes = _codes(root)
        self.assertIn("ijp_loop.trigger_contract", codes)
        self.assertIn("ijp_loop.map_fallback", codes)

    def test_rejects_debug_reset_without_public_route_exit(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "jxp_74_ijp_debug_reset_effect = {\n"
            "\tjxp_74_ijp_route_exit_effect = yes\n",
            "jxp_74_ijp_debug_reset_effect = {\n",
        )
        self.assertIn("ijp_loop.debug_cleanup", _codes(root))

    def test_rejects_route_exit_that_leaves_pending_guard(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "jxp_74_ijp_route_exit_effect = {\n"
            "\tjxp_74_ijp_cleanup_effect = yes\n"
            "\tclr_country_flag = jxp_74_ijp_route_guard_pending\n",
            "jxp_74_ijp_route_exit_effect = {\n"
            "\tjxp_74_ijp_cleanup_effect = yes\n",
        )
        self.assertIn("ijp_loop.route_exit", _codes(root))

    def test_rejects_legacy_entry_without_existing_ikko_flag_branch(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            LEGACY_EVENT_FILE,
            "\t\t\thas_country_flag = jxp_path_ikko\n",
            "",
        )
        self.assertIn("ijp_loop.legacy_entry_gate", _codes(root))

    def test_rejects_legacy_entry_bypassing_canonical_effect(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            LEGACY_EVENT_FILE,
            "\t\tjxp_74_ijp_route_entry_effect = yes\n",
            "\t\tset_country_flag = jxp_path_ikko\n",
        )
        self.assertIn("ijp_loop.legacy_entry_effect", _codes(root))

    def test_rejects_route_entry_without_next_day_reconcile(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\t\tcountry_event = { id = jxp_ijp_loop.5 days = 1 }\n",
            "\t\tcountry_event = { id = jxp_ijp_loop.5 days = 2 }\n",
        )
        self.assertIn("ijp_loop.route_reconcile", _codes(root))

    def test_rejects_cycle_start_without_fixed_expiry_schedule(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\tcountry_event = { id = jxp_ijp_loop.6 days = 3651 }\n",
            "\tcountry_event = { id = jxp_ijp_loop.6 days = 3650 }\n",
        )
        self.assertIn("ijp_loop.start_state", _codes(root))

    def test_rejects_expiry_without_generation_safe_charter_guard(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EVENT_FILE,
            "\t\t\t\tNOT = { has_country_modifier = jxp_74_ijp_temple_market_charter }\n",
            "",
        )
        self.assertIn("ijp_loop.expiry_lifecycle", _codes(root))

    def test_rejects_passive_cleanup_that_ignores_charter_expiry(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EVENT_FILE,
            "\t\tNOT = { jxp_74_ijp_cycle_active_trigger = yes }\n",
            "\t\tNOT = { jxp_74_ijp_route_trigger = yes }\n",
        )
        self.assertIn("ijp_loop.route_loss_cleanup", _codes(root))

    def test_rejects_hidden_route_cleanup_without_option(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(root, EVENT_FILE, "\n\toption = { name = \"OK\" }\n", "")
        self.assertIn("ijp_loop.route_loss_cleanup", _codes(root))

    def test_rejects_ikko_disaster_without_ijp_exclusion(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DISASTER_FILE,
            "\t\tNOT = { tag = IJP }\n",
            "",
        )
        self.assertIn("ijp_loop.disaster_contract", _codes(root))

    def test_rejects_route_rebuild_before_canonical_clear(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\tjxp_clear_all_route_flags_effect = yes\n",
            "",
        )
        self.assertIn("ijp_loop.route_entry_clear", _codes(root))


if __name__ == "__main__":
    unittest.main()
