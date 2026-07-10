from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from jxp_validation.names import (
    audit_japanese_names,
    is_untranslated_person_literal,
)


LIVE_MAIN_ROOT = Path(__file__).resolve().parents[3]
LIVE_REPO_ROOT = LIVE_MAIN_ROOT.parent
LIVE_MAP_ROOT = LIVE_REPO_ROOT / "japan_expanded_v2_map"


class JapaneseNameAuditTests(unittest.TestCase):
    def test_live_main_and_companion_name_surface_is_clean(self) -> None:
        audit = audit_japanese_names(
            LIVE_MAIN_ROOT,
            LIVE_MAP_ROOT,
            LIVE_REPO_ROOT,
        )
        self.assertEqual([], audit.issues)
        self.assertEqual(30, audit.stats["map_source_records"])
        self.assertGreaterEqual(audit.stats["localisation_pairs"], 60)

    def test_romaji_classifier_preserves_non_japanese_names(self) -> None:
        self.assertTrue(is_untranslated_person_literal("Ieyasu"))
        self.assertTrue(is_untranslated_person_literal("Hideyoshi"))
        self.assertFalse(is_untranslated_person_literal("家康"))
        self.assertFalse(is_untranslated_person_literal("Yusuf"))
        self.assertFalse(is_untranslated_person_literal("Dom Justo #0"))

    def test_mutated_country_history_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            main = repo / "japan_expanded_v2"
            companion = repo / "japan_expanded_v2_map"
            history = main / "history" / "countries"
            history.mkdir(parents=True)
            companion.mkdir()
            (history / "CJP - Confucian Wa.txt").write_text(
                '1444.11.11 = { monarch = { name = "Ieyasu" dynasty = "Tokugawa" } }\n',
                encoding="utf-8",
            )
            audit = audit_japanese_names(main, companion, repo)
        self.assertIn("names.romaji_literal", {issue.code for issue in audit.issues})


if __name__ == "__main__":
    unittest.main()
