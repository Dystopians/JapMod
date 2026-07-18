from __future__ import annotations

import re
import unittest
from pathlib import Path

from jxp_validation.clausewitz import parse_text


MOD_ROOT = Path(__file__).resolve().parents[3]


def read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


def brace_block(payload: str, marker: str, *, enclosing: str | None = None) -> str:
    marker_at = payload.index(marker)
    start = payload.rfind(enclosing, 0, marker_at) if enclosing else marker_at
    if start < 0:
        raise AssertionError(f"missing enclosing marker {enclosing!r} for {marker!r}")
    opening = payload.index("{", start)
    depth = 0
    for index in range(opening, len(payload)):
        if payload[index] == "{":
            depth += 1
        elif payload[index] == "}":
            depth -= 1
            if depth == 0:
                return payload[start : index + 1]
    raise AssertionError(f"unterminated block for {marker!r}")


def paid_costs(payload: str) -> dict[str, int]:
    result = {"treasury": 0, "adm_power": 0, "dip_power": 0}
    for resource, value in re.findall(r"add_(treasury|adm_power|dip_power)\s*=\s*-(\d+)", payload):
        result[resource] += int(value)
    return result


class ExternalDepthContractTests(unittest.TestCase):
    B112_FILES = (
        "common/scripted_triggers/jxp_b_112_external_triggers.txt",
        "common/scripted_effects/jxp_b_112_external_effects.txt",
        "common/event_modifiers/jxp_b_112_external_modifiers.txt",
        "common/opinion_modifiers/jxp_b_112_external_opinions.txt",
        "decisions/jxp_b_112_overseas_company_decisions.txt",
        "events/jxp_b_112_overseas_company_events.txt",
    )
    B113_FILES = (
        "common/scripted_triggers/jxp_b_113_external_triggers.txt",
        "common/scripted_effects/jxp_b_113_external_effects.txt",
        "common/event_modifiers/jxp_b_113_external_modifiers.txt",
        "common/opinion_modifiers/jxp_b_113_external_opinions.txt",
        "decisions/jxp_b_113_regional_diplomacy_decisions.txt",
        "events/jxp_b_113_postconquest_governance.txt",
        "events/jxp_b_113_regional_diplomacy_events.txt",
        "events/jxp_b_113_china_endgame_depth_events.txt",
    )

    def test_new_gameplay_files_parse(self) -> None:
        for relative in self.B112_FILES + self.B113_FILES:
            with self.subTest(relative=relative):
                parse_text(read(relative))

    def test_five_companies_have_full_lifecycle_without_land_grants(self) -> None:
        decisions = read("decisions/jxp_b_112_overseas_company_decisions.txt")
        events = read("events/jxp_b_112_overseas_company_events.txt")
        effects = read("common/scripted_effects/jxp_b_112_external_effects.txt")
        modifiers = read("common/event_modifiers/jxp_b_112_external_modifiers.txt")
        for company in (
            "south_seas",
            "north_sea",
            "taiwan_fujian",
            "oceanic",
            "new_world",
        ):
            with self.subTest(company=company):
                self.assertIn(f"jxp_b_112_found_{company}_company", decisions)
                self.assertIn(f"jxp_b_112_review_{company}_company", decisions)
                self.assertIn(f"jxp_b_112_{company}_company_active", effects)
                self.assertIn(f"jxp_b_112_{company}_company", modifiers)
        for event_id in (*range(1, 6), *range(21, 26), *range(41, 46), *range(61, 66)):
            self.assertIn(f"id = jxp_b_company.{event_id}", events)
        self.assertIn("host_accept", events)
        self.assertIn("host_refuse", events)
        self.assertIn("ai_chance", events)
        payload = decisions + events + effects
        self.assertNotIn("save_event_target_as = jxp_b_112_company_host", payload)
        for forbidden in (
            "annex =",
            "inherit =",
            "cede_province",
            "add_core",
            "change_tag",
            "create_subject",
        ):
            self.assertNotIn(forbidden, payload)

    def test_agent_a_company_requests_settle_once_through_b_company_registry(self) -> None:
        a_effects = read("common/scripted_effects/jxp_a_104_economy_effects.txt")
        a_decisions = read("decisions/jxp_a_104_economy_decisions.txt")
        b_effects = read("common/scripted_effects/jxp_b_112_external_effects.txt")
        b_triggers = read("common/scripted_triggers/jxp_b_112_external_triggers.txt")
        b_decisions = read("decisions/jxp_b_112_overseas_company_decisions.txt")
        b_events = read("events/jxp_b_112_overseas_company_events.txt")
        mappings = (
            ("red_seal_overseas", 81, "south_seas", 1),
            ("pacific_charter", 82, "new_world", 5),
            ("southern_seas", 83, "oceanic", 4),
            ("northern_seas", 84, "north_sea", 2),
            ("continental", 85, "taiwan_fujian", 3),
        )
        special_gates = {
            "red_seal_overseas": "num_of_light_ship = 8",
            "pacific_charter": "OR = { num_of_colonists = 1 tag = NYA tag = TPF jxp_b_92_rnw_western_anchor_trigger = yes }",
            "southern_seas": "num_of_transport = 10",
            "northern_seas": None,
            "continental": "num_of_ports = 10",
        }

        for request, request_event, company, charter_event in mappings:
            with self.subTest(request=request, company=company):
                flag = f"jxp_iface_a_request_{request}_company"
                visible_trigger = f"jxp_b_112_agent_a_{request}_request_visible_trigger"
                ready_trigger = f"jxp_b_112_agent_a_{request}_request_ready_trigger"
                a_effect = brace_block(a_effects, f"jxp_a_request_{request}_company_effect")
                self.assertIn(f"set_country_flag = {flag}", a_effect)
                self.assertEqual(1, a_effect.count("jxp_b_112_consume_agent_a_company_request_effect = yes"))

                dispatch = brace_block(b_effects, "jxp_b_112_consume_agent_a_company_request_effect")
                self.assertIn(f"has_country_flag = {flag}", dispatch)
                self.assertIn(f"country_event = {{ id = jxp_b_company.{request_event} }}", dispatch)

                a_request = brace_block(a_decisions, f"jxp_a_request_{request}_company =")
                self.assertIn(f"{visible_trigger} = yes", a_request)
                self.assertIn(f"{ready_trigger} = yes", a_request)
                request_ai = brace_block(a_request, "ai_will_do =")
                self.assertIn("factor = 0", request_ai)
                self.assertNotIn("factor = 0.10", request_ai)
                visible = brace_block(b_triggers, visible_trigger)
                ready = brace_block(b_triggers, ready_trigger)
                self.assertIn("jxp_b_112_company_actor_trigger = yes", visible)
                self.assertIn(f"jxp_b_112_{company}_company_available_trigger = yes", visible)
                self.assertIn(f"NOT = {{ has_country_flag = jxp_b_112_{company}_company_active }}", visible)
                self.assertIn(f"{visible_trigger} = yes", ready)
                self.assertIn("jxp_b_112_company_foundation_capacity_trigger = yes", ready)
                if special_gates[request] is not None:
                    self.assertIn(special_gates[request], ready)

                request_block = brace_block(
                    b_events,
                    f"id = jxp_b_company.{request_event}",
                    enclosing="country_event = {",
                )
                self.assertIn(f"jxp_b_112_{company}_company_available_trigger = yes", request_block)
                self.assertIn(f"NOT = {{ has_country_flag = jxp_b_112_{company}_company_active }}", request_block)
                self.assertIn("dip_tech = 9", request_block)
                self.assertIn(
                    "num_of_ports = 10" if request == "continental" else "num_of_ports = 8",
                    request_block,
                )
                if special_gates[request] is not None:
                    self.assertIn(special_gates[request], request_block)
                self.assertIn(f"country_event = {{ id = jxp_b_company.{charter_event} }}", request_block)
                self.assertNotIn(f"id = jxp_b_company.{charter_event} days =", request_block)
                self.assertIn("ai_chance = { factor = 100 }", request_block)
                self.assertIn("ai_chance = { factor = 0 }", request_block)
                self.assertEqual(2, request_block.count("jxp_b_112_clear_agent_a_company_requests_effect = yes"))

                direct_foundation = brace_block(b_decisions, f"jxp_b_112_found_{company}_company =")
                combined = paid_costs(a_request)
                for resource, value in paid_costs(request_block).items():
                    combined[resource] += value
                self.assertEqual(paid_costs(direct_foundation), combined)

        annual = brace_block(a_effects, "jxp_a_company_annual_pulse_effect")
        self.assertEqual(
            1,
            annual.count("jxp_b_112_consume_agent_a_company_request_effect = yes"),
        )

        runtime_files = (
            path
            for folder in ("common", "decisions", "events", "missions")
            for path in (MOD_ROOT / folder).rglob("*.txt")
        )
        writers: dict[str, set[str]] = {request: set() for request, *_rest in mappings}
        for path in runtime_files:
            payload = path.read_text(encoding="utf-8-sig", errors="ignore")
            for request in writers:
                flag = f"jxp_iface_a_request_{request}_company"
                if f"set_country_flag = {flag}" in payload:
                    writers[request].add(path.relative_to(MOD_ROOT).as_posix())
        self.assertEqual(
            {request: {"common/scripted_effects/jxp_a_104_economy_effects.txt"} for request in writers},
            writers,
        )

    def test_new_world_company_supports_normal_and_random_new_world(self) -> None:
        triggers = read("common/scripted_triggers/jxp_b_112_external_triggers.txt")
        decisions = read("decisions/jxp_b_112_overseas_company_decisions.txt")
        self.assertIn("jxp_b_92_normal_west_coast_anchor_trigger", triggers)
        self.assertIn("jxp_b_92_rnw_western_anchor_trigger", triggers)
        self.assertIn("continent = new_world", triggers)
        self.assertIn(
            "OR = { num_of_colonists = 1 tag = NYA tag = TPF jxp_b_92_rnw_western_anchor_trigger = yes }",
            decisions,
        )
        self.assertEqual(5, decisions.count("jxp_b_118_ai_company_ready_trigger = yes"))

    def test_four_governance_modes_have_three_reviews_and_terminal_choice(self) -> None:
        b99 = read("common/scripted_effects/jxp_b_99_continental_strategy_effects.txt")
        effects = read("common/scripted_effects/jxp_b_113_external_effects.txt")
        events = read("events/jxp_b_113_postconquest_governance.txt")
        for mode in (
            "military_commission",
            "local_dynasty",
            "tribute_trade",
            "direct_governor",
        ):
            self.assertIn(f"jxp_b_113_begin_{mode}_governance_effect = yes", b99)
            self.assertIn(f"jxp_b_113_transition_to_{mode}_effect", effects)
        for event_id in range(100, 104):
            self.assertIn(f"id = jxp_b_governance.{event_id}", events)
        self.assertGreaterEqual((effects + events).count("duration = 7300"), 6)
        for review in range(1, 4):
            self.assertIn(f"jxp_b_113_governance_review_{review}_done", events)
        self.assertIn("jxp_iface_b_postconquest_governance_active", effects)
        self.assertIn("remove_province_modifier = jxp_b_113_governed_province", effects)
        self.assertIn(
            "add_province_modifier = { name = jxp_b_113_governed_province duration = 7300 }",
            effects,
        )
        self.assertNotIn(
            "add_province_modifier = { name = jxp_b_113_governed_province duration = -1 }",
            effects,
        )

    def test_regional_chains_preserve_local_agency(self) -> None:
        decisions = read("decisions/jxp_b_113_regional_diplomacy_decisions.txt")
        events = read("events/jxp_b_113_regional_diplomacy_events.txt")
        for decision in (
            "open_ryukyu_compact",
            "open_tsushima_mediation",
            "open_northern_compact",
            "open_taiwan_maritime_compact",
        ):
            self.assertIn(f"jxp_b_113_{decision}", decisions)
        expected = {
            *range(201, 209),
            *range(301, 307),
            *range(401, 407),
            *range(501, 507),
        }
        actual = {int(value) for value in re.findall(r"id = jxp_b_regional_depth\.(\d+)", events)}
        self.assertEqual(expected, actual)
        for interface in (
            "ryukyu_compact",
            "tsushima_mediation",
            "northern_compact",
            "taiwan_compact",
        ):
            self.assertIn(f"jxp_iface_b_{interface}_active", events)

    def test_three_china_endgames_are_five_stage_programs(self) -> None:
        events = read("events/jxp_b_113_china_endgame_depth_events.txt")
        effects = read("common/scripted_effects/jxp_b_100_china_endgames_effects.txt")
        triggers = read("common/scripted_triggers/jxp_b_100_china_endgames_triggers.txt")
        for base in (600, 610, 620):
            for step in range(1, 6):
                self.assertIn(f"id = jxp_b_china_depth.{base + step}", events)
        self.assertEqual(24, events.count("days = 730"))
        self.assertEqual(3, events.count("jxp_b_113_complete_china_long_program_effect = yes"))
        self.assertEqual(3, effects.count("jxp_b_113_start_china_long_program_effect = yes"))
        self.assertEqual(3, triggers.count("jxp_b_113_china_long_program_complete_trigger = yes"))

    def test_source_and_active_localisation_match(self) -> None:
        key_pattern = re.compile(r"^\s+([^#\s][^:]*):\d+", re.MULTILINE)
        for stem in ("jxp_b_112_external", "jxp_b_113_external"):
            source = read(f"localisation_source/{stem}_l_english_utf8_source.yml")
            active_path = MOD_ROOT / f"localisation/{stem}_l_english.yml"
            active = active_path.read_text(encoding="utf-8-sig")
            self.assertEqual(set(key_pattern.findall(source)), set(key_pattern.findall(active)))
            self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        source = read("localisation_source/jxp_b_113_external_l_english_utf8_source.yml")
        for key in (
            "jxp_iface_b_postconquest_governance_active",
            "jxp_iface_b_ryukyu_compact_active",
            "jxp_iface_b_tsushima_mediation_active",
            "jxp_iface_b_northern_compact_active",
            "jxp_iface_b_taiwan_compact_active",
            "jxp_iface_b_china_long_program_complete",
        ):
            self.assertRegex(source, rf"(?m)^\s+{re.escape(key)}:\d+")


if __name__ == "__main__":
    unittest.main()
