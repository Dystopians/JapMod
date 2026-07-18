from __future__ import annotations

from pathlib import Path
import re
import unittest


MOD_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


class ColonialExpansionContractTests(unittest.TestCase):
    def test_b1_tracks_exactly_three_bounded_society_variables(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_91_colonial_society_effects.txt")
        variables = set(re.findall(r"which\s*=\s*(jxp_b_(?:colonial_identity|metropole_control|local_compact))", effects))
        self.assertEqual(
            {"jxp_b_colonial_identity", "jxp_b_metropole_control", "jxp_b_local_compact"},
            variables,
        )
        for variable in variables:
            self.assertIn(f"which = {variable} value = 0", effects)
            self.assertIn(f"which = {variable} value = 100", effects)

    def test_b1_uses_one_self_scheduled_annual_pulse(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_91_colonial_society_effects.txt")
        events = _read("events/jxp_b_91_colonial_society_events.txt")
        self.assertIn("country_event = { id = jxp_colonial_society.2 days = 365 }", effects)
        self.assertIn("set_country_flag = jxp_b_colonial_pulse_scheduled", effects)
        self.assertIn("clr_country_flag = jxp_b_colonial_pulse_scheduled", events)
        self.assertNotIn("mean_time_to_happen", events)

    def test_b1_migrates_stable_overseas_milestones_idempotently(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_91_colonial_society_effects.txt")
        self.assertIn("NOT = { has_country_flag = jxp_b_colonial_society_initialized }", effects)
        for flag in (
            "jxp_pacific_charter_enacted",
            "jxp_new_world_japan_towns_done",
            "jxp_manila_nagasaki_route_seen",
            "jxp_alaska_survey_seen",
            "jxp_california_anchorages_seen",
        ):
            self.assertIn(flag, effects)

    def test_b2_has_five_exclusive_charters_and_costly_reform(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_91_colonial_charter_effects.txt")
        events = _read("events/jxp_b_91_colonial_charter_events.txt")
        decisions = _read("decisions/jxp_b_91_colonial_charter_decisions.txt")
        charters = (
            "red_seal_town",
            "military_settlement",
            "faith_community",
            "free_port",
            "naval_station",
        )
        for charter in charters:
            self.assertIn(f"clr_country_flag = jxp_b_charter_{charter}", effects)
            self.assertIn(f"set_country_flag = jxp_b_charter_{charter}", effects)
            self.assertIn(f"jxp_b_91_charter_{charter}", effects)
        for suffix in "abcde":
            self.assertIn(f'jxp_colonial_charter.1.{suffix}', events)
        self.assertIn("duration = 7300", effects)
        self.assertIn("add_adm_power = -100", decisions)
        self.assertIn("add_dip_power = -100", decisions)
        self.assertIn("add_treasury = -250", decisions)

    def test_b2_charter_history_blocks_repeat_opening_rewards(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_91_colonial_charter_effects.txt")
        self.assertEqual(5, effects.count("NOT = { has_country_flag = jxp_b_charter_history_"))
        self.assertEqual(5, effects.count("set_country_flag = jxp_b_charter_history_"))

    def test_b9_uses_verified_fixed_tag_switch_and_honest_dynamic_fallback(self) -> None:
        events = _read("events/jxp_b_95_colonial_switch_events.txt")
        localisation = _read("localisation_source/jxp_b_95_colonial_switch_l_english_utf8_source.yml")
        for tag in ("NYA", "HKK", "NJF", "OIA"):
            self.assertEqual(1, events.count(f"switch_tag = {tag}"))
        self.assertNotIn("play_as", events)
        self.assertNotIn("every_subject_country", events)
        self.assertEqual(4, events.count("add_treasury = 100"))
        self.assertEqual(4, events.count("set_country_flag = jxp_b_colonial_switch_startup_received"))
        self.assertIn("释放殖民地并扮演", localisation)

    def test_b10_independence_crisis_has_ten_stages_and_metropole_reply(self) -> None:
        events = _read("events/jxp_b_96_colonial_independence_events.txt")
        event_ids = set(re.findall(r"^\s*id\s*=\s*jxp_colonial_independence\.(\d+)\s*$", events, re.MULTILINE))
        self.assertTrue({str(value) for value in range(1, 11)}.issubset(event_ids))
        self.assertIn("20", event_ids)
        self.assertIn("overlord = { country_event = { id = jxp_colonial_independence.20 } }", events)
        self.assertIn("grant_independence = yes", events)
        self.assertNotIn("mean_time_to_happen", events)

    def test_b10_independence_war_excludes_land_grab_and_has_bounded_outcomes(self) -> None:
        cb = _read("common/cb_types/jxp_b_96_colonial_independence_cb.txt")
        wargoal = _read("common/wargoal_types/jxp_b_96_colonial_independence_wargoal.txt")
        treaties = _read("common/peace_treaties/jxp_b_96_colonial_independence_treaties.txt")
        self.assertIn("independence = yes", cb)
        self.assertIn("valid_for_subject = yes", cb)
        self.assertNotIn("po_demand_provinces", wargoal)
        for option in (
            "po_independence",
            "po_jxp_b_colonial_compact",
            "po_jxp_b_trade_independence",
            "po_jxp_b_restore_metropole_control",
        ):
            self.assertIn(option, wargoal)
        self.assertEqual(3, len(re.findall(r"^po_jxp_b_\w+\s*=", treaties, re.MULTILINE)))

    def test_b10_builtin_independence_is_reconciled_on_bounded_peace_callbacks(self) -> None:
        on_actions = _read("common/on_actions/jxp_b_117_external_reconcile_on_actions.txt")
        triggers = _read("common/scripted_triggers/jxp_b_117_external_reconcile_triggers.txt")
        effects = _read("common/scripted_effects/jxp_b_117_external_reconcile_effects.txt")
        independence_effects = _read("common/scripted_effects/jxp_b_96_colonial_independence_effects.txt")
        for callback in ("on_peace_actor", "on_peace_recipient", "on_war_ended"):
            self.assertIn(f"{callback} =", on_actions)
        self.assertIn("has_country_flag = jxp_b_96_independence_declared", triggers)
        self.assertIn("is_subject = no", triggers)
        self.assertIn("NOT = { has_country_flag = jxp_iface_colonial_independence }", triggers)
        self.assertIn("jxp_b_96_mark_full_independence_effect = yes", effects)
        marker = independence_effects.split("jxp_b_96_mark_full_independence_effect = {", 1)[1].split(
            "jxp_b_96_restore_metropole_control_effect", 1
        )[0]
        self.assertIn("NOT = { has_country_flag = jxp_iface_colonial_independence }", marker)
        self.assertEqual(1, marker.count("jxp_b_91_add_identity_10_effect = yes"))
        self.assertNotIn("every_country", on_actions + triggers + effects)
        self.assertNotIn("every_subject_country", on_actions + triggers + effects)

    def test_b6_shared_library_has_thirty_six_visible_weighted_events(self) -> None:
        events = _read("events/jxp_b_93_colonial_society_events.txt")
        pulse = _read("events/jxp_b_91_colonial_society_events.txt")
        event_ids = re.findall(r"^\s*id\s*=\s*jxp_colonial_society\.(\d+)\s*$", events, re.MULTILINE)
        self.assertEqual(["90"] + [str(value) for value in range(101, 137)], event_ids)
        self.assertEqual(72, events.count("ai_chance ="))
        self.assertNotIn("mean_time_to_happen", events)
        self.assertIn("country_event = { id = jxp_colonial_society.90 days = 1 }", pulse)
        self.assertIn("duration = 730", pulse)

    def test_b6_local_society_has_cooperative_as_well_as_coercive_paths(self) -> None:
        source = _read("localisation_source/jxp_b_93_colonial_society_events_l_english_utf8_source.yml")
        for concept in ("条约", "公民", "双语", "共同防御", "地方代表", "共同节期"):
            self.assertIn(concept, source)

    def test_b3_to_b5_have_six_bounded_regional_decisions(self) -> None:
        decisions = _read("decisions/jxp_b_92_regional_colonial_decisions.txt")
        events = _read("events/jxp_b_92_regional_colonial_events.txt")
        self.assertEqual(6, len(re.findall(r"^\s*jxp_b_92_decision_\w+\s*=", decisions, re.MULTILINE)))
        self.assertEqual(10, len(re.findall(r"^\s*id\s*=\s*jxp_b_regional_colonial\.\d+\s*$", events, re.MULTILINE)))
        self.assertEqual(6, decisions.count("ai_will_do ="))
        self.assertNotIn("mean_time_to_happen", events)
        self.assertIn("is_bankrupt = yes", decisions)

    def test_b3_southeast_asian_japan_town_requires_host_consent(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_92_regional_colonial_triggers.txt")
        events = _read("events/jxp_b_92_regional_colonial_events.txt")
        self.assertIn("jxp_b_92_south_seas_host_candidate_trigger", triggers)
        self.assertIn("NOT = { jxp_is_japanese_polity_trigger = yes }", triggers)
        self.assertIn("has_opinion = { who = ROOT value = 75 }", triggers)
        self.assertIn("jxp_b_92_host_grant_charter_tt", events)
        self.assertIn("jxp_b_92_host_refuse_charter_tt", events)

    def test_b5_normal_and_random_new_world_paths_are_both_live(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_92_regional_colonial_triggers.txt")
        decisions = _read("decisions/jxp_b_92_regional_colonial_decisions.txt")
        self.assertGreaterEqual(triggers.count("is_random_new_world = no"), 2)
        self.assertGreaterEqual(triggers.count("is_random_new_world = yes"), 2)
        self.assertGreaterEqual(triggers.count("continent = new_world"), 2)
        self.assertIn("jxp_b_92_begin_normal_west_coast_machiya_effect", decisions)
        self.assertIn("jxp_b_92_begin_rnw_machiya_effect", decisions)

    def test_b11_end_metropole_rule_only_releases_filtered_overseas_subjects(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_97_end_metropole_rule_triggers.txt")
        effects = _read("common/scripted_effects/jxp_b_97_end_metropole_rule_effects.txt")
        self.assertIn("jxp_b_96_colonial_origin_trigger = yes", triggers)
        self.assertIn("continent = new_world", triggers)
        self.assertIn("region = oceanea_region", triggers)
        self.assertIn("every_subject_country", effects)
        self.assertIn("grant_independence = yes", effects)
        self.assertNotIn("create_subject", effects)
        self.assertNotIn("remove_core", effects)
        self.assertIn("remove_claim = ROOT", effects)
        self.assertNotIn("every_province", effects)
        self.assertIn("every_owned_province", effects)
        for exclusion in ("tag = KOR", "tag = RYU", "has_reform = daimyo", "has_reform = indep_daimyo"):
            self.assertIn(exclusion, triggers)

    def test_b11_peace_blocks_recharter_for_forty_years_without_land_demands(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_97_end_metropole_rule_effects.txt")
        wargoal = _read("common/wargoal_types/jxp_b_97_end_metropole_rule_wargoal.txt")
        regional = _read("common/scripted_triggers/jxp_b_92_regional_colonial_triggers.txt")
        self.assertIn("duration = 14600", effects)
        self.assertNotIn("po_demand_provinces", wargoal)
        self.assertIn("po_jxp_b_end_metropole_colonial_rule", wargoal)
        self.assertIn("NOT = { has_country_modifier = jxp_b_97_overseas_rights_revoked }", regional)

    def test_b11_historical_defeat_flag_does_not_outlive_timed_recharter_block(self) -> None:
        society = _read("common/scripted_triggers/jxp_b_91_colonial_society_triggers.txt")
        cleanup = _read("common/scripted_effects/jxp_b_91_colonial_society_effects.txt")
        self.assertIn("NOT = { has_country_modifier = jxp_b_97_overseas_rights_revoked }", society)
        self.assertNotIn("NOT = { has_country_flag = jxp_iface_metropole_new_world_rule_broken }", society)
        self.assertIn("clr_country_flag = jxp_iface_overseas_charter_ready", cleanup)

    def test_b12_eastward_revolution_has_four_non_annexation_outcomes(self) -> None:
        wargoal = _read("common/wargoal_types/jxp_b_98_eastward_revolution_wargoal.txt")
        treaties = _read("common/peace_treaties/jxp_b_98_eastward_revolution_treaties.txt")
        options = (
            "po_jxp_b_liberate_overseas",
            "po_jxp_b_old_world_member",
            "po_jxp_b_two_ocean_federation",
            "po_jxp_b_eastward_capital",
        )
        for option in options:
            self.assertIn(option, wargoal)
        self.assertNotIn("po_demand_provinces", wargoal)
        self.assertNotIn("add_core", treaties)
        self.assertNotIn("every_owned_province", treaties)
        self.assertIn("1020 = { cede_province = ROOT }", treaties)

    def test_b12_two_ocean_federation_has_recurring_real_costs(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_98_transpacific_state_effects.txt")
        events = _read("events/jxp_b_98_transpacific_state_events.txt")
        modifiers = _read("common/event_modifiers/jxp_b_98_transpacific_state_modifiers.txt")
        self.assertIn("change_tag = TPF", effects)
        self.assertIn("country_event = { id = jxp_transpacific_state.10 days = 1095 }", effects)
        self.assertIn("clr_country_flag = jxp_b_98_federal_council_scheduled", events)
        self.assertIn("governing_capacity_modifier = -0.15", modifiers)
        self.assertIn("naval_maintenance_modifier = 0.15", modifiers)
        self.assertGreaterEqual(events.count("add_treasury = -"), 3)

    def test_b7_new_yamato_has_full_five_column_mission_identity(self) -> None:
        missions = _read("missions/jxp_b_94_new_yamato_missions.txt")
        events = _read("events/jxp_b_94_new_yamato_events.txt") + _read("events/jxp_b_110_colonial_state_depth_events.txt")
        reforms = _read("common/government_reforms/jxp_b_94_new_yamato_reforms.txt")
        self.assertEqual(5, len(re.findall(r"^jxp_b_94_nya_\w+_missions\s*=", missions, re.MULTILINE)))
        self.assertEqual(35, len(re.findall(r"^\s*jxp_b_94_mission_\w+\s*=", missions, re.MULTILINE)))
        self.assertEqual(20, len(re.findall(r"^\s*id\s*=\s*jxp_new_yamato\.\d+\s*$", events, re.MULTILINE)))
        self.assertEqual(4, len(re.findall(r"^jxp_b_94_\w+_reform\s*=", reforms, re.MULTILINE)))
        self.assertEqual(5, missions.count("potential = { tag = NYA }"))
        self.assertNotIn("tag = TPF", missions)

    def test_b7_new_yamato_formation_is_bounded_and_refreshes_transactionally(self) -> None:
        triggers = _read("common/scripted_triggers/jxp_b_94_new_yamato_triggers.txt")
        effects = _read("common/scripted_effects/jxp_b_94_new_yamato_effects.txt")
        payload = triggers + effects + _read("missions/jxp_b_94_new_yamato_missions.txt")
        self.assertIn("total_development = 120", triggers)
        self.assertIn("continent = new_world", triggers)
        self.assertIn("change_tag = NYA", effects)
        self.assertLess(effects.index("change_tag = NYA"), effects.index("jxp_refresh_route_missions_effect = yes"))
        self.assertLess(effects.index("jxp_refresh_route_missions_effect = yes"), effects.index("on_change_tag_effect = yes"))
        self.assertNotIn("add_core", payload)
        self.assertNotIn("add_permanent_claim", payload)

    def test_b7_new_yamato_idea_source_has_seven_ideas(self) -> None:
        ideas = _read("tools/jxp_validation/idea_sources/jxp_b_colonial_state_ideas.txt")
        modifiers = _read("common/event_modifiers/jxp_b_94_new_yamato_modifiers.txt")
        nya_block = ideas.split("HKK_ideas", 1)[0]
        idea_names = re.findall(r"^\t(nya_\w+)\s*=", nya_block, re.MULTILINE)
        self.assertEqual(7, len(idea_names))
        self.assertIn("global_colonial_growth = 10", nya_block)
        self.assertNotIn("global_settler_increase", nya_block)
        self.assertIn("global_colonial_growth = 10", modifiers)
        self.assertNotIn("global_settler_increase", modifiers)

    def test_b8_secondary_states_retain_their_foundation_events_and_gain_full_depth(self) -> None:
        missions = _read("missions/jxp_b_95_secondary_colonial_states_missions.txt")
        events = _read("events/jxp_b_95_secondary_colonial_states_events.txt")
        for tag, event_start, expected_count in (("hkk", 1, 28), ("njf", 101, 30), ("oia", 201, 28)):
            self.assertEqual(
                expected_count,
                len(re.findall(rf"^\tjxp_b_95_{tag}_\w+\s*=", missions, re.MULTILINE)),
            )
            expected = {str(value) for value in range(event_start, event_start + 8)}
            event_ids = set(re.findall(r"^\s*id\s*=\s*jxp_secondary_colonies\.(\d+)\s*$", events, re.MULTILINE))
            self.assertTrue(expected.issubset(event_ids))

    def test_b8_secondary_state_formation_is_bounded_and_refreshes_missions(self) -> None:
        effects = _read("common/scripted_effects/jxp_b_95_secondary_states_effects.txt")
        triggers = _read("common/scripted_triggers/jxp_b_95_secondary_states_triggers.txt")
        payload = effects + triggers + _read("missions/jxp_b_95_secondary_colonial_states_missions.txt")
        for tag in ("HKK", "NJF", "OIA"):
            marker = f"change_tag = {tag}"
            start = effects.index(marker)
            refresh = effects.index("jxp_refresh_route_missions_effect = yes", start)
            callback = effects.index("on_change_tag_effect = yes", refresh)
            self.assertLess(start, refresh)
            self.assertLess(refresh, callback)
        self.assertIn("is_random_new_world = yes", triggers)
        self.assertIn("continent = new_world", triggers)
        self.assertNotIn("add_core", payload)
        self.assertNotIn("add_permanent_claim", payload)

    def test_b8_secondary_reforms_and_ideas_are_complete(self) -> None:
        reforms = _read("common/government_reforms/jxp_b_95_secondary_colonial_reforms.txt")
        ideas = _read("tools/jxp_validation/idea_sources/jxp_b_colonial_state_ideas.txt")
        self.assertEqual(10, len(re.findall(r"^jxp_b_95_\w+_reform\s*=", reforms, re.MULTILINE)))
        for tag, prefix in (("HKK", "hkk"), ("NJF", "njf"), ("OIA", "oia")):
            block = ideas.split(f"{tag}_ideas =", 1)[1]
            next_header = re.search(r"^\w+_ideas\s*=", block, re.MULTILINE)
            if next_header:
                block = block[: next_header.start()]
            self.assertEqual(7, len(re.findall(rf"^\t{prefix}_\w+\s*=", block, re.MULTILINE)))

    def test_colonial_state_flags_are_engine_ready_tga(self) -> None:
        for tag in ("NYA", "HKK", "NJF", "OIA", "TPF"):
            data = (MOD_ROOT / "gfx" / "flags" / f"{tag}.tga").read_bytes()
            self.assertEqual(49196, len(data))
            self.assertEqual(2, data[2], f"{tag} must be an uncompressed true-color TGA")
            self.assertEqual(128, int.from_bytes(data[12:14], "little"))
            self.assertEqual(128, int.from_bytes(data[14:16], "little"))
            self.assertEqual(24, data[16])

    def test_b12_transpacific_state_has_independent_missions_and_seven_ideas(self) -> None:
        nya_missions = _read("missions/jxp_b_94_new_yamato_missions.txt")
        missions = _read("missions/jxp_b_114_transpacific_federation_missions.txt")
        ideas = _read("tools/jxp_validation/idea_sources/jxp_b_colonial_state_ideas.txt")
        self.assertNotIn("tag = TPF", nya_missions)
        self.assertEqual(5, missions.count("potential = { tag = TPF NOT = { has_country_flag = jxp_b_tpf_federation_dissolved } }"))
        self.assertEqual(35, len(re.findall(r"^\s*jxp_b_114_tpf_\w+\s*=", missions, re.MULTILINE)) - 5)
        tpf_block = ideas.split("TPF_ideas =", 1)[1]
        self.assertEqual(7, len(re.findall(r"^\t(tpf_\w+)\s*=", tpf_block, re.MULTILINE)))


if __name__ == "__main__":
    unittest.main()
