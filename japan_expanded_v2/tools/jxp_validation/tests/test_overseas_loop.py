from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.overseas_loop import (
    ACTIVE_LOC_FILE,
    DEBUG_DECISION_FILE,
    DEBUG_ROOT_FILE,
    DECISION_FILE,
    EFFECT_FILE,
    EVENT_FILE,
    LEGACY_MODIFIER_FILE,
    MODIFIER_FILE,
    SOURCE_LOC_FILE,
    TRIGGER_FILE,
    check_overseas_loop,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_FILES = (
    TRIGGER_FILE,
    EFFECT_FILE,
    MODIFIER_FILE,
    LEGACY_MODIFIER_FILE,
    DECISION_FILE,
    DEBUG_DECISION_FILE,
    EVENT_FILE,
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
        for issue in check_overseas_loop(ValidationContext(root)).issues
    }


class PacificOverseasLoopTests(unittest.TestCase):
    def _temporary_contract(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        _copy_contract(root)
        return directory, root

    def test_live_overseas_loop_is_closed(self) -> None:
        result = check_overseas_loop(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(4, result.metrics["repeatable_investments"])
        self.assertEqual(2, result.metrics["exit_paths"])
        self.assertEqual(10, result.metrics["ai_weighted_options"])
        self.assertEqual(14, result.metrics["finite_modifiers"])
        self.assertEqual(1, result.metrics["debug_root"])
        self.assertEqual(1, result.metrics["standalone_contract"])
        self.assertEqual(0, result.metrics["legacy_signature_collisions"])

    def test_rejects_broad_entry_bypassing_private_trade_semantics(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\tjxp_allows_private_overseas_trade_trigger = yes\n",
            "\tjxp_can_use_overseas_expansion_trigger = yes\n",
        )
        self.assertIn("overseas_loop.entry_semantics", _codes(root))

    def test_rejects_route_profile_collapse(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\t\thas_country_flag = jxp_path_imperial\n",
            "",
        )
        self.assertIn("overseas_loop.route_profiles", _codes(root))

    def test_rejects_permanent_repeatable_investment(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\t\t\tname = jxp_76_manila_nagasaki_convoys\n"
            "\t\t\t\tduration = 1825\n",
            "\t\t\t\tname = jxp_76_manila_nagasaki_convoys\n"
            "\t\t\t\tduration = -1\n",
        )
        codes = _codes(root)
        self.assertIn("overseas_loop.investment_contract", codes)
        self.assertIn("overseas_loop.modifier_duration", codes)

    def test_rejects_legacy_california_signature_collision(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            MODIFIER_FILE,
            "jxp_76_california_settlement_compacts = {\n"
            "\tglobal_colonial_growth = 10\n"
            "\tproduction_efficiency = 0.05\n"
            "}",
            "jxp_76_california_settlement_compacts = {\n"
            "\tglobal_colonial_growth = 10\n"
            "\tglobal_tariffs = 0.10\n"
            "}",
        )
        self.assertIn("overseas_loop.legacy_signature_collision", _codes(root))

    def test_rejects_pressure_clamp_without_upper_bound(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\t\t\tset_variable = { which = jxp_76_pacific_pressure value = 100 }\n",
            "",
        )
        self.assertIn("overseas_loop.pressure_bounds", _codes(root))

    def test_rejects_cleanup_inventory_gap(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\tremove_country_modifier = jxp_76_california_settlement_compacts\n",
            "",
        )
        self.assertIn("overseas_loop.cleanup_modifier", _codes(root))

    def test_rejects_crisis_without_retrenchment_exit(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            EVENT_FILE,
            "\t\thidden_effect = { jxp_76_pacific_stand_down_effect = yes }\n",
            "",
        )
        self.assertIn("overseas_loop.crisis_exits", _codes(root))

    def test_rejects_hidden_loss_cleanup_without_option(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(root, EVENT_FILE, "\n\toption = { name = \"OK\" }\n", "")
        self.assertIn("overseas_loop.loss_cleanup", _codes(root))

    def test_rejects_player_decision_without_ai_policy(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DECISION_FILE,
            "\t\tai_will_do = {\n",
            "\t\tai_policy_removed = {\n",
        )
        self.assertIn("overseas_loop.ai_decision", _codes(root))

    def test_rejects_companion_only_reference(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\t\thas_country_flag = jxp_pacific_charter_enacted\n",
            "\t\thas_country_flag = jxp_pacific_charter_enacted\n"
            "\t\thas_province_flag = jxp_map_compat_wokou_waters\n",
        )
        self.assertIn("overseas_loop.map_contract", _codes(root))

    def test_rejects_debug_reset_not_reachable_from_canonical_root(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            DEBUG_ROOT_FILE,
            "\t\tjxp_76_pacific_debug_reset_effect = yes\n",
            "",
        )
        self.assertIn("overseas_loop.debug_root", _codes(root))


if __name__ == "__main__":
    unittest.main()
