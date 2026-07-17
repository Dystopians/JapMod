from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.imjin import OCCUPATION_INTERVALS, WAR_ACTIONS, check_imjin_history
from jxp_validation.clausewitz import read_clausewitz_text


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
ENCODER_PATH = REPO_ROOT / "skills/eu4-modding/scripts/encode_eu4_special_gameplay.py"


def _encode_gameplay(text: str) -> bytes:
    spec = importlib.util.spec_from_file_location("_jxp_test_imjin_encoder", ENCODER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {ENCODER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.encode_gameplay_text(text)


def _codes(root: Path) -> set[str]:
    return {
        issue.code for issue in check_imjin_history(ValidationContext(root)).issues
    }


def _fixture_root(temporary: str) -> Path:
    root = Path(temporary) / "main"
    for filename in WAR_ACTIONS:
        relative = Path("history/wars") / filename
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MAIN_ROOT / relative, target)
    for province_id in OCCUPATION_INTERVALS:
        matches = list((MAIN_ROOT / "history/provinces").glob(f"{province_id} - *.txt"))
        if len(matches) != 1:
            raise AssertionError(f"unexpected province fixture set for {province_id}: {matches}")
        target = root / "history/provinces" / matches[0].name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(matches[0], target)
    diplomacy = Path("history/diplomacy/Japanese_alliances.txt")
    (root / diplomacy).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAIN_ROOT / diplomacy, root / diplomacy)
    return root


class ImjinHistoryContractTests(unittest.TestCase):
    def test_live_war_and_occupation_contract_is_clean(self) -> None:
        result = check_imjin_history(ValidationContext(MAIN_ROOT))
        self.assertEqual([], result.issues, result.to_dict())

    def test_stale_oda_war_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = root / "history/wars/KoreanSevenYearsWar.txt"
            path.write_bytes(path.read_bytes().replace(b"TOY", b"ODA", 1))
            self.assertIn("imjin.post_succession_oda", _codes(root))

    def test_wrong_busan_province_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = root / "history/wars/KoreanSevenYearsWar.txt"
            path.write_bytes(
                path.read_bytes().replace(
                    b"location = 2745", b"location = 736", 1
                )
            )
            self.assertIn("imjin.battle_contract", _codes(root))

    def test_english_imjin_war_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = root / "history/wars/KoreanSevenYearsWar.txt"
            text = read_clausewitz_text(path).replace("\u58ec\u8fb0\u502d\u4e71", "Imjin War", 1)
            path.write_bytes(_encode_gameplay(text))
            self.assertIn("imjin.war_display_name", _codes(root))

    def test_english_battle_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = root / "history/wars/KoreanSevenYearsWar.txt"
            text = read_clausewitz_text(path).replace("\u91dc\u5c71", "Busan", 1)
            path.write_bytes(_encode_gameplay(text))
            self.assertIn("imjin.battle_contract", _codes(root))

    def test_raw_utf8_war_literals_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = root / "history/wars/KoreanSevenYearsWar.txt"
            path.write_text(read_clausewitz_text(path), encoding="utf-8", newline="")
            self.assertIn("imjin.war_display_encoding", _codes(root))

    def test_false_jeju_occupation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = next((root / "history/provinces").glob("2741 - *.txt"))
            with path.open("a", encoding="cp1252", newline="") as stream:
                stream.write("1597.9.26 = { controller = TOY }\n")
            codes = _codes(root)
            self.assertTrue(
                {"imjin.jeju_occupation", "imjin.occupation_snapshot"} & codes
            )

    def test_missing_pyongyang_occupation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = next((root / "history/provinces").glob("1845 - *.txt"))
            text = path.read_text(encoding="cp1252").replace("controller = TOY", "", 1)
            path.write_text(text, encoding="cp1252", newline="")
            self.assertIn("imjin.occupation_start", _codes(root))

    def test_co_belligerent_without_toyotomi_overlord_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(temporary)
            path = root / "history/diplomacy/Japanese_alliances.txt"
            text = path.read_text(encoding="cp1252").replace(
                "second = SMZ", "second = XXX"
            )
            path.write_text(text, encoding="cp1252", newline="")
            self.assertIn("imjin.participant_subject", _codes(root))


if __name__ == "__main__":
    unittest.main()
