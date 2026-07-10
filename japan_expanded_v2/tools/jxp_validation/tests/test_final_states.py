from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from jxp_validation.core import ValidationContext
from jxp_validation.final_states import (
    ACTIVE_LOC_FILE,
    DEBUG_FILE,
    EFFECT_FILE,
    LEGACY_REFORM_FILE,
    LIFECYCLE_FILE,
    MIGRATION_FILE,
    MISSION_FILES,
    MISSION_REFRESH_FILE,
    MODIFIER_FILE,
    ON_ACTION_FILE,
    REFORM_FILE,
    ROUTE_EFFECT_FILE,
    SOURCE_LOC_FILE,
    TRIGGER_FILE,
    check_final_states,
)


LIVE_MOD_ROOT = Path(__file__).resolve().parents[3]
LEGACY_SOURCE_LOC_FILE = Path("localisation_source/jxp_l_english_utf8_source.yml")
CONTRACT_FILES = (
    TRIGGER_FILE,
    REFORM_FILE,
    LEGACY_REFORM_FILE,
    LIFECYCLE_FILE,
    EFFECT_FILE,
    ROUTE_EFFECT_FILE,
    MODIFIER_FILE,
    MIGRATION_FILE,
    MISSION_REFRESH_FILE,
    ON_ACTION_FILE,
    DEBUG_FILE,
    SOURCE_LOC_FILE,
    ACTIVE_LOC_FILE,
    LEGACY_SOURCE_LOC_FILE,
    *MISSION_FILES,
)


def _copy_contract(root: Path) -> None:
    for relative in CONTRACT_FILES:
        source = LIVE_MOD_ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _mutate(root: Path, relative: Path, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8-sig")
    changed = text.replace(old, new, 1)
    if changed == text:
        raise AssertionError(f"mutation anchor not found in {relative}: {old!r}")
    path.write_text(changed, encoding="utf-8")


def _codes(root: Path) -> set[str]:
    return {issue.code for issue in check_final_states(ValidationContext(root)).issues}


class FinalStateContractTests(unittest.TestCase):
    def _temporary_contract(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        _copy_contract(root)
        return root

    def test_live_final_state_contract_is_closed(self) -> None:
        result = check_final_states(ValidationContext(LIVE_MOD_ROOT))
        self.assertEqual([], result.issues)
        self.assertEqual(10, result.metrics["final_states"])
        self.assertEqual(6, result.metrics["new_power_structures"])
        self.assertEqual(4, result.metrics["reused_power_structures"])
        self.assertEqual(10, result.metrics["exclusive_trigger_profiles"])
        self.assertEqual(512, result.metrics["jap_route_state_vectors"])
        self.assertEqual(10, result.metrics["mismatch_guards"])
        self.assertEqual(10, result.metrics["political_capstones"])
        self.assertEqual(10, result.metrics["capstone_modifiers"])

    def test_rejects_reused_reform_visible_from_prefinal_route_flag(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            LEGACY_REFORM_FILE,
            "\t\t\tjxp_final_state_reformed_trigger = yes\n"
            "\t\t\thas_reform = jxp_reformed_japan_reform\n",
            "\t\t\thas_country_flag = jxp_path_reformed\n"
            "\t\t\thas_reform = jxp_reformed_japan_reform\n",
        )
        self.assertIn("final_state.reform_potential", _codes(root))

    def test_rejects_new_reform_without_basic_visibility(self) -> None:
        root = self._temporary_contract()
        _mutate(root, REFORM_FILE, "\tbasic_reform = yes\n", "\tbasic_reform = no\n")
        self.assertIn("final_state.reform_visibility", _codes(root))

    def test_rejects_overlapping_or_missing_state_trigger(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "jxp_final_state_open_trigger = {\n\ttag = JAP\n",
            "jxp_final_state_open_trigger = {\n\ttag = KJP\n",
        )
        codes = _codes(root)
        self.assertIn("final_state.trigger_exclusivity", codes)
        self.assertIn("final_state.trigger_density", codes)

    def test_rejects_contaminated_jap_route_vector_as_final_state(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "jxp_final_state_sakoku_trigger = {\n"
            "\ttag = JAP\n"
            "\thas_country_flag = jxp_path_sakoku\n"
            "\tNOT = {\n"
            "\t\tOR = {\n"
            "\t\t\thas_country_flag = jxp_path_open_trade\n",
            "jxp_final_state_sakoku_trigger = {\n"
            "\ttag = JAP\n"
            "\thas_country_flag = jxp_path_sakoku\n"
            "\tNOT = {\n"
            "\t\tOR = {\n",
        )
        self.assertIn("final_state.jap_route_vector_exclusivity", _codes(root))

    def test_rejects_mismatch_guard_that_ignores_one_structure(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\t\thas_reform = jxp_wokou_admiralty_reform\n",
            "",
        )
        self.assertIn("final_state.mismatch_inventory", _codes(root))

    def test_rejects_mismatch_guard_that_leaks_foreign_capstone(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            TRIGGER_FILE,
            "\t\thas_country_modifier = jxp_79_wokou_admiralty_articles\n",
            "",
        )
        self.assertIn("final_state.mismatch_modifier_inventory", _codes(root))

    def test_rejects_sync_branch_without_mismatch_guard(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\t\t\t\tlimit = { jxp_final_state_open_power_mismatch_trigger = yes }\n",
            "\t\t\t\tlimit = { always = yes }\n",
        )
        self.assertIn("final_state.sync_mapping", _codes(root))

    def test_rejects_state_change_that_keeps_old_capstone_modifier(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\t\t\t\tlimit = { jxp_final_state_open_power_mismatch_trigger = yes }\n"
            "\t\t\t\tjxp_clear_final_state_power_structures_effect = yes\n"
            "\t\t\t\tjxp_clear_final_state_capstone_modifiers_effect = yes\n",
            "\t\t\t\tlimit = { jxp_final_state_open_power_mismatch_trigger = yes }\n"
            "\t\t\t\tjxp_clear_final_state_power_structures_effect = yes\n",
        )
        self.assertIn("final_state.sync_mapping", _codes(root))

    def test_rejects_incomplete_canonical_clear(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\tif = { limit = { has_reform = jxp_wokou_admiralty_reform } "
            "remove_government_reform = jxp_wokou_admiralty_reform }\n",
            "",
        )
        self.assertIn("final_state.clear_inventory", _codes(root))

    def test_rejects_incomplete_capstone_cleanup(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            EFFECT_FILE,
            "\tremove_country_modifier = jxp_79_wokou_admiralty_articles\n",
            "",
        )
        self.assertIn("final_state.capstone_clear_inventory", _codes(root))

    def test_rejects_route_change_bypassing_canonical_sync(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            ROUTE_EFFECT_FILE,
            "\tjxp_sync_final_state_power_structure_effect = yes\n",
            "",
        )
        self.assertIn("final_state.route_sync_wiring", _codes(root))

    def test_rejects_migration_without_reform_sync(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            MIGRATION_FILE,
            "\t\tjxp_sync_final_state_power_structure_effect = yes\n",
            "",
        )
        self.assertIn("final_state.migration_sync", _codes(root))

    def test_rejects_migration_not_registered_on_startup(self) -> None:
        root = self._temporary_contract()
        _mutate(root, ON_ACTION_FILE, "\t\tjxp_migration_v028.1\n", "")
        self.assertIn("final_state.migration_on_startup", _codes(root))

    def test_rejects_next_day_refresh_without_reform_reconcile(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            MISSION_REFRESH_FILE,
            "\t\tjxp_sync_final_state_power_structure_effect = yes\n",
            "",
        )
        self.assertIn("final_state.next_day_sync", _codes(root))

    def test_rejects_missing_debug_migration_cleanup(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            DEBUG_FILE,
            "\t\tclr_country_flag = jxp_final_state_power_migration_v0280\n",
            "",
        )
        self.assertIn("final_state.debug_cleanup", _codes(root))

    def test_rejects_capstone_without_its_power_structure_gate(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            Path("missions/jxp_40_final_state_completion_missions.txt"),
            "\t\t\thas_reform = jxp_uncommitted_realm_council_reform\n",
            "",
        )
        self.assertIn("final_state.capstone_reform_gate", _codes(root))

    def test_rejects_capstone_without_unique_permanent_modifier(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            Path("missions/jxp_56_final_tag_identity_missions.txt"),
            "\t\t\t\tname = jxp_79_wokou_admiralty_articles\n",
            "\t\t\t\tname = jxp_route_wokou\n",
        )
        self.assertIn("final_state.capstone_modifier", _codes(root))

    def test_rejects_capstone_without_direct_predecessor(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            Path("missions/jxp_japan_missions.txt"),
            "\t\trequired_missions = { jxp_mission_equal_treaties }\n",
            "\t\trequired_missions = { jxp_mission_manila_route }\n",
        )
        self.assertIn("final_state.capstone_dependency", _codes(root))

    def test_rejects_shallow_capstone_modifier(self) -> None:
        root = self._temporary_contract()
        _mutate(root, MODIFIER_FILE, "\tdiplomatic_reputation = 1\n", "")
        self.assertIn("final_state.modifier_depth", _codes(root))

    def test_rejects_stale_escaped_localisation(self) -> None:
        root = self._temporary_contract()
        _mutate(
            root,
            SOURCE_LOC_FILE,
            'jxp_79_uncommitted_realm_program:0 "天下评议法"',
            'jxp_79_uncommitted_realm_program:0 "天下评议法典"',
        )
        self.assertIn("final_state.localisation_escape", _codes(root))


if __name__ == "__main__":
    unittest.main()
