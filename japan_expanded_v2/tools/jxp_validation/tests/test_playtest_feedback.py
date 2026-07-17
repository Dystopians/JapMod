from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import unittest

from jxp_validation.build_consolidated_country_ideas import top_level_blocks
from jxp_validation.clausewitz import Object, Scalar, first_object, parse_text


MAIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = MAIN_ROOT.parent
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"


def _text(root: Path, relative: str, encoding: str = "utf-8-sig") -> str:
    return (root / relative).read_text(encoding=encoding)


def _top_level_block(text: str, key: str) -> str:
    for block_key, start, end in top_level_blocks(text):
        if block_key == key:
            return text[start:end]
    raise AssertionError(f"Missing top-level block: {key}")


def _clausewitz_shape(value: Object | Scalar | None) -> object:
    if value is None:
        return None
    if isinstance(value, Scalar):
        return ("scalar", value.text, value.quoted)
    return tuple(
        (
            entry.key,
            entry.operator,
            _clausewitz_shape(entry.value),
        )
        for entry in value.entries
    )


class PlaytestFeedbackRegressionTests(unittest.TestCase):
    def test_imperial_edict_is_costly_one_time_and_nonpermanent(self) -> None:
        decision = _text(MAIN_ROOT, "decisions/jxp_polity_decisions.txt")
        interaction = _text(
            MAIN_ROOT,
            "common/government_mechanics/jxp_japanese_polity_mechanic.txt",
        )
        required_contract = (
            "is_at_war = no",
            "stability = 1",
            "prestige = 25",
            "num_of_cities = 10",
            "dip_power = 200",
            "treasury = 500",
            "check_variable = { which = jxp_imperial_sanction value = 70 }",
            "NOT = { has_country_flag = jxp_imperial_edict_claims_received }",
            "add_dip_power = -200",
            "add_treasury = -500",
            "add_stability = -1",
            "add_prestige = -25",
            "jxp_subtract_imperial_sanction_50_effect = yes",
            "set_country_flag = jxp_imperial_edict_claims_received",
            "duration = 3650",
        )
        for needle in required_contract:
            with self.subTest(needle=needle):
                self.assertIn(needle, decision)
                self.assertIn(needle, interaction)

        decision_root = parse_text(decision).root
        decision_contract = first_object(
            first_object(decision_root, "country_decisions"),
            "jxp_decision_request_imperial_edict",
        )
        mechanic_root = first_object(
            parse_text(interaction).root,
            "jxp_japanese_polity_mechanic",
        )
        interaction_contract = first_object(
            first_object(mechanic_root, "interactions"),
            "jxp_gov_request_imperial_edict",
        )
        self.assertEqual(
            _clausewitz_shape(first_object(decision_contract, "allow")),
            _clausewitz_shape(first_object(interaction_contract, "trigger")),
        )
        self.assertEqual(
            _clausewitz_shape(first_object(decision_contract, "effect")),
            _clausewitz_shape(first_object(interaction_contract, "effect")),
        )
        self.assertIn("ai_will_do = {\n\t\t\tfactor = 0", decision)
        self.assertIn("ai_chance = {\n\t\t\t\tfactor = 0", interaction)

        effects = _text(
            MAIN_ROOT,
            "common/scripted_effects/jxp_scripted_effects.txt",
        )
        claims_effect = effects.split(
            "jxp_grant_japan_region_claims_effect = {",
            1,
        )[1].split("jxp_grant_ikko_heartland_claims_effect = {", 1)[0]
        self.assertIn("add_claim = ROOT", claims_effect)
        self.assertNotIn("add_permanent_claim = ROOT", claims_effect)
        localisation = _text(
            MAIN_ROOT,
            "localisation_source/jxp_l_english_utf8_source.yml",
        )
        self.assertIn("普通宣称", localisation)
        self.assertIn("会依通常规则随时间消逝", localisation)
        self.assertNotIn("十年内赋予日本诸国的普通宣称", localisation)

    def test_ikko_and_wokou_formations_use_historical_gates(self) -> None:
        triggers = _text(
            MAIN_ROOT,
            "common/scripted_triggers/jxp_scripted_triggers.txt",
        )
        for needle in (
            "jxp_can_form_ikko_commonwealth_trigger = {",
            "culture_group = japanese_g",
            "jxp_is_daimyo_stage_trigger = yes",
            "NOT = { has_reform = shogunate }",
            "is_year = 1470",
            "NOT = { is_year = 1603 }",
            "has_disaster = jxp_ikko_rising",
            "jxp_ikko_historical_heartland_trigger = yes",
            "num_of_cities = 8",
            "jxp_can_form_wokou_confederacy_trigger = {",
            "is_year = 1500",
            "NOT = { is_year = 1650 }",
            "jxp_wokou_historical_waters_trigger = yes",
            "num_of_ports = 5",
            "dip_tech = 7",
            "jxp_oceanic_opening_at_least_50 = yes",
            "has_country_flag = jxp_wokou_brokers_funded",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, triggers)

        decisions = _text(
            MAIN_ROOT,
            "decisions/jxp_10_popular_maritime_decisions.txt",
        )
        self.assertGreaterEqual(decisions.count("ai_will_do = { factor = 0 }"), 4)
        self.assertIn("jxp_can_form_ikko_commonwealth_trigger = yes", decisions)
        self.assertIn("jxp_can_form_wokou_confederacy_trigger = yes", decisions)

        realm_events = _text(MAIN_ROOT, "events/jxp_realm_events.txt")
        self.assertIn(
            'name = "jxp_realm.1.j"\n\t\tai_chance = { factor = 0 }',
            realm_events,
        )
        self.assertIn(
            'name = "jxp_realm.1.k"\n\t\tai_chance = { factor = 0 }',
            realm_events,
        )

        effects = _text(
            MAIN_ROOT,
            "common/scripted_effects/jxp_scripted_effects.txt",
        )
        self.assertIn("change_religion = jodo_shinshu", effects)
        ijp_history = _text(
            MAIN_ROOT,
            "tools/jxp_name_builder/source/history/countries/"
            "IJP - Ikko Commonwealth.txt",
        )
        self.assertIn("religion = jodo_shinshu", ijp_history)

        map_effects = _text(
            MAP_ROOT,
            "common/scripted_effects/jxp_map_effects.txt",
        )
        self.assertIn("province_id = 4953", map_effects)
        self.assertIn(
            "set_province_flag = jxp_map_compat_ikko_formable_heartland",
            map_effects,
        )

    def test_daimyo_reforms_persist_as_japanese_institutional_options(self) -> None:
        reforms = _text(
            MAIN_ROOT,
            "common/government_reforms/jxp_83_daimyo_stage_reforms.txt",
        )
        governments = _text(MAIN_ROOT, "common/governments/00_governments.txt")
        effects = _text(
            MAIN_ROOT,
            "common/scripted_effects/jxp_scripted_effects.txt",
        )
        reform_ids = (
            "jxp_reform_daimyo_kokujin_oaths",
            "jxp_reform_daimyo_bunkoku_law",
            "jxp_reform_daimyo_kachu_hyojoshu",
        )
        for reform_id in reform_ids:
            with self.subTest(reform_id=reform_id):
                self.assertEqual(1, reforms.count(f"{reform_id} = {{"))
                self.assertIn(
                    "jxp_uses_japanese_government_reform_track_trigger = yes",
                    reforms,
                )
                self.assertEqual(1, governments.count(reform_id))
                self.assertIn(
                    f"remove_government_reform = {reform_id}",
                    effects,
                )
        self.assertIn("jxp_reconcile_daimyo_stage_reforms_effect = {", effects)
        self.assertIn(
            "NOT = { jxp_uses_japanese_government_reform_track_trigger = yes }",
            effects,
        )

    def test_shogunate_war_is_named_joraku_and_uses_selective_cta(self) -> None:
        subjects = _text(
            MAIN_ROOT,
            "common/subject_types/00_subject_types.txt",
        )
        contract = (
            "# JXP_DAIMYO_SELECTIVE_CALL_TO_ARMS_V1\n"
            "\tjoins_overlords_wars = no\n"
            "\tcan_be_co_belligerented = yes\n"
            "\tmust_accept_cta_from_overlord = yes\n"
            "\tcan_gain_favors = yes\n"
            "\tfavors_cost_to_join_offensive_wars = 20\n"
            "\tfavors_cost_to_join_defensive_wars = 10\n"
            "\topinion_cost_to_join_offensive_wars = 40\n"
            "\topinion_cost_to_join_defensive_wars = 20"
        )
        self.assertIn(contract, subjects)

        localisation = _text(
            MAIN_ROOT,
            "localisation_source/jxp_83_playtest_feedback_l_english_utf8_source.yml",
        )
        self.assertIn('cb_daimyo_annex:0 "上洛"', localisation)
        self.assertIn('cb_independent_daimyo_annex:0 "上洛"', localisation)
        self.assertIn("付出人情或关系代价逐一召集", localisation)
        self.assertNotIn("愿意", localisation)

    def test_oda_and_toyotomi_ideas_have_distinct_s_tier_strength(self) -> None:
        oda_source = _text(
            MAIN_ROOT,
            "tools/jxp_validation/idea_sources/"
            "00_basic_z1_jxp_15_daimyo_ideas.txt",
        )
        toy_source = _text(
            MAIN_ROOT,
            "tools/jxp_validation/idea_sources/jxp_70_toyotomi_ideas.txt",
        )
        registry = _text(MAIN_ROOT, "common/ideas/00_country_ideas.txt")
        source_blocks = {
            "ODA_ideas": _top_level_block(oda_source, "ODA_ideas"),
            "TOY_ideas": _top_level_block(toy_source, "TOY_ideas"),
        }
        registry_blocks = {
            key: _top_level_block(registry, key)
            for key in source_blocks
        }
        expected_profiles = {
            "ODA_ideas": (
                "siege_ability = 0.10",
                "province_warscore_cost = -0.10",
                "core_creation = -0.10",
                "army_tradition = 0.5",
                "artillery_power = 0.10",
                "global_institution_spread = 0.10",
                "global_manpower_modifier = 0.15",
            ),
            "TOY_ideas": (
                "administrative_efficiency = 0.05",
                "development_cost = -0.10",
                "state_maintenance_modifier = -0.05",
                "global_unrest = -2",
                "years_of_nationalism = -3",
                "improve_relation_modifier = 0.15",
                "governing_capacity_modifier = 0.15",
                "advisor_cost = -0.10",
                "global_trade_power = 0.15",
                "trade_efficiency = 0.10",
            ),
        }
        for group, needles in expected_profiles.items():
            for needle in needles:
                with self.subTest(group=group, needle=needle):
                    self.assertIn(needle, source_blocks[group])
                    self.assertIn(needle, registry_blocks[group])

        self.assertIn("artillery_power = 0.10", source_blocks["ODA_ideas"])
        self.assertNotIn("artillery_power", source_blocks["TOY_ideas"])
        self.assertIn(
            "administrative_efficiency = 0.05",
            source_blocks["TOY_ideas"],
        )
        self.assertNotIn(
            "administrative_efficiency",
            source_blocks["ODA_ideas"],
        )

    def test_common_surnames_reach_all_three_japanese_cultures(self) -> None:
        payload = json.loads(
            _text(
                MAIN_ROOT,
                "tools/jxp_name_builder/japanese_common_surnames.json",
                encoding="utf-8",
            )
        )
        surnames = payload["surnames"]
        cultures_path = MAIN_ROOT / "common/cultures/00_cultures.txt"
        cultures = cultures_path.read_bytes()
        encoder_path = (
            REPO_ROOT
            / "skills"
            / "eu4-modding"
            / "scripts"
            / "encode_eu4_special_gameplay.py"
        )
        spec = importlib.util.spec_from_file_location(
            "_test_gameplay_name_decoder",
            encoder_path,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec is not None else None)
        assert spec is not None and spec.loader is not None
        encoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(encoder)
        marker = b"# JXP_COMMON_JAPANESE_SURNAMES_V1"
        sections = cultures.split(marker)[1:]
        self.assertEqual(3, len(sections))
        for section in sections:
            closing = section.find(b"\n\t\t}")
            self.assertGreater(closing, 0)
            readable = encoder.decode_gameplay_bytes(marker + section[:closing])
            for surname in surnames:
                with self.subTest(surname=surname):
                    self.assertIn(surname, readable)


if __name__ == "__main__":
    unittest.main()
