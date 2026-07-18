from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"
ESCAPER_PATH = (
    REPO_ROOT
    / "skills"
    / "eu4-modding"
    / "scripts"
    / "escape_eu4_special_localisation.py"
)
LOCALISATION_KEY = re.compile(r"^\s*([A-Za-z0-9_.-]+):\d+\s", re.MULTILINE)
LOCALISATION_ENTRY = re.compile(
    r'^\s*([A-Za-z0-9_.-]+):\d+\s+"(.*)"\s*$', re.MULTILINE
)
FLAG_REFERENCE = re.compile(
    rb"\b(?:has|had)_(?:country|province)_flag\s*=\s*([A-Za-z0-9_.-]+)"
)
EVENT_STRUCTURE_TOKEN = re.compile(
    rb"([A-Za-z0-9_.-]+)\s*=\s*\{|([{}])|"
    rb"\b(?:has|had)_(?:country|province)_flag\s*=\s*([A-Za-z0-9_.-]+)"
)
REFORM_DEFINITION = re.compile(
    r"^\s*(jxp_reform_[A-Za-z0-9_]+)\s*=\s*\{", re.MULTILINE
)
PLAYER_VISIBLE_FLAG_LOCATIONS = (
    "missions",
    "decisions",
    "common/cb_types",
    "common/disasters",
    "common/government_mechanics",
    "common/government_reforms",
    "common/ideas",
    "common/imperial_reforms",
    "common/new_diplomatic_actions",
    "common/peace_treaties",
    "common/scripted_triggers",
    "common/triggered_modifiers",
    "common/wargoal_types",
)

VISIBLE_FLAG_KEYS = {
    "jxp_path_sakoku",
    "jxp_path_open_trade",
    "jxp_path_kirishitan",
    "jxp_path_confucian",
    "jxp_path_imperial",
    "jxp_path_reformed",
    "jxp_path_kaikyo",
    "jxp_path_ikko",
    "jxp_path_wokou",
    "jxp_path_buddhist",
    "jxp_24_house_path_completed",
    "jxp_24_unification_by_blade",
    "jxp_24_unification_by_edict",
    "jxp_24_unification_by_league",
    "jxp_24_warrior_agenda_rolls",
    "jxp_24_warrior_agenda_captains",
    "jxp_24_court_agenda_ranks",
    "jxp_24_court_agenda_stewards",
    "jxp_24_maritime_agenda_merchants",
    "jxp_24_maritime_agenda_ship_rolls",
    "jxp_24_frontier_agenda_wardens",
    "jxp_24_frontier_agenda_brokers",
    "jxp_24_temple_agenda_privileges",
    "jxp_24_temple_agenda_ledgers",
    "jxp_toyotomi_identity_established",
    "jxp_hakko_ichiu_reform_passed",
    "jxp_mandate_claimed",
    "jxp_mandate_broken",
    "jxp_mandate_claim_fallback",
    "jxp_pacific_charter_enacted",
    "jxp_alaska_survey_seen",
    "jxp_california_anchorages_seen",
    "jxp_pacific_silver_flow_done",
    "jxp_new_world_japan_towns_done",
}

PACIFIC_STAGE_TOOLTIPS = {
    "jxp_pacific_stage_gateway_tt",
    "jxp_pacific_stage_manila_tt",
    "jxp_pacific_stage_admiralty_tt",
    "jxp_pacific_stage_north_charts_tt",
    "jxp_pacific_stage_new_world_tt",
}


def _load_escaper():
    spec = importlib.util.spec_from_file_location("_jxp_content_escaper", ESCAPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load localisation escaper: {ESCAPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _block(text: str, key: str) -> str:
    start = text.index(f"{key} = {{")
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unterminated block: {key}")


def _localisation_entries(root: Path, directory: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for path in (root / directory).rglob("*.yml"):
        text = path.read_text(encoding="utf-8-sig")
        entries.update(LOCALISATION_ENTRY.findall(text))
    return entries


def _player_visible_jxp_flags() -> set[str]:
    flags: set[str] = set()
    for root in (MAIN_ROOT, MAP_ROOT):
        for relative in PLAYER_VISIBLE_FLAG_LOCATIONS:
            directory = root / relative
            if not directory.exists():
                continue
            for path in directory.rglob("*.txt"):
                for line in path.read_bytes().splitlines():
                    code = line.split(b"#", 1)[0]
                    for match in FLAG_REFERENCE.findall(code):
                        key = match.decode("ascii")
                        if key.startswith("jxp_"):
                            flags.add(key)
        event_root = root / "events"
        if event_root.exists():
            for path in event_root.rglob("*.txt"):
                code = b"\n".join(
                    line.split(b"#", 1)[0]
                    for line in path.read_bytes().splitlines()
                )
                stack: list[bytes] = []
                for match in EVENT_STRUCTURE_TOKEN.finditer(code):
                    if match.group(1):
                        stack.append(match.group(1))
                    elif match.group(2) == b"{":
                        stack.append(b"{")
                    elif match.group(2) == b"}":
                        if stack:
                            stack.pop()
                    elif (
                        match.group(3)
                        and stack[-2:] == [b"option", b"trigger"]
                        and match.group(3).startswith(b"jxp_")
                    ):
                        flags.add(match.group(3).decode("ascii"))
    return flags


def _defined_jxp_reforms() -> set[str]:
    reforms: set[str] = set()
    reform_root = MAIN_ROOT / "common" / "government_reforms"
    for path in reform_root.glob("*.txt"):
        reforms.update(
            REFORM_DEFINITION.findall(path.read_text(encoding="utf-8-sig"))
        )
    return reforms


class PlaytestContentClarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.escaper = _load_escaper()

    def assert_generated_pair(self, source_relative: str, active_relative: str) -> None:
        source = MAIN_ROOT / source_relative
        active = MAIN_ROOT / active_relative
        expected = self.escaper.escape_text(
            source.read_text(encoding="utf-8-sig")
        ).encode("utf-8-sig")
        self.assertEqual(expected, active.read_bytes())

    def test_daimyo_administration_rewards_are_layered(self) -> None:
        modifiers = (
            MAIN_ROOT
            / "common"
            / "event_modifiers"
            / "jxp_40_mission_expansion_modifiers.txt"
        ).read_text(encoding="utf-8-sig")
        province_code = _block(modifiers, "jxp_24_daimyo_province_code")
        town_magistrates = _block(modifiers, "jxp_24_daimyo_town_magistrates")
        household_council = _block(modifiers, "jxp_24_daimyo_household_council")

        self.assertIn("state_maintenance_modifier = -0.05", province_code)
        self.assertNotIn("governing_capacity_modifier", province_code)
        self.assertIn("governing_capacity_modifier = 0.05", town_magistrates)
        self.assertIn("governing_capacity_modifier = 0.10", household_council)

        prose = (
            MAIN_ROOT
            / "localisation_source"
            / "jxp_40_mission_expansion_l_english_utf8_source.yml"
        ).read_text(encoding="utf-8-sig")
        for phrase in ("新附郡乡", "新领与旧臣", "扩张后的案牍"):
            self.assertIn(phrase, prose)

    def test_player_visible_mission_flags_have_generated_chinese_labels(self) -> None:
        source_relative = (
            "localisation_source/"
            "jxp_82_player_status_labels_l_english_utf8_source.yml"
        )
        active_relative = "localisation/jxp_82_player_status_labels_l_english.yml"
        source = (MAIN_ROOT / source_relative).read_text(encoding="utf-8-sig")
        active = (MAIN_ROOT / active_relative).read_text(encoding="utf-8-sig")
        self.assertTrue(VISIBLE_FLAG_KEYS <= set(LOCALISATION_KEY.findall(source)))
        self.assertTrue(VISIBLE_FLAG_KEYS <= set(LOCALISATION_KEY.findall(active)))
        self.assert_generated_pair(source_relative, active_relative)

    def test_all_player_visible_jxp_flags_have_generated_chinese_labels(self) -> None:
        flags = _player_visible_jxp_flags()
        source_entries = {
            **_localisation_entries(MAIN_ROOT, "localisation_source"),
            **_localisation_entries(MAP_ROOT, "localisation_source"),
        }
        active_entries = {
            **_localisation_entries(MAIN_ROOT, "localisation"),
            **_localisation_entries(MAP_ROOT, "localisation"),
        }

        self.assertGreater(len(flags), 400)
        self.assertEqual(set(), flags - source_entries.keys())
        self.assertEqual(set(), flags - active_entries.keys())
        for flag in flags:
            self.assertRegex(source_entries[flag], r"[\u3400-\u9fff]", flag)

        self.assert_generated_pair(
            "localisation_source/jxp_85_ui_flag_labels_l_english_utf8_source.yml",
            "localisation/jxp_85_ui_flag_labels_l_english.yml",
        )

    def test_japanese_reform_display_names_are_unique(self) -> None:
        reforms = _defined_jxp_reforms()
        source_entries = _localisation_entries(MAIN_ROOT, "localisation_source")
        missing = reforms - source_entries.keys()
        duplicate_names: dict[str, list[str]] = {}
        for reform in reforms - missing:
            duplicate_names.setdefault(source_entries[reform], []).append(reform)
        duplicate_names = {
            name: sorted(keys)
            for name, keys in duplicate_names.items()
            if len(keys) > 1
        }

        self.assertGreater(len(reforms), 400)
        self.assertEqual(set(), missing)
        self.assertEqual({}, duplicate_names)
        for stem in (
            "jxp_37_route_special_reforms",
            "jxp_40_route_grand_reforms",
            "jxp_44_route_program_reforms",
        ):
            self.assert_generated_pair(
                f"localisation_source/{stem}_l_english_utf8_source.yml",
                f"localisation/{stem}_l_english.yml",
            )

    def test_pacific_missions_explain_stages_and_long_term_loop(self) -> None:
        missions = (
            MAIN_ROOT / "missions" / "jxp_03_overseas_missions.txt"
        ).read_text(encoding="utf-8-sig")
        mission_source = (
            MAIN_ROOT
            / "localisation_source"
            / "jxp_03_l_english_utf8_source.yml"
        ).read_text(encoding="utf-8-sig")
        for tooltip in PACIFIC_STAGE_TOOLTIPS:
            self.assertEqual(1, missions.count(f"custom_tooltip = {tooltip}"))
            self.assertIn(f" {tooltip}:0 ", mission_source)

        decisions = (
            MAIN_ROOT / "decisions" / "jxp_76_overseas_loop_decisions.txt"
        ).read_text(encoding="utf-8-sig")
        loop_source = (
            MAIN_ROOT
            / "localisation_source"
            / "jxp_76_overseas_loop_l_english_utf8_source.yml"
        ).read_text(encoding="utf-8-sig")
        self.assertIn(
            "custom_tooltip = jxp_76_pacific_network_scope_tt", decisions
        )
        self.assertIn(" jxp_76_pacific_network_scope_tt:0 ", loop_source)
        self.assert_generated_pair(
            "localisation_source/jxp_03_l_english_utf8_source.yml",
            "localisation/jxp_03_l_english.yml",
        )
        self.assert_generated_pair(
            "localisation_source/jxp_76_overseas_loop_l_english_utf8_source.yml",
            "localisation/jxp_76_overseas_loop_l_english.yml",
        )

    def test_pacific_charter_has_no_diplomatic_technology_gate(self) -> None:
        decisions = (
            MAIN_ROOT / "decisions" / "jxp_03_overseas_decisions.txt"
        ).read_text(encoding="utf-8-sig")
        decision = _block(decisions, "jxp_decision_charter_pacific")
        self.assertNotIn("dip_tech", decision)
        for requirement in (
            "dip_power = 100",
            "treasury = 200",
            "num_of_ports = 8",
            "jxp_oceanic_opening_at_least_60 = yes",
            "num_of_colonists = 1",
            "has_country_flag = jxp_manila_nagasaki_route_seen",
            "has_country_modifier = jxp_pacific_waystations",
        ):
            self.assertIn(requirement, decision)

        missions = (
            MAIN_ROOT / "missions" / "jxp_03_overseas_missions.txt"
        ).read_text(encoding="utf-8-sig")
        mission = _block(missions, "jxp_mission_pacific_charter")
        self.assertNotIn("dip_tech", mission)
        for requirement in (
            "mission_completed = jxp_mission_eastasia_ryukyu_gateway",
            "mission_completed = jxp_mission_open_nagasaki",
            "num_of_ports = 8",
            "jxp_oceanic_opening_at_least_60 = yes",
        ):
            self.assertIn(requirement, mission)
