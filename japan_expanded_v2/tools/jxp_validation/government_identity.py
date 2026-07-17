"""Validate fresh-start Japanese government identity and reform wiring."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .clausewitz import (
    Object,
    Scalar,
    bare_scalars,
    entries_named,
    first_object,
    first_scalar,
)
from .core import CheckResult, ValidationContext
from .final_states import FINAL_STATES
from .missions import DAIMYO_TAGS


MONARCHY_REFORM_FILE = Path(
    "common/government_reforms/01_government_reforms_monarchies.txt"
)
LEGACY_ROUTE_FILE = Path("common/government_reforms/jxp_14_route_reforms.txt")
LEGACY_POLITY_FILE = Path("common/government_reforms/jxp_japanese_reforms.txt")
LEGACY_OCEANIC_FILE = Path("common/government_reforms/jxp_03_overseas_reforms.txt")
DAIMYO_TRIGGER_FILE = Path("common/scripted_triggers/jxp_04_daimyo_triggers.txt")
CANONICAL_FINAL_SYNC_FILE = Path(
    "common/scripted_effects/jxp_79_final_state_effects.txt"
)
PINNED_MONARCHY_REFORM_SHA256 = (
    "b8157df415dbaf0fc711df18bb0d65d593ccc269f1a8d98b3983a5db6b26ce2e"
)
POLITY_ABILITY_BLOCK = (
    "\tgovernment_abilities = {\n"
    "\t\tjxp_japanese_polity_mechanic\n"
    "\t}\n"
)
CELESTIAL_POLITY_CONDITIONAL_BLOCK = (
    "\tconditional = {\n"
    "\t\tallow = { jxp_is_japanese_polity_trigger = yes }\n"
    "\t\tgovernment_abilities = {\n"
    "\t\t\tjxp_japanese_polity_mechanic\n"
    "\t\t}\n"
    "\t}\n"
)
SHOGUNATE_PRESERVATION_BLOCK = (
    "\t\tOR = {\n"
    "\t\t\thas_reform = shogunate\n"
    "\t\t\tAND = {\n"
)
SHOGUNATE_VANILLA_BLOCK = (
    "\t\tOR = {\n"
    "\t\t\tAND = {\n"
)
DAIMYO_PRESERVATION_BLOCK = (
    "\t\tOR = {\n"
    "\t\t\thas_reform = daimyo\n"
    "\t\t\toverlord = { has_reform = shogunate }\n"
    "\t\t\tis_subject_of_type = daimyo_vassal\n"
    "\t\t}\n"
)
DAIMYO_VANILLA_BLOCK = "\t\toverlord = { has_reform = shogunate }\n"
INDEP_DAIMYO_PRESERVATION_BLOCK = (
    "\t\tOR = {\n"
    "\t\t\thas_reform = indep_daimyo\n"
    "\t\t\tAND = {\n"
)
INDEP_DAIMYO_VANILLA_BLOCK = (
    "\t\tOR = {\n"
    "\t\t\tAND = {\n"
)
FRESH_START_DATE = (1444, 11, 11)
TOYOTOMI_GOVERNMENT_REFORM = "jxp_toyotomi_kampaku_taiko_reform"

LEGACY_ROUTE_REFORMS = (
    "jxp_reform_sakoku_buke_laws",
    "jxp_reform_sakoku_terauke_registers",
    "jxp_reform_sakoku_dejima_inspectors",
    "jxp_reform_open_red_seal_council",
    "jxp_reform_open_rangaku_bureaucracy",
    "jxp_reform_open_chartered_harbors",
    "jxp_reform_kirishitan_church_court",
    "jxp_reform_kirishitan_port_congregations",
    "jxp_reform_kirishitan_cross_sun_guard",
    "jxp_reform_confucian_shushi_academies",
    "jxp_reform_confucian_ritual_census",
    "jxp_reform_confucian_kami_rites",
    "jxp_reform_imperial_daijokan",
    "jxp_reform_imperial_kinri_guard",
    "jxp_reform_imperial_court_rites",
    "jxp_reform_reformed_consistory_ports",
    "jxp_reform_reformed_oranda_schools",
    "jxp_reform_reformed_elder_militias",
    "jxp_reform_kaikyo_qadi_harbormasters",
    "jxp_reform_kaikyo_hajj_sea_lanes",
    "jxp_reform_kaikyo_halal_granaries",
    "jxp_reform_ikko_monto_covenant",
    "jxp_reform_ikko_terauchi_markets",
    "jxp_reform_ikko_village_militias",
    "jxp_reform_wokou_letters_of_mark",
    "jxp_reform_wokou_setouchi_pilotage",
    "jxp_reform_wokou_free_harbor_codes",
)

MAP_DAIMYO_TAGS = (
    "ANK", "ARI", "ASN", "AZI", "DHO", "HCS", "HNG", "HNM", "KMP", "KRD",
    "KYO", "MKM", "MOG", "MTS", "MTU", "MYO", "NBS", "NHT", "OSK", "RKK",
    "RZJ", "SGR", "SMA", "STM", "STO", "TGR", "TGS", "UKT", "WKT", "YMC",
)

RETIRED_CARRIERS = {
    *LEGACY_ROUTE_REFORMS,
    "jxp_japanese_polity_reform",
    "jxp_oceanic_sun_reform",
}
FINAL_POWER_REFORMS = {state.reform_id for state in FINAL_STATES}


def _top_objects(context: ValidationContext, relative: Path) -> dict[str, Object]:
    document = context.document(context.mod_root / relative)
    if document is None:
        return {}
    return {
        entry.key: entry.value
        for entry in document.root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }


def _direct_scalar_values(obj: Object | None, key: str) -> tuple[str, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value.text
        for entry in entries_named(obj, key)
        if isinstance(entry.value, Scalar)
    )


def _history_file(root: Path, tag: str) -> Path | None:
    matches = tuple(sorted((root / "history/countries").glob(f"{tag} - *.txt")))
    return matches[0] if len(matches) == 1 else None


def _effective_history_file(
    context: ValidationContext,
    game_root: Path,
    tag: str,
) -> Path | None:
    return _history_file(context.mod_root, tag) or _history_file(game_root, tag)


def _check_history_identity(
    context: ValidationContext,
    result: CheckResult,
    path: Path | None,
    tag: str,
    expected_reform: str,
    source_label: str,
    *,
    allow_custom_carrier: bool = False,
) -> bool:
    if path is None:
        result.add(
            "government_identity.history_missing",
            f"{tag} has no unique effective country history",
            source_label,
        )
        return False
    document = context.document(path)
    if document is None:
        result.add(
            "government_identity.history_parse",
            f"{tag} country history could not be parsed",
            str(path),
        )
        return False
    government = first_scalar(document.root, "government")
    reforms = _direct_scalar_values(document.root, "add_government_reform")
    if government != "monarchy" or reforms != (expected_reform,):
        result.add(
            "government_identity.fresh_history",
            f"{tag} starts as {government!r} with reforms {reforms}; expected "
            f"monarchy + {expected_reform}",
            str(path),
        )
        return False
    if not allow_custom_carrier and any(
        reform.startswith("jxp_") for reform in reforms
    ):
        result.add(
            "government_identity.fresh_history_custom_carrier",
            f"{tag} history must not auto-grant a JXP government carrier",
            str(path),
        )
        return False
    for entry in document.root.entries:
        if entry.key is None or not isinstance(entry.value, Object):
            continue
        try:
            when = tuple(int(part) for part in entry.key.split("."))
        except (TypeError, ValueError):
            continue
        if len(when) != 3 or when > FRESH_START_DATE:
            continue
        forbidden = tuple(
            child.key
            for child in entry.value.entries
            if child.key
            in {
                "government",
                "change_government",
                "add_government_reform",
                "remove_government_reform",
            }
        )
        if forbidden:
            result.add(
                "government_identity.pre_start_history_mutation",
                f"{tag} mutates government identity at {entry.key}: {forbidden}",
                str(path),
            )
            return False
    return True


def _check_monarchy_override(
    context: ValidationContext,
    game_root: Path,
    result: CheckResult,
) -> int:
    source = game_root / MONARCHY_REFORM_FILE
    override = context.mod_root / MONARCHY_REFORM_FILE
    if not source.is_file() or not override.is_file():
        result.add(
            "government_identity.monarchy_override_missing",
            "the pinned vanilla monarchy reform override is missing",
            str(override),
        )
        return 0
    source_bytes = source.read_bytes()
    source_hash = sha256(source_bytes).hexdigest()
    if source_hash != PINNED_MONARCHY_REFORM_SHA256:
        result.add(
            "government_identity.vanilla_source_drift",
            f"vanilla monarchy reform hash is {source_hash}; expected "
            f"{PINNED_MONARCHY_REFORM_SHA256}",
            str(source),
        )
    source_text = source_bytes.decode("utf-8-sig").replace("\r\n", "\n")
    override_text = override.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if override_text.count(POLITY_ABILITY_BLOCK) != 3:
        result.add(
            "government_identity.monarchy_override_ability_count",
            "monarchy override must add exactly three JXP polity ability blocks",
            str(override),
        )
    if override_text.count(CELESTIAL_POLITY_CONDITIONAL_BLOCK) != 1:
        result.add(
            "government_identity.celestial_polity_ability_count",
            "monarchy override must add exactly one Japanese-only celestial polity "
            "ability block",
            str(override),
        )
    preservation_blocks = (
        ("shogunate", SHOGUNATE_PRESERVATION_BLOCK),
        ("daimyo", DAIMYO_PRESERVATION_BLOCK),
        ("indep_daimyo", INDEP_DAIMYO_PRESERVATION_BLOCK),
    )
    for reform_id, block in preservation_blocks:
        if override_text.count(block) != 1:
            result.add(
                "government_identity.monarchy_override_preservation_count",
                f"monarchy override must contain exactly one pinned {reform_id} "
                "identity-preservation potential block",
                str(override),
            )
    stripped = override_text.replace(POLITY_ABILITY_BLOCK, "").replace(
        CELESTIAL_POLITY_CONDITIONAL_BLOCK, ""
    )
    stripped = stripped.replace(
        SHOGUNATE_PRESERVATION_BLOCK,
        SHOGUNATE_VANILLA_BLOCK,
    ).replace(
        DAIMYO_PRESERVATION_BLOCK,
        DAIMYO_VANILLA_BLOCK,
    ).replace(
        INDEP_DAIMYO_PRESERVATION_BLOCK,
        INDEP_DAIMYO_VANILLA_BLOCK,
    )
    if stripped.rstrip("\n") != source_text.rstrip("\n"):
        result.add(
            "government_identity.monarchy_override_drift",
            "monarchy override differs from pinned vanilla beyond the three daimyo "
            "ability blocks, one Japanese celestial conditional, and the three "
            "pinned identity-preservation potential blocks",
            str(override),
        )

    definitions = _top_objects(context, MONARCHY_REFORM_FILE)
    carriers = 0
    for reform_id in ("shogunate", "daimyo", "indep_daimyo"):
        definition = definitions.get(reform_id)
        direct_abilities = tuple(
            tuple(value.text for value in bare_scalars(entry.value))
            for entry in entries_named(definition, "government_abilities")
            if isinstance(entry.value, Object)
        )
        if direct_abilities != (("jxp_japanese_polity_mechanic",),):
            result.add(
                "government_identity.daimyo_mechanic_wiring",
                f"{reform_id} must carry exactly one direct JXP polity mechanic",
                str(override),
            )
        else:
            carriers += 1
    return carriers


def check_government_identity(
    context: ValidationContext,
    game_root: Path,
    companion_context: ValidationContext | None = None,
) -> CheckResult:
    result = CheckResult("Fresh Japanese government identity")

    mechanic_carriers = _check_monarchy_override(context, game_root, result)

    basic_reforms: set[str] = set()
    reform_root = context.mod_root / "common/government_reforms"
    for path in sorted(reform_root.glob("*.txt")):
        for reform_id, definition in _top_objects(
            context, path.relative_to(context.mod_root)
        ).items():
            if first_scalar(definition, "basic_reform") == "yes":
                basic_reforms.add(reform_id)
    if basic_reforms != {"monarchy_mechanic"}:
        result.add(
            "government_identity.basic_reform_inventory",
            f"mod-defined basic reforms are {sorted(basic_reforms)}; expected only "
            "the pinned vanilla monarchy_mechanic",
            "common/government_reforms",
        )

    legacy_definitions = _top_objects(context, LEGACY_ROUTE_FILE)
    if set(legacy_definitions) != set(LEGACY_ROUTE_REFORMS):
        result.add(
            "government_identity.legacy_route_inventory",
            "legacy route tombstone inventory must contain exactly 27 reforms",
            str(LEGACY_ROUTE_FILE),
        )
    for reform_id in LEGACY_ROUTE_REFORMS:
        definition = legacy_definitions.get(reform_id)
        potential = first_object(definition, "potential")
        forbidden = (
            first_scalar(definition, "basic_reform") is not None
            or first_object(definition, "modifiers") is not None
            or first_object(definition, "government_abilities") is not None
            or first_scalar(definition, "monarchy") is not None
            or first_scalar(definition, "republic") is not None
        )
        if definition is None or first_scalar(potential, "always") != "no" or forbidden:
            result.add(
                "government_identity.legacy_route_tombstone",
                f"{reform_id} must remain an inert always=no tombstone",
                str(LEGACY_ROUTE_FILE),
            )

    for reform_id, relative in (
        ("jxp_japanese_polity_reform", LEGACY_POLITY_FILE),
        ("jxp_oceanic_sun_reform", LEGACY_OCEANIC_FILE),
    ):
        definition = _top_objects(context, relative).get(reform_id)
        potential = first_object(definition, "potential")
        if (
            definition is None
            or first_scalar(potential, "always") != "no"
            or first_scalar(definition, "basic_reform") is not None
            or first_object(definition, "modifiers") is not None
            or first_object(definition, "government_abilities") is not None
        ):
            result.add(
                "government_identity.retired_carrier_tombstone",
                f"{reform_id} must remain an inert always=no tombstone",
                str(relative),
            )

    for reform_id in sorted(RETIRED_CARRIERS):
        calls = context.assignment_occurrences("add_government_reform", reform_id)
        if calls:
            result.add(
                "government_identity.retired_carrier_autogrant",
                f"{reform_id} is still auto-granted from "
                + ", ".join(sorted({context.relative(call.source) for call in calls})),
            )

    canonical_final_adds = 0
    for reform_id in sorted(FINAL_POWER_REFORMS):
        calls = context.assignment_occurrences("add_government_reform", reform_id)
        sources = {context.relative(call.source) for call in calls}
        if sources != {CANONICAL_FINAL_SYNC_FILE.as_posix()} or len(calls) != 1:
            result.add(
                "government_identity.final_power_autogrant",
                f"{reform_id} add sites are {sorted(sources)} ({len(calls)} calls); "
                "expected one exact-final-state canonical sync call",
            )
        else:
            canonical_final_adds += 1

    trigger_definitions = _top_objects(context, DAIMYO_TRIGGER_FILE)
    stage = trigger_definitions.get("jxp_is_daimyo_stage_trigger")
    stage_or = first_object(stage, "OR")
    stage_reforms = set(_direct_scalar_values(stage_or, "has_reform"))
    if stage_reforms != {"daimyo", "indep_daimyo", "shogunate"}:
        result.add(
            "government_identity.daimyo_stage_reforms",
            f"daimyo stage reforms are {sorted(stage_reforms)}; expected the three "
            "vanilla Japanese monarchy identities",
            str(DAIMYO_TRIGGER_FILE),
        )

    route_effects = (context.mod_root / "common/scripted_effects/jxp_scripted_effects.txt")
    realm_events = context.mod_root / "events/jxp_realm_events.txt"
    if route_effects.is_file():
        route_text = route_effects.read_text(encoding="utf-8-sig")
        truthful_registration = (
            "limit = { has_government_mechanic = jxp_japanese_polity_mechanic }\n"
            "\t\t\tset_country_flag = jxp_polity_mechanic_registered"
        )
        if truthful_registration not in route_text:
            result.add(
                "government_identity.mechanic_registration_truth",
                "polity mechanic registration flag must be gated by the actual mechanic",
                context.relative(route_effects),
            )
    if realm_events.is_file():
        realm_text = realm_events.read_text(encoding="utf-8-sig")
        event_anchor = "id = jxp_realm.3"
        event_start = realm_text.find(event_anchor)
        event_end = realm_text.find("\ncountry_event = {", event_start + len(event_anchor))
        event_block = realm_text[event_start : event_end if event_end >= 0 else None]
        if "has_government_mechanic = jxp_japanese_polity_mechanic" not in event_block:
            result.add(
                "government_identity.mechanic_retry_scope",
                "jxp_realm.3 must not retry registration for countries without the mechanic",
                context.relative(realm_events),
            )

    main_fresh = 0
    for tag in DAIMYO_TAGS:
        expected = "shogunate" if tag == "ASK" else "daimyo"
        path = _effective_history_file(context, game_root, tag)
        if _check_history_identity(
            context, result, path, tag, expected, "main fresh-start history"
        ):
            main_fresh += 1

    map_fresh = 0
    if companion_context is None:
        result.add(
            "government_identity.companion_missing",
            "companion map context is required for the 30-tag fresh-start matrix",
        )
    else:
        for tag in MAP_DAIMYO_TAGS:
            path = _history_file(companion_context.mod_root, tag)
            if _check_history_identity(
                companion_context,
                result,
                path,
                tag,
                "daimyo",
                "companion fresh-start history",
            ):
                map_fresh += 1

    ryukyu = _effective_history_file(context, game_root, "RYU")
    ryukyu_ok = _check_history_identity(
        context, result, ryukyu, "RYU", "autocracy_reform", "Ryukyu control history"
    )
    toyotomi = _history_file(context.mod_root, "TOY")
    toyotomi_ok = _check_history_identity(
        context,
        result,
        toyotomi,
        "TOY",
        TOYOTOMI_GOVERNMENT_REFORM,
        "Toyotomi historical-start history",
        allow_custom_carrier=True,
    )

    result.metrics.update(
        {
            "vanilla_basic_reforms": len(basic_reforms),
            "daimyo_mechanic_carriers": mechanic_carriers,
            "retired_route_tombstones": len(legacy_definitions),
            "canonical_final_power_adds": canonical_final_adds,
            "main_fresh_identities": main_fresh,
            "map_fresh_identities": map_fresh,
            "fresh_identity_total": main_fresh + map_fresh,
            "ryukyu_control": int(ryukyu_ok),
            "toyotomi_historical_control": int(toyotomi_ok),
        }
    )
    result.summary = (
        f"{main_fresh + map_fresh}/67 fresh daimyo/shogunate identities; "
        f"{len(basic_reforms)} legal basic reform; {canonical_final_adds}/10 "
        "final power grants centralized"
    )
    return result
