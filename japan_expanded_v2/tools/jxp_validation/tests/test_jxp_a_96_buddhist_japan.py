from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import sys
import unittest

from jxp_validation.clausewitz import parse_text


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
BUILDER_ROOT = MAIN_ROOT / "tools" / "jxp_a_content_builder"
sys.path.insert(0, str(BUILDER_ROOT))
try:
    import jxp_a_96_buddhist_builder as builder
finally:
    sys.path.remove(str(BUILDER_ROOT))


EXPECTED_MISSION_TITLES = (
    "南都伽蓝",
    "比叡山安堵",
    "高野山参诣",
    "京都诸寺修复",
    "五山名籍",
    "神佛习合之议",
    "寺社奉行",
    "寺领检地",
    "免税地名簿",
    "僧兵军役",
    "勧进与普请",
    "王法与佛法",
    "召开诸宗评议",
    "天台真言席",
    "禅林五山席",
    "净土真宗席",
    "法华宗席",
    "南都旧宗席",
    "诸宗和议",
    "版木与经卷",
    "学寮与寺子教育",
    "施药院",
    "义仓与饥馑救济",
    "参诣道路",
    "僧侣文书官",
    "町众与寺院信用",
    "朝鲜经卷",
    "中华僧侣往来",
    "琉球法灯",
    "南海佛寺网络",
    "四海法灯",
    "佛国之宪",
)

EXPECTED_CRISES = {
    "寺领检地危机",
    "僧兵拒绝解散",
    "法华与净土冲突",
    "大寺院与地方坊舍竞争",
    "国家任命住持",
    "经卷版本争议",
    "神佛习合与排佛倾向",
    "净土真宗自治危机",
    "町众支持某宗派",
    "寺院债务和德政",
}


def _event_block(text: str, event_id: int) -> str:
    marker = f"\tid = jxp_buddhist_state.{event_id}\n"
    return text.split(marker, 1)[1].split("\n}\n", 1)[0]


class BuddhistJapanRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = builder.render_outputs()
        cls.gameplay = "\n".join(
            payload
            for path, payload in cls.outputs.items()
            if isinstance(payload, str)
            and path.suffix == ".txt"
            and "localisation" not in path.parts
        )

    def test_exact_thirty_two_authored_missions_preserve_only_frozen_runtime_columns(self) -> None:
        builder.validate_design()
        self.assertEqual(EXPECTED_MISSION_TITLES, tuple(mission.title for mission in builder.MISSIONS))
        self.assertEqual(
            {1: 6, 2: 6, 3: 7, 4: 7, 5: 6},
            Counter(mission.slot for mission in builder.MISSIONS),
        )
        for slot in range(1, 6):
            rows = [
                mission.position
                for mission in builder.MISSIONS
                if mission.slot == slot
            ]
            self.assertEqual(list(range(rows[0], rows[-1] + 1, 2)), rows)
            self.assertTrue(all(row % 2 == (slot % 2) for row in rows))

        missions = builder.render_missions()
        self.assertEqual((4, 5), builder.RUNTIME_MISSION_SLOTS)
        self.assertEqual(2, missions.count("tag = JAP"))
        self.assertEqual(2, missions.count(f"has_country_flag = {builder.ROUTE_FLAG}"))
        for slot in (1, 2, 3):
            self.assertNotIn(f"jxp_a_96_buddhist_slot_{slot}_missions", missions)
        for slot in builder.RUNTIME_MISSION_SLOTS:
            self.assertEqual(1, missions.count(f"jxp_a_96_buddhist_slot_{slot}_missions"))
        for flag in builder.OTHER_ROUTE_FLAGS:
            self.assertEqual(2, missions.count(f"has_country_flag = {flag}"), flag)

    def test_generated_outputs_are_byte_current_and_clausewitz_parseable(self) -> None:
        self.assertEqual(10, len(self.outputs))
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

    def test_entry_is_unified_japan_and_buddhist_or_prepared_shinto_only(self) -> None:
        triggers = builder.render_triggers()
        decisions = builder.render_decisions()
        for religion in ("buddhism", "vajrayana", "mahayana", "jodo_shinshu"):
            self.assertIn(f"religion = {religion}", triggers)
        self.assertIn("religion = shinto", triggers)
        self.assertIn("has_country_flag = jxp_a_buddhist_shinbutsu_prepared", triggers)
        self.assertIn("jxp_is_unified_japan_state_trigger = yes", triggers)
        self.assertIn("owns = 1020", triggers)
        self.assertIn("jxp_clear_all_route_flags_effect = yes", decisions)
        self.assertIn("set_country_flag = jxp_path_buddhist", decisions)
        self.assertIn(
            f"override_country_name = {builder.DYNAMIC_NAME}",
            decisions,
        )
        self.assertIn(
            "modifier = { factor = 0 NOT = { adm_power = 250 } }",
            decisions,
        )
        self.assertNotIn("change_tag", self.gameplay)

    def test_dynamic_name_is_applied_reconciled_and_restored_without_a_new_tag(self) -> None:
        decisions = builder.render_decisions()
        effects = builder.render_effects()
        source = builder.render_localisation()
        self.assertIn(f"override_country_name = {builder.DYNAMIC_NAME}", decisions)
        self.assertIn(f"override_country_name = {builder.DYNAMIC_NAME}", effects)
        self.assertIn("set_country_flag = jxp_a_buddhist_dynamic_name_applied", effects)
        self.assertEqual(1, effects.count("restore_country_name = yes"))
        self.assertIn(
            "if = {\n"
            "\t\tlimit = { has_country_flag = jxp_a_buddhist_dynamic_name_applied }\n"
            "\t\trestore_country_name = yes\n"
            "\t}",
            effects,
        )
        self.assertIn(f' {builder.DYNAMIC_NAME}:0 "佛教日本"', source)
        self.assertNotIn("change_tag", decisions + effects)

    def test_five_seats_have_hard_three_seat_cap_and_real_tradeoffs(self) -> None:
        events = builder.render_events()
        self.assertEqual(5, len(builder.SEATS))
        self.assertEqual(
            5,
            events.count(
                "NOT = { check_variable = { which = "
                f"{builder.SEAT_VARIABLE} value = 3 }} }}"
            ),
        )
        self.assertEqual(
            5,
            events.count(
                f"change_variable = {{ which = {builder.SEAT_VARIABLE} value = 1 }}"
            ),
        )
        for index, seat in enumerate(builder.SEATS):
            values = tuple(float(value) for _, value in seat.modifiers)
            self.assertTrue(any(value > 0 for value in values), seat.key)
            self.assertTrue(any(value < 0 for value in values), seat.key)
            block = _event_block(events, 100 + index)
            self.assertEqual(3, block.count("\n\toption = {"))
            for stance in ("recognized", "tolerated", "restricted"):
                self.assertIn(
                    f"has_country_flag = jxp_a_buddhist_seat_{seat.key}_{stance}",
                    block,
                )

    def test_three_finales_and_ten_two_choice_crises_are_complete(self) -> None:
        events = builder.render_events()
        final = _event_block(events, 200)
        self.assertEqual(3, len(builder.FINALES))
        self.assertEqual(3, final.count("\n\toption = {"))
        self.assertEqual(
            (
                "王法佛法相依体制",
                "诸山公议国制",
                "僧俗分治法度",
            ),
            tuple(finale.title for finale in builder.FINALES),
        )
        for finale in builder.FINALES:
            self.assertIn(f"set_country_flag = jxp_a_buddhist_final_{finale.key}", final)
            self.assertIn(
                f"add_government_reform = {finale.reform_id}",
                final,
            )
            self.assertNotIn(
                f"add_country_modifier = {{ name = jxp_a_buddhist_final_{finale.key}",
                final,
            )

        self.assertEqual(EXPECTED_CRISES, {crisis.title for crisis in builder.CRISES})
        for crisis in builder.CRISES:
            block = _event_block(events, crisis.event_id)
            self.assertIn("\tis_triggered_only = yes", block)
            self.assertNotIn("mean_time_to_happen", block)
            self.assertEqual(2, block.count("\n\toption = {"), crisis.title)

    def test_finales_are_real_mutually_exclusive_government_reforms(self) -> None:
        reforms = builder.render_reforms()
        effects = builder.render_effects()
        events = builder.render_events()
        for finale in builder.FINALES:
            self.assertEqual(1, reforms.count(f"\n{finale.reform_id} = {{"))
            self.assertIn(
                f"has_country_flag = jxp_a_buddhist_final_{finale.key}",
                reforms,
            )
            self.assertIn(f"has_reform = {finale.reform_id}", reforms)
            self.assertIn(f"remove_government_reform = {finale.reform_id}", effects)
            self.assertIn(f"add_government_reform = {finale.reform_id}", effects)
            self.assertIn(f"add_government_reform = {finale.reform_id}", events)
        self.assertEqual(3, events.count("add_government_reform = jxp_a_96_buddhist_"))
        self.assertIn("jxp_a_96_reconcile_buddhist_finale_effect = {", effects)
        self.assertIn(
            "jxp_a_96_reconcile_buddhist_finale_effect = yes",
            builder.render_on_actions(),
        )

    def test_only_declared_interface_crosses_the_agent_boundary(self) -> None:
        missions = builder.render_missions()
        self.assertEqual(1, missions.count("jxp_a_mark_buddhist_diplomacy_ready_effect = yes"))
        self.assertNotIn(
            f"set_country_flag = {builder.INTERFACE_FLAG}",
            self.gameplay,
        )
        interface_tokens = set(re.findall(r"\bjxp_iface_[a-z0-9_]+\b", self.gameplay))
        external_capstone = "jxp_iface_b_external_capstone_complete"
        external_private = "jxp_b_115_buddhist_interaction_unlocked"
        self.assertEqual({builder.INTERFACE_FLAG, external_capstone}, interface_tokens)
        self.assertEqual(
            1,
            self.gameplay.count(f"set_country_flag = {external_capstone}"),
        )
        self.assertEqual(
            2,
            self.gameplay.count(f"set_country_flag = {external_private}"),
        )

        flags = re.findall(
            r"(?:set|clr)_country_flag = (jxp_[a-z0-9_]+)",
            self.gameplay,
        )
        self.assertTrue(flags)
        for flag in flags:
            self.assertTrue(
                flag.startswith("jxp_a_")
                or flag in {
                    builder.ROUTE_FLAG,
                    builder.INTERFACE_FLAG,
                    external_capstone,
                    external_private,
                },
                flag,
            )
        variables = set(
            re.findall(
                r"(?:set|change|check)_variable = \{ which = ([a-z0-9_]+)",
                self.gameplay,
            )
        )
        self.assertEqual({builder.SEAT_VARIABLE}, variables)
        for forbidden in (
            "add_permanent_claim",
            "create_subject",
            "jxp_map_",
        ):
            self.assertNotIn(forbidden, self.gameplay)

    def test_public_route_registration_cleanup_and_slot_exclusions_are_wired(self) -> None:
        trigger_text = (
            MAIN_ROOT / "common/scripted_triggers/jxp_scripted_triggers.txt"
        ).read_text(encoding="utf-8-sig")
        effect_text = (
            MAIN_ROOT / "common/scripted_effects/jxp_scripted_effects.txt"
        ).read_text(encoding="utf-8-sig")
        government_text = (
            MAIN_ROOT / "common/governments/00_governments.txt"
        ).read_text(encoding="utf-8-sig")
        state_missions = (
            MAIN_ROOT / "missions/jxp_japan_missions.txt"
        ).read_text(encoding="utf-8-sig")
        shinto_missions = (
            MAIN_ROOT / "missions/jxp_11_branching_missions.txt"
        ).read_text(encoding="utf-8-sig")

        route_trigger = trigger_text.split(
            "jxp_has_any_route_trigger = {", 1
        )[1].split("\n}", 1)[0]
        self.assertEqual(1, route_trigger.count("has_country_flag = jxp_path_buddhist"))
        clear_effect = effect_text.split(
            "jxp_clear_all_route_flags_effect = {", 1
        )[1].split("\n}", 1)[0]
        self.assertEqual(
            1,
            clear_effect.count("jxp_a_96_clear_buddhist_route_effect = yes"),
        )

        tier = government_text.split(
            "absolute_rule_vs_constitutional = {", 1
        )[1].split("\n\t\t}", 1)[0]
        for finale in builder.FINALES:
            self.assertEqual(1, tier.count(finale.reform_id), finale.reform_id)
            self.assertEqual(1, government_text.count(finale.reform_id), finale.reform_id)

        self.assertEqual(
            0,
            state_missions.count(
                "NOT = { has_country_flag = jxp_path_buddhist }"
            ),
        )
        self.assertNotIn("jxp_japan_state_missions = {", state_missions)
        self.assertNotIn("jxp_japan_court_missions = {", state_missions)
        shinto_potential = shinto_missions.split(
            "jxp_shinto_branch_missions = {", 1
        )[1].split("has_country_shield", 1)[0]
        self.assertEqual(
            1,
            shinto_potential.count("has_country_flag = jxp_path_buddhist"),
        )

    def test_source_and_active_localisation_are_complete_and_escaped(self) -> None:
        source_path = (
            MAIN_ROOT
            / "localisation_source"
            / "jxp_a_96_buddhist_l_english_utf8_source.yml"
        )
        active_path = (
            MAIN_ROOT / "localisation" / "jxp_a_96_buddhist_l_english.yml"
        )
        source = source_path.read_text(encoding="utf-8")
        active_bytes = active_path.read_bytes()
        self.assertTrue(active_bytes.startswith(b"\xef\xbb\xbf"))
        self.assertIn("佛教日本国制", source)
        self.assertNotIn("佛教日本国制", active_bytes.decode("utf-8-sig"))
        for mission in builder.MISSIONS:
            self.assertIn(f" {mission.mission_id}_title:0 ", source)
            self.assertIn(f" {mission.mission_id}_desc:0 ", source)


if __name__ == "__main__":
    unittest.main()
