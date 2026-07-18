from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import re
import unittest

from jxp_validation.clausewitz import Object, Scalar, first_object, first_scalar
from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.missions import (
    BASE_PROFILES,
    check_missions,
    evaluate_potential,
    extract_mission_series,
)


MOD_ROOT = Path(__file__).resolve().parents[3]
ROUTE_ORDER = (
    "uncommitted", "sakoku", "open", "buddhist", "kirishitan", "confucian",
    "imperial", "reformed", "kaikyo", "ikko", "wokou", "toyotomi",
)
PROFILE_NAMES = {
    "uncommitted": "JAP Shinto (uncommitted)",
    "sakoku": "JAP Shinto (sakoku)",
    "open": "JAP Shinto (open)",
    "buddhist": "JAP Buddhist (Shinbutsu)",
    "kirishitan": "KJP Christian",
    "confucian": "CJP Confucian + harmonized Shinto",
    "imperial": "EJP Imperial",
    "reformed": "RFJ Reformed",
    "kaikyo": "SJP Kaikyo",
    "ikko": "IJP Ikko",
    "wokou": "WAK Wokou",
    "toyotomi": "TOY Toyotomi realm",
}


def numbered(prefix: str, count: int) -> tuple[str, ...]:
    return tuple(f"{prefix}_{index:02d}" for index in range(1, count + 1))


ROUTE_MATRIX = {
    "uncommitted": {
        "mainland": numbered("jxp_b_115_uncommitted_mainland", 5),
        "overseas": numbered("jxp_b_115_uncommitted_overseas", 5),
    },
    "sakoku": {
        "mainland": (
            "jxp_mission_sakoku_coastal_magistrates",
            "jxp_mission_sakoku_matsumae_compact",
            "jxp_mission_sakoku_tsushima_interpreters",
            "jxp_mission_sakoku_ryukyu_protocol",
            "jxp_mission_sakoku_beacon_coast",
        ),
        "overseas": (
            "jxp_mission_dejima_window",
            "jxp_mission_sakoku_one_permitted_window",
            *numbered("jxp_b_115_sakoku_overseas", 3),
        ),
    },
    "open": {
        "mainland": (
            "jxp_mission_eastasia_ryukyu_gateway",
            "jxp_mission_eastasia_korea_embassy",
            "jxp_mission_eastasia_ming_trade",
            *numbered("jxp_b_115_open_trade", 2),
        ),
        "overseas": (
            "jxp_mission_pacific_charter",
            "jxp_mission_pacific_ogasawara_anchor",
            "jxp_mission_pacific_hawaii_soundings",
            *numbered("jxp_b_115_open_settlement", 2),
        ),
        "navy": (
            "jxp_mission_eastasia_manchu_watch",
            "jxp_mission_eastasia_taiwan_lanes",
            "jxp_mission_eastasia_hegemon_of_the_seas",
            "jxp_mission_eastasia_celestial_diplomacy",
            "jxp_mission_eastasia_littoral_entrepots",
        ),
    },
    "buddhist": {
        "mainland": (
            "jxp_a_buddhist_korean_scriptures",
            "jxp_a_buddhist_chinese_monks",
            "jxp_a_buddhist_ryukyu_dharma_lamp",
            *numbered("jxp_b_115_buddhist_mainland", 2),
        ),
        "overseas": (
            "jxp_a_buddhist_south_seas_temples",
            *numbered("jxp_b_115_buddhist_overseas", 4),
        ),
    },
    "kirishitan": {
        "mainland": (
            "jxp_mission_nagasaki_bishopric",
            "jxp_mission_roman_kyoto_embassy",
            *numbered("jxp_b_115_kirishitan_mainland", 3),
        ),
        "overseas": numbered("jxp_b_115_kirishitan_overseas", 5),
    },
    "confucian": {
        "mainland": (
            "jxp_mission_korean_envoys",
            "jxp_mission_cjp_three_teachings_register",
            "jxp_mission_cjp_rites_without_severance",
            *numbered("jxp_b_115_confucian_mainland", 2),
        ),
        "overseas": (
            "jxp_mission_nagasaki_translation_house",
            "jxp_mission_silver_silk_routing",
            "jxp_mission_three_capitals_ledgers",
            "jxp_mission_castle_town_markets",
            "jxp_b_115_confucian_overseas_01",
        ),
    },
    "imperial": {
        "mainland": (
            "jxp_mission_ejp_ryukyu_envoys",
            "jxp_mission_ejp_ezo_commission",
            "jxp_mission_ejp_korean_mission",
            *numbered("jxp_b_115_imperial_mainland", 2),
        ),
        "overseas": numbered("jxp_b_115_imperial_overseas", 5),
    },
    "reformed": {
        "mainland": (
            "jxp_mission_reformed_settlement",
            "jxp_mission_oranda_colleges",
            "jxp_mission_covenant_commonwealth",
            *numbered("jxp_b_115_reformed_mainland", 2),
        ),
        "overseas": (
            "jxp_mission_batavia_compacts",
            "jxp_mission_rfj_chartered_companies",
            "jxp_mission_rfj_free_seas_commonwealth",
            "jxp_mission_rfj_synodic_constitution",
            "jxp_b_115_reformed_overseas_01",
        ),
    },
    "kaikyo": {
        "mainland": (
            "jxp_mission_sakai_malay_brokers",
            "jxp_mission_qadi_port_courts",
            *numbered("jxp_b_115_kaikyo_mainland", 3),
        ),
        "overseas": (
            "jxp_mission_kaikyo_settlement",
            "jxp_mission_hajj_registry",
            "jxp_mission_south_sea_compact",
            "jxp_mission_sultanate_sea_law",
            "jxp_mission_sjp_diwan_constitution",
        ),
    },
    "ikko": {
        "mainland": (
            "jxp_mission_commonwealth_covenant",
            *numbered("jxp_b_115_ikko_mainland", 4),
        ),
        "overseas": (
            "jxp_mission_ikko_temple_granaries",
            "jxp_mission_ikko_communal_shipyards",
            *numbered("jxp_b_115_ikko_overseas", 3),
        ),
    },
    "wokou": {
        "mainland": (
            "jxp_mission_tsushima_interpreters",
            "jxp_mission_ryukyu_embassy_records",
            *numbered("jxp_b_115_wokou_mainland", 3),
        ),
        "overseas": (
            "jxp_mission_wak_letters_of_black_current",
            "jxp_mission_wak_island_courts",
            *numbered("jxp_b_115_wokou_overseas", 3),
        ),
    },
    "toyotomi": {
        "mainland": (
            "jxp_mission_toyotomi_osaka_castle_town",
            "jxp_mission_toyotomi_jurakudai_audiences",
            "jxp_mission_toyotomi_sakai_magistrates",
            "jxp_mission_toyotomi_kuraire_ledgers",
            "jxp_mission_toyotomi_taiko_testament",
        ),
        "overseas": (
            "jxp_mission_toyotomi_ryukyu_letters",
            "jxp_mission_toyotomi_tsushima_channel",
            "jxp_mission_toyotomi_continental_preparations",
            "jxp_mission_toyotomi_east_asian_negotiations",
            "jxp_mission_toyotomi_peace_beneath_heaven",
        ),
    },
}

CAPSTONES = {
    "uncommitted": ("jxp_b_115_uncommitted_overseas_05",),
    "sakoku": ("jxp_b_115_sakoku_overseas_03",),
    "open": (
        "jxp_b_115_open_trade_02",
        "jxp_b_115_open_settlement_02",
    ),
    "buddhist": ("jxp_b_115_buddhist_overseas_04",),
    "kirishitan": ("jxp_b_115_kirishitan_overseas_05",),
    "confucian": ("jxp_b_115_confucian_overseas_01",),
    "imperial": ("jxp_b_115_imperial_overseas_05",),
    "reformed": ("jxp_b_115_reformed_overseas_01",),
    "kaikyo": ("jxp_b_115_kaikyo_mainland_03",),
    "ikko": ("jxp_b_115_ikko_overseas_03",),
    "wokou": ("jxp_b_115_wokou_overseas_03",),
    "toyotomi": (),
}


def _read(relative: str) -> str:
    return (MOD_ROOT / relative).read_text(encoding="utf-8-sig")


def _contains_scalar(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any(
        (entry.key == key and isinstance(entry.value, Scalar) and entry.value.text == value)
        or (isinstance(entry.value, Object) and _contains_scalar(entry.value, key, value))
        for entry in obj.entries
    )


def _contains_key(obj: Object | None, key: str) -> bool:
    if obj is None:
        return False
    return any(
        entry.key == key
        or (isinstance(entry.value, Object) and _contains_key(entry.value, key))
        for entry in obj.entries
    )


class ExternalRouteMissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = ValidationContext(MOD_ROOT)
        result = CheckResult("B115")
        cls.series = extract_mission_series(
            cls.context,
            result,
            (MOD_ROOT / "missions").glob("*.txt"),
            infer_implicit_positions=True,
        )
        if result.issues:
            raise AssertionError([issue.message for issue in result.issues])
        cls.profiles = {profile.name: profile for profile in BASE_PROFILES}
        cls.mission_objects: dict[str, Object] = {}
        for source in (MOD_ROOT / "missions").glob("*.txt"):
            document = cls.context.document(source)
            if document is None:
                continue
            for series_entry in document.root.entries:
                if not isinstance(series_entry.value, Object):
                    continue
                for mission_entry in series_entry.value.entries:
                    if mission_entry.key and isinstance(mission_entry.value, Object):
                        if first_scalar(mission_entry.value, "position") is not None:
                            cls.mission_objects[mission_entry.key] = mission_entry.value

    def active_missions(self, route: str, *, random_world: bool = False) -> set[str]:
        profile = self.profiles[PROFILE_NAMES[route]]
        if random_world:
            profile = replace(profile, map_setup="map_setup_random")
        return {
            mission.mission_id
            for series in self.series
            if not series.generic and True in evaluate_potential(series.potential, profile)[0]
            for mission in series.missions
        }

    def test_twelve_routes_each_have_five_mainland_and_five_overseas_missions(self) -> None:
        signatures = set()
        for route in ROUTE_ORDER:
            active = self.active_missions(route)
            mainland = ROUTE_MATRIX[route]["mainland"]
            overseas = ROUTE_MATRIX[route]["overseas"]
            self.assertEqual(len(mainland), 5, route)
            self.assertEqual(len(overseas), 5, route)
            self.assertTrue(set(mainland) <= active, (route, set(mainland) - active))
            self.assertTrue(set(overseas) <= active, (route, set(overseas) - active))
            signatures.add(tuple(sorted((*mainland, *overseas))))
        self.assertEqual(len(signatures), 12)
        self.assertEqual(len(ROUTE_MATRIX["open"]["navy"]), 5)
        self.assertTrue(set(ROUTE_MATRIX["open"]["navy"]) <= self.active_missions("open"))

    def test_live_profile_topology_remains_collision_free_and_balanced(self) -> None:
        result = check_missions(ValidationContext(MOD_ROOT))
        forbidden = {
            "mission.position_order",
            "mission.position_gap",
            "mission.profile_series_overlap",
            "mission.profile_collision",
            "mission.unified_terminal_imbalance",
        }
        self.assertFalse([issue for issue in result.issues if issue.code in forbidden])
        for series in self.series:
            new_rows = [m.row for m in series.missions if m.mission_id.startswith("jxp_b_115_")]
            if new_rows:
                rows = [m.row for m in series.missions if m.row is not None]
                self.assertEqual(rows, sorted(rows), series.name)
                self.assertLessEqual(max(b - a for a, b in zip(rows, rows[1:])), 2, series.name)

    def test_every_route_has_events_interaction_and_bounded_capstone(self) -> None:
        events = _read("events/jxp_b_115_external_route_events.txt")
        decisions = _read("decisions/jxp_b_115_external_route_interactions.txt")
        for index, route in enumerate(ROUTE_ORDER):
            base = index * 10
            for number in range(1, 6):
                self.assertIn(f"id = jxp_b_115_routes.{base + number}", events)
            self.assertIn(f"jxp_b_115_{route}_external_interaction = {{", decisions)
            for capstone_id in CAPSTONES[route]:
                effect = first_object(self.mission_objects[capstone_id], "effect")
                self.assertTrue(_contains_scalar(effect, "set_country_flag", "jxp_iface_b_external_capstone_complete"), capstone_id)
                self.assertTrue(_contains_scalar(effect, "name", f"jxp_b_115_{route}_external_capstone"), capstone_id)
                self.assertTrue(_contains_scalar(effect, "duration", "7300"), capstone_id)
        naval = decisions[decisions.index("jxp_b_115_open_naval_charter = {"):]
        self.assertIn("mission_completed = jxp_mission_eastasia_hegemon_of_the_seas", naval)
        self.assertIn("set_country_flag = jxp_iface_b_external_capstone_complete", naval)
        self.assertIn("name = jxp_b_115_open_external_capstone", naval)
        self.assertIn("duration = 7300", naval)
        toyotomi = decisions[decisions.index("jxp_b_115_toyotomi_external_charter = {"):]
        self.assertIn("mission_completed = jxp_mission_toyotomi_taiko_testament", toyotomi)
        self.assertIn("mission_completed = jxp_mission_toyotomi_peace_beneath_heaven", toyotomi)
        self.assertIn("set_country_flag = jxp_iface_b_external_capstone_complete", toyotomi)
        self.assertIn("name = jxp_b_115_toyotomi_external_capstone", toyotomi)

    def test_open_trade_navy_settlement_are_one_mainline_and_one_limited_side_line(self) -> None:
        decisions = _read("decisions/jxp_b_115_external_route_interactions.txt")
        events = _read("events/jxp_b_115_external_route_events.txt")
        self.assertIn("NOT = { has_country_flag = jxp_b_115_open_strategy_chosen }", decisions)
        for kind in ("trade", "settlement"):
            prep = first_object(self.mission_objects[f"jxp_b_115_open_{kind}_01"], "trigger")
            capstone = first_object(self.mission_objects[f"jxp_b_115_open_{kind}_02"], "trigger")
            self.assertTrue(_contains_scalar(prep, "has_country_flag", f"jxp_b_115_open_main_{kind}"))
            self.assertTrue(_contains_scalar(prep, "has_country_flag", f"jxp_b_115_open_secondary_{kind}"))
            self.assertTrue(_contains_scalar(capstone, "has_country_flag", f"jxp_b_115_open_main_{kind}"))
            self.assertFalse(_contains_scalar(capstone, "has_country_flag", f"jxp_b_115_open_secondary_{kind}"))
        self.assertIn("has_country_flag = jxp_b_115_open_main_navy", decisions)
        self.assertIn("jxp_b_115_open_secondary_navy", events)
        self.assertIn("jxp_b_115_open_naval_charter", decisions)
        self.assertIn("num_of_colonists = 1", events)
        self.assertIn("navy_size_percentage = 0.8", events)
        self.assertIn("trade_efficiency = 0.25", events)

    def test_ai_interactions_have_financial_and_war_brakes(self) -> None:
        decisions = _read("decisions/jxp_b_115_external_route_interactions.txt")
        for guard in (
            "factor = 0 is_bankrupt = yes",
            "factor = 0 is_at_war = yes",
            "factor = 0 num_of_loans = 3",
            "factor = 0 NOT = { stability = 0 }",
            "factor = 0.25 war_exhaustion = 2",
        ):
            self.assertGreaterEqual(decisions.count(guard), 12, guard)

    def test_route_change_cleanup_closes_every_b115_flag_and_modifier(self) -> None:
        missions = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (MOD_ROOT / "missions").glob("*.txt")
            if "jxp_b_115_" in path.read_text(encoding="utf-8-sig")
        )
        decisions = _read("decisions/jxp_b_115_external_route_interactions.txt")
        events = _read("events/jxp_b_115_external_route_events.txt")
        cleanup = _read("common/scripted_effects/jxp_b_115_external_route_effects.txt")
        lifecycle = _read("common/scripted_effects/jxp_scripted_effects.txt")
        set_flags = set(re.findall(r"set_country_flag\s*=\s*(jxp_(?:b_115|iface_b)[A-Za-z0-9_]*)", missions + decisions + events))
        added_modifiers = set(re.findall(r"name\s*=\s*(jxp_b_115_[A-Za-z0-9_]+)", missions + decisions))
        for flag in set_flags:
            self.assertIn(f"clr_country_flag = {flag}", cleanup)
        for modifier in added_modifiers:
            self.assertIn(f"remove_country_modifier = {modifier}", cleanup)
        self.assertIn("jxp_b_115_clear_external_route_state_effect = yes", lifecycle)
        self.assertNotIn("mission_completed", cleanup)

    def test_rewards_avoid_overpowered_permanent_shortcuts(self) -> None:
        modifiers = _read("common/event_modifiers/jxp_b_115_external_route_modifiers.txt")
        for forbidden in (
            "administrative_efficiency",
            "discipline",
            "core_creation",
            "ae_impact",
        ):
            self.assertNotIn(forbidden, modifiers)
            for mission_id, mission in self.mission_objects.items():
                if mission_id.startswith("jxp_b_115_"):
                    self.assertFalse(_contains_key(first_object(mission, "effect"), forbidden), mission_id)
        for mission_id, mission in self.mission_objects.items():
            if mission_id.startswith("jxp_b_115_"):
                self.assertFalse(_contains_scalar(first_object(mission, "effect"), "duration", "-1"), mission_id)

    def test_readable_source_exactly_generates_active_localisation_and_all_flags_are_named(self) -> None:
        source_path = MOD_ROOT / "localisation_source/jxp_b_115_external_routes_l_english_utf8_source.yml"
        active_path = MOD_ROOT / "localisation/jxp_b_115_external_routes_l_english.yml"
        source_bytes = source_path.read_bytes()
        source = source_bytes.decode("utf-8-sig")
        spec = importlib.util.spec_from_file_location(
            "_b115_escape",
            MOD_ROOT.parent / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(active_path.read_bytes(), module.escape_text(source).encode("utf-8-sig"))
        self.assertFalse(re.search(r"[\u3400-\u9fff]", active_path.read_text(encoding="utf-8-sig")))
        keys = set(re.findall(r"(?m)^\s*([A-Za-z0-9_.-]+):0\s", source))
        scripts = "\n".join((
            _read("events/jxp_b_115_external_route_events.txt"),
            _read("decisions/jxp_b_115_external_route_interactions.txt"),
            *(
                path.read_text(encoding="utf-8-sig")
                for path in (MOD_ROOT / "missions").glob("*.txt")
                if "jxp_b_115_" in path.read_text(encoding="utf-8-sig")
            ),
        ))
        flags = set(re.findall(
            r"(?:has|set|clr)_country_flag\s*=\s*(jxp_(?:b_115[A-Za-z0-9_]*|iface_b_external_capstone_complete))",
            scripts,
        ))
        self.assertFalse(flags - keys, flags - keys)
        for tooltip in re.findall(r"tooltip\s*=\s*(jxp_b_115_[A-Za-z0-9_]+)", scripts):
            self.assertIn(tooltip, keys)

    def test_mission_descriptions_use_stage_specific_narratives(self) -> None:
        source = _read("localisation_source/jxp_b_115_external_routes_l_english_utf8_source.yml")
        descriptions = re.findall(
            r'^\s*jxp_b_115_[A-Za-z0-9_]+_(?:mainland|overseas|trade|navy|settlement)_\d\d_desc:0\s+"([^"]+)"',
            source,
            re.MULTILINE,
        )
        self.assertGreaterEqual(len(descriptions), 50)
        self.assertEqual(len(descriptions), len(set(descriptions)))
        for marker in ("首批训令", "当地使者", "最昂贵", "总章程"):
            self.assertTrue(any(marker in desc for desc in descriptions), marker)
        self.assertFalse(any("为议题，把" in desc for desc in descriptions))

    def test_random_new_world_hides_b115_trees_and_uses_b118_simplified_fallback(self) -> None:
        for route in ROUTE_ORDER:
            self.assertFalse(
                {mission for mission in self.active_missions(route, random_world=True) if mission.startswith("jxp_b_115_")},
                route,
            )
        fallback_decision = _read("decisions/jxp_b_118_external_fallback_decisions.txt")
        fallback_event = _read("events/jxp_b_118_external_fallback_events.txt")
        self.assertIn("jxp_b_118_review_external_sailing_orders", fallback_decision)
        self.assertIn("jxp_b_external_fallbacks.1", fallback_event)

    def test_commercial_council_route_keeps_agent_a_as_the_only_writer(self) -> None:
        b_scripts = "\n".join(
            path.read_text(encoding="utf-8-sig", errors="ignore")
            for folder in ("common", "decisions", "events", "missions")
            for path in (MOD_ROOT / folder).rglob("jxp_b_*.txt")
        )
        self.assertIn("has_country_flag = jxp_iface_a_company_state_route", b_scripts)
        self.assertNotIn("set_country_flag = jxp_iface_a_company_state_route", b_scripts)
        self.assertIn("jxp_b_legacy_commercial_council", b_scripts)
        self.assertNotIn("jxp_b_115_commercial_council", b_scripts)


if __name__ == "__main__":
    unittest.main()
