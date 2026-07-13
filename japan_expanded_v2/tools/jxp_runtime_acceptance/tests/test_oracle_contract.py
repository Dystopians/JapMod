from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest


TOOLS_ROOT = Path(__file__).resolve().parents[2]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from jxp_runtime_acceptance import oracle_contract
from jxp_runtime_acceptance import runtime_acceptance as runtime


REPO_ROOT = Path(__file__).resolve().parents[4]
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")


class RuntimeOracleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        matrix = json.loads(
            (
                REPO_ROOT
                / "japan_expanded_v2/tools/jxp_runtime_acceptance/runtime_scenarios.json"
            ).read_text(encoding="utf-8")
        )
        cls.scenario = next(item for item in matrix["scenarios"] if item["id"] == "R12")
        contract = cls.scenario["session_contract"]
        cls.artifact_specs = {
            item["role"]: item for item in contract["required_artifacts"]
        }
        cls.assertion_ids = contract["assertion_ids"]
        cls.pack = json.loads(
            (
                REPO_ROOT
                / "japan_expanded_v2_map/tools/jxp_map_validation/generated/runtime_oracle_pack.json"
            ).read_text(encoding="utf-8")
        )

    def verify(self, scenario: dict[str, object]) -> dict[str, object]:
        return oracle_contract.verify_runtime_oracle(
            scenario,
            self.artifact_specs,
            self.assertion_ids,
            REPO_ROOT,
            GAME_ROOT,
            verify_sources=False,
        )

    def test_live_pack_typed_cases_and_all_258_sources_verify(self) -> None:
        value = oracle_contract.verify_runtime_oracle(
            self.scenario,
            self.artifact_specs,
            self.assertion_ids,
            REPO_ROOT,
            GAME_ROOT,
            verify_sources=True,
        )
        self.assertEqual(258, value["source_pin_count"])
        self.assertEqual(282, value["typed_case_count"])
        self.assertEqual(282, len(value["case_contracts"]))
        runtime._verify_oracle_snapshot_sources(
            value,
            [
                {
                    "component": component,
                    "source_revision": runtime._current_candidate_revision(),
                }
                for component in ("main", "map")
            ],
        )

    def test_exact_metadata_and_semantic_projection_fail_closed(self) -> None:
        for mutate in (
            lambda value: value["exact_oracle"].update({"sha256": "0" * 64}),
            lambda value: value["exact_oracle"].update({"schema": "wrong"}),
            lambda value: value["exact_oracle"].update({"extra": True}),
            lambda value: value["executable_checklist"].update(
                {"japan_region_province_count": 87}
            ),
        ):
            scenario = deepcopy(self.scenario)
            mutate(scenario)
            with self.assertRaises(oracle_contract.OracleContractError):
                self.verify(scenario)

    def test_pointer_assertion_and_binding_swaps_fail_even_at_same_counts(self) -> None:
        mutations = []

        def lifecycle_leaf(value: dict[str, object]) -> None:
            value["typed_cases"][-1]["expected"]["pointer"] = (
                "/unification/lifecycle/r12_twelve_month_reload_stability"
            )

        mutations.append(lifecycle_leaf)

        def wrong_assertion(value: dict[str, object]) -> None:
            value["typed_cases"][0]["assertion_ids"] = ["r12_event_semantics"]

        mutations.append(wrong_assertion)

        def swap_focus(value: dict[str, object]) -> None:
            focused = [
                case
                for case in value["typed_cases"]
                if any(
                    binding.get("role") == "r12_island_focus_screenshot_set"
                    for binding in case["evidence_bindings"]
                )
            ]
            first = next(
                binding
                for binding in focused[0]["evidence_bindings"]
                if binding.get("role") == "r12_island_focus_screenshot_set"
            )
            second = next(
                binding
                for binding in focused[1]["evidence_bindings"]
                if binding.get("role") == "r12_island_focus_screenshot_set"
            )
            first["case_id"], second["case_id"] = second["case_id"], first["case_id"]

        mutations.append(swap_focus)

        def remove_hnm_mission(value: dict[str, object]) -> None:
            hnm = next(
                case
                for case in value["typed_cases"]
                if case["case_id"] == "r12_origin_hnm_sea_exclusive"
            )
            hnm["evidence_bindings"].pop()
            hnm["evidence_bindings"].append(
                deepcopy(hnm["evidence_bindings"][-1])
            )

        mutations.append(remove_hnm_mission)

        for mutate in mutations:
            scenario = deepcopy(self.scenario)
            mutate(scenario)
            with self.assertRaises(oracle_contract.OracleContractError):
                self.verify(scenario)

    def test_pack_internal_hashes_and_nonfinite_json_are_rejected(self) -> None:
        pack = deepcopy(self.pack)
        history = next(iter(pack["history_states"].values()))
        history["state_sha256"] = "0" * 64
        with self.assertRaises(oracle_contract.OracleContractError):
            oracle_contract._validate_pack_shape(pack)
        with self.assertRaises(oracle_contract.OracleContractError):
            oracle_contract._strict_json_bytes(b'{"value":NaN}', "non-finite")
        with self.assertRaises(oracle_contract.OracleContractError):
            oracle_contract._strict_json_bytes(b'{"value":1,"value":2}', "duplicate")

    def test_typed_checklist_requires_all_cases_and_terminal_oracle_hashes(self) -> None:
        normalized = runtime._normalized_evidence_contract(
            runtime._scenario("R12"), None
        )
        role = "r12_ports_straits_positions_checklist"
        contracts = normalized["runtime_oracle"]["case_contracts"]
        expected = {
            case_id: contract
            for case_id, contract in contracts.items()
            if any(
                binding["role"] == role
                for binding in contract["evidence_bindings"]
            )
        }
        value = {
            "schema": "jxp_runtime_typed_case_evidence/v1",
            "scenario_id": "R12",
            "role": role,
            "oracle_pack_sha256": normalized["runtime_oracle"]["sha256"],
            "cases": {
                case_id: {
                    "status": "PASS",
                    "note": "rendering row observed against the named oracle",
                    "attestor": "RuntimeOracleContractTests",
                    "attested_at": "2026-07-13T20:00:00Z",
                    "oracle_pointer": contract["pointer"],
                    "oracle_object_sha256": contract["oracle_object_sha256"],
                    "observed": {"rendered": True},
                }
                for case_id, contract in expected.items()
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "checklist.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = runtime._validate_r12_typed_checklist(path, role, normalized)
            self.assertEqual(88, result["case_count"])
            value["cases"].pop(next(iter(value["cases"])))
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_r12_typed_checklist(path, role, normalized)

    def test_282_case_index_expands_all_bindings_to_exact_artifacts(self) -> None:
        normalized = runtime._normalized_evidence_contract(
            runtime._scenario("R12"), None
        )
        role_records: dict[str, list[dict[str, object]]] = {}
        counter = 1
        for role, spec in normalized["artifact_specs"].items():
            if spec["kind"] == "screenshot_set":
                records = []
                for case_id in spec["case_ids"]:
                    records.append(
                        {
                            "case_id": case_id,
                            "path": f"C:/sealed/{counter}.png",
                            "sha256": f"{counter:064x}",
                        }
                    )
                    counter += 1
            else:
                records = [
                    {
                        "path": f"C:/sealed/{counter}.artifact",
                        "sha256": f"{counter:064x}",
                    }
                ]
                counter += 1
            role_records[role] = records
        index = runtime._runtime_oracle_evidence_index(normalized, role_records)
        self.assertEqual(282, len(index))
        self.assertEqual(697, sum(len(item["artifacts"]) for item in index))
        role_records["r12_island_focus_screenshot_set"].pop()
        with self.assertRaises(runtime.AcceptanceError):
            runtime._runtime_oracle_evidence_index(normalized, role_records)


if __name__ == "__main__":
    unittest.main()
