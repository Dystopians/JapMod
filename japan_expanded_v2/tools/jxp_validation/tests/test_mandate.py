from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.mandate import check_mandate_contract


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
LIVE_GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
MOD_CONTRACT_FILES = (
    Path("common/cb_types/jxp_08_cb_types.txt"),
    Path("common/imperial_reforms/jxp_08_celestial_reforms.txt"),
    Path("common/scripted_effects/jxp_debug_effects.txt"),
    Path("common/scripted_effects/jxp_03_overseas_effects.txt"),
    Path("common/wargoal_types/jxp_08_wargoal_types.txt"),
    Path("decisions/jxp_03_overseas_decisions.txt"),
    Path("decisions/jxp_debug_decisions.txt"),
    Path("localisation_source/jxp_08_l_english_utf8_source.yml"),
    Path("missions/jxp_03_overseas_missions.txt"),
)
VANILLA_CONTRACT_FILES = (
    Path("common/cb_types/00_cb_types.txt"),
    Path("common/imperial_reforms/01_china.txt"),
    Path("common/wargoal_types/00_wargoal_types.txt"),
    Path("events/ChineseEmpire.txt"),
)


class MandateContractTests(unittest.TestCase):
    def _temporary_contract(
        self,
    ) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        mod_root = root / "mod"
        game_root = root / "game"
        for relative in MOD_CONTRACT_FILES:
            destination = mod_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LIVE_MOD_ROOT / relative, destination)
        for relative in VANILLA_CONTRACT_FILES:
            destination = game_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LIVE_GAME_ROOT / relative, destination)
        return directory, mod_root, game_root

    @staticmethod
    def _codes(mod_root: Path, game_root: Path) -> set[str]:
        result = check_mandate_contract(ValidationContext(mod_root), game_root)
        return {issue.code for issue in result.issues}

    def test_live_mandate_contract_is_closed(self) -> None:
        if not (LIVE_GAME_ROOT / "launcher-settings.json").is_file():
            self.skipTest("pinned EU4 1.37.5 game root is unavailable")
        self.assertEqual(self._codes(LIVE_MOD_ROOT, LIVE_GAME_ROOT), set())

    def test_rejects_hakko_cb_without_japanese_identity(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / MOD_CONTRACT_FILES[0]
            text = source.read_text(encoding="utf-8")
            original = "\t\tjxp_is_japanese_polity_trigger = yes\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, "", 1), encoding="utf-8")
            self.assertIn("mandate.cb_identity", self._codes(mod_root, game_root))

    def test_rejects_mod_override_of_vanilla_take_mandate_cb(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / MOD_CONTRACT_FILES[0]
            text = source.read_text(encoding="utf-8")
            source.write_text(
                text + "\ncb_take_mandate = { valid_for_subject = no }\n",
                encoding="utf-8",
            )
            self.assertIn(
                "mandate.vanilla_cb_override", self._codes(mod_root, game_root)
            )

    def test_rejects_hakko_cb_outside_far_east_contract(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / MOD_CONTRACT_FILES[0]
            text = source.read_text(encoding="utf-8")
            original = "\t\t\t\t\tsuperregion = far_east_superregion\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, "", 1), encoding="utf-8")
            self.assertIn("mandate.cb_scope", self._codes(mod_root, game_root))

    def test_rejects_hakko_wargoal_without_half_ae(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / Path("common/wargoal_types/jxp_08_wargoal_types.txt")
            text = source.read_text(encoding="utf-8")
            original = "\t\tbadboy_factor = 0.5\n"
            self.assertIn(original, text)
            source.write_text(
                text.replace(original, "\t\tbadboy_factor = 1\n", 1),
                encoding="utf-8",
            )
            self.assertIn("mandate.cb_ae", self._codes(mod_root, game_root))

    def test_rejects_missing_vanilla_pressure_exemption(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / Path(
                "common/imperial_reforms/jxp_08_celestial_reforms.txt"
            )
            text = source.read_text(encoding="utf-8")
            original = "\t\tset_country_flag = reacted_to_confucianism_event\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, "", 1), encoding="utf-8")
            self.assertIn(
                "mandate.celestial_exemption", self._codes(mod_root, game_root)
            )

    def test_rejects_non_mission_player_unlock_caller(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / Path("decisions/jxp_03_overseas_decisions.txt")
            text = source.read_text(encoding="utf-8")
            original = "\t\t\tjxp_apply_mandate_claim_reward_effect = yes\n"
            replacement = original + "\t\t\tjxp_unlock_hakko_ichiu_reform_effect = yes\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, replacement, 1), encoding="utf-8")
            self.assertIn(
                "mandate.mission_only_unlock", self._codes(mod_root, game_root)
            )

    def test_rejects_debug_scaffold_that_bypasses_emperor_setup(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / Path(
                "common/scripted_effects/jxp_debug_effects.txt"
            )
            text = source.read_text(encoding="utf-8")
            original = "\t\t\tset_emperor_of_china = ROOT\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, "", 1), encoding="utf-8")
            self.assertIn(
                "mandate.debug_emperor_scaffold", self._codes(mod_root, game_root)
            )

    def test_rejects_missing_non_mandate_fallback(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = mod_root / Path(
                "common/scripted_effects/jxp_03_overseas_effects.txt"
            )
            text = source.read_text(encoding="utf-8")
            original = "\t\tset_country_flag = jxp_mandate_claim_fallback\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, "", 1), encoding="utf-8")
            self.assertIn("mandate.no_dlc_fallback", self._codes(mod_root, game_root))

    def test_rejects_vanilla_cb_without_shogunate_exclusion(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = game_root / Path("common/cb_types/00_cb_types.txt")
            text = source.read_text(encoding="utf-8-sig")
            original = "\t\tNOT = { has_reform = shogunate }\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, "", 1), encoding="utf-8")
            self.assertIn(
                "mandate.vanilla_acquisition_cb", self._codes(mod_root, game_root)
            )

    def test_rejects_vanilla_wargoal_without_take_mandate(self) -> None:
        temporary, mod_root, game_root = self._temporary_contract()
        with temporary:
            source = game_root / Path("common/wargoal_types/00_wargoal_types.txt")
            text = source.read_text(encoding="utf-8-sig")
            original = "\t\t\tpo_take_mandate\n"
            self.assertIn(original, text)
            source.write_text(text.replace(original, "", 1), encoding="utf-8")
            self.assertIn(
                "mandate.vanilla_take_mandate_peace",
                self._codes(mod_root, game_root),
            )


if __name__ == "__main__":
    unittest.main()
