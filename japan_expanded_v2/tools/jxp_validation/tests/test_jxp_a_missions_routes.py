from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import re
import sys
import unittest

from jxp_validation.clausewitz import Object, Scalar, first_scalar, parse_file
from jxp_validation.missions import MISSION_SERIES_METADATA


MAIN_ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = (
    MAIN_ROOT
    / "tools"
    / "jxp_a_socioeconomic_builder"
    / "build_missions_routes.py"
)


def _load_builder():
    spec = importlib.util.spec_from_file_location("jxp_a_build_missions_routes", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load build_missions_routes.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def _mission_series(path: Path):
    document = parse_file(path)
    for entry in document.root.entries:
        if entry.key is None or not isinstance(entry.value, Object):
            continue
        slot = first_scalar(entry.value, "slot")
        if slot not in {"1", "2", "3", "4", "5"}:
            continue
        missions = tuple(
            child.key
            for child in entry.value.entries
            if child.key is not None
            and child.key not in MISSION_SERIES_METADATA
            and isinstance(child.value, Object)
        )
        yield entry.key, int(slot), entry.value, missions


def _collect_mission_refs(obj: Object) -> set[str]:
    refs: set[str] = set()
    for entry in obj.entries:
        if entry.key == "mission_completed" and isinstance(entry.value, Scalar):
            refs.add(entry.value.text)
        if entry.key == "required_missions" and isinstance(entry.value, Object):
            refs.update(
                child.value.text
                for child in entry.value.entries
                if child.key is None and isinstance(child.value, Scalar)
            )
        if isinstance(entry.value, Object):
            refs.update(_collect_mission_refs(entry.value))
    return refs


class MissionsRoutesBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = BUILDER.render_outputs()
        cls.mission_path = MAIN_ROOT / BUILDER.MISSION_PATH
        cls.series = list(_mission_series(cls.mission_path))

    def test_generated_outputs_are_current_and_clausewitz_parses(self) -> None:
        for relative, expected in self.outputs.items():
            path = MAIN_ROOT / relative
            with self.subTest(path=relative.as_posix()):
                self.assertTrue(path.is_file())
                self.assertEqual(expected, path.read_bytes())
                if path.suffix == ".txt":
                    parse_file(path)

    def test_engine_safe_152_mission_layout_uses_only_a_slots(self) -> None:
        all_ids = [mission for _name, _slot, _body, missions in self.series for mission in missions]
        self.assertEqual(152, len(all_ids))
        self.assertEqual(152, len(set(all_ids)))
        self.assertEqual({1, 2, 3}, {slot for _name, slot, _body, _missions in self.series})
        counts = {name: len(missions) for name, _slot, _body, missions in self.series}
        self.assertEqual(18, counts["jxp_a_105_shared_capital_slot_1_missions"])
        self.assertEqual(17, counts["jxp_a_105_shared_capital_slot_2_missions"])
        for profile in BUILDER.ROUTE_PROFILES:
            self.assertEqual(8, counts[f"jxp_a_105_{profile.key}_domestic_missions"])
        for slot in (1, 2, 3):
            self.assertEqual(7, counts[f"jxp_a_105_commercial_council_slot_{slot}_missions"])
        self.assertEqual(Counter({1: 2, 2: 2, 3: 13}), Counter(slot for _name, slot, _body, _missions in self.series))

    def test_profiles_compose_one_a_series_per_slot_without_competition(self) -> None:
        # Standard profiles share exactly one slot-1 and one slot-2 series and
        # select one mutually exclusive slot-3 series.  Commercial Council
        # instead selects its own slots 1-3 and never masquerades as uncommitted.
        names = {name for name, _slot, _body, _missions in self.series}
        for profile in BUILDER.ROUTE_PROFILES:
            active = {
                "jxp_a_105_shared_capital_slot_1_missions": 1,
                "jxp_a_105_shared_capital_slot_2_missions": 2,
                f"jxp_a_105_{profile.key}_domestic_missions": 3,
            }
            self.assertEqual({1, 2, 3}, set(active.values()))
            self.assertTrue(set(active) <= names)
        commercial = {
            f"jxp_a_105_commercial_council_slot_{slot}_missions": slot
            for slot in (1, 2, 3)
        }
        self.assertEqual({1, 2, 3}, set(commercial.values()))
        triggers = (MAIN_ROOT / BUILDER.TRIGGER_PATH).read_text(encoding="utf-8")
        uncommitted = triggers.split("jxp_a_105_profile_uncommitted_trigger = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("NOT = { has_country_flag = jxp_path_commercial_council }", uncommitted)
        legacy_route = (MAIN_ROOT / "common/scripted_triggers/jxp_scripted_triggers.txt").read_text(encoding="utf-8").split("jxp_has_any_route_trigger = {", 1)[1].split("\n}", 1)[0]
        self.assertNotIn("jxp_path_commercial_council", legacy_route)

        # The new profile is nevertheless a complete five-column tree without
        # changing B-owned bytes: slots 1-3 are generated above, frozen Shinto
        # slot 4 remains eligible, and frozen uncommitted-horizon slot 5 remains
        # eligible because the legacy route helper deliberately excludes it.
        shinto_slot = (MAIN_ROOT / "missions/jxp_11_branching_missions.txt").read_text(encoding="utf-8")
        shinto_slot = shinto_slot.split("jxp_shinto_branch_missions = {", 1)[1].split("\njxp_christian_branch_missions = {", 1)[0]
        self.assertIn("slot = 4", shinto_slot)
        self.assertNotIn("jxp_path_commercial_council", shinto_slot)
        horizon_slot = (MAIN_ROOT / "missions/jxp_40_final_state_completion_missions.txt").read_text(encoding="utf-8")
        horizon_slot = horizon_slot.split("jxp_japan_uncommitted_horizon_missions = {", 1)[1].split("\njxp_japan_sakoku_horizon_missions = {", 1)[0]
        self.assertIn("slot = 5", horizon_slot)
        self.assertIn("jxp_has_any_route_trigger = yes", horizon_slot)
        final_uncommitted = (MAIN_ROOT / "common/scripted_triggers/jxp_79_final_state_triggers.txt").read_text(encoding="utf-8")
        final_uncommitted = final_uncommitted.split("jxp_final_state_uncommitted_trigger = {", 1)[1].split("\njxp_final_state_sakoku_trigger = {", 1)[0]
        self.assertIn("has_country_flag = jxp_path_commercial_council", final_uncommitted)

    def test_route_rows_reach_late_game_and_dependencies_never_point_backwards(self) -> None:
        coordinates: dict[str, tuple[int, int]] = {}
        mission_bodies: dict[str, Object] = {}
        for _series, slot, body, missions in self.series:
            for mission in missions:
                mission_body = next(
                    entry.value
                    for entry in body.entries
                    if entry.key == mission and isinstance(entry.value, Object)
                )
                row = first_scalar(mission_body, "position")
                self.assertIsNotNone(row, mission)
                coordinates[mission] = (slot, int(row))
                mission_bodies[mission] = mission_body
        for series_name, slot, body, missions in self.series:
            rows = [coordinates[mission][1] for mission in missions]
            if slot == 3:
                self.assertGreaterEqual(max(rows), 10, series_name)
                if series_name != "jxp_a_105_commercial_council_slot_3_missions":
                    profile = series_name.removeprefix("jxp_a_105_").removesuffix("_domestic_missions")
                    self.assertEqual(list(BUILDER.ROUTE_ROWS_BY_PROFILE[profile]), rows, series_name)
            self.assertLessEqual(max(b - a for a, b in zip(rows, rows[1:])), 2, series_name)
            for mission in missions:
                current_row = coordinates[mission][1]
                required = next(
                    (
                        entry.value
                        for entry in mission_bodies[mission].entries
                        if entry.key == "required_missions" and isinstance(entry.value, Object)
                    ),
                    None,
                )
                dependencies = (
                    tuple(
                        entry.value.text
                        for entry in required.entries
                        if entry.key is None and isinstance(entry.value, Scalar)
                    )
                    if required is not None
                    else ()
                )
                for dependency in dependencies:
                    if dependency in coordinates:
                        self.assertGreater(
                            current_row,
                            coordinates[dependency][1],
                            f"{dependency} -> {mission}",
                        )

    def test_old_a_series_are_removed_not_overridden_by_duplicate_tombstones(self) -> None:
        old = {name for name, _slot in BUILDER.TOMBSTONE_SERIES}
        found: dict[str, list[str]] = {name: [] for name in old}
        for path in (MAIN_ROOT / "missions").glob("*.txt"):
            for name, _slot, _body, _missions in _mission_series(path):
                if name in old:
                    found[name].append(path.name)
        self.assertEqual({}, {name: paths for name, paths in found.items() if paths})

    def test_frozen_b_files_and_mixed_slot_blocks_keep_schema_v2_hashes(self) -> None:
        manifest = BUILDER._load_frozen_manifest()
        self.assertEqual(2, manifest["schema_version"])
        BUILDER._validate_frozen_surface(manifest)
        self.assertEqual(13, len(manifest["whole_file_sha256"]))
        self.assertEqual(6, len(manifest["slot_series_sha256"]))
        self.assertEqual(18, sum(len(value) for value in manifest["slot_series_sha256"].values()))

    def test_every_retained_legacy_anchor_is_consumed_by_frozen_slot_4_or_5(self) -> None:
        generated_ids = {
            mission
            for _name, _slot, _body, missions in self.series
            for mission in missions
        }
        legacy_ids = {mission for mission in generated_ids if not mission.startswith("jxp_a_105_")}
        self.assertEqual(60, len(legacy_ids))
        refs: set[str] = set()
        for path in (MAIN_ROOT / "missions").glob("*.txt"):
            for _name, slot, body, _missions in _mission_series(path):
                if slot in {4, 5}:
                    refs.update(_collect_mission_refs(body))
        self.assertEqual(set(), legacy_ids - refs)
        for profile in BUILDER.ROUTE_PROFILES:
            with self.subTest(profile=profile.key):
                self.assertTrue({mission for _position, mission in profile.legacy_by_position} <= refs)

    def test_profile_fingerprint_migration_and_replay_are_transactional(self) -> None:
        triggers = (MAIN_ROOT / BUILDER.TRIGGER_PATH).read_text(encoding="utf-8")
        effects = (MAIN_ROOT / BUILDER.EFFECT_PATH).read_text(encoding="utf-8")
        for key in (
            "jxp_a_105_mission_profile_fingerprint_valid_trigger",
            "jxp_a_105_capture_legacy_mission_progress_effect",
            "jxp_a_105_replay_mission_progress_effect",
            "jxp_a_105_reconcile_mission_profile_effect",
            "jxp_a_105_migrate_mission_schema_effect",
        ):
            self.assertIn(key, triggers + effects)
        migrate = effects.split("jxp_a_105_migrate_mission_schema_effect = {", 1)[1]
        fingerprint = migrate.index("jxp_a_105_mission_profile_fingerprint_valid_trigger = yes")
        replay = migrate.index("jxp_a_105_replay_mission_progress_effect = yes")
        marker = migrate.index("set_country_flag = jxp_a_105_mission_schema_v1")
        self.assertLess(fingerprint, replay)
        self.assertLess(replay, marker)
        self.assertIn("has_country_flag = jxp_a_105_mission_replay_in_progress", (MAIN_ROOT / BUILDER.MISSION_PATH).read_text(encoding="utf-8"))
        self.assertNotIn("swap_non_generic_missions", effects)
        self.assertIn("jxp_refresh_route_missions_effect = yes", effects)
        capture = effects.split("jxp_a_105_capture_legacy_mission_progress_effect = {", 1)[1].split("\n}\n", 1)[0]
        replay_block = effects.split("jxp_a_105_replay_mission_progress_effect = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("NOT = { has_country_flag = jxp_a_105_legacy_snapshot_captured }", capture)
        self.assertEqual(1, capture.count("jxp_a_105_capture_legacy_mission_progress_once_effect = yes"))
        self.assertNotIn("clr_country_flag = jxp_a_105_legacy_snapshot_captured", replay_block)
        self.assertGreater(
            migrate.index("clr_country_flag = jxp_a_105_legacy_snapshot_captured"),
            migrate.index("jxp_a_105_mission_profile_fingerprint_valid_trigger = yes", replay),
        )

    def test_founder_unification_and_three_era_attributes_are_wired(self) -> None:
        triggers = (MAIN_ROOT / BUILDER.TRIGGER_PATH).read_text(encoding="utf-8")
        effects = (MAIN_ROOT / BUILDER.EFFECT_PATH).read_text(encoding="utf-8")
        origins = [origin for values in BUILDER.FOUNDER_ORIGINS.values() for origin in values]
        map_origins = [
            origin
            for values in BUILDER.MAP_FOUNDER_ORIGINS.values()
            for origin in values
        ]
        self.assertEqual(37, len(origins))
        self.assertEqual(37, len(set(origins)))
        self.assertEqual(30, len(map_origins))
        self.assertEqual(30, len(set(map_origins)))
        self.assertEqual(67, len(origins) + len(map_origins))
        self.assertEqual(set(BUILDER.FOUNDER_ORIGINS), set(BUILDER.MAP_FOUNDER_ORIGINS))
        for category in BUILDER.FOUNDER_ORIGINS:
            self.assertIn(f"jxp_iface_a_founder_{category}_legacy", effects)
            for origin in BUILDER.MAP_FOUNDER_ORIGINS[category]:
                self.assertEqual(1, effects.count(f"has_country_flag = jxp_map_origin_{origin}"))
        map_effects = (
            MAIN_ROOT.parent
            / "japan_expanded_v2_map/common/scripted_effects/jxp_map_effects.txt"
        ).read_text(encoding="utf-8")
        published_map_origins = set(
            re.findall(r"set_country_flag = jxp_map_origin_([a-z0-9_]+)", map_effects)
        )
        self.assertEqual(set(map_origins), published_map_origins)
        # Main-mod runtime consumes only the semantic origin flags.  It never
        # hard-references a companion-only tag.
        for origin in map_origins:
            self.assertNotIn(f"tag = {origin.upper()}", effects)
        for category, required in {
            "commercial": {"rkk", "myo"},
            "maritime": {"mtu", "mts", "ari"},
            "bureaucratic": {"nbs", "krd"},
            "communal": {"hng", "tgs"},
            "frontier": {"tgr", "mog"},
        }.items():
            self.assertTrue(required <= set(BUILDER.MAP_FOUNDER_ORIGINS[category]))
        for method in ("blade", "edict", "league"):
            self.assertIn(f"jxp_24_unification_by_{method}", effects)
            self.assertIn(f"jxp_a_unification_method_{method}", effects)
        founder = effects.split("jxp_a_105_reconcile_founder_legacy_effect = {", 1)[1].split("\n}\n", 1)[0]
        diplomacy = founder.index("has_country_flag = jxp_iface_house_diplomacy_ready")
        bureaucratic = founder.index("set_country_flag = jxp_iface_a_founder_bureaucratic_legacy", diplomacy)
        self.assertLess(diplomacy, bureaucratic)
        unification = effects.split("jxp_a_105_reconcile_unification_method_effect = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("has_country_flag = jxp_iface_a_founder_frontier_legacy", unification)
        self.assertIn("has_country_flag = jxp_iface_a_founder_maritime_legacy", unification)
        self.assertIn("set_country_flag = jxp_a_unification_method_blade", unification)
        self.assertIn("set_country_flag = jxp_a_unification_method_league", unification)
        for stage in range(1, 5):
            block = triggers.split(f"jxp_a_105_market_stage_{stage}_support_trigger = {{", 1)[1].split("\n}\n", 1)[0]
            for variable in ("jxp_tenka_order", "jxp_imperial_sanction", "jxp_oceanic_opening"):
                self.assertGreaterEqual(block.count(variable), 2)

    def test_twelve_routes_have_eight_tasks_four_events_models_crises_and_interfaces(self) -> None:
        event_doc = parse_file(MAIN_ROOT / BUILDER.EVENT_PATH)
        visible_events = [entry for entry in event_doc.root.entries if entry.key == "country_event"]
        self.assertEqual(71, len(visible_events))
        events = (MAIN_ROOT / BUILDER.EVENT_PATH).read_text(encoding="utf-8")
        effects = (MAIN_ROOT / BUILDER.EFFECT_PATH).read_text(encoding="utf-8")
        modifiers = (MAIN_ROOT / BUILDER.MODIFIER_PATH).read_text(encoding="utf-8")
        for index, profile in enumerate(BUILDER.ROUTE_PROFILES):
            with self.subTest(profile=profile.key):
                for stage in range(1, 5):
                    self.assertIn(f"jxp_domestic_routes.{100 + index * 10 + stage}", events)
                self.assertIn(f"jxp_a_105_model_{profile.key} = {{", modifiers)
                self.assertIn(f"jxp_a_105_capstone_{profile.key} = {{", modifiers)
                self.assertIn(f"jxp_a_105_apply_{profile.key}_profile_effect", effects)
                self.assertIn(f"jxp_iface_a_domestic_{profile.key}_ready", effects + events)
                self.assertIn(profile.crisis, BUILDER.render_localisation())
                primary, secondary = BUILDER.ROUTE_STAKEHOLDERS[profile.key]
                event_one = events.split(f"id = jxp_domestic_routes.{100 + index * 10 + 1}", 1)[1].split("\n}", 1)[0]
                event_three = events.split(f"id = jxp_domestic_routes.{100 + index * 10 + 3}", 1)[1].split("\n}", 1)[0]
                self.assertIn(f"estate = {primary}", event_one)
                self.assertIn(f"estate = {secondary}", event_one)
                self.assertIn(f"add_treasury = -{150 + index * 25}", event_three)
        self.assertEqual(
            12,
            len(
                {
                    events.split(f"id = jxp_domestic_routes.{100 + index * 10 + 3}", 1)[1].split("\n}", 1)[0]
                    for index in range(12)
                }
            ),
        )

    def test_capital_and_commercial_tasks_have_real_business_effects(self) -> None:
        for index in range(1, 36):
            rewards = BUILDER._capital_rewards(index)
            substantive = tuple(
                line
                for line in rewards
                if not line.startswith("add_adm_power =")
                and not line.startswith("add_dip_power =")
            )
            with self.subTest(kind="capital", index=index):
                self.assertTrue(substantive)
                self.assertNotIn("duration = -1", "\n".join(rewards))
        for index in range(1, 22):
            rewards = BUILDER._commercial_rewards(index)
            substantive = tuple(
                line
                for line in rewards
                if not line.startswith("add_adm_power =")
                and not line.startswith("add_dip_power =")
            )
            with self.subTest(kind="commercial", index=index):
                self.assertTrue(substantive)
                self.assertNotIn("duration = -1", "\n".join(rewards))

        missions = (MAIN_ROOT / BUILDER.MISSION_PATH).read_text(encoding="utf-8")
        for index, task in enumerate(BUILDER.CAPITAL_TASKS, 1):
            self.assertIn(
                f"set_country_flag = {BUILDER.capital_business_flag(index)}",
                missions,
                task.mission_id,
            )
        for index in range(1, 22):
            self.assertIn(
                f"set_country_flag = {BUILDER.commercial_business_flag(index)}",
                missions,
                BUILDER.commercial_id(index),
            )
        for required_task in (2, 4, 6, 9, 13, 20, 22, 23, 24, 25, 26, 27, 31):
            event_id = BUILDER.CAPITAL_POLICY_EVENT_BY_TASK[required_task]
            self.assertIn(
                f"country_event = {{ id = jxp_capital_missions.{event_id} }}",
                "\n".join(BUILDER._capital_rewards(required_task)),
            )

    def test_policy_choices_cover_required_historical_tradeoffs(self) -> None:
        events = (MAIN_ROOT / BUILDER.EVENT_PATH).read_text(encoding="utf-8")
        self.assertEqual(14, len(BUILDER.CAPITAL_POLICY_EVENTS))
        expected_options = {1: 3, 2: 3, 3: 3, 4: 3, 5: 4, 6: 5, 7: 4, 8: 3, 9: 5, 10: 3, 11: 3, 12: 4, 13: 3, 14: 5}
        for event in BUILDER.CAPITAL_POLICY_EVENTS:
            with self.subTest(event=event.event_id):
                self.assertEqual(expected_options[event.event_id], len(event.options))
                self.assertIn(f"id = jxp_capital_missions.{event.event_id}", events)
                for option in event.options:
                    self.assertIn(
                        f"name = jxp_capital_missions.{event.event_id}.{option.key}",
                        events,
                    )
        shipping_primary = next(event for event in BUILDER.CAPITAL_POLICY_EVENTS if event.event_id == 5)
        shipping_secondary = next(event for event in BUILDER.CAPITAL_POLICY_EVENTS if event.event_id == 6)
        self.assertEqual(4, len([option for option in shipping_primary.options if option.flag]))
        self.assertEqual(4, len([option for option in shipping_secondary.options if option.flag]))
        for option in shipping_secondary.options[:-1]:
            self.assertTrue(option.trigger)
            self.assertIn("NOT = { has_country_flag = jxp_a_105_shipping_", option.trigger[0])

    def test_commercial_council_is_strict_rare_and_has_three_government_branches(self) -> None:
        triggers = (MAIN_ROOT / BUILDER.TRIGGER_PATH).read_text(encoding="utf-8")
        decisions = (MAIN_ROOT / BUILDER.DECISION_PATH).read_text(encoding="utf-8")
        reforms = (MAIN_ROOT / BUILDER.REFORM_PATH).read_text(encoding="utf-8")
        events = (MAIN_ROOT / BUILDER.EVENT_PATH).read_text(encoding="utf-8")
        gate = triggers.split("jxp_a_105_can_enter_commercial_council_trigger = {", 1)[1].split("\n}\n", 1)[0]
        for token in (
            "jxp_is_unified_japan_state_trigger = yes",
            "is_year = 1600",
            "has_institution = global_trade",
            "jxp_a_market_stage_at_least_3_trigger = yes",
            "jxp_iface_a_public_credit_ready",
            "jxp_a_company_has_at_least_2_trigger = yes",
            "value = 3",
            "monthly_income = 35",
            "estate_loyalty = { estate = estate_burghers loyalty = 60 }",
            "estate_influence = { estate = estate_burghers influence = 60 }",
            "NOT = { estate_influence = { estate = estate_nobles influence = 70 } }",
            "NOT = { is_bankrupt = yes }",
        ):
            self.assertIn(token, gate)
        self.assertIn("factor = 0.02", decisions)
        self.assertEqual(4, reforms.count("allow_normal_conversion = no"))
        self.assertIn("jxp_a_105_commercial_council_state_reform = {", reforms)
        neutral = reforms.split("jxp_a_105_commercial_council_state_reform = {", 1)[1].split("\n}\n", 1)[0]
        for branch in ("shogunate", "merchant", "company"):
            self.assertIn(f"has_country_flag = jxp_a_105_commercial_branch_{branch}", neutral)
        for branch in ("shogunate", "merchant_council", "company_empire"):
            self.assertIn(f"jxp_a_105_commercial_{branch}_reform = {{", reforms)
        crisis = events.split("id = jxp_commercial_council.5", 1)[1].split("\n}", 1)[0]
        for option in "abcdef":
            self.assertIn(f"jxp_commercial_council.5.{option}", crisis)
        disaster = (MAIN_ROOT / BUILDER.DISASTER_PATH).read_text(encoding="utf-8")
        for token in (
            "jxp_a_105_commercial_capital_crisis = {",
            "has_country_flag = jxp_a_105_commercial_crisis_pressure",
            "on_start = jxp_commercial_council.8",
            "on_end = jxp_commercial_council.7",
            "can_start = {",
            "progress = {",
            "can_end = {",
        ):
            self.assertIn(token, disaster)
        for _option, outcome, modifier in BUILDER.COMMERCIAL_CRISIS_OUTCOMES:
            self.assertIn(f"set_country_flag = jxp_a_105_commercial_crisis_outcome_{outcome}", events)
            self.assertIn(f"add_country_modifier = {{ name = {modifier} duration = -1 }}", events)
        self.assertIn("jxp_a_105_settle_commercial_capital_crisis", decisions)
        self.assertIn("had_country_flag = { flag = jxp_a_105_commercial_crisis_active days = 365 }", decisions)
        self.assertIn("end_disaster = jxp_a_105_commercial_capital_crisis", events)

    def test_commercial_name_override_and_cleanup_do_not_recurse(self) -> None:
        effects = (MAIN_ROOT / BUILDER.EFFECT_PATH).read_text(encoding="utf-8")
        clear = effects.split("jxp_a_105_clear_commercial_council_effect = {", 1)[1].split("\n}\n", 1)[0]
        enter = effects.split("jxp_a_105_enter_commercial_council_effect = {", 1)[1].split("\n}\n", 1)[0]
        exit_route = effects.split("jxp_a_105_exit_commercial_council_route_effect = {", 1)[1].split("\n}\n", 1)[0]
        full_cleanup = effects.split("jxp_a_105_full_cleanup_effect = {", 1)[1].split("\n}\n", 1)[0]
        clear_branch = effects.split("jxp_a_105_clear_commercial_branch_effect = {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("jxp_clear_all_route_flags_effect", clear)
        self.assertNotIn("change_government_to_", clear)
        self.assertIn("restore_country_name = yes", clear)
        self.assertIn("jxp_clear_all_route_flags_effect = yes", enter)
        self.assertIn("jxp_grant_route_reforms_effect = yes", enter)
        self.assertIn("add_government_reform = jxp_a_105_commercial_council_state_reform", enter)
        self.assertIn("override_country_name = JXP_COMMERCIAL_COUNCIL_JAPAN", enter)
        self.assertIn("has_country_flag = jxp_a_105_commercial_branch_merchant", exit_route)
        self.assertIn("government = republic", exit_route)
        self.assertIn("change_government_to_monarchy = yes", exit_route)
        self.assertNotIn("change_government_to_", full_cleanup)
        self.assertIn("remove_government_reform = jxp_a_105_commercial_council_state_reform", clear_branch)
        for name in (
            "JXP_COMMERCIAL_COUNCIL_JAPAN",
            "JXP_COMMERCIAL_MERCHANT_REPUBLIC",
            "JXP_COMMERCIAL_COMPANY_EMPIRE",
        ):
            self.assertIn(f"override_country_name = {name}", effects)
        for key, government, reform in (
            ("shogunate", "monarchy", "jxp_a_105_commercial_shogunate_reform"),
            ("merchant", "republic", "jxp_a_105_commercial_merchant_council_reform"),
            ("company", "monarchy", "jxp_a_105_commercial_company_empire_reform"),
        ):
            block = effects.split(f"jxp_a_105_set_commercial_{key}_branch_effect = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertIn(f"change_government_to_{government} = yes", block)
            self.assertIn(f"add_government_reform = {reform}", block)
            self.assertIn("jxp_a_105_clear_commercial_branch_effect = yes", block)

    def test_persistent_state_trigger_covers_cleanup_sentinels(self) -> None:
        triggers = (MAIN_ROOT / BUILDER.TRIGGER_PATH).read_text(encoding="utf-8")
        block = triggers.split("jxp_a_105_any_persistent_state_trigger = {", 1)[1].split("\n}\n", 1)[0]
        for profile in (*BUILDER.ROUTE_PROFILES,):
            self.assertIn(f"has_country_flag = jxp_a_105_model_{profile.key}", block)
            self.assertIn(f"has_country_modifier = jxp_a_105_model_{profile.key}", block)
            self.assertIn(f"has_country_flag = jxp_iface_a_domestic_{profile.key}_ready", block)
        for token in (
            "jxp_a_105_model_commercial_council",
            "jxp_iface_a_founder_commercial_legacy",
            "jxp_a_unification_method_blade",
            "jxp_path_commercial_council",
            "jxp_a_105_commercial_branch_merchant",
            "jxp_a_105_commercial_merchant_council_reform",
            "jxp_a_105_mission_schema_v1",
            "jxp_a_105_legacy_capital_depth_7",
            "jxp_a_105_legacy_route_depth_8",
            "jxp_a_105_crisis_civil_conflict",
            "jxp_a_105_capstone_toyotomi",
            "jxp_a_105_commercial_state_shareholding",
            "jxp_a_105_commercial_crisis_outcome_four_estates",
            "jxp_a_105_commercial_council_state_reform",
            "jxp_a_105_mining_governance_ready",
        ):
            self.assertIn(token, block)

    def test_public_consistency_triggers_and_complete_cleanup_surface(self) -> None:
        triggers = (MAIN_ROOT / BUILDER.TRIGGER_PATH).read_text(encoding="utf-8")
        effects = (MAIN_ROOT / BUILDER.EFFECT_PATH).read_text(encoding="utf-8")
        modifiers = (MAIN_ROOT / BUILDER.MODIFIER_PATH).read_text(encoding="utf-8")
        for trigger in (
            "jxp_a_105_has_any_domestic_route_trigger",
            "jxp_a_105_founder_legacy_consistent_trigger",
            "jxp_a_105_unification_method_consistent_trigger",
            "jxp_a_105_profile_state_consistent_trigger",
            "jxp_a_105_any_persistent_state_trigger",
        ):
            self.assertEqual(1, triggers.count(f"\n{trigger} = {{"), trigger)
        cleanup = effects.split("jxp_a_105_full_cleanup_effect = {", 1)[1].split("\n}\n", 1)[0]
        for profile in BUILDER.ROUTE_PROFILES:
            self.assertIn(f"clr_country_flag = jxp_a_105_model_{profile.key}", cleanup)
            self.assertIn(f"clr_country_flag = jxp_iface_a_domestic_{profile.key}_ready", cleanup)
            self.assertIn(f"remove_country_modifier = jxp_a_105_capstone_{profile.key}", cleanup)
        for depth in range(1, 8):
            self.assertIn(f"clr_country_flag = jxp_a_105_legacy_capital_depth_{depth}", cleanup)
        for depth in range(1, 9):
            self.assertIn(f"clr_country_flag = jxp_a_105_legacy_route_depth_{depth}", cleanup)
        nonexistent_tradeoffs = (
            "jxp_a_105_high_order_tradeoff",
            "jxp_a_105_low_order_tradeoff",
            "jxp_a_105_high_sanction_tradeoff",
            "jxp_a_105_low_sanction_tradeoff",
            "jxp_a_105_high_ocean_tradeoff",
            "jxp_a_105_low_ocean_tradeoff",
        )
        for stale in nonexistent_tradeoffs:
            self.assertNotIn(f"\n{stale} = {{", modifiers)
            self.assertNotIn(stale, cleanup)
            self.assertNotIn(stale, triggers)
        for flag in (
            "jxp_a_105_mission_schema_v1",
            "jxp_a_105_mission_replay_in_progress",
            "jxp_a_105_legacy_snapshot_captured",
            "jxp_a_105_commercial_crisis_unlocked",
            "jxp_a_105_commercial_crisis_pressure",
            "jxp_a_105_commercial_crisis_resolved",
            "jxp_iface_a_company_state_route",
            "jxp_iface_a_company_charter_active",
            "jxp_a_105_company_state_eligible",
        ):
            self.assertIn(f"clr_country_flag = {flag}", cleanup)
        for index in range(1, 36):
            self.assertIn(
                f"clr_country_flag = {BUILDER.capital_business_flag(index)}",
                cleanup,
            )
        for index in range(1, 22):
            self.assertIn(
                f"clr_country_flag = {BUILDER.commercial_business_flag(index)}",
                cleanup,
            )
        for flag in BUILDER.policy_choice_flags():
            self.assertIn(f"clr_country_flag = {flag}", cleanup)

    def test_history_gates_and_performance_contract(self) -> None:
        combined = "\n".join(
            (MAIN_ROOT / path).read_text(encoding="utf-8")
            for path in (
                BUILDER.MISSION_PATH,
                BUILDER.TRIGGER_PATH,
                BUILDER.EFFECT_PATH,
                BUILDER.EVENT_PATH,
                BUILDER.DECISION_PATH,
            )
        )
        self.assertIn("is_year = 1730", combined)
        self.assertIn("is_year = 1601", combined)
        self.assertIn("is_year = 1600", combined)
        for forbidden in (
            "on_monthly_pulse",
            "every_country",
            "every_province",
            "add_permanent_claim",
            "jxp_a_capitalism_score",
            "jxp_a_company_meter",
        ):
            self.assertNotIn(forbidden, combined)

    def test_complete_chinese_localisation_and_exact_escaped_mirror(self) -> None:
        source = (MAIN_ROOT / BUILDER.SOURCE_LOC_PATH).read_text(encoding="utf-8")
        active = (MAIN_ROOT / BUILDER.ACTIVE_LOC_PATH).read_bytes()
        self.assertTrue(active.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(BUILDER._load_escape_module().escape_text(source).encode("utf-8-sig"), active)
        keys = set(re.findall(r"(?m)^\s*([A-Za-z0-9_.-]+):0\s", source))
        mission_ids = {
            mission
            for _name, _slot, _body, missions in self.series
            for mission in missions
        }
        for mission_id in mission_ids:
            self.assertIn(f"{mission_id}_title", keys)
            self.assertIn(f"{mission_id}_desc", keys)
            self.assertIn(f"{mission_id}_reward_tt", keys)
        reward_entries = re.findall(
            r'(?m)^\s*([A-Za-z0-9_.-]+_reward_tt):0\s+"([^"]*)"',
            source,
        )
        generated_rewards = {
            key: value
            for key, value in reward_entries
            if key.removesuffix("_reward_tt") in mission_ids
        }
        self.assertEqual(152, len(generated_rewards))
        self.assertEqual(152, len(set(generated_rewards.values())))
        for key, value in generated_rewards.items():
            with self.subTest(tooltip=key):
                self.assertIn("实际解锁", value)
                self.assertIn("当前市场阶段", value)
                self.assertIn("活跃会社数量", value)
                self.assertRegex(value, r"支持|支持者")

        mission_text = (MAIN_ROOT / BUILDER.MISSION_PATH).read_text(encoding="utf-8")
        for stage in range(5):
            self.assertEqual(
                152,
                mission_text.count(f"custom_tooltip = jxp_a_105_progress_market_{stage}_tt"),
            )
        for companies in range(6):
            self.assertEqual(
                152,
                mission_text.count(f"custom_tooltip = jxp_a_105_progress_companies_{companies}_tt"),
            )

        modifier_doc = parse_file(MAIN_ROOT / BUILDER.MODIFIER_PATH)
        modifier_keys = {
            entry.key for entry in modifier_doc.root.entries if entry.key is not None
        }
        self.assertEqual(40, len(modifier_keys))
        for modifier in modifier_keys:
            self.assertIn(modifier, keys)
            self.assertIn(f"{modifier}_desc", keys)
        for flag in (
            "jxp_a_105_commercial_crisis_pressure",
            "jxp_a_105_commercial_crisis_resolved",
        ):
            self.assertIn(flag, keys)
        for flag in BUILDER.policy_choice_flags():
            self.assertIn(flag, keys)
        for index in range(1, 36):
            self.assertIn(BUILDER.capital_business_flag(index), keys)
        for index in range(1, 22):
            self.assertIn(BUILDER.commercial_business_flag(index), keys)
        for shared in (
            "jxp_path_commercial_council",
            "jxp_iface_a_public_credit_ready",
            "jxp_iface_a_company_state_route",
        ):
            self.assertNotRegex(source, rf"(?m)^\s*{re.escape(shared)}:0\s")


if __name__ == "__main__":
    unittest.main()
