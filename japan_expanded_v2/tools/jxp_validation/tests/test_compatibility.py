from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.compatibility import check_release_compatibility
from jxp_validation.core import ValidationContext


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_FILES = (
    Path("common/imperial_reforms/jxp_08_celestial_reforms.txt"),
    Path("common/on_actions/jxp_60_mission_runtime_on_actions.txt"),
    Path("common/scripted_effects/jxp_03_overseas_effects.txt"),
    Path("common/scripted_effects/jxp_08_celestial_effects.txt"),
    Path("common/scripted_effects/jxp_50_legacy_cabinet_effects.txt"),
    Path("events/jxp_23_celestial_compat_events.txt"),
    Path("missions/jxp_03_overseas_missions.txt"),
)


class HakkoIchiuCompatibilityTests(unittest.TestCase):
    def _copy_contract(self, root: Path) -> None:
        for relative in CONTRACT_FILES:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LIVE_MOD_ROOT / relative, destination)

    @staticmethod
    def _codes(root: Path) -> set[str]:
        result = check_release_compatibility(ValidationContext(root))
        return {issue.code for issue in result.issues if issue.code.startswith("compat.hakko")}

    def test_live_hakko_contract_is_closed(self) -> None:
        self.assertEqual(self._codes(LIVE_MOD_ROOT), set())

    def test_dynamic_unlock_in_potential_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            reform = root / CONTRACT_FILES[0]
            source = reform.read_text(encoding="utf-8")
            source = source.replace(
                "\t\tjxp_is_japanese_polity_trigger = yes\n\t}",
                "\t\tjxp_is_japanese_polity_trigger = yes\n"
                "\t\thas_country_flag = jxp_unlocked_hakko_ichiu_reform\n\t}",
                1,
            )
            reform.write_text(source, encoding="utf-8")
            self.assertIn("compat.hakko_dynamic_potential", self._codes(root))

    def test_unlock_or_requires_direct_alternatives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            reform = root / CONTRACT_FILES[0]
            source = reform.read_text(encoding="utf-8")
            original = (
                "\t\t\tOR = {\n"
                "\t\t\t\thas_country_flag = jxp_unlocked_hakko_ichiu_reform\n"
                "\t\t\t\tmission_completed = jxp_mission_eastasia_claim_mandate\n"
                "\t\t\t}"
            )
            replacement = (
                "\t\t\tOR = {\n"
                "\t\t\t\tAND = {\n"
                "\t\t\t\t\thas_country_flag = jxp_unlocked_hakko_ichiu_reform\n"
                "\t\t\t\t\tmission_completed = jxp_mission_eastasia_claim_mandate\n"
                "\t\t\t\t}\n"
                "\t\t\t}"
            )
            self.assertIn(original, source)
            reform.write_text(source.replace(original, replacement, 1), encoding="utf-8")
            self.assertIn("compat.hakko_unlock_or", self._codes(root))

    def test_mission_dlc_guard_cannot_be_negated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            missions = root / Path("missions/jxp_03_overseas_missions.txt")
            source = missions.read_text(encoding="utf-8")
            original = '\t\t\t\thas_dlc = "Mandate of Heaven"\n'
            replacement = '\t\t\t\tNOT = { has_dlc = "Mandate of Heaven" }\n'
            self.assertIn(original, source)
            missions.write_text(source.replace(original, replacement, 1), encoding="utf-8")
            self.assertIn("compat.hakko_mission_reward", self._codes(root))

    def test_mission_dlc_guard_rejects_extra_false_condition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            missions = root / Path("missions/jxp_03_overseas_missions.txt")
            source = missions.read_text(encoding="utf-8")
            original = '\t\t\t\thas_dlc = "Mandate of Heaven"\n'
            replacement = original + "\t\t\t\talways = no\n"
            self.assertIn(original, source)
            missions.write_text(source.replace(original, replacement, 1), encoding="utf-8")
            self.assertIn("compat.hakko_mission_reward", self._codes(root))

    def test_cached_visibility_refresh_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            effects = root / Path("common/scripted_effects/jxp_08_celestial_effects.txt")
            source = effects.read_text(encoding="utf-8")
            source = source.replace("\t\t\tregenerate_government_mechanics = yes\n", "", 1)
            effects.write_text(source, encoding="utf-8")
            self.assertIn("compat.hakko_effect_contract", self._codes(root))

    def test_reconcile_or_requires_direct_alternatives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            effects = root / Path("common/scripted_effects/jxp_08_celestial_effects.txt")
            source = effects.read_text(encoding="utf-8")
            original = (
                "\t\t\t\tOR = {\n"
                "\t\t\t\t\thas_country_flag = jxp_unlocked_hakko_ichiu_reform\n"
                "\t\t\t\t\tmission_completed = jxp_mission_eastasia_claim_mandate\n"
                "\t\t\t\t}"
            )
            replacement = (
                "\t\t\t\tOR = {\n"
                "\t\t\t\t\tAND = {\n"
                "\t\t\t\t\t\thas_country_flag = jxp_unlocked_hakko_ichiu_reform\n"
                "\t\t\t\t\t\tmission_completed = jxp_mission_eastasia_claim_mandate\n"
                "\t\t\t\t\t}\n"
                "\t\t\t\t}"
            )
            self.assertIn(original, source)
            effects.write_text(source.replace(original, replacement, 1), encoding="utf-8")
            self.assertIn("compat.hakko_reconcile_or", self._codes(root))

    def test_no_dlc_fallback_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            rewards = root / Path("common/scripted_effects/jxp_03_overseas_effects.txt")
            source = rewards.read_text(encoding="utf-8")
            source = source.replace(
                "\t\tset_country_flag = jxp_mandate_claim_fallback\n", "", 1
            )
            rewards.write_text(source, encoding="utf-8")
            self.assertIn("compat.hakko_no_dlc_fallback", self._codes(root))

    def test_startup_migration_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            on_actions = root / Path("common/on_actions/jxp_60_mission_runtime_on_actions.txt")
            source = on_actions.read_text(encoding="utf-8")
            source = source.replace("\t\tjxp_celestial_compat.1\n", "", 1)
            on_actions.write_text(source, encoding="utf-8")
            self.assertIn("compat.hakko_startup_migration", self._codes(root))

    def test_catchup_migration_flag_must_be_negated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._copy_contract(root)
            events = root / Path("events/jxp_23_celestial_compat_events.txt")
            source = events.read_text(encoding="utf-8")
            original = (
                "\t\tNOT = { has_country_flag = "
                "jxp_hakko_visibility_reconciled_v0260 }\n"
            )
            replacement = (
                "\t\thas_country_flag = "
                "jxp_hakko_visibility_reconciled_v0260\n"
            )
            self.assertIn(original, source)
            events.write_text(source.replace(original, replacement, 1), encoding="utf-8")
            self.assertIn("compat.hakko_catchup", self._codes(root))


if __name__ == "__main__":
    unittest.main()
