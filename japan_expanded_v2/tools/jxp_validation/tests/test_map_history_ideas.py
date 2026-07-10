from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
LIVE_MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
VALIDATOR_PATH = (
    REPO_ROOT
    / "japan_expanded_v2_map"
    / "tools"
    / "jxp_map_validation"
    / "validate_history.py"
)

# The focused tests exercise no raster paths. Keep them runnable with the
# repository's lightweight Python test interpreter when Pillow is absent.
if importlib.util.find_spec("PIL") is None:
    pil_module = types.ModuleType("PIL")
    pil_module.Image = types.SimpleNamespace()
    sys.modules["PIL"] = pil_module

SPEC = importlib.util.spec_from_file_location("jxp_map_validate_history_tests", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import setup guard
    raise RuntimeError(f"Could not load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def render_group(*, idea_count: int = 7, commented_tag: str | None = None) -> str:
    comment = f"\n\t\t\t# tag = {commented_tag} {{ ignored }}" if commented_tag else ""
    ideas = " ".join(
        f'idea_{index} = {{ test_modifier = {index} note = "literal {{ # }}" }}'
        for index in range(idea_count)
    )
    return f"""jxp_map_new_daimyo_ideas = {{
\tstart = {{ land_morale = 0.05 }}
\tbonus = {{ discipline = 0.05 }}
\ttrigger = {{
\t\tOR = {{
\t\t\ttag = AAA{comment}
\t\t}}
\t}}
\tfree = yes
\t# These braces must not affect object depth: {{ }}
\t{ideas}
}}
"""


def validate_text(text: str, tags: set[str]):
    with tempfile.TemporaryDirectory() as directory:
        map_root = Path(directory)
        ideas_root = map_root / "common" / "ideas"
        ideas_root.mkdir(parents=True)
        (ideas_root / "jxp_map_new_daimyo_ideas.txt").write_text(
            text,
            encoding="cp1252",
        )
        report = VALIDATOR.Report()
        VALIDATOR.validate_ideas(tags, report, LIVE_MAIN_ROOT, map_root)
        return report


class CompanionIdeaValidationTests(unittest.TestCase):
    def test_counts_multiple_idea_objects_on_one_line_and_ignores_literal_braces(self) -> None:
        report = validate_text(render_group(), {"AAA"})
        self.assertEqual([], report.errors)

    def test_rejects_an_eighth_same_line_idea_object(self) -> None:
        report = validate_text(render_group(idea_count=8), {"AAA"})
        self.assertTrue(
            any("has 8 ideas, expected exactly 7" in error for error in report.errors),
            report.errors,
        )

    def test_commented_tag_does_not_satisfy_trigger_coverage(self) -> None:
        report = validate_text(
            render_group(commented_tag="BBB"),
            {"AAA", "BBB"},
        )
        self.assertTrue(
            any("trigger coverage differs" in error for error in report.errors),
            report.errors,
        )

    def test_rejects_extra_activation_condition_outside_tag_or(self) -> None:
        source = render_group().replace(
            "\ttrigger = {\n\t\tOR = {",
            "\ttrigger = {\n\t\talways = no\n\t\tOR = {",
            1,
        )
        report = validate_text(source, {"AAA"})
        self.assertTrue(
            any("exactly one direct OR" in error for error in report.errors),
            report.errors,
        )

    def test_rejects_main_contract_count_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            main_root = Path(directory)
            contract_root = main_root / "tools" / "jxp_validation"
            contract_root.mkdir(parents=True)
            (contract_root / "ideas.py").write_text(
                "NATIONAL_IDEA_COUNT = 8\n",
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            count = VALIDATOR.read_main_national_idea_count(main_root, report)
        self.assertIsNone(count)
        self.assertTrue(
            any("expected 7, found 8" in error for error in report.errors),
            report.errors,
        )


if __name__ == "__main__":
    unittest.main()
