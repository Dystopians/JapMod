from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import importlib.util
from pathlib import Path
import re
import unittest

from jxp_validation.clausewitz import Object, Scalar, bare_scalars, first_object, parse_text
from jxp_validation.final_states import _evaluate_final_reform_predicate
from jxp_validation.missions import BASE_PROFILES, Profile, evaluate_potential


MAIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = MAIN_ROOT.parent
TRACK_TRIGGER_FILE = MAIN_ROOT / "common/scripted_triggers/jxp_04_daimyo_triggers.txt"
LEGACY_REFORM_FILE = MAIN_ROOT / "common/government_reforms/jxp_83_daimyo_stage_reforms.txt"
TRACK_REFORM_FILE = MAIN_ROOT / "common/government_reforms/jxp_84_japanese_government_track.txt"
ROUTE_REFORM_FILE = MAIN_ROOT / "common/government_reforms/jxp_18_route_reforms_extra.txt"
FINAL_REFORM_FILE = MAIN_ROOT / "common/government_reforms/jxp_80_final_state_political_reforms.txt"
FOUNDER_REFORM_FILE = MAIN_ROOT / "common/government_reforms/jxp_28_founder_house_reforms.txt"
FINAL_TRIGGER_FILE = MAIN_ROOT / "common/scripted_triggers/jxp_79_final_state_triggers.txt"
GOVERNMENT_FILE = MAIN_ROOT / "common/governments/00_governments.txt"
MONARCHY_REFORM_FILE = (
    MAIN_ROOT / "common/government_reforms/01_government_reforms_monarchies.txt"
)
REFORM_ICON_GFX_FILE = MAIN_ROOT / "interface/jxp_governmentreformicons.gfx"
REFORM_ICON_DIRECTORY = MAIN_ROOT / "gfx/interface/government_reform_icons"
SOURCE_LOC_FILES = (
    MAIN_ROOT / "localisation_source/jxp_83_playtest_feedback_l_english_utf8_source.yml",
    MAIN_ROOT / "localisation_source/jxp_84_japanese_government_track_l_english_utf8_source.yml",
)
ACTIVE_LOC_FILES = (
    MAIN_ROOT / "localisation/jxp_83_playtest_feedback_l_english.yml",
    MAIN_ROOT / "localisation/jxp_84_japanese_government_track_l_english.yml",
)

REPLACED_VANILLA_BY_TIER = {
    "hereditary_vs_nobility": {
        "enforce_privileges_reform",
        "quash_noble_power_reform",
        "enforce_trader_privileges_reform",
        "grant_noble_castle_rights_reform",
        "maintain_nobles_status_quo_reform",
        "grant_military_command_reform",
        "grant_nobles_electorate_reform",
        "blackmail_nobility_reform",
    },
    "bureaucracy": {
        "centralize_reform",
        "centralize_empire_reform",
        "decentralize_reform",
        "expand_imperial_court_reform",
        "limit_imperial_court_reform",
        "regional_council_reform",
        "representation_of_the_crown_reform",
        "penal_colonies_reform",
    },
    "state_and_religion": {
        "curtail_clergy_power_reform",
        "secure_clergy_power_reform",
        "maintain_clergy_balance_of_power_reform",
        "separate_clergy_from_state_affairs_reform",
    },
    "military_doctrines": {
        "organized_military_staff_reform",
        "military_engineering_reform",
        "defensive_stance_reform",
        "sustained_discipline_reform",
        "cavalry_warfare_reform",
        "mercenary_leadership_reform",
        "amphibious_specialization_reform",
        "royal_marines_reform",
        "maritime_military_reform",
        "professional_navy_reform",
        "doppelsoldner_reform",
        "ashigaru_reform",
        "early_bushido_code_reform",
    },
    "deliberative_assembly": {
        "parliamentary_reform",
        "royal_decree_reform",
        "aristocratic_court_reform",
        "general_estates_reform",
        "states_general_reform",
        "become_a_republic_reform",
        "install_theocratic_government_reform",
    },
    "growth_of_administration": {
        "clergy_in_administration_reform",
        "of_noble_bearing_reform",
        "meritocratic_focus_reform",
        "dyanstic_administration_reform",
        "superiority_of_the_state_reform",
        "administration_of_the_parliament_reform",
        "strengthened_parliament_reform",
    },
    "economical_matters": {
        "empower_the_burghers_reform",
        "curtail_the_burghers_reform",
        "mercantilistic_approach_reform",
        "free_trade_reform",
        "embrace_the_economic_theory_reform",
        "war_economy_reform",
        "new_world_exploitation_reform",
        "lockean_proviso_reform",
    },
    "legitimation_of_power": {
        "machiavellianistic_rule_reform",
        "six_livres_reform",
        "two_treatises_reform",
        "the_leviathan_reform",
        "the_social_contract_reform",
    },
    "absolute_rule_vs_constitutional": {
        "letat_cest_moi_reform",
        "regional_representation_reform",
        "peoples_kingdom_reform",
        "deified_monarchy_reform",
    },
    "separation_of_power": {
        "political_absolutism_reform",
        "legislative_houses_reform",
        "presidential_monarchy_reform",
    },
}

RETAINED_SPECIAL_BUDGET = {
    "bureaucracy": 1,
    "state_and_religion": 2,
    "military_doctrines": 1,
    "deliberative_assembly": 1,
    "economical_matters": 1,
}


def _top_objects(path: Path) -> dict[str, Object]:
    root = parse_text(path.read_text(encoding="utf-8-sig")).root
    return {
        entry.key: entry.value
        for entry in root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }


def _contains_assignment(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    for entry in obj.entries:
        if (
            entry.key == key
            and isinstance(entry.value, Scalar)
            and entry.value.text == value
        ):
            return True
        if isinstance(entry.value, Object) and _contains_assignment(
            entry.value, key, value
        ):
            return True
    return False


def _assignment_values(obj: Object | None, key: str) -> tuple[str, ...]:
    if obj is None:
        return ()
    values: list[str] = []
    for entry in obj.entries:
        if entry.key == key and isinstance(entry.value, Scalar):
            values.append(entry.value.text)
        if isinstance(entry.value, Object):
            values.extend(_assignment_values(entry.value, key))
    return tuple(values)


def _registration_levels() -> dict[str, str]:
    root = parse_text(GOVERNMENT_FILE.read_text(encoding="utf-8-sig")).root
    monarchy = first_object(root, "monarchy")
    levels = first_object(monarchy, "reform_levels")
    result: dict[str, str] = {}
    assert levels is not None
    for level_entry in levels.entries:
        if level_entry.key is None or not isinstance(level_entry.value, Object):
            continue
        reforms = first_object(level_entry.value, "reforms")
        if reforms is None:
            continue
        for scalar in bare_scalars(reforms):
            result[scalar.text] = level_entry.key
    return result


def _final_trigger_objects() -> dict[str, list[Object]]:
    result: dict[str, list[Object]] = defaultdict(list)
    for key, body in _top_objects(FINAL_TRIGGER_FILE).items():
        result[key].append(body)
    return result


def _localisation_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    pattern = re.compile(r'^\s*([A-Za-z0-9_.-]+):\d+\s+"(.*)"\s*$')
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(line)
        if match:
            entries[match.group(1)] = match.group(2)
    return entries


class JapaneseGovernmentTrackTests(unittest.TestCase):
    def test_track_reforms_have_unique_registered_icons(self) -> None:
        definitions = {
            **_top_objects(LEGACY_REFORM_FILE),
            **_top_objects(TRACK_REFORM_FILE),
        }
        self.assertEqual(39, len(definitions))
        icons: dict[str, str] = {}
        for reform_id, body in definitions.items():
            values = _assignment_values(body, "icon")
            with self.subTest(reform_id=reform_id):
                self.assertEqual(1, len(values))
            icons[reform_id] = values[0]

        self.assertEqual(39, len(set(icons.values())))
        registry = REFORM_ICON_GFX_FILE.read_text(encoding="utf-8-sig")
        self.assertNotRegex(registry, r"(?m)^\s*\+")
        for reform_id, icon in icons.items():
            with self.subTest(reform_icon=reform_id):
                self.assertIn(f'government_reform_{icon}', registry)
                self.assertIn(
                    f'government_reform_icons//{icon}.dds',
                    registry,
                )
                self.assertTrue((REFORM_ICON_DIRECTORY / f"{icon}.dds").is_file())

    def test_core_japanese_identity_reforms_preserve_the_selected_tier(self) -> None:
        definitions = _top_objects(MONARCHY_REFORM_FILE)
        registrations = _registration_levels()
        for reform_id in ("daimyo", "indep_daimyo", "shogunate"):
            with self.subTest(reform_id=reform_id):
                self.assertEqual(
                    "feudalism_vs_autocracy", registrations[reform_id]
                )
                self.assertTrue(
                    _contains_assignment(
                        first_object(definitions[reform_id], "potential"),
                        "has_reform",
                        reform_id,
                    )
                )
        self.assertTrue(
            _contains_assignment(
                first_object(definitions["daimyo"], "potential"),
                "is_subject_of_type",
                "daimyo_vassal",
            )
        )

    def test_strict_track_membership_does_not_use_a_moved_capital(self) -> None:
        trigger = _top_objects(TRACK_TRIGGER_FILE)[
            "jxp_uses_japanese_government_reform_track_trigger"
        ]
        self.assertIsNotNone(first_object(trigger, "ROOT"))
        trigger_text = TRACK_TRIGGER_FILE.read_text(encoding="utf-8-sig").split(
            "jxp_uses_japanese_government_reform_track_trigger = {", 1
        )[1].split("jxp_has_final_state_political_profile_trigger = {", 1)[0]
        self.assertNotIn("capital_scope", trigger_text)
        self.assertNotIn("jxp_is_japanese_polity_trigger", trigger_text)

        positive_profiles = [
            Profile(
                "Japanese culture monarchy",
                "FRA",
                "catholic",
                "christian",
                japanese_polity=False,
            ),
            *(
                Profile(
                    f"foreign {reform} carrier",
                    "FRA",
                    "catholic",
                    "christian",
                    reforms=frozenset({reform}),
                    culture_group="french",
                    japanese_polity=False,
                )
                for reform in ("daimyo", "indep_daimyo", "shogunate")
            ),
            *(
                Profile(
                    f"exact tag {tag}",
                    tag,
                    "catholic",
                    "christian",
                    culture_group="french",
                    japanese_polity=False,
                )
                for tag in ("JAP", "TOY", "KJP", "CJP", "EJP", "RFJ", "SJP", "IJP", "WAK")
            ),
            Profile(
                "committed route state",
                "FRA",
                "catholic",
                "christian",
                flags=frozenset({"jxp_path_open_trade"}),
                culture_group="french",
                japanese_polity=False,
            ),
        ]
        for profile in positive_profiles:
            values, unknown = evaluate_potential(trigger, profile)
            with self.subTest(profile=profile.name):
                self.assertEqual((), unknown)
                self.assertEqual(frozenset({True}), values)

        moved_capital_foreigner = Profile(
            "foreign monarchy with an Asian capital",
            "FRA",
            "catholic",
            "christian",
            culture_group="french",
            japanese_polity=False,
            capital_continent="asia",
        )
        values, unknown = evaluate_potential(trigger, moved_capital_foreigner)
        self.assertEqual((), unknown)
        self.assertEqual(frozenset({False}), values)

    def test_final_identity_triggers_are_anchored_to_country_root(self) -> None:
        definitions = _top_objects(FINAL_TRIGGER_FILE)
        for route in (
            "uncommitted",
            "sakoku",
            "open",
            "kirishitan",
            "confucian",
            "imperial",
            "reformed",
            "kaikyo",
            "ikko",
            "wokou",
        ):
            trigger_id = f"jxp_final_state_{route}_trigger"
            with self.subTest(trigger_id=trigger_id):
                self.assertIsNotNone(first_object(definitions[trigger_id], "ROOT"))

    def test_vanilla_replacements_are_exact_late_track_overrides(self) -> None:
        override_files = sorted(
            (MAIN_ROOT / "common/government_reforms").glob(
                "zz_jxp_84_tier*_vanilla_overrides.txt"
            )
        )
        self.assertEqual(10, len(override_files))
        definitions: dict[str, Object] = {}
        for path in override_files:
            self.assertTrue(path.name.startswith("zz_"))
            for reform_id, body in _top_objects(path).items():
                self.assertNotIn(reform_id, definitions)
                definitions[reform_id] = body

        expected = set().union(*REPLACED_VANILLA_BY_TIER.values())
        self.assertEqual(expected, set(definitions))
        japanese = Profile("Japanese", "ODA", "shinto", "eastern")
        for reform_id, body in definitions.items():
            self.assertEqual(
                1,
                sum(1 for entry in body.entries if entry.key == "potential"),
                reform_id,
            )
            potential = first_object(body, "potential")
            with self.subTest(reform_id=reform_id):
                self.assertTrue(
                    _contains_assignment(
                        potential,
                        "jxp_uses_japanese_government_reform_track_trigger",
                        "yes",
                    )
                )
                values, _unknown = evaluate_potential(potential, japanese)
                self.assertEqual(frozenset({False}), values)

        foreign = Profile(
            "French monarchy",
            "FRA",
            "catholic",
            "christian",
            culture_group="french",
            japanese_polity=False,
        )
        for reform_id in (
            "machiavellianistic_rule_reform",
            "six_livres_reform",
            "two_treatises_reform",
            "the_leviathan_reform",
            "the_social_contract_reform",
            "letat_cest_moi_reform",
            "regional_representation_reform",
            "peoples_kingdom_reform",
            "deified_monarchy_reform",
            "presidential_monarchy_reform",
        ):
            values, _unknown = evaluate_potential(
                first_object(definitions[reform_id], "potential"), foreign
            )
            with self.subTest(foreign_reform=reform_id):
                self.assertIn(True, values)

    def test_candidate_matrix_stays_at_or_below_eight(self) -> None:
        registrations = _registration_levels()
        track_definitions = {
            **_top_objects(LEGACY_REFORM_FILE),
            **_top_objects(TRACK_REFORM_FILE),
        }
        self.assertEqual(39, len(track_definitions))
        western_book_icons = {
            "machiavellianism",
            "six_livres",
            "two_treaties",
            "leviathan",
            "the_social_contract",
            "letat_cest_moi",
            "parliament_hall",
        }
        for reform_id, body in track_definitions.items():
            with self.subTest(reform_icon=reform_id):
                self.assertTrue(_assignment_values(body, "icon"))
                self.assertTrue(
                    set(_assignment_values(body, "icon")).isdisjoint(
                        western_book_icons
                    )
                )
        route_definitions = _top_objects(ROUTE_REFORM_FILE)
        final_definitions = _top_objects(FINAL_REFORM_FILE)
        founder_tiers = {
            registrations[reform_id]
            for reform_id in _top_objects(FOUNDER_REFORM_FILE)
        }
        final_trigger_objects = _final_trigger_objects()

        profiles = [
            Profile(
                "ordinary daimyo",
                "ODA",
                "shinto",
                "eastern",
                reforms=frozenset({"daimyo"}),
                daimyo_stage=True,
            ),
            Profile(
                "independent daimyo",
                "ODA",
                "shinto",
                "eastern",
                reforms=frozenset({"indep_daimyo"}),
                daimyo_stage=True,
            ),
            Profile(
                "shogunate",
                "ASK",
                "shinto",
                "eastern",
                reforms=frozenset({"shogunate"}),
                daimyo_stage=True,
            ),
            Profile(
                "Japanese Buddhist daimyo",
                "ODA",
                "mahayana",
                "eastern",
                reforms=frozenset({"daimyo"}),
                daimyo_stage=True,
            ),
            *(
                profile
                for profile in BASE_PROFILES
                if not profile.daimyo_stage
            ),
            Profile(
                "TOY sakoku",
                "TOY",
                "shinto",
                "eastern",
                flags=frozenset({"jxp_path_sakoku"}),
            ),
            Profile(
                "TOY open",
                "TOY",
                "shinto",
                "eastern",
                flags=frozenset({"jxp_path_open_trade"}),
            ),
        ]
        idea_sets = (
            frozenset(),
            frozenset({"economic_ideas"}),
            frozenset({"infrastructure_ideas"}),
            frozenset({"economic_ideas", "infrastructure_ideas"}),
            frozenset({"exploration_ideas"}),
            frozenset({"expansion_ideas"}),
            frozenset({"economic_ideas", "infrastructure_ideas", "exploration_ideas"}),
        )
        all_levels = tuple(REPLACED_VANILLA_BY_TIER)
        for base_profile in profiles:
            for ideas in idea_sets:
                profile = replace(base_profile, full_idea_groups=ideas)
                candidates_by_tier: dict[str, set[str]] = defaultdict(set)
                for reform_id, body in track_definitions.items():
                    values, unknown = evaluate_potential(
                        first_object(body, "potential"), profile
                    )
                    self.assertEqual((), unknown, (profile.name, reform_id))
                    if True in values:
                        candidates_by_tier[registrations[reform_id]].add(reform_id)

                for reform_id, body in {
                    **route_definitions,
                    **final_definitions,
                }.items():
                    values, unknown = _evaluate_final_reform_predicate(
                        first_object(body, "potential"),
                        profile,
                        final_trigger_objects,
                    )
                    self.assertEqual((), unknown, (profile.name, reform_id))
                    if True in values:
                        candidates_by_tier[registrations[reform_id]].add(reform_id)

                for level in all_levels:
                    conservative_count = len(candidates_by_tier[level])
                    if level in founder_tiers:
                        conservative_count += 1
                    conservative_count += RETAINED_SPECIAL_BUDGET.get(level, 0)
                    with self.subTest(
                        profile=profile.name,
                        ideas=sorted(ideas),
                        level=level,
                    ):
                        self.assertLessEqual(conservative_count, 8)

    def test_final_profiles_replace_tier_ten_fallbacks(self) -> None:
        definitions = _top_objects(TRACK_REFORM_FILE)
        final_profile_trigger = _top_objects(TRACK_TRIGGER_FILE)[
            "jxp_has_final_state_political_profile_trigger"
        ]
        self.assertTrue(
            _contains_assignment(
                final_profile_trigger,
                "jxp_a_96_buddhist_exact_route_trigger",
                "yes",
            )
        )
        self.assertTrue(
            _contains_assignment(
                final_profile_trigger,
                "jxp_a_105_profile_commercial_council_trigger",
                "yes",
            )
        )
        fallback_ids = {
            "jxp_reform_japanese_unitary_investiture",
            "jxp_reform_japanese_domain_federation",
            "jxp_reform_japanese_benevolent_government",
            "jxp_reform_japanese_divine_law",
        }
        final_profiles = tuple(
            profile
            for profile in BASE_PROFILES
            if not profile.daimyo_stage and profile.tag != "TOY"
        )
        for profile in final_profiles:
            for reform_id in fallback_ids:
                values, unknown = evaluate_potential(
                    first_object(definitions[reform_id], "potential"), profile
                )
                with self.subTest(profile=profile.name, reform_id=reform_id):
                    self.assertEqual((), unknown)
                    self.assertEqual(frozenset({False}), values)

        for profile in (
            Profile(
                "ordinary daimyo",
                "ODA",
                "shinto",
                "eastern",
                reforms=frozenset({"daimyo"}),
                daimyo_stage=True,
            ),
            Profile("TOY", "TOY", "shinto", "eastern"),
        ):
            visible = {
                reform_id
                for reform_id in fallback_ids
                if True
                in evaluate_potential(
                    first_object(definitions[reform_id], "potential"), profile
                )[0]
            }
            self.assertEqual(fallback_ids, visible)

    def test_legacy_reforms_survive_unification_until_track_exit(self) -> None:
        reforms = LEGACY_REFORM_FILE.read_text(encoding="utf-8-sig")
        self.assertNotIn("jxp_is_daimyo_stage_trigger = yes", reforms)
        self.assertEqual(
            6,
            reforms.count(
                "jxp_uses_japanese_government_reform_track_trigger = yes"
            ),
        )
        effects = (
            MAIN_ROOT / "common/scripted_effects/jxp_scripted_effects.txt"
        ).read_text(encoding="utf-8-sig")
        reconcile = effects.split(
            "jxp_reconcile_daimyo_stage_reforms_effect = {", 1
        )[1].split("jxp_clear_route_reforms_effect = {", 1)[0]
        self.assertIn(
            "NOT = { jxp_uses_japanese_government_reform_track_trigger = yes }",
            reconcile,
        )
        route_clear = effects.split("jxp_clear_route_reforms_effect = {", 1)[1].split(
            "jxp_remove_legacy_autogranted_route_reforms_effect = {", 1
        )[0]
        self.assertNotIn("jxp_clear_daimyo_stage_reforms_effect = yes", route_clear)

        reform_ids = set(_top_objects(LEGACY_REFORM_FILE)) | set(
            _top_objects(TRACK_REFORM_FILE)
        )
        trigger_inventory = set(
            _assignment_values(
                _top_objects(TRACK_TRIGGER_FILE)[
                    "jxp_has_japanese_government_track_reform_trigger"
                ],
                "has_reform",
            )
        )
        effect_objects = _top_objects(
            MAIN_ROOT / "common/scripted_effects/jxp_scripted_effects.txt"
        )
        clear_inventory = set(
            _assignment_values(
                effect_objects["jxp_clear_japanese_government_track_reforms_effect"],
                "remove_government_reform",
            )
        ) | set(
            _assignment_values(
                effect_objects["jxp_clear_daimyo_stage_reforms_effect"],
                "remove_government_reform",
            )
        )
        self.assertEqual(reform_ids, trigger_inventory)
        self.assertEqual(reform_ids, clear_inventory)

        on_actions = (
            MAIN_ROOT / "common/on_actions/jxp_60_mission_runtime_on_actions.txt"
        ).read_text(encoding="utf-8-sig")
        self.assertIn(
            "jxp_has_japanese_government_track_reform_trigger = yes",
            on_actions,
        )

    def test_localisation_is_complete_and_pipeline_exact(self) -> None:
        encoder_path = (
            REPO_ROOT
            / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py"
        )
        spec = importlib.util.spec_from_file_location(
            "_jxp_track_localisation_encoder", encoder_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec is not None else None)
        assert spec is not None and spec.loader is not None
        encoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(encoder)

        combined_entries: dict[str, str] = {}
        for source, active in zip(SOURCE_LOC_FILES, ACTIVE_LOC_FILES, strict=True):
            source_text = source.read_text(encoding="utf-8-sig")
            expected = encoder.escape_text(source_text).encode("utf-8-sig")
            active_bytes = active.read_bytes()
            self.assertEqual(expected, active_bytes, active)
            self.assertNotIn(b"?", active_bytes, active)
            combined_entries.update(_localisation_entries(source))

        reform_ids = set(_top_objects(LEGACY_REFORM_FILE)) | set(
            _top_objects(TRACK_REFORM_FILE)
        )
        self.assertEqual(39, len(reform_ids))
        reform_definitions = {
            **_top_objects(LEGACY_REFORM_FILE),
            **_top_objects(TRACK_REFORM_FILE),
        }
        for reform_id in reform_ids:
            with self.subTest(reform_id=reform_id):
                self.assertIn(reform_id, combined_entries)
                self.assertIn(f"{reform_id}_desc", combined_entries)
                self.assertRegex(combined_entries[reform_id], r"[\u3400-\u9fff]")
                self.assertRegex(
                    combined_entries[f"{reform_id}_desc"], r"[\u3400-\u9fff]"
                )
                self.assertNotEqual(reform_id, combined_entries[reform_id])
                tooltip_keys = set(
                    _assignment_values(
                        first_object(reform_definitions[reform_id], "trigger"),
                        "tooltip",
                    )
                )
                self.assertTrue(
                    tooltip_keys
                    & {
                        "jxp_japanese_reform_track_requirement_tt",
                        "jxp_japanese_tier_ten_fallback_requirement_tt",
                    }
                )

        for tooltip_key in (
            "jxp_japanese_reform_track_requirement_tt",
            "jxp_japanese_overseas_reform_requirement_tt",
            "jxp_japanese_tier_ten_fallback_requirement_tt",
        ):
            self.assertIn(tooltip_key, combined_entries)
            self.assertRegex(combined_entries[tooltip_key], r"[\u3400-\u9fff]")

        prose = "\n".join(combined_entries.values()).lower()
        for forbidden in (
            "trigger",
            "modifier",
            "variable",
            "设置变量",
            "复制原版改革",
        ):
            self.assertNotIn(forbidden, prose)


if __name__ == "__main__":
    unittest.main()
