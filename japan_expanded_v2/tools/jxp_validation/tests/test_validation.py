from __future__ import annotations

from pathlib import Path
import struct
import tempfile
import unittest

from jxp_validation.assets import validate_reform_dds_bytes
from jxp_validation.clausewitz import (
    ClausewitzParseError,
    entries_named,
    first_object,
    parse_text,
)
from jxp_validation.compatibility import check_release_compatibility
from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.create_legacy_bom_mission_aliases_v0241 import render_alias
from jxp_validation.create_japanese_mission_overrides_v0231 import patch_potentials
from jxp_validation.create_mission_runtime_fingerprint_v0242 import render as render_fingerprint
from jxp_validation.effective_topology import (
    _active_generic_series,
    analyze_effective_topology,
    summarize_cells,
)
from jxp_validation.missions import (
    BASE_PROFILES,
    DAIMYO_TAGS,
    DLC_PROFILE_VARIANTS,
    Mission,
    MissionSeries,
    PROFILES,
    Profile,
    evaluate_potential,
    extract_mission_series,
    find_position_collisions,
    check_missions,
    check_mission_scripted_triggers,
)
from jxp_validation.reforms import EXPECTED_LEVEL_MEMBERS
from jxp_validation.shared_ledger import check_shared_development_ledger
from jxp_validation.rewrite_government_reforms_v0232 import (
    rewrite_founder_file,
    rewrite_route_file,
    write_effect_file,
)
from reflow_missions_v0231 import reorder_series_missions


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]


class ClausewitzParserTests(unittest.TestCase):
    def test_preserves_repeated_keys_and_ignores_comments(self) -> None:
        document = parse_text(
            """
            group = {
                # A repeated-key list must not collapse.
                tag = JAP
                tag = CJP
                required = { first second }
            }
            """
        )
        group = first_object(document.root, "group")
        self.assertIsNotNone(group)
        self.assertEqual([entry.value.text for entry in entries_named(group, "tag")], ["JAP", "CJP"])

    def test_rejects_unclosed_object(self) -> None:
        with self.assertRaises(ClausewitzParseError):
            parse_text("group = { tag = JAP")


class CompatibilityGuardTests(unittest.TestCase):
    def test_rejects_plausible_but_invalid_reform_progress_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mission_root = root / "missions"
            mission_root.mkdir(parents=True)
            (mission_root / "test.txt").write_text(
                "test = { effect = { add_government_reform_progress = 25 } }\n",
                encoding="utf-8",
            )
            result = check_release_compatibility(ValidationContext(root))
        self.assertIn(
            "compat.invalid_reform_progress_effect",
            {issue.code for issue in result.issues},
        )


class SharedLedgerTests(unittest.TestCase):
    def _copy_coordination_surface(self, destination: Path) -> Path:
        main_root = destination / "japan_expanded_v2"
        map_root = destination / "japan_expanded_v2_map"
        (main_root / "dev_logs").mkdir(parents=True)
        (map_root / "dev_logs").mkdir(parents=True)
        (map_root / "tools" / "jxp_map_validation").mkdir(parents=True)
        ledger = (
            LIVE_MOD_ROOT / "dev_logs" / "JXP_SHARED_DEVELOPMENT_LEDGER.md"
        ).read_text(encoding="utf-8")
        (main_root / "dev_logs" / "JXP_SHARED_DEVELOPMENT_LEDGER.md").write_text(
            ledger,
            encoding="utf-8",
        )
        (main_root / "AGENTS.md").write_text(
            "dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md\nDo not launch EU4\n",
            encoding="utf-8",
        )
        (map_root / "AGENTS.md").write_text(
            "../japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md\n"
            "Do not launch EU4\n",
            encoding="utf-8",
        )
        (
            map_root
            / "tools"
            / "jxp_map_validation"
            / "main_compatibility_contract.json"
        ).write_text("{}\n", encoding="utf-8")
        return main_root

    @staticmethod
    def _write_descriptors(main_root: Path, main_version: str) -> None:
        map_root = main_root.parent / "japan_expanded_v2_map"
        (main_root / "descriptor.mod").write_text(
            f'version="{main_version}"\n', encoding="utf-8"
        )
        (main_root.parent / "japan_expanded_v2.mod").write_text(
            f'version="{main_version}"\n', encoding="utf-8"
        )
        (map_root / "descriptor.mod").write_text(
            'version="0.1.2-alpha"\n', encoding="utf-8"
        )
        (main_root.parent / "japan_expanded_v2_map.mod").write_text(
            'version="0.1.2-alpha"\n', encoding="utf-8"
        )

    def test_live_shared_ledger_is_consistent(self) -> None:
        result = check_shared_development_ledger(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)

    def test_shared_ledger_rejects_descriptor_version_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_coordination_surface(Path(directory))
            self._write_descriptors(root, "9.9.9")
            result = check_shared_development_ledger(ValidationContext(root))
        self.assertIn(
            "ledger.main_version_drift",
            {issue.code for issue in result.issues},
        )

    def test_shared_ledger_rejects_unindexed_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_coordination_surface(Path(directory))
            self._write_descriptors(root, "0.27.0")
            map_root = root.parent / "japan_expanded_v2_map"
            (map_root / "dev_logs" / "unindexed_report.md").write_text(
                "# New report\n", encoding="utf-8"
            )
            result = check_shared_development_ledger(ValidationContext(root))
        self.assertIn(
            "ledger.report_unindexed",
            {issue.code for issue in result.issues},
        )


class GovernmentReformRewriteTests(unittest.TestCase):
    def test_semantic_level_matrix_covers_active_reforms(self) -> None:
        all_ids = set().union(*EXPECTED_LEVEL_MEMBERS.values())
        founder_ids = {
            reform_id
            for reform_id in all_ids
            if reform_id.startswith("jxp_reform_founder_")
        }
        self.assertEqual(len(founder_ids), 39)
        self.assertEqual(len(all_ids - founder_ids), 27)
        self.assertIn(
            "jxp_reform_founder_otm_funai_arsenal",
            EXPECTED_LEVEL_MEMBERS["military_doctrines"],
        )
        self.assertIn(
            "jxp_reform_founder_toyotomi_five_regents",
            EXPECTED_LEVEL_MEMBERS["growth_of_administration"],
        )
        self.assertIn(
            "jxp_reform_kirishitan_nagasaki_admiralty",
            EXPECTED_LEVEL_MEMBERS["military_doctrines"],
        )

    def test_route_rewrite_is_idempotent(self) -> None:
        source = """jxp_reform_open_test = {
\ticon = \"test\"
\tmonarchy = yes
\trepublic = yes
\tvalid_for_nation_designer = no
\tpotential = { has_country_flag = jxp_path_open_trade }
\tmodifiers = { trade_efficiency = 0.05 }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "route.txt"
            path.write_text(source, encoding="utf-8")
            rewrite_route_file(path)
            first = path.read_text(encoding="utf-8")
            rewrite_route_file(path)
            self.assertEqual(path.read_text(encoding="utf-8"), first)
            self.assertEqual(first.count("\ttrigger = {"), 1)
            self.assertIn("jxp_is_japanese_polity_trigger = yes", first)

    def test_founder_rewrite_is_idempotent(self) -> None:
        source = """jxp_reform_founder_test = {
\ticon = \"test\"
\tmonarchy = yes
\trepublic = yes
\tvalid_for_nation_designer = no
\tpotential = {
\t\tjxp_is_unified_japan_state_trigger = yes
\t\thas_country_flag = jxp_origin_test
\t}
\tmodifiers = { prestige = 0.5 }
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "founder.txt"
            path.write_text(source, encoding="utf-8")
            rewrite_founder_file(path)
            first = path.read_text(encoding="utf-8")
            rewrite_founder_file(path)
            self.assertEqual(path.read_text(encoding="utf-8"), first)
            self.assertEqual(first.count("has_reform = jxp_reform_founder_test"), 1)

    def test_visibility_effect_writer_does_not_auto_grant_founder_reforms(self) -> None:
        founders = (
            ("jxp_reform_founder_test", "jxp_origin_test"),
            ("jxp_reform_founder_generic_test", None),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "effects.txt"
            write_effect_file(path, ("jxp_reform_old",), founders)
            text = path.read_text(encoding="utf-8")
        self.assertNotIn("add_government_reform = jxp_reform_founder_", text)
        self.assertIn("jxp_founder_reform_unlocked_v0234", text)
        self.assertIn("add_government_reform = quash_noble_power_reform", text)

class MissionProfileTests(unittest.TestCase):
    def test_mission_requires_canonical_title_and_description_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mission_root = root / "missions"
            localisation_root = root / "localisation"
            mission_root.mkdir(parents=True)
            localisation_root.mkdir(parents=True)
            (mission_root / "test.txt").write_text(
                """test_series = {
    slot = 1
    generic = no
    potential = { always = no }
    test_mission = {
        icon = mission_conqueror_icon
        position = 1
        required_missions = { }
        trigger = { always = yes }
        effect = { }
    }
}
""",
                encoding="utf-8",
            )
            (localisation_root / "test_l_english.yml").write_text(
                'l_english:\n test_mission:0 "Bare alias"\n test_mission_title:0 "Test"\n',
                encoding="utf-8-sig",
            )
            result = check_missions(ValidationContext(root))
        missing = [
            issue.message
            for issue in result.issues
            if issue.code == "mission.localisation_missing"
        ]
        self.assertEqual(missing, [
            "mission test_mission is missing canonical localisation key test_mission_desc"
        ])

    def test_profile_matrix_covers_every_tag_across_four_dlc_states(self) -> None:
        self.assertEqual(len(DLC_PROFILE_VARIANTS), 4)
        self.assertEqual(len(BASE_PROFILES), len(DAIMYO_TAGS) + 10)
        self.assertEqual(len(PROFILES), len(BASE_PROFILES) * len(DLC_PROFILE_VARIANTS))

    def test_legacy_bom_alias_is_byte_exact_and_inactive(self) -> None:
        payload = render_alias("jxp_japan_state_missions", 1)
        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))
        body = payload[3:].decode("ascii")
        self.assertTrue(body.startswith("jxp_japan_state_missions = {"))
        self.assertIn("potential_on_load = { always = no }", body)
        self.assertIn("potential = { always = no }", body)
        self.assertNotIn("effect =", body)

    def test_disjoint_rows_in_same_slot_do_not_collide(self) -> None:
        collisions = find_position_collisions(
            [(3, 2, "foundation"), (3, 8, "foundation"), (3, 14, "route")]
        )
        self.assertEqual(collisions, {})

    def test_same_slot_and_row_collides(self) -> None:
        collisions = find_position_collisions([(4, 21, "a"), (4, 21, "b")])
        self.assertEqual(collisions[(4, 21)], ("a", "b"))

    def test_confucian_harmonized_profile(self) -> None:
        document = parse_text(
            """
            potential = {
                tag = CJP
                religion = confucianism
                has_harmonized_with = shinto
            }
            """
        )
        profile = Profile(
            "CJP",
            "CJP",
            "confucianism",
            "eastern",
            harmonized=frozenset({"shinto"}),
        )
        values, unknown = evaluate_potential(first_object(document.root, "potential"), profile)
        self.assertEqual(values, frozenset({True}))
        self.assertEqual(unknown, ())

    def test_domination_jap_potential_uses_actual_tag_and_dlc(self) -> None:
        document = parse_text(
            """
            potential = {
                tag = JAP
                has_dlc = "Domination"
                NOT = { map_setup = map_setup_random }
            }
            """
        )
        potential = first_object(document.root, "potential")
        jap = Profile("JAP", "JAP", "shinto", "eastern")
        route = Profile("KJP", "KJP", "catholic", "christian")
        self.assertEqual(evaluate_potential(potential, jap)[0], frozenset({True}))
        self.assertEqual(evaluate_potential(potential, route)[0], frozenset({False}))

    def test_jxp_override_excludes_custom_mission_profiles(self) -> None:
        document = parse_text(
            """
            potential = {
                tag = JAP
                NOT = { jxp_use_custom_missions_trigger = yes }
            }
            """
        )
        profile = Profile("JAP", "JAP", "shinto", "eastern")
        values, unknown = evaluate_potential(
            first_object(document.root, "potential"), profile
        )
        self.assertEqual(values, frozenset({False}))
        self.assertEqual(unknown, ())

    def test_pinned_override_disables_existing_preload_gate(self) -> None:
        source = """vanilla = {
\tslot = 1
\tpotential_on_load = {
\t\thas_dlc = \"Domination\"
\t}
\tpotential = {
\t\ttag = JAP
\t}
\tmission = { position = 1 }
}
"""
        patched, count = patch_potentials(source, "DOM_Japanese_Missions.txt")
        self.assertEqual(count, 1)
        self.assertIn("# JXP_OVERRIDE_DISABLE_VANILLA_SERIES\n\t\talways = no", patched)
        self.assertIn("# JXP_OVERRIDE_DISABLE_VANILLA_POTENTIAL\n\t\talways = no", patched)
        self.assertIn("NOT = { jxp_use_custom_missions_trigger = yes }", patched)
        self.assertIn("# JXP_OVERRIDE_TOMBSTONE_LEGACY_SERIES", patched)
        self.assertIn("\nvanilla = {", patched)
        self.assertNotIn("jxp_disabled_vanilla_vanilla", patched)

    def test_pinned_override_adds_missing_preload_gate(self) -> None:
        source = """vanilla = {
\tslot = 1
\tpotential = {
\t\ttag = JAP
\t}
\tmission = { position = 1 }
}
"""
        patched, count = patch_potentials(source, "Japanese_Missions.txt")
        self.assertEqual(count, 1)
        self.assertIn("\tpotential_on_load = {\n", patched)
        self.assertIn("# JXP_OVERRIDE_DISABLE_VANILLA_SERIES\n\t\talways = no", patched)
        self.assertIn("# JXP_OVERRIDE_DISABLE_VANILLA_POTENTIAL\n\t\talways = no", patched)
        self.assertIn("# JXP_OVERRIDE_TOMBSTONE_LEGACY_SERIES", patched)
        self.assertIn("\nvanilla = {", patched)
        self.assertNotIn("jxp_disabled_vanilla_vanilla", patched)

    def test_pinned_override_routes_legacy_swap_through_delayed_helper(self) -> None:
        source = """vanilla = {
\tslot = 1
\tpotential = { tag = JAP }
\tmission = {
\t\teffect = { swap_non_generic_missions = yes }
\t}
}
"""
        patched, count = patch_potentials(source, "DOM_Japanese_Missions.txt")
        self.assertEqual(count, 1)
        self.assertNotIn("swap_non_generic_missions = yes", patched)
        self.assertIn("jxp_refresh_route_missions_effect = yes", patched)

    def test_reflow_physically_orders_mission_blocks(self) -> None:
        source = """series = {
\tslot = 1
\tsecond = { position = 3 required_missions = { first } }

\tfirst = { position = 1 required_missions = { } }
}
"""
        reordered, changed = reorder_series_missions(
            source,
            "series",
            ("first", "second"),
        )
        self.assertTrue(changed)
        self.assertLess(reordered.index("\tfirst ="), reordered.index("\tsecond ="))

    def test_runtime_fingerprint_is_parseable_and_keeps_legacy_anchors(self) -> None:
        rendered = render_fingerprint()
        parse_text(rendered)
        self.assertIn("has_mission = jap_balance_shinokosho", rendered)
        self.assertIn("has_mission = jxp_mission_cjp_three_teachings_register", rendered)
        self.assertIn("has_mission = jxp_mission_ejp_restore_daijokan", rendered)
        self.assertIn("has_mission = jxp_mission_rfj_oranda_factors", rendered)
        self.assertIn("has_mission = jxp_mission_wak_letters_of_black_current", rendered)
        self.assertIn("jxp_mission_tree_needs_reconcile_trigger = {", rendered)

    def test_vanilla_implicit_rows_and_potential_on_load_metadata(self) -> None:
        document = parse_text(
            """
            vanilla_group = {
                slot = 1
                potential = { tag = JAP }
                potential_on_load = { always = yes }
                first = { required_missions = { } }
                second = { position = 3 required_missions = { first } }
                third = { required_missions = { second } }
            }
            """
        )

        class StubContext:
            def document(self, _source):
                return document

            def relative(self, source):
                return source.as_posix()

        result = CheckResult("test")
        series = extract_mission_series(
            StubContext(),
            result,
            [Path("vanilla.txt")],
            infer_implicit_positions=True,
        )
        self.assertEqual([mission.mission_id for mission in series[0].missions], ["first", "second", "third"])
        self.assertEqual([mission.row for mission in series[0].missions], [1, 3, 4])
        self.assertEqual(result.issues, [])

    def test_missing_scripted_trigger_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trigger_root = root / "common" / "scripted_triggers"
            mission_root = root / "missions"
            trigger_root.mkdir(parents=True)
            mission_root.mkdir()
            (trigger_root / "known.txt").write_text(
                "jxp_known_trigger = { always = yes }\n",
                encoding="utf-8",
            )
            mission_file = mission_root / "test.txt"
            mission_file.write_text(
                """
                test_series = {
                    slot = 1
                    potential = { jxp_known_trigger = yes }
                    mission = {
                        position = 1
                        required_missions = { }
                        trigger = { jxp_missing_trigger = yes }
                        effect = { }
                    }
                }
                """,
                encoding="utf-8",
            )
            context = ValidationContext(root)
            result = CheckResult("test")
            calls = check_mission_scripted_triggers(context, result, (mission_file,))
            self.assertEqual(calls, 2)
            self.assertEqual(
                {issue.code for issue in result.issues},
                {"mission.scripted_trigger_missing"},
            )
            self.assertIn("jxp_missing_trigger", result.issues[0].message)


def _series(
    origin: str,
    series_name: str,
    mission_id: str,
    slot: int,
    row: int,
    required: tuple[str, ...] = (),
) -> MissionSeries:
    source = Path(origin) / f"{series_name}.txt"
    mission = Mission(mission_id, row, required, source, 10, series_name, slot)
    return MissionSeries(series_name, slot, False, None, (mission,), source, 1)


def _origin(source: Path) -> str:
    return source.parts[0]


class EffectiveTopologyTests(unittest.TestCase):
    def test_generic_fallback_only_fills_unoccupied_slots(self) -> None:
        occupied = _series("vanilla", "generic_two", "generic_two", 2, 1)
        fallback = _series("vanilla", "generic_four", "generic_four", 4, 1)
        occupied = MissionSeries(
            occupied.name,
            occupied.slot,
            True,
            occupied.potential,
            occupied.missions,
            occupied.source,
            occupied.line,
        )
        fallback = MissionSeries(
            fallback.name,
            fallback.slot,
            True,
            fallback.potential,
            fallback.missions,
            fallback.source,
            fallback.line,
        )
        active, unknown = _active_generic_series(
            (occupied, fallback),
            Profile("JAP", "JAP", "shinto", "eastern"),
            {2},
        )
        self.assertEqual([series.name for series in active], ["generic_four"])
        self.assertEqual(unknown, ())

    def test_combined_vanilla_mod_collision_is_detected(self) -> None:
        vanilla = _series("vanilla", "vanilla_group", "vanilla_mission", 1, 1)
        mod = _series("mod", "mod_group", "mod_mission", 1, 1)
        problems, _edges = analyze_effective_topology(
            (vanilla, mod),
            (vanilla, mod),
            _origin,
        )
        self.assertIn("effective.cell_collision", {problem.code for problem in problems})

    def test_disjoint_cells_in_same_active_slot_still_overlap_series(self) -> None:
        first = _series("mod", "jxp_first", "jxp_first", 2, 1)
        second = _series("mod", "jxp_second", "jxp_second", 2, 4)
        problems, _edges = analyze_effective_topology(
            (first, second),
            (first, second),
            _origin,
        )
        self.assertIn(
            "effective.series_slot_overlap",
            {problem.code for problem in problems},
        )

    def test_coordinated_non_jxp_segments_may_share_slot(self) -> None:
        first = _series("vanilla", "base_first", "base_first", 2, 1)
        second = _series("vanilla", "base_second", "base_second", 2, 4)
        problems, _edges = analyze_effective_topology(
            (first, second),
            (first, second),
            _origin,
        )
        self.assertNotIn(
            "effective.series_slot_overlap",
            {problem.code for problem in problems},
        )

    def test_disjoint_vanilla_and_mod_series_do_not_mimic_engine_overlap(self) -> None:
        vanilla = _series("vanilla", "vanilla_group", "vanilla_mission", 2, 1)
        mod = _series("mod", "mod_group", "mod_mission", 2, 4)
        problems, _edges = analyze_effective_topology(
            (vanilla, mod),
            (vanilla, mod),
            _origin,
        )
        self.assertNotIn(
            "effective.series_slot_overlap",
            {problem.code for problem in problems},
        )

    def test_cross_source_inactive_prerequisite_is_detected(self) -> None:
        vanilla = _series("vanilla", "vanilla_group", "vanilla_base", 1, 1)
        mod = _series("mod", "mod_group", "mod_followup", 1, 2, ("vanilla_base",))
        problems, _edges = analyze_effective_topology((mod,), (vanilla, mod), _origin)
        self.assertIn(
            "effective.cross_source_prerequisite_inactive",
            {problem.code for problem in problems},
        )

    def test_cross_source_edge_must_point_to_larger_row(self) -> None:
        vanilla = _series("vanilla", "vanilla_group", "vanilla_base", 1, 2)
        mod = _series("mod", "mod_group", "mod_followup", 2, 2, ("vanilla_base",))
        problems, cross_source_edges = analyze_effective_topology(
            (vanilla, mod),
            (vanilla, mod),
            _origin,
        )
        self.assertEqual(cross_source_edges, 1)
        self.assertIn("effective.edge_not_forward", {problem.code for problem in problems})

    def test_more_than_five_columns_is_detected(self) -> None:
        series = _series("mod", "bad_column", "mission", 6, 1)
        problems, _edges = analyze_effective_topology((series,), (series,), _origin)
        self.assertIn("effective.column_range", {problem.code for problem in problems})

    def test_renderer_rejects_long_row_span(self) -> None:
        parent = _series("mod", "parent", "parent", 1, 1)
        child = _series("mod", "child", "child", 1, 4, ("parent",))
        problems, _edges = analyze_effective_topology(
            (parent, child),
            (parent, child),
            _origin,
        )
        self.assertIn("effective.edge_row_span", {problem.code for problem in problems})

    def test_renderer_rejects_nonadjacent_columns(self) -> None:
        parent = _series("mod", "parent", "parent", 1, 1)
        child = _series("mod", "child", "child", 3, 2, ("parent",))
        problems, _edges = analyze_effective_topology(
            (parent, child),
            (parent, child),
            _origin,
        )
        self.assertIn("effective.edge_column_span", {problem.code for problem in problems})

    def test_renderer_rejects_two_row_diagonal(self) -> None:
        parent = _series("mod", "parent", "parent", 2, 1)
        child = _series("mod", "child", "child", 1, 3, ("parent",))
        problems, _edges = analyze_effective_topology(
            (parent, child),
            (parent, child),
            _origin,
        )
        self.assertIn(
            "effective.edge_diagonal_span",
            {problem.code for problem in problems},
        )

    def test_renderer_rejects_crossing_diagonals(self) -> None:
        left_top = _series("mod", "left_top", "left_top", 1, 1)
        right_top = _series("mod", "right_top", "right_top", 2, 1)
        left_bottom = _series(
            "mod", "left_bottom", "left_bottom", 1, 2, ("right_top",)
        )
        right_bottom = _series(
            "mod", "right_bottom", "right_bottom", 2, 2, ("left_top",)
        )
        series = (left_top, right_top, left_bottom, right_bottom)
        problems, _edges = analyze_effective_topology(series, series, _origin)
        self.assertIn("effective.diagonal_crossing", {problem.code for problem in problems})

    def test_verbose_cell_summary_keeps_sources_separate(self) -> None:
        series = (
            _series("vanilla", "one", "a", 1, 1),
            _series("vanilla", "two", "b", 1, 2),
            _series("vanilla", "three", "c", 3, 8),
        )
        missions = tuple(group.missions[0] for group in series)
        self.assertEqual(summarize_cells(missions), "3 cells [s1:1-2; s3:8]")


def _rgba_dds(alpha: int) -> bytes:
    width = height = 57
    header = bytearray(128)
    header[:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    struct.pack_into("<I", header, 8, 0x100F)  # caps, height, width, pitch, pixel format
    struct.pack_into("<I", header, 12, height)
    struct.pack_into("<I", header, 16, width)
    struct.pack_into("<I", header, 20, width * 4)
    struct.pack_into("<I", header, 76, 32)
    struct.pack_into("<I", header, 80, 0x41)  # RGB + alpha pixels
    struct.pack_into("<I", header, 88, 32)
    struct.pack_into("<I", header, 92, 0x00FF0000)
    struct.pack_into("<I", header, 96, 0x0000FF00)
    struct.pack_into("<I", header, 100, 0x000000FF)
    struct.pack_into("<I", header, 104, 0xFF000000)
    struct.pack_into("<I", header, 108, 0x1000)
    pixel = bytes((16, 32, 48, alpha))
    return bytes(header + pixel * (width * height))


class DdsTests(unittest.TestCase):
    def test_accepts_57_square_rgba_with_visible_alpha(self) -> None:
        self.assertEqual(validate_reform_dds_bytes(_rgba_dds(255)), ())

    def test_rejects_blank_alpha(self) -> None:
        errors = validate_reform_dds_bytes(_rgba_dds(0))
        self.assertTrue(any("alpha channel is blank" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
