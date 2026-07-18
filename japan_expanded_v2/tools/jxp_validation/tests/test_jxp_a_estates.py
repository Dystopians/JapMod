from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import sys
import unittest

from jxp_validation.clausewitz import parse_file


MAIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = MAIN_ROOT.parent
GAME_ROOT = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
BUILDER_PATH = (
    MAIN_ROOT
    / "tools"
    / "jxp_a_socioeconomic_builder"
    / "build_estates.py"
)


def _load_builder():
    spec = importlib.util.spec_from_file_location("jxp_a_build_estates", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load build_estates.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


class JapaneseEstateBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = BUILDER.render_outputs(GAME_ROOT)

    def test_fixed_design_inventory(self) -> None:
        self.assertEqual(48, len(BUILDER.PRIVILEGES))
        self.assertEqual(
            Counter({estate: 12 for estate in BUILDER.ESTATE_ORDER}),
            Counter(row.estate for row in BUILDER.PRIVILEGES),
        )
        self.assertEqual(40, len(BUILDER.AGENDAS))
        self.assertEqual(
            Counter({estate: 10 for estate in BUILDER.ESTATE_ORDER}),
            Counter(row.estate for row in BUILDER.AGENDAS),
        )
        self.assertEqual(15, len(BUILDER.NAME_MATRIX))

    def test_agendas_cannot_be_selected_already_complete(self) -> None:
        text = (
            MAIN_ROOT / "common/estate_agendas/jxp_a_110_japanese_agendas.txt"
        ).read_text(encoding="utf-8")
        for agenda in BUILDER.AGENDAS:
            with self.subTest(agenda=agenda.key):
                self.assertIn(
                    "OR = {\n"
                    "\t\t\thas_estate_agenda_auto_completion = "
                    f"{{ estate = {agenda.estate} }}\n"
                    f"\t\t\tNOT = {{ {agenda.requirement} }}",
                    text,
                )

    def test_checked_in_outputs_are_deterministic(self) -> None:
        for path, expected in self.outputs.items():
            with self.subTest(path=path.relative_to(MAIN_ROOT)):
                self.assertTrue(path.is_file())
                self.assertEqual(expected, path.read_bytes())

    def test_all_generated_gameplay_files_parse(self) -> None:
        suffixes = {".txt"}
        for path in self.outputs:
            if path.suffix in suffixes:
                with self.subTest(path=path.relative_to(MAIN_ROOT)):
                    parse_file(path)

    def test_exact_vanilla_overrides_register_all_estate_content(self) -> None:
        for estate, relative in BUILDER.ESTATE_FILES.items():
            text = (MAIN_ROOT / relative).read_bytes().decode("cp1252")
            for privilege in BUILDER._privileges_for(estate):
                self.assertEqual(1, text.count(f"\t\t{privilege.key}\n"))
            for agenda in BUILDER._agendas_for(estate):
                self.assertEqual(1, text.count(f"\t\t{agenda.key}\n"))
            for state, _trigger, _names in BUILDER.NAME_MATRIX:
                self.assertEqual(
                    1,
                    text.count(
                        f"desc = jxp_a_estate_name_{BUILDER.ESTATE_SHORT[estate]}_{state}"
                    ),
                )

        village_text = (
            MAIN_ROOT / "common/estates/jxp_a_110_japanese_estates.txt"
        ).read_text(encoding="utf-8")
        dynamic_text = (
            MAIN_ROOT / "customizable_localization/jxp_a_110_estate_names.txt"
        ).read_text(encoding="utf-8")
        for state, _trigger, _names in BUILDER.NAME_MATRIX:
            self.assertEqual(
                1,
                village_text.count(
                    f"desc = jxp_a_estate_name_villages_{state}"
                ),
            )
            self.assertEqual(
                1,
                dynamic_text.count(
                    f"localisation_key = jxp_a_estate_name_villages_{state}"
                ),
            )

    def test_fourth_estate_is_in_call_diet_and_seize_land_contracts(self) -> None:
        event_text = (
            MAIN_ROOT / "events/EstatePrivilegesAndAgendasEvents.txt"
        ).read_bytes().decode("cp1252")
        helper_text = (
            MAIN_ROOT / "common/scripted_effects/01_scripted_effects_for_estates.txt"
        ).read_bytes().decode("cp1252")
        needles = (
            "start_estate_agenda = jxp_estate_village_communes",
            "seize_land_estate_effect = { estate = jxp_estate_village_communes }",
            "clr_country_flag = jxp_estate_village_communes_present_agenda",
        )
        for needle in needles:
            self.assertIn(needle, event_text)
        for needle in (
            "$estate_action$ = jxp_estate_village_communes",
            "estate = jxp_estate_village_communes",
            "type = peasant_rebels",
            "on_completed_agenda_effect_jxp_estate_village_communes = {}",
            "auto_complete_estate_agenda_jxp_estate_village_communes",
        ):
            self.assertIn(needle, helper_text)

    def test_cleanup_and_interactions_are_explicit(self) -> None:
        effects = (
            MAIN_ROOT / "common/scripted_effects/jxp_a_110_estate_effects.txt"
        ).read_text(encoding="utf-8")
        for privilege in BUILDER.PRIVILEGES:
            self.assertIn(f"remove_estate_privilege = {privilege.key}", effects)
        self.assertIn("jxp_a_reconcile_japanese_estates_effect = {", effects)
        self.assertIn(
            "jxp_a_reconcile_estates_for_route = {\n"
            "\tjxp_a_reconcile_japanese_estates_effect = yes\n"
            "}",
            effects,
        )
        self.assertIn("set_country_flag = jxp_iface_a_estates_ready", effects)

        decisions = (
            MAIN_ROOT / "decisions/jxp_a_110_estate_interactions.txt"
        ).read_text(encoding="utf-8")
        events = (
            MAIN_ROOT / "events/jxp_a_110_estate_interactions.txt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("estate_interaction =", decisions + events)
        for short, _estate, event_id, *_rest in BUILDER.INTERACTIONS:
            self.assertIn(f"jxp_a_convene_{short}_estate_council = {{", decisions)
            self.assertIn(f"id = {event_id}", events)
            for suffix in ("a", "b", "c", "z"):
                self.assertIn(f"name = {event_id}.{suffix}", events)

    def test_legacy_privileges_are_preserved_and_duplicates_migrate_transactionally(self) -> None:
        self.assertEqual(5, len(BUILDER.LEGACY_PRIVILEGE_EQUIVALENTS))
        privileges = (
            MAIN_ROOT / "common/estate_privileges/jxp_a_110_japanese_privileges.txt"
        ).read_text(encoding="utf-8")
        effects = (
            MAIN_ROOT / "common/scripted_effects/jxp_a_110_estate_effects.txt"
        ).read_text(encoding="utf-8")

        for old, new, estate in BUILDER.LEGACY_PRIVILEGE_EQUIVALENTS:
            with self.subTest(old=old, new=new):
                vanilla_hits = list(
                    (GAME_ROOT / "common/estate_privileges").glob("*.txt")
                )
                self.assertTrue(
                    any(f"{old} = {{" in path.read_text(encoding="utf-8", errors="ignore") for path in vanilla_hits),
                    f"pinned vanilla privilege missing: {old}",
                )
                start, end = BUILDER._named_blocks(privileges, new)[0]
                block = privileges[start:end]
                valid_start, valid_end = BUILDER._named_blocks(block, "is_valid")[0]
                valid = block[valid_start:valid_end]
                self.assertIn(f"has_estate_privilege = {new}", valid)
                self.assertIn(
                    f"NOT = {{ has_estate_privilege = {old} }}",
                    valid,
                )
                self.assertIn(
                    f"NOT = {{ has_estate_privilege = {old} }}",
                    block,
                )
                self.assertIn(f"has_estate_privilege = {old}", effects)
                self.assertIn(f"has_estate_privilege = {new}", effects)
                self.assertIn(f"remove_estate_privilege = {new}", effects)
                self.assertNotIn(f"remove_estate_privilege = {old}", effects)
                self.assertIn(f"has_estate = {estate}", effects)

        self.assertIn("jxp_a_migrate_legacy_estate_privileges_effect = {", effects)
        self.assertIn(
            "limit = { NOT = { has_country_flag = jxp_a_estate_privilege_migration_v2 } }",
            effects,
        )
        self.assertIn(
            "set_country_flag = jxp_a_estate_privilege_migration_v2",
            effects,
        )
        self.assertIn(
            "desc = jxp_a_estate_val_privilege_transition loyalty = 5 duration = 1825",
            effects,
        )
        self.assertEqual(
            len(BUILDER.CONTROLLED_TRANSITION_KEYS),
            len(BUILDER.PRIVILEGE_TRANSITION_FLAGS),
        )
        for flag in BUILDER.PRIVILEGE_TRANSITION_FLAGS.values():
            self.assertIn(f"had_country_flag = {{ flag = {flag} days = 1825 }}", effects)
            self.assertIn(f"clr_country_flag = {flag}", effects)

    def test_privilege_and_interaction_ai_uses_distinct_contexts(self) -> None:
        privileges = (
            MAIN_ROOT / "common/estate_privileges/jxp_a_110_japanese_privileges.txt"
        ).read_text(encoding="utf-8")
        ai_blocks = []
        for privilege in BUILDER.PRIVILEGES:
            start, end = BUILDER._named_blocks(privileges, privilege.key)[0]
            block = privileges[start:end]
            nested = BUILDER._named_blocks(block, "ai_will_do")
            self.assertEqual(1, len(nested), privilege.key)
            ai = block[nested[0][0] : nested[0][1]]
            self.assertGreaterEqual(ai.count("modifier = {"), 5, privilege.key)
            ai_blocks.append(ai)
        self.assertGreaterEqual(len(set(ai_blocks)), 16)

        decisions = (
            MAIN_ROOT / "decisions/jxp_a_110_estate_interactions.txt"
        ).read_text(encoding="utf-8")
        decision_ai = []
        for short, _estate, _event_id, *_rest in BUILDER.INTERACTIONS:
            key = f"jxp_a_convene_{short}_estate_council"
            start, end = BUILDER._named_blocks(decisions, key)[0]
            block = decisions[start:end]
            nested = BUILDER._named_blocks(block, "ai_will_do")
            self.assertEqual(1, len(nested), key)
            decision_ai.append(block[nested[0][0] : nested[0][1]])
        self.assertEqual(4, len(set(decision_ai)))

        events = (
            MAIN_ROOT / "events/jxp_a_110_estate_interactions.txt"
        ).read_text(encoding="utf-8")
        option_ai = [
            events[start:end]
            for start, end in BUILDER._named_blocks(events, "ai_chance")
        ]
        self.assertEqual(16, len(option_ai))
        self.assertGreaterEqual(len(set(option_ai)), 12)
        self.assertNotIn("ai_chance = { factor = 1 }", events)

        combined = privileges + decisions + events
        for token in (
            "num_of_loans = 3",
            "monthly_income = 20",
            "is_at_war = yes",
            "current_age = age_of_reformation",
            "jxp_a_market_stage_at_least_2_trigger = yes",
            "jxp_a_company_has_at_least_1_trigger = yes",
            "religion = shinto",
            "NOT = { stability = 0 }",
            "has_spawned_rebels = anti_tax_rebels",
            "has_government_attribute = jxp_toyotomi_regents_council",
        ):
            self.assertIn(token, combined)

        fudai_start, fudai_end = BUILDER._named_blocks(
            privileges, "jxp_a_nobles_fudai_magistrates"
        )[0]
        self.assertIn(
            "has_government_attribute = jxp_toyotomi_regents_council",
            privileges[fudai_start:fudai_end],
        )

    def test_localisation_uses_source_to_bom_active_pipeline(self) -> None:
        source_path = (
            MAIN_ROOT
            / "localisation_source"
            / "jxp_a_110_estates_l_english_utf8_source.yml"
        )
        active_path = (
            MAIN_ROOT / "localisation" / "jxp_a_110_estates_l_english.yml"
        )
        self.assertFalse(source_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertTrue(active_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(self.outputs[source_path], source_path.read_bytes())
        self.assertEqual(self.outputs[active_path], active_path.read_bytes())
        expected_active = (
            b"\xef\xbb\xbf"
            + BUILDER._escape_module().escape_text(
                source_path.read_text(encoding="utf-8")
            ).encode("utf-8")
        )
        self.assertEqual(expected_active, active_path.read_bytes())
        active = active_path.read_bytes().decode("utf-8-sig")
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in active))
        source = source_path.read_text(encoding="utf-8")
        self.assertIn(" jxp_estate_village_communes_ownership:0 ", source)
        self.assertIn(" jxp_a_estate_val_privilege_transition:0 ", source)
        for key, title, desc in BUILDER.VISIBLE_STATE_LOCALISATION:
            self.assertIn(f" {key}:0 \"{title}\"", source)
            self.assertIn(f" {key}_desc:0 \"{desc}\"", source)
        for state, _trigger, _names in BUILDER.NAME_MATRIX:
            for estate in BUILDER.ESTATE_ORDER:
                self.assertIn(
                    " jxp_a_estate_name_"
                    f"{BUILDER.ESTATE_SHORT[estate]}_{state}:0 ",
                    source,
                )

    def test_player_visible_estate_state_flags_have_direct_labels(self) -> None:
        expected = {
            f"jxp_a_{short}_estate_interaction_recent"
            for short, *_rest in BUILDER.INTERACTIONS
        }
        registered = {
            key: (title, desc)
            for key, title, desc in BUILDER.VISIBLE_STATE_LOCALISATION
        }
        self.assertEqual(expected, set(registered))

        decisions = (
            MAIN_ROOT / "decisions/jxp_a_110_estate_interactions.txt"
        ).read_text(encoding="utf-8")
        privileges = (
            MAIN_ROOT / "common/estate_privileges/jxp_a_110_japanese_privileges.txt"
        ).read_text(encoding="utf-8")
        for key in sorted(expected):
            with self.subTest(key=key):
                self.assertIn(key, decisions + privileges)
                title, desc = registered[key]
                self.assertGreaterEqual(len(title), 6)
                self.assertGreaterEqual(len(desc), 20)
                self.assertNotIn("jxp_", title + desc)

        shared = "jxp_iface_overseas_charter_ready"
        self.assertIn(shared, decisions + privileges)
        owners = [
            path
            for path in (MAIN_ROOT / "localisation_source").glob("*.yml")
            if f" {shared}:0 " in path.read_text(encoding="utf-8-sig")
        ]
        self.assertEqual(
            [MAIN_ROOT / "localisation_source/jxp_85_ui_flag_labels_l_english_utf8_source.yml"],
            owners,
        )


if __name__ == "__main__":
    unittest.main()
