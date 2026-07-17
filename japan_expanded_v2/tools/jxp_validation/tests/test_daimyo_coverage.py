from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.build_consolidated_country_ideas import top_level_blocks
from jxp_validation.clausewitz import (
    Object,
    Scalar,
    first_object,
    first_scalar,
    parse_file,
)
from jxp_validation.daimyo_coverage import (
    audit_idea_assignment,
    audit_identity_depth,
    audit_forbidden_modifier_text,
    audit_major_identity_series,
    audit_map_identity_migration_text,
    audit_post_tag_idea_sync_text,
    check_daimyo_coverage,
    collect_idea_identities,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
MAP_BUILDER = MAP_ROOT / "tools" / "jxp_map_builder"
DAIMYO_REWARD_FILES = (
    MAIN_ROOT / "missions" / "Japanese_Missions.txt",
    MAIN_ROOT / "missions" / "jxp_04_daimyo_missions.txt",
    MAIN_ROOT / "missions" / "jxp_21_daimyo_house_missions.txt",
    MAIN_ROOT / "missions" / "jxp_81_major_daimyo_identity_missions.txt",
    MAP_ROOT / "missions" / "jxp_map_new_daimyo_missions.txt",
    MAP_ROOT / "missions" / "jxp_map_15_major_daimyo_identity_missions.txt",
)
ERA_AXES = frozenset(
    {"jxp_tenka_order", "jxp_imperial_sanction", "jxp_oceanic_opening"}
)
ERA_REWARD_EFFECT = re.compile(
    r"jxp_(?:add|subtract)_(?:tenka_order|imperial_sanction|oceanic_opening)_\d+_effect"
)


def _walk_entries(obj: Object | None):
    if obj is None:
        return
    for entry in obj.entries:
        yield entry
        if isinstance(entry.value, Object):
            yield from _walk_entries(entry.value)


def _codes(result: CheckResult) -> set[str]:
    return {issue.code for issue in result.issues}


def _identity_group(group: str, trigger: str) -> str:
    ideas = "\n".join(
        f"\tidea_{index} = {{ global_tax_modifier = 0.01 }}"
        for index in range(7)
    )
    return f"""{group} = {{
\tstart = {{ prestige = 1 }}
\tbonus = {{ discipline = 0.05 }}
\ttrigger = {{ {trigger} }}
\tfree = yes
{ideas}
}}
"""


class DaimyoCoverageTests(unittest.TestCase):
    def test_live_67_daimyo_tag_matrix_is_closed(self) -> None:
        result = check_daimyo_coverage(ValidationContext(MAIN_ROOT))
        self.assertEqual([], result.issues, result.to_dict())
        self.assertEqual(67, result.metrics["tags"])
        self.assertEqual(37, result.metrics["main_tags"])
        self.assertEqual(30, result.metrics["map_tags"])
        self.assertEqual(67, result.metrics["exact_idea_groups"])
        self.assertEqual(28, result.metrics["exact_major_identity_series"])
        self.assertEqual(12, result.metrics["generated_major_outputs"])
        self.assertEqual(268, result.metrics["dlc_profiles"])

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
            MAIN_ROOT
            / "tools"
            / "jxp_validation"
            / "idea_sources"
            / "jxp_map_daimyo_ideas.txt"
        ).read_text(encoding="utf-8")
        self.assertEqual(actual, rendered)
        self.assertFalse(
            (MAP_ROOT / "common" / "ideas" / "jxp_map_new_daimyo_ideas.txt").exists()
        )
        registry = (MAIN_ROOT / "common" / "ideas" / "00_country_ideas.txt").read_text(
            encoding="utf-8"
        )
        source_ids = [group for group, _start, _end in top_level_blocks(actual)]
        registry_ids = [group for group, _start, _end in top_level_blocks(registry)]
        self.assertEqual(source_ids, registry_ids[-len(source_ids) :])

    def test_daimyo_missions_never_hard_set_era_attributes(self) -> None:
        hard_sets: list[str] = []
        for path in DAIMYO_REWARD_FILES:
            document = parse_file(path)
            for series in document.root.entries:
                if not isinstance(series.value, Object):
                    continue
                for mission in series.value.entries:
                    if not (
                        mission.key
                        and "_mission_" in mission.key
                        and isinstance(mission.value, Object)
                    ):
                        continue
                    effect = first_object(mission.value, "effect")
                    for entry in _walk_entries(effect):
                        if entry.key in {
                            "set_variable",
                            "set_government_power",
                        } and isinstance(entry.value, Object):
                            axis = first_scalar(entry.value, "which") or first_scalar(
                                entry.value, "power_type"
                            )
                            if axis in ERA_AXES:
                                hard_sets.append(
                                    f"{path.name}:{mission.key}:{entry.key}:{axis}"
                                )
                        if (
                            entry.key in ERA_AXES
                            and isinstance(entry.value, Scalar)
                            and re.fullmatch(r"-?\d+(?:\.\d+)?", entry.value.text)
                        ):
                            hard_sets.append(
                                f"{path.name}:{mission.key}:direct:{entry.key}"
                            )
        self.assertEqual([], hard_sets)

    def test_each_daimyo_series_has_distinct_era_reward_signatures(self) -> None:
        duplicates: list[str] = []
        for path in DAIMYO_REWARD_FILES:
            document = parse_file(path)
            for series in document.root.entries:
                if not (series.key and isinstance(series.value, Object)):
                    continue
                seen: dict[tuple[str, ...], str] = {}
                for mission in series.value.entries:
                    if not (
                        mission.key
                        and "_mission_" in mission.key
                        and isinstance(mission.value, Object)
                    ):
                        continue
                    effect = first_object(mission.value, "effect")
                    signature = tuple(
                        sorted(
                            entry.key
                            for entry in _walk_entries(effect)
                            if entry.key and ERA_REWARD_EFFECT.fullmatch(entry.key)
                        )
                    )
                    if not signature:
                        continue
                    previous = seen.get(signature)
                    if previous is not None:
                        duplicates.append(
                            f"{path.name}:{series.key}:{previous}/{mission.key}:{signature}"
                        )
                    else:
                        seen[signature] = mission.key
        self.assertEqual([], duplicates)

    def test_shared_idea_trigger_mutation_is_rejected(self) -> None:
        identities = collect_idea_identities(ValidationContext(MAIN_ROOT))
        rkk = next(identity for identity in identities if identity.group == "RKK_ideas")
        mutated = replace(rkk, tags=("RKK", "MOG"))
        result = CheckResult("mutation")
        audit_idea_assignment("map", "RKK", "A", (mutated,), result)
        self.assertIn("daimyo.idea_not_exact_tag", _codes(result))

    def test_nonfree_idea_mutation_is_rejected(self) -> None:
        identities = collect_idea_identities(ValidationContext(MAIN_ROOT))
        rkk = next(identity for identity in identities if identity.group == "RKK_ideas")
        result = CheckResult("mutation")
        audit_idea_assignment(
            "map", "RKK", "A", (replace(rkk, free=False),), result
        )
        self.assertIn("daimyo.idea_not_free", _codes(result))

    def test_origin_flag_without_daimyo_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ideas = root / "common" / "ideas"
            ideas.mkdir(parents=True)
            (ideas / "00_country_ideas.txt").write_text(
                """RKK_ideas = {
\tstart = { prestige = 1 }
\tbonus = { discipline = 0.05 }
\ttrigger = { has_country_flag = jxp_map_origin_rkk }
\tfree = yes
\ta = { global_tax_modifier = 0.01 }
\tb = { global_tax_modifier = 0.01 }
\tc = { global_tax_modifier = 0.01 }
\td = { global_tax_modifier = 0.01 }
\te = { global_tax_modifier = 0.01 }
\tf = { global_tax_modifier = 0.01 }
\tg = { global_tax_modifier = 0.01 }
}
""",
                encoding="utf-8",
            )
            identity = collect_idea_identities(ValidationContext(root))[0]
        self.assertEqual((), identity.tags)

    def test_direct_tag_and_origin_flag_identities_are_both_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ideas = root / "common" / "ideas"
            ideas.mkdir(parents=True)
            (ideas / "00_country_ideas.txt").write_text(
                _identity_group("AAA_ideas", "tag = AAA")
                + _identity_group(
                    "RKK_ideas",
                    "jxp_is_daimyo_stage_trigger = yes "
                    "has_country_flag = jxp_map_origin_rkk",
                ),
                encoding="utf-8",
            )
            identities = collect_idea_identities(ValidationContext(root))
        self.assertEqual(
            {"AAA_ideas": ("AAA",), "RKK_ideas": ("RKK",)},
            {identity.group: identity.tags for identity in identities},
        )

    def test_missing_or_duplicate_origin_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ideas = root / "common" / "ideas"
            ideas.mkdir(parents=True)
            (ideas / "00_country_ideas.txt").write_text(
                _identity_group(
                    "RKK_ideas",
                    "jxp_is_daimyo_stage_trigger = yes "
                    "has_country_flag = jxp_map_origin_rkk",
                )
                + _identity_group(
                    "RKK_duplicate_ideas",
                    "jxp_is_daimyo_stage_trigger = yes "
                    "has_country_flag = jxp_map_origin_rkk",
                )
                + _identity_group(
                    "MOG_ideas", "jxp_is_daimyo_stage_trigger = yes"
                ),
                encoding="utf-8",
            )
            identities = collect_idea_identities(ValidationContext(root))
        rkk = tuple(identity for identity in identities if identity.tags == ("RKK",))
        result = CheckResult("mutation")
        audit_idea_assignment("map", "RKK", "A", rkk, result)
        self.assertIn("daimyo.idea_coverage", _codes(result))
        self.assertEqual(
            (), next(identity for identity in identities if identity.group == "MOG_ideas").tags
        )

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

    def test_shared_major_identity_scope_mutation_is_rejected(self) -> None:
        result = CheckResult("mutation")
        audit_major_identity_series(
            "map",
            "RKK",
            "A",
            "jxp_map_rkk_identity_missions",
            ("RKK", "MOG"),
            (),
            (),
            result,
        )
        self.assertIn("daimyo.major_identity_not_exact_tag", _codes(result))

    def test_major_identity_series_name_mutation_is_rejected(self) -> None:
        result = CheckResult("mutation")
        audit_major_identity_series(
            "main",
            "MRI",
            "A",
            "jxp_maritime_house_missions",
            ("MRI",),
            (),
            (),
            result,
        )
        self.assertIn("daimyo.major_identity_series", _codes(result))

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
            "\t\t\t\t\tNOT = { jxp_has_expected_route_national_ideas_trigger = yes }\n",
            "",
            1,
        )
        result = CheckResult("mutation")
        audit_post_tag_idea_sync_text(mutated, map_events, map_effects, result)
        self.assertIn("daimyo.post_tag_idea_sync", _codes(result))


if __name__ == "__main__":
    unittest.main()
