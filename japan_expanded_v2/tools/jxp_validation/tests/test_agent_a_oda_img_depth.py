from __future__ import annotations

from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"


def object_block(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if match is None:
        raise AssertionError(f"missing object {key}")
    start = match.start()
    depth = 0
    opened = False
    for index in range(match.end() - 1, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
            opened = True
        elif char == "}":
            depth -= 1
            if opened and depth == 0:
                return text[start:index + 1]
    raise AssertionError(f"unterminated object {key}")


def mission_positions(block: str, prefix: str) -> list[int]:
    positions: list[int] = []
    for match in re.finditer(rf"(?m)^\s+({re.escape(prefix)}[a-z0-9_]+)\s*=\s*\{{", block):
        mission = object_block(block[match.start():], match.group(1))
        position = re.search(r"(?m)^\s*position\s*=\s*(\d+)", mission)
        if position:
            positions.append(int(position.group(1)))
    return positions


class AgentAOdaImagawaDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.depth_missions = (MAIN_ROOT / "missions" / "jxp_a_91_oda_img_depth_missions.txt").read_text(encoding="utf-8")
        cls.oda_missions = (MAIN_ROOT / "missions" / "jxp_70_oda_toyotomi_missions.txt").read_text(encoding="utf-8")
        cls.major_missions = (MAIN_ROOT / "missions" / "jxp_81_major_daimyo_identity_missions.txt").read_text(encoding="utf-8")
        cls.events = (MAIN_ROOT / "events" / "jxp_a_91_oda_img_depth_events.txt").read_text(encoding="utf-8")

    def test_exact_mission_counts_and_safe_five_column_terminals(self) -> None:
        oda_new = set(re.findall(r"(?m)^\s+(jxp_a_mission_oda_[a-z0-9_]+)\s*=", self.depth_missions))
        img_new = set(re.findall(r"(?m)^\s+(jxp_a_mission_img_[a-z0-9_]+)\s*=", self.depth_missions))
        img_generated = set(re.findall(r"(?m)^\s+(jxp_mission_img_[a-z0-9_]+)\s*=", object_block(self.major_missions, "jxp_img_identity_missions")))
        self.assertEqual(16, len(oda_new))
        self.assertEqual(9, len(img_new))
        self.assertEqual(8, len(img_generated))
        self.assertEqual(19, 3 + len(oda_new))
        self.assertEqual(17, len(img_new | img_generated))

        oda_slot2 = mission_positions(object_block(self.depth_missions, "jxp_a_oda_government_missions"), "jxp_a_mission_oda_")
        oda_slot4 = mission_positions(object_block(self.depth_missions, "jxp_a_oda_settlement_missions"), "jxp_a_mission_oda_")
        img_slot2 = mission_positions(object_block(self.depth_missions, "jxp_a_img_law_missions"), "jxp_a_mission_img_")
        img_slot4 = mission_positions(object_block(self.depth_missions, "jxp_a_img_diplomacy_missions"), "jxp_a_mission_img_")
        self.assertEqual(list(range(2, 17, 2)), oda_slot2)
        self.assertEqual(list(range(2, 17, 2)), oda_slot4)
        self.assertEqual(list(range(2, 11, 2)), img_slot2)
        self.assertEqual(list(range(4, 11, 2)), img_slot4)
        self.assertLessEqual(max((11, max(oda_slot2), 11, max(oda_slot4), 11)) - min((11, max(oda_slot2), 11, max(oda_slot4), 11)), 5)
        self.assertLessEqual(max((11, max(img_slot2), 15, max(img_slot4), 11)) - min((11, max(img_slot2), 15, max(img_slot4), 11)), 5)

    def test_inactive_public_slot_dependencies_are_absent(self) -> None:
        oda_exact = object_block(self.oda_missions, "jxp_oda_toyotomi_house_missions")
        img_exact = object_block(self.major_missions, "jxp_img_identity_missions")
        inactive = (
            "jxp_mission_daimyo_market_roads",
            "jxp_mission_daimyo_artisan_guilds",
            "jxp_mission_daimyo_foreign_letters",
            "jxp_mission_daimyo_licensed_caravans",
            "jxp_mission_daimyo_shrine_village_compact",
            "jxp_mission_daimyo_town_magistrates",
            "jxp_mission_daimyo_people_of_the_domain",
        )
        for mission_id in inactive:
            self.assertNotIn(mission_id, oda_exact)
            self.assertNotIn(mission_id, img_exact)
        self.assertIn("has_country_flag = jxp_a_oda_succession_toyotomi", oda_exact)

    def test_events_are_bounded_and_do_not_force_historical_deaths(self) -> None:
        ids = set(int(value) for value in re.findall(r"id\s*=\s*jxp_daimyo_depth\.(\d+)", self.events))
        self.assertTrue(set(range(1, 9)) <= ids)
        self.assertTrue(set(range(101, 109)) <= ids)
        self.assertIn(190, ids)
        self.assertNotRegex(self.events, r"\bkill_(?:ruler|leader)\b")
        succession = self.events[self.events.index("id = jxp_daimyo_depth.8"):self.events.index("id = jxp_daimyo_depth.101")]
        okehazama = self.events[self.events.index("id = jxp_daimyo_depth.108"):self.events.index("id = jxp_daimyo_depth.190")]
        self.assertEqual(4, len(re.findall(r"(?m)^\s*option\s*=", succession)))
        self.assertEqual(4, len(re.findall(r"(?m)^\s*option\s*=", okehazama)))

    def test_dynamic_alliance_fallback_and_interface_flags(self) -> None:
        triggers = (MAIN_ROOT / "common" / "scripted_triggers" / "jxp_a_91_oda_img_depth_triggers.txt").read_text(encoding="utf-8")
        effects = (MAIN_ROOT / "common" / "scripted_effects" / "jxp_a_91_oda_img_depth_effects.txt").read_text(encoding="utf-8")
        self.assertIn("TKD = { exists = yes }", triggers)
        self.assertIn("HJO = { exists = yes }", triggers)
        self.assertIn("NOT = {", triggers)
        self.assertIn("culture_group = japanese_g", triggers)
        self.assertIn("is_neighbor_of = ROOT", triggers)
        self.assertNotIn("set_country_flag = jxp_iface_", self.events + self.depth_missions)
        for capability in ("government", "diplomacy", "logistics", "mass_mobilization"):
            flag = f"jxp_iface_house_{capability}_ready"
            helper = f"jxp_a_mark_house_{capability}_ready_effect"
            self.assertIn(flag, effects)
            self.assertIn(f"{helper} = yes", self.events + self.depth_missions)

    def test_three_oda_reforms_are_registered_once_in_one_level(self) -> None:
        reforms = (MAIN_ROOT / "common" / "government_reforms" / "jxp_a_91_oda_government_reforms.txt").read_text(encoding="utf-8")
        governments = (MAIN_ROOT / "common" / "governments" / "00_governments.txt").read_text(encoding="utf-8")
        level = object_block(governments, "absolute_rule_vs_constitutional")
        for reform in (
            "jxp_a_oda_azuchi_magistracy_reform",
            "jxp_a_oda_legion_domains_reform",
            "jxp_a_oda_ashikaga_protectorate_reform",
        ):
            self.assertEqual(1, len(re.findall(rf"(?m)^{re.escape(reform)}\s*=", reforms)))
            self.assertEqual(1, len(re.findall(rf"(?m)^\s*{re.escape(reform)}\s*$", governments)))
            self.assertIn(reform, level)
        self.assertIn("remove_government_reform", (MAIN_ROOT / "common" / "scripted_effects" / "jxp_a_91_oda_img_depth_effects.txt").read_text(encoding="utf-8"))

    def test_active_localisation_is_bom_escaped(self) -> None:
        active = (MAIN_ROOT / "localisation" / "jxp_a_91_oda_img_depth_l_english.yml").read_bytes()
        self.assertTrue(active.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn("清洲".encode("utf-8"), active)
        source = (MAIN_ROOT / "localisation_source" / "jxp_a_91_oda_img_depth_l_english_utf8_source.yml").read_text(encoding="utf-8")
        self.assertIn("清洲裁断", source)


if __name__ == "__main__":
    unittest.main()
