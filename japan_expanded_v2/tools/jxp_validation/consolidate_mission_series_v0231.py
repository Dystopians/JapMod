#!/usr/bin/env python3
"""Consolidate JXP missions so one active series owns each visible slot."""

from __future__ import annotations

from pathlib import Path
import re
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reflow_missions_v023 import matching_brace


FOUNDATION_STATE = (
    "jxp_mission_route_inherited_realm",
    "jxp_mission_route_province_registers",
    "jxp_mission_route_archipelago_circuit",
    "jxp_mission_route_settle_new_constitution",
    "jxp_mission_route_laws_of_the_new_realm",
    "jxp_mission_route_renewed_japan",
    "jxp_mission_route_muster_rolls",
    "jxp_mission_route_firearm_offices",
)

FOUNDATION_COURT = (
    "jxp_mission_route_two_capitals",
    "jxp_mission_route_rice_and_silver",
    "jxp_mission_route_post_station_ledger",
    "jxp_mission_route_rites_of_the_isles",
    "jxp_mission_route_guard_the_sea_lanes",
)

HOUSE_DIET = (
    "jxp_mission_house_diet_into_realm",
    "jxp_mission_house_law_local_offices",
    "jxp_mission_house_law_state_doctrine",
)

CONFUCIAN_DOMESTIC = (
    "jxp_mission_osaka_rice_ledger",
    "jxp_mission_castle_town_markets",
    "jxp_mission_domain_school_network",
    "jxp_mission_nagasaki_translation_house",
    "jxp_mission_silver_silk_routing",
    "jxp_mission_three_capitals_ledgers",
)


def locate_block(text: str, name: str, indent: str) -> tuple[int, int] | None:
    pattern = re.compile(
        rf"(?m)^{re.escape(indent)}{re.escape(name)}[ \t]*=[ \t]*\{{"
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(f"expected one block named {name}, found {len(matches)}")
    opening = text.find("{", matches[0].start(), matches[0].end())
    closing = matching_brace(text, opening)
    return matches[0].start(), closing + 1


def remove_block(text: str, start: int, end: int) -> tuple[str, str]:
    block = text[start:end]
    remove_end = end
    while remove_end < len(text) and text[remove_end] in "\r\n":
        remove_end += 1
    return text[:start] + text[remove_end:], block


def insert_into_series(text: str, series_name: str, block: str) -> str:
    location = locate_block(text, series_name, "")
    if location is None:
        raise ValueError(f"target series {series_name} is missing")
    _start, end = location
    closing = end - 1
    newline = "\r\n" if "\r\n" in text else "\n"
    insertion = newline + block.rstrip("\r\n") + newline
    return text[:closing] + insertion + text[closing:]


def contains_mission(text: str, mission_id: str) -> bool:
    return locate_block(text, mission_id, "\t") is not None


def move_mission(
    texts: dict[Path, str],
    source: Path,
    target: Path,
    target_series: str,
    mission_id: str,
) -> bool:
    source_text = texts.get(source, "")
    target_text = texts[target]
    source_location = locate_block(source_text, mission_id, "\t") if source.exists() else None
    target_has = contains_mission(target_text, mission_id)
    if source_location is None:
        if target_has:
            return False
        raise ValueError(f"mission {mission_id} is absent from source and target")
    if target_has:
        raise ValueError(f"mission {mission_id} exists in both source and target")
    texts[source], block = remove_block(source_text, *source_location)
    texts[target] = insert_into_series(target_text, target_series, block)
    return True


def main() -> int:
    mod_root = Path(__file__).resolve().parents[2]
    mission_root = (mod_root / "missions").resolve()
    japan = mission_root / "jxp_japan_missions.txt"
    branching = mission_root / "jxp_11_branching_missions.txt"
    foundation = mission_root / "jxp_54_route_foundation_missions.txt"
    house = mission_root / "jxp_36_house_diet_legacy_missions.txt"
    for required in (japan, branching):
        if not required.is_file() or required.parent != mission_root:
            raise ValueError(f"required mission file is missing or outside mod root: {required}")

    paths = (japan, branching, foundation, house)
    texts = {
        path: path.read_text(encoding="utf-8-sig")
        for path in paths
        if path.is_file()
    }
    texts.setdefault(foundation, "")
    texts.setdefault(house, "")
    moved = 0
    for mission_id in FOUNDATION_STATE:
        moved += move_mission(
            texts,
            foundation,
            japan,
            "jxp_japan_state_missions",
            mission_id,
        )
    for mission_id in FOUNDATION_COURT:
        moved += move_mission(
            texts,
            foundation,
            japan,
            "jxp_japan_court_missions",
            mission_id,
        )
    for mission_id in HOUSE_DIET:
        moved += move_mission(
            texts,
            house,
            japan,
            "jxp_japan_court_missions",
            mission_id,
        )
    for mission_id in CONFUCIAN_DOMESTIC:
        moved += move_mission(
            texts,
            branching,
            japan,
            "jxp_japan_confucian_imperial_missions",
            mission_id,
        )

    domestic_group = locate_block(
        texts[branching], "jxp_domestic_institution_missions", ""
    )
    if domestic_group is not None:
        texts[branching], _discarded = remove_block(texts[branching], *domestic_group)

    for path in (japan, branching):
        path.write_text(texts[path], encoding="utf-8", newline="")

    for obsolete in (foundation, house):
        if obsolete.exists():
            remaining = texts[obsolete]
            if re.search(r"(?m)^\t+jxp_mission_[A-Za-z0-9_]+\s*=\s*\{", remaining):
                raise ValueError(f"refusing to remove {obsolete}; mission blocks remain")
            obsolete.unlink()

    print(
        f"Consolidated mission series; moved={moved}, "
        "removed_groups=7, active_series_target=28."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
