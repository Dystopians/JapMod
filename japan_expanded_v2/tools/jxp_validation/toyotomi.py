"""Validate the Toyotomi identity, migration, art, and dated-history contract."""

from __future__ import annotations

import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path
import re
import sys
from types import ModuleType

from PIL import Image, ImageChops

from .clausewitz import (
    Object,
    Scalar,
    bare_scalars,
    entries_named,
    find_assignments,
    find_objects,
    first_object,
    first_scalar,
)
from .core import CheckResult, ValidationContext
from .create_legacy_bom_mission_aliases_v0241 import FILE_PREFIX as LEGACY_BOM_FILE_PREFIX
from .missions import Profile, evaluate_potential, extract_mission_series


TOYOTOMI_START = (1586, 1, 1)
SEKIGAHARA = (1600, 10, 21)
OSAKA_FALL = (1615, 6, 4)
TOYOTOMI_GOVERNMENT_REFORM = "jxp_toyotomi_kampaku_taiko_reform"
EXPECTED_MISSIONS = (
    "jxp_mission_oda_rakuichi_network",
    "jxp_mission_oda_tenka_fubu_mainline",
    "jxp_mission_oda_azuchi_statutes_mainline",
    "jxp_mission_toyotomi_name_and_osaka",
    "jxp_mission_toyotomi_taiko_cadaster",
    "jxp_mission_toyotomi_realm_settlement",
)
EXPECTED_TOYOTOMI_SERIES = {
    1: "jxp_japan_state_missions",
    2: "jxp_japan_court_missions",
    3: "jxp_toyotomi_realm_missions",
    4: "jxp_toyotomi_court_missions",
    5: "jxp_toyotomi_horizon_missions",
}
EXPECTED_TOYOTOMI_MISSIONS = {
    "jxp_toyotomi_realm_missions": (
        "jxp_mission_toyotomi_yamazaki_settlement",
        "jxp_mission_toyotomi_kampaku_appointment",
        "jxp_mission_toyotomi_cadaster_realm",
        "jxp_mission_toyotomi_sword_hunt_realm",
        "jxp_mission_toyotomi_sobuji_order",
        "jxp_mission_toyotomi_five_commissions",
        "jxp_mission_toyotomi_settle_succession",
    ),
    "jxp_toyotomi_court_missions": (
        "jxp_mission_toyotomi_osaka_castle_town",
        "jxp_mission_toyotomi_jurakudai_audiences",
        "jxp_mission_toyotomi_sakai_magistrates",
        "jxp_mission_toyotomi_kuraire_ledgers",
        "jxp_mission_toyotomi_gold_silver_offices",
        "jxp_mission_toyotomi_momoyama_patronage",
        "jxp_mission_toyotomi_taiko_testament",
    ),
    "jxp_toyotomi_horizon_missions": (
        "jxp_mission_toyotomi_kyushu_settlement",
        "jxp_mission_toyotomi_oshu_pacification",
        "jxp_mission_toyotomi_ryukyu_letters",
        "jxp_mission_toyotomi_tsushima_channel",
        "jxp_mission_toyotomi_continental_preparations",
        "jxp_mission_toyotomi_east_asian_negotiations",
        "jxp_mission_toyotomi_peace_beneath_heaven",
    ),
}


def _date(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def _document(
    context: ValidationContext,
    relative: str,
    result: CheckResult,
):
    path = context.mod_root / relative
    if not path.is_file():
        result.add("toyotomi.file_missing", "required Toyotomi file is missing", relative)
        return None
    document = context.document(path)
    if document is None:
        result.add(
            "toyotomi.parse",
            context.parse_errors.get(path.resolve(), "could not parse file"),
            relative,
        )
    return document


def _has(obj: Object | None, key: str, value: str) -> bool:
    return bool(obj is not None and find_assignments(obj, key, value))


def _has_negative(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any(
        bool(find_assignments(entry.value, key, value))
        for _path, entry in find_objects(obj, "NOT")
        if isinstance(entry.value, Object)
    )


def _event(document, event_id: str) -> Object | None:
    if document is None:
        return None
    for entry in entries_named(document.root, "country_event"):
        if isinstance(entry.value, Object) and first_scalar(entry.value, "id") == event_id:
            return entry.value
    return None


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _check_flag_assets(context: ValidationContext, result: CheckResult) -> None:
    tga_path = context.mod_root / "gfx/flags/TOY.tga"
    preview_path = context.mod_root / "gfx/flags/source/TOY_128_preview.png"
    source_path = context.mod_root / "gfx/flags/source/build_toyotomi_flag.py"
    for path in (tga_path, preview_path, source_path):
        if not path.is_file():
            result.add(
                "toyotomi.flag_missing",
                "deterministic Toyotomi flag asset/source is missing",
                context.relative(path),
            )
    if not all(path.is_file() for path in (tga_path, preview_path, source_path)):
        return
    try:
        module = _load_module(source_path, "_jxp_toyotomi_flag_builder")
        expected = module.render().resize((128, 128), Image.Resampling.LANCZOS)
        with Image.open(tga_path) as image:
            actual_tga = image.convert("RGB")
            tga_shape = (image.size, image.mode)
        with Image.open(preview_path) as image:
            actual_preview = image.convert("RGB")
            preview_shape = (image.size, image.mode)
        if tga_shape != ((128, 128), "RGB"):
            result.add(
                "toyotomi.flag_format",
                f"TOY.tga must be 128x128 RGB, found {tga_shape}",
                context.relative(tga_path),
            )
        if preview_shape != ((128, 128), "RGB"):
            result.add(
                "toyotomi.flag_format",
                f"TOY preview must be 128x128 RGB, found {preview_shape}",
                context.relative(preview_path),
            )
        if ImageChops.difference(expected, actual_tga).getbbox() is not None:
            result.add(
                "toyotomi.flag_stale",
                "TOY.tga pixels do not match the deterministic flag source",
                context.relative(tga_path),
            )
        if ImageChops.difference(expected, actual_preview).getbbox() is not None:
            result.add(
                "toyotomi.flag_stale",
                "Toyotomi preview pixels do not match the deterministic flag source",
                context.relative(preview_path),
            )
    except Exception as exc:
        result.add(
            "toyotomi.flag_validation",
            f"could not reproduce deterministic flag assets: {exc}",
            context.relative(source_path),
        )


def _check_identity(context: ValidationContext, result: CheckResult) -> None:
    tags = _document(context, "common/country_tags/jxp_tags.txt", result)
    if tags is not None and first_scalar(tags.root, "TOY") != "countries/TOY - Toyotomi.txt":
        result.add(
            "toyotomi.tag",
            "TOY must map exactly to countries/TOY - Toyotomi.txt",
            "common/country_tags/jxp_tags.txt",
        )

    country = _document(context, "common/countries/TOY - Toyotomi.txt", result)
    if country is not None:
        color = first_object(country.root, "color")
        color_values = tuple(value.text for value in bare_scalars(color))
        if color_values != ("72", "43", "91"):
            result.add(
                "toyotomi.country_color",
                f"Toyotomi color changed from the flag field contract: {color_values}",
                "common/countries/TOY - Toyotomi.txt",
            )
        ship_names = first_object(country.root, "ship_names")
        if len(bare_scalars(ship_names)) < 16:
            result.add(
                "toyotomi.ship_names",
                "TOY requires at least 16 localized ship names",
                "common/countries/TOY - Toyotomi.txt",
            )

    history = _document(context, "history/countries/TOY - Toyotomi.txt", result)
    if history is not None:
        start = first_object(history.root, "1586.1.1")
        monarch = first_object(start, "monarch")
        if (
            first_scalar(monarch, "name") != "秀吉"
            or first_scalar(monarch, "dynasty") != "丰臣"
        ):
            result.add(
                "toyotomi.ruler_history",
                "1586 TOY history must begin with 秀吉 of the 丰臣 dynasty",
                "history/countries/TOY - Toyotomi.txt",
            )
        governments = [
            entry.value.text
            for _path, entry in find_assignments(history.root, "government")
            if isinstance(entry.value, Scalar)
        ]
        reforms = [
            entry.value.text
            for _path, entry in find_assignments(
                history.root, "add_government_reform"
            )
            if isinstance(entry.value, Scalar)
        ]
        if not (
            first_scalar(history.root, "government") == "monarchy"
            and first_scalar(history.root, "add_government_reform")
            == TOYOTOMI_GOVERNMENT_REFORM
            and governments == ["monarchy"]
            and reforms == [TOYOTOMI_GOVERNMENT_REFORM]
        ):
            result.add(
                "toyotomi.government_history",
                "every selectable TOY date must retain monarchy plus the unique "
                "Kampaku/Taiko tier-one reform",
                "history/countries/TOY - Toyotomi.txt",
            )

    oda_history = _document(context, "history/countries/ODA - Oda.txt", result)
    if oda_history is not None:
        hashishiba = first_object(oda_history.root, "1582.6.21")
        hashishiba_monarch = first_object(hashishiba, "monarch")
        residual = first_object(oda_history.root, "1586.1.1")
        residual_monarch = first_object(residual, "monarch")
        if (
            first_scalar(hashishiba_monarch, "name") != "秀吉"
            or first_scalar(hashishiba_monarch, "dynasty") != "羽柴"
            or first_scalar(residual_monarch, "name") != "信雄"
            or first_scalar(residual_monarch, "dynasty") != "织田"
        ):
            result.add(
                "toyotomi.oda_handoff_rulers",
                "ODA must use Hashiba Hideyoshi in 1582 and a distinct Oda Nobukatsu residual history from 1586",
                "history/countries/ODA - Oda.txt",
            )
        for entry in oda_history.root.entries:
            if entry.key is None or not isinstance(entry.value, Object):
                continue
            try:
                when = _date(entry.key)
            except (TypeError, ValueError):
                continue
            if when < TOYOTOMI_START:
                continue
            if find_assignments(entry.value, "name", "秀吉") or find_assignments(
                entry.value, "dynasty", "丰臣"
            ):
                result.add(
                    "toyotomi.duplicate_oda_identity",
                    f"ODA repeats Hideyoshi/Toyotomi identity after the 1586 handoff ({entry.key})",
                    "history/countries/ODA - Oda.txt",
                    entry.line,
                )

    encoder_path = (
        context.mod_root.parent
        / "skills/eu4-modding/scripts/encode_eu4_special_gameplay.py"
    )
    source_root = context.mod_root / "tools/jxp_history_builder/source"
    source_pairs = {
        "history/countries/ODA - Oda.txt": source_root / "history/countries/ODA - Oda.txt",
        "history/countries/TOY - Toyotomi.txt": source_root / "history/countries/TOY - Toyotomi.txt",
        "common/countries/TOY - Toyotomi.txt": source_root / "common/countries/TOY - Toyotomi.txt",
    }
    try:
        encoder = _load_module(encoder_path, "_jxp_gameplay_name_encoder")
        for relative, source_path in source_pairs.items():
            active_path = context.mod_root / relative
            expected = encoder.encode_gameplay_text(
                source_path.read_bytes().decode("utf-8-sig")
            )
            actual = active_path.read_bytes()
            if actual != expected:
                result.add(
                    "toyotomi.gameplay_name_encoding",
                    "active literal-name file is not the exact BOM-free EU4SpecialEscape form of its readable source",
                    relative,
                )
            if actual.startswith(b"\xef\xbb\xbf"):
                result.add(
                    "toyotomi.gameplay_name_bom",
                    "EU4SpecialEscape gameplay files must not carry a UTF-8 BOM",
                    relative,
                )
            if re.search(r"[\u3400-\u9fff]", actual.decode("utf-8", errors="ignore")):
                result.add(
                    "toyotomi.gameplay_name_raw_cjk",
                    "active literal-name file still contains raw UTF-8 CJK",
                    relative,
                )
        result.metrics["toyotomi_encoded_name_files"] = len(source_pairs)
    except Exception as exc:
        result.add(
            "toyotomi.gameplay_name_pipeline",
            f"could not reproduce the gameplay-name encoding pipeline: {exc}",
            context.relative(encoder_path),
        )

    for relative in (
        "common/ideas/00_country_ideas.txt",
        "common/event_modifiers/jxp_70_toyotomi_modifiers.txt",
        "localisation_source/jxp_70_toyotomi_l_english_utf8_source.yml",
        "localisation/jxp_70_toyotomi_l_english.yml",
    ):
        if not (context.mod_root / relative).is_file():
            result.add("toyotomi.file_missing", "Toyotomi identity surface is incomplete", relative)
    _check_flag_assets(context, result)


def _check_transition(context: ValidationContext, result: CheckResult) -> None:
    effects = _document(context, "common/scripted_effects/jxp_70_toyotomi_effects.txt", result)
    effect = first_object(effects.root, "jxp_establish_toyotomi_identity_effect") if effects else None
    hidden = first_object(effect, "hidden_effect")
    required = (
        ("jxp_record_daimyo_origin_effect", "yes"),
        ("set_country_flag", "jxp_toyotomi_identity_established"),
        ("change_tag", "TOY"),
        ("on_change_tag_effect", "yes"),
        ("restore_country_name_effect", "yes"),
        ("jxp_set_toyotomi_government_effect", "yes"),
        ("jxp_sync_route_national_ideas_effect", "yes"),
        ("jxp_refresh_route_missions_effect", "yes"),
        ("regenerate_government_mechanics", "yes"),
        ("set_country_flag", "jxp_toyotomi_identity_migrated_v0270"),
    )
    for key, value in required:
        if not _has(hidden, key, value):
            result.add(
                "toyotomi.transition_contract",
                f"canonical Toyotomi transition is missing {key} = {value}",
                "common/scripted_effects/jxp_70_toyotomi_effects.txt",
            )
    if hidden is not None:
        record_lines = [entry.line for _path, entry in find_assignments(hidden, "jxp_record_daimyo_origin_effect", "yes")]
        change_lines = [entry.line for _path, entry in find_assignments(hidden, "change_tag", "TOY")]
        if not record_lines or not change_lines or min(record_lines) >= min(change_lines):
            result.add(
                "toyotomi.origin_order",
                "ODA origin must be recorded before change_tag = TOY",
                "common/scripted_effects/jxp_70_toyotomi_effects.txt",
            )
        government_lines = [
            entry.line
            for _path, entry in find_assignments(
                hidden, "jxp_set_toyotomi_government_effect", "yes"
            )
        ]
        if not government_lines or not change_lines or min(change_lines) >= min(
            government_lines
        ):
            result.add(
                "toyotomi.government_transition_order",
                "TOY must receive its Kampaku/Taiko government after change_tag = TOY",
                "common/scripted_effects/jxp_70_toyotomi_effects.txt",
            )

    government_helper = (
        first_object(effects.root, "jxp_set_toyotomi_government_effect")
        if effects
        else None
    )
    helper_requirements = (
        ("tag", "TOY"),
        ("change_government", "monarchy"),
        ("remove_government_reform", "shogunate"),
        ("remove_government_reform", "daimyo"),
        ("remove_government_reform", "indep_daimyo"),
        ("add_government_reform", TOYOTOMI_GOVERNMENT_REFORM),
        ("regenerate_government_mechanics", "yes"),
    )
    if not all(_has(government_helper, key, value) for key, value in helper_requirements):
        result.add(
            "toyotomi.government_transition",
            "Toyotomi identity transition does not replace daimyo/shogunate identity "
            "with the unique Kampaku/Taiko reform",
            "common/scripted_effects/jxp_70_toyotomi_effects.txt",
        )

    events = _document(context, "events/jxp_70_toyotomi_events.txt", result)
    catchup = _event(events, "jxp_toyotomi.1")
    trigger = first_object(catchup, "trigger")
    immediate = first_object(catchup, "immediate")
    if not (
        first_scalar(catchup, "hidden") == "yes"
        and _has(trigger, "tag", "TOY")
        and _has_negative(trigger, "has_country_flag", "jxp_toyotomi_identity_migrated_v0270")
        and _has(immediate, "jxp_establish_toyotomi_identity_effect", "yes")
    ):
        result.add(
            "toyotomi.catchup",
            "one-day TOY old-save/history catch-up event is incomplete",
            "events/jxp_70_toyotomi_events.txt",
        )

    on_actions = _document(context, "common/on_actions/jxp_60_mission_runtime_on_actions.txt", result)
    startup = first_object(on_actions.root, "on_startup") if on_actions else None
    startup_events = first_object(startup, "events")
    if "jxp_toyotomi.1" not in {scalar.text for scalar in bare_scalars(startup_events)}:
        result.add(
            "toyotomi.catchup_registration",
            "jxp_toyotomi.1 must run from on_startup",
            "common/on_actions/jxp_60_mission_runtime_on_actions.txt",
        )

    origin_effects = _document(context, "common/scripted_effects/jxp_04_daimyo_effects.txt", result)
    origin = first_object(origin_effects.root, "jxp_record_daimyo_origin_effect") if origin_effects else None
    toy_origin = False
    if origin is not None:
        for _path, entry in find_objects(origin, "if"):
            block = entry.value
            if isinstance(block, Object) and _has(block, "tag", "TOY") and _has(
                block, "set_country_flag", "jxp_origin_oda"
            ):
                toy_origin = True
                break
    if not toy_origin:
        result.add(
            "toyotomi.origin_mapping",
            "TOY must preserve ODA founder lineage through jxp_origin_oda",
            "common/scripted_effects/jxp_04_daimyo_effects.txt",
        )


def _check_missions_and_decision(context: ValidationContext, result: CheckResult) -> None:
    missions = _document(context, "missions/jxp_70_oda_toyotomi_missions.txt", result)
    series = first_object(missions.root, "jxp_oda_toyotomi_house_missions") if missions else None
    actual = tuple(
        entry.key
        for entry in (series.entries if series is not None else ())
        if entry.key and entry.key.startswith("jxp_mission_") and isinstance(entry.value, Object)
    )
    if actual != EXPECTED_MISSIONS:
        result.add(
            "toyotomi.mission_series",
            f"ODA/TOY series must contain the ordered six-mission identity chain; found {actual}",
            "missions/jxp_70_oda_toyotomi_missions.txt",
        )

    mission_root = context.mod_root / "missions"
    mission_sources = tuple(
        path
        for path in sorted(mission_root.glob("*.txt"))
        if path.name not in {"Japanese_Missions.txt", "DOM_Japanese_Missions.txt"}
        and not path.name.startswith(LEGACY_BOM_FILE_PREFIX)
    )
    extraction = CheckResult("Toyotomi mission profile extraction")
    catalog = extract_mission_series(context, extraction, mission_sources)
    if extraction.issues:
        for issue in extraction.issues:
            result.add(
                "toyotomi.mission_parse",
                issue.message,
                issue.path,
                issue.line,
            )
    profile = Profile("TOY hard contract", "TOY", "shinto", "eastern")
    active = [
        item
        for item in catalog
        if not item.generic and True in evaluate_potential(item.potential, profile)[0]
    ]
    by_slot: dict[int, list[str]] = {}
    for item in active:
        if item.slot is not None:
            by_slot.setdefault(item.slot, []).append(item.name)
    actual_signature = {
        slot: names[0] for slot, names in by_slot.items() if len(names) == 1
    }
    if actual_signature != EXPECTED_TOYOTOMI_SERIES or any(
        len(names) != 1 for names in by_slot.values()
    ):
        result.add(
            "toyotomi.mission_profile",
            f"TOY must own exactly the bespoke five-series signature; found {by_slot}",
            "missions/jxp_70_oda_toyotomi_missions.txt",
        )
    catalog_by_name = {item.name: item for item in catalog}
    for series_name, expected_missions in EXPECTED_TOYOTOMI_MISSIONS.items():
        item = catalog_by_name.get(series_name)
        actual_missions = tuple(
            mission.mission_id for mission in item.missions
        ) if item is not None else ()
        if actual_missions != expected_missions:
            result.add(
                "toyotomi.mission_branch",
                f"{series_name} lost its ordered seven-mission branch: {actual_missions}",
                "missions/jxp_70_oda_toyotomi_missions.txt",
            )
    result.metrics["toyotomi_mission_series"] = len(actual_signature)
    result.metrics["toyotomi_unique_missions"] = sum(
        len(missions) for missions in EXPECTED_TOYOTOMI_MISSIONS.values()
    )
    transition = first_object(series, "jxp_mission_toyotomi_name_and_osaka")
    trigger = first_object(transition, "trigger")
    effect = first_object(transition, "effect")
    anchors = {
        entry.value.text
        for _path, entry in find_assignments(trigger, "owns_or_non_sovereign_subject_of")
        if isinstance(entry.value, Scalar)
    } if trigger else set()
    if not (
        _has(trigger, "is_year", "1586")
        and {"1020", "1021"}.issubset(anchors)
        and _has(effect, "jxp_establish_toyotomi_identity_effect", "yes")
    ):
        result.add(
            "toyotomi.mission_transition",
            "Toyotomi-name mission must use the 1586 Kyoto/Settsu gate and canonical transition",
            "missions/jxp_70_oda_toyotomi_missions.txt",
        )

    decisions = _document(context, "decisions/jxp_70_toyotomi_decisions.txt", result)
    root = first_object(decisions.root, "country_decisions") if decisions else None
    decision = first_object(root, "jxp_decision_assume_toyotomi_name")
    potential = first_object(decision, "potential")
    allow = first_object(decision, "allow")
    decision_effect = first_object(decision, "effect")
    allow_anchors = {
        entry.value.text
        for _path, entry in find_assignments(allow, "owns_or_non_sovereign_subject_of")
        if isinstance(entry.value, Scalar)
    } if allow else set()
    if not (
        _has(potential, "tag", "ODA")
        and _has(potential, "is_year", "1586")
        and _has_negative(potential, "has_country_flag", "jxp_toyotomi_identity_established")
        and {"1020", "1021"}.issubset(allow_anchors)
        and _has(decision_effect, "jxp_establish_toyotomi_identity_effect", "yes")
    ):
        result.add(
            "toyotomi.decision_fallback",
            "ODA old saves require a guarded 1586 Kyoto/Settsu fallback decision",
            "decisions/jxp_70_toyotomi_decisions.txt",
        )

    debug_decisions = _document(context, "decisions/jxp_debug_decisions.txt", result)
    debug_root = (
        first_object(debug_decisions.root, "country_decisions")
        if debug_decisions
        else None
    )
    scaffold_decision = first_object(
        debug_root, "jxp_debug_prepare_toyotomi_decision"
    )
    scaffold_potential = first_object(scaffold_decision, "potential")
    scaffold_decision_effect = first_object(scaffold_decision, "effect")
    debug_effects = _document(
        context, "common/scripted_effects/jxp_debug_effects.txt", result
    )
    scaffold_effect = (
        first_object(
            debug_effects.root, "jxp_debug_prepare_toyotomi_decision_effect"
        )
        if debug_effects
        else None
    )
    scaffold_hidden = first_object(scaffold_effect, "hidden_effect")
    scaffold_requirements = (
        ("jxp_debug_return_jap_baseline_effect", "yes"),
        ("change_tag", "ODA"),
        ("change_government", "monarchy"),
        ("add_government_reform", "shogunate"),
        ("regenerate_government_mechanics", "yes"),
        ("jxp_record_daimyo_origin_effect", "yes"),
        ("jxp_debug_unify_japan_effect", "yes"),
        ("set_country_flag", "jxp_15_oda_tenka_fubu_edicts_taken"),
        ("add_legitimacy", "100"),
        ("add_stability", "3"),
        ("jxp_refresh_route_missions_effect", "yes"),
    )
    if not (
        _has(scaffold_potential, "ai", "no")
        and _has(scaffold_potential, "has_country_flag", "jxp_debug_enabled")
        and _has(
            scaffold_decision_effect,
            "jxp_debug_prepare_toyotomi_decision_effect",
            "yes",
        )
        and all(
            _has(scaffold_hidden, key, value)
            for key, value in scaffold_requirements
        )
        and not _has(scaffold_hidden, "change_tag", "TOY")
        and not _has(
            scaffold_hidden, "jxp_establish_toyotomi_identity_effect", "yes"
        )
        and not _has(
            scaffold_hidden,
            "set_country_flag",
            "jxp_toyotomi_identity_established",
        )
    ):
        result.add(
            "toyotomi.debug_scaffold",
            "Toyotomi runtime scaffold must prepare ODA eligibility without "
            "performing the production identity transition",
            "common/scripted_effects/jxp_debug_effects.txt",
        )
    result.metrics["toyotomi_debug_scaffolds"] = 1


def _check_reform(context: ValidationContext, result: CheckResult) -> None:
    base_reforms = _document(
        context,
        "common/government_reforms/jxp_70_toyotomi_reforms.txt",
        result,
    )
    base = (
        first_object(base_reforms.root, TOYOTOMI_GOVERNMENT_REFORM)
        if base_reforms is not None
        else None
    )
    base_potential = first_object(base, "potential")
    abilities = first_object(base, "government_abilities")
    if not (
        first_scalar(base, "basic_reform") is None
        and first_scalar(base, "allow_normal_conversion") == "no"
        and first_scalar(base, "lock_level_when_selected") == "yes"
        and first_scalar(base, "maintain_dynasty") == "yes"
        and first_scalar(base, "valid_for_nation_designer") == "no"
        and _has(base_potential, "tag", "TOY")
        and _has(base_potential, "has_reform", TOYOTOMI_GOVERNMENT_REFORM)
        and "jxp_japanese_polity_mechanic"
        in {scalar.text for scalar in bare_scalars(abilities)}
        and not find_assignments(base, "republican_tradition")
    ):
        result.add(
            "toyotomi.government_reform",
            "Toyotomi requires a locked, non-basic monarchy reform with exact TOY "
            "identity and no republican mechanics",
            "common/government_reforms/jxp_70_toyotomi_reforms.txt",
        )

    governments = _document(context, "common/governments/00_governments.txt", result)
    monarchy = first_object(governments.root, "monarchy") if governments else None
    levels = first_object(monarchy, "reform_levels")
    tier_one = first_object(levels, "feudalism_vs_autocracy")
    registered = [
        scalar.text for scalar in bare_scalars(first_object(tier_one, "reforms"))
    ]
    if registered.count(TOYOTOMI_GOVERNMENT_REFORM) != 1:
        result.add(
            "toyotomi.government_registration",
            "Toyotomi Kampaku/Taiko reform must be registered exactly once in the "
            "monarchy tier-one slot",
            "common/governments/00_governments.txt",
        )

    names = _document(
        context,
        "common/government_names/jxp_70_toyotomi_government_names.txt",
        result,
    )
    government_name = (
        first_object(names.root, "jxp_toyotomi_kampaku_government")
        if names is not None
        else None
    )
    name_trigger = first_object(government_name, "trigger")
    rank_names = {
        entry.value.text
        for entry in (first_object(government_name, "rank") or Object(())).entries
        if isinstance(entry.value, Scalar)
    }
    if not (
        _has(name_trigger, "has_reform", TOYOTOMI_GOVERNMENT_REFORM)
        and rank_names == {"JXP_TOYOTOMI_KAMPAKU_GOVERNMENT"}
    ):
        result.add(
            "toyotomi.government_name",
            "Toyotomi reform must select its bespoke Kampaku/Taiko government name",
            "common/government_names/jxp_70_toyotomi_government_names.txt",
        )

    localisation_path = (
        context.mod_root
        / "localisation_source/jxp_70_toyotomi_l_english_utf8_source.yml"
    )
    localisation = (
        localisation_path.read_text(encoding="utf-8-sig")
        if localisation_path.is_file()
        else ""
    )
    required_localisation = {
        TOYOTOMI_GOVERNMENT_REFORM,
        f"{TOYOTOMI_GOVERNMENT_REFORM}_desc",
        "JXP_TOYOTOMI_KAMPAKU_GOVERNMENT",
        "JXP_TOYOTOMI_RULER",
        "JXP_TOYOTOMI_CONSORT",
        "JXP_TOYOTOMI_HEIR",
    }
    missing_localisation = sorted(
        key for key in required_localisation if f" {key}:0 " not in localisation
    )
    if missing_localisation:
        result.add(
            "toyotomi.government_localisation",
            f"Toyotomi government localisation is missing {missing_localisation}",
            context.relative(localisation_path),
        )

    reforms = _document(context, "common/government_reforms/jxp_28_founder_house_reforms.txt", result)
    if reforms is None:
        return
    toy = first_object(reforms.root, "jxp_reform_founder_toyotomi_five_regents")
    toy_potential = first_object(toy, "potential")
    oda = first_object(reforms.root, "jxp_reform_founder_oda_azuchi_statutes")
    oda_potential = first_object(oda, "potential")
    if not (
        _has(toy_potential, "tag", "TOY")
        and _has(toy_potential, "has_country_flag", "jxp_toyotomi_identity_established")
        and _has(toy_potential, "has_country_flag", "jxp_origin_oda")
    ):
        result.add(
            "toyotomi.reform_identity",
            "Five Regents reform lacks TOY and unified ODA-lineage identity gates",
            "common/government_reforms/jxp_28_founder_house_reforms.txt",
        )
    if not _has_negative(oda_potential, "has_country_flag", "jxp_toyotomi_identity_established"):
        result.add(
            "toyotomi.reform_collision",
            "Oda Azuchi reform must exclude the established Toyotomi identity",
            "common/government_reforms/jxp_28_founder_house_reforms.txt",
        )


def _check_main_history_generator(
    context: ValidationContext,
    game_root: Path,
    result: CheckResult,
) -> None:
    builder_path = context.mod_root / "tools/jxp_history_builder/build_toyotomi_history.py"
    if not builder_path.is_file():
        result.add(
            "toyotomi.history_generator_missing",
            "pinned Toyotomi history generator is missing",
            context.relative(builder_path),
        )
        return
    try:
        builder = _load_module(builder_path, "_jxp_toyotomi_history_builder")
        expected = builder.build_outputs(game_root.resolve())
        stale = []
        for relative, payload in expected.items():
            target = context.mod_root / relative
            if not target.is_file() or target.read_bytes() != payload:
                stale.append(str(relative).replace("\\", "/"))
        if stale:
            result.add(
                "toyotomi.history_stale",
                f"generated Toyotomi history differs from pinned 1.37.5 source: {stale}",
                context.relative(builder_path),
            )
        manifest_relative = Path("tools/jxp_history_builder/generated_toyotomi_history_manifest.json")
        manifest = json.loads(expected[manifest_relative].decode("utf-8"))
        exact = {
            "schema_version": 4,
            "game_version": "1.37.5.0",
            "toyotomi_start": "1586.1.1",
            "sekigahara_handoff": "1600.10.21",
            "osaka_fall": "1615.6.4",
            "settsu_province": 1021,
            "province_override_count": 18,
            "war_override_count": 4,
            "war_display_language": "zh-Hans",
            "war_display_name_count": 13,
            "war_display_name_encoding": "EU4SpecialEscape-CP1252-no-BOM",
            "imjin_province_override_count": 18,
            "imjin_occupation_interval_count": 19,
            "toyotomi_subject_intervals": 24,
            "pinned_vanilla_source_count": 41,
            "country_history_overrides": ["ODA", "TOY"],
            "gameplay_name_encoding": "EU4SpecialEscape-CP1252-no-BOM",
        }
        for key, value in exact.items():
            if manifest.get(key) != value:
                result.add(
                    "toyotomi.history_manifest",
                    f"manifest {key} is {manifest.get(key)!r}; expected {value!r}",
                    str(manifest_relative).replace("\\", "/"),
                )
        result.metrics["main_history_overrides"] = manifest.get("province_override_count", 0)
        result.metrics["main_toyotomi_subject_intervals"] = manifest.get(
            "toyotomi_subject_intervals", 0
        )
        result.metrics["main_war_overrides"] = manifest.get("war_override_count", 0)
        result.metrics["main_imjin_province_overrides"] = manifest.get(
            "imjin_province_override_count", 0
        )

        timelines = {}
        boundary_dates = {
            date(1444, 11, 11),
            date(*TOYOTOMI_START),
            date(1820, 12, 31),
        }
        for province_id in builder.PINNED_JAPAN_PROVINCES:
            source_path = builder.province_history_path(
                game_root / "history/provinces", province_id
            )
            relative = Path("history/provinces") / source_path.name
            payload = expected.get(relative, source_path.read_bytes())
            timeline = builder.owner_timeline(payload.decode("cp1252"))
            timelines[province_id] = timeline
            for changed, _owner, _block in timeline[1]:
                boundary_dates.add(changed)
                if changed > date(1444, 11, 11):
                    boundary_dates.add(changed - timedelta(days=1))

        snapshots_checked = 0
        for when in sorted(boundary_dates):
            owners = {
                tag: {
                    province_id
                    for province_id, timeline in timelines.items()
                    if builder.owner_at(timeline, when) == tag
                }
                for tag in ("ODA", "TOY")
            }
            snapshots_checked += 1
            if owners["ODA"] and owners["TOY"]:
                result.add(
                    "toyotomi.main_dual_landed_identity",
                    f"ODA and TOY are both landed on {when}: ODA={sorted(owners['ODA'])}, TOY={sorted(owners['TOY'])}",
                    "tools/jxp_history_builder/build_toyotomi_history.py",
                )
            if when >= date(*TOYOTOMI_START) and owners["ODA"]:
                result.add(
                    "toyotomi.main_post_handoff_oda",
                    f"ODA remains landed after the Toyotomi handoff on {when}: {sorted(owners['ODA'])}",
                    "tools/jxp_history_builder/build_toyotomi_history.py",
                )
            if when < date(*TOYOTOMI_START) and owners["TOY"]:
                result.add(
                    "toyotomi.main_early_toyotomi",
                    f"TOY is landed before receiving the Toyotomi name on {when}: {sorted(owners['TOY'])}",
                    "tools/jxp_history_builder/build_toyotomi_history.py",
                )
        if not any(
            builder.owner_at(timeline, date(*TOYOTOMI_START)) == "TOY"
            for timeline in timelines.values()
        ):
            result.add(
                "toyotomi.main_handoff_missing",
                "TOY owns no pinned Japanese province on 1586.1.1",
                "tools/jxp_history_builder/build_toyotomi_history.py",
            )
        result.metrics["main_identity_boundary_snapshots"] = snapshots_checked
    except Exception as exc:
        result.add(
            "toyotomi.history_generator",
            f"could not reproduce pinned Toyotomi history: {exc}",
            context.relative(builder_path),
        )


def audit_companion_plan(
    plan: dict[str, object],
    result: CheckResult,
    source: str = "japan_expanded_v2_map/tools/jxp_map_builder/history_plan.json",
) -> None:
    timelines = plan.get("province_timelines")
    subjects = plan.get("subject_intervals")
    if not isinstance(timelines, dict) or not isinstance(subjects, list):
        result.add(
            "toyotomi.map_plan_shape",
            "companion history plan lacks province_timelines or subject_intervals",
            source,
        )
        return

    toy_intervals = 0
    owner_timelines: dict[str, tuple[str, tuple[tuple[date, str], ...]]] = {}
    boundary_dates = {
        date(1444, 11, 11),
        date(*TOYOTOMI_START),
        date(1820, 12, 31),
    }
    for province_id, raw in timelines.items():
        if not isinstance(raw, dict):
            continue
        root_owner = str(raw.get("root", ""))
        changes_for_timeline: list[tuple[date, str]] = []
        for change in raw.get("changes", []):
            if not isinstance(change, list) or len(change) != 2:
                continue
            when, owner = str(change[0]), str(change[1])
            changed = date(*_date(when))
            changes_for_timeline.append((changed, owner))
            boundary_dates.add(changed)
            if changed > date(1444, 11, 11):
                boundary_dates.add(changed - timedelta(days=1))
            if owner == "TOY":
                toy_intervals += 1
            if owner == "ODA" and _date(when) >= TOYOTOMI_START:
                result.add(
                    "toyotomi.map_post_start_oda",
                    f"province {province_id} restores ODA after 1586.1.1 ({when})",
                    source,
                )
        owner_timelines[str(province_id)] = (
            root_owner,
            tuple(sorted(changes_for_timeline)),
        )
    if toy_intervals != 33:
        result.add(
            "toyotomi.map_interval_count",
            f"companion source must contain 33 Toyotomi ownership/core intervals, found {toy_intervals}",
            source,
        )

    identity_snapshots = 0
    for when in sorted(boundary_dates):
        landed = {"ODA": set(), "TOY": set()}
        for province_id, (root_owner, changes) in owner_timelines.items():
            owner = root_owner
            for changed, changed_owner in changes:
                if changed > when:
                    break
                owner = changed_owner
            if owner in landed:
                landed[owner].add(province_id)
        identity_snapshots += 1
        if landed["ODA"] and landed["TOY"]:
            result.add(
                "toyotomi.map_dual_landed_identity",
                f"ODA and TOY are both landed on {when}: ODA={sorted(landed['ODA'])}, TOY={sorted(landed['TOY'])}",
                source,
            )
        if when >= date(*TOYOTOMI_START) and landed["ODA"]:
            result.add(
                "toyotomi.map_post_handoff_oda_landed",
                f"ODA remains landed after 1586.1.1 on {when}: {sorted(landed['ODA'])}",
                source,
            )
        if when < date(*TOYOTOMI_START) and landed["TOY"]:
            result.add(
                "toyotomi.map_early_toyotomi",
                f"TOY is landed before 1586.1.1 on {when}: {sorted(landed['TOY'])}",
                source,
            )

    settsu = timelines.get("1021")
    expected_settsu = [
        ["1569.12.1", "ODA"],
        ["1586.1.1", "TOY"],
        ["1615.6.4", "TKG"],
    ]
    if not isinstance(settsu, dict) or settsu.get("changes") != expected_settsu:
        result.add(
            "toyotomi.map_settsu_interval",
            "Settsu must pass ODA->TOY on 1586.1.1 and remain TOY until 1615.6.4",
            source,
        )

    toy_subjects = 0
    for interval in subjects:
        if not isinstance(interval, list) or len(interval) != 4:
            continue
        overlord, _subject, start, end = (str(value) for value in interval)
        if overlord == "ODA" and _date(end) > TOYOTOMI_START:
            result.add(
                "toyotomi.map_post_start_oda_subject",
                f"ODA subject interval survives past 1586.1.1: {interval}",
                source,
            )
        if overlord == "TOY":
            toy_subjects += 1
            if not (TOYOTOMI_START <= _date(start) < _date(end) <= SEKIGAHARA):
                result.add(
                    "toyotomi.map_subject_interval",
                    f"invalid Toyotomi companion subject interval: {interval}",
                    source,
                )
    if len(subjects) != 70 or toy_subjects != 15:
        result.add(
            "toyotomi.map_subject_count",
            f"companion source must contain 70 subject intervals / 15 Toyotomi intervals; found {len(subjects)}/{toy_subjects}",
            source,
        )
    result.metrics["map_toyotomi_owner_intervals"] = toy_intervals
    result.metrics["map_subject_intervals"] = len(subjects)
    result.metrics["map_toyotomi_subject_intervals"] = toy_subjects
    result.metrics["map_identity_boundary_snapshots"] = identity_snapshots


def _check_companion(context: ValidationContext, result: CheckResult) -> None:
    map_root = context.mod_root.parent / "japan_expanded_v2_map"
    plan_path = map_root / "tools/jxp_map_builder/history_plan.json"
    if not plan_path.is_file():
        result.add(
            "toyotomi.map_missing",
            "mandatory companion history plan is missing",
            str(plan_path),
        )
        return
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result.add(
            "toyotomi.map_plan_parse",
            f"could not read companion history plan: {exc}",
            str(plan_path),
        )
        return
    audit_companion_plan(plan, result)


def check_toyotomi_history(
    context: ValidationContext,
    game_root: Path,
) -> CheckResult:
    """Return the complete static JXP-018 identity/history contract."""

    result = CheckResult("Toyotomi identity and dated succession")
    _check_identity(context, result)
    _check_transition(context, result)
    _check_missions_and_decision(context, result)
    _check_reform(context, result)
    _check_main_history_generator(context, game_root, result)
    _check_companion(context, result)
    result.summary = (
        f"{result.metrics.get('main_history_overrides', 0)} main province overrides, "
        f"{result.metrics.get('main_toyotomi_subject_intervals', 0)} main subject intervals, "
        f"{result.metrics.get('main_war_overrides', 0)} post-succession wars, "
        f"{result.metrics.get('main_imjin_province_overrides', 0)} Korean province overrides, "
        f"{result.metrics.get('map_toyotomi_owner_intervals', 0)} companion owner/core intervals, "
        f"{result.metrics.get('map_subject_intervals', 0)} companion subject intervals; "
        f"{len(result.issues)} issue(s)"
    )
    return result
