from __future__ import annotations

import re
import unittest
from pathlib import Path

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]


def read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


class ColonialStateDepthTests(unittest.TestCase):
    @staticmethod
    def _series_position_lists(payload: str) -> list[list[int]]:
        starts = list(re.finditer(r"^(jxp_b_(?:94_nya|95_(?:hkk|njf|oia)|114_tpf)_\w+_missions)\s*=\s*\{", payload, re.MULTILINE))
        result: list[list[int]] = []
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(payload)
            positions = [int(value) for value in re.findall(r"^\s*position\s*=\s*(\d+)", payload[match.start():end], re.MULTILINE)]
            result.append(positions)
        return result

    def test_exact_five_column_mission_depth_and_tpf_separation(self) -> None:
        nya = read("missions/jxp_b_94_new_yamato_missions.txt")
        secondary = read("missions/jxp_b_95_secondary_colonial_states_missions.txt")
        tpf = read("missions/jxp_b_114_transpacific_federation_missions.txt")
        self.assertEqual(35, len(re.findall(r"^\s*jxp_b_94_mission_\w+\s*=", nya, re.MULTILINE)))
        for prefix, expected in (("hkk", 28), ("njf", 30), ("oia", 28)):
            entries = re.findall(rf"^\s*(jxp_b_95_{prefix}_\w+)\s*=", secondary, re.MULTILINE)
            self.assertEqual(expected, len([key for key in entries if not key.endswith("_missions")]))
        entries = re.findall(r"^\s*(jxp_b_114_tpf_\w+)\s*=", tpf, re.MULTILINE)
        self.assertEqual(35, len([key for key in entries if not key.endswith("_missions")]))
        self.assertEqual(5, tpf.count("potential = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_federation_dissolved } }"))
        self.assertNotIn("tag = TPF", nya)
        for payload in (nya, secondary, tpf):
            for positions in self._series_position_lists(payload):
                self.assertEqual(positions, sorted(positions))
                self.assertTrue(all(right - left <= 2 for left, right in zip(positions, positions[1:])), positions)

    def test_state_events_decisions_reforms_and_crisis_loops_meet_minima(self) -> None:
        events = "\n".join(
            read(path)
            for path in (
                "events/jxp_b_94_new_yamato_events.txt",
                "events/jxp_b_95_secondary_colonial_states_events.txt",
                "events/jxp_b_98_transpacific_state_events.txt",
                "events/jxp_b_110_colonial_state_depth_events.txt",
                "events/jxp_b_111_secondary_state_depth_events.txt",
                "events/jxp_b_114_transpacific_depth_events.txt",
            )
        )
        expectations = {
            r"jxp_new_yamato\.\d+": 20,
            r"jxp_secondary_colonies\.(?:[1-9]|1[0-6])": 16,
            r"jxp_secondary_colonies\.1(?:0[1-9]|1[0-8])": 18,
            r"jxp_secondary_colonies\.2(?:0[1-9]|1[0-6])": 16,
            r"jxp_transpacific_state\.\d+": 22,
        }
        for pattern, expected in expectations.items():
            found = set(re.findall(rf"^\s*id\s*=\s*({pattern})\s*$", events, re.MULTILINE))
            self.assertEqual(expected, len(found), pattern)

        decisions = read("decisions/jxp_b_111_colonial_state_actions.txt")
        for prefix, expected in (("nya", 10), ("hkk", 5), ("njf", 7), ("oia", 5), ("tpf", 10)):
            self.assertEqual(expected, len(re.findall(rf"^\s*jxp_b_111_{prefix}_action_\d+\s*=", decisions, re.MULTILINE)))
        shared = read("decisions/jxp_b_110_colonial_state_decisions.txt")
        self.assertEqual(10, len(re.findall(r"^\s*jxp_b_110_(?!open_state_guide)\w+\s*=", shared, re.MULTILINE)))

        reforms = read("common/government_reforms/jxp_b_98_transpacific_state_reform.txt")
        self.assertEqual(4, len(re.findall(r"^jxp_b_(?:two_ocean|114_)\w+_reform\s*=", reforms, re.MULTILINE)))
        registry = read("common/governments/00_governments.txt")
        for reform in (
            "jxp_b_two_ocean_federation_reform",
            "jxp_b_114_old_world_directed_federation_reform",
            "jxp_b_114_overseas_rights_confederation_reform",
            "jxp_b_114_two_ocean_directorate_reform",
        ):
            self.assertIn(reform, registry)
        bounded = "\n".join(
            read(path)
            for path in (
                "common/government_reforms/jxp_b_94_new_yamato_reforms.txt",
                "common/government_reforms/jxp_b_95_secondary_colonial_reforms.txt",
                "common/government_reforms/jxp_b_98_transpacific_state_reform.txt",
                "common/event_modifiers/jxp_b_95_secondary_states_modifiers.txt",
            )
        )
        for forbidden in ("discipline =", "mercenary_discipline =", "administrative_efficiency =", "core_creation =", "aggressive_expansion_impact ="):
            self.assertNotIn(forbidden, bounded)
        crisis = read("events/jxp_b_111_colonial_state_crisis_events.txt")
        on_action = read("common/on_actions/jxp_b_110_colonial_state_crisis_on_actions.txt")
        self.assertIn("jxp_colonial_state_crisis.50", on_action)
        self.assertEqual(5, len(re.findall(r"id = jxp_colonial_state_crisis\.(?:1|11|21|31|41)\s*$", crisis, re.MULTILINE)))
        self.assertEqual(10, crisis.count("_crisis_pulse_scheduled country_event ="))
        self.assertFalse((MOD_ROOT / "common/disasters/jxp_b_110_colonial_state_disasters.txt").exists())

        migration = read("events/jxp_b_110_colonial_migration_events.txt")
        registry_event = read("events/jxp_a_97_colonial_registry_events.txt")
        registry_effect = read("common/scripted_effects/jxp_a_97_colonial_registry_effects.txt")
        finalizer = read("common/scripted_effects/jxp_b_102_overseas_program_effects.txt")
        self.assertIn("jxp_b_110_colonial_depth_migration_pending", migration)
        self.assertIn("jxp_b_110_colonial_depth_postcondition_trigger = yes", migration)
        self.assertIn("jxp_b_102_finalize_overseas_program_startup_migration_effect = yes", migration)
        self.assertIn("jxp_b_102_finalize_overseas_program_startup_migration_effect = yes", registry_event)
        self.assertNotIn("jxp_b_114_old_world_directed_federation_reform", registry_effect)
        self.assertIn("remove_government_reform = jxp_b_two_ocean_federation_reform", finalizer)

    def test_metropole_legacy_is_single_recorded_before_route_clear(self) -> None:
        depth = read("common/scripted_effects/jxp_b_110_colonial_depth_effects.txt")
        for legacy in (
            "undecided", "closed_country", "open_country", "buddhist", "kirishitan", "confucian", "imperial",
            "reformed", "sultanate", "ikko", "wakou", "toyotomi", "commercial_council",
        ):
            self.assertIn(f"jxp_b_legacy_{legacy}", depth)
        for effect in ("jxp_b_record_metropole_legacy", "jxp_b_clear_duplicate_metropole_legacies", "jxp_b_reconcile_metropole_legacy"):
            self.assertIn(f"{effect} = {{", depth)
        for path, clear in (
            ("common/scripted_effects/jxp_b_94_new_yamato_effects.txt", "jxp_b_94_clear_japanese_home_paths_effect"),
            ("common/scripted_effects/jxp_b_95_secondary_states_effects.txt", "jxp_b_95_clear_japanese_home_paths_effect"),
        ):
            payload = read(path)
            self.assertLess(payload.index("jxp_b_record_metropole_legacy = yes"), payload.index(f"{clear} = yes"))

    def test_generated_content_parses_and_localisation_is_synced(self) -> None:
        for relative in (
            "missions/jxp_b_94_new_yamato_missions.txt", "missions/jxp_b_95_secondary_colonial_states_missions.txt",
            "missions/jxp_b_114_transpacific_federation_missions.txt", "events/jxp_b_110_colonial_state_depth_events.txt",
            "events/jxp_b_111_secondary_state_depth_events.txt", "events/jxp_b_114_transpacific_depth_events.txt",
            "events/jxp_b_110_colonial_state_guide_events.txt", "events/jxp_b_111_colonial_state_crisis_events.txt",
            "events/jxp_b_110_colonial_migration_events.txt",
            "decisions/jxp_b_110_colonial_state_decisions.txt", "decisions/jxp_b_111_colonial_state_actions.txt",
            "common/government_reforms/jxp_b_98_transpacific_state_reform.txt",
            "common/on_actions/jxp_b_110_colonial_state_crisis_on_actions.txt", "common/scripted_effects/jxp_b_110_colonial_depth_effects.txt",
        ):
            parse_text(read(relative))
        source = read("localisation_source/jxp_b_110_colonial_state_depth_l_english_utf8_source.yml")
        active_path = MOD_ROOT / "localisation/jxp_b_110_colonial_state_depth_l_english.yml"
        active = active_path.read_text(encoding="utf-8-sig")
        key_pattern = re.compile(r"^\s+([^#\s][^:]*):\d+", re.MULTILINE)
        self.assertEqual(set(key_pattern.findall(source)), set(key_pattern.findall(active)))
        self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertIsNone(re.search(r"[\u3400-\u9fff]", active))


if __name__ == "__main__":
    unittest.main()
