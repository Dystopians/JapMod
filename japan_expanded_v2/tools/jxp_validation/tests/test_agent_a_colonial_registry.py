from __future__ import annotations

from pathlib import Path
import re
import unittest

from jxp_validation.build_consolidated_country_ideas import (
    SOURCE_FILENAMES,
    top_level_blocks,
)
from jxp_validation.clausewitz import parse_text


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
TAGS = ("NYA", "HKK", "NJF", "OIA", "TPF")
COUNTRY_PATHS = {
    "NYA": "NYA - New Yamato.txt",
    "HKK": "HKK - Northern Star Sea Realm.txt",
    "NJF": "NJF - Southern Japan Town Federation.txt",
    "OIA": "OIA - Oceanic Island Alliance.txt",
    "TPF": "TPF - Two Ocean Federation.txt",
}
MONARCHY_REFORMS = {
    "jxp_b_94_oceanic_monarchy_reform",
    "jxp_b_95_hkk_frontier_bakufu_reform",
    "jxp_b_95_njf_southern_military_diaspora_reform",
    "jxp_b_95_oia_island_kingdom_reform",
}
REPUBLIC_REFORMS = {
    "jxp_b_94_federal_assembly_reform",
    "jxp_b_94_frontier_military_republic_reform",
    "jxp_b_94_merchant_commonwealth_reform",
    "jxp_b_95_hkk_company_republic_reform",
    "jxp_b_95_hkk_northern_peoples_assembly_reform",
    "jxp_b_95_njf_japan_town_league_reform",
    "jxp_b_95_njf_red_seal_company_state_reform",
    "jxp_b_95_njf_plural_port_federation_reform",
    "jxp_b_95_oia_harbor_assembly_reform",
    "jxp_b_95_oia_oceanic_naval_league_reform",
    "jxp_b_two_ocean_federation_reform",
}
INTERFACE_FLAGS = (
    "jxp_iface_b_nya_needs_mission_refresh",
    "jxp_iface_b_nya_needs_idea_refresh",
    "jxp_iface_b_nya_needs_government_registry",
    "jxp_iface_b_secondary_needs_mission_refresh",
    "jxp_iface_b_secondary_needs_idea_refresh",
    "jxp_iface_b_secondary_needs_government_registry",
    "jxp_iface_b_tpf_needs_mission_refresh",
    "jxp_iface_b_tpf_needs_idea_refresh",
    "jxp_iface_b_tpf_needs_government_registry",
)


def _read(relative: str, *, map_mod: bool = False) -> str:
    root = MAP_ROOT if map_mod else MAIN_ROOT
    return (root / relative).read_text(encoding="utf-8-sig")


def _block(text: str, key: str) -> str:
    for candidate, start, end in top_level_blocks(text):
        if candidate == key:
            return text[start:end]
    raise AssertionError(f"missing top-level Clausewitz block: {key}")


class ColonialCentralRegistryTests(unittest.TestCase):
    def test_five_tags_have_colored_definitions_and_landless_history_shells(self) -> None:
        tag_registry = _read("common/country_tags/jxp_tags.txt")
        for tag, filename in COUNTRY_PATHS.items():
            with self.subTest(tag=tag):
                self.assertEqual(
                    1,
                    len(re.findall(rf"^{tag}\s*=", tag_registry, re.MULTILINE)),
                )
                self.assertIn(f'"countries/{filename}"', tag_registry)
                country = _read(
                    f"tools/jxp_name_builder/source/common/countries/{filename}"
                )
                history = _read(f"history/countries/{filename}")
                self.assertTrue((MAIN_ROOT / "common/countries" / filename).is_file())
                parse_text(
                    country,
                    MAIN_ROOT
                    / "tools/jxp_name_builder/source/common/countries"
                    / filename,
                )
                parse_text(history, MAIN_ROOT / "history/countries" / filename)
                self.assertEqual(1, len(re.findall(r"^color\s*=", country, re.MULTILINE)))
                self.assertIn("random_nation_chance = 0", country)
                for forbidden in (
                    "capital =",
                    "add_core",
                    "add_permanent_claim",
                    "owner =",
                    "owned_by =",
                ):
                    self.assertNotIn(forbidden, history)

    def test_five_seven_idea_groups_are_generated_once_into_the_only_registry(self) -> None:
        self.assertIn("jxp_b_colonial_state_ideas.txt", SOURCE_FILENAMES)
        source = _read("tools/jxp_validation/idea_sources/jxp_b_colonial_state_ideas.txt")
        runtime = _read("common/ideas/00_country_ideas.txt")
        self.assertNotIn("global_settler_increase", source)
        self.assertIn("global_colonial_growth = 10", source)
        self.assertEqual(
            {f"{tag}_ideas" for tag in TAGS},
            {key for key, _start, _end in top_level_blocks(source)},
        )
        for tag in TAGS:
            with self.subTest(tag=tag):
                block = _block(source, f"{tag}_ideas")
                children = {
                    key
                    for key in re.findall(
                        r"^\t([A-Za-z0-9_]+)\s*=",
                        block,
                        re.MULTILINE,
                    )
                    if key not in {"start", "bonus", "trigger", "free"}
                }
                self.assertEqual(7, len(children))
                self.assertEqual(
                    1,
                    len(
                        re.findall(
                            rf"^{tag}_ideas\s*=\s*\{{",
                            runtime,
                            re.MULTILINE,
                        )
                    ),
                )
        idea_files = tuple((MAIN_ROOT / "common/ideas").glob("*.txt"))
        self.assertEqual(["00_country_ideas.txt"], [path.name for path in idea_files])

    def test_fifteen_reforms_are_registered_once_in_the_correct_tier_one(self) -> None:
        governments = _read("common/governments/00_governments.txt")
        monarchy = _block(governments, "monarchy")
        republic = _block(governments, "republic")
        for reform in MONARCHY_REFORMS:
            with self.subTest(reform=reform):
                self.assertEqual(1, governments.count(reform))
                self.assertIn(reform, monarchy)
                self.assertNotIn(reform, republic)
        for reform in REPUBLIC_REFORMS:
            with self.subTest(reform=reform):
                self.assertEqual(1, governments.count(reform))
                self.assertIn(reform, republic)
                self.assertNotIn(reform, monarchy)

    def test_refresh_handshakes_converge_and_clear_after_their_registry_action(self) -> None:
        effects = _read("common/scripted_effects/jxp_a_97_colonial_registry_effects.txt")
        event = _read("events/jxp_a_97_colonial_registry_events.txt")
        parse_text(effects, MAIN_ROOT / "common/scripted_effects/jxp_a_97_colonial_registry_effects.txt")
        parse_text(event, MAIN_ROOT / "events/jxp_a_97_colonial_registry_events.txt")
        for flag in INTERFACE_FLAGS:
            self.assertIn(f"has_country_flag = {flag}", event)
            self.assertIn(f"clr_country_flag = {flag}", effects)
        self.assertLess(
            effects.index("jxp_clear_all_route_flags_effect = yes"),
            effects.index("jxp_refresh_route_missions_effect = yes"),
        )
        self.assertLess(
            effects.index("country_event = { id = jxp_idea_registry.1 }"),
            effects.index("clr_country_flag = jxp_iface_b_nya_needs_idea_refresh"),
        )
        self.assertIn("change_government = republic", effects)
        self.assertIn(
            "add_government_reform = jxp_b_two_ocean_federation_reform",
            effects,
        )
        self.assertLess(
            effects.index("jxp_b_94_clear_foundational_reforms_effect = yes"),
            effects.index("change_government = republic"),
        )
        self.assertLess(
            effects.index("jxp_b_95_clear_secondary_reforms_effect = yes"),
            effects.index("add_government_reform = jxp_b_two_ocean_federation_reform"),
        )
        self.assertIn("mean_time_to_happen = { days = 1 }", event)

    def test_overseas_migration_uses_existing_country_scoped_startup_hook(
        self,
    ) -> None:
        on_actions = _read(
            "common/on_actions/jxp_a_97_colonial_registry_on_actions.txt"
        )
        event = _read("events/jxp_a_97_colonial_registry_events.txt")
        parse_text(
            on_actions,
            MAIN_ROOT
            / "common/on_actions/jxp_a_97_colonial_registry_on_actions.txt",
        )
        parse_text(
            event,
            MAIN_ROOT / "events/jxp_a_97_colonial_registry_events.txt",
        )
        self.assertIn("on_startup = {", on_actions)
        self.assertIn("events = { jxp_a_colonial_registry.1 }", on_actions)
        self.assertIn(
            "jxp_b_102_needs_startup_migration_trigger = yes",
            event,
        )
        migration_call = (
            "jxp_b_102_overseas_program_startup_migration_effect = yes"
        )
        registry_call = "jxp_a_consume_colonial_registry_interfaces_effect = yes"
        finalize_call = (
            "jxp_b_102_finalize_overseas_program_startup_migration_effect = yes"
        )
        self.assertEqual(1, event.count(migration_call))
        self.assertEqual(1, event.count(finalize_call))
        self.assertLess(event.index(migration_call), event.index(registry_call))
        self.assertLess(event.index(registry_call), event.index(finalize_call))
        for forbidden in ("on_monthly_pulse", "every_country", "every_province"):
            self.assertNotIn(forbidden, on_actions + event)

    def test_colonial_successors_are_managed_for_ideas_but_excluded_from_home_routes(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_scripted_triggers.txt")
        ideas = _read("common/scripted_triggers/jxp_80_national_idea_triggers.txt")
        colonial = _block(triggers, "jxp_is_colonial_successor_tag_trigger")
        polity = _block(triggers, "jxp_is_japanese_polity_trigger")
        routes = _block(triggers, "jxp_has_any_route_trigger")
        custom_missions = _block(triggers, "jxp_use_custom_missions_trigger")
        expected = _block(ideas, "jxp_has_expected_managed_national_ideas_trigger")
        managed = _block(ideas, "jxp_uses_managed_national_ideas_trigger")
        route_ideas = _block(ideas, "jxp_uses_route_national_ideas_trigger")
        for tag in TAGS:
            self.assertIn(f"tag = {tag}", colonial)
            self.assertIn(f"tag = {tag}", managed)
            self.assertIn(f"tag = {tag} has_idea_group = {tag}_ideas", expected)
            self.assertNotIn(f"tag = {tag}", route_ideas)
        exclusion = "NOT = { jxp_is_colonial_successor_tag_trigger = yes }"
        self.assertIn(exclusion, polity)
        self.assertIn(exclusion, routes)
        self.assertIn(exclusion, custom_missions)

    def test_map_initialization_marks_matsumae_and_tsugaru_as_frontier_houses(self) -> None:
        effects = _read("common/scripted_effects/jxp_map_effects.txt", map_mod=True)
        initialize = _block(effects, "jxp_map_initialize_effect")
        self.assertIn("tag = MTS", initialize)
        self.assertIn("tag = TGR", initialize)
        self.assertIn("jxp_a_mark_house_frontier_ready_effect = yes", initialize)


if __name__ == "__main__":
    unittest.main()
