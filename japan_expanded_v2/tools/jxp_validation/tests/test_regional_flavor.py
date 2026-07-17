from __future__ import annotations

from pathlib import Path
import unittest

from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.regional_flavor import (
    CLEANUP_FILE,
    DECISION_FILE,
    DEBUG_EFFECT_FILE,
    EVENT_FILE,
    LEGACY_FOUNDER_MODIFIER_FILE,
    LEGACY_OVERSEAS_MODIFIER_FILE,
    MAP_CONTRACT_FILE,
    MAP_EFFECT_FILE,
    MAP_MISSION_FILE,
    MODIFIER_FILE,
    TRIGGER_FILE,
    audit_cleanup_contract_text,
    audit_decision_contract_text,
    audit_event_contract_text,
    audit_forbidden_anchor_text,
    audit_map_contract,
    audit_regional_modifier_signature_contract,
    audit_schedule_contract_text,
    audit_trigger_contract_text,
    check_regional_flavor,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = REPO_ROOT / "japan_expanded_v2"
MAP_ROOT = REPO_ROOT / "japan_expanded_v2_map"


def _text(root: Path, relative: Path) -> str:
    return (root / relative).read_text(encoding="utf-8-sig")


def _codes(result: CheckResult) -> set[str]:
    return {issue.code for issue in result.issues}


class RegionalFlavorContractTests(unittest.TestCase):
    def test_live_regional_slice_is_closed(self) -> None:
        result = check_regional_flavor(
            ValidationContext(MAIN_ROOT), ValidationContext(MAP_ROOT)
        )
        self.assertEqual([], result.issues, result.to_dict())
        self.assertEqual(3, result.metrics["semantic_gates"])
        self.assertEqual(3, result.metrics["regional_missions"])
        self.assertEqual(3, result.metrics["regional_events"])
        self.assertEqual(6, result.metrics["choice_options"])
        self.assertEqual(3, result.metrics["player_decisions"])
        self.assertEqual(3, result.metrics["debug_decisions"])
        self.assertEqual(7, result.metrics["finite_modifiers"])
        self.assertEqual(3, result.metrics["schedule_helpers"])
        self.assertEqual(0, result.metrics["legacy_signature_collisions"])

    def test_mutation_removing_standalone_fallback_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, TRIGGER_FILE)
        mutated = source.replace(
            "owns_or_non_sovereign_subject_of = 4651",
            "owns_or_non_sovereign_subject_of = 4652",
            1,
        )
        result = CheckResult("mutation")
        audit_trigger_contract_text(mutated, result)
        self.assertIn("regional_flavor.fallback_missing", _codes(result))

    def test_mutation_replacing_semantic_flag_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, TRIGGER_FILE)
        mutated = source.replace(
            "jxp_map_compat_ryukyu_gateway",
            "jxp_map_compat_ryukyu_gateway_broken",
            1,
        )
        result = CheckResult("mutation")
        audit_trigger_contract_text(mutated, result)
        self.assertIn("regional_flavor.trigger_contract", _codes(result))

    def test_mutation_introducing_duplicate_reward_anchor_is_rejected(self) -> None:
        result = CheckResult("mutation")
        audit_forbidden_anchor_text(
            {"mutated-event": _text(MAIN_ROOT, EVENT_FILE) + "\n1021 = { }\n"},
            result,
        )
        self.assertIn("regional_flavor.forbidden_anchor", _codes(result))

    def test_mutation_introducing_awaji_reward_anchor_is_rejected(self) -> None:
        result = CheckResult("mutation")
        audit_forbidden_anchor_text(
            {"mutated-event": _text(MAIN_ROOT, EVENT_FILE) + "\n4943 = { }\n"},
            result,
        )
        self.assertIn("regional_flavor.forbidden_anchor", _codes(result))

    def test_mutation_making_reward_permanent_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, EVENT_FILE)
        mutated = source.replace("duration = 3650", "duration = -1", 1)
        result = CheckResult("mutation")
        audit_event_contract_text(mutated, result)
        self.assertTrue(
            {"regional_flavor.outcome_duration", "regional_flavor.finite_duration"}
            & _codes(result)
        )

    def test_mutation_removing_option_ai_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, EVENT_FILE)
        mutated = source.replace("ai_chance = {", "broken_ai_chance = {", 1)
        result = CheckResult("mutation")
        audit_event_contract_text(mutated, result)
        self.assertIn("regional_flavor.option_ai", _codes(result))

    def test_mutation_removing_option_outcome_reset_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, EVENT_FILE)
        mutated = source.replace(
            "\t\tjxp_77_clear_regional_outcomes_effect = yes\n", "", 1
        )
        result = CheckResult("mutation")
        audit_event_contract_text(mutated, result)
        self.assertIn("regional_flavor.option_outcome_reset", _codes(result))

    def test_mutation_bypassing_decision_schedule_helper_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, DECISION_FILE)
        mutated = source.replace(
            "\t\t\tjxp_77_schedule_tsushima_channel_council_effect = yes\n",
            "\t\t\tcountry_event = { id = jxp_77.1 days = 1 }\n",
            1,
        )
        result = CheckResult("mutation")
        audit_decision_contract_text(mutated, result)
        self.assertIn("regional_flavor.decision_schedule_helper", _codes(result))

    def test_mutation_breaking_atomic_schedule_lock_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, CLEANUP_FILE)
        mutated = source.replace("\t\tduration = 2\n", "\t\tduration = 3\n", 1)
        result = CheckResult("mutation")
        audit_schedule_contract_text(mutated, result)
        self.assertIn("regional_flavor.schedule_helper", _codes(result))

    def test_mutation_bypassing_map_mission_schedule_helper_is_rejected(self) -> None:
        mission = _text(MAP_ROOT, MAP_MISSION_FILE)
        mutated = mission.replace(
            "\t\t\tjxp_77_schedule_tsushima_channel_council_effect = yes\n",
            "\t\t\tcountry_event = { id = jxp_77.1 days = 1 }\n",
            1,
        )
        result = CheckResult("mutation")
        audit_map_contract(
            _text(MAP_ROOT, MAP_CONTRACT_FILE),
            _text(MAP_ROOT, MAP_EFFECT_FILE),
            mutated,
            result,
        )
        self.assertIn("regional_flavor.map_mission_contract", _codes(result))

    def test_mutation_reintroducing_tsushima_legacy_signature_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, MODIFIER_FILE)
        mutated = source.replace(
            "jxp_77_tsushima_interpreter_office = {\n"
            "\tenvoy_travel_time = -0.10\n"
            "\timprove_relation_modifier = 0.10\n"
            "}",
            "jxp_77_tsushima_interpreter_office = {\n"
            "\ttrade_steering = 0.10\n"
            "\tdiplomatic_reputation = 1\n"
            "}",
            1,
        )
        result = CheckResult("mutation")
        audit_regional_modifier_signature_contract(
            mutated,
            _text(MAIN_ROOT, LEGACY_OVERSEAS_MODIFIER_FILE),
            _text(MAIN_ROOT, LEGACY_FOUNDER_MODIFIER_FILE),
            result,
        )
        self.assertIn(
            "regional_flavor.legacy_signature_collision", _codes(result)
        )

    def test_mutation_reintroducing_soo_coastal_signature_is_rejected(self) -> None:
        source = _text(MAIN_ROOT, MODIFIER_FILE)
        mutated = source.replace(
            "jxp_77_tsushima_coastal_watch = {\n"
            "\tnaval_morale = 0.05\n"
            "\tglobal_sailors_modifier = 0.08\n"
            "}",
            "jxp_77_tsushima_coastal_watch = {\n"
            "\tnaval_morale = 0.05\n"
            "\tprivateer_efficiency = 0.15\n"
            "}",
            1,
        )
        result = CheckResult("mutation")
        audit_regional_modifier_signature_contract(
            mutated,
            _text(MAIN_ROOT, LEGACY_OVERSEAS_MODIFIER_FILE),
            _text(MAIN_ROOT, LEGACY_FOUNDER_MODIFIER_FILE),
            result,
        )
        self.assertIn(
            "regional_flavor.legacy_signature_collision", _codes(result)
        )

    def test_mutation_removing_cleanup_is_rejected(self) -> None:
        cleanup = _text(MAIN_ROOT, CLEANUP_FILE)
        mutated = cleanup.replace(
            "\tremove_country_modifier = jxp_77_ryukyu_free_port\n", "", 1
        )
        result = CheckResult("mutation")
        audit_cleanup_contract_text(
            mutated, _text(MAIN_ROOT, DEBUG_EFFECT_FILE), result
        )
        self.assertIn("regional_flavor.outcome_cleanup_contract", _codes(result))


if __name__ == "__main__":
    unittest.main()
