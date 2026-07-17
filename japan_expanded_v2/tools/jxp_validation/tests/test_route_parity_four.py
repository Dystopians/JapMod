from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.route_parity_four import (
    ACTIVE_LOC_FILE,
    DEBUG_DECISION_FILE,
    DECISION_FILE,
    EVENT_FILE,
    MODIFIER_FILE,
    RESET_EFFECT_FILE,
    ROUTE_EFFECT_FILE,
    SOURCE_LOC_FILE,
    TRIGGER_FILE,
    check_route_parity_four_content,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_FILES = (
    TRIGGER_FILE,
    EVENT_FILE,
    DECISION_FILE,
    DEBUG_DECISION_FILE,
    MODIFIER_FILE,
    RESET_EFFECT_FILE,
    ROUTE_EFFECT_FILE,
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
    changed = text.replace(old, new, 1)
    if changed == text:
        raise AssertionError(f"mutation anchor not found in {relative}: {old!r}")
    path.write_text(changed, encoding="utf-8")


class FourRouteParityContractTests(unittest.TestCase):
    def test_live_four_route_slice_is_closed(self) -> None:
        result = check_route_parity_four_content(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(8, result.metrics["route_gates"])
        self.assertEqual(4, result.metrics["native_events"])
        self.assertEqual(12, result.metrics["reform_options"])
        self.assertEqual(4, result.metrics["native_decisions"])
        self.assertEqual(4, result.metrics["debug_entries"])
        self.assertEqual(13, result.metrics["modifiers"])
        self.assertEqual(13, result.metrics["route_cleanup"])
        self.assertEqual(1, result.metrics["route_cleanup_hook"])
        self.assertEqual(4, result.metrics["cross_route_cleanup"])

    def test_rejects_missing_mutual_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                TRIGGER_FILE,
                "\t\t\thas_country_flag = jxp_path_open_trade\n",
                "",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.trigger_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_missing_one_of_twelve_reform_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                EVENT_FILE,
                "\t\t\thas_reform = jxp_reform_kaikyo_spice_guard\n",
                "\t\t\thas_reform = jxp_reform_kaikyo_spice_guard_broken\n",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.option_reform_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_option_without_exact_attribute_tradeoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                EVENT_FILE,
                "\t\tjxp_subtract_tenka_order_5_effect = yes\n",
                "",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.option_attribute_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_option_without_contextual_ai_weight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                EVENT_FILE,
                "\t\tai_chance = {\n",
                "\t\tai_weight = {\n",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.option_ai_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_permanent_result_modifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                EVENT_FILE,
                "\t\t\tduration = 3650\n",
                "\t\t\tduration = -1\n",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.option_modifier_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_incomplete_route_reset_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                RESET_EFFECT_FILE,
                "\tremove_country_modifier = jxp_75_confucian_code_commission\n",
                "",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.route_cleanup_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_cross_route_cleanup_blind_spot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                EVENT_FILE,
                "\t\t\t\tNOT = { jxp_75_is_kirishitan_route_trigger = yes }\n",
                "",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.cross_route_cleanup",
                {issue.code for issue in result.issues},
            )

    def test_rejects_missing_canonical_route_cleanup_hook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                ROUTE_EFFECT_FILE,
                "\tjxp_75_reset_route_parity_four_effect = yes\n",
                "",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.canonical_route_cleanup",
                {issue.code for issue in result.issues},
            )

    def test_rejects_debug_entry_that_bypasses_reset_interface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                DEBUG_DECISION_FILE,
                "\t\t\tjxp_75_reset_route_parity_four_effect = yes\n",
                "\t\t\talways = yes\n",
            )
            result = check_route_parity_four_content(ValidationContext(root))
            self.assertIn(
                "route_parity_four.debug_root_interface",
                {issue.code for issue in result.issues},
            )


if __name__ == "__main__":
    unittest.main()
