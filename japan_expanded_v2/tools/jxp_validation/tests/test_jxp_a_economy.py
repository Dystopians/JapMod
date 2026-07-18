from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

from jxp_validation.build_consolidated_country_ideas import top_level_blocks
from jxp_validation.clausewitz import parse_text


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
BUILDER_ROOT = MAIN_ROOT / "tools" / "jxp_a_socioeconomic_builder"
sys.path.insert(0, str(BUILDER_ROOT))
try:
    import build_economy as builder
finally:
    sys.path.remove(str(BUILDER_ROOT))


def _block(text: str, key: str) -> str:
    for candidate, start, end in top_level_blocks(text):
        if candidate == key:
            return text[start:end]
    raise AssertionError(f"missing top-level Clausewitz block: {key}")


def _event_block(text: str, namespace: str, event_id: int) -> str:
    marker = f"\tid = {namespace}.{event_id}\n"
    if marker not in text:
        raise AssertionError(f"missing event {namespace}.{event_id}")
    return text.split(marker, 1)[1].split("\n}\n", 1)[0]


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class AgentAEconomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        builder.validate_model()
        cls.outputs = builder.render_outputs()
        cls.gameplay = "\n".join(
            payload
            for path, payload in cls.outputs.items()
            if isinstance(payload, str)
            and path.suffix == ".txt"
            and "localisation" not in path.parts
        )

    def test_generated_outputs_are_current_deterministic_and_parseable(self) -> None:
        self.assertEqual(14, len(self.outputs))
        self.assertEqual(self.outputs, builder.render_outputs())
        for path, expected in self.outputs.items():
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                actual = (
                    path.read_bytes()
                    if isinstance(expected, bytes)
                    else path.read_text(encoding="utf-8")
                )
                self.assertEqual(expected, actual)
                if isinstance(expected, str) and path.suffix == ".txt":
                    parse_text(expected, path)

    def test_market_has_four_monotonic_exclusive_stages_and_exact_public_effects(self) -> None:
        effects = builder.render_effects()
        triggers = builder.render_triggers()
        decisions = builder.render_decisions()
        for stage in range(1, 5):
            key = f"jxp_a_set_market_stage_{stage}"
            block = _block(effects, key)
            restore = _block(effects, f"jxp_a_restore_market_stage_{stage}_effect")
            self.assertEqual(1, effects.count(f"\n{key} = {{"))
            self.assertIn(
                f"set_country_flag = jxp_a_market_stage_{stage}", block
            )
            self.assertIn(
                f"set_country_flag = jxp_iface_a_market_stage_{stage}", block
            )
            self.assertIn(
                f"has_country_flag = jxp_a_market_stage_{stage}_rewarded",
                block,
            )
            for lower in range(1, stage):
                self.assertNotIn(
                    f"set_country_flag = jxp_a_market_stage_{lower}", block
                )
            if stage < 4:
                self.assertIn(
                    f"has_country_flag = jxp_a_market_stage_{stage + 1}",
                    block,
                )
            self.assertIn(
                f"set_country_flag = jxp_a_market_stage_{stage}_rewarded",
                restore,
            )
            support_key = (
                f"jxp_a_market_stage_{stage}_two_of_three_support_trigger"
            )
            support = _block(triggers, support_key)
            self.assertEqual(3, support.count("\n\t\tAND = {"))
            for requirement in builder.MARKET_STAGE_SUPPORT[stage - 1]:
                self.assertEqual(2, support.count(f"{requirement} = yes"))
            decision = decisions.split(
                f"\tjxp_a_advance_market_stage_{stage} = {{", 1
            )[1].split("\n\t}", 1)[0]
            self.assertIn(f"{support_key} = yes", decision)

        self.assertEqual(1, effects.count("\njxp_a_reconcile_market_stage = {"))
        self.assertEqual(1, effects.count("\njxp_a_reconcile_market_for_route = {"))
        self.assertEqual(
            1, effects.count("\njxp_a_clear_illegal_market_stages = {")
        )
        route_alias = _block(effects, "jxp_a_reconcile_market_for_route")
        self.assertIn("jxp_a_reconcile_market_stage = yes", route_alias)
        reconcile = _block(effects, "jxp_a_reconcile_market_stage")
        self.assertLess(
            reconcile.index("has_country_flag = jxp_iface_a_market_stage_4"),
            reconcile.index("jxp_a_clear_illegal_market_stages = yes"),
        )
        self.assertIn(
            "jxp_a_market_stage_1_two_of_three_support_trigger = yes",
            reconcile,
        )
        consistency = _block(triggers, "jxp_a_market_state_is_single_trigger")
        self.assertEqual(6, consistency.count("NOT = { AND = {"))
        self.assertNotIn("capitalism", self.gameplay.lower())
        self.assertNotRegex(
            self.gameplay,
            r"(?:set|change|check)_variable\s*=\s*\{",
        )

    def test_market_attribute_extremes_are_six_visible_double_edged_modifiers(self) -> None:
        modifiers = builder.render_triggered_modifiers()
        source_loc = builder.render_localisation()
        expected = {
            "jxp_a_market_high_tenka_order": (
                "jxp_tenka_order_at_least_75 = yes",
                "global_autonomy = -0.02",
                "technology_cost = 0.03",
            ),
            "jxp_a_market_low_tenka_order": (
                "NOT = { jxp_tenka_order_at_least_25 = yes }",
                "trade_efficiency = 0.05",
                "interest = 0.5",
            ),
            "jxp_a_market_high_imperial_sanction": (
                "jxp_imperial_sanction_at_least_70 = yes",
                "interest = -0.5",
                "advisor_cost = 0.05",
            ),
            "jxp_a_market_low_imperial_sanction": (
                "NOT = { jxp_imperial_sanction_at_least_30 = yes }",
                "production_efficiency = 0.05",
                "diplomatic_reputation = -1",
            ),
            "jxp_a_market_high_oceanic_opening": (
                "jxp_oceanic_opening_at_least_75 = yes",
                "trade_efficiency = 0.05",
                "tolerance_own = -1",
            ),
            "jxp_a_market_low_oceanic_opening": (
                "NOT = { jxp_oceanic_opening_at_least_20 = yes }",
                "production_efficiency = 0.05",
                "global_institution_spread = -0.10",
            ),
        }
        self.assertTrue(
            set(expected).issubset(
                {key for key, _start, _end in top_level_blocks(modifiers)}
            )
        )
        for key, anchors in expected.items():
            with self.subTest(modifier=key):
                block = _block(modifiers, key)
                self.assertIn(
                    "potential = { jxp_a_has_any_market_stage_trigger = yes }",
                    block,
                )
                for anchor in anchors:
                    self.assertIn(anchor, block)
                self.assertIn(f"\n {key}:0 ", source_loc)
                self.assertIn(f"\n {key}_desc:0 ", source_loc)

    def test_four_crises_have_scalar_lifecycle_five_phases_and_cleanup(self) -> None:
        disasters = builder.render_disasters()
        events = builder.render_estate_events()
        effects = builder.render_effects()
        self.assertEqual(4, len(builder.CRISES))
        self.assertEqual(4, disasters.count("\n\ton_start = jxp_estates."))
        self.assertEqual(4, disasters.count("\n\ton_end = jxp_estates."))
        self.assertNotIn("on_end = {", disasters)
        self.assertNotIn("add_disaster_progress", effects)
        for index, crisis in enumerate(builder.CRISES):
            with self.subTest(crisis=crisis.key):
                disaster = _block(disasters, f"jxp_a_{crisis.key}")
                self.assertIn("can_start = {\n\t\thas_any_disaster = no", disaster)
                can_stop = disaster.split("\n\tcan_stop = {", 1)[1].split(
                    "\n\t}", 1
                )[0]
                self.assertNotIn("has_any_disaster = yes", can_stop)
                self.assertIn(
                    f"on_start = jxp_estates.{101 + index * 100}", disasters
                )
                self.assertIn(
                    f"on_end = jxp_estates.{190 + index * 100}", disasters
                )
                for phase in range(1, 6):
                    self.assertIn(
                        f"jxp_a_{crisis.key}_phase_{phase}", events
                    )
                final = _event_block(events, "jxp_estates", 114 + index * 100)
                self.assertEqual(3, final.count("\n\toption = {"))
                for outcome in ("central", "estate", "failure"):
                    self.assertIn(
                        f"jxp_a_resolve_{crisis.key}_{outcome}_effect = yes",
                        final,
                    )
                cleanup = _event_block(events, "jxp_estates", 190 + index * 100)
                self.assertIn(
                    f"jxp_a_clear_{crisis.key}_runtime_effect = yes", cleanup
                )

    def test_fifty_visible_economic_events_have_two_meaningful_options(self) -> None:
        market = builder.render_market_events()
        companies = builder.render_company_events()
        self.assertEqual(30, len(builder.MARKET_EVENT_TOPICS))
        self.assertEqual(20, len(builder.COMPANY_EVENT_TOPICS))
        for event_id in range(1, 31):
            block = _event_block(market, "jxp_market", event_id)
            self.assertEqual(2, block.count("\n\toption = {"), event_id)
            self.assertEqual(2, block.count("\n\t\tai_chance = {"), event_id)
            self.assertIn("add_country_modifier", block)
        for event_id in range(31, 51):
            block = _event_block(companies, "jxp_companies", event_id)
            self.assertEqual(2, block.count("\n\toption = {"), event_id)
            self.assertEqual(2, block.count("\n\t\tai_chance = {"), event_id)
            self.assertIn("add_country_modifier", block)
        event_19 = _event_block(market, "jxp_market", 19)
        self.assertIn("trigger = { is_year = 1730 }", event_19)
        dispatcher = _event_block(market, "jxp_market", 900)
        event_19_calls = dispatcher.count(
            "country_event = { id = jxp_market.19 days = 30 }"
        )
        filtered_calls = len(
            re.findall(
                r"1 = \{\s*trigger = \{ is_year = 1730 \}\s*"
                r"country_event = \{ id = jxp_market\.19 days = 30 \}\s*\}",
                dispatcher,
            )
        )
        self.assertGreaterEqual(event_19_calls, 2)
        self.assertEqual(event_19_calls, filtered_calls)
        self.assertNotIn(
            "has_country_flag = jxp_a_market_stage_2 is_year = 1730",
            dispatcher,
        )
        self.assertIn("duration = 1095", market)
        self.assertIn("duration = 1460", companies)

    def test_five_domestic_companies_have_full_discrete_lifecycle_and_caps(self) -> None:
        decisions = builder.render_decisions()
        events = builder.render_company_events()
        effects = builder.render_effects()
        triggers = builder.render_triggers()
        modifiers = builder.render_modifiers()
        triggered_modifiers = builder.render_triggered_modifiers()
        source_loc = builder.render_localisation()
        self.assertEqual(5, len(builder.COMPANIES))
        for index, company in enumerate(builder.COMPANIES):
            with self.subTest(company=company.key):
                self.assertIn(
                    f"jxp_a_charter_company_{company.key} = {{", decisions
                )
                decision = decisions.split(
                    f"\tjxp_a_charter_company_{company.key} = {{", 1
                )[1].split("\n\t}", 1)[0]
                self.assertIn("is_year = 1600", decision)
                self.assertIn("jxp_a_company_slot_available_trigger = yes", decision)
                self.assertIn("has_any_disaster = no", decision)
                self.assertIn("has_estate = estate_burghers", decision)
                self.assertIn(
                    "estate_loyalty = { estate = estate_burghers loyalty = 45 }",
                    decision,
                )
                self.assertIn("NOT = { num_of_loans = 3 }", decision)
                self.assertIn("NOT = { war_exhaustion = 3 }", decision)
                self.assertIn(
                    "NOT = { num_of_rebel_controlled_provinces = 1 }", decision
                )
                self.assertIn(
                    _squash(builder.COMPANY_FORMATION_CHECKS[company.key]),
                    _squash(decision),
                )
                for affinity in builder.COMPANY_FOUNDER_AFFINITIES[company.key]:
                    self.assertIn(
                        f"has_country_flag = jxp_iface_a_founder_{affinity}_legacy",
                        decision,
                    )
                self.assertIn("monthly_income = 20", decision)
                self.assertIn(
                    "estate_influence = { estate = estate_burghers influence = 50 }",
                    decision,
                )
                self.assertIn("jxp_tenka_order_at_least_50 = yes", decision)
                self.assertIn("jxp_imperial_sanction_at_least_50 = yes", decision)
                self.assertIn("jxp_oceanic_opening_at_least_50 = yes", decision)
                self.assertIn(
                    "modifier = { factor = 0 has_any_disaster = yes }",
                    decision,
                )
                ai_factor, ai_business_modifier = builder.COMPANY_AI_PROFILES[
                    company.key
                ]
                self.assertIn(f"factor = {ai_factor}", decision)
                self.assertIn(ai_business_modifier, decision)
                formation = _event_block(events, "jxp_companies", 101 + index)
                self.assertEqual(5, formation.count("\n\toption = {"))
                self.assertEqual(5, formation.count("\n\t\tai_chance = {"))
                renewal = _event_block(events, "jxp_companies", 201 + index)
                self.assertEqual(4, renewal.count("\n\toption = {"))
                self.assertEqual(4, renewal.count("\n\t\tai_chance = {"))
                for action in (
                    "renew",
                    "split_reorganize",
                    "nationalize",
                    "bankrupt",
                ):
                    self.assertIn(action, renewal)
                self.assertIn("is_at_war = yes", renewal)
                self.assertIn("num_of_loans = 5", renewal)
                self.assertIn(
                    f"jxp_a_company_{company.key}_state_distressed", renewal
                )
                self.assertIn("jxp_a_unification_method_blade", renewal)
                self.assertIn("jxp_a_unification_method_edict", renewal)
                self.assertIn("jxp_a_unification_method_league", renewal)
                split_reorganize = _block(
                    effects,
                    f"jxp_a_split_reorganize_company_{company.key}_effect",
                )
                self.assertIn(
                    f"jxp_a_clear_company_{company.key}_operating_state_effect = yes",
                    split_reorganize,
                )
                self.assertIn(
                    f"set_country_flag = jxp_a_company_{company.key}_state_reformed",
                    split_reorganize,
                )
                clear_operating = _block(
                    effects,
                    f"jxp_a_clear_company_{company.key}_operating_state_effect",
                )
                for director, _title, _desc in builder.DIRECTORS:
                    self.assertIn(
                        f"clr_country_flag = jxp_a_company_{company.key}_director_{director}",
                        clear_operating,
                    )
                self.assertIn("add_adm_power = -75", renewal)
                self.assertIn("add_treasury = -100", renewal)
                self.assertIn(
                    f"jxp_companies.{201 + index}.split_reorganize", source_loc
                )
                self.assertIn("撤换全体旧董事", source_loc)
                self.assertIn(
                    f"add_country_modifier = {{ name = {company.charter_modifier} duration = 3650 }}",
                    effects,
                )
                annual = _block(effects, "jxp_a_company_annual_pulse_effect")
                self.assertIn(f"has_country_flag = {company.charter_flag}", annual)
                self.assertIn(
                    f"NOT = {{ has_country_modifier = {company.charter_modifier} }}",
                    annual,
                )
                self.assertIn(
                    f"country_event = {{ id = jxp_companies.{201 + index} }}",
                    annual,
                )
                reconcile = _block(effects, "jxp_a_reconcile_companies_effect")
                self.assertIn(
                    f"has_country_flag = jxp_a_company_{company.key}_bankrupt_cleanup",
                    reconcile,
                )
                self.assertIn(
                    f"NOT = {{ has_country_modifier = jxp_a_company_{company.key}_bankruptcy_modifier }}",
                    reconcile,
                )
                self.assertIn(
                    f"clr_country_flag = jxp_a_company_{company.key}_bankrupt_cleanup",
                    reconcile,
                )
                nationalize = _block(
                    effects, f"jxp_a_nationalize_company_{company.key}_effect"
                )
                self.assertIn(
                    f"add_country_modifier = {{ name = jxp_a_company_{company.key}_nationalized_modifier duration = -1 }}",
                    nationalize,
                )
                self.assertIn(
                    f"has_country_flag = jxp_a_company_{company.key}_nationalized",
                    reconcile,
                )
                self.assertIn(
                    f"NOT = {{ has_country_modifier = jxp_a_company_{company.key}_nationalized_modifier }}",
                    reconcile,
                )
                self.assertIn(
                    f"add_country_modifier = {{ name = jxp_a_company_{company.key}_nationalized_modifier duration = -1 }}",
                    reconcile,
                )
                self.assertIn(f"{company.charter_modifier} = {{", modifiers)
                for state in builder.COMPANY_STATES:
                    self.assertIn(
                        f"jxp_a_company_{company.key}_state_{state}", effects
                    )
                for director, _title, _desc in builder.DIRECTORS:
                    self.assertIn(
                        f"jxp_a_charter_{company.key}_{director}_effect = {{",
                        effects,
                    )

        self.assertEqual(
            5, len({profile[0] for profile in builder.COMPANY_AI_PROFILES.values()})
        )
        annual = _block(effects, "jxp_a_company_annual_pulse_effect")
        self.assertNotIn("\n\t\telse_if = {", annual)
        for director, _title, _desc in builder.DIRECTORS:
            director_trigger = _block(
                triggers, f"jxp_a_has_company_director_{director}_trigger"
            )
            self.assertEqual(5, director_trigger.count("\n\t\tAND = {"))
            director_modifier = _block(
                triggered_modifiers,
                f"jxp_a_company_director_{director}_structure",
            )
            self.assertIn(
                f"jxp_a_has_company_director_{director}_trigger = yes",
                director_modifier,
            )
            for modifier, value in builder.DIRECTOR_MODIFIERS[director]:
                self.assertIn(f"{modifier} = {value}", director_modifier)
            self.assertIn(
                f"\n jxp_a_company_director_{director}_structure:0 ", source_loc
            )
            self.assertIn(
                f"\n jxp_a_company_director_{director}_structure_desc:0 ",
                source_loc,
            )

        for cap in range(1, 5):
            self.assertIn(f"jxp_a_company_cap_{cap}_trigger = {{", triggers)
            self.assertIn(
                f"NOT = {{ jxp_a_company_has_at_least_{cap}_trigger = yes }}",
                triggers,
            )
        self.assertEqual(1, effects.count("\njxp_a_reconcile_companies_effect = {"))
        self.assertEqual(1, effects.count("\njxp_a_reconcile_companies_for_route = {"))
        route_alias = _block(effects, "jxp_a_reconcile_companies_for_route")
        self.assertIn("jxp_a_reconcile_companies_effect = yes", route_alias)
        self.assertEqual(1, effects.count("\njxp_a_company_full_cleanup_effect = {"))
        self.assertEqual(1, effects.count("\njxp_a_company_annual_pulse_effect = {"))

    def test_economic_identity_migration_is_idempotent_and_consumed(self) -> None:
        effects = builder.render_effects()
        decisions = builder.render_decisions()
        reconcile_identity = _block(
            effects, "jxp_a_reconcile_economic_identity_effect"
        )
        reconcile_market = _block(effects, "jxp_a_reconcile_market_stage")
        self.assertIn(
            "jxp_a_reconcile_economic_identity_effect = yes", reconcile_market
        )
        for method in builder.UNIFICATION_METHODS:
            legacy = f"jxp_24_foundation_{method}"
            canonical = f"jxp_24_unification_by_{method}"
            current = f"jxp_a_unification_method_{method}"
            self.assertIn(f"has_country_modifier = {legacy}", reconcile_identity)
            self.assertIn(f"set_country_flag = {canonical}", reconcile_identity)
            self.assertIn(f"set_country_flag = {current}", reconcile_identity)
            self.assertEqual(
                1,
                reconcile_identity.count(f"remove_country_modifier = {legacy}"),
            )
            self.assertIn(current, self.gameplay)
        for affinity in (
            "commercial",
            "maritime",
            "bureaucratic",
            "communal",
            "frontier",
        ):
            self.assertIn(f"jxp_iface_a_founder_{affinity}_legacy", decisions)
        self.assertIn("jxp_a_company_has_at_least_3_trigger = yes", decisions)
        self.assertIn("num_of_rebel_controlled_provinces = 1", decisions)
        self.assertNotIn(
            "set_country_flag = jxp_iface_a_company_state_route", effects
        )
        self.assertNotIn(
            "set_country_flag = jxp_iface_a_company_state_route", decisions
        )

    def test_full_cleanup_and_persistent_state_contract_cover_every_104_surface(self) -> None:
        effects = builder.render_effects()
        triggers = builder.render_triggers()
        market_cleanup = _block(effects, "jxp_a_clear_market_runtime_effect")
        for stage in range(1, 5):
            self.assertIn(
                f"clr_country_flag = jxp_a_market_stage_{stage}_rewarded",
                market_cleanup,
            )
            self.assertIn(
                f"remove_country_modifier = jxp_a_market_stage_{stage}_transition",
                market_cleanup,
            )
        for modifier in builder.MARKET_EVENT_MODIFIERS:
            self.assertIn(
                f"remove_country_modifier = {modifier}", market_cleanup
            )

        company_cleanup = _block(effects, "jxp_a_company_full_cleanup_effect")
        company_state = _block(triggers, "jxp_a_has_any_company_state_trigger")
        for company in builder.COMPANIES:
            clear_operating = _block(
                effects,
                f"jxp_a_clear_company_{company.key}_operating_state_effect",
            )
            self.assertIn(
                f"jxp_a_clear_company_{company.key}_operating_state_effect = yes",
                company_cleanup,
            )
            for state in builder.COMPANY_STATES:
                flag = f"jxp_a_company_{company.key}_state_{state}"
                self.assertIn(f"clr_country_flag = {flag}", clear_operating)
                self.assertIn(f"has_country_flag = {flag}", company_state)
            for director, _title, _desc in builder.DIRECTORS:
                flag = f"jxp_a_company_{company.key}_director_{director}"
                self.assertIn(f"clr_country_flag = {flag}", clear_operating)
                self.assertIn(f"has_country_flag = {flag}", company_state)
            for flag in (
                company.charter_flag,
                f"jxp_a_company_{company.key}_nationalized",
                f"jxp_a_company_{company.key}_bankrupt_cleanup",
            ):
                self.assertIn(f"clr_country_flag = {flag}", company_cleanup)
                self.assertIn(f"has_country_flag = {flag}", company_state)
        for modifier in builder.COMPANY_EVENT_MODIFIERS:
            self.assertIn(
                f"remove_country_modifier = {modifier}", company_cleanup
            )
            self.assertIn(f"has_country_modifier = {modifier}", company_state)

        full_cleanup = _block(effects, "jxp_a_socioeconomic_full_cleanup_effect")
        crisis_state = _block(
            triggers, "jxp_a_any_socioeconomic_crisis_state_trigger"
        )
        for crisis in builder.CRISES:
            persistent_cleanup = _block(
                effects,
                f"jxp_a_clear_{crisis.key}_persistent_state_effect",
            )
            self.assertIn(
                f"jxp_a_clear_{crisis.key}_persistent_state_effect = yes",
                full_cleanup,
            )
            self.assertIn(
                f"jxp_a_clear_{crisis.key}_runtime_effect = yes",
                persistent_cleanup,
            )
            for suffix in (
                "resolved",
                "outcome_central",
                "outcome_estate",
                "outcome_failure",
            ):
                flag = f"jxp_a_{crisis.key}_{suffix}"
                self.assertIn(f"clr_country_flag = {flag}", persistent_cleanup)
                self.assertIn(f"has_country_flag = {flag}", crisis_state)
            for phase in range(1, 6):
                self.assertIn(
                    f"has_country_flag = jxp_a_{crisis.key}_phase_{phase}",
                    crisis_state,
                )
        self.assertIn("jxp_a_company_full_cleanup_effect = yes", full_cleanup)
        self.assertIn("jxp_a_clear_market_runtime_effect = yes", full_cleanup)

        persistent = _block(
            triggers, "jxp_a_any_socioeconomic_persistent_state_trigger"
        )
        self.assertIn("jxp_a_any_market_persistent_state_trigger = yes", persistent)
        self.assertIn(
            "jxp_a_any_company_persistent_state_trigger = yes", persistent
        )
        self.assertIn(
            "jxp_a_any_socioeconomic_crisis_state_trigger = yes", persistent
        )

    def test_b_boundary_is_five_request_flags_and_declared_bridge_only(self) -> None:
        effects = builder.render_effects()
        decisions = builder.render_decisions()
        expected = {
            f"jxp_iface_a_request_{key}_company"
            for key, _title, _desc in builder.B_REQUESTS
        }
        actual = set(
            re.findall(r"\bjxp_iface_a_request_[a-z0-9_]+_company\b", self.gameplay)
        )
        self.assertEqual(expected, actual)
        for flag in expected:
            self.assertEqual(1, effects.count(f"set_country_flag = {flag}"))
            self.assertIn(f"has_country_flag = {flag}", decisions)
        expected_b_calls = {
            "jxp_b_112_consume_agent_a_company_request_effect",
            *(
                trigger
                for trigger_pair in builder.B_REQUEST_BRIDGES.values()
                for trigger in trigger_pair
            ),
        }
        b_calls = set(re.findall(r"\bjxp_b_[a-z0-9_.]+", self.gameplay))
        self.assertEqual(
            expected_b_calls,
            b_calls,
        )
        self.assertEqual(
            6,
            effects.count("jxp_b_112_consume_agent_a_company_request_effect = yes"),
        )
        for forbidden in (
            "change_tag",
            "create_subject",
            "add_core",
            "add_permanent_claim",
            "cede_province",
        ):
            self.assertNotIn(forbidden, self.gameplay)

    def test_pulses_are_yearly_scoped_and_never_scan_the_world(self) -> None:
        on_actions = builder.render_on_actions()
        triggers = builder.render_triggers()
        self.assertEqual(1, on_actions.count("on_yearly_pulse = {"))
        self.assertNotIn("on_startup", on_actions)
        for forbidden in (
            "on_monthly_pulse",
            "every_country",
            "every_province",
            "every_owned_province",
            "random_country",
        ):
            self.assertNotIn(forbidden, self.gameplay)
        self.assertIn("jxp_a_company_pulse_relevant_trigger = yes", self.gameplay)
        self.assertIn("jxp_a_has_any_market_stage_trigger = yes", self.gameplay)

        company_pulse = _block(
            triggers, "jxp_a_company_pulse_relevant_trigger"
        )
        annual_company_pulse = _block(
            builder.render_effects(), "jxp_a_company_annual_pulse_effect"
        )
        self.assertEqual(
            1,
            annual_company_pulse.count(
                "jxp_b_112_consume_agent_a_company_request_effect = yes"
            ),
        )
        # Installation readiness and market progression are not company work:
        # a stage-three country with no charter must fail this trigger.
        self.assertNotIn("jxp_iface_a_company_core_ready", company_pulse)
        self.assertNotIn("jxp_a_has_any_company_state_trigger", company_pulse)
        for stage in range(1, 5):
            self.assertNotIn(f"jxp_a_market_stage_{stage}", company_pulse)
        self.assertIn("jxp_iface_a_company_charter_active", company_pulse)
        for company in builder.COMPANIES:
            self.assertIn(company.charter_flag, company_pulse)
            for state in builder.COMPANY_STATES:
                self.assertIn(
                    f"jxp_a_company_{company.key}_state_{state}", company_pulse
                )
            self.assertIn(
                f"jxp_a_company_{company.key}_nationalized", company_pulse
            )
            self.assertIn(
                f"jxp_a_company_{company.key}_bankrupt_cleanup", company_pulse
            )
            self.assertIn(company.charter_modifier, company_pulse)
            self.assertIn(
                f"jxp_a_company_{company.key}_nationalized_modifier",
                company_pulse,
            )
            self.assertIn(
                f"jxp_a_company_{company.key}_bankruptcy_modifier",
                company_pulse,
            )
        for request_key, _title, _desc in builder.B_REQUESTS:
            self.assertIn(
                f"jxp_iface_a_request_{request_key}_company", company_pulse
            )
        for modifier in builder.COMPANY_EVENT_MODIFIERS:
            self.assertIn(modifier, company_pulse)

    def test_chinese_source_and_active_escape_are_complete(self) -> None:
        source_path = builder.OUTPUT_PATHS["source_loc"]
        active_path = builder.OUTPUT_PATHS["active_loc"]
        source = source_path.read_text(encoding="utf-8")
        active_bytes = active_path.read_bytes()
        active = active_bytes.decode("utf-8-sig")
        self.assertTrue(active_bytes.startswith(b"\xef\xbb\xbf"))
        for stage in range(1, 5):
            key = f"jxp_iface_a_market_stage_{stage}"
            self.assertEqual(1, source.count(f"\n {key}:0 "))
            self.assertEqual(1, source.count(f"\n {key}_desc:0 "))
        for shared_key in (
            "jxp_iface_a_company_core_ready",
            "jxp_iface_a_company_charter_active",
            "jxp_iface_a_public_credit_ready",
        ):
            self.assertNotIn(f"\n {shared_key}:0 ", source)
        for request_key, _title, _desc in builder.B_REQUESTS:
            self.assertIn(
                f"\n jxp_iface_a_request_{request_key}_company:0 ", source
            )
        self.assertIn("堂岛帐合危机", source)
        self.assertIn("金银山会所", source)
        self.assertIn("家中割据", source)
        self.assertNotRegex(active, r"[\u3400-\u9fff]")
        for event_id in range(1, 31):
            self.assertIn(f" jxp_market.{event_id}.t:0 ", source)
            self.assertIn(f" jxp_market.{event_id}.d:0 ", source)
        for event_id in range(31, 51):
            self.assertIn(f" jxp_companies.{event_id}.t:0 ", source)
            self.assertIn(f" jxp_companies.{event_id}.d:0 ", source)


if __name__ == "__main__":
    unittest.main()
