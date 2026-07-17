from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest

from jxp_validation.clausewitz import (
    Object,
    Scalar,
    entries_named,
    first_object,
    first_scalar,
    parse_file,
)


MAIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = MAIN_ROOT.parent
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"

RELIGION_FILE = Path("common/religions/00_religion.txt")
REBEL_FILE = Path("common/rebel_types/jxp_a_95_jodo_shinshu.txt")
SHINSHU_EFFECT_FILE = Path("common/scripted_effects/jxp_a_95_shinshu_effects.txt")
SHINSHU_EVENT_FILE = Path("events/jxp_a_95_shinshu_events.txt")
SHINSHU_DECISION_FILE = Path("decisions/jxp_a_95_shinshu_decisions.txt")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object_scalars(obj: Object | None, key: str) -> set[str]:
    values: set[str] = set()
    if obj is None:
        return values
    for entry in obj.entries:
        if entry.key == key and isinstance(entry.value, Scalar):
            values.add(entry.value.text)
        if isinstance(entry.value, Object):
            values.update(_object_scalars(entry.value, key))
    return values


class ShinshuAndIjpContractTests(unittest.TestCase):
    def test_pinned_religion_registry_and_rebel_output_match_manifest(self) -> None:
        manifest_path = (
            MAIN_ROOT
            / "tools/jxp_religion_builder/generated_religion_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("1.37.5.0", manifest["eu4_version"])
        self.assertEqual(
            "609e2d235f3441c64b895d9faf3927bbf1399149cffa955137ab2d070b9645a6",
            manifest["vanilla_religion_sha256"],
        )
        self.assertEqual(
            "6069db79fd15ecdb7ac69495a3b99d8566a647534ffdf2e4c0838088f666b343",
            manifest["vanilla_mahayana_rebel_sha256"],
        )
        self.assertEqual(23, manifest["temporary_icon_frame"])
        self.assertEqual("PENDING_RUNTIME_MILESTONE", manifest["a12_custom_icon_status"])
        for relative, expected in manifest["outputs"].items():
            self.assertEqual(expected, _sha256(MAIN_ROOT / relative))

        religion = (MAIN_ROOT / RELIGION_FILE).read_text(encoding="cp1252")
        rebel = (MAIN_ROOT / REBEL_FILE).read_text(encoding="cp1252")
        self.assertEqual(1, religion.count("\tjodo_shinshu = {"))
        jodo = religion.split("\tjodo_shinshu = {", 1)[1].split(
            "\tconfucianism = {", 1
        )[0]
        for needle in ("icon = 23", "uses_karma = yes", "mahayana", "shinto"):
            self.assertIn(needle, jodo)
        self.assertIn("jodo_shinshu_rebels", rebel)
        self.assertNotIn("mahayana_rebels", rebel)

    def test_twenty_event_chronicle_and_five_stage_crisis_are_complete(self) -> None:
        document = parse_file(MAIN_ROOT / SHINSHU_EVENT_FILE)
        events: dict[str, Object] = {}
        for entry in entries_named(document.root, "country_event"):
            if isinstance(entry.value, Object):
                event_id = first_scalar(entry.value, "id")
                if event_id is not None:
                    events[event_id] = entry.value

        expected = {f"jxp_shinshu.{index}" for index in range(1, 21)}
        self.assertTrue(expected.issubset(events))
        for event_id in sorted(expected):
            with self.subTest(event_id=event_id):
                self.assertEqual(2, len(entries_named(events[event_id], "option")))

        event_text = (MAIN_ROOT / SHINSHU_EVENT_FILE).read_text(encoding="utf-8-sig")
        for stage in range(1, 6):
            self.assertIn(f"jxp_a_shinshu_set_stage_{stage}_effect = yes", event_text)
        self.assertIn("id = jxp_shinshu.90", event_text)
        self.assertIn("id = jxp_shinshu.190", event_text)
        self.assertIn("modifier = { factor = 100 has_country_flag = jxp_map_origin_hng }", event_text)
        self.assertIn("modifier = { factor = 0.05 NOT = { has_country_flag = jxp_map_origin_hng } }", event_text)
        self.assertIn(
            "add_country_modifier = { name = jxp_a_shinshu_reconciled_order duration = 7300 }",
            event_text,
        )
        self.assertIn(
            "add_country_modifier = { name = jxp_a_shinshu_suppression_aftershock duration = 3650 }",
            event_text,
        )

    def test_unified_militancy_migration_and_terminal_cleanup_are_transactional(self) -> None:
        effects = (MAIN_ROOT / SHINSHU_EFFECT_FILE).read_text(encoding="utf-8-sig")
        legacy_effects = (
            MAIN_ROOT / "common/scripted_effects/jxp_74_ijp_effects.txt"
        ).read_text(encoding="utf-8-sig")
        on_actions = (
            MAIN_ROOT / "common/on_actions/jxp_60_mission_runtime_on_actions.txt"
        ).read_text(encoding="utf-8-sig")

        self.assertIn("jxp_shinshu.90", on_actions)
        self.assertIn("jxp_a_shinshu_migration_postcondition_trigger = yes", effects)
        self.assertLess(
            effects.index("jxp_a_shinshu_migration_postcondition_trigger = yes"),
            effects.index("set_country_flag = jxp_a_shinshu_migration_v029"),
        )
        self.assertEqual(5, effects.count("jxp_74_ijp_pressure"))
        self.assertNotIn("which = jxp_74_ijp_pressure", legacy_effects)
        self.assertIn("which = jxp_a_shinshu_militancy", legacy_effects)

        decisions = parse_file(MAIN_ROOT / SHINSHU_DECISION_FILE)
        decision_root = first_object(decisions.root, "country_decisions")
        ids = {
            entry.key
            for entry in decision_root.entries
            if entry.key is not None and isinstance(entry.value, Object)
        }
        expected_ids = {
            "jxp_a_95_decision_hoshu_state",
            "jxp_a_95_decision_somon_council",
            "jxp_a_95_decision_secular_commonwealth",
        }
        self.assertEqual(expected_ids, ids)
        for entry in decision_root.entries:
            if entry.key not in expected_ids or not isinstance(entry.value, Object):
                continue
            potential = first_object(entry.value, "potential")
            self.assertIn(
                "yes",
                _object_scalars(potential, "jxp_a_ijp_has_terminal_settlement_trigger"),
            )

        for suffix in ("hoshu_state", "somon_council", "secular_commonwealth"):
            block = effects.split(f"jxp_a_ijp_choose_{suffix}_effect = {{", 1)[1].split(
                "\n}", 1
            )[0]
            self.assertIn("jxp_a_ijp_clear_terminal_settlement_effect = yes", block)
            self.assertIn("jxp_74_ijp_cleanup_effect = yes", block)
            self.assertIn("jxp_a_shinshu_cleanup_crisis_effect = yes", block)

        crisis_cleanup = effects.split(
            "jxp_a_shinshu_cleanup_crisis_effect = {", 1
        )[1].split("\n}", 1)[0]
        self.assertNotIn("jxp_a_shinshu_reconciled_order", crisis_cleanup)
        self.assertNotIn("jxp_a_shinshu_suppression_aftershock", crisis_cleanup)

    def test_honganji_history_and_ikko_heartland_use_authoritative_sources(self) -> None:
        plan = json.loads(
            (MAP_ROOT / "tools/jxp_map_builder/history_plan.json").read_text(
                encoding="utf-8"
            )
        )
        honganji = next(item for item in plan["countries"] if item["tag"] == "HNG")
        self.assertEqual("jodo_shinshu", honganji["religion"])
        self.assertEqual(
            [["1488.1.1", "religion = jodo_shinshu"]],
            plan["dated_effects"]["4953"],
        )

        country = parse_file(MAP_ROOT / "history/countries/HNG - Honganji.txt")
        province = parse_file(MAP_ROOT / "history/provinces/4953 - Kaga.txt")
        self.assertEqual("jodo_shinshu", first_scalar(country.root, "religion"))
        dated_religions = {
            first_scalar(entry.value, "religion")
            for entry in entries_named(province.root, "1488.1.1")
            if isinstance(entry.value, Object)
        }
        self.assertIn("jodo_shinshu", dated_religions)

        contract = json.loads(
            (
                MAP_ROOT
                / "tools/jxp_map_validation/main_compatibility_contract.json"
            ).read_text(encoding="utf-8")
        )
        expected_areas = {
            "jxp_western_hokuriku_area",
            "chubu_area",
            "kinai_area",
            "jxp_tokai_area",
            "jxp_ise_kii_area",
        }
        self.assertEqual(
            expected_areas,
            set(contract["geography_flags"]["jxp_map_compat_ikko_heartland"]),
        )

        map_effects = parse_file(MAP_ROOT / "common/scripted_effects/jxp_map_effects.txt")
        initializer = first_object(
            map_effects.root, "jxp_map_initialize_geography_contract_effect"
        )
        initialization_branch = first_object(initializer, "if")
        published_areas: set[str] = set()
        for entry in entries_named(initialization_branch, "every_province"):
            if not isinstance(entry.value, Object):
                continue
            if "jxp_map_compat_ikko_heartland" not in _object_scalars(
                entry.value, "set_province_flag"
            ):
                continue
            published_areas.update(
                _object_scalars(first_object(entry.value, "limit"), "area")
            )
        self.assertEqual(expected_areas, published_areas)
        self.assertNotIn("jxp_western_saigoku_area", published_areas)
        self.assertIn(
            "jxp_map_geography_contract_v013",
            _object_scalars(initializer, "set_global_flag"),
        )
        self.assertIn(
            "jxp_map_compat_ikko_heartland",
            _object_scalars(initializer, "clr_province_flag"),
        )

    def test_source_and_active_localisation_pipeline_is_stable(self) -> None:
        source = MAIN_ROOT / "localisation_source/jxp_a_95_shinshu_l_english_utf8_source.yml"
        active = MAIN_ROOT / "localisation/jxp_a_95_shinshu_l_english.yml"
        source_text = source.read_text(encoding="utf-8-sig")
        active_bytes = active.read_bytes()
        active_text = active_bytes.decode("utf-8-sig")
        encoder_path = (
            REPO_ROOT
            / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py"
        )
        spec = importlib.util.spec_from_file_location("_jxp_a95_escape", encoder_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        encoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(encoder)
        self.assertIn("jodo_shinshu", source_text)
        self.assertTrue(active_bytes.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(encoder.escape_text(source_text).encode("utf-8-sig"), active_bytes)
        self.assertIsNone(re.search(r"[\u3400-\u9fff]", active_text))


if __name__ == "__main__":
    unittest.main()
