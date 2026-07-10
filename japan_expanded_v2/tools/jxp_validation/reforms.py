"""Government reform definition, registration, and grant checks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .clausewitz import Object, Scalar, bare_scalars, first_object, first_scalar
from .core import CheckResult, ValidationContext
from .missions import BASE_PROFILES, evaluate_potential


VISIBLE_ROUTE_FILE = "jxp_18_route_reforms_extra.txt"
FOUNDER_FILE = "jxp_28_founder_house_reforms.txt"
EXPECTED_VISIBLE_ROUTE_COUNT = 27
EXPECTED_FOUNDER_COUNT = 39
VANILLA_MONARCHY_FIRST_11_LEVELS = (
    "feudalism_vs_autocracy",
    "hereditary_vs_nobility",
    "bureaucracy",
    "state_and_religion",
    "military_doctrines",
    "deliberative_assembly",
    "growth_of_administration",
    "economical_matters",
    "legitimation_of_power",
    "absolute_rule_vs_constitutional",
    "separation_of_power",
)
AUTO_GRANT_KEYS = ("add_government_reform", "set_government_reform")
ROUTE_REQUIREMENTS = {
    "sakoku": (None, "jxp_path_sakoku"),
    "open": (None, "jxp_path_open_trade"),
    "kirishitan": ("KJP", "jxp_path_kirishitan"),
    "confucian": ("CJP", "jxp_path_confucian"),
    "imperial": ("EJP", "jxp_path_imperial"),
    "reformed": ("RFJ", "jxp_path_reformed"),
    "kaikyo": ("SJP", "jxp_path_kaikyo"),
    "ikko": ("IJP", "jxp_path_ikko"),
    "wokou": ("WAK", "jxp_path_wokou"),
}
ROUTE_BY_FLAG = {flag: route for route, (_tag, flag) in ROUTE_REQUIREMENTS.items()}
EXPECTED_LEVEL_MEMBERS = {
    "feudalism_vs_autocracy": frozenset(),
    "hereditary_vs_nobility": frozenset(
        {
            "jxp_reform_founder_tkg_mikawa_fudai_code",
            "jxp_reform_founder_ama_gassan_toda_law",
            "jxp_reform_founder_htk_wakae_retainer_law",
        }
    ),
    "bureaucracy": frozenset(
        {
            "jxp_reform_founder_img_tokaido_lawbooks",
            "jxp_reform_sakoku_hidden_learning",
            "jxp_reform_confucian_examination_domains",
            "jxp_reform_reformed_printing_synods",
        }
    ),
    "state_and_religion": frozenset(
        {
            "jxp_reform_founder_ktb_ise_court_law",
            "jxp_reform_founder_kkc_aso_rite_council",
            "jxp_reform_founder_utn_nikko_barrier_guard",
            "jxp_reform_founder_tti_yamato_temple_compact",
            "jxp_reform_kirishitan_seminaries",
            "jxp_reform_confucian_three_teachings_board",
            "jxp_reform_kaikyo_wakf_granaries",
        }
    ),
    "military_doctrines": frozenset(
        {
            "jxp_reform_founder_tkd_koshu_military_law",
            "jxp_reform_founder_mri_setouchi_admiralty",
            "jxp_reform_founder_smz_satsuma_gunnery",
            "jxp_reform_founder_otm_funai_arsenal",
            "jxp_reform_founder_dte_oshu_cavalry_envoys",
            "jxp_reform_founder_csk_tosa_ichiryo_gusoku",
            "jxp_reform_founder_rfr_mutsu_nine_gates",
            "jxp_reform_founder_akm_harima_castle_roads",
            "jxp_reform_founder_cba_katori_muster",
            "jxp_reform_founder_ito_hyuga_fort_network",
            "jxp_reform_founder_kno_setouchi_pilot_law",
            "jxp_reform_founder_ogs_suwa_horse_archery",
            "jxp_reform_founder_stk_hitachi_warrior_rolls",
            "jxp_reform_open_foreign_artillery_contracts",
            "jxp_reform_kirishitan_nagasaki_admiralty",
            "jxp_reform_imperial_restoration_army",
            "jxp_reform_kaikyo_spice_guard",
            "jxp_reform_ikko_ashigaru_congregations",
            "jxp_reform_wokou_boarding_companies",
        }
    ),
    "deliberative_assembly": frozenset(
        {
            "jxp_reform_founder_asa_ichijodani_council",
            "jxp_reform_founder_hsk_sakai_kanrei_compact",
            "jxp_reform_kaikyo_monsoon_diwan",
            "jxp_reform_ikko_somon_councils",
        }
    ),
    "growth_of_administration": frozenset(
        {
            "jxp_reform_founder_toyotomi_five_regents",
            "jxp_reform_founder_hjo_odawara_cadasters",
            "jxp_reform_founder_ike_himeji_stewards",
            "jxp_reform_founder_ymn_roku_bun_ichi_domain",
            "jxp_reform_founder_tki_mino_river_offices",
            "jxp_reform_sakoku_coastal_barriers",
            "jxp_reform_kirishitan_misericordia_hospitals",
            "jxp_reform_imperial_kokushi_governors",
        }
    ),
    "economical_matters": frozenset(
        {
            "jxp_reform_founder_ouc_yamaguchi_court",
            "jxp_reform_founder_soo_tsushima_wakan",
            "jxp_reform_founder_mae_kaga_million_koku",
            "jxp_reform_founder_akt_ezochi_brokers",
            "jxp_reform_founder_isk_tango_port_wardens",
            "jxp_reform_founder_shn_dazaifu_brokerage",
            "jxp_reform_open_silver_exchange",
            "jxp_reform_open_chartered_factories",
            "jxp_reform_reformed_contract_fleet",
            "jxp_reform_ikko_granary_communes",
            "jxp_reform_wokou_island_freeports",
        }
    ),
    "legitimation_of_power": frozenset(
        {
            "jxp_reform_founder_ues_kanto_justice",
            "jxp_reform_confucian_sinicized_codes",
            "jxp_reform_imperial_kokugaku_office",
            "jxp_reform_wokou_black_tide_law",
        }
    ),
    "absolute_rule_vs_constitutional": frozenset(
        {
            "jxp_reform_founder_oda_azuchi_statutes",
            "jxp_reform_founder_generic_renovated_japan",
            "jxp_reform_sakoku_sankin_kotai_roads",
            "jxp_reform_reformed_civic_compacts",
        }
    ),
    "separation_of_power": frozenset(
        {
            "jxp_reform_founder_ask_muromachi_office",
            "jxp_reform_founder_sba_buei_offices",
        }
    ),
}
EXPECTED_LEVEL_BY_REFORM = {
    reform_id: level
    for level, reform_ids in EXPECTED_LEVEL_MEMBERS.items()
    for reform_id in reform_ids
}


@dataclass(frozen=True, slots=True)
class ReformDefinition:
    reform_id: str
    source: Path
    line: int
    body: Object


@dataclass(frozen=True, slots=True)
class ReformRegistration:
    reform_id: str
    source: Path
    line: int
    path: tuple[str, ...]


def _top_level_reform_definitions(
    context: ValidationContext,
    source: Path,
) -> tuple[ReformDefinition, ...]:
    document = context.document(source)
    if document is None:
        return ()
    return tuple(
        ReformDefinition(entry.key, source, entry.line, entry.value)
        for entry in document.root.entries
        if entry.key is not None
        and entry.key.startswith("jxp_reform_")
        and isinstance(entry.value, Object)
    )


def _contains_assignment(obj: Object | None, key: str, value: str | None = None) -> bool:
    if obj is None:
        return False
    for entry in obj.entries:
        if entry.key == key and isinstance(entry.value, Scalar):
            if value is None or entry.value.text == value:
                return True
        if isinstance(entry.value, Object) and _contains_assignment(entry.value, key, value):
            return True
    return False


def _route_key(reform_id: str) -> str | None:
    stem = reform_id.removeprefix("jxp_reform_")
    key = stem.split("_", 1)[0]
    return key if key in ROUTE_REQUIREMENTS else None


def _collect_registrations(
    obj: Object,
    source: Path,
    path: tuple[str, ...] = (),
) -> tuple[ReformRegistration, ...]:
    registrations: list[ReformRegistration] = []
    for entry in obj.entries:
        if entry.key == "reforms" and isinstance(entry.value, Object):
            registrations.extend(
                ReformRegistration(value.text, source, value.line, path)
                for value in bare_scalars(entry.value)
            )
        if isinstance(entry.value, Object):
            registrations.extend(
                _collect_registrations(
                    entry.value,
                    source,
                    path + ((entry.key or "{}"),),
                )
            )
    return tuple(registrations)


def check_reforms(context: ValidationContext) -> CheckResult:
    result = CheckResult("Government reforms")
    reform_root = context.mod_root / "common" / "government_reforms"
    government_file = context.mod_root / "common" / "governments" / "00_governments.txt"
    if not reform_root.is_dir():
        result.add(
            "reform.directory_missing",
            "common/government_reforms is missing",
            "common/government_reforms",
        )
        result.summary = "government reform directory missing"
        return result

    definition_files = tuple(sorted(reform_root.glob("*.txt"), key=lambda path: path.name.casefold()))
    definitions_by_id: dict[str, list[ReformDefinition]] = defaultdict(list)
    for source in definition_files:
        for definition in _top_level_reform_definitions(context, source):
            definitions_by_id[definition.reform_id].append(definition)

    for reform_id, definitions in sorted(definitions_by_id.items()):
        if len(definitions) > 1:
            first = definitions[0]
            for duplicate in definitions[1:]:
                result.add(
                    "reform.duplicate_definition",
                    f"{reform_id} is also defined at "
                    f"{context.relative(first.source)}:{first.line}",
                    context.relative(duplicate.source),
                    duplicate.line,
                )

    visible_source = reform_root / VISIBLE_ROUTE_FILE
    founder_source = reform_root / FOUNDER_FILE
    visible_definitions = _top_level_reform_definitions(context, visible_source)
    founder_definitions = _top_level_reform_definitions(context, founder_source)
    visible_ids = {definition.reform_id for definition in visible_definitions}
    founder_ids = {definition.reform_id for definition in founder_definitions}

    if len(visible_definitions) != EXPECTED_VISIBLE_ROUTE_COUNT:
        result.add(
            "reform.visible_count",
            f"{VISIBLE_ROUTE_FILE} defines {len(visible_definitions)} jxp_reform_* entries; "
            f"expected {EXPECTED_VISIBLE_ROUTE_COUNT}",
            context.relative(visible_source),
        )
    if len(founder_definitions) != EXPECTED_FOUNDER_COUNT:
        result.add(
            "reform.founder_count",
            f"{FOUNDER_FILE} defines {len(founder_definitions)} jxp_reform_* entries; "
            f"expected {EXPECTED_FOUNDER_COUNT}",
            context.relative(founder_source),
        )
    for definition in founder_definitions:
        if not definition.reform_id.startswith("jxp_reform_founder_"):
            result.add(
                "reform.founder_name",
                f"founder reform {definition.reform_id} lacks jxp_reform_founder_ prefix",
                context.relative(definition.source),
                definition.line,
            )
    overlap = visible_ids & founder_ids
    if overlap:
        result.add(
            "reform.set_overlap",
            "visible route and founder sets overlap: " + ", ".join(sorted(overlap)),
        )

    route_counts: dict[str, int] = defaultdict(int)
    for definition in visible_definitions:
        route = _route_key(definition.reform_id)
        if route is None:
            result.add(
                "reform.visible_route_name",
                f"cannot derive route from {definition.reform_id}",
                context.relative(definition.source),
                definition.line,
            )
            continue
        route_counts[route] += 1
        potential = first_object(definition.body, "potential")
        trigger = first_object(definition.body, "trigger")
        expected_tag, expected_flag = ROUTE_REQUIREMENTS[route]
        if first_scalar(definition.body, "allow_normal_conversion") != "yes":
            result.add(
                "reform.visible_conversion",
                f"{definition.reform_id} must use allow_normal_conversion = yes",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(
            potential,
            "jxp_is_japanese_polity_trigger",
            "yes",
        ):
            result.add(
                "reform.visible_stable_potential",
                f"{definition.reform_id} lacks stable Japanese-polity potential",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(potential, "has_reform", definition.reform_id):
            result.add(
                "reform.visible_selected_fallback",
                f"{definition.reform_id} potential does not preserve an already selected reform",
                context.relative(definition.source),
                definition.line,
            )
        if _contains_assignment(potential, "has_country_flag", expected_flag):
            result.add(
                "reform.dynamic_gate_in_potential",
                f"{definition.reform_id} puts dynamic route flag {expected_flag} in potential; "
                "route gates belong in trigger",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(trigger, "has_country_flag", expected_flag):
            result.add(
                "reform.visible_route_trigger",
                f"{definition.reform_id} trigger lacks {expected_flag}",
                context.relative(definition.source),
                definition.line,
            )
        if expected_tag is not None and not _contains_assignment(trigger, "tag", expected_tag):
            result.add(
                "reform.visible_route_tag",
                f"{definition.reform_id} trigger lacks route tag {expected_tag}",
                context.relative(definition.source),
                definition.line,
            )

    for route in sorted(ROUTE_REQUIREMENTS):
        if route_counts.get(route, 0) != 3:
            result.add(
                "reform.visible_route_count",
                f"route {route} has {route_counts.get(route, 0)} visible reforms; expected 3",
                context.relative(visible_source),
            )

    # Definition and registration are insufficient: simulate the actual
    # unified country states and prove that each route exposes only its own
    # three reforms. This catches a dynamic gate accidentally left in
    # potential, a missing final tag, or a foreign route leaking into the UI.
    visible_by_route: dict[str, set[str]] = defaultdict(set)
    for definition in visible_definitions:
        route = _route_key(definition.reform_id)
        if route is not None:
            visible_by_route[route].add(definition.reform_id)
    reform_profile_count = 0
    for profile in BASE_PROFILES:
        if profile.daimyo_stage:
            continue
        reform_profile_count += 1
        expected_routes = {
            ROUTE_BY_FLAG[flag]
            for flag in profile.flags
            if flag in ROUTE_BY_FLAG
        }
        expected_ids = set().union(
            *(visible_by_route[route] for route in expected_routes)
        ) if expected_routes else set()
        actual_ids: set[str] = set()
        for definition in visible_definitions:
            potential = first_object(definition.body, "potential")
            trigger = first_object(definition.body, "trigger")
            potential_values, potential_unknown = evaluate_potential(potential, profile)
            trigger_values, trigger_unknown = evaluate_potential(trigger, profile)
            for unknown in (*potential_unknown, *trigger_unknown):
                result.add(
                    "reform.profile_predicate_unknown",
                    f"{definition.reform_id} uses unsupported profile predicate "
                    f"{unknown.key}: {unknown.reason}",
                    context.relative(definition.source),
                    unknown.line,
                )
            if True in potential_values and True in trigger_values:
                actual_ids.add(definition.reform_id)
        if actual_ids != expected_ids:
            result.add(
                "reform.profile_visibility",
                f"profile {profile.name} exposes the wrong route reforms; missing="
                + ", ".join(sorted(expected_ids - actual_ids))
                + "; foreign="
                + ", ".join(sorted(actual_ids - expected_ids)),
            )

    grant_source = (
        context.mod_root / "common" / "scripted_effects" / "jxp_scripted_effects.txt"
    )
    grant_document = context.document(grant_source) if grant_source.is_file() else None
    grant_effect = (
        first_object(grant_document.root, "jxp_grant_route_reforms_effect")
        if grant_document is not None
        else None
    )
    if not _contains_assignment(grant_effect, "regenerate_government_mechanics", "yes"):
        result.add(
            "reform.route_refresh_missing",
            "the canonical route-reform sync must regenerate government mechanics so "
            "new trigger-gated options appear immediately",
            context.relative(grant_source),
        )

    for definition in founder_definitions:
        potential = first_object(definition.body, "potential")
        if first_scalar(definition.body, "allow_normal_conversion") != "yes":
            result.add(
                "reform.founder_conversion",
                f"{definition.reform_id} must use allow_normal_conversion = yes",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(potential, "has_reform", definition.reform_id):
            result.add(
                "reform.founder_selected_fallback",
                f"{definition.reform_id} potential does not preserve its assigned reform",
                context.relative(definition.source),
                definition.line,
            )

    government_document = context.document(government_file) if government_file.is_file() else None
    if not government_file.is_file():
        result.add(
            "reform.government_file_missing",
            "common/governments/00_governments.txt is missing",
            context.relative(government_file),
        )
        registrations: tuple[ReformRegistration, ...] = ()
        level_indices: dict[tuple[str, str], int] = {}
    elif government_document is None:
        registrations = ()
        level_indices = {}
    else:
        registrations = _collect_registrations(
            government_document.root,
            government_file,
        )
        level_indices = {}
        for government_entry in government_document.root.entries:
            if government_entry.key is None or not isinstance(government_entry.value, Object):
                continue
            levels = first_object(government_entry.value, "reform_levels")
            if levels is None:
                continue
            level_entries = [
                entry
                for entry in levels.entries
                if entry.key is not None and isinstance(entry.value, Object)
            ]
            for index, level_entry in enumerate(level_entries, start=1):
                level_indices[(government_entry.key, level_entry.key)] = index
                if level_entry.key.startswith("jxp_"):
                    result.add(
                        "reform.custom_level_key",
                        f"custom JXP reform level {level_entry.key} is not allowed; "
                        "use vanilla level blocks 1..11",
                        context.relative(government_file),
                        level_entry.line,
                    )

        monarchy = first_object(government_document.root, "monarchy")
        monarchy_levels = first_object(monarchy, "reform_levels")
        actual_first_11 = tuple(
            entry.key
            for entry in (monarchy_levels.entries if monarchy_levels is not None else ())
            if entry.key is not None and isinstance(entry.value, Object)
        )[:11]
        if actual_first_11 != VANILLA_MONARCHY_FIRST_11_LEVELS:
            result.add(
                "reform.vanilla_level_layout",
                "monarchy first-11 level keys differ from the EU4 1.37 vanilla layout: "
                + ", ".join(actual_first_11),
                context.relative(government_file),
            )

    registrations_by_id: dict[str, list[ReformRegistration]] = defaultdict(list)
    for registration in registrations:
        registrations_by_id[registration.reform_id].append(registration)

    active_ids = visible_ids | founder_ids
    mapped_count = sum(len(items) for items in EXPECTED_LEVEL_MEMBERS.values())
    mapped_ids = set(EXPECTED_LEVEL_BY_REFORM)
    if mapped_count != len(mapped_ids):
        result.add(
            "reform.semantic_level_duplicate",
            "semantic reform-level matrix contains a reform in more than one level",
        )
    if mapped_ids != active_ids:
        result.add(
            "reform.semantic_level_coverage",
            "semantic reform-level matrix mismatch; missing="
            + ", ".join(sorted(active_ids - mapped_ids))
            + "; stale="
            + ", ".join(sorted(mapped_ids - active_ids)),
        )
    for reform_id in sorted(active_ids):
        found = registrations_by_id.get(reform_id, [])
        if len(found) != 1:
            location = definitions_by_id.get(reform_id, [None])[0]
            result.add(
                "reform.registration_count",
                f"{reform_id} is registered {len(found)} times; expected exactly once",
                context.relative(location.source) if location is not None else None,
                location.line if location is not None else None,
            )
        for registration in found:
            actual_level = registration.path[2] if len(registration.path) >= 3 else None
            expected_level = EXPECTED_LEVEL_BY_REFORM.get(reform_id)
            if expected_level is not None and actual_level != expected_level:
                result.add(
                    "reform.semantic_level",
                    f"{reform_id} is registered in {actual_level}; semantic matrix "
                    f"requires {expected_level}",
                    context.relative(registration.source),
                    registration.line,
                )
            valid_path = (
                len(registration.path) == 3
                and registration.path[0] == "monarchy"
                and registration.path[1] == "reform_levels"
                and registration.path[2] in VANILLA_MONARCHY_FIRST_11_LEVELS
                and level_indices.get(("monarchy", registration.path[2]), 99) <= 11
            )
            if not valid_path:
                result.add(
                    "reform.registration_location",
                    f"{reform_id} is registered outside monarchy's vanilla first-11 "
                    f"level blocks ({'/'.join(registration.path)})",
                    context.relative(registration.source),
                    registration.line,
                )

    all_defined_ids = set(definitions_by_id)
    parked_ids = all_defined_ids - active_ids
    for reform_id in sorted(parked_ids):
        for registration in registrations_by_id.get(reform_id, []):
            result.add(
                "reform.parked_registered",
                f"parked dormant reform {reform_id} is registered",
                context.relative(registration.source),
                registration.line,
            )

    for reform_id, found in sorted(registrations_by_id.items()):
        if reform_id.startswith("jxp_reform_") and reform_id not in active_ids:
            if reform_id not in parked_ids:
                for registration in found:
                    result.add(
                        "reform.undefined_registered",
                        f"undefined JXP reform {reform_id} is registered",
                        context.relative(registration.source),
                        registration.line,
                    )

    for grant_key in AUTO_GRANT_KEYS:
        for occurrence in context.assignment_occurrences(grant_key):
            if occurrence.value in visible_ids:
                result.add(
                    "reform.visible_auto_grant",
                    f"visible route reform {occurrence.value} is auto-granted by {grant_key}",
                    context.relative(occurrence.source),
                    occurrence.entry.line,
                )
            if occurrence.value in parked_ids:
                result.add(
                    "reform.parked_auto_grant",
                    f"parked reform {occurrence.value} is auto-granted by {grant_key}",
                    context.relative(occurrence.source),
                    occurrence.entry.line,
                )
            if occurrence.value in founder_ids:
                result.add(
                    "reform.founder_auto_grant",
                    f"optional founder reform {occurrence.value} is auto-granted by {grant_key}",
                    context.relative(occurrence.source),
                    occurrence.entry.line,
                )

    set_flags = {
        occurrence.value
        for occurrence in context.assignment_occurrences("set_country_flag")
    }
    clear_flags = {
        occurrence.value
        for occurrence in context.assignment_occurrences("clr_country_flag")
    }
    for flag in (
        "jxp_reform_visibility_migration_v0232",
        "jxp_founder_reform_unlocked_v0234",
        "jxp_founder_reform_reclassified_v0234",
    ):
        if flag not in set_flags:
            result.add(
                "reform.migration_flag_not_set",
                f"government-reform migration flag {flag} is never set",
            )
        if flag not in clear_flags:
            result.add(
                "reform.migration_flag_not_cleared",
                f"government-reform migration flag {flag} is not covered by debug cleanup",
            )
    if "jxp_founder_reform_assigned_v0232" in set_flags:
        result.add(
            "reform.legacy_founder_assignment",
            "legacy founder auto-assignment flag is still being set",
        )
    if "jxp_founder_reform_assigned_v0232" not in clear_flags:
        result.add(
            "reform.legacy_founder_cleanup",
            "legacy founder auto-assignment flag is not cleared by migration/debug cleanup",
        )

    tier_two_fallbacks = context.assignment_occurrences(
        "add_government_reform", "quash_noble_power_reform"
    )
    if len(tier_two_fallbacks) != 1:
        result.add(
            "reform.founder_tier_two_fallback",
            f"found {len(tier_two_fallbacks)} founder reclassification tier-two fallbacks; "
            "expected exactly one",
        )

    result.metrics.update(
        {
            "visible_route_reforms": len(visible_ids),
            "founder_reforms": len(founder_ids),
            "parked_reforms": len(parked_ids),
            "route_visibility_profiles": reform_profile_count,
            "jxp_registrations": sum(
                len(found)
                for reform_id, found in registrations_by_id.items()
                if reform_id.startswith("jxp_reform_")
            ),
        }
    )
    result.summary = (
        f"{len(visible_ids)} visible route + {len(founder_ids)} founder reforms; "
        f"{len(parked_ids)} parked definitions"
    )
    return result
