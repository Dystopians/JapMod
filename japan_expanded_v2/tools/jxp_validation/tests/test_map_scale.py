from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.map_scale import (
    EXPECTED_CALLS,
    EXPECTED_TRIGGER_BODIES,
    check_map_scale_progression,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]


class MapScaleProgressionTests(unittest.TestCase):
    def test_live_mod_closes_all_nineteen_legacy_gates(self) -> None:
        result = check_map_scale_progression(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(len(EXPECTED_CALLS), 19)
        self.assertEqual(result.metrics["matched_calls"], 19)
        self.assertEqual(
            result.metrics["semantic_contracts"], len(EXPECTED_TRIGGER_BODIES)
        )
        self.assertEqual(result.metrics["legacy_city_thresholds"], 0)

    def test_rejects_semantic_trigger_body_regression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            triggers = root / "common" / "scripted_triggers"
            triggers.mkdir(parents=True)
            live_contract = (
                LIVE_MOD_ROOT / "common" / "scripted_triggers" / "jxp_70_map_scale_triggers.txt"
            ).read_text(encoding="utf-8")
            weakened_contract = live_contract.replace(
                "\tjxp_tenka_order_at_least_50 = yes\n\treligious_unity = 0.8\n}",
                "\talways = yes\n}",
                1,
            )
            self.assertNotEqual(live_contract, weakened_contract)
            (triggers / "jxp_70_map_scale_triggers.txt").write_text(
                weakened_contract,
                encoding="utf-8",
            )
            result = check_map_scale_progression(ValidationContext(root))
            self.assertIn(
                "map_scale.trigger_contract",
                {issue.code for issue in result.issues},
            )

    def test_rejects_gameplay_call_moved_from_trigger_to_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trigger_destination = (
                root / "common" / "scripted_triggers" / "jxp_70_map_scale_triggers.txt"
            )
            trigger_destination.parent.mkdir(parents=True)
            trigger_destination.write_text(
                (
                    LIVE_MOD_ROOT
                    / "common"
                    / "scripted_triggers"
                    / "jxp_70_map_scale_triggers.txt"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            mission_destination = root / "missions" / "jxp_japan_missions.txt"
            mission_destination.parent.mkdir(parents=True)
            mission_destination.write_text(
                "jxp_japan_state_missions = {\n"
                "\tjxp_mission_unite_the_isles = {\n"
                "\t\teffect = {\n"
                "\t\t\tjxp_has_unite_the_isles_scope_trigger = yes\n"
                "\t\t}\n"
                "\t}\n"
                "}\n",
                encoding="utf-8",
            )
            result = check_map_scale_progression(ValidationContext(root))
            self.assertIn(
                "map_scale.call_context",
                {issue.code for issue in result.issues},
            )

    def test_rejects_gameplay_call_negated_inside_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trigger_destination = (
                root / "common" / "scripted_triggers" / "jxp_70_map_scale_triggers.txt"
            )
            trigger_destination.parent.mkdir(parents=True)
            trigger_destination.write_text(
                (
                    LIVE_MOD_ROOT
                    / "common"
                    / "scripted_triggers"
                    / "jxp_70_map_scale_triggers.txt"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            mission_destination = root / "missions" / "jxp_japan_missions.txt"
            mission_destination.parent.mkdir(parents=True)
            mission_destination.write_text(
                "jxp_japan_state_missions = {\n"
                "\tjxp_mission_unite_the_isles = {\n"
                "\t\ttrigger = {\n"
                "\t\t\tNOT = {\n"
                "\t\t\t\tjxp_has_unite_the_isles_scope_trigger = yes\n"
                "\t\t\t}\n"
                "\t\t}\n"
                "\t}\n"
                "}\n",
                encoding="utf-8",
            )
            result = check_map_scale_progression(ValidationContext(root))
            self.assertIn(
                "map_scale.call_polarity",
                {issue.code for issue in result.issues},
            )

    def test_rejects_legacy_twenty_five_or_thirty_city_thresholds(self) -> None:
        for value in (25, 30):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                missions = root / "missions"
                missions.mkdir(parents=True)
                (missions / "test.txt").write_text(
                    f"test = {{ trigger = {{ num_of_cities = {value} }} }}\n",
                    encoding="utf-8",
                )
                result = check_map_scale_progression(ValidationContext(root))
                self.assertIn(
                    "map_scale.legacy_city_threshold",
                    {issue.code for issue in result.issues},
                )

    def test_rejects_companion_only_reference_in_main_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            triggers = root / "common" / "scripted_triggers"
            triggers.mkdir(parents=True)
            (triggers / "jxp_70_map_scale_triggers.txt").write_text(
                "jxp_has_unite_the_isles_scope_trigger = { owns = 4942 }\n",
                encoding="utf-8",
            )
            result = check_map_scale_progression(ValidationContext(root))
            self.assertIn(
                "map_scale.companion_only_reference",
                {issue.code for issue in result.issues},
            )


if __name__ == "__main__":
    unittest.main()
