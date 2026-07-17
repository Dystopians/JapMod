"""Validate the KJP/CJP/RFJ/SJP policy-council parity slice.

This contract deliberately fixes behavior, not just file counts: four exact
route gates reject stacked state, all twelve currently visible reforms own an
independent era-attribute tradeoff and finite result, natural and player-led
entry paths converge on the same events, AI weights are explicit, stale
cross-route state self-cleans, and one public reset effect is available to the
canonical route/debug roots.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .clausewitz import (
    Document,
    Object,
    Scalar,
    entries_named,
    find_assignments,
    first_object,
    first_scalar,
    parse_text,
)
from .core import CheckResult, ValidationContext


TRIGGER_FILE = Path(
    "common/scripted_triggers/jxp_75_route_parity_four_triggers.txt"
)
EVENT_FILE = Path("events/jxp_75_route_parity_four_events.txt")
DECISION_FILE = Path("decisions/jxp_75_route_parity_four_decisions.txt")
DEBUG_DECISION_FILE = Path(
    "decisions/jxp_75_route_parity_four_debug_decisions.txt"
)
MODIFIER_FILE = Path(
    "common/event_modifiers/jxp_75_route_parity_four_modifiers.txt"
)
RESET_EFFECT_FILE = Path(
    "common/scripted_effects/jxp_75_route_parity_four_effects.txt"
)
ROUTE_EFFECT_FILE = Path("common/scripted_effects/jxp_scripted_effects.txt")
SOURCE_LOC_FILE = Path(
    "localisation_source/jxp_75_route_parity_four_l_english_utf8_source.yml"
)
ACTIVE_LOC_FILE = Path(
    "localisation/jxp_75_route_parity_four_l_english.yml"
)

COOLDOWN_MODIFIER = "jxp_75_route_policy_recent"
RESET_EFFECT = "jxp_75_reset_route_parity_four_effect"
FINITE_DAYS = "3650"
NATURAL_MTTH_MONTHS = "120"
STALE_EVENT_ID = "jxp_route_parity_four.100"
ALL_ROUTE_FLAGS = (
    "jxp_path_sakoku",
    "jxp_path_open_trade",
    "jxp_path_kirishitan",
    "jxp_path_confucian",
    "jxp_path_imperial",
    "jxp_path_reformed",
    "jxp_path_kaikyo",
    "jxp_path_ikko",
    "jxp_path_wokou",
)
ERA_EFFECT_PATTERN = re.compile(
    r"^jxp_(?:add|subtract)_(?:tenka_order|imperial_sanction|oceanic_opening)_"
    r"(?:5|10|15)_effect$"
)
COMPANION_ONLY_REFERENCE = re.compile(
    r"\bjxp_map_[A-Za-z0-9_]+\b|\b49(?:4[2-9]|[5-7][0-9]|8[01])\b"
)
RAW_CJK = re.compile(r"[\u3400-\u9fff]")


@dataclass(frozen=True, slots=True)
class OptionContract:
    reform: str
    option_key: str
    outcome_modifier: str
    era_effects: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RouteContract:
    slug: str
    tag: str
    flag: str
    route_trigger: str
    reform_trigger: str
    event_id: str
    decision_id: str
    debug_decision_id: str
    power_trigger: str
    power_effect: str
    options: tuple[OptionContract, ...]


ROUTES = (
    RouteContract(
        slug="kirishitan",
        tag="KJP",
        flag="jxp_path_kirishitan",
        route_trigger="jxp_75_is_kirishitan_route_trigger",
        reform_trigger="jxp_75_has_kirishitan_policy_reform_trigger",
        event_id="jxp_route_parity_four.1",
        decision_id="jxp_decision_convene_kirishitan_visitation",
        debug_decision_id="jxp_debug_fire_route_parity_four_kirishitan",
        power_trigger="dip_power",
        power_effect="add_dip_power",
        options=(
            OptionContract(
                "jxp_reform_kirishitan_seminaries",
                "jxp_route_parity_four.1.a",
                "jxp_75_kirishitan_seminary_visitation",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_subtract_tenka_order_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_kirishitan_misericordia_hospitals",
                "jxp_route_parity_four.1.b",
                "jxp_75_kirishitan_mercy_accounts",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_kirishitan_nagasaki_admiralty",
                "jxp_route_parity_four.1.c",
                "jxp_75_kirishitan_harbor_chaplains",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_add_tenka_order_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
        ),
    ),
    RouteContract(
        slug="confucian",
        tag="CJP",
        flag="jxp_path_confucian",
        route_trigger="jxp_75_is_confucian_route_trigger",
        reform_trigger="jxp_75_has_confucian_policy_reform_trigger",
        event_id="jxp_route_parity_four.2",
        decision_id="jxp_decision_convene_confucian_rite_code_council",
        debug_decision_id="jxp_debug_fire_route_parity_four_confucian",
        power_trigger="adm_power",
        power_effect="add_adm_power",
        options=(
            OptionContract(
                "jxp_reform_confucian_examination_domains",
                "jxp_route_parity_four.2.a",
                "jxp_75_confucian_examination_rosters",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_add_imperial_sanction_5_effect",
                    "jxp_subtract_oceanic_opening_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_confucian_sinicized_codes",
                "jxp_route_parity_four.2.b",
                "jxp_75_confucian_code_commission",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_subtract_oceanic_opening_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_confucian_three_teachings_board",
                "jxp_route_parity_four.2.c",
                "jxp_75_confucian_three_teachings_concordance",
                (
                    "jxp_add_imperial_sanction_5_effect",
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_subtract_tenka_order_5_effect",
                ),
            ),
        ),
    ),
    RouteContract(
        slug="reformed",
        tag="RFJ",
        flag="jxp_path_reformed",
        route_trigger="jxp_75_is_reformed_route_trigger",
        reform_trigger="jxp_75_has_reformed_policy_reform_trigger",
        event_id="jxp_route_parity_four.3",
        decision_id="jxp_decision_convene_reformed_policy_consistory",
        debug_decision_id="jxp_debug_fire_route_parity_four_reformed",
        power_trigger="adm_power",
        power_effect="add_adm_power",
        options=(
            OptionContract(
                "jxp_reform_reformed_printing_synods",
                "jxp_route_parity_four.3.a",
                "jxp_75_reformed_printing_consistory",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_reformed_civic_compacts",
                "jxp_route_parity_four.3.b",
                "jxp_75_reformed_civic_auditors",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_reformed_contract_fleet",
                "jxp_route_parity_four.3.c",
                "jxp_75_reformed_fleet_articles",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_subtract_tenka_order_5_effect",
                ),
            ),
        ),
    ),
    RouteContract(
        slug="kaikyo",
        tag="SJP",
        flag="jxp_path_kaikyo",
        route_trigger="jxp_75_is_kaikyo_route_trigger",
        reform_trigger="jxp_75_has_kaikyo_policy_reform_trigger",
        event_id="jxp_route_parity_four.4",
        decision_id="jxp_decision_review_kaikyo_monsoon_diwan",
        debug_decision_id="jxp_debug_fire_route_parity_four_kaikyo",
        power_trigger="dip_power",
        power_effect="add_dip_power",
        options=(
            OptionContract(
                "jxp_reform_kaikyo_monsoon_diwan",
                "jxp_route_parity_four.4.a",
                "jxp_75_kaikyo_monsoon_accounts",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_kaikyo_wakf_granaries",
                "jxp_route_parity_four.4.b",
                "jxp_75_kaikyo_endowment_granaries",
                (
                    "jxp_add_tenka_order_5_effect",
                    "jxp_add_imperial_sanction_5_effect",
                    "jxp_subtract_oceanic_opening_5_effect",
                ),
            ),
            OptionContract(
                "jxp_reform_kaikyo_spice_guard",
                "jxp_route_parity_four.4.c",
                "jxp_75_kaikyo_convoy_muster",
                (
                    "jxp_add_oceanic_opening_5_effect",
                    "jxp_add_tenka_order_5_effect",
                    "jxp_subtract_imperial_sanction_5_effect",
                ),
            ),
        ),
    ),
)

OUTCOME_MODIFIERS = tuple(
    option.outcome_modifier for route in ROUTES for option in route.options
)
EXPECTED_MODIFIERS = (COOLDOWN_MODIFIER,) + OUTCOME_MODIFIERS


def _canonical_object(obj: Object) -> tuple[object, ...]:
    members: list[tuple[object, ...]] = []
    for entry in obj.entries:
        if isinstance(entry.value, Object):
            value: tuple[object, ...] = ("object", _canonical_object(entry.value))
        else:
            value = ("scalar", entry.value.text)
        members.append((entry.key, entry.operator, value))
    return tuple(sorted(members, key=repr))


def _parsed_body(text: str) -> Object:
    document = parse_text(f"expected = {{\n{text}\n}}")
    body = first_object(document.root, "expected")
    if body is None:  # pragma: no cover - fixed validator literals
        raise AssertionError("invalid internal Clausewitz contract")
    return body


def _expected_route_gate(route: RouteContract) -> Object:
    exclusions = "\n".join(
        f"has_country_flag = {flag}"
        for flag in ALL_ROUTE_FLAGS
        if flag != route.flag
    )
    return _parsed_body(
        f"""
jxp_is_japanese_polity_trigger = yes
OR = {{ tag = {route.tag} has_country_flag = {route.flag} }}
NOT = {{ OR = {{ {exclusions} }} }}
"""
    )


def _expected_reform_gate(route: RouteContract) -> Object:
    reforms = "\n".join(
        f"has_reform = {option.reform}" for option in route.options
    )
    return _parsed_body(
        f"""
{route.route_trigger} = yes
OR = {{ {reforms} }}
"""
    )


def _expected_option_gate(route: RouteContract, reform: str) -> Object:
    return _parsed_body(
        f"{route.route_trigger} = yes\nhas_reform = {reform}"
    )


def _expected_stale_trigger() -> Object:
    groups: list[str] = []
    for route in ROUTES:
        modifiers = "\n".join(
            f"has_country_modifier = {option.outcome_modifier}"
            for option in route.options
        )
        groups.append(
            f"AND = {{ OR = {{ {modifiers} }} "
            f"NOT = {{ {route.route_trigger} = yes }} }}"
        )
    exact_routes = "\n".join(
        f"{route.route_trigger} = yes" for route in ROUTES
    )
    groups.append(
        f"AND = {{ has_country_modifier = {COOLDOWN_MODIFIER} "
        f"NOT = {{ OR = {{ {exact_routes} }} }} }}"
    )
    return _parsed_body("OR = {\n" + "\n".join(groups) + "\n}")


def _document(
    context: ValidationContext, relative: Path, result: CheckResult
) -> Document | None:
    source = context.mod_root / relative
    if not source.is_file():
        result.add(
            "route_parity_four.file_missing",
            f"required file is missing: {relative.as_posix()}",
            relative.as_posix(),
        )
        return None
    document = context.document(source)
    if document is None:
        result.add(
            "route_parity_four.parse",
            context.parse_errors.get(source.resolve(), "could not parse file"),
            relative.as_posix(),
        )
    return document


def _named_object(obj: Object | None, key: str) -> Object | None:
    matches = entries_named(obj, key)
    if len(matches) != 1 or not isinstance(matches[0].value, Object):
        return None
    return matches[0].value


def _direct_scalar(obj: Object | None, key: str, value: str) -> bool:
    if obj is None:
        return False
    return any(
        entry.key == key
        and isinstance(entry.value, Scalar)
        and entry.value.text == value
        for entry in obj.entries
    )


def _event_bodies(document: Document | None) -> dict[str, Object]:
    found: dict[str, Object] = {}
    if document is None:
        return found
    for entry in entries_named(document.root, "country_event"):
        if isinstance(entry.value, Object):
            event_id = first_scalar(entry.value, "id")
            if event_id is not None:
                found[event_id] = entry.value
    return found


def _decision_bodies(document: Document | None) -> dict[str, Object]:
    wrapper = first_object(document.root, "country_decisions") if document else None
    if wrapper is None:
        return {}
    return {
        entry.key: entry.value
        for entry in wrapper.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }


def _modifier_writes(option: Object) -> dict[str, str | None]:
    found: dict[str, str | None] = {}
    for entry in entries_named(option, "add_country_modifier"):
        if not isinstance(entry.value, Object):
            continue
        name = first_scalar(entry.value, "name")
        if name is not None:
            found[name] = first_scalar(entry.value, "duration")
    return found


def _event_call_id(effect: Object | None) -> str | None:
    if effect is None:
        return None
    calls = entries_named(effect, "country_event")
    if len(calls) != 1 or not isinstance(calls[0].value, Object):
        return None
    return first_scalar(calls[0].value, "id")


def _check_triggers(document: Document | None, result: CheckResult) -> int:
    if document is None:
        return 0
    expected_keys = {
        key
        for route in ROUTES
        for key in (route.route_trigger, route.reform_trigger)
    }
    actual_keys = {
        entry.key
        for entry in document.root.entries
        if entry.key is not None and isinstance(entry.value, Object)
    }
    if actual_keys != expected_keys:
        result.add(
            "route_parity_four.trigger_inventory",
            f"trigger inventory is {sorted(actual_keys)}; expected {sorted(expected_keys)}",
            TRIGGER_FILE.as_posix(),
        )
    matched = 0
    for route in ROUTES:
        for key, expected in (
            (route.route_trigger, _expected_route_gate(route)),
            (route.reform_trigger, _expected_reform_gate(route)),
        ):
            actual = _named_object(document.root, key)
            if actual is None or _canonical_object(actual) != _canonical_object(expected):
                result.add(
                    "route_parity_four.trigger_contract",
                    f"{key} no longer matches its exact mutually exclusive route/reform gate",
                    TRIGGER_FILE.as_posix(),
                )
            else:
                matched += 1
    return matched


def _check_visible_events(
    events: dict[str, Object], result: CheckResult
) -> tuple[int, int]:
    matched_events = 0
    matched_options = 0
    for route in ROUTES:
        event = events.get(route.event_id)
        if event is None:
            continue
        trigger = first_object(event, "trigger")
        mtth = first_object(event, "mean_time_to_happen")
        cooldown_reads = (
            find_assignments(trigger, "has_country_modifier", COOLDOWN_MODIFIER)
            if trigger
            else ()
        )
        event_ok = (
            _direct_scalar(trigger, route.route_trigger, "yes")
            and _direct_scalar(trigger, route.reform_trigger, "yes")
            and len(cooldown_reads) == 1
            and "NOT" in cooldown_reads[0][0]
            and mtth is not None
            and _canonical_object(mtth)
            == _canonical_object(_parsed_body(f"months = {NATURAL_MTTH_MONTHS}"))
        )
        if not event_ok:
            result.add(
                "route_parity_four.event_reachability",
                f"{route.event_id} lacks its exact route/reform/cooldown/120-month contract",
                EVENT_FILE.as_posix(),
            )

        options = tuple(
            entry.value
            for entry in entries_named(event, "option")
            if isinstance(entry.value, Object)
        )
        if len(options) != len(route.options):
            result.add(
                "route_parity_four.option_count",
                f"{route.event_id} has {len(options)} options; expected three",
                EVENT_FILE.as_posix(),
            )

        options_by_reform: dict[str, Object] = {}
        for option in options:
            option_trigger = first_object(option, "trigger")
            reform_values = tuple(
                entry.value.text
                for entry in entries_named(option_trigger, "has_reform")
                if isinstance(entry.value, Scalar)
            )
            if len(reform_values) == 1:
                options_by_reform[reform_values[0]] = option

        route_options_ok = len(options) == len(route.options)
        for contract in route.options:
            option = options_by_reform.get(contract.reform)
            if option is None or first_scalar(option, "name") != contract.option_key:
                result.add(
                    "route_parity_four.option_reform_contract",
                    f"{route.event_id} lacks the exact option for {contract.reform}",
                    EVENT_FILE.as_posix(),
                )
                route_options_ok = False
                continue

            option_trigger = first_object(option, "trigger")
            if (
                option_trigger is None
                or _canonical_object(option_trigger)
                != _canonical_object(_expected_option_gate(route, contract.reform))
            ):
                result.add(
                    "route_parity_four.option_gate_contract",
                    f"{contract.option_key} is not bound to its exact route and reform",
                    EVENT_FILE.as_posix(),
                )
                route_options_ok = False

            writes = _modifier_writes(option)
            expected_writes = {
                COOLDOWN_MODIFIER: FINITE_DAYS,
                contract.outcome_modifier: FINITE_DAYS,
            }
            if writes != expected_writes:
                result.add(
                    "route_parity_four.option_modifier_contract",
                    f"{contract.option_key} writes {writes}; expected two finite modifiers",
                    EVENT_FILE.as_posix(),
                )
                route_options_ok = False

            era_effects = tuple(
                entry.key
                for entry in option.entries
                if entry.key is not None
                and isinstance(entry.value, Scalar)
                and entry.value.text == "yes"
                and ERA_EFFECT_PATTERN.fullmatch(entry.key)
            )
            has_gain = any(key.startswith("jxp_add_") for key in era_effects)
            has_cost = any(key.startswith("jxp_subtract_") for key in era_effects)
            if (
                len(era_effects) != len(contract.era_effects)
                or set(era_effects) != set(contract.era_effects)
                or not has_gain
                or not has_cost
            ):
                result.add(
                    "route_parity_four.option_attribute_contract",
                    f"{contract.option_key} era tradeoff is {era_effects}; expected {contract.era_effects}",
                    EVENT_FILE.as_posix(),
                )
                route_options_ok = False

            ai = first_object(option, "ai_chance")
            if (
                first_scalar(ai, "factor") != "1"
                or len(entries_named(ai, "modifier")) < 1
            ):
                result.add(
                    "route_parity_four.option_ai_contract",
                    f"{contract.option_key} lacks explicit contextual AI weighting",
                    EVENT_FILE.as_posix(),
                )
                route_options_ok = False
            else:
                matched_options += 1

        if event_ok and route_options_ok:
            matched_events += 1
    return matched_events, matched_options


def _check_stale_cleanup(events: dict[str, Object], result: CheckResult) -> int:
    event = events.get(STALE_EVENT_ID)
    if event is None:
        return 0
    trigger = first_object(event, "trigger")
    mtth = first_object(event, "mean_time_to_happen")
    immediate = first_object(event, "immediate")
    options = tuple(
        entry.value
        for entry in entries_named(event, "option")
        if isinstance(entry.value, Object)
    )
    valid = (
        first_scalar(event, "hidden") == "yes"
        and trigger is not None
        and _canonical_object(trigger) == _canonical_object(_expected_stale_trigger())
        and mtth is not None
        and _canonical_object(mtth) == _canonical_object(_parsed_body("days = 1"))
        and _direct_scalar(immediate, RESET_EFFECT, "yes")
        and len(options) == 1
        and first_scalar(options[0], "name") == "OK"
    )
    if not valid:
        result.add(
            "route_parity_four.cross_route_cleanup",
            "hidden cleanup must detect each outcome family against its exact current route and reset within one day",
            EVENT_FILE.as_posix(),
        )
        return 0
    return len(ROUTES)


def _check_events(document: Document | None, result: CheckResult) -> tuple[int, int, int]:
    events = _event_bodies(document)
    expected_ids = {route.event_id for route in ROUTES} | {STALE_EVENT_ID}
    if set(events) != expected_ids:
        result.add(
            "route_parity_four.event_inventory",
            f"event IDs are {sorted(events)}; expected {sorted(expected_ids)}",
            EVENT_FILE.as_posix(),
        )
    namespace_count = 0
    if document is not None:
        namespace_count = sum(
            1
            for entry in entries_named(document.root, "namespace")
            if isinstance(entry.value, Scalar)
            and entry.value.text == "jxp_route_parity_four"
        )
    if namespace_count != 1:
        result.add(
            "route_parity_four.namespace",
            f"jxp_route_parity_four namespace appears {namespace_count} times",
            EVENT_FILE.as_posix(),
        )
    visible, options = _check_visible_events(events, result)
    cleanup_routes = _check_stale_cleanup(events, result)
    return visible, options, cleanup_routes


def _check_decisions(
    document: Document | None,
    debug_document: Document | None,
    result: CheckResult,
) -> tuple[int, int]:
    decisions = _decision_bodies(document)
    debug_decisions = _decision_bodies(debug_document)
    expected = {route.decision_id for route in ROUTES}
    expected_debug = {route.debug_decision_id for route in ROUTES}
    if set(decisions) != expected:
        result.add(
            "route_parity_four.decision_inventory",
            f"decision inventory is {sorted(decisions)}; expected {sorted(expected)}",
            DECISION_FILE.as_posix(),
        )
    if set(debug_decisions) != expected_debug:
        result.add(
            "route_parity_four.debug_inventory",
            f"debug inventory is {sorted(debug_decisions)}; expected {sorted(expected_debug)}",
            DEBUG_DECISION_FILE.as_posix(),
        )

    matched = 0
    debug_matched = 0
    for route in ROUTES:
        decision = decisions.get(route.decision_id)
        if decision is not None:
            potential = first_object(decision, "potential")
            allow = first_object(decision, "allow")
            effect = first_object(decision, "effect")
            ai = first_object(decision, "ai_will_do")
            cooldown_reads = (
                find_assignments(allow, "has_country_modifier", COOLDOWN_MODIFIER)
                if allow
                else ()
            )
            valid = (
                _direct_scalar(potential, route.route_trigger, "yes")
                and _direct_scalar(allow, route.reform_trigger, "yes")
                and _direct_scalar(allow, "is_at_war", "no")
                and _direct_scalar(allow, route.power_trigger, "25")
                and len(cooldown_reads) == 1
                and "NOT" in cooldown_reads[0][0]
                and _direct_scalar(effect, route.power_effect, "-25")
                and _event_call_id(effect) == route.event_id
                and first_scalar(ai, "factor") == "1"
                and len(entries_named(ai, "modifier")) >= 2
            )
            if not valid:
                result.add(
                    "route_parity_four.decision_contract",
                    f"{route.decision_id} lacks its route/reform/cost/cooldown/event/AI contract",
                    DECISION_FILE.as_posix(),
                )
            else:
                matched += 1

        debug = debug_decisions.get(route.debug_decision_id)
        if debug is not None:
            potential = first_object(debug, "potential")
            effect = first_object(debug, "effect")
            ai = first_object(debug, "ai_will_do")
            valid = (
                _direct_scalar(potential, "ai", "no")
                and _direct_scalar(potential, "has_country_flag", "jxp_debug_enabled")
                and _direct_scalar(
                    potential, "has_country_flag", "jxp_debug_events_enabled"
                )
                and _direct_scalar(
                    potential,
                    "has_country_flag",
                    "jxp_debug_event_category_early",
                )
                and _direct_scalar(potential, route.route_trigger, "yes")
                and _direct_scalar(potential, route.reform_trigger, "yes")
                and _direct_scalar(effect, RESET_EFFECT, "yes")
                and not entries_named(effect, "remove_country_modifier")
                and _event_call_id(effect) == route.event_id
                and first_scalar(ai, "factor") == "0"
            )
            if not valid:
                result.add(
                    "route_parity_four.debug_root_interface",
                    f"{route.debug_decision_id} must use canonical debug gates and the public reset callable",
                    DEBUG_DECISION_FILE.as_posix(),
                )
            else:
                debug_matched += 1
    return matched, debug_matched


def _check_modifiers_and_reset(
    modifier_document: Document | None,
    reset_document: Document | None,
    route_effect_document: Document | None,
    result: CheckResult,
) -> tuple[int, int, int]:
    definitions = (
        {
            entry.key
            for entry in modifier_document.root.entries
            if entry.key is not None and isinstance(entry.value, Object)
        }
        if modifier_document is not None
        else set()
    )
    if definitions != set(EXPECTED_MODIFIERS):
        result.add(
            "route_parity_four.modifier_inventory",
            f"modifier inventory is {sorted(definitions)}; expected {sorted(EXPECTED_MODIFIERS)}",
            MODIFIER_FILE.as_posix(),
        )

    reset_matched = 0
    if reset_document is not None:
        roots = {
            entry.key: entry.value
            for entry in reset_document.root.entries
            if entry.key is not None and isinstance(entry.value, Object)
        }
        reset = roots.get(RESET_EFFECT)
        removals = (
            tuple(
                entry.value.text
                for entry in entries_named(reset, "remove_country_modifier")
                if isinstance(entry.value, Scalar)
            )
            if isinstance(reset, Object)
            else ()
        )
        if (
            set(roots) != {RESET_EFFECT}
            or len(removals) != len(EXPECTED_MODIFIERS)
            or set(removals) != set(EXPECTED_MODIFIERS)
        ):
            result.add(
                "route_parity_four.route_cleanup_contract",
                "public reset effect must remove every finite modifier exactly once",
                RESET_EFFECT_FILE.as_posix(),
            )
        else:
            reset_matched = len(EXPECTED_MODIFIERS)
    route_hook = 0
    if route_effect_document is not None:
        occurrences = find_assignments(
            route_effect_document.root, RESET_EFFECT, "yes"
        )
        if (
            len(occurrences) != 1
            or "jxp_clear_route_modifiers_effect" not in occurrences[0][0]
        ):
            result.add(
                "route_parity_four.canonical_route_cleanup",
                f"{RESET_EFFECT} must be called exactly once by jxp_clear_route_modifiers_effect",
                ROUTE_EFFECT_FILE.as_posix(),
            )
        else:
            route_hook = 1
    return len(definitions & set(EXPECTED_MODIFIERS)), reset_matched, route_hook


def _localisation_keys() -> set[str]:
    keys: set[str] = set()
    for route in ROUTES:
        keys.update(
            {
                f"{route.decision_id}_title",
                f"{route.decision_id}_desc",
                route.reform_trigger,
                f"{route.event_id}.t",
                f"{route.event_id}.d",
                f"{route.debug_decision_id}_title",
                f"{route.debug_decision_id}_desc",
            }
        )
        keys.update(option.option_key for option in route.options)
    for modifier in EXPECTED_MODIFIERS:
        keys.add(modifier)
        keys.add(f"{modifier}_desc")
    return keys


def _read_loc_keys(path: Path, encoding: str) -> set[str]:
    text = path.read_text(encoding=encoding)
    return {
        match.group(1)
        for match in re.finditer(r"^\s+([A-Za-z0-9_.-]+):\d+\s+", text, re.MULTILINE)
    }


def _check_localisation(context: ValidationContext, result: CheckResult) -> int:
    required = _localisation_keys()
    source = context.mod_root / SOURCE_LOC_FILE
    active = context.mod_root / ACTIVE_LOC_FILE
    if not source.is_file() or not active.is_file():
        result.add(
            "route_parity_four.localisation_file",
            "source and active localisation files are both required",
        )
        return 0
    source_text = source.read_text(encoding="utf-8-sig")
    source_keys = _read_loc_keys(source, "utf-8-sig")
    active_keys = _read_loc_keys(active, "utf-8-sig")
    if not RAW_CJK.search(source_text):
        result.add(
            "route_parity_four.localisation_source",
            "UTF-8 source localisation must retain readable Chinese prose",
            SOURCE_LOC_FILE.as_posix(),
        )
    active_bytes = active.read_bytes()
    active_text = active_bytes.decode("utf-8-sig")
    if not active_bytes.startswith(b"\xef\xbb\xbf") or RAW_CJK.search(active_text):
        result.add(
            "route_parity_four.localisation_active",
            "active localisation must be UTF-8 BOM and EU4SpecialEscape encoded",
            ACTIVE_LOC_FILE.as_posix(),
        )
    missing_source = required - source_keys
    missing_active = required - active_keys
    if missing_source or missing_active:
        result.add(
            "route_parity_four.localisation_keys",
            f"missing source={sorted(missing_source)} active={sorted(missing_active)}",
        )
        return 0
    return len(required)


def _check_surface_safety(context: ValidationContext, result: CheckResult) -> None:
    gameplay = (
        TRIGGER_FILE,
        EVENT_FILE,
        DECISION_FILE,
        DEBUG_DECISION_FILE,
        RESET_EFFECT_FILE,
    )
    for relative in gameplay:
        source = context.mod_root / relative
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8-sig")
        if re.search(r"\b(?:set|clr)_country_flag\s*=", text):
            result.add(
                "route_parity_four.persistent_flag_write",
                "route-parity content must not write or clear persistent country flags",
                relative.as_posix(),
            )
        if re.search(r"\bchange_tag\s*=", text):
            result.add(
                "route_parity_four.tag_mutation",
                "route-parity content must not change country tags",
                relative.as_posix(),
            )
        match = COMPANION_ONLY_REFERENCE.search(text)
        if match is not None:
            result.add(
                "route_parity_four.companion_reference",
                f"main-mod slice references companion-only object {match.group(0)}",
                relative.as_posix(),
                text.count("\n", 0, match.start()) + 1,
            )


def check_route_parity_four_content(context: ValidationContext) -> CheckResult:
    """Return the exact four-route interaction and lifecycle contract."""

    result = CheckResult("Kirishitan, Confucian, Reformed, and Kaikyo route parity")
    trigger_document = _document(context, TRIGGER_FILE, result)
    event_document = _document(context, EVENT_FILE, result)
    decision_document = _document(context, DECISION_FILE, result)
    debug_document = _document(context, DEBUG_DECISION_FILE, result)
    modifier_document = _document(context, MODIFIER_FILE, result)
    reset_document = _document(context, RESET_EFFECT_FILE, result)
    route_effect_document = _document(context, ROUTE_EFFECT_FILE, result)

    triggers = _check_triggers(trigger_document, result)
    events, options, cross_cleanup = _check_events(event_document, result)
    decisions, debug_entries = _check_decisions(
        decision_document, debug_document, result
    )
    modifiers, route_cleanup, route_hook = _check_modifiers_and_reset(
        modifier_document, reset_document, route_effect_document, result
    )
    localisation = _check_localisation(context, result)
    _check_surface_safety(context, result)

    result.metrics.update(
        {
            "route_gates": triggers,
            "native_events": events,
            "reform_options": options,
            "native_decisions": decisions,
            "debug_entries": debug_entries,
            "modifiers": modifiers,
            "route_cleanup": route_cleanup,
            "route_cleanup_hook": route_hook,
            "cross_route_cleanup": cross_cleanup,
            "localisation_keys": localisation,
        }
    )
    result.summary = (
        f"{events}/{len(ROUTES)} native events; "
        f"{options}/{sum(len(route.options) for route in ROUTES)} reform options; "
        f"{decisions}/{len(ROUTES)} decisions and {debug_entries}/{len(ROUTES)} debug entries; "
        f"{route_cleanup}/{len(EXPECTED_MODIFIERS)} reset-cleaned modifiers and "
        f"{route_hook}/1 canonical route hook; "
        f"{cross_cleanup}/{len(ROUTES)} exact-route stale cleanup branches"
    )
    return result
