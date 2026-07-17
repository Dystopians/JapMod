from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from jxp_validation.internal_systems import (
    ACTION_FILE,
    PATCHED_REGISTRY,
    PLAN_FILE,
    TRIGGER_FILE,
    WAR_ACTION_FILE,
    WARGOAL_FILE,
    audit_payload,
    load_payload,
)


MOD_ROOT = Path(__file__).resolve().parents[3]


class AgentAInternalSystemsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = json.loads((MOD_ROOT / PLAN_FILE).read_text(encoding="utf-8"))
        cls.payload = load_payload(MOD_ROOT)

    def test_current_contract_passes(self) -> None:
        self.assertEqual(audit_payload(self.payload, self.plan), [])

    def test_capacity_mutation_is_rejected(self) -> None:
        mutated = dict(self.payload)
        key = TRIGGER_FILE.as_posix()
        mutated[key] = mutated[key].replace(
            "which = jxp_a_nested_client_count\n\t\t\tvalue = 3",
            "which = jxp_a_nested_client_count\n\t\t\tvalue = 4",
            1,
        )
        self.assertIn("internal_systems.capacity_runtime", audit_payload(mutated, self.plan))

    def test_overseas_annex_mutation_is_rejected(self) -> None:
        mutated = dict(self.payload)
        key = PATCHED_REGISTRY.as_posix()
        text = mutated[key]
        start = text.index("annex_country_japan = {")
        end = text.index("\nwar_goal_change_government = {", start)
        block = text[start:end].replace("region = japan_region", "region = korea_region", 1)
        mutated[key] = text[:start] + block + text[end:]
        self.assertIn("internal_systems.annex_region", audit_payload(mutated, self.plan))

    def test_internal_wargoal_geography_mutation_is_rejected(self) -> None:
        mutated = dict(self.payload)
        key = WARGOAL_FILE.as_posix()
        mutated[key] = mutated[key].replace("region = japan_region", "region = korea_region", 1)
        self.assertIn("internal_systems.wargoal_geography", audit_payload(mutated, self.plan))

    def test_permanent_claim_mutation_is_rejected(self) -> None:
        mutated = dict(self.payload)
        key = WAR_ACTION_FILE.as_posix()
        mutated[key] = mutated[key].replace("add_claim = ROOT", "add_permanent_claim = ROOT", 1)
        self.assertIn("internal_systems.permanent_claim", audit_payload(mutated, self.plan))

    def test_native_subject_plan_mutation_is_rejected(self) -> None:
        mutated_plan = deepcopy(self.plan)
        mutated_plan["implementation_path"] = "A"
        mutated_plan["native_nested_subject_type"] = True
        self.assertIn("internal_systems.path_b", audit_payload(self.payload, mutated_plan))

    def test_global_cta_mutation_is_rejected(self) -> None:
        mutated = dict(self.payload)
        key = ACTION_FILE.as_posix()
        mutated[key] += "\njoin_all_offensive_wars = yes\n"
        self.assertIn("internal_systems.native_or_global_leak", audit_payload(mutated, self.plan))


if __name__ == "__main__":
    unittest.main()
