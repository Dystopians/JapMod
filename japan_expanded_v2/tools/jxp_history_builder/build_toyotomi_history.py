#!/usr/bin/env python3
"""Build the pinned 1.37.5 Toyotomi succession and war-history overrides.

The generator keeps vanilla history intact outside the Oda-to-Toyotomi succession:

* Oda land still held on 1586.1.1 becomes Toyotomi land and core territory.
* Any later vanilla Oda acquisition becomes a Toyotomi acquisition instead.
* Oda-to-Tokugawa handovers are normalized to 1600.10.21, except Settsu,
  which remains Toyotomi until the fall of Osaka on 1615.6.4.
* Oda subject intervals are split at 1586.1.1, and Tokugawa subjects
  Toyotomi only from 1600.10.21 through 1615.6.4.
* Every post-succession vanilla war names Toyotomi rather than Oda, including
  battle ownership in the Imjin War.
* Korean land remains Korean-owned while dated Japanese occupations use TOY;
  Pyongyang receives its missing occupation and Jeju loses the misplaced
  Namwon occupation.

No game process is started. The game root is a read-only pinned input.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
MANIFEST_PATH = SCRIPT_DIR / "generated_toyotomi_history_manifest.json"
SOURCE_ROOT = SCRIPT_DIR / "source"
GAMEPLAY_ENCODER = (
    MOD_ROOT.parent
    / "skills"
    / "eu4-modding"
    / "scripts"
    / "encode_eu4_special_gameplay.py"
)

GAME_VERSION = "1.37.5.0"
ODA = "ODA"
TOY = "TOY"
TKG = "TKG"
TOYOTOMI_START = date(1586, 1, 1)
SEKIGAHARA = date(1600, 10, 21)
OSAKA_FALL = date(1615, 6, 4)
SETTSU = 1021

# Pinned vanilla japan_region closure for EU4 1.37.5. The companion map
# expands this set, but the standalone main mod must only override vanilla IDs.
PINNED_JAPAN_PROVINCES = (
    1012, 1014, 1015, 1017, 1018, 1019, 1020, 1021, 1023, 1024,
    1025, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1818, 1819,
    1820, 1825, 1830, 1832, 1835, 1837, 1839, 1843, 1847, 1852,
    4131, 4180, 4181, 4182, 4183, 4184, 4185, 4186, 4187, 4188,
    4189, 4190, 4191, 4192, 4193, 4359, 4360, 4651,
)

WAR_OVERRIDE_SPECS = {
    "SubjugationOfKyushu.txt": 2,
    "SubjugationOfKanto.txt": 2,
    "KoreanSevenYearsWar.txt": 11,
    "SekigaharaCampaign.txt": 2,
}

# War and battle names are literal gameplay strings, not localisation keys.
# Keep readable Chinese here, then encode the generated history files through
# the same EU4SpecialEscape pipeline as ruler and dynasty names.
WAR_DISPLAY_NAMES = {
    "SubjugationOfKyushu.txt": {
        "Subjugation of Kyushu": "\u5f81\u670d\u4e5d\u5dde",
    },
    "SubjugationOfKanto.txt": {
        "Subjugation of Kanto": "\u5f81\u670d\u5173\u4e1c",
    },
    "KoreanSevenYearsWar.txt": {
        "Imjin War": "\u58ec\u8fb0\u502d\u4e71",
        "Busan": "\u91dc\u5c71",
        "Ch'ungju": "\u5fe0\u5dde",
        "Okpo": "\u7389\u6d66",
        "Imjin River": "\u4e34\u6d25\u6c5f",
        "Hansan": "\u95f2\u5c71\u5c9b",
        "Pyongyang": "\u5e73\u58e4",
        "Byeokjegwan": "\u78a7\u8e44\u9986",
        "Chilcheollyang": "\u6f06\u5ddd\u6881",
        "Myeongnyang": "\u9e23\u6881",
    },
    "SekigaharaCampaign.txt": {
        "Sekigahara Campaign": "\u5173\u539f\u4e4b\u6218",
    },
}
WAR_DISPLAY_NAME_COUNT = sum(len(names) for names in WAR_DISPLAY_NAMES.values())

# Province controller intervals are half-open: start <= date < end. Ownership
# remains KOR throughout. Empty Jeju is deliberate: vanilla misplaces the
# 1597 Battle of Namwon there even though Namwon belongs to mainland Jeolla.
IMJIN_OCCUPATION_INTERVALS = {
    732: ((date(1592, 7, 18), date(1593, 2, 22)),),
    733: ((date(1592, 6, 9), date(1593, 2, 15)),),
    735: ((date(1592, 6, 11), date(1593, 5, 20)),),
    736: ((date(1592, 5, 26), date(1598, 12, 24)),),
    737: ((date(1597, 9, 26), date(1597, 11, 1)),),
    1013: (
        (date(1592, 6, 6), date(1593, 6, 10)),
        (date(1597, 9, 30), date(1597, 11, 1)),
    ),
    1845: ((date(1592, 7, 19), date(1593, 2, 8)),),
    2741: (),
    2742: ((date(1592, 7, 18), date(1593, 2, 22)),),
    2743: ((date(1592, 7, 18), date(1593, 2, 22)),),
    2744: ((date(1592, 7, 19), date(1593, 2, 8)),),
    2745: ((date(1592, 5, 25), date(1598, 12, 24)),),
    4227: ((date(1592, 5, 26), date(1598, 12, 24)),),
    4228: ((date(1597, 9, 26), date(1597, 11, 1)),),
    4229: (
        (date(1592, 6, 6), date(1593, 6, 10)),
        (date(1597, 9, 30), date(1597, 11, 1)),
    ),
    4230: ((date(1592, 6, 11), date(1593, 5, 20)),),
    4231: ((date(1592, 6, 9), date(1593, 2, 15)),),
    4232: ((date(1592, 7, 19), date(1593, 2, 8)),),
}
JEJU_FALSE_OCCUPATION_DATES = (date(1597, 9, 26), date(1597, 11, 1))

DATE_BLOCK_RE = re.compile(r"(?m)^[ \t]*(\d+\.\d+\.\d+)\s*=\s*\{")
ASSIGNMENT_RE = re.compile(
    r"(?m)\b(?P<key>owner|controller|add_core|remove_core)"
    r"(?P<spacing>\s*=\s*)(?P<value>[A-Z0-9_]+)\b"
)
VASSAL_BLOCK_RE = re.compile(r"(?m)^[ \t]*vassal\s*=\s*\{")


def encode_gameplay_text(text: str) -> bytes:
    spec = importlib.util.spec_from_file_location(
        "_jxp_eu4_special_gameplay", GAMEPLAY_ENCODER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load gameplay-name encoder: {GAMEPLAY_ENCODER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.encode_gameplay_text(text)


def encode_gameplay_source(path: Path) -> bytes:
    return encode_gameplay_text(path.read_bytes().decode("utf-8-sig"))


def normalize_generated_text(text: str) -> str:
    return re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)


@dataclass(frozen=True)
class Block:
    start: int
    end: int
    opening_brace: int
    when: date | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", required=True, type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare generated bytes with the checked-in outputs without writing",
    )
    return parser.parse_args()


def parse_date(value: str) -> date:
    year, month, day = (int(part) for part in value.split("."))
    return date(year, month, day)


def date_text(value: date) -> str:
    return f"{value.year}.{value.month}.{value.day}"


def find_block_end(text: str, opening_brace: int) -> int:
    depth = 0
    in_quote = False
    escaped = False
    cursor = opening_brace
    while cursor < len(text):
        char = text[cursor]
        if escaped:
            escaped = False
        elif char == "\\" and in_quote:
            escaped = True
        elif char == '"':
            in_quote = not in_quote
        elif char == "#" and not in_quote:
            newline = text.find("\n", cursor)
            cursor = len(text) if newline < 0 else newline
            continue
        elif not in_quote and char == "{":
            depth += 1
        elif not in_quote and char == "}":
            depth -= 1
            if depth == 0:
                return cursor + 1
        cursor += 1
    raise RuntimeError("Unclosed Clausewitz block")


def dated_blocks(text: str) -> list[Block]:
    blocks = []
    for match in DATE_BLOCK_RE.finditer(text):
        opening = text.find("{", match.start(), match.end())
        blocks.append(
            Block(match.start(), find_block_end(text, opening), opening, parse_date(match.group(1)))
        )
    return blocks


def vassal_blocks(text: str) -> list[Block]:
    blocks = []
    for match in VASSAL_BLOCK_RE.finditer(text):
        opening = text.find("{", match.start(), match.end())
        blocks.append(Block(match.start(), find_block_end(text, opening), opening))
    return blocks


def assignment_values(text: str, key: str) -> list[str]:
    return [
        match.group("value")
        for match in ASSIGNMENT_RE.finditer(text)
        if match.group("key") == key
    ]


def one_assignment(text: str, key: str) -> str:
    pattern = re.compile(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\s#}}]+)")
    values = pattern.findall(text)
    if len(values) != 1:
        raise RuntimeError(f"Expected one {key} assignment, found {values}")
    return values[0]


def replace_one_assignment(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^(\s*{re.escape(key)}\s*=\s*)[^\s#}}]+")
    updated, count = pattern.subn(rf"\g<1>{value}", text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not replace {key} in diplomacy block")
    return updated


def province_history_path(directory: Path, province_id: int) -> Path:
    matches = sorted(directory.glob(f"{province_id} - *.txt"))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one pinned province history for {province_id}, found {matches}"
        )
    return matches[0]


def owner_timeline(text: str) -> tuple[str, list[tuple[date, str, Block]]]:
    blocks = dated_blocks(text)
    prefix_end = blocks[0].start if blocks else len(text)
    roots = assignment_values(text[:prefix_end], "owner")
    if len(roots) != 1:
        raise RuntimeError(f"Expected one root owner, found {roots}")
    changes = []
    for block in blocks:
        owners = assignment_values(text[block.start:block.end], "owner")
        if owners:
            changes.append((block.when, owners[-1], block))
    changes.sort(key=lambda item: (item[0], item[2].start))
    return roots[0], changes


def owner_at(timeline: tuple[str, list[tuple[date, str, Block]]], when: date) -> str:
    owner, changes = timeline
    for changed, new_owner, _ in changes:
        if changed <= when:
            owner = new_owner
    return owner


def controller_timeline(text: str) -> tuple[str, list[tuple[date, str, Block]]]:
    blocks = dated_blocks(text)
    prefix_end = blocks[0].start if blocks else len(text)
    root_owner = assignment_values(text[:prefix_end], "owner")
    root_controller = assignment_values(text[:prefix_end], "controller")
    if len(root_owner) != 1 or len(root_controller) > 1:
        raise RuntimeError(
            f"Expected one root owner and at most one controller, found {root_owner}/{root_controller}"
        )
    changes = []
    for block in blocks:
        controllers = assignment_values(text[block.start:block.end], "controller")
        if controllers:
            changes.append((block.when, controllers[-1], block))
    changes.sort(key=lambda item: (item[0], item[2].start))
    return (root_controller[0] if root_controller else root_owner[0]), changes


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def core_tags_at(text: str, when: date) -> set[str]:
    blocks = dated_blocks(text)
    prefix_end = blocks[0].start if blocks else len(text)
    cores: set[str] = set()

    def apply(fragment: str) -> None:
        for match in ASSIGNMENT_RE.finditer(fragment):
            key, value = match.group("key"), match.group("value")
            if key == "add_core":
                cores.add(value)
            elif key == "remove_core":
                cores.discard(value)

    apply(text[:prefix_end])
    for block in sorted(blocks, key=lambda item: (item.when, item.start)):
        if block.when <= when:
            apply(text[block.start:block.end])
    return cores


def insert_assignment(block_text: str, key: str, value: str) -> str:
    closing = block_text.rfind("}")
    if closing < 0:
        raise RuntimeError("Cannot add assignment to an unclosed block")
    separator = "" if block_text[:closing].endswith("\n") else "\n"
    return block_text[:closing] + separator + f"\t{key} = {value}\n" + block_text[closing:]


def replace_oda_assignments(block_text: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        value = TOY if match.group("value") == ODA else match.group("value")
        return f"{match.group('key')}{match.group('spacing')}{value}"

    return ASSIGNMENT_RE.sub(replacement, block_text)


def replace_controller(block_text: str, source_tag: str, target_tag: str) -> str:
    pattern = re.compile(
        rf"(?m)\bcontroller(?P<spacing>\s*=\s*){re.escape(source_tag)}\b"
    )
    updated, count = pattern.subn(
        rf"controller\g<spacing>{target_tag}", block_text, count=1
    )
    if count != 1:
        raise RuntimeError(
            f"Expected one controller = {source_tag} assignment in dated block"
        )
    return updated


def strip_dated_blocks(text: str, dates: tuple[date, ...]) -> str:
    targets = set(dates)
    replacements: list[tuple[int, int]] = []
    found: set[date] = set()
    for block in dated_blocks(text):
        if block.when not in targets:
            continue
        line_end = text.find("\n", block.end)
        line_end = len(text) if line_end < 0 else line_end + 1
        trailing = text[block.end:line_end].strip()
        if trailing and not trailing.startswith("#"):
            raise RuntimeError(
                f"Cannot safely remove {date_text(block.when)} with trailing script"
            )
        replacements.append((block.start, line_end))
        found.add(block.when)
    if found != targets:
        raise RuntimeError(
            f"Missing dated blocks while removing false occupation: {targets - found}"
        )
    rendered = text
    for start, end in reversed(replacements):
        rendered = rendered[:start] + rendered[end:]
    return rendered


def replace_block_date(block_text: str, target: date) -> str:
    updated, count = DATE_BLOCK_RE.subn(
        lambda match: match.group(0).replace(match.group(1), date_text(target), 1),
        block_text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not replace dated-block label")
    return updated


def insert_toyotomi_start(text: str) -> str:
    marker = (
        "# JXP: Hideyoshi receives the Toyotomi name and assumes the realm.\n"
        f"{date_text(TOYOTOMI_START)} = {{\n"
        f"\towner = {TOY}\n"
        f"\tcontroller = {TOY}\n"
        f"\tadd_core = {TOY}\n"
        f"\tremove_core = {ODA}\n"
        "}\n\n"
    )
    candidates = [block.start for block in dated_blocks(text) if block.when > TOYOTOMI_START]
    if candidates:
        position = min(candidates)
        return text[:position] + marker + text[position:]
    return text.rstrip() + "\n\n" + marker


def transform_province(province_id: int, source: str) -> str | None:
    original = owner_timeline(source)
    oda_at_start = owner_at(original, TOYOTOMI_START) == ODA
    later_oda_dates = [
        changed
        for changed, new_owner, _ in original[1]
        if changed >= TOYOTOMI_START and new_owner == ODA
    ]
    if not oda_at_start and not later_oda_dates:
        return None

    previous_owner = original[0]
    departure_targets: dict[int, date] = {}
    toyotomi_departures: set[int] = set()
    departure_owners: dict[int, str] = {}
    for changed, new_owner, block in original[1]:
        if changed >= TOYOTOMI_START and previous_owner == ODA and new_owner != ODA:
            toyotomi_departures.add(block.start)
            departure_owners[block.start] = new_owner
            if new_owner == TKG:
                departure_targets[block.start] = OSAKA_FALL if province_id == SETTSU else SEKIGAHARA
        previous_owner = new_owner

    replacements = []
    for block in dated_blocks(source):
        fragment = source[block.start:block.end]
        if block.when >= TOYOTOMI_START:
            fragment = replace_oda_assignments(fragment)
        if block.start in departure_targets:
            fragment = replace_block_date(fragment, departure_targets[block.start])
        if block.start in toyotomi_departures and departure_owners[block.start] == TKG:
            fragment = re.sub(
                r"\bremove_core(?P<spacing>\s*=\s*)TKG\b",
                rf"remove_core\g<spacing>{TOY}",
                fragment,
            )
        if block.start in toyotomi_departures and TOY not in assignment_values(fragment, "remove_core"):
            fragment = insert_assignment(fragment, "remove_core", TOY)
        replacements.append((block.start, block.end, fragment))

    transformed = source
    for start, end, fragment in reversed(replacements):
        transformed = transformed[:start] + fragment + transformed[end:]
    if oda_at_start:
        transformed = insert_toyotomi_start(transformed)
    transformed = "\n".join(line.rstrip() for line in transformed.splitlines()) + "\n"

    generated = owner_timeline(transformed)
    if oda_at_start and owner_at(generated, TOYOTOMI_START) != TOY:
        raise RuntimeError(f"Province {province_id} did not transfer to TOY on 1586.1.1")
    for changed in later_oda_dates:
        if owner_at(generated, changed) != TOY:
            raise RuntimeError(f"Province {province_id} did not rewrite later ODA rule on {changed}")
    if any(changed >= TOYOTOMI_START and owner == ODA for changed, owner, _ in generated[1]):
        raise RuntimeError(f"Province {province_id} retains post-1586 ODA ownership")

    for changed, new_owner, block in original[1]:
        if block.start in toyotomi_departures:
            target = departure_targets.get(block.start, changed)
            before = target - timedelta(days=1)
            if owner_at(generated, before) != TOY or owner_at(generated, target) != new_owner:
                raise RuntimeError(
                    f"Province {province_id} does not close TOY->{new_owner} on {date_text(target)}"
                )
            cores_before = core_tags_at(transformed, before)
            cores_after = core_tags_at(transformed, target)
            if TOY not in cores_before or ODA in cores_before:
                raise RuntimeError(f"Province {province_id} has an invalid Toyotomi core interval")
            if TOY in cores_after or new_owner not in cores_after:
                raise RuntimeError(
                    f"Province {province_id} has an invalid {new_owner} core handoff"
                )
    return transformed


def render_post_succession_war(filename: str, source: str) -> str:
    expected_oda = WAR_OVERRIDE_SPECS.get(filename)
    if expected_oda is None:
        raise RuntimeError(f"Unpinned post-succession war file: {filename}")
    actual_oda = len(re.findall(r"\bODA\b", source))
    if actual_oda != expected_oda:
        raise RuntimeError(
            f"{filename} ODA reference drift: expected {expected_oda}, found {actual_oda}"
        )
    rendered = re.sub(r"\bODA\b", TOY, source)
    if filename == "KoreanSevenYearsWar.txt":
        location_rewrites = {
            'name = "Busan"\n\t\tlocation = 736':
                'name = "Busan"\n\t\tlocation = 2745',
            'name = "Ch\'ungju"\n\t\tlocation = 735':
                'name = "Ch\'ungju"\n\t\tlocation = 4229',
        }
        for old, new in location_rewrites.items():
            if rendered.count(old) != 1:
                raise RuntimeError(
                    f"Pinned Imjin battle-location source drift: {old!r}"
                )
            rendered = rendered.replace(old, new, 1)
    for source_name, display_name in WAR_DISPLAY_NAMES[filename].items():
        source_literal = f'name = "{source_name}"'
        if rendered.count(source_literal) != 1:
            raise RuntimeError(
                f"{filename} display-name source drift: {source_name!r}"
            )
        rendered = rendered.replace(
            source_literal,
            f'name = "{display_name}"',
            1,
        )
    if re.search(r"\bODA\b", rendered):
        raise RuntimeError(f"{filename} retains ODA after the Toyotomi succession")
    return normalize_generated_text(
        "# JXP generated Toyotomi war-history override; source: EU4 1.37.5.0.\n"
        + rendered.rstrip()
        + "\n"
    )


def transform_imjin_province(province_id: int, source: str) -> str:
    if province_id not in IMJIN_OCCUPATION_INTERVALS:
        raise RuntimeError(f"Unpinned Imjin province: {province_id}")
    transformed = source
    if province_id == 2741:
        transformed = strip_dated_blocks(transformed, JEJU_FALSE_OCCUPATION_DATES)
    else:
        replacements: list[tuple[int, int, str]] = []
        starts = {start for start, _end in IMJIN_OCCUPATION_INTERVALS[province_id]}
        found: set[date] = set()
        for block in dated_blocks(transformed):
            if block.when not in starts:
                continue
            fragment = transformed[block.start:block.end]
            controllers = assignment_values(fragment, "controller")
            if province_id == 1845:
                if controllers:
                    raise RuntimeError(
                        "Pinned South Pyongan source unexpectedly already has a controller"
                    )
                opening = fragment.find("{")
                if opening < 0:
                    raise RuntimeError("South Pyongan occupation block has no opening brace")
                fragment = (
                    fragment[: opening + 1]
                    + f" controller = {TOY}"
                    + fragment[opening + 1 :]
                )
            else:
                if controllers != [ODA]:
                    raise RuntimeError(
                        f"Province {province_id} occupation start {date_text(block.when)} "
                        f"has unexpected controllers {controllers}"
                    )
                fragment = replace_controller(fragment, ODA, TOY)
            replacements.append((block.start, block.end, fragment))
            found.add(block.when)
        if found != starts:
            raise RuntimeError(
                f"Province {province_id} lacks occupation starts: {starts - found}"
            )
        for start, end, fragment in reversed(replacements):
            transformed = transformed[:start] + fragment + transformed[end:]

    transformed = (
        "# JXP generated Imjin occupation override; source: EU4 1.37.5.0.\n"
        + "# Korean ownership is preserved; Japanese field control belongs to TOY.\n"
        + transformed.rstrip()
        + "\n"
    )
    owner_history = owner_timeline(transformed)
    controller_history = controller_timeline(transformed)
    boundaries = {date(1592, 5, 24), date(1598, 12, 24)}
    for start, end in IMJIN_OCCUPATION_INTERVALS[province_id]:
        boundaries.update({start - timedelta(days=1), start, end - timedelta(days=1), end})
    for when in sorted(boundaries):
        expected_controller = (
            TOY
            if any(
                start <= when < end
                for start, end in IMJIN_OCCUPATION_INTERVALS[province_id]
            )
            else "KOR"
        )
        actual_owner = owner_at(owner_history, when)
        actual_controller = owner_at(controller_history, when)
        if actual_owner != "KOR":
            raise RuntimeError(
                f"Province {province_id} changes owner to {actual_owner} on {when}"
            )
        if actual_controller != expected_controller:
            raise RuntimeError(
                f"Province {province_id} controller on {when} is {actual_controller}; "
                f"expected {expected_controller}"
            )
    for block in dated_blocks(transformed):
        if block.when >= TOYOTOMI_START and ODA in assignment_values(
            transformed[block.start:block.end], "controller"
        ):
            raise RuntimeError(
                f"Province {province_id} retains post-succession ODA control"
            )
    return transformed


def render_diplomacy(source: str) -> tuple[str, dict[str, int]]:
    replacements: list[tuple[int, int, str]] = []
    split_count = 0
    toyotomi_count = 0
    for block in vassal_blocks(source):
        fragment = source[block.start:block.end]
        first = one_assignment(fragment, "first")
        second = one_assignment(fragment, "second")
        start = parse_date(one_assignment(fragment, "start_date"))
        end = parse_date(one_assignment(fragment, "end_date"))
        replacement = fragment
        if first == ODA and end > TOYOTOMI_START:
            toy_start = max(start, TOYOTOMI_START)
            toy_end = min(end, SEKIGAHARA)
            toy_fragment = replace_one_assignment(fragment, "first", TOY)
            toy_fragment = replace_one_assignment(toy_fragment, "start_date", date_text(toy_start))
            toy_fragment = replace_one_assignment(toy_fragment, "end_date", date_text(toy_end))
            toyotomi_count += 1
            if start < TOYOTOMI_START:
                oda_fragment = replace_one_assignment(fragment, "end_date", date_text(TOYOTOMI_START))
                replacement = (
                    oda_fragment
                    + "\n\n# JXP: subject succeeds from Oda to Toyotomi.\n"
                    + toy_fragment
                )
                split_count += 1
            else:
                replacement = toy_fragment
        elif first == TKG and second == ODA:
            replacement = replace_one_assignment(fragment, "second", TOY)
            replacement = replace_one_assignment(replacement, "start_date", date_text(SEKIGAHARA))
            replacement = replace_one_assignment(replacement, "end_date", date_text(OSAKA_FALL))
        replacements.append((block.start, block.end, replacement))

    rendered = source
    for start, end, replacement in reversed(replacements):
        rendered = rendered[:start] + replacement + rendered[end:]
    rendered = (
        "# JXP generated Toyotomi succession override; source: EU4 1.37.5.0.\n"
        + rendered.rstrip()
        + "\n"
    )

    tkg_toy = []
    for block in vassal_blocks(rendered):
        fragment = rendered[block.start:block.end]
        first = one_assignment(fragment, "first")
        second = one_assignment(fragment, "second")
        start = parse_date(one_assignment(fragment, "start_date"))
        end = parse_date(one_assignment(fragment, "end_date"))
        if first == ODA and end > TOYOTOMI_START:
            raise RuntimeError(f"ODA->{second} remains active after 1586.1.1")
        if first == TOY and not (TOYOTOMI_START <= start < end <= SEKIGAHARA):
            raise RuntimeError(f"Invalid TOY->{second} interval: {start}..{end}")
        if first == TKG and second == ODA:
            raise RuntimeError("TKG->ODA survived the Toyotomi rewrite")
        if first == TKG and second == TOY:
            tkg_toy.append((start, end))
    if tkg_toy != [(SEKIGAHARA, OSAKA_FALL)]:
        raise RuntimeError(f"Expected one bounded TKG->TOY interval, found {tkg_toy}")
    return rendered, {
        "oda_intervals_split": split_count,
        "toyotomi_subject_intervals": toyotomi_count,
    }


def build_outputs(game_root: Path) -> dict[Path, bytes]:
    game_root = game_root.resolve()
    settings = json.loads((game_root / "launcher-settings.json").read_text(encoding="utf-8-sig"))
    raw_version = str(settings.get("rawVersion", "")).removeprefix("v")
    if raw_version != GAME_VERSION:
        raise RuntimeError(
            f"Pinned game version mismatch: {settings.get('rawVersion')} != {GAME_VERSION}"
        )
    if not re.search(r"(?m)^\s*TOY\s*=", (MOD_ROOT / "common/country_tags/jxp_tags.txt").read_text(encoding="utf-8")):
        raise RuntimeError("TOY must be registered before generating historical overrides")

    vanilla_provinces = game_root / "history" / "provinces"
    outputs: dict[Path, bytes] = {}
    province_rows = []
    source_pins: list[dict[str, object]] = []
    for province_id in PINNED_JAPAN_PROVINCES:
        source_path = province_history_path(vanilla_provinces, province_id)
        source = source_path.read_text(encoding="cp1252")
        transformed = transform_province(province_id, source)
        if transformed is None:
            continue
        relative = Path("history/provinces") / source_path.name
        outputs[relative] = transformed.encode("cp1252")
        province_rows.append({"id": province_id, "file": source_path.name})
        source_pins.append(
            {
                "path": source_path.relative_to(game_root).as_posix(),
                "sha256": file_sha256(source_path),
            }
        )

    war_rows = []
    vanilla_wars = game_root / "history" / "wars"
    for filename in WAR_OVERRIDE_SPECS:
        source_path = vanilla_wars / filename
        source = source_path.read_text(encoding="cp1252")
        relative = Path("history/wars") / filename
        outputs[relative] = encode_gameplay_text(
            render_post_succession_war(filename, source)
        )
        war_rows.append(filename)
        source_pins.append(
            {
                "path": source_path.relative_to(game_root).as_posix(),
                "sha256": file_sha256(source_path),
            }
        )

    imjin_province_rows = []
    for province_id, intervals in sorted(IMJIN_OCCUPATION_INTERVALS.items()):
        source_path = province_history_path(vanilla_provinces, province_id)
        source = source_path.read_text(encoding="cp1252")
        relative = Path("history/provinces") / source_path.name
        outputs[relative] = normalize_generated_text(
            transform_imjin_province(province_id, source)
        ).encode("cp1252")
        imjin_province_rows.append(
            {
                "id": province_id,
                "file": source_path.name,
                "intervals": [
                    [date_text(start), date_text(end)] for start, end in intervals
                ],
            }
        )
        source_pins.append(
            {
                "path": source_path.relative_to(game_root).as_posix(),
                "sha256": file_sha256(source_path),
            }
        )

    diplomacy_source = (
        game_root / "history" / "diplomacy" / "Japanese_alliances.txt"
    ).read_text(encoding="cp1252")
    diplomacy, diplomacy_stats = render_diplomacy(diplomacy_source)
    diplomacy_relative = Path("history/diplomacy/Japanese_alliances.txt")
    outputs[diplomacy_relative] = diplomacy.encode("cp1252")
    diplomacy_source_path = game_root / diplomacy_relative
    source_pins.append(
        {
            "path": diplomacy_relative.as_posix(),
            "sha256": file_sha256(diplomacy_source_path),
        }
    )

    gameplay_sources = {
        Path("history/countries/ODA - Oda.txt"): (
            SOURCE_ROOT / "history/countries/ODA - Oda.txt"
        ),
        Path("history/countries/TOY - Toyotomi.txt"): (
            SOURCE_ROOT / "history/countries/TOY - Toyotomi.txt"
        ),
        Path("common/countries/TOY - Toyotomi.txt"): (
            SOURCE_ROOT / "common/countries/TOY - Toyotomi.txt"
        ),
    }
    for relative, source_path in gameplay_sources.items():
        if not source_path.is_file():
            raise RuntimeError(f"Missing readable gameplay-name source: {source_path}")
        outputs[relative] = encode_gameplay_source(source_path)

    oda_source = gameplay_sources[Path("history/countries/ODA - Oda.txt")].read_text(
        encoding="utf-8-sig"
    )
    post_handoff = oda_source.split("1586.1.1 = {", 1)
    if len(post_handoff) != 2 or any(
        duplicate in post_handoff[1] for duplicate in ('name = "秀吉"', 'dynasty = "丰臣"')
    ):
        raise RuntimeError("ODA history retains a duplicate Hideyoshi/Toyotomi identity")

    manifest = {
        "schema_version": 4,
        "game_version": GAME_VERSION,
        "toyotomi_start": date_text(TOYOTOMI_START),
        "sekigahara_handoff": date_text(SEKIGAHARA),
        "osaka_fall": date_text(OSAKA_FALL),
        "settsu_province": SETTSU,
        "province_override_count": len(province_rows),
        "province_overrides": province_rows,
        "war_override_count": len(war_rows),
        "war_overrides": war_rows,
        "war_display_language": "zh-Hans",
        "war_display_name_count": WAR_DISPLAY_NAME_COUNT,
        "war_display_name_encoding": "EU4SpecialEscape-CP1252-no-BOM",
        "imjin_province_override_count": len(imjin_province_rows),
        "imjin_occupation_interval_count": sum(
            len(intervals) for intervals in IMJIN_OCCUPATION_INTERVALS.values()
        ),
        "imjin_province_overrides": imjin_province_rows,
        "imjin_jeju_policy": "KOR owner/controller; no Namwon occupation",
        "diplomacy_override": str(diplomacy_relative).replace("\\", "/"),
        "country_history_overrides": ["ODA", "TOY"],
        "gameplay_name_outputs": [
            str(relative).replace("\\", "/") for relative in gameplay_sources
        ],
        "gameplay_name_encoding": "EU4SpecialEscape-CP1252-no-BOM",
        "pinned_vanilla_source_count": len(source_pins),
        "pinned_vanilla_sources": sorted(source_pins, key=lambda item: str(item["path"])),
        **diplomacy_stats,
    }
    outputs[MANIFEST_PATH.relative_to(MOD_ROOT)] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return outputs


def main() -> int:
    args = parse_args()
    expected = build_outputs(args.game_root)
    mismatches = []
    for relative, payload in sorted(expected.items(), key=lambda item: str(item[0])):
        target = MOD_ROOT / relative
        if args.check:
            if not target.is_file() or target.read_bytes() != payload:
                mismatches.append(str(relative).replace("\\", "/"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)

    if mismatches:
        print("ERROR: generated Toyotomi history is stale:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  {mismatch}", file=sys.stderr)
        return 1
    action = "Verified" if args.check else "Generated"
    manifest = json.loads(expected[MANIFEST_PATH.relative_to(MOD_ROOT)].decode("utf-8"))
    print(
        f"{action} {manifest['province_override_count']} province overrides and "
        f"{manifest['toyotomi_subject_intervals']} Toyotomi subject intervals; "
        f"{manifest['war_override_count']} war and "
        f"{manifest['imjin_province_override_count']} Korean province overrides"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
