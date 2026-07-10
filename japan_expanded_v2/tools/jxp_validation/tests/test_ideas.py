from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.ideas import NATIONAL_IDEA_COUNT, check_national_idea_structure


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]


def render_group(
    idea_count: int = NATIONAL_IDEA_COUNT,
    *,
    start: bool = True,
    bonus: bool = True,
    trigger: bool = True,
    free: str = "yes",
    extra_member: str = "",
) -> str:
    members = []
    if start:
        members.append("\tstart = { prestige = 1 }")
    if bonus:
        members.append("\tbonus = { discipline = 0.05 }")
    if trigger:
        members.append("\ttrigger = { tag = TST }")
    members.append(f"\tfree = {free}")
    if extra_member:
        members.append(f"\t{extra_member}")
    members.extend(
        f"\ttest_idea_{index} = {{ global_tax_modifier = 0.01 }}"
        for index in range(idea_count)
    )
    return "test_ideas = {\n" + "\n".join(members) + "\n}\n"


def validate_text(text: str):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ideas_root = root / "common" / "ideas"
        ideas_root.mkdir(parents=True)
        (ideas_root / "test.txt").write_text(text, encoding="utf-8")
        return check_national_idea_structure(ValidationContext(root))


class NationalIdeaStructureTests(unittest.TestCase):
    def test_live_mod_audits_more_than_the_seven_route_groups(self) -> None:
        result = check_national_idea_structure(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertGreater(result.metrics["groups"], 7)
        self.assertEqual(result.metrics["groups"], result.metrics["valid_groups"])

    def test_rejects_fewer_or_more_than_seven_ideas(self) -> None:
        for count in (NATIONAL_IDEA_COUNT - 1, NATIONAL_IDEA_COUNT + 1):
            with self.subTest(count=count):
                result = validate_text(render_group(count))
                self.assertIn("ideas.count", {issue.code for issue in result.issues})

    def test_rejects_missing_start_and_bonus(self) -> None:
        result = validate_text(render_group(start=False, bonus=False))
        codes = {issue.code for issue in result.issues}
        self.assertIn("ideas.start_missing", codes)
        self.assertIn("ideas.bonus_missing", codes)

    def test_rejects_invalid_activation_metadata(self) -> None:
        result = validate_text(render_group(trigger=False, free="no"))
        codes = {issue.code for issue in result.issues}
        self.assertIn("ideas.trigger_missing", codes)
        self.assertIn("ideas.free_value", codes)

    def test_rejects_unrecognised_scalar_member_inside_group(self) -> None:
        result = validate_text(render_group(extra_member="eighth_slot = yes"))
        self.assertIn(
            "ideas.unexpected_member",
            {issue.code for issue in result.issues},
        )

    def test_rejects_anomalous_file_root_member(self) -> None:
        result = validate_text(render_group() + "rogue_setting = yes\n")
        self.assertIn(
            "ideas.top_level_member",
            {issue.code for issue in result.issues},
        )


if __name__ == "__main__":
    unittest.main()
