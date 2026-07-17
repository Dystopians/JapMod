from __future__ import annotations

import base64
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
GENERATOR_PATH = SCRIPT_DIR / "generate_visualizer.py"
HTML_PATH = SCRIPT_DIR / "jxp_visualizer.html"
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
COMPANION_ROOT = MOD_ROOT.parent / "japan_expanded_v2_map"

SPEC = importlib.util.spec_from_file_location("jxp_visualizer_generator", GENERATOR_PATH)
assert SPEC and SPEC.loader
VIZ = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VIZ
SPEC.loader.exec_module(VIZ)


EXPECTED_REFORMS = {
    "jxp_reform_final_uncommitted_consensus": (
        "jxp_final_state_uncommitted_trigger",
        [("all_estate_loyalty_equilibrium", "0.05"), ("reform_progress_growth", "0.10")],
    ),
    "jxp_reform_final_sakoku_constitution": (
        "jxp_final_state_sakoku_trigger",
        [("global_unrest", "-1"), ("max_absolutism", "5")],
    ),
    "jxp_reform_final_open_cabinet": (
        "jxp_final_state_open_trigger",
        [("possible_policy", "1"), ("free_policy", "1")],
    ),
    "jxp_reform_final_kirishitan_estates": (
        "jxp_final_state_kirishitan_trigger",
        [("church_loyalty_modifier", "0.10"), ("burghers_loyalty_modifier", "0.05")],
    ),
    "jxp_reform_final_confucian_censorate": (
        "jxp_final_state_confucian_trigger",
        [("yearly_corruption", "-0.05"), ("reform_progress_growth", "0.10")],
    ),
    "jxp_reform_final_imperial_daijokan": (
        "jxp_final_state_imperial_trigger",
        [("max_absolutism", "10"), ("yearly_absolutism", "0.5")],
    ),
    "jxp_reform_final_reformed_synod": (
        "jxp_final_state_reformed_trigger",
        [("burghers_loyalty_modifier", "0.10"), ("global_institution_spread", "0.10")],
    ),
    "jxp_reform_final_kaikyo_diwan": (
        "jxp_final_state_kaikyo_trigger",
        [("trade_steering", "0.10"), ("caravan_power", "0.15")],
    ),
    "jxp_reform_final_ikko_somon": (
        "jxp_final_state_ikko_trigger",
        [("all_estate_loyalty_equilibrium", "0.05"), ("global_unrest", "-1")],
    ),
    "jxp_reform_final_wokou_admiralty": (
        "jxp_final_state_wokou_trigger",
        [("navy_tradition", "0.5"), ("global_ship_recruit_speed", "-0.10")],
    ),
}

EXPECTED_POWER_STRUCTURES = {
    "jxp_final_state_uncommitted_trigger": (
        "jxp_uncommitted_realm_council_reform",
        "jxp_82_eoc_uncommitted_power_structure",
        [("governing_capacity_modifier", "0.10"), ("advisor_cost", "-0.05"), ("stability_cost_modifier", "-0.05")],
    ),
    "jxp_final_state_sakoku_trigger": (
        "jxp_sakoku_bakuhan_council_reform",
        "jxp_82_eoc_sakoku_power_structure",
        [("global_unrest", "-1"), ("global_spy_defence", "0.10"), ("state_maintenance_modifier", "-0.10")],
    ),
    "jxp_final_state_open_trigger": (
        "jxp_open_maritime_cabinet_reform",
        "jxp_82_eoc_open_power_structure",
        [("trade_efficiency", "0.10"), ("global_ship_trade_power", "0.10"), ("diplomatic_reputation", "1")],
    ),
    "jxp_final_state_kirishitan_trigger": (
        "jxp_kirishitan_estates_general_reform",
        "jxp_82_eoc_kirishitan_power_structure",
        [("papal_influence", "1"), ("global_missionary_strength", "0.01"), ("tolerance_own", "1")],
    ),
    "jxp_final_state_confucian_trigger": (
        "jxp_confucian_censorate_reform",
        "jxp_82_eoc_confucian_power_structure",
        [("harmonization_speed", "0.15"), ("idea_cost", "-0.05"), ("advisor_cost", "-0.05")],
    ),
    "jxp_final_state_imperial_trigger": (
        "jxp_imperial_daijokan_reform",
        "jxp_82_eoc_imperial_power_structure",
        [("legitimacy", "1"), ("global_autonomy", "-0.03"), ("diplomatic_reputation", "1")],
    ),
    "jxp_final_state_reformed_trigger": (
        "jxp_reformed_japan_reform",
        "jxp_82_eoc_reformed_power_structure",
        [("global_trade_power", "0.05"), ("tolerance_heretic", "1"), ("church_power_modifier", "0.10")],
    ),
    "jxp_final_state_kaikyo_trigger": (
        "jxp_kaikyo_japan_reform",
        "jxp_82_eoc_kaikyo_power_structure",
        [("global_trade_power", "0.05"), ("tolerance_heathen", "1"), ("global_sailors_modifier", "0.10")],
    ),
    "jxp_final_state_ikko_trigger": (
        "jxp_ikko_commonwealth_reform",
        "jxp_82_eoc_ikko_power_structure",
        [("global_manpower_modifier", "0.10"), ("production_efficiency", "0.05"), ("stability_cost_modifier", "-0.05")],
    ),
    "jxp_final_state_wokou_trigger": (
        "jxp_wokou_admiralty_reform",
        "jxp_82_eoc_wokou_power_structure",
        [("privateer_efficiency", "0.20"), ("naval_forcelimit_modifier", "0.15"), ("trade_efficiency", "0.05")],
    ),
}


def flatten_tip_texts(tips: list[dict]) -> list[str]:
    result: list[str] = []
    for tip in tips:
        result.append(tip["text"])
        result.extend(flatten_tip_texts(tip.get("children", [])))
    return result


class VisualizerGovernmentReformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = VIZ.build_data(MOD_ROOT, GAME_ROOT)
        cls.reforms = {reform["id"]: reform for reform in cls.data["finalStateReforms"]}

    def test_final_state_reforms_are_structured_and_exact(self) -> None:
        self.assertEqual(set(self.reforms), set(EXPECTED_REFORMS))
        self.assertEqual(self.data["counts"]["finalStateReforms"], 10)
        self.assertEqual(self.data["counts"]["finalStatePowerStructures"], 10)
        self.assertEqual(self.data["counts"]["finalStateEocModifiers"], 10)
        self.assertEqual(self.data["warnings"], [])
        for reform_id, (state_trigger, expected_modifiers) in EXPECTED_REFORMS.items():
            with self.subTest(reform=reform_id):
                reform = self.reforms[reform_id]
                self.assertEqual(reform["tier"], "absolute_rule_vs_constitutional")
                self.assertEqual(reform["stateTrigger"], state_trigger)
                self.assertTrue(reform["title"] and reform["title"] != reform_id)
                self.assertTrue(reform["desc"])
                self.assertEqual(
                    [(entry["id"], entry["value"]) for entry in reform["modifierEntries"]],
                    expected_modifiers,
                )
                self.assertEqual(len(reform["modifierTips"]), 2)

                potential_text = "\n".join(flatten_tip_texts(reform["potentialTips"]))
                trigger_text = "\n".join(flatten_tip_texts(reform["triggerTips"]))
                self.assertIn(reform["stateLabel"], potential_text)
                self.assertIn(reform["stateLabel"], trigger_text)
                self.assertIn(reform["title"], potential_text)

                prefix = "data:image/png;base64,"
                self.assertTrue(reform["iconDataUri"].startswith(prefix))
                png = base64.b64decode(reform["iconDataUri"][len(prefix):], validate=True)
                self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_power_structures_and_eoc_mirrors_are_exact(self) -> None:
        for reform in self.reforms.values():
            state_trigger = reform["stateTrigger"]
            with self.subTest(state=state_trigger):
                expected_power, expected_eoc, expected_modifiers = EXPECTED_POWER_STRUCTURES[state_trigger]
                power = reform["powerStructure"]
                eoc = reform["eocPowerModifier"]
                power_signature = [(entry["id"], entry["value"]) for entry in power["modifierEntries"]]
                eoc_signature = [(entry["id"], entry["value"]) for entry in eoc["modifierEntries"]]

                self.assertEqual(power["id"], expected_power)
                self.assertEqual(power["tier"], "feudalism_vs_autocracy")
                self.assertEqual(eoc["id"], expected_eoc)
                self.assertEqual(eoc["identity"], "celestial_empire")
                self.assertEqual(eoc["identityTitle"], "天朝政体")
                self.assertEqual(power_signature, expected_modifiers)
                self.assertEqual(eoc_signature, expected_modifiers)
                self.assertTrue(eoc["mirrorMatches"])
                self.assertEqual(eoc["mirrorMatchedCount"], 3)
                self.assertEqual(eoc["mirrorExpectedCount"], 3)

                power_potential = "\n".join(flatten_tip_texts(power["potentialTips"]))
                power_active = "\n".join(flatten_tip_texts(power["powerActiveTips"]))
                eoc_potential = "\n".join(flatten_tip_texts(eoc["potentialTips"]))
                self.assertIn(reform["stateLabel"], power_potential)
                self.assertIn("不是中华天子", power_potential)
                self.assertIn("不是中华天子", power_active)
                self.assertIn("是中华天子", power_active)
                self.assertIn("天朝政体", power_active)
                self.assertIn(reform["stateLabel"], eoc_potential)
                self.assertIn("是中华天子", eoc_potential)
                self.assertIn("天朝政体", eoc_potential)

                prefix = "data:image/png;base64,"
                self.assertTrue(power["iconDataUri"].startswith(prefix))
                png = base64.b64decode(power["iconDataUri"][len(prefix):], validate=True)
                self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_add_remove_reform_effects_use_localised_names(self) -> None:
        added_id = "jxp_reform_final_confucian_censorate"
        removed_id = "jxp_reform_final_wokou_admiralty"
        fallback_ids = (
            "military_dictatorship_reform",
            "presidential_despot_reform",
            "quash_noble_power_reform",
        )
        script = VIZ.Parser(
            VIZ.tokenize(
                f"add_government_reform = {added_id}\n"
                f"remove_government_reform = {removed_id}\n"
                f"add_government_reform = {fallback_ids[0]}\n"
                f"remove_government_reform = {fallback_ids[1]}\n"
                f"add_government_reform = {fallback_ids[2]}\n"
            ),
            Path("<visualizer-test>"),
        ).parse()
        ctx = VIZ.VisualContext(
            loc={
                added_id: "经世监察政治",
                removed_id: "海军府联邦政治",
            },
            modifiers={},
            scripted_effects={},
            scripted_triggers={},
            province_names={},
        )
        texts = flatten_tip_texts(VIZ.summarize_script(script, ctx, "effect"))
        self.assertEqual(texts, [
            "采用政府改革：经世监察政治",
            "移除政府改革：海军府联邦政治",
            "采用政府改革：军事独裁制",
            "移除政府改革：总统独裁制",
            "采用政府改革：限制贵族特权",
        ])
        self.assertNotIn(added_id, "\n".join(texts))
        self.assertNotIn(removed_id, "\n".join(texts))
        for fallback_id in fallback_ids:
            self.assertNotIn(fallback_id, "\n".join(texts))

    def test_route_flags_have_stable_chinese_labels(self) -> None:
        script = VIZ.Parser(
            VIZ.tokenize(
                "OR = {\n"
                + "".join(f"has_country_flag = {flag}\n" for flag in VIZ.COUNTRY_FLAG_LABELS)
                + "}\n"
            ),
            Path("<visualizer-route-flag-test>"),
        ).parse()
        ctx = VIZ.VisualContext(
            loc={},
            modifiers={},
            scripted_effects={},
            scripted_triggers={},
            province_names={},
        )
        text = "\n".join(flatten_tip_texts(VIZ.summarize_script(script, ctx, "trigger")))
        for flag, label in VIZ.COUNTRY_FLAG_LABELS.items():
            self.assertIn(label, text)
            self.assertNotIn(flag, text)
        self.assertNotIn("Path sakoku", text)
        self.assertNotIn("Path open trade", text)

    def test_png_embedding_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.png"
            with self.assertRaises(FileNotFoundError):
                VIZ.png_data_uri(missing, "jxp_reform_final_test")
            invalid = Path(temp_dir) / "invalid.png"
            invalid.write_bytes(b"not a png")
            with self.assertRaises(ValueError):
                VIZ.png_data_uri(invalid, "jxp_reform_final_test")

    def test_companion_root_does_not_require_main_reform_source(self) -> None:
        data = VIZ.build_data(COMPANION_ROOT, GAME_ROOT)
        self.assertEqual(data["finalStateReforms"], [])
        self.assertEqual(data["counts"]["finalStateReforms"], 0)
        self.assertFalse(
            any("Missing final-state reform source" in warning for warning in data["warnings"]),
            data["warnings"],
        )

    def test_generated_html_contains_review_surface(self) -> None:
        page = HTML_PATH.read_text(encoding="utf-8")
        for reform_id in EXPECTED_REFORMS:
            self.assertIn(reform_id, page)
        for power_id, eoc_id, _ in EXPECTED_POWER_STRUCTURES.values():
            self.assertIn(power_id, page)
            self.assertIn(eoc_id, page)
        for expected_text in (
            "朱子礼制日本（CJP）",
            "一向宗共和国（IJP）",
            "倭寇联邦（WAK）",
            "jxp_debug_80_refresh_final_state_reforms",
            "采用政府改革：",
            "移除政府改革：",
            "权力结构双态合同",
            "非天朝：路线一级权力结构",
            "天朝：保留 celestial_empire 的等价层",
            "天朝身份：",
            '"identityTitle": "天朝政体"',
            "不是中华天子",
            "数值镜像已验证 ",
            "数值不一致 ",
            '["reforms", "政府改革"]',
            "const selected = filtered.find(reform => reform.id === state.reform) || filtered[0];",
        ):
            self.assertIn(expected_text, page)
        self.assertEqual(page.count("data:image/png;base64,"), 20)
        self.assertNotIn("../../gfx/interface/government_reform_icons/source/previews/icons/", page)
        self.assertNotIn("Government reform：jxp_reform_final_", page)
        self.assertNotIn("Path sakoku", page)
        self.assertNotIn("Path open trade", page)
        self.assertNotIn(
            "DATA.finalStateReforms.find(reform => reform.id === state.reform) || filtered[0]",
            page,
        )


if __name__ == "__main__":
    unittest.main()
