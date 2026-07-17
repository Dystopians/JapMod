from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.writing_events import (
    ACTIVE_LOC_FILE,
    SOURCE_LOC_FILE,
    TARGETS,
    check_writing_events,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_FILES = tuple(TARGETS) + (SOURCE_LOC_FILE, ACTIVE_LOC_FILE)


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
    return {issue.code for issue in check_writing_events(ValidationContext(root)).issues}


class LowFrequencyWritingTests(unittest.TestCase):
    def _temporary_contract(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        _copy_contract(root)
        return directory, root

    def test_live_low_frequency_events_have_real_choices(self) -> None:
        result = check_writing_events(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(22, result.metrics["target_events"])
        self.assertEqual(22, result.metrics["improved_events"])
        self.assertEqual(22, result.metrics["tradeoff_choices"])
        self.assertEqual(22, result.metrics["localised_choices"])
        self.assertEqual(0, result.metrics["remaining_slow_single_choice"])

    def test_rejects_removed_second_choice(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            Path("events/jxp_wokou_events.txt"),
            "\n\toption = {\n"
            "\t\tname = \"jxp_wokou.2.b\"\n"
            "\t\tset_country_flag = jxp_wokou_letters_seen\n"
            "\t\tadd_treasury = -75\n"
            "\t\tadd_navy_tradition = 5\n"
            "\t\tjxp_add_tenka_order_5_effect = yes\n"
            "\t\tjxp_subtract_oceanic_opening_5_effect = yes\n"
            "\t}\n",
            "",
        )
        codes = _codes(root)
        self.assertIn("writing_events.choice_pair", codes)
        self.assertIn("writing_events.remaining_single_choice", codes)

    def test_rejects_choice_without_completion_flag(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            Path("events/jxp_ikko_events.txt"),
            "\t\tname = \"jxp_ikko.3.b\"\n"
            "\t\tset_country_flag = jxp_ikko_monto_militia_seen\n",
            "\t\tname = \"jxp_ikko.3.b\"\n",
        )
        self.assertIn("writing_events.completion_flag", _codes(root))

    def test_rejects_costless_alternative(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            Path("events/jxp_wokou_events.txt"),
            "\t\tname = \"jxp_wokou.6.b\"\n"
            "\t\tset_country_flag = jxp_ming_sea_smugglers_seen\n"
            "\t\tadd_treasury = -50\n",
            "\t\tname = \"jxp_wokou.6.b\"\n"
            "\t\tset_country_flag = jxp_ming_sea_smugglers_seen\n"
            "\t\tadd_treasury = 50\n",
        )
        self.assertIn("writing_events.tradeoff", _codes(root))

    def test_rejects_duplicate_outcomes(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            Path("events/jxp_route_events.txt"),
            "\toption = {\n"
            "\t\tname = \"jxp_confucian.1.b\"\n"
            "\t\tset_country_flag = jxp_confucian_academy_seen\n"
            "\t\tadd_country_modifier = {\n"
            "\t\t\tname = jxp_confucian_academies\n"
            "\t\t\tduration = 7300\n"
            "\t\t}\n"
            "\t\tadd_adm_power = -50\n"
            "\t\tadd_stability = 1\n"
            "\t\tjxp_add_tenka_order_5_effect = yes\n"
            "\t}\n",
            "\toption = {\n"
            "\t\tname = \"jxp_confucian.1.b\"\n"
            "\t\tset_country_flag = jxp_confucian_academy_seen\n"
            "\t\tadd_country_modifier = {\n"
            "\t\t\tname = jxp_confucian_academies\n"
            "\t\t\tduration = 7300\n"
            "\t\t}\n"
            "\t\tjxp_add_imperial_sanction_5_effect = yes\n"
            "\t}\n",
        )
        codes = _codes(root)
        self.assertIn("writing_events.distinct_outcome", codes)
        self.assertIn("writing_events.tradeoff", codes)

    def test_rejects_new_permanent_reward_modifier(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            Path("events/jxp_kirishitan_events.txt"),
            "\t\t\tname = jxp_kirishitan_oceanic_orders\n"
            "\t\t\tduration = 3650\n",
            "\t\t\tname = jxp_kirishitan_oceanic_orders\n"
            "\t\t\tduration = -1\n",
        )
        self.assertIn("writing_events.permanent_reward", _codes(root))

    def test_rejects_target_reclassified_as_short_setup_pulse(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            Path("events/jxp_route_events.txt"),
            "\t\tmonths = 160\n",
            "\t\tmonths = 3\n",
        )
        self.assertIn("writing_events.classification", _codes(root))

    def test_rejects_mechanical_option_prose(self) -> None:
        _directory, root = self._temporary_contract()
        _mutate(
            root,
            SOURCE_LOC_FILE,
            ' jxp_ikko.2.b:0 "把寺内町编入领国法度"\n',
            ' jxp_ikko.2.b:0 "获得 50 点行政"\n',
        )
        self.assertIn("writing_events.prose", _codes(root))

    def test_rejects_unescaped_active_localisation(self) -> None:
        _directory, root = self._temporary_contract()
        source = (root / SOURCE_LOC_FILE).read_bytes()
        (root / ACTIVE_LOC_FILE).write_bytes(source)
        self.assertIn("writing_events.localisation_pipeline", _codes(root))


if __name__ == "__main__":
    unittest.main()
