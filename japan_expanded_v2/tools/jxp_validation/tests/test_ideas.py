from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.ideas import (
    NATIONAL_IDEA_COUNT,
    check_national_idea_modifiers,
    check_national_idea_structure,
    check_route_ideas,
    check_vanilla_national_idea_precedence,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")


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

    def test_rejects_nonexistent_vanilla_modifier_key(self) -> None:
        if not (GAME_ROOT / "common" / "ideas").is_dir():
            self.skipTest("pinned EU4 idea catalog is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ideas_root = root / "common" / "ideas"
            ideas_root.mkdir(parents=True)
            text = render_group().replace(
                "global_tax_modifier = 0.01",
                "fort_defense = 0.15",
                1,
            )
            (ideas_root / "test.txt").write_text(text, encoding="utf-8")
            result = check_national_idea_modifiers(
                ValidationContext(root), GAME_ROOT
            )
        self.assertTrue(
            any(
                issue.code == "ideas.unknown_modifier"
                and "fort_defense" in issue.message
                for issue in result.issues
            )
        )

    def test_live_vanilla_overrides_have_effective_file_precedence(self) -> None:
        if not (GAME_ROOT / "common" / "ideas").is_dir():
            self.skipTest("pinned EU4 idea catalog is unavailable")
        result = check_vanilla_national_idea_precedence(
            ValidationContext(LIVE_MOD_ROOT), GAME_ROOT
        )
        self.assertEqual([], result.issues)
        self.assertGreater(result.metrics["vanilla_overrides"], 0)
        self.assertEqual(
            result.metrics["vanilla_overrides"],
            result.metrics["precedence_safe_overrides"],
        )

    def test_live_managed_idea_migration_contract_is_clean(self) -> None:
        if not (GAME_ROOT / "common" / "ideas").is_dir():
            self.skipTest("pinned EU4 idea catalog is unavailable")
        result = check_route_ideas(ValidationContext(LIVE_MOD_ROOT), GAME_ROOT)
        self.assertEqual([], result.issues, result.to_dict())

    def test_live_first_assignment_uses_expected_group_postcondition(self) -> None:
        event_text = (
            LIVE_MOD_ROOT / "events/jxp_81_national_idea_registry_events.txt"
        ).read_text(encoding="utf-8")
        marker_read = "has_country_flag = jxp_national_idea_registry_repair_v0282"
        marker_clear = "clr_country_flag = jxp_national_idea_registry_repair_v0282"
        sync_call = "jxp_sync_managed_national_ideas_effect = yes"
        marker = "set_country_flag = jxp_national_idea_registry_repair_v0282"
        self.assertEqual(1, event_text.count(marker_read))
        self.assertEqual(1, event_text.count(marker_clear))
        self.assertEqual(1, event_text.count(sync_call))
        self.assertEqual(1, event_text.count(marker))
        self.assertLess(event_text.index(marker_clear), event_text.index(sync_call))
        self.assertLess(event_text.index(sync_call), event_text.index(marker))
        self.assertNotIn(
            "NOT = { has_country_flag = jxp_national_idea_registry_repair_v0282 }",
            event_text,
        )

    def test_rejects_additive_same_key_registry_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mod_root = root / "mod"
            game_root = root / "game"
            (mod_root / "common" / "ideas").mkdir(parents=True)
            (game_root / "common" / "ideas").mkdir(parents=True)
            (mod_root / "common" / "ideas" / "jxp_late.txt").write_text(
                render_group(), encoding="utf-8"
            )
            (game_root / "common" / "ideas" / "00_country_ideas.txt").write_text(
                render_group(), encoding="utf-8"
            )
            result = check_vanilla_national_idea_precedence(
                ValidationContext(mod_root), game_root
            )
        self.assertIn(
            "ideas.additive_registry_file",
            {issue.code for issue in result.issues},
        )

    def test_rejects_additive_free_file_before_basic_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mod_root = root / "mod"
            game_root = root / "game"
            (mod_root / "common" / "ideas").mkdir(parents=True)
            (game_root / "common" / "ideas").mkdir(parents=True)
            (mod_root / "common" / "ideas" / "00_0_jxp_early.txt").write_text(
                render_group(), encoding="utf-8"
            )
            (game_root / "common" / "ideas" / "00_country_ideas.txt").write_text(
                render_group(), encoding="utf-8"
            )
            result = check_vanilla_national_idea_precedence(
                ValidationContext(mod_root), game_root
            )
        self.assertIn(
            "ideas.additive_registry_file",
            {issue.code for issue in result.issues},
        )

    def test_accepts_exact_path_consolidated_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mod_root = root / "mod"
            game_root = root / "game"
            (mod_root / "common" / "ideas").mkdir(parents=True)
            (game_root / "common" / "ideas").mkdir(parents=True)
            (mod_root / "common" / "ideas" / "00_country_ideas.txt").write_text(
                render_group(), encoding="utf-8"
            )
            (game_root / "common" / "ideas" / "00_country_ideas.txt").write_text(
                render_group(), encoding="utf-8"
            )
            result = check_vanilla_national_idea_precedence(
                ValidationContext(mod_root), game_root
            )
        self.assertEqual([], result.issues)

    def test_rejects_duplicate_group_inside_consolidated_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mod_root = root / "mod"
            game_root = root / "game"
            (mod_root / "common" / "ideas").mkdir(parents=True)
            (game_root / "common" / "ideas").mkdir(parents=True)
            (mod_root / "common" / "ideas" / "00_country_ideas.txt").write_text(
                render_group() + render_group(), encoding="utf-8"
            )
            (game_root / "common" / "ideas" / "00_country_ideas.txt").write_text(
                render_group(), encoding="utf-8"
            )
            result = check_vanilla_national_idea_precedence(
                ValidationContext(mod_root), game_root
            )
        self.assertIn(
            "ideas.consolidated_duplicate_group",
            {issue.code for issue in result.issues},
        )


if __name__ == "__main__":
    unittest.main()
