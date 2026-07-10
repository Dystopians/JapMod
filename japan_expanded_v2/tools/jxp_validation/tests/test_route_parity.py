from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.route_parity import (
    ACTIVE_LOC_FILE,
    DEBUG_DECISION_FILE,
    DEBUG_EFFECT_FILE,
    DECISION_FILE,
    EVENT_FILE,
    MODIFIER_FILE,
    ROUTE_EFFECT_FILE,
    SOURCE_LOC_FILE,
    TRIGGER_FILE,
    check_route_parity_content,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_FILES = (
    TRIGGER_FILE,
    EVENT_FILE,
    DECISION_FILE,
    DEBUG_DECISION_FILE,
    MODIFIER_FILE,
    DEBUG_EFFECT_FILE,
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


class RouteParityContractTests(unittest.TestCase):
    def test_live_route_parity_slice_is_closed(self) -> None:
        result = check_route_parity_content(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(result.metrics["route_gates"], 6)
        self.assertEqual(result.metrics["native_events"], 3)
        self.assertEqual(result.metrics["reform_options"], 9)
        self.assertEqual(result.metrics["native_decisions"], 3)
        self.assertEqual(result.metrics["debug_entries"], 3)
        self.assertEqual(result.metrics["modifiers"], 10)
        self.assertEqual(result.metrics["debug_cleanup"], 10)
        self.assertEqual(result.metrics["route_cleanup"], 10)

    def test_rejects_missing_route_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                TRIGGER_FILE,
                "\t\t\thas_country_flag = jxp_path_open_trade\n",
                "",
            )
            result = check_route_parity_content(ValidationContext(root))
            self.assertIn(
                "route_parity.trigger_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_reform_option_without_exact_era_tradeoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                EVENT_FILE,
                "\t\tjxp_add_imperial_sanction_5_effect = yes\n",
                "",
            )
            result = check_route_parity_content(ValidationContext(root))
            self.assertIn(
                "route_parity.option_attribute_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_permanent_cooldown_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                EVENT_FILE,
                "\t\t\tduration = 3650\n",
                "\t\t\tduration = -1\n",
            )
            result = check_route_parity_content(ValidationContext(root))
            self.assertIn(
                "route_parity.option_modifier_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_missing_canonical_debug_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                DEBUG_EFFECT_FILE,
                "\tremove_country_modifier = jxp_71_open_charter_auditors\n",
                "",
            )
            result = check_route_parity_content(ValidationContext(root))
            self.assertIn(
                "route_parity.debug_cleanup",
                {issue.code for issue in result.issues},
            )

    def test_rejects_missing_route_transition_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_contract(root)
            _mutate(
                root,
                ROUTE_EFFECT_FILE,
                "\tremove_country_modifier = jxp_71_imperial_guard_muster\n",
                "",
            )
            result = check_route_parity_content(ValidationContext(root))
            self.assertIn(
                "route_parity.route_cleanup",
                {issue.code for issue in result.issues},
            )


if __name__ == "__main__":
    unittest.main()
