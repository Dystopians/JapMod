from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.government_identity import (
    CELESTIAL_POLITY_CONDITIONAL_BLOCK,
    LEGACY_ROUTE_FILE,
    MONARCHY_REFORM_FILE,
    check_government_identity,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
LIVE_COMPANION_ROOT = LIVE_MOD_ROOT.parent / "japan_expanded_v2_map"
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")


def _mutate(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    changed = text.replace(old, new, 1)
    if changed == text:
        raise AssertionError(f"mutation anchor not found in {path}: {old!r}")
    path.write_text(changed, encoding="utf-8")


class GovernmentIdentityTests(unittest.TestCase):
    def _copy_contract(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for relative in ("common", "events", "decisions", "history", "missions"):
            source = LIVE_MOD_ROOT / relative
            if source.is_dir():
                shutil.copytree(source, root / relative)
        return root

    def _codes(self, root: Path) -> set[str]:
        result = check_government_identity(
            ValidationContext(root),
            GAME_ROOT,
            ValidationContext(LIVE_COMPANION_ROOT),
        )
        return {issue.code for issue in result.issues}

    def test_live_fresh_start_identity_contract_is_closed(self) -> None:
        result = check_government_identity(
            ValidationContext(LIVE_MOD_ROOT),
            GAME_ROOT,
            ValidationContext(LIVE_COMPANION_ROOT),
        )
        self.assertEqual([], result.issues)
        self.assertEqual(37, result.metrics["main_fresh_identities"])
        self.assertEqual(30, result.metrics["map_fresh_identities"])
        self.assertEqual(67, result.metrics["fresh_identity_total"])
        self.assertEqual(3, result.metrics["daimyo_mechanic_carriers"])
        self.assertEqual(27, result.metrics["retired_route_tombstones"])
        self.assertEqual(10, result.metrics["canonical_final_power_adds"])
        self.assertEqual(1, result.metrics["ryukyu_control"])

    def test_rejects_legacy_route_reform_as_basic(self) -> None:
        root = self._copy_contract()
        path = root / LEGACY_ROUTE_FILE
        _mutate(
            path,
            '\ticon = "shogunate"\n',
            '\ticon = "shogunate"\n\tbasic_reform = yes\n',
        )
        codes = self._codes(root)
        self.assertIn("government_identity.basic_reform_inventory", codes)
        self.assertIn("government_identity.legacy_route_tombstone", codes)

    def test_rejects_missing_daimyo_polity_mechanic(self) -> None:
        root = self._copy_contract()
        path = root / MONARCHY_REFORM_FILE
        marker = (
            "daimyo = {\n"
            '\ticon = "daimyo"'
        )
        text = path.read_text(encoding="utf-8-sig")
        start = text.index(marker)
        end = text.index("\n}\n", start) + 3
        block = text[start:end]
        ability = (
            "\n\tgovernment_abilities = {\n"
            "\t\tjxp_japanese_polity_mechanic\n"
            "\t}\n"
        )
        self.assertIn(ability, block)
        path.write_text(text[:start] + block.replace(ability, "", 1) + text[end:], encoding="utf-8")
        codes = self._codes(root)
        self.assertIn("government_identity.daimyo_mechanic_wiring", codes)

    def test_rejects_missing_celestial_polity_conditional(self) -> None:
        root = self._copy_contract()
        path = root / MONARCHY_REFORM_FILE
        _mutate(path, CELESTIAL_POLITY_CONDITIONAL_BLOCK, "")
        codes = self._codes(root)
        self.assertIn("government_identity.celestial_polity_ability_count", codes)

    def test_rejects_mori_republic_fresh_start(self) -> None:
        root = self._copy_contract()
        source = GAME_ROOT / "history/countries/MRI - Mori.txt"
        target = root / "history/countries/MRI - Mori.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        _mutate(target, "government = monarchy", "government = republic")
        self.assertIn("government_identity.fresh_history", self._codes(root))

    def test_rejects_pre_start_dated_government_mutation(self) -> None:
        root = self._copy_contract()
        source = GAME_ROOT / "history/countries/MRI - Mori.txt"
        target = root / "history/countries/MRI - Mori.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        with target.open("a", encoding="utf-8") as handle:
            handle.write("\n1444.1.1 = { government = republic }\n")
        self.assertIn(
            "government_identity.pre_start_history_mutation", self._codes(root)
        )

    def test_rejects_realm_retry_without_actual_mechanic_gate(self) -> None:
        root = self._copy_contract()
        path = root / "events/jxp_realm_events.txt"
        _mutate(
            path,
            "\t\thas_government_mechanic = jxp_japanese_polity_mechanic\n",
            "",
        )
        self.assertIn("government_identity.mechanic_retry_scope", self._codes(root))

    def test_rejects_final_power_grant_before_exact_final_state(self) -> None:
        root = self._copy_contract()
        event = root / "events/jxp_wokou_events.txt"
        _mutate(
            event,
            "\t\tjxp_grant_route_reforms_effect = yes\n",
            "\t\tadd_government_reform = jxp_wokou_admiralty_reform\n"
            "\t\tjxp_grant_route_reforms_effect = yes\n",
        )
        self.assertIn("government_identity.final_power_autogrant", self._codes(root))


if __name__ == "__main__":
    unittest.main()
