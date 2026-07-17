#!/usr/bin/env python3
"""Reflow JXP missions to renderer-safe EU4 1.37.5 geometry.

The visible graph follows the measured vanilla Japanese limits: vertical
edges may span two rows, but cross-column edges must enter the immediately
following row. It also rejects non-adjacent columns, diagonal crossings, and
more than two visible parents. Longer logical prerequisites remain mission
trigger conditions, so the redesign does not weaken progression.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from jxp_validation.core import CheckResult, ValidationContext
from jxp_validation.create_legacy_bom_mission_aliases_v0241 import (
    FILE_PREFIX as LEGACY_BOM_FILE_PREFIX,
)
from jxp_validation.missions import PROFILES, evaluate_potential, extract_mission_series
from reflow_missions_v023 import LAYOUT as LEGACY_LAYOUT
from reflow_missions_v023 import matching_brace


def spaced(start: int, count: int, step: int = 2) -> tuple[int, ...]:
    return tuple(start + step * index for index in range(count))


EASTASIA_ORDER = (
    "jxp_mission_eastasia_ryukyu_gateway",
    "jxp_mission_eastasia_korea_embassy",
    "jxp_mission_eastasia_ming_trade",
    "jxp_mission_eastasia_ryukyu_registry",
    "jxp_mission_eastasia_liaodong_route",
    "jxp_mission_eastasia_tribute_registry",
    "jxp_mission_eastasia_tsushima_office",
    "jxp_mission_eastasia_manchu_watch",
    "jxp_mission_eastasia_nagasaki_interpreters",
    "jxp_mission_eastasia_taiwan_lanes",
    "jxp_mission_eastasia_balance_mandate",
    "jxp_mission_eastasia_hegemon_of_the_seas",
    "jxp_mission_eastasia_celestial_diplomacy",
    "jxp_mission_eastasia_littoral_entrepots",
    "jxp_mission_eastasia_rite_sphere",
)

PACIFIC_ORDER = (
    "jxp_mission_pacific_charter",
    "jxp_mission_pacific_ogasawara_anchor",
    "jxp_mission_pacific_guam_waystation",
    "jxp_mission_pacific_manila_link",
    "jxp_mission_pacific_admiralty",
    "jxp_mission_pacific_hawaii_soundings",
    "jxp_mission_pacific_north_charts",
    "jxp_mission_pacific_silver_current",
    "jxp_mission_pacific_alaska_posts",
    "jxp_mission_pacific_california_harbors",
    "jxp_mission_pacific_new_world_towns",
    "jxp_mission_pacific_oceanic_sun",
    "jxp_mission_eastasia_claim_mandate",
    "jxp_mission_eastasia_break_mandate",
)

STATE_ORDER = (
    "jxp_mission_secure_home_domain",
    "jxp_mission_road_to_kyoto",
    "jxp_mission_unite_the_isles",
    "jxp_mission_settle_the_realm",
    "jxp_mission_land_survey_state",
    "jxp_mission_modern_state",
    "jxp_mission_route_inherited_realm",
    "jxp_mission_route_muster_rolls",
    "jxp_mission_route_settle_new_constitution",
    "jxp_mission_route_province_registers",
    "jxp_mission_route_firearm_offices",
    "jxp_mission_route_laws_of_the_new_realm",
    "jxp_mission_route_archipelago_circuit",
    "jxp_mission_route_renewed_japan",
)

COURT_ORDER = (
    "jxp_mission_capital_cities",
    "jxp_mission_kyoto_and_edo",
    "jxp_mission_iwami_silver",
    "jxp_mission_osaka_granary",
    "jxp_mission_tanegashima_firearms",
    "jxp_mission_massed_volley",
    "jxp_mission_route_two_capitals",
    "jxp_mission_route_rites_of_the_isles",
    "jxp_mission_route_rice_and_silver",
    "jxp_mission_route_guard_the_sea_lanes",
    "jxp_mission_route_post_station_ledger",
    "jxp_mission_house_diet_into_realm",
    "jxp_mission_house_law_local_offices",
    "jxp_mission_house_law_state_doctrine",
)

CONFUCIAN_IMPERIAL_ORDER = (
    "jxp_mission_zhu_xi_lectures",
    "jxp_mission_domain_schools",
    "jxp_mission_kyoto_rites",
    "jxp_mission_merit_over_lineage",
    "jxp_mission_korean_envoys",
    "jxp_mission_yamato_restoration",
    "jxp_mission_ritual_state",
    "jxp_mission_osaka_rice_ledger",
    "jxp_mission_castle_town_markets",
    "jxp_mission_domain_school_network",
    "jxp_mission_nagasaki_translation_house",
    "jxp_mission_silver_silk_routing",
    "jxp_mission_three_capitals_ledgers",
)


# One row plan per mission series.  Explicit orders are used where the source
# order contains parallel branches whose blocks are intentionally interleaved.
SERIES_PLANS: dict[str, tuple[tuple[int, ...], tuple[str, ...] | None]] = {
    "jxp_japan_eastasia_missions": (tuple(range(9, 24)), EASTASIA_ORDER),
    "jxp_japan_pacific_missions": (tuple(range(9, 23)), PACIFIC_ORDER),
    "jxp_daimyo_domain_missions": (spaced(9, 6), None),
    "jxp_daimyo_contact_missions": (spaced(10, 6), None),
    "jxp_daimyo_society_missions": (spaced(10, 6), None),
    "jxp_daimyo_unification_missions": (spaced(9, 6), None),
    "jxp_kirishitan_deep_missions": (spaced(11, 6), None),
    "jxp_reformed_deep_missions": (spaced(11, 6), None),
    "jxp_kaikyo_deep_missions": (spaced(12, 6), None),
    "jxp_ikko_route_missions": (spaced(10, 7), None),
    "jxp_wokou_route_missions": (spaced(10, 7), None),
    "jxp_ikko_common_economy_missions": (spaced(10, 7), None),
    "jxp_shinto_branch_missions": (spaced(11, 5), None),
    "jxp_christian_branch_missions": (spaced(12, 5), None),
    "jxp_confucian_branch_missions": (spaced(10, 5), None),
    "jxp_muslim_branch_missions": (spaced(11, 5), None),
    "jxp_popular_branch_missions": (spaced(11, 5), None),
    "jxp_frontier_diplomacy_missions": (spaced(12, 6), None),
    "jxp_cjp_syncretic_missions": (spaced(11, 5), None),
    "jxp_ejp_restoration_state_missions": (spaced(10, 5), None),
    "jxp_ejp_court_rite_missions": (spaced(11, 5), None),
    "jxp_ejp_imperial_seas_missions": (spaced(12, 5), None),
    "jxp_rfj_covenant_horizon_missions": (spaced(12, 5), None),
    "jxp_wak_black_current_missions": (spaced(11, 5), None),
    "jxp_daimyo_warrior_house_missions": (spaced(9, 6), None),
    "jxp_daimyo_court_house_missions": (spaced(9, 6), None),
    "jxp_daimyo_sea_house_missions": (spaced(9, 6), None),
    "jxp_daimyo_frontier_house_missions": (spaced(9, 6), None),
    "jxp_daimyo_temple_market_house_missions": (spaced(9, 6), None),
    "jxp_toyotomi_realm_missions": (spaced(9, 7), None),
    "jxp_toyotomi_court_missions": (spaced(10, 7), None),
    "jxp_toyotomi_horizon_missions": (spaced(9, 7), None),
    "jxp_japan_uncommitted_council_missions": (spaced(10, 5), None),
    "jxp_japan_uncommitted_horizon_missions": (spaced(10, 5), None),
    "jxp_japan_sakoku_horizon_missions": (spaced(10, 7), None),
    # The common late-game columns are deliberately dense. Vanilla Japanese
    # trees use one-row vertical steps, and keeping both spines inside rows
    # 1..14 prevents short route branches from leaving a half-screen void.
    "jxp_japan_state_missions": (tuple(range(9, 23)), STATE_ORDER),
    "jxp_japan_court_missions": (tuple(range(9, 23)), COURT_ORDER),
    "jxp_japan_sakoku_missions": (spaced(10, 7), None),
    "jxp_japan_open_missions": (spaced(10, 7), None),
    "jxp_japan_kirishitan_missions": (spaced(10, 7), None),
    "jxp_japan_reformed_missions": (spaced(10, 5), None),
    "jxp_japan_confucian_imperial_missions": (
        tuple(range(10, 23)),
        CONFUCIAN_IMPERIAL_ORDER,
    ),
    "jxp_japan_kaikyo_missions": (spaced(10, 5), None),
}

NO_CHAIN_TARGETS = {
    "jxp_mission_eastasia_claim_mandate",
    "jxp_mission_eastasia_break_mandate",
}

PINNED_OVERRIDE_FILES = {"Japanese_Missions.txt", "DOM_Japanese_Missions.txt"}
CUSTOM_TREE_ROW_OFFSET = 8


def depends_on(graph: dict[str, set[str]], start: str, target: str) -> bool:
    pending = list(graph.get(start, ()))
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(graph.get(current, ()))
    return False


def active_profiles(series_list) -> dict[str, frozenset[int]]:
    active: dict[str, set[int]] = defaultdict(set)
    for series in series_list:
        if series.generic:
            continue
        for index, profile in enumerate(PROFILES):
            possible, _unknown = evaluate_potential(series.potential, profile)
            if True not in possible:
                continue
            for mission in series.missions:
                active[mission.mission_id].add(index)
    return {mission_id: frozenset(values) for mission_id, values in active.items()}


def cross_geometry(edge, rows, slots):
    parent, child = edge
    if slots[parent] < slots[child]:
        return slots[parent], rows[parent], rows[child]
    return slots[child], rows[child], rows[parent]


def crosses(first, second, rows, slots) -> bool:
    if set(first) & set(second):
        return False
    first_left, first_left_row, first_right_row = cross_geometry(first, rows, slots)
    second_left, second_left_row, second_right_row = cross_geometry(second, rows, slots)
    if first_left != second_left:
        return False
    return (first_left_row - second_left_row) * (first_right_row - second_right_row) < 0


def vertical_clear(parent, child, rows, slots, profiles, cells) -> bool:
    if slots[parent] != slots[child] or rows[child] - rows[parent] != 2:
        return True
    shared = profiles.get(parent, frozenset()) & profiles.get(child, frozenset())
    middle = rows[parent] + 1
    for profile_index in shared:
        occupant = cells[profile_index].get((slots[parent], middle))
        if occupant is not None and occupant not in {parent, child}:
            return False
    return True


def build_layout(series_list):
    series_by_name = {series.name: series for series in series_list}
    missing_plans = sorted(set(series_by_name) - set(SERIES_PLANS))
    stale_plans = sorted(set(SERIES_PLANS) - set(series_by_name))
    if missing_plans or stale_plans:
        raise ValueError(
            f"mission-series plan mismatch; missing={missing_plans}, stale={stale_plans}"
        )

    for profile in PROFILES:
        by_slot: dict[int, list[str]] = defaultdict(list)
        for series in series_list:
            if series.generic or series.slot is None:
                continue
            possible, _unknown = evaluate_potential(series.potential, profile)
            if True in possible:
                by_slot[series.slot].append(series.name)
        for slot, names in sorted(by_slot.items()):
            if len(names) > 1:
                raise ValueError(
                    f"profile {profile.name} activates overlapping mission series "
                    f"in slot {slot}: {', '.join(names)}"
                )

    rows: dict[str, int] = {}
    slots: dict[str, int] = {}
    display_orders: dict[str, tuple[str, ...]] = {}
    mission_to_series: dict[str, str] = {}
    for series_name, series in series_by_name.items():
        plan_rows, explicit_order = SERIES_PLANS[series_name]
        plan_rows = tuple(row - CUSTOM_TREE_ROW_OFFSET for row in plan_rows)
        if any(row <= 0 for row in plan_rows):
            raise ValueError(f"compacted row plan for {series_name} is not positive")
        source_ids = tuple(mission.mission_id for mission in series.missions)
        order = explicit_order or source_ids
        if set(order) != set(source_ids) or len(order) != len(source_ids):
            raise ValueError(f"display order for {series_name} does not match its missions")
        if len(plan_rows) != len(order):
            raise ValueError(
                f"row plan for {series_name} has {len(plan_rows)} rows for {len(order)} missions"
            )
        if series.slot is None:
            raise ValueError(f"series {series_name} has no slot")
        display_orders[series_name] = order
        for mission_id, row in zip(order, plan_rows):
            if mission_id in rows:
                raise ValueError(f"duplicate mission id in row plan: {mission_id}")
            rows[mission_id] = row
            slots[mission_id] = series.slot
            mission_to_series[mission_id] = series_name

    missing = sorted(set(LEGACY_LAYOUT) - set(rows))
    if missing:
        raise ValueError(f"mission row coverage is missing legacy missions: {missing}")

    # 0.24.x extends the original 0.23 layout snapshot.  Preserve the pinned
    # logical graph for old missions and seed newly authored missions from
    # their current explicit prerequisites.
    current_required = {
        mission.mission_id: mission.required
        for series in series_list
        for mission in series.missions
    }
    logical = {
        mission_id: {
            item
            for item in LEGACY_LAYOUT.get(
                mission_id,
                (rows[mission_id], current_required.get(mission_id, ())),
            )[1]
            if item in rows
        }
        for mission_id in rows
    }
    # The two outcomes are mutually exclusive.  The common continuation is
    # gated by the resolution flag in its trigger, not by completing both.
    logical["jxp_mission_eastasia_hegemon_of_the_seas"] = {
        "jxp_mission_eastasia_balance_mandate",
        "jxp_mission_equal_treaties",
    }
    # WAK no longer borrows the shared Shinto column. Rebind the saved 0.23
    # logical graph to the dedicated Black Current branch so reflow cannot
    # resurrect inactive shrine prerequisites.
    logical.update(
        {
            "jxp_mission_setouchi_suigun": {
                "jxp_mission_fund_wokou",
                "jxp_mission_wak_letters_of_black_current",
            },
            "jxp_mission_tsushima_brokers": {
                "jxp_mission_setouchi_suigun",
                "jxp_mission_wak_boarding_schools",
            },
            "jxp_mission_ryukyu_sea_gate": {
                "jxp_mission_tsushima_brokers",
                "jxp_mission_wak_island_courts",
            },
            "jxp_mission_ming_sea_smugglers": {
                "jxp_mission_ryukyu_sea_gate",
                "jxp_mission_wak_tidewater_arsenals",
            },
            "jxp_mission_wokou_admiralty": {
                "jxp_mission_ming_sea_smugglers",
                "jxp_mission_wak_black_tide_code",
            },
        }
    )

    chain_edges: set[tuple[str, str]] = set()
    for series_name, order in display_orders.items():
        for parent, child in zip(order, order[1:]):
            if child in NO_CHAIN_TARGETS:
                continue
            if rows[child] <= rows[parent] or rows[child] - rows[parent] > 2:
                continue
            eligible_same_series = any(
                mission_to_series.get(dependency) == series_name
                and 0 < rows[child] - rows[dependency] <= 2
                for dependency in logical[child]
            )
            if eligible_same_series:
                continue
            if depends_on(logical, parent, child):
                continue
            logical[child].add(parent)
            chain_edges.add((parent, child))

    for mission_id in rows:
        if depends_on(logical, mission_id, mission_id):
            raise ValueError(f"combined logical graph contains a cycle at {mission_id}")

    profiles = active_profiles(series_list)
    cells: list[dict[tuple[int, int], str]] = [dict() for _ in PROFILES]
    for mission_id, active in profiles.items():
        for profile_index in active:
            coordinate = (slots[mission_id], rows[mission_id])
            previous = cells[profile_index].get(coordinate)
            if previous is not None:
                raise ValueError(
                    f"profile {PROFILES[profile_index].name} collides at {coordinate}: "
                    f"{previous}, {mission_id}"
                )
            cells[profile_index][coordinate] = mission_id

    selected: dict[str, list[str]] = defaultdict(list)
    accepted_cross: list[tuple[str, str]] = []

    def span_ok(parent: str, child: str) -> bool:
        row_span = rows[child] - rows[parent]
        column_span = abs(slots[child] - slots[parent])
        return (
            0 < row_span <= 2
            and column_span <= 1
            and (column_span == 0 or row_span == 1)
        )

    # Mandatory chain edges and renderer-clear vertical legacy edges establish
    # the backbone before optional diagonals are considered.
    for parent, child in sorted(chain_edges, key=lambda edge: (rows[edge[1]], slots[edge[1]])):
        if not span_ok(parent, child):
            raise ValueError(f"chain edge exceeds renderer limits: {parent} -> {child}")
        if not vertical_clear(parent, child, rows, slots, profiles, cells):
            raise ValueError(f"chain edge crosses an occupied cell: {parent} -> {child}")
        selected[child].append(parent)

    same_slot = []
    cross_slot = []
    for child, dependencies in logical.items():
        for parent in dependencies:
            edge = (parent, child)
            if edge in chain_edges or not span_ok(parent, child):
                continue
            if slots[parent] == slots[child]:
                same_slot.append(edge)
            else:
                cross_slot.append(edge)

    for parent, child in sorted(
        same_slot,
        key=lambda edge: (rows[edge[1]], rows[edge[1]] - rows[edge[0]], edge[1], edge[0]),
    ):
        if len(selected[child]) >= 2:
            continue
        if vertical_clear(parent, child, rows, slots, profiles, cells):
            selected[child].append(parent)

    def cross_priority(edge):
        parent, child = edge
        return (
            bool(selected[child]),
            rows[child],
            rows[child] - rows[parent],
            slots[child],
            slots[parent],
            child,
            parent,
        )

    for parent, child in sorted(cross_slot, key=cross_priority):
        if len(selected[child]) >= 2:
            continue
        edge_profiles = profiles.get(parent, frozenset()) & profiles.get(child, frozenset())
        blocked = False
        for accepted in accepted_cross:
            accepted_profiles = (
                profiles.get(accepted[0], frozenset())
                & profiles.get(accepted[1], frozenset())
            )
            if edge_profiles & accepted_profiles and crosses(
                (parent, child), accepted, rows, slots
            ):
                blocked = True
                break
        if blocked:
            continue
        selected[child].append(parent)
        accepted_cross.append((parent, child))

    return (
        rows,
        logical,
        {key: tuple(value) for key, value in selected.items()},
        display_orders,
    )


def update_mission(
    text: str,
    mission_id: str,
    row: int,
    visual_required: tuple[str, ...],
    logical_required: set[str],
) -> str:
    pattern = re.compile(rf"(?m)^[ \t]+{re.escape(mission_id)}[ \t]*=[ \t]*\{{")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"expected one definition of {mission_id}, found {len(matches)}")
    opening = text.find("{", matches[0].start(), matches[0].end())
    closing = matching_brace(text, opening)
    block = text[matches[0].start() : closing + 1]

    position_pattern = re.compile(r"(?m)^\t\tposition[ \t]*=[ \t]*\d+[ \t]*(?=\r?$)")
    if len(position_pattern.findall(block)) != 1:
        raise ValueError(f"expected one position field in {mission_id}")
    block = position_pattern.sub(f"\t\tposition = {row}", block, count=1)

    required_pattern = re.compile(r"(?m)^\t\trequired_missions[ \t]*=[ \t]*\{")
    required_matches = list(required_pattern.finditer(block))
    if len(required_matches) != 1:
        raise ValueError(f"expected one required_missions field in {mission_id}")
    required_open = block.find("{", required_matches[0].start(), required_matches[0].end())
    required_close = matching_brace(block, required_open)
    dependency_text = " ".join(visual_required)
    replacement = f"\t\trequired_missions = {{ {dependency_text} }}"
    block = block[: required_matches[0].start()] + replacement + block[required_close + 1 :]

    hidden_gates = sorted(logical_required - set(visual_required))
    if hidden_gates:
        trigger_pattern = re.compile(r"(?m)^\t\ttrigger[ \t]*=[ \t]*\{")
        trigger_matches = list(trigger_pattern.finditer(block))
        if len(trigger_matches) != 1:
            raise ValueError(f"expected one trigger block in {mission_id}")
        trigger_open = block.find("{", trigger_matches[0].start(), trigger_matches[0].end())
        trigger_close = matching_brace(block, trigger_open)
        trigger_block = block[trigger_open : trigger_close + 1]
        missing_gates = [
            dependency
            for dependency in hidden_gates
            if not re.search(
                rf"\bmission_completed[ \t]*=[ \t]*{re.escape(dependency)}\b",
                trigger_block,
            )
        ]
        if missing_gates:
            newline = "\r\n" if "\r\n" in block else "\n"
            line_end = block.find("\n", trigger_open)
            gate_lines = "".join(
                f"\t\t\tmission_completed = {dependency}{newline}"
                for dependency in missing_gates
            )
            if line_end == -1 or line_end > trigger_close:
                inline_body = block[trigger_open + 1 : trigger_close].strip()
                body_line = (
                    f"\t\t\t{inline_body}{newline}" if inline_body else ""
                )
                replacement = (
                    "{" + newline + gate_lines + body_line + "\t\t}"
                )
                block = (
                    block[:trigger_open]
                    + replacement
                    + block[trigger_close + 1 :]
                )
            else:
                block = block[: line_end + 1] + gate_lines + block[line_end + 1 :]

    return text[: matches[0].start()] + block + text[closing + 1 :]


def reorder_series_missions(
    text: str,
    series_name: str,
    order: tuple[str, ...],
) -> tuple[str, bool]:
    """Put mission blocks in the same increasing order used by their row plan.

    EU4 preserves declaration order while assembling a mission column.  A
    numerically valid but physically scrambled series therefore renders with
    displaced missions and long connector runs.  Vanilla Japanese mission
    series keep declaration order monotonic, so the generated JXP sources do
    the same.
    """

    series_pattern = re.compile(
        rf"(?m)^{re.escape(series_name)}[ \t]*=[ \t]*\{{"
    )
    series_matches = list(series_pattern.finditer(text))
    if len(series_matches) != 1:
        raise ValueError(
            f"expected one top-level series {series_name}, found {len(series_matches)}"
        )
    series_start = series_matches[0].start()
    series_open = text.find("{", series_start, series_matches[0].end())
    series_close = matching_brace(text, series_open)
    series_block = text[series_start : series_close + 1]

    spans: dict[str, tuple[int, int]] = {}
    for mission_id in order:
        mission_pattern = re.compile(
            rf"(?m)^\t{re.escape(mission_id)}[ \t]*=[ \t]*\{{"
        )
        matches = list(mission_pattern.finditer(series_block))
        if len(matches) != 1:
            raise ValueError(
                f"expected one mission {mission_id} in {series_name}, found {len(matches)}"
            )
        opening = series_block.find("{", matches[0].start(), matches[0].end())
        spans[mission_id] = (matches[0].start(), matching_brace(series_block, opening) + 1)

    source_order = tuple(
        mission_id for mission_id, _span in sorted(spans.items(), key=lambda item: item[1][0])
    )
    if source_order == order:
        return text, False

    ordered_spans = sorted(spans.values())
    for (_left_start, left_end), (right_start, _right_end) in zip(
        ordered_spans,
        ordered_spans[1:],
    ):
        if series_block[left_end:right_start].strip():
            raise ValueError(
                f"refusing to reorder {series_name}; non-whitespace text separates missions"
            )

    first_start = ordered_spans[0][0]
    last_end = ordered_spans[-1][1]
    newline = "\r\n" if "\r\n" in series_block else "\n"
    prefix = series_block[:first_start].rstrip("\r\n")
    suffix = series_block[last_end:].lstrip("\r\n")
    mission_blocks = [series_block[spans[mission_id][0] : spans[mission_id][1]] for mission_id in order]
    rebuilt = prefix + newline * 2 + (newline * 2).join(mission_blocks) + newline + suffix
    return text[:series_start] + rebuilt + text[series_close + 1 :], True


def main() -> int:
    mod_root = Path(__file__).resolve().parents[2]
    mission_files = sorted(
        path
        for path in (mod_root / "missions").glob("*.txt")
        if path.name not in PINNED_OVERRIDE_FILES
        and not path.name.startswith(LEGACY_BOM_FILE_PREFIX)
    )
    context = ValidationContext(mod_root)
    parse_result = CheckResult("reflow")
    series_list = extract_mission_series(context, parse_result, mission_files)
    if parse_result.issues:
        raise ValueError("mission files are not structurally valid before reflow")

    rows, logical, visual, display_orders = build_layout(series_list)
    texts: dict[Path, str] = {}
    broad_preloads_removed = 0
    for path in mission_files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            text = handle.read()
        text, removed = re.subn(
            r"(?m)^\tpotential_on_load[ \t]*=[ \t]*\{[ \t]*always[ \t]*=[ \t]*yes[ \t]*\}[ \t]*\r?\n",
            "",
            text,
        )
        broad_preloads_removed += removed
        texts[path] = text

    definitions: dict[str, Path] = {}
    for mission_id in rows:
        assignment = re.compile(rf"(?m)^[ \t]+{re.escape(mission_id)}[ \t]*=[ \t]*\{{")
        owners = [path for path, text in texts.items() if assignment.search(text)]
        if len(owners) != 1:
            raise ValueError(f"expected one source file for {mission_id}, found {len(owners)}")
        definitions[mission_id] = owners[0]

    for mission_id in sorted(rows, key=lambda item: (str(definitions[item]), rows[item], item)):
        owner = definitions[mission_id]
        texts[owner] = update_mission(
            texts[owner],
            mission_id,
            rows[mission_id],
            visual.get(mission_id, ()),
            logical[mission_id],
        )

    reordered_series = 0
    for series_name, order in sorted(display_orders.items()):
        owners = {definitions[mission_id] for mission_id in order}
        if len(owners) != 1:
            raise ValueError(f"series {series_name} spans multiple source files")
        owner = owners.pop()
        texts[owner], changed = reorder_series_missions(texts[owner], series_name, order)
        reordered_series += int(changed)

    for path, text in texts.items():
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    visible_edges = sum(len(items) for items in visual.values())
    hidden_gates = sum(len(logical[key] - set(visual.get(key, ()))) for key in logical)
    print(
        f"Reflowed {len(rows)} missions across {len(mission_files)} files; "
        f"visible_edges={visible_edges}, hidden_logical_gates={hidden_gates}, "
        f"source_series_reordered={reordered_series}, "
        f"broad_preloads_removed={broad_preloads_removed}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
