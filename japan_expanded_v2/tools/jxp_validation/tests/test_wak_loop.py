from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.wak_loop import (
    ACTIVE_LOC_FILE,
    DEBUG_DECISION_FILE,
    DEBUG_ROOT_FILE,
    DECISION_FILE,
    EFFECT_FILE,
    EVENT_FILE,
    LEGACY_EVENT_FILE,
    MODIFIER_FILE,
    SOURCE_LOC_FILE,
    TRIGGER_FILE,
    check_wak_loop,
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
    DEBUG_ROOT_FILE,
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
    return {
        issue.code
        for issue in check_wak_loop(ValidationContext(root)).issues
    }


class WakLongLoopTests(unittest.TestCase):
    def _temporary_contract(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        _copy_contract(root)
        return directory, root

    def test_live_wak_loop_is_closed(self) -> None:
        result = check_wak_loop(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(3, result.metrics["repeatable_investments"])
        self.assertEqual(2, result.metrics["exit_paths"])
        self.assertEqual(9, result.metrics["ai_weighted_options"])
        self.assertEqual(11, result.metrics["modifiers"])
        self.assertEqual(1, result.metrics["map_contract"])
        self.assertEqual(1, result.metrics["legacy_entry_hardened"])
        self.assertEqual(1, result.metrics["debug_root"])

    def test_rejects_entry_without_exclusive_wak_route(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\t\tjxp_72_wak_route_trigger = yes\n",
            "",
        )
        self.assertIn("wak_loop.entry_gate", _codes(root))

    def test_rejects_active_cycle_without_live_charter(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\thas_country_modifier = jxp_72_wak_sea_league_charter\n",
            "",
        )
        codes = _codes(root)
        self.assertIn("wak_loop.trigger_contract", codes)
        self.assertIn("wak_loop.charter_lifecycle", codes)

    def test_rejects_permanent_repeatable_investment(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\t\t\tname = jxp_72_wak_rotating_letters\n"
            "\t\t\t\tduration = 1825\n",
            "\t\t\t\tname = jxp_72_wak_rotating_letters\n"
            "\t\t\t\tduration = -1\n",
        )
        codes = _codes(root)
        self.assertIn("wak_loop.investment_cooldown", codes)
        self.assertIn("wak_loop.modifier_duration", codes)

    def test_rejects_crisis_without_pressure_threshold(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EVENT_FILE,
            "\ttrigger = {\n"
            "\t\tjxp_72_wak_cycle_active_trigger = yes\n"
            "\t\tjxp_72_wak_pressure_at_least_85_trigger = yes\n"
            "\t\tNOT = { has_country_modifier = jxp_72_wak_crisis_recess }\n"
            "\t}\n",
            "\ttrigger = {\n"
            "\t\tjxp_72_wak_cycle_active_trigger = yes\n"
            "\t\tNOT = { has_country_modifier = jxp_72_wak_crisis_recess }\n"
            "\t}\n",
        )
        self.assertIn("wak_loop.pressure_crisis", _codes(root))

    def test_rejects_missing_player_transformation_exit(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\t\t\tjxp_72_wak_transform_to_maritime_state_effect = yes\n",
            "",
        )
        self.assertIn("wak_loop.exit_path", _codes(root))

    def test_rejects_player_decision_without_ai_policy(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\tai_will_do = {\n",
            "\t\tai_policy_removed = {\n",
        )
        self.assertIn("wak_loop.ai_decision", _codes(root))

    def test_rejects_semantic_geography_without_standalone_fallback(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(root, TRIGGER_FILE, "\t\tnum_of_ports = 8\n", "")
        codes = _codes(root)
        self.assertIn("wak_loop.trigger_contract", codes)
        self.assertIn("wak_loop.map_fallback", codes)

    def test_rejects_cleanup_that_leaves_pressure_behind(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "jxp_72_wak_cleanup_effect = {\n"
            "\tclr_country_flag = jxp_72_wak_cycle_active\n"
            "\tset_variable = { which = jxp_72_wak_pressure value = 0 }\n",
            "jxp_72_wak_cleanup_effect = {\n"
            "\tclr_country_flag = jxp_72_wak_cycle_active\n",
        )
        self.assertIn("wak_loop.cleanup_state", _codes(root))

    def test_rejects_legacy_entry_without_canonical_clear(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            LEGACY_EVENT_FILE,
            "\t\tjxp_clear_all_route_flags_effect = yes\n",
            "",
        )
        self.assertIn("wak_loop.legacy_entry_clear", _codes(root))

    def test_rejects_hidden_route_cleanup_without_option(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(root, EVENT_FILE, "\n\toption = { name = \"OK\" }\n", "")
        self.assertIn("wak_loop.route_loss_cleanup", _codes(root))

    def test_rejects_passive_cleanup_that_ignores_charter_expiry(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EVENT_FILE,
            "\t\tNOT = { jxp_72_wak_cycle_active_trigger = yes }\n",
            "\t\tNOT = { jxp_72_wak_route_trigger = yes }\n",
        )
        self.assertIn("wak_loop.route_loss_cleanup", _codes(root))

    def test_rejects_cycle_start_without_fixed_expiry_schedule(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\tcountry_event = { id = jxp_wak_loop.5 days = 3651 }\n",
            "\tcountry_event = { id = jxp_wak_loop.5 days = 3650 }\n",
        )
        self.assertIn("wak_loop.start_state", _codes(root))

    def test_rejects_expiry_without_generation_safe_charter_guard(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EVENT_FILE,
            "\t\t\t\tNOT = { has_country_modifier = jxp_72_wak_sea_league_charter }\n",
            "",
        )
        self.assertIn("wak_loop.expiry_lifecycle", _codes(root))

    def test_rejects_debug_reset_not_reachable_from_canonical_root(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DEBUG_ROOT_FILE,
            "\tjxp_72_wak_debug_reset_effect = yes\n",
            "",
        )
        self.assertIn("wak_loop.debug_root", _codes(root))


if __name__ == "__main__":
    unittest.main()
