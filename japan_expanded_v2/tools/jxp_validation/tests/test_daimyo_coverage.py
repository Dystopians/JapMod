from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.daimyo_coverage import (
    audit_idea_assignment,
    audit_identity_depth,
    audit_forbidden_modifier_text,
    audit_map_identity_migration_text,
    audit_post_tag_idea_sync_text,
    check_daimyo_coverage,
    collect_idea_identities,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
MAP_BUILDER = MAP_ROOT / "tools" / "jxp_map_builder"


def _codes(result: CheckResult) -> set[str]:
    return {issue.code for issue in result.issues}


class DaimyoCoverageTests(unittest.TestCase):
    def test_live_68_tag_matrix_is_closed(self) -> None:
        result = check_daimyo_coverage(ValidationContext(MAIN_ROOT))
        self.assertEqual([], result.issues, result.to_dict())
        self.assertEqual(68, result.metrics["tags"])
        self.assertEqual(38, result.metrics["main_tags"])
        self.assertEqual(30, result.metrics["map_tags"])
        self.assertEqual(68, result.metrics["exact_idea_groups"])
        self.assertEqual(272, result.metrics["dlc_profiles"])

    def test_generated_companion_ideas_are_idempotent(self) -> None:
        sys.path.insert(0, str(MAP_BUILDER))
        try:
            import build_countries

            countries = json.loads(
                (MAP_BUILDER / "history_plan.json").read_text(encoding="utf-8")
            )["countries"]
            identity_plan = json.loads(
                (MAP_BUILDER / "daimyo_identity_plan.json").read_text(encoding="utf-8")
            )
            contract = json.loads(
                (
                    MAP_ROOT
                    / "tools"
                    / "jxp_map_validation"
                    / "main_compatibility_contract.json"
                ).read_text(encoding="utf-8")
            )
            records = build_countries.identity_records(
                countries, identity_plan, contract
            )
            rendered = build_countries.ideas_file(records)
        finally:
            sys.path.remove(str(MAP_BUILDER))
        actual = (
            MAP_ROOT / "common" / "ideas" / "jxp_map_new_daimyo_ideas.txt"
        ).read_text(encoding="cp1252")
        self.assertEqual(actual, rendered)

    def test_shared_idea_trigger_mutation_is_rejected(self) -> None:
        identities = collect_idea_identities(ValidationContext(MAP_ROOT))
        rkk = next(identity for identity in identities if identity.group == "RKK_ideas")
        mutated = replace(rkk, tags=("RKK", "MOG"))
        result = CheckResult("mutation")
        audit_idea_assignment("map", "RKK", "A", (mutated,), result)
        self.assertIn("daimyo.idea_not_exact_tag", _codes(result))

    def test_nonfree_idea_mutation_is_rejected(self) -> None:
        identities = collect_idea_identities(ValidationContext(MAP_ROOT))
        rkk = next(identity for identity in identities if identity.group == "RKK_ideas")
        result = CheckResult("mutation")
        audit_idea_assignment(
            "map", "RKK", "A", (replace(rkk, free=False),), result
        )
        self.assertIn("daimyo.idea_not_free", _codes(result))

    def test_invalid_fort_modifier_mutation_is_rejected(self) -> None:
        result = CheckResult("mutation")
        audit_forbidden_modifier_text(
            "idea = { " + "fort_" + "defense = 0.15 }", result
        )
        self.assertIn("daimyo.unknown_modifier_alias", _codes(result))

    def test_shallow_major_identity_mutation_is_rejected(self) -> None:
        result = CheckResult("mutation")
        audit_identity_depth(
            "map", "RKK", "A", "jxp_map_warrior_house_missions", 5, result
        )
        self.assertIn("daimyo.identity_depth_floor", _codes(result))

    def test_migration_cleanup_mutation_is_rejected(self) -> None:
        source = (
            MAP_ROOT / "common" / "scripted_effects" / "jxp_map_effects.txt"
        ).read_text(encoding="cp1252")
        mutated = source.replace(
            "\tclr_country_flag = jxp_map_identity_migration_v012\n", "", 1
        )
        result = CheckResult("mutation")
        audit_map_identity_migration_text(mutated, result)
        self.assertIn("daimyo.map_identity_migration", _codes(result))

    def test_post_tag_canonical_swap_mutation_is_rejected(self) -> None:
        main_effects = (
            MAIN_ROOT / "common" / "scripted_effects" / "jxp_scripted_effects.txt"
        ).read_text(encoding="cp1252")
        map_events = (MAP_ROOT / "events" / "jxp_map_events.txt").read_text(
            encoding="cp1252"
        )
        map_effects = (
            MAP_ROOT / "common" / "scripted_effects" / "jxp_map_effects.txt"
        ).read_text(encoding="cp1252")
        mutated = main_effects.replace(
            "\t\t\t\t\tAND = { tag = JAP NOT = { has_idea_group = JAP_ideas } }\n",
            "",
            1,
        )
        result = CheckResult("mutation")
        audit_post_tag_idea_sync_text(mutated, map_events, map_effects, result)
        self.assertIn("daimyo.post_tag_idea_sync", _codes(result))


if __name__ == "__main__":
    unittest.main()
