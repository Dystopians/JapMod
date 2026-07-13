"""Pinned EU4 1.37.5 and JXP contracts for Mandate-of-Heaven gameplay."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .clausewitz import (
    Object,
    Scalar,
    bare_scalars,
    find_assignments,
    find_objects,
    first_object,
    first_scalar,
)
from .core import CheckResult, ValidationContext


MANIFEST_FILE = Path(__file__).with_name("vanilla_1_37_5_manifest.json")
VANILLA_CB_FILE = Path("common/cb_types/00_cb_types.txt")
VANILLA_WARGOAL_FILE = Path("common/wargoal_types/00_wargoal_types.txt")
VANILLA_REFORM_FILE = Path("common/imperial_reforms/01_china.txt")
VANILLA_EVENT_FILE = Path("events/ChineseEmpire.txt")

JXP_CB_FILE = Path("common/cb_types/jxp_08_cb_types.txt")
JXP_WARGOAL_FILE = Path("common/wargoal_types/jxp_08_wargoal_types.txt")
JXP_REFORM_FILE = Path("common/imperial_reforms/jxp_08_celestial_reforms.txt")
JXP_EFFECT_FILE = Path("common/scripted_effects/jxp_03_overseas_effects.txt")
JXP_MISSION_FILE = Path("missions/jxp_03_overseas_missions.txt")
JXP_DECISION_FILE = Path("decisions/jxp_03_overseas_decisions.txt")
JXP_DEBUG_FILE = Path("decisions/jxp_debug_decisions.txt")
JXP_DEBUG_EFFECT_FILE = Path("common/scripted_effects/jxp_debug_effects.txt")
JXP_LOCALISATION_FILE = Path(
    "localisation_source/jxp_08_l_english_utf8_source.yml"
)

HAKKO_MISSION = "jxp_mission_eastasia_claim_mandate"
HAKKO_UNLOCK_EFFECT = "jxp_unlock_hakko_ichiu_reform_effect"
HAKKO_PASSED_FLAG = "jxp_hakko_ichiu_reform_passed"
MANDATE_FALLBACK_FLAG = "jxp_mandate_claim_fallback"
EAST_ASIA_SUPERREGIONS = frozenset(
    {"china_superregion", "far_east_superregion"}
)
EXPECTED_UNLOCK_CALLERS = frozenset(
    {
        (
            JXP_MISSION_FILE.as_posix(),
            (
                "jxp_japan_pacific_missions",
                HAKKO_MISSION,
                "effect",
                "if",
            ),
        ),
        (
            JXP_DEBUG_FILE.as_posix(),
            (
                "country_decisions",
                "jxp_debug_unlock_hakko_ichiu_reform",
                "effect",
            ),
        ),
    }
)


def _direct_objects(obj: Object | None, key: str) -> tuple[Object, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value
        for entry in obj.entries
        if entry.key == key
        and entry.operator == "="
        and isinstance(entry.value, Object)
    )


def _has_direct(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any(
        entry.key == key
        and entry.operator == "="
        and isinstance(entry.value, Scalar)
        and entry.value.text == value
        for entry in obj.entries
    )


def _has(obj: Object | None, key: str, value: str) -> bool:
    return obj is not None and bool(find_assignments(obj, key, value))


def _has_direct_not(obj: Object | None, key: str, value: str) -> bool:
    return any(
        len(block.entries) == 1 and _has_direct(block, key, value)
        for block in _direct_objects(obj, "NOT")
    )


def _has_direct_or(obj: Object | None, assignments: frozenset[tuple[str, str]]) -> bool:
    return any(
        frozenset(
            (entry.key, entry.value.text)
            for entry in block.entries
            if entry.key is not None
            and entry.operator == "="
            and isinstance(entry.value, Scalar)
        )
        == assignments
        for block in _direct_objects(obj, "OR")
    )


def _bare_values(obj: Object | None) -> frozenset[str]:
    return frozenset(value.text for value in bare_scalars(obj))


def _event_by_id(root: Object, event_id: str) -> Object | None:
    for event in _direct_objects(root, "country_event"):
        if first_scalar(event, "id") == event_id:
            return event
    return None


def _unique_object(root: Object | None, key: str) -> Object | None:
    if root is None:
        return None
    matches = tuple(find_objects(root, key))
    if len(matches) != 1 or not isinstance(matches[0][1].value, Object):
        return None
    return matches[0][1].value


def _has_modifier(obj: Object | None, modifier: str) -> bool:
    if obj is None:
        return False
    return any(
        isinstance(entry.value, Object)
        and _has_direct(entry.value, "name", modifier)
        for _path, entry in find_objects(obj, "add_country_modifier")
    )


def _has_owned_province_cleanup(
    on_effect: Object | None,
    *,
    guard_key: str,
    guard_value: str,
    effect_key: str,
    effect_value: str,
) -> bool:
    for block in _direct_objects(on_effect, "every_owned_province"):
        limit = first_object(block, "limit")
        if _has_direct(limit, guard_key, guard_value) and _has_direct(
            block, effect_key, effect_value
        ):
            return True
    return False


def _load_document(
    context: ValidationContext,
    relative: Path,
    result: CheckResult,
    code: str,
) -> Object | None:
    source = context.mod_root / relative
    document = context.document(source) if source.is_file() else None
    if document is None:
        result.add(code, f"missing or unparseable {relative.as_posix()}", relative.as_posix())
        return None
    return document.root


def _check_vanilla_hashes(game_root: Path, result: CheckResult) -> int:
    try:
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        records = manifest["mandate_files"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        result.add(
            "mandate.vanilla_manifest",
            f"could not read pinned Mandate manifest: {exc}",
            MANIFEST_FILE.name,
        )
        return 0

    verified = 0
    for record in records:
        try:
            relative = Path(record["path"])
            expected = str(record["sha256"]).lower()
        except (KeyError, TypeError):
            result.add(
                "mandate.vanilla_manifest",
                "Mandate manifest contains a malformed record",
                MANIFEST_FILE.name,
            )
            continue
        source = game_root / relative
        if not source.is_file():
            result.add(
                "mandate.vanilla_file_missing",
                f"pinned EU4 1.37.5 source is missing: {relative.as_posix()}",
                relative.as_posix(),
            )
            continue
        actual = sha256(source.read_bytes()).hexdigest()
        if actual != expected:
            result.add(
                "mandate.vanilla_hash",
                f"{relative.as_posix()} hash {actual} does not match pinned 1.37.5 {expected}",
                relative.as_posix(),
            )
            continue
        verified += 1
    return verified


def _check_vanilla_acquisition(game_root: Path, result: CheckResult) -> None:
    game = ValidationContext(game_root)
    cb_root = _load_document(game, VANILLA_CB_FILE, result, "mandate.vanilla_cb_file")
    wargoal_root = _load_document(
        game, VANILLA_WARGOAL_FILE, result, "mandate.vanilla_wargoal_file"
    )
    reform_root = _load_document(
        game, VANILLA_REFORM_FILE, result, "mandate.vanilla_reform_file"
    )
    event_root = _load_document(
        game, VANILLA_EVENT_FILE, result, "mandate.vanilla_event_file"
    )

    cb = first_object(cb_root, "cb_take_mandate")
    self_gate = first_object(cb, "prerequisites_self")
    target_gate = first_object(cb, "prerequisites")
    target_from = first_object(target_gate, "FROM")
    religion_groups = frozenset(
        {("religion_group", "pagan"), ("religion_group", "eastern")}
    )
    if not (
        _has_direct(cb, "valid_for_subject", "no")
        and _has_direct(self_gate, "has_dlc", "Mandate of Heaven")
        and _has_direct(self_gate, "is_subject", "no")
        and _has_direct_not(self_gate, "has_reform", "shogunate")
        and _has_direct(self_gate, "is_revolutionary", "no")
        and _has_direct_or(self_gate, religion_groups)
        and _has_direct(target_gate, "is_neighbor_of", "FROM")
        and _has_direct(target_from, "is_emperor_of_china", "yes")
        and _has_direct_not(target_gate, "truce_with", "FROM")
        and _has_direct(cb, "war_goal", "take_capital_take_mandate")
    ):
        result.add(
            "mandate.vanilla_acquisition_cb",
            "pinned cb_take_mandate no longer proves the independent "
            "Eastern/pagan neighbor-of-Emperor acquisition path",
            VANILLA_CB_FILE.as_posix(),
        )

    wargoal = first_object(wargoal_root, "take_capital_take_mandate")
    attacker = first_object(wargoal, "attacker")
    peace_options = first_object(attacker, "peace_options")
    if not (
        _has_direct(wargoal, "type", "take_capital")
        and _has_direct(attacker, "badboy_factor", "0.5")
        and _has_direct(attacker, "peace_cost_factor", "0.5")
        and {"po_demand_provinces", "po_take_mandate"}.issubset(
            _bare_values(peace_options)
        )
    ):
        result.add(
            "mandate.vanilla_take_mandate_peace",
            "pinned take_capital_take_mandate no longer exposes "
            "po_take_mandate with the vanilla cost/AE contract",
            VANILLA_WARGOAL_FILE.as_posix(),
        )

    vanilla_reform = first_object(reform_root, "military_governors_decision")
    vanilla_emperor = first_object(vanilla_reform, "emperor")
    if not (
        _has_direct(vanilla_reform, "empire", "celestial_empire")
        and _has_direct(vanilla_emperor, "core_creation", "-0.1")
    ):
        result.add(
            "mandate.vanilla_reform_schema",
            "pinned imperial reform schema no longer proves "
            "empire = celestial_empire with emperor-scoped modifiers",
            VANILLA_REFORM_FILE.as_posix(),
        )

    religion_event = (
        _event_by_id(event_root, "celestial_empire_events.2")
        if event_root is not None
        else None
    )
    religion_trigger = first_object(religion_event, "trigger")
    culture_event = (
        _event_by_id(event_root, "celestial_empire_events.3")
        if event_root is not None
        else None
    )
    culture_trigger = first_object(culture_event, "trigger")
    if not (
        _has_direct(religion_trigger, "has_dlc", "Mandate of Heaven")
        and _has_direct(religion_trigger, "is_emperor_of_china", "yes")
        and _has_direct_not(religion_trigger, "religion", "confucianism")
        and _has_direct_not(
            religion_trigger, "has_country_flag", "reacted_to_confucianism_event"
        )
        and _has_direct(culture_trigger, "has_dlc", "Mandate of Heaven")
        and _has_direct(culture_trigger, "is_emperor_of_china", "yes")
        and _has_direct_not(culture_trigger, "culture_group", "east_asian")
        and _has_direct_not(
            culture_trigger, "has_country_flag", "had_sinicization_event"
        )
        and _has(culture_event, "name", "resistance_to_cultural_changes")
    ):
        result.add(
            "mandate.vanilla_pressure_events",
            "pinned ChineseEmpire events no longer prove the two country-flag "
            "exemptions and cultural-resistance state",
            VANILLA_EVENT_FILE.as_posix(),
        )


def _check_mod_contract(context: ValidationContext, result: CheckResult) -> None:
    cb_root = _load_document(context, JXP_CB_FILE, result, "mandate.cb_file")
    wargoal_root = _load_document(
        context, JXP_WARGOAL_FILE, result, "mandate.wargoal_file"
    )
    reform_root = _load_document(context, JXP_REFORM_FILE, result, "mandate.reform_file")
    effect_root = _load_document(context, JXP_EFFECT_FILE, result, "mandate.effect_file")
    mission_root = _load_document(context, JXP_MISSION_FILE, result, "mandate.mission_file")
    decision_root = _load_document(
        context, JXP_DECISION_FILE, result, "mandate.decision_file"
    )
    debug_decision_root = _load_document(
        context, JXP_DEBUG_FILE, result, "mandate.debug_decision_file"
    )
    debug_effect_root = _load_document(
        context, JXP_DEBUG_EFFECT_FILE, result, "mandate.debug_effect_file"
    )

    vanilla_cb_overrides: list[str] = []
    cb_directory = context.mod_root / "common" / "cb_types"
    cb_sources = sorted(cb_directory.glob("*.txt")) if cb_directory.is_dir() else ()
    for source in cb_sources:
        document = context.document(source)
        if document is not None and first_object(document.root, "cb_take_mandate"):
            vanilla_cb_overrides.append(context.relative(source))
    if vanilla_cb_overrides:
        result.add(
            "mandate.vanilla_cb_override",
            "JXP must consume, not override, pinned vanilla cb_take_mandate; "
            f"found {vanilla_cb_overrides}",
        )

    cb = first_object(cb_root, "cb_jxp_hakko_ichiu")
    self_gate = first_object(cb, "prerequisites_self")
    target_gate = first_object(cb, "prerequisites")
    target_from = first_object(target_gate, "FROM")
    target_provinces = first_object(target_from, "any_owned_province")
    region_contract = frozenset(
        ("superregion", region) for region in EAST_ASIA_SUPERREGIONS
    )
    if not _has_direct(self_gate, "jxp_is_japanese_polity_trigger", "yes"):
        result.add(
            "mandate.cb_identity",
            "Hakko Ichiu CB must independently require Japanese-polity identity",
            JXP_CB_FILE.as_posix(),
        )
    if not (
        _has_direct(cb, "valid_for_subject", "no")
        and _has_direct(self_gate, "has_dlc", "Mandate of Heaven")
        and _has_direct(self_gate, "is_emperor_of_china", "yes")
        and _has_direct(self_gate, "has_country_flag", HAKKO_PASSED_FLAG)
        and _has_direct_or(target_provinces, region_contract)
        and _has_direct(cb, "war_goal", "jxp_hakko_ichiu_wargoal")
    ):
        result.add(
            "mandate.cb_scope",
            "Hakko Ichiu CB must be DLC/emperor/reform-gated and target only China/Far East owners",
            JXP_CB_FILE.as_posix(),
        )

    wargoal = first_object(wargoal_root, "jxp_hakko_ichiu_wargoal")
    attacker = first_object(wargoal, "attacker")
    defender = first_object(wargoal, "defender")
    allowed = first_object(attacker, "allowed_provinces")
    attacker_peace = first_object(attacker, "peace_options")
    if not (
        _has_direct(wargoal, "type", "take_capital")
        and _has_direct(attacker, "badboy_factor", "0.5")
        and _has_direct(attacker, "peace_cost_factor", "1.0")
        and _has_direct_or(allowed, region_contract)
        and _bare_values(attacker_peace) == frozenset({"po_demand_provinces"})
        and _has_direct(defender, "badboy_factor", "1")
        and _has_direct(defender, "peace_cost_factor", "1")
        and _has_direct(wargoal, "war_name", "JXP_HAKKO_ICHIU_WAR_NAME")
    ):
        result.add(
            "mandate.cb_ae",
            "Hakko Ichiu wargoal must keep 50% attacker AE only for "
            "China/Far East province demands",
            JXP_WARGOAL_FILE.as_posix(),
        )

    reform = first_object(reform_root, "jxp_hakko_ichiu_reform")
    emperor = first_object(reform, "emperor")
    on_effect = first_object(reform, "on_effect")
    off_effect = first_object(reform, "off_effect")
    if not (
        _has_direct(reform, "empire", "celestial_empire")
        and _has_direct(emperor, "core_creation", "-0.10")
        and _has_direct(on_effect, "set_country_flag", HAKKO_PASSED_FLAG)
        and _has_direct(
            on_effect, "set_country_flag", "reacted_to_confucianism_event"
        )
        and _has_direct(on_effect, "set_country_flag", "had_sinicization_event")
        and _has_owned_province_cleanup(
            on_effect,
            guard_key="has_province_flag",
            guard_value="resentment_to_sinicization",
            effect_key="clr_province_flag",
            effect_value="resentment_to_sinicization",
        )
        and _has_owned_province_cleanup(
            on_effect,
            guard_key="has_province_modifier",
            guard_value="resistance_to_cultural_changes",
            effect_key="remove_province_modifier",
            effect_value="resistance_to_cultural_changes",
        )
        and _has_direct(off_effect, "clr_country_flag", HAKKO_PASSED_FLAG)
    ):
        result.add(
            "mandate.celestial_exemption",
            "Hakko reform must use vanilla pressure flags, clear existing "
            "resistance, and own its CB flag lifecycle",
            JXP_REFORM_FILE.as_posix(),
        )

    claim_reward = first_object(effect_root, "jxp_apply_mandate_claim_reward_effect")
    positive_dlc_branch = any(
        _has_direct(first_object(block, "limit"), "has_dlc", "Mandate of Heaven")
        and _has_direct(first_object(block, "limit"), "is_emperor_of_china", "yes")
        and _has_direct(block, "add_mandate", "10")
        for block in _direct_objects(claim_reward, "if")
    )
    fallback_branch = any(
        _has_direct(block, "set_country_flag", MANDATE_FALLBACK_FLAG)
        and _has_modifier(block, "jxp_celestial_diplomacy")
        and _has_modifier(block, "jxp_solar_court_recognition")
        for block in _direct_objects(claim_reward, "else")
    )
    if not positive_dlc_branch or not fallback_branch:
        result.add(
            "mandate.no_dlc_fallback",
            "claim reward must preserve the real-emperor Mandate branch "
            "and the non-Mandate fallback state",
            JXP_EFFECT_FILE.as_posix(),
        )

    mission = _unique_object(mission_root, HAKKO_MISSION)
    mission_trigger = first_object(mission, "trigger")
    mission_effect = first_object(mission, "effect")
    mission_alternatives = frozenset(
        {
            ("is_emperor_of_china", "yes"),
            ("has_country_flag", MANDATE_FALLBACK_FLAG),
            ("has_country_modifier", "jxp_solar_court_recognition"),
        }
    )
    guarded_unlock = any(
        _has_direct(first_object(block, "limit"), "has_dlc", "Mandate of Heaven")
        and _has_direct(block, HAKKO_UNLOCK_EFFECT, "yes")
        for block in _direct_objects(mission_effect, "if")
    )
    if not (
        _has_direct(mission_trigger, "has_country_flag", "jxp_mandate_claimed")
        and _has_direct_or(mission_trigger, mission_alternatives)
        and _has_direct(
            mission_effect, "jxp_apply_mandate_claim_reward_effect", "yes"
        )
        and guarded_unlock
    ):
        result.add(
            "mandate.mission_unlock_contract",
            "mandate-claim mission must bridge real Emperor and fallback "
            "states while DLC-guarding the Hakko unlock",
            JXP_MISSION_FILE.as_posix(),
        )

    claim_decisions = first_object(decision_root, "country_decisions")
    claim_decision = first_object(claim_decisions, "jxp_decision_claim_mandate_japan")
    claim_decision_effect = first_object(claim_decision, "effect")
    if not _has_direct(
        claim_decision_effect, "jxp_apply_mandate_claim_reward_effect", "yes"
    ):
        result.add(
            "mandate.claim_entry",
            "Japanese Mandate claim decision must route through the canonical claim reward",
            JXP_DECISION_FILE.as_posix(),
        )

    unlock_callers = frozenset(
        (context.relative(occurrence.source), occurrence.path)
        for occurrence in context.assignment_occurrences(
            HAKKO_UNLOCK_EFFECT, "yes", files=context.script_files()
        )
    )
    if unlock_callers != EXPECTED_UNLOCK_CALLERS:
        result.add(
            "mandate.mission_only_unlock",
            "Hakko unlock may be called only by the mandate-claim mission and its debug-only tool; "
            f"found {sorted(unlock_callers)}",
        )

    debug_decisions = first_object(debug_decision_root, "country_decisions")
    emperor_scaffold = first_object(
        debug_decisions, "jxp_debug_prepare_hakko_emperor"
    )
    scaffold_potential = first_object(emperor_scaffold, "potential")
    scaffold_decision_effect = first_object(emperor_scaffold, "effect")
    scaffold_effect = first_object(
        debug_effect_root, "jxp_debug_prepare_hakko_emperor_effect"
    )
    scaffold_hidden = first_object(scaffold_effect, "hidden_effect")
    if not (
        _has_direct(scaffold_potential, "ai", "no")
        and _has_direct(scaffold_potential, "has_dlc", "Mandate of Heaven")
        and _has_direct(
            scaffold_potential, "has_country_flag", "jxp_debug_enabled"
        )
        and _has_direct(
            scaffold_decision_effect,
            "jxp_debug_prepare_hakko_emperor_effect",
            "yes",
        )
        and _has(scaffold_hidden, "set_emperor_of_china", "ROOT")
        and _has(scaffold_hidden, "add_mandate", "100")
        and _has(
            scaffold_hidden,
            "jxp_reconcile_hakko_ichiu_reform_visibility_effect",
            "yes",
        )
        and not _has(scaffold_hidden, HAKKO_UNLOCK_EFFECT, "yes")
        and not _has(scaffold_hidden, "set_country_flag", HAKKO_PASSED_FLAG)
    ):
        result.add(
            "mandate.debug_emperor_scaffold",
            "Hakko runtime scaffold must create only a DLC-gated Japanese Emperor "
            "fixture without unlocking or passing the reform",
            JXP_DEBUG_EFFECT_FILE.as_posix(),
        )

    localisation_source = context.mod_root / JXP_LOCALISATION_FILE
    localisation = (
        localisation_source.read_text(encoding="utf-8-sig")
        if localisation_source.is_file()
        else ""
    )
    required_keys = {
        "jxp_hakko_ichiu_reform",
        "jxp_hakko_ichiu_reform_desc",
        "cb_jxp_hakko_ichiu",
        "cb_jxp_hakko_ichiu_desc",
        "jxp_hakko_ichiu_wargoal",
        "jxp_hakko_ichiu_wargoal_desc",
        "JXP_HAKKO_ICHIU_COUNTRY_DESC",
        "JXP_HAKKO_ICHIU_PROV_DESC",
        "JXP_HAKKO_ICHIU_WAR_NAME",
    }
    present_keys = {
        line.lstrip().split(":", 1)[0]
        for line in localisation.splitlines()
        if ":" in line and not line.lstrip().startswith("#")
    }
    missing_keys = sorted(required_keys - present_keys)
    if missing_keys:
        result.add(
            "mandate.localisation",
            f"Hakko CB/reform localisation is missing {missing_keys}",
            JXP_LOCALISATION_FILE.as_posix(),
        )


def check_mandate_contract(
    context: ValidationContext,
    game_root: Path,
) -> CheckResult:
    """Validate JXP-010 without treating static evidence as runtime proof."""

    result = CheckResult("Mandate acquisition, Hakko CB, and DLC fallback")
    pinned_files = _check_vanilla_hashes(game_root, result)
    _check_vanilla_acquisition(game_root, result)
    _check_mod_contract(context, result)
    result.metrics.update(
        {
            "pinned_vanilla_files": pinned_files,
            "hakko_ae_factor": 0.5,
            "hakko_superregions": len(EAST_ASIA_SUPERREGIONS),
            "mission_unlock_callers": len(EXPECTED_UNLOCK_CALLERS),
            "debug_emperor_scaffolds": 1,
        }
    )
    result.notes.extend(
        (
            "Vanilla 1.37.5 cb_take_mandate supplies the actual acquisition "
            "path and po_take_mandate peace option.",
            "JXP Hakko Ichiu is a post-acquisition mission unlock; its conquest "
            "CB is not a replacement Take-Mandate CB.",
            "Runtime UI visibility, CB availability, AE calculation, "
            "peace-option execution, and no-DLC pacing remain permission-gated.",
        )
    )
    result.summary = (
        f"{pinned_files}/4 pinned vanilla files; mission-only Hakko unlock; "
        "50% AE across 2 East Asian superregions; fallback preserved"
    )
    return result
