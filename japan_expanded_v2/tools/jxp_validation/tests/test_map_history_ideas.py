from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
LIVE_MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
LIVE_MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
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


def render_group(
    *,
    idea_count: int = 7,
    commented_tag: str | None = None,
    extra_trigger: str = "",
) -> str:
    comment = (
        f"\n\t\t# has_country_flag = jxp_map_origin_{commented_tag.lower()} {{ ignored }}\n\t"
        if commented_tag
        else ""
    )
    ideas = " ".join(
        f'idea_{index} = {{ global_tax_modifier = 0.0{index} prestige = 0.{index} note = "literal {{ # }}" }}'
        for index in range(idea_count)
    )
    legacy_ideas = " ".join(
        f"legacy_{index} = {{ global_tax_modifier = 0.0{index} }}"
        for index in range(7)
    )
    return f"""jxp_map_new_daimyo_ideas = {{
\tstart = {{ land_morale = 0.05 }}
\tbonus = {{ discipline = 0.05 }}
\ttrigger = {{ always = no }}
\tfree = yes
\t{legacy_ideas}
}}

AAA_ideas = {{
\tstart = {{ land_morale = 0.05 global_manpower_modifier = 0.10 }}
\tbonus = {{ discipline = 0.05 }}
\ttrigger = {{ jxp_is_daimyo_stage_trigger = yes has_country_flag = jxp_map_origin_aaa{extra_trigger}{comment} }}
\tfree = yes
\t# These braces must not affect object depth: {{ }}
\t{ideas}
}}
"""


def validate_text(text: str, tags: set[str]):
    with tempfile.TemporaryDirectory() as directory:
        map_root = Path(directory)
        builder_root = map_root / "tools" / "jxp_map_builder"
        builder_root.mkdir(parents=True)
        (builder_root / "daimyo_identity_plan.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tags": {
                        tag: {
                            "tier": "C",
                            "focus": ["global_tax_modifier", "0.10"],
                            "historical_role": "test",
                        }
                        for tag in tags
                    },
                }
            ),
            encoding="utf-8",
        )
        source = map_root / "jxp_map_daimyo_ideas.txt"
        source.write_text(text, encoding="utf-8")
        consolidated = map_root / "00_country_ideas.txt"
        consolidated.write_text(text, encoding="utf-8")
        report = VALIDATOR.Report()
        VALIDATOR.validate_ideas(
            tags,
            report,
            LIVE_MAIN_ROOT,
            map_root,
            idea_source_path=source,
            consolidated_path=consolidated,
        )
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
            any("identity idea groups are missing" in error for error in report.errors),
            report.errors,
        )

    def test_rejects_extra_activation_condition_outside_stage_and_origin(self) -> None:
        source = render_group(extra_trigger=" always = no")
        report = validate_text(source, {"AAA"})
        self.assertTrue(
            any("must use exact daimyo-stage" in error for error in report.errors),
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

    def test_live_runtime_identity_contract_is_complete(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        report = VALIDATOR.Report()
        VALIDATOR.validate_idea_runtime_contract(
            tags, report, LIVE_MAIN_ROOT, LIVE_MAP_ROOT
        )
        self.assertEqual([], report.errors)

    def test_runtime_identity_contract_rejects_missing_tag_guard(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        with tempfile.TemporaryDirectory() as directory:
            map_root = Path(directory)
            relative_files = (
                Path("common/scripted_triggers/jxp_map_triggers.txt"),
                Path("common/scripted_effects/jxp_map_effects.txt"),
                Path("common/on_actions/jxp_map_on_actions.txt"),
                Path("events/jxp_map_events.txt"),
            )
            for relative in relative_files:
                target = map_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIVE_MAP_ROOT / relative, target)
            trigger_path = (
                map_root / "common" / "scripted_triggers" / "jxp_map_triggers.txt"
            )
            trigger_path.write_text(
                trigger_path.read_text(encoding="utf-8").replace(
                    "\t\tAND = { tag = RKK has_idea_group = RKK_ideas }\n",
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            VALIDATOR.validate_idea_runtime_contract(
                tags, report, LIVE_MAIN_ROOT, map_root
            )
        self.assertTrue(
            any("Expected map identity trigger coverage drifted" in error for error in report.errors),
            report.errors,
        )

    def test_runtime_identity_contract_rejects_missing_origin_fallback(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        with tempfile.TemporaryDirectory() as directory:
            map_root = Path(directory)
            relative_files = (
                Path("common/scripted_triggers/jxp_map_triggers.txt"),
                Path("common/scripted_effects/jxp_map_effects.txt"),
                Path("common/on_actions/jxp_map_on_actions.txt"),
                Path("events/jxp_map_events.txt"),
            )
            for relative in relative_files:
                target = map_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIVE_MAP_ROOT / relative, target)
            effects_path = (
                map_root / "common" / "scripted_effects" / "jxp_map_effects.txt"
            )
            effects_path.write_text(
                effects_path.read_text(encoding="utf-8").replace(
                    "\tif = { limit = { NOT = { jxp_map_has_any_origin_trigger = yes } tag = RKK } set_country_flag = jxp_map_origin_rkk }\n",
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            VALIDATOR.validate_idea_runtime_contract(
                tags, report, LIVE_MAIN_ROOT, map_root
            )
        self.assertTrue(
            any("Map origin recorder coverage drifted" in error for error in report.errors),
            report.errors,
        )

    def test_runtime_identity_contract_rejects_positive_origin_guard(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        with tempfile.TemporaryDirectory() as directory:
            map_root = Path(directory)
            relative_files = (
                Path("common/scripted_triggers/jxp_map_triggers.txt"),
                Path("common/scripted_effects/jxp_map_effects.txt"),
                Path("common/on_actions/jxp_map_on_actions.txt"),
                Path("events/jxp_map_events.txt"),
            )
            for relative in relative_files:
                target = map_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIVE_MAP_ROOT / relative, target)
            effects_path = (
                map_root / "common" / "scripted_effects" / "jxp_map_effects.txt"
            )
            effects_path.write_text(
                effects_path.read_text(encoding="utf-8").replace(
                    "NOT = { jxp_map_has_any_origin_trigger = yes } tag = RKK",
                    "jxp_map_has_any_origin_trigger = yes tag = RKK",
                    1,
                ),
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            VALIDATOR.validate_idea_runtime_contract(
                tags, report, LIVE_MAIN_ROOT, map_root
            )
        self.assertTrue(
            any("Malformed map origin recorder branch" in error for error in report.errors),
            report.errors,
        )

    def test_runtime_identity_contract_rejects_missing_fresh_sync(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        with tempfile.TemporaryDirectory() as directory:
            map_root = Path(directory)
            relative_files = (
                Path("common/scripted_triggers/jxp_map_triggers.txt"),
                Path("common/scripted_effects/jxp_map_effects.txt"),
                Path("common/on_actions/jxp_map_on_actions.txt"),
                Path("events/jxp_map_events.txt"),
            )
            for relative in relative_files:
                target = map_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIVE_MAP_ROOT / relative, target)
            effects_path = (
                map_root / "common" / "scripted_effects" / "jxp_map_effects.txt"
            )
            effects_path.write_text(
                effects_path.read_text(encoding="utf-8").replace(
                    "\tjxp_map_sync_identity_ideas_effect = yes\n",
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            VALIDATOR.validate_idea_runtime_contract(
                tags, report, LIVE_MAIN_ROOT, map_root
            )
        self.assertTrue(
            any("postcondition idea sync" in error for error in report.errors),
            report.errors,
        )

    def test_runtime_identity_contract_rejects_marker_only_v014_guard(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        with tempfile.TemporaryDirectory() as directory:
            map_root = Path(directory)
            relative_files = (
                Path("common/scripted_triggers/jxp_map_triggers.txt"),
                Path("common/scripted_effects/jxp_map_effects.txt"),
                Path("common/on_actions/jxp_map_on_actions.txt"),
                Path("events/jxp_map_events.txt"),
            )
            for relative in relative_files:
                target = map_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIVE_MAP_ROOT / relative, target)
            effects_path = (
                map_root / "common" / "scripted_effects" / "jxp_map_effects.txt"
            )
            effects_path.write_text(
                effects_path.read_text(encoding="utf-8").replace(
                    "\t\t\t\tNOT = { jxp_map_idea_identity_v014_postcondition_trigger = yes }\n",
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            VALIDATOR.validate_idea_runtime_contract(
                tags, report, LIVE_MAIN_ROOT, map_root
            )
        self.assertTrue(
            any("marker is present but the postcondition is false" in error for error in report.errors),
            report.errors,
        )

    def test_runtime_identity_contract_rejects_unconditional_v014_marker(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        with tempfile.TemporaryDirectory() as directory:
            map_root = Path(directory)
            relative_files = (
                Path("common/scripted_triggers/jxp_map_triggers.txt"),
                Path("common/scripted_effects/jxp_map_effects.txt"),
                Path("common/on_actions/jxp_map_on_actions.txt"),
                Path("events/jxp_map_events.txt"),
            )
            for relative in relative_files:
                target = map_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIVE_MAP_ROOT / relative, target)
            effects_path = (
                map_root / "common" / "scripted_effects" / "jxp_map_effects.txt"
            )
            effects_path.write_text(
                effects_path.read_text(encoding="utf-8").replace(
                    "\t\tif = {\n"
                    "\t\t\tlimit = { jxp_map_idea_identity_v014_postcondition_trigger = yes }\n"
                    "\t\t\tset_country_flag = jxp_map_idea_identity_migration_v014\n"
                    "\t\t}\n",
                    "\t\tset_country_flag = jxp_map_idea_identity_migration_v014\n",
                    1,
                ),
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            VALIDATOR.validate_idea_runtime_contract(
                tags, report, LIVE_MAIN_ROOT, map_root
            )
        self.assertTrue(
            any("postcondition commit branch" in error for error in report.errors),
            report.errors,
        )

    def test_runtime_identity_contract_rejects_extra_not_child(self) -> None:
        manifest = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "generated_countries_manifest.json"
            ).read_text(encoding="utf-8")
        )
        tags = set(manifest["idea_groups"])
        with tempfile.TemporaryDirectory() as directory:
            map_root = Path(directory)
            relative_files = (
                Path("common/scripted_triggers/jxp_map_triggers.txt"),
                Path("common/scripted_effects/jxp_map_effects.txt"),
                Path("common/on_actions/jxp_map_on_actions.txt"),
                Path("events/jxp_map_events.txt"),
            )
            for relative in relative_files:
                target = map_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIVE_MAP_ROOT / relative, target)
            effects_path = (
                map_root / "common" / "scripted_effects" / "jxp_map_effects.txt"
            )
            effects_path.write_text(
                effects_path.read_text(encoding="utf-8").replace(
                    "NOT = { jxp_map_has_any_origin_trigger = yes } tag = RKK",
                    "NOT = { jxp_map_has_any_origin_trigger = yes always = no } tag = RKK",
                    1,
                ),
                encoding="utf-8",
            )
            report = VALIDATOR.Report()
            VALIDATOR.validate_idea_runtime_contract(
                tags, report, LIVE_MAIN_ROOT, map_root
            )
        self.assertTrue(
            any("Malformed map origin recorder branch" in error for error in report.errors),
            report.errors,
        )


class CompanionGeneratedHistorySafetyTests(unittest.TestCase):
    def test_live_map_ship_names_are_globally_unique_and_vanilla_disjoint(self) -> None:
        plan = json.loads(
            (
                LIVE_MAP_ROOT
                / "tools"
                / "jxp_map_builder"
                / "history_plan.json"
            ).read_text(encoding="utf-8")
        )
        report = VALIDATOR.Report()
        suffixes = VALIDATOR.read_builder_ship_name_suffixes(report)
        generated: list[str] = []
        for country in plan["countries"]:
            path = (
                LIVE_MAP_ROOT
                / "common"
                / "countries"
                / f"JXP {country['name']}.txt"
            )
            generated.extend(
                VALIDATOR.validate_country_ship_names(
                    path,
                    VALIDATOR.expected_map_ship_names(country, suffixes),
                    country["tag"],
                    report,
                )
            )
        baseline = VALIDATOR.scan_country_ship_names(GAME_ROOT)
        baseline.update(VALIDATOR.scan_country_ship_names(LIVE_MAIN_ROOT))
        VALIDATOR.validate_global_ship_name_registry(
            generated,
            len(plan["countries"]) * len(suffixes),
            baseline,
            report,
        )
        self.assertEqual([], report.errors)
        self.assertEqual(960, len(generated))
        self.assertEqual(960, len(set(generated)))

    def test_shared_ship_name_pool_is_rejected_globally(self) -> None:
        report = VALIDATOR.Report()
        shared = [f"Shared{index}Maru" for index in range(32)] * 30
        VALIDATOR.validate_global_ship_name_registry(shared, 960, set(), report)
        self.assertTrue(
            any("not globally unique" in error for error in report.errors),
            report.errors,
        )

    def test_ship_name_case_only_collision_is_rejected_globally(self) -> None:
        report = VALIDATOR.Report()
        VALIDATOR.validate_global_ship_name_registry(
            ["HikariMaru", "hikarimaru"], 2, set(), report
        )
        self.assertTrue(
            any("not globally unique" in error for error in report.errors),
            report.errors,
        )

    def test_live_map_histories_have_no_invalid_core_removals(self) -> None:
        invalid = {}
        for path in (LIVE_MAP_ROOT / "history" / "provinces").glob("*.txt"):
            failures = VALIDATOR.invalid_core_removals(
                path.read_text(encoding="cp1252")
            )
            if failures:
                invalid[path.name] = failures
        self.assertEqual({}, invalid)

    def test_duplicate_or_stale_remove_core_is_rejected(self) -> None:
        same_date = """add_core = AAA
1500.1.1 = { remove_core = AAA remove_core = AAA }
"""
        stale = """add_core = AAA
1500.1.1 = { remove_core = AAA }
1510.1.1 = { remove_core = AAA }
"""
        self.assertEqual([(VALIDATOR.parse_date("1500.1.1"), "AAA")], VALIDATOR.invalid_core_removals(same_date))
        self.assertEqual([(VALIDATOR.parse_date("1510.1.1"), "AAA")], VALIDATOR.invalid_core_removals(stale))


class CompanionAreaLocalisationTests(unittest.TestCase):
    def test_tokai_land_area_uses_tokaido_instead_of_east_china_sea(self) -> None:
        report = VALIDATOR.Report()
        VALIDATOR.validate_area_localisation_plan(
            {"areas": {"jxp_tokai_area": "东海道"}},
            ' jxp_tokai_area:0 "东海道"\n',
            report,
        )
        self.assertEqual([], report.errors)

    def test_east_china_sea_label_is_rejected_for_tokai_land_area(self) -> None:
        report = VALIDATOR.Report()
        VALIDATOR.validate_area_localisation_plan(
            {"areas": {"jxp_tokai_area": "东海"}},
            ' jxp_tokai_area:0 "东海"\n',
            report,
        )
        self.assertTrue(
            any("must display as 东海道" in error for error in report.errors),
            report.errors,
        )


if __name__ == "__main__":
    unittest.main()
