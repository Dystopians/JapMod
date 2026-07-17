"""Government reform definition, registration, and grant checks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .clausewitz import Object, Scalar, bare_scalars, first_object, first_scalar
from .core import CheckResult, ValidationContext
from .final_states import _evaluate_final_reform_predicate
from .missions import BASE_PROFILES, Profile, evaluate_potential


VISIBLE_ROUTE_FILE = "jxp_18_route_reforms_extra.txt"
FOUNDER_FILE = "jxp_28_founder_house_reforms.txt"
FINAL_STATE_POLITICAL_FILE = "jxp_80_final_state_political_reforms.txt"
DAIMYO_STAGE_FILE = "jxp_83_daimyo_stage_reforms.txt"
JAPANESE_TRACK_FILE = "jxp_84_japanese_government_track.txt"
FINAL_STATE_TRIGGER_FILE = "jxp_79_final_state_triggers.txt"
EXPECTED_VISIBLE_ROUTE_COUNT = 27
EXPECTED_FOUNDER_COUNT = 39
EXPECTED_FINAL_STATE_POLITICAL_COUNT = 10
EXPECTED_DAIMYO_STAGE_COUNT = 3
EXPECTED_JAPANESE_TRACK_COUNT = 36
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
ROUTE_TRIGGER_BY_ROUTE = {
    route: f"jxp_final_state_{route}_trigger" for route in ROUTE_REQUIREMENTS
}
FINAL_STATE_POLITICAL_REQUIREMENTS = {
    "jxp_reform_final_uncommitted_consensus": (
        "jxp_final_state_uncommitted_trigger",
        "JAP Shinto (uncommitted)",
    ),
    "jxp_reform_final_sakoku_constitution": (
        "jxp_final_state_sakoku_trigger",
        "JAP Shinto (sakoku)",
    ),
    "jxp_reform_final_open_cabinet": (
        "jxp_final_state_open_trigger",
        "JAP Shinto (open)",
    ),
    "jxp_reform_final_kirishitan_estates": (
        "jxp_final_state_kirishitan_trigger",
        "KJP Christian",
    ),
    "jxp_reform_final_confucian_censorate": (
        "jxp_final_state_confucian_trigger",
        "CJP Confucian + harmonized Shinto",
    ),
    "jxp_reform_final_imperial_daijokan": (
        "jxp_final_state_imperial_trigger",
        "EJP Imperial",
    ),
    "jxp_reform_final_reformed_synod": (
        "jxp_final_state_reformed_trigger",
        "RFJ Reformed",
    ),
    "jxp_reform_final_kaikyo_diwan": (
        "jxp_final_state_kaikyo_trigger",
        "SJP Kaikyo",
    ),
    "jxp_reform_final_ikko_somon": (
        "jxp_final_state_ikko_trigger",
        "IJP Ikko",
    ),
    "jxp_reform_final_wokou_admiralty": (
        "jxp_final_state_wokou_trigger",
        "WAK Wokou",
    ),
}
EXPECTED_LEVEL_MEMBERS = {
    "feudalism_vs_autocracy": frozenset(),
    "hereditary_vs_nobility": frozenset(
        {
            "jxp_reform_daimyo_kokujin_oaths",
            "jxp_reform_japanese_fudai_service_rolls",
            "jxp_reform_japanese_direct_investiture",
            "jxp_reform_founder_tkg_mikawa_fudai_code",
            "jxp_reform_founder_ama_gassan_toda_law",
            "jxp_reform_founder_htk_wakae_retainer_law",
        }
    ),
    "bureaucracy": frozenset(
        {
            "jxp_reform_daimyo_bunkoku_law",
            "jxp_reform_japanese_gundai_daikan_partition",
            "jxp_reform_japanese_branch_castle_cadasters",
            "jxp_reform_founder_img_tokaido_lawbooks",
            "jxp_reform_sakoku_hidden_learning",
            "jxp_reform_confucian_examination_domains",
            "jxp_reform_reformed_printing_synods",
        }
    ),
    "state_and_religion": frozenset(
        {
            "jxp_reform_japanese_religious_arbitration",
            "jxp_reform_japanese_temple_land_settlement",
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
            "jxp_reform_japanese_ashigaru_muster_rolls",
            "jxp_reform_japanese_kyuba_hatamoto",
            "jxp_reform_japanese_castle_artillery_office",
            "jxp_reform_japanese_funade_ura_service",
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
            "jxp_reform_daimyo_kachu_hyojoshu",
            "jxp_reform_japanese_lordly_arbitration",
            "jxp_reform_japanese_elder_countersignature",
            "jxp_reform_japanese_domain_assembly",
            "jxp_reform_founder_asa_ichijodani_council",
            "jxp_reform_founder_hsk_sakai_kanrei_compact",
            "jxp_reform_kaikyo_monsoon_diwan",
            "jxp_reform_ikko_somon_councils",
        }
    ),
    "growth_of_administration": frozenset(
        {
            "jxp_reform_japanese_court_temple_service",
            "jxp_reform_japanese_yuhitsu_accountants",
            "jxp_reform_japanese_fudai_magistracy",
            "jxp_reform_japanese_public_authority",
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
            "jxp_reform_japanese_townsmen_guild_charters",
            "jxp_reform_japanese_checkpoint_red_seals",
            "jxp_reform_japanese_rakuichi_rakuza",
            "jxp_reform_japanese_war_provisioning",
            "jxp_reform_japanese_coinage_edicts",
            "jxp_reform_japanese_new_field_works",
            "jxp_reform_japanese_overseas_settlement_office",
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
            "jxp_reform_japanese_rule_by_arms",
            "jxp_reform_japanese_general_peace",
            "jxp_reform_japanese_service_compact",
            "jxp_reform_japanese_quarrel_suppression",
            "jxp_reform_japanese_common_security",
            "jxp_reform_founder_ues_kanto_justice",
            "jxp_reform_confucian_sinicized_codes",
            "jxp_reform_imperial_kokugaku_office",
            "jxp_reform_wokou_black_tide_law",
        }
    ),
    "absolute_rule_vs_constitutional": frozenset(
        {
            "jxp_reform_japanese_unitary_investiture",
            "jxp_reform_japanese_domain_federation",
            "jxp_reform_japanese_benevolent_government",
            "jxp_reform_japanese_divine_law",
            *FINAL_STATE_POLITICAL_REQUIREMENTS,
            "jxp_reform_founder_oda_azuchi_statutes",
            "jxp_reform_founder_generic_renovated_japan",
            "jxp_reform_sakoku_sankin_kotai_roads",
            "jxp_reform_reformed_civic_compacts",
        }
    ),
    "separation_of_power": frozenset(
        {
            "jxp_reform_japanese_buke_laws_inspectors",
            "jxp_reform_japanese_hyojosho_collegial_offices",
            "jxp_reform_japanese_petition_direct_appeal",
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
    final_state_source = reform_root / FINAL_STATE_POLITICAL_FILE
    daimyo_stage_source = reform_root / DAIMYO_STAGE_FILE
    japanese_track_source = reform_root / JAPANESE_TRACK_FILE
    final_state_trigger_source = (
        context.mod_root
        / "common"
        / "scripted_triggers"
        / FINAL_STATE_TRIGGER_FILE
    )
    visible_definitions = _top_level_reform_definitions(context, visible_source)
    founder_definitions = _top_level_reform_definitions(context, founder_source)
    final_state_definitions = _top_level_reform_definitions(context, final_state_source)
    daimyo_stage_definitions = _top_level_reform_definitions(
        context, daimyo_stage_source
    )
    japanese_track_definitions = _top_level_reform_definitions(
        context, japanese_track_source
    )
    final_state_trigger_document = (
        context.document(final_state_trigger_source)
        if final_state_trigger_source.is_file()
        else None
    )
    final_state_trigger_objects: dict[str, list[Object]] = defaultdict(list)
    if final_state_trigger_document is not None:
        for entry in final_state_trigger_document.root.entries:
            if entry.key is not None and isinstance(entry.value, Object):
                final_state_trigger_objects[entry.key].append(entry.value)
    visible_ids = {definition.reform_id for definition in visible_definitions}
    founder_ids = {definition.reform_id for definition in founder_definitions}
    final_state_ids = {
        definition.reform_id for definition in final_state_definitions
    }
    daimyo_stage_ids = {
        definition.reform_id for definition in daimyo_stage_definitions
    }
    japanese_track_ids = {
        definition.reform_id for definition in japanese_track_definitions
    }

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
    if len(final_state_definitions) != EXPECTED_FINAL_STATE_POLITICAL_COUNT:
        result.add(
            "reform.final_state_count",
            f"{FINAL_STATE_POLITICAL_FILE} defines {len(final_state_definitions)} "
            f"jxp_reform_* entries; expected {EXPECTED_FINAL_STATE_POLITICAL_COUNT}",
            context.relative(final_state_source),
        )
    if len(daimyo_stage_definitions) != EXPECTED_DAIMYO_STAGE_COUNT:
        result.add(
            "reform.daimyo_stage_count",
            f"{DAIMYO_STAGE_FILE} defines {len(daimyo_stage_definitions)} "
            f"jxp_reform_* entries; expected {EXPECTED_DAIMYO_STAGE_COUNT}",
            context.relative(daimyo_stage_source),
        )
    if len(japanese_track_definitions) != EXPECTED_JAPANESE_TRACK_COUNT:
        result.add(
            "reform.japanese_track_count",
            f"{JAPANESE_TRACK_FILE} defines {len(japanese_track_definitions)} "
            f"jxp_reform_* entries; expected {EXPECTED_JAPANESE_TRACK_COUNT}",
            context.relative(japanese_track_source),
        )
    if final_state_ids != set(FINAL_STATE_POLITICAL_REQUIREMENTS):
        result.add(
            "reform.final_state_inventory",
            "final-state political reform inventory mismatch; missing="
            + ", ".join(sorted(set(FINAL_STATE_POLITICAL_REQUIREMENTS) - final_state_ids))
            + "; foreign="
            + ", ".join(sorted(final_state_ids - set(FINAL_STATE_POLITICAL_REQUIREMENTS))),
            context.relative(final_state_source),
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
    category_overlap = (
        (visible_ids & final_state_ids)
        | (founder_ids & final_state_ids)
        | (daimyo_stage_ids & visible_ids)
        | (daimyo_stage_ids & founder_ids)
        | (daimyo_stage_ids & final_state_ids)
        | (japanese_track_ids & visible_ids)
        | (japanese_track_ids & founder_ids)
        | (japanese_track_ids & final_state_ids)
        | (japanese_track_ids & daimyo_stage_ids)
    )
    if category_overlap:
        result.add(
            "reform.set_overlap",
            "final-state political reforms overlap another active category: "
            + ", ".join(sorted(category_overlap)),
        )

    for definition in final_state_definitions:
        requirement = FINAL_STATE_POLITICAL_REQUIREMENTS.get(definition.reform_id)
        if requirement is None:
            continue
        trigger_id, _profile_name = requirement
        potential = first_object(definition.body, "potential")
        trigger = first_object(definition.body, "trigger")
        if first_scalar(definition.body, "allow_normal_conversion") != "yes":
            result.add(
                "reform.final_state_conversion",
                f"{definition.reform_id} must use allow_normal_conversion = yes",
                context.relative(definition.source),
                definition.line,
            )
        if first_scalar(definition.body, "valid_for_nation_designer") != "no":
            result.add(
                "reform.final_state_nation_designer",
                f"{definition.reform_id} must be excluded from the nation designer",
                context.relative(definition.source),
                definition.line,
            )
        if _contains_assignment(
            potential, "jxp_is_japanese_polity_trigger", "yes"
        ):
            result.add(
                "reform.final_state_broad_potential",
                f"{definition.reform_id} uses broad Japanese-polity potential; "
                "only its exact final state may be visible",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(potential, trigger_id, "yes"):
            result.add(
                "reform.final_state_potential",
                f"{definition.reform_id} potential lacks {trigger_id}",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(
            potential, "has_reform", definition.reform_id
        ):
            result.add(
                "reform.final_state_selected_fallback",
                f"{definition.reform_id} potential does not preserve its selected state",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(trigger, trigger_id, "yes"):
            result.add(
                "reform.final_state_trigger",
                f"{definition.reform_id} trigger lacks {trigger_id}",
                context.relative(definition.source),
                definition.line,
            )

    for definition in (*daimyo_stage_definitions, *japanese_track_definitions):
        potential = first_object(definition.body, "potential")
        trigger = first_object(definition.body, "trigger")
        if first_scalar(definition.body, "allow_normal_conversion") != "yes":
            result.add(
                "reform.japanese_track_conversion",
                f"{definition.reform_id} must use allow_normal_conversion = yes",
                context.relative(definition.source),
                definition.line,
            )
        if first_scalar(definition.body, "valid_for_nation_designer") != "no":
            result.add(
                "reform.japanese_track_nation_designer",
                f"{definition.reform_id} must be excluded from the nation designer",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(
            potential,
            "jxp_uses_japanese_government_reform_track_trigger",
            "yes",
        ):
            result.add(
                "reform.japanese_track_potential",
                f"{definition.reform_id} potential lacks the strict Japanese track trigger",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(
            potential, "has_reform", definition.reform_id
        ):
            result.add(
                "reform.japanese_track_selected_fallback",
                f"{definition.reform_id} potential does not preserve its selected state",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(
            trigger,
            "jxp_uses_japanese_government_reform_track_trigger",
            "yes",
        ):
            result.add(
                "reform.japanese_track_trigger",
                f"{definition.reform_id} trigger lacks the strict Japanese track trigger",
                context.relative(definition.source),
                definition.line,
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
        expected_final_trigger = ROUTE_TRIGGER_BY_ROUTE[route]
        if first_scalar(definition.body, "allow_normal_conversion") != "yes":
            result.add(
                "reform.visible_conversion",
                f"{definition.reform_id} must use allow_normal_conversion = yes",
                context.relative(definition.source),
                definition.line,
            )
        if _contains_assignment(
            potential, "jxp_is_japanese_polity_trigger", "yes"
        ):
            result.add(
                "reform.route_broad_potential",
                f"{definition.reform_id} uses broad Japanese-polity potential; "
                "this leaks cross-route candidates into the government tier",
                context.relative(definition.source),
                definition.line,
            )
        if not _contains_assignment(potential, expected_final_trigger, "yes"):
            result.add(
                "reform.route_exact_potential",
                f"{definition.reform_id} potential lacks {expected_final_trigger}",
                context.relative(definition.source),
                definition.line,
            )
        foreign_final_triggers = sorted(
            trigger_id
            for foreign_route, trigger_id in ROUTE_TRIGGER_BY_ROUTE.items()
            if foreign_route != route
            and _contains_assignment(potential, trigger_id, "yes")
        )
        if foreign_final_triggers:
            result.add(
                "reform.route_cross_potential",
                f"{definition.reform_id} potential references foreign final states: "
                + ", ".join(foreign_final_triggers),
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

    # EU4 builds each tier's candidate list from potential before trigger
    # determines selectability. Keep those matrices separate: combining them
    # hid the 1.37 engine's 16-candidate tier overflow in earlier validation.
    visible_by_route: dict[str, set[str]] = defaultdict(set)
    for definition in visible_definitions:
        route = _route_key(definition.reform_id)
        if route is not None:
            visible_by_route[route].add(definition.reform_id)
    final_state_by_profile = {
        profile_name: reform_id
        for reform_id, (_trigger_id, profile_name) in FINAL_STATE_POLITICAL_REQUIREMENTS.items()
    }
    profiles = tuple(profile for profile in BASE_PROFILES if not profile.daimyo_stage) + (
        Profile(
            "TOY Toyotomi realm (sakoku)",
            "TOY",
            "shinto",
            "eastern",
            flags=frozenset({"jxp_path_sakoku"}),
        ),
        Profile(
            "TOY Toyotomi realm (open)",
            "TOY",
            "shinto",
            "eastern",
            flags=frozenset({"jxp_path_open_trade"}),
        ),
        Profile(
            "TOY Toyotomi realm (corrupt stacked routes)",
            "TOY",
            "shinto",
            "eastern",
            flags=frozenset({"jxp_path_sakoku", "jxp_path_open_trade"}),
        ),
        Profile(
            "foreign non-Japanese monarchy",
            "FRA",
            "catholic",
            "christian",
            culture_group="french",
            japanese_polity=False,
        ),
    )
    reform_profile_count = 0
    maximum_route_final_candidates_per_tier = 0
    for profile in profiles:
        if profile.daimyo_stage:
            continue
        reform_profile_count += 1
        expected_routes = {
            ROUTE_BY_FLAG[flag]
            for flag in profile.flags
            if flag in ROUTE_BY_FLAG
        }
        expected_ids = (
            set(visible_by_route[next(iter(expected_routes))])
            if len(expected_routes) == 1
            else set()
        )
        visible_ids_for_profile: set[str] = set()
        selectable_ids_for_profile: set[str] = set()
        for definition in visible_definitions:
            potential = first_object(definition.body, "potential")
            trigger = first_object(definition.body, "trigger")
            potential_values, potential_unknown = _evaluate_final_reform_predicate(
                potential, profile, final_state_trigger_objects
            )
            trigger_values, trigger_unknown = _evaluate_final_reform_predicate(
                trigger, profile, final_state_trigger_objects
            )
            for unknown in (*potential_unknown, *trigger_unknown):
                result.add(
                    "reform.profile_predicate_unknown",
                    f"{definition.reform_id} uses unsupported profile predicate {unknown}",
                    context.relative(definition.source),
                    definition.line,
                )
            if True in potential_values:
                visible_ids_for_profile.add(definition.reform_id)
                if True in trigger_values:
                    selectable_ids_for_profile.add(definition.reform_id)
        if visible_ids_for_profile != expected_ids:
            result.add(
                "reform.profile_visibility",
                f"profile {profile.name} sees the wrong route reforms; missing="
                + ", ".join(sorted(expected_ids - visible_ids_for_profile))
                + "; foreign="
                + ", ".join(sorted(visible_ids_for_profile - expected_ids)),
            )
        if selectable_ids_for_profile != expected_ids:
            result.add(
                "reform.profile_selectability",
                f"profile {profile.name} can select the wrong route reforms; missing="
                + ", ".join(sorted(expected_ids - selectable_ids_for_profile))
                + "; foreign="
                + ", ".join(sorted(selectable_ids_for_profile - expected_ids)),
            )

        final_visible: set[str] = set()
        for definition in final_state_definitions:
            potential = first_object(definition.body, "potential")
            values, unknown = _evaluate_final_reform_predicate(
                potential, profile, final_state_trigger_objects
            )
            for predicate in unknown:
                result.add(
                    "reform.profile_predicate_unknown",
                    f"{definition.reform_id} uses unsupported profile predicate {predicate}",
                    context.relative(definition.source),
                    definition.line,
                )
            if True in values:
                final_visible.add(definition.reform_id)
        expected_final = (
            {final_state_by_profile[profile.name]}
            if profile.name in final_state_by_profile
            else set()
        )
        if final_visible != expected_final:
            result.add(
                "reform.profile_final_visibility",
                f"profile {profile.name} sees the wrong final political reforms; missing="
                + ", ".join(sorted(expected_final - final_visible))
                + "; foreign="
                + ", ".join(sorted(final_visible - expected_final)),
            )

        candidates_by_tier: dict[str, set[str]] = defaultdict(set)
        for reform_id in visible_ids_for_profile | final_visible:
            level = EXPECTED_LEVEL_BY_REFORM.get(reform_id)
            if level is not None:
                candidates_by_tier[level].add(reform_id)
        profile_maximum = max(
            (len(candidates) for candidates in candidates_by_tier.values()),
            default=0,
        )
        maximum_route_final_candidates_per_tier = max(
            maximum_route_final_candidates_per_tier, profile_maximum
        )
        if profile_maximum > 2:
            result.add(
                "reform.profile_tier_capacity",
                f"profile {profile.name} has {profile_maximum} route/final JXP candidates "
                "in one tier; expected at most 2 before its single founder option",
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

    active_ids = (
        visible_ids
        | founder_ids
        | final_state_ids
        | daimyo_stage_ids
        | japanese_track_ids
    )
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
            if occurrence.value in final_state_ids:
                result.add(
                    "reform.final_state_auto_grant",
                    f"selectable final-state reform {occurrence.value} is auto-granted "
                    f"by {grant_key}",
                    context.relative(occurrence.source),
                    occurrence.entry.line,
                )
            if occurrence.value in daimyo_stage_ids:
                result.add(
                    "reform.japanese_track_auto_grant",
                    f"optional Japanese-track reform {occurrence.value} is auto-granted "
                    f"by {grant_key}",
                    context.relative(occurrence.source),
                    occurrence.entry.line,
                )
            if occurrence.value in japanese_track_ids:
                result.add(
                    "reform.japanese_track_auto_grant",
                    f"optional Japanese-track reform {occurrence.value} is auto-granted "
                    f"by {grant_key}",
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
        "jxp_final_state_political_reform_migration_v0283",
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
            "final_state_political_reforms": len(final_state_ids),
            "daimyo_stage_reforms": len(daimyo_stage_ids),
            "japanese_track_reforms": len(japanese_track_ids),
            "parked_reforms": len(parked_ids),
            "route_visibility_profiles": reform_profile_count,
            "max_route_final_candidates_per_tier": maximum_route_final_candidates_per_tier,
            "max_jxp_candidates_per_tier_with_founder": (
                maximum_route_final_candidates_per_tier + 1
            ),
            "jxp_registrations": sum(
                len(found)
                for reform_id, found in registrations_by_id.items()
                if reform_id.startswith("jxp_reform_")
            ),
        }
    )
    result.summary = (
        f"{len(visible_ids)} visible route + {len(founder_ids)} founder + "
        f"{len(final_state_ids)} final-state political + "
        f"{len(daimyo_stage_ids) + len(japanese_track_ids)} Japanese-track reforms; "
        f"{len(parked_ids)} parked definitions"
    )
    return result
