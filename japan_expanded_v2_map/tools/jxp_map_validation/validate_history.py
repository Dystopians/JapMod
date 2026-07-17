#!/usr/bin/env python3
"""Validate continuous province/country history for the JXP 88-province map."""

from __future__ import annotations

import argparse
import ast
import csv
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .gameplay_text import read_gameplay_text
except ImportError:  # pragma: no cover - direct script entry point
    from gameplay_text import read_gameplay_text


MOD_ROOT = SCRIPT_DIR.parents[1]
BUILDER_DIR = MOD_ROOT / "tools" / "jxp_map_builder"
IDEA_OBJECT_METADATA = {"start", "bonus", "trigger", "ai_will_do"}
IDEA_SCALAR_METADATA = {"free", "category", "important"}
MINIMUM_SAFE_SHIP_NAMES = 24
TOYOTOMI_START = date(1586, 1, 1)
TOYOTOMI_CORE_TAGS = frozenset({"ODA", "TOY", "TKG"})


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def note(self, message):
        self.notes.append(message)

    def emit(self):
        for message in self.notes:
            print(f"NOTE: {message}")
        for message in self.warnings:
            print(f"WARNING: {message}")
        for message in self.errors:
            print(f"ERROR: {message}")
        print(f"SUMMARY: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--main-mod", type=Path, required=True)
    return parser.parse_args()


def parse_date(value: str) -> date:
    year, month, day = (int(part) for part in value.split("."))
    return date(year, month, day)


def date_text(value: date) -> str:
    return f"{value.year}.{value.month}.{value.day}"


def iter_dated_blocks(text: str):
    for match in re.finditer(r"(?m)^(\d+\.\d+\.\d+)\s*=\s*\{", text):
        cursor = match.end() - 1
        depth = 0
        in_quote = False
        escaped = False
        while cursor < len(text):
            char = text[cursor]
            if escaped:
                escaped = False
            elif char == "\\" and in_quote:
                escaped = True
            elif char == '"':
                in_quote = not in_quote
            elif not in_quote and char == "#":
                newline = text.find("\n", cursor)
                cursor = len(text) if newline < 0 else newline
                continue
            elif not in_quote and char == "{":
                depth += 1
            elif not in_quote and char == "}":
                depth -= 1
                if depth == 0:
                    yield match.group(1), text[match.end():cursor]
                    break
            cursor += 1
        else:
            raise RuntimeError(f"Unclosed dated block {match.group(1)}")


def root_token(text: str, key: str) -> str | None:
    prefix = text.split(next(iter(re.findall(r"(?m)^\d+\.\d+\.\d+\s*=", text)), "__NO_DATE__"), 1)[0]
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\"?([^\s\"#}}]+)", prefix)
    return match.group(1) if match else None


def parse_province_state(text: str, pid: int, report: Report):
    root_owner = root_token(text, "owner")
    root_controller = root_token(text, "controller")
    if not root_owner or not root_controller:
        report.error(f"Province {pid} lacks root owner/controller")
    if root_owner != root_controller:
        report.error(f"Province {pid} root owner {root_owner} != controller {root_controller}")
    changes = []
    for date_value, body in iter_dated_blocks(text):
        owners = re.findall(r"\bowner\s*=\s*([A-Z0-9_]+)", body)
        controllers = re.findall(r"\bcontroller\s*=\s*([A-Z0-9_]+)", body)
        if owners:
            if not controllers:
                report.error(f"Province {pid} changes owner on {date_value} without controller")
            elif owners[-1] != controllers[-1]:
                report.error(f"Province {pid} owner/controller differ on {date_value}")
            changes.append((parse_date(date_value), owners[-1]))
    return root_owner, sorted(changes)


def owner_at(parsed, when: date):
    owner, changes = parsed
    for changed, new_owner in changes:
        if changed <= when:
            owner = new_owner
    return owner


def core_tags_at(text: str, when: date) -> set[str]:
    """Evaluate add_core/remove_core history through one selectable date."""

    first_date = re.search(r"(?m)^\d+\.\d+\.\d+\s*=", text)
    prefix = text[:first_date.start()] if first_date else text
    cores: set[str] = set()

    def apply(fragment: str):
        for action, tag in re.findall(
            r"\b(add_core|remove_core)\s*=\s*([A-Z0-9_]+)", fragment
        ):
            if action == "add_core":
                cores.add(tag)
            else:
                cores.discard(tag)

    apply(prefix)
    blocks = [
        (parse_date(date_value), index, body)
        for index, (date_value, body) in enumerate(iter_dated_blocks(text))
    ]
    for changed, _, body in sorted(blocks):
        if changed <= when:
            apply(body)
    return cores


def core_action_records(text: str) -> list[tuple[date | None, str, str]]:
    first_date = re.search(r"(?m)^\d+\.\d+\.\d+\s*=", text)
    prefix = text[:first_date.start()] if first_date else text
    records = [
        (None, action, tag)
        for action, tag in re.findall(
            r"\b(add_core|remove_core)\s*=\s*([A-Z0-9_]+)", prefix
        )
    ]
    for date_value, body in iter_dated_blocks(text):
        changed = parse_date(date_value)
        records.extend(
            (changed, action, tag)
            for action, tag in re.findall(
                r"\b(add_core|remove_core)\s*=\s*([A-Z0-9_]+)", body
            )
        )
    return records


def invalid_core_removals(text: str) -> list[tuple[date | None, str]]:
    cores: set[str] = set()
    invalid: list[tuple[date | None, str]] = []
    for _, (when, effect, target) in sorted(
        enumerate(core_action_records(text)),
        key=lambda item: (
            item[1][0] or date.min,
            item[0],
        ),
    ):
        if effect == "add_core":
            cores.add(target)
        elif target not in cores:
            invalid.append((when, target))
        else:
            cores.remove(target)
    return invalid


def validate_core_action_safety(
    history_texts: dict[int, str],
    plan: dict,
    history_plan: dict,
    game_root: Path,
    report: Report,
) -> None:
    invalid_generated = []
    invalid_vanilla = []
    inherited_missing = []
    for pid, text in sorted(history_texts.items()):
        invalid_generated.extend((pid, when, tag) for when, tag in invalid_core_removals(text))

    for pid in plan["existing_japan_ids"]:
        source = province_history_file(game_root / "history" / "provinces", int(pid))
        if source is None:
            continue
        source_text = source.read_text(encoding="cp1252")
        invalid_vanilla.extend(
            (int(pid), when, tag) for when, tag in invalid_core_removals(source_text)
        )
        expected = Counter(core_action_records(source_text))
        timeline = history_plan["province_timelines"].get(str(pid))
        if timeline and any(owner == "TOY" for _, owner in timeline.get("changes", [])):
            expected = Counter(
                {
                    record: count
                    for record, count in expected.items()
                    if not (
                        record[0] is not None
                        and record[0] >= TOYOTOMI_START
                        and record[2] in TOYOTOMI_CORE_TAGS
                    )
                }
            )
        actual = Counter(core_action_records(history_texts[int(pid)]))
        for record, count in expected.items():
            if actual[record] < count:
                inherited_missing.append((int(pid), record, count, actual[record]))

    if invalid_vanilla:
        report.error(
            "Pinned vanilla Japan core baseline contains invalid removals: "
            f"{invalid_vanilla[:10]}"
        )
    if invalid_generated:
        report.error(
            "Companion province histories contain invalid remove_core actions: "
            f"{invalid_generated[:20]}"
        )
    if inherited_missing:
        report.error(
            "Companion province histories dropped inherited vanilla core chronology: "
            f"{inherited_missing[:10]}"
        )
    if not invalid_generated and not invalid_vanilla and not inherited_missing:
        report.note(
            f"Validated zero invalid remove_core actions across {len(history_texts)} map histories "
            f"and preserved inherited core chronology for {len(plan['existing_japan_ids'])} provinces"
        )


def validate_toyotomi_core_contract(history_texts, history_plan, report):
    """Prove every planned TOY owner interval has an exclusive Toyotomi core."""

    campaign_start = parse_date(history_plan["campaign_start"])
    campaign_end = parse_date(history_plan["campaign_end_exclusive"])
    checked = 0
    for pid_text, timeline in history_plan["province_timelines"].items():
        pid = int(pid_text)
        if pid not in history_texts:
            continue
        segments = []
        owner = timeline["root"]
        cursor = campaign_start
        for changed_text, new_owner in timeline.get("changes", []):
            changed = parse_date(changed_text)
            segments.append((cursor, changed, owner, new_owner))
            cursor, owner = changed, new_owner
        segments.append((cursor, campaign_end, owner, None))
        for start, end, segment_owner, next_owner in segments:
            if segment_owner != "TOY":
                continue
            checked += 1
            for sample in {start, end - timedelta(days=1)}:
                cores = core_tags_at(history_texts[pid], sample)
                if "TOY" not in cores or "ODA" in cores:
                    report.error(
                        f"Province {pid} has invalid Toyotomi cores on "
                        f"{date_text(sample)}: {sorted(cores)}"
                    )
            if end < campaign_end:
                cores = core_tags_at(history_texts[pid], end)
                if "TOY" in cores:
                    report.error(
                        f"Province {pid} retains TOY core after handoff on {date_text(end)}"
                    )
                if next_owner and next_owner not in cores:
                    report.error(
                        f"Province {pid} lacks {next_owner} core after handoff on "
                        f"{date_text(end)}: {sorted(cores)}"
                    )
    report.note(f"Validated {checked} Toyotomi province/core intervals")


def scan_tags(root: Path) -> set[str]:
    directory = root / "common" / "country_tags"
    tags = set()
    if directory.exists():
        for path in directory.glob("*.txt"):
            tags.update(re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*=", path.read_text(encoding="utf-8", errors="ignore")))
    return tags


def country_history_file(tag: str) -> Path | None:
    matches = sorted((MOD_ROOT / "history" / "countries").glob(f"{tag} - *.txt"))
    return matches[0] if len(matches) == 1 else None


def interval_active(interval, when: date):
    return parse_date(interval[2]) <= when < parse_date(interval[3])


def province_history_file(directory: Path, pid: int) -> Path | None:
    matches = sorted(directory.glob(f"{pid} - *.txt"))
    return matches[0] if len(matches) == 1 else None


def validate_timeline_contract(
    plan: dict,
    history_plan: dict,
    histories: dict,
    game_root: Path,
    report: Report,
):
    new_ids = {int(province["id"]) for province in plan["new_provinces"]}
    planned = {int(pid): value for pid, value in history_plan["province_timelines"].items()}
    missing_new = new_ids - set(planned)
    extra = set(planned) - set(histories)
    if missing_new:
        report.error(f"New provinces lack explicit ownership timelines: {sorted(missing_new)}")
    if extra:
        report.error(f"Ownership plan references unknown provinces: {sorted(extra)}")

    campaign_start = parse_date(history_plan["campaign_start"])
    campaign_end = parse_date(history_plan["campaign_end_exclusive"])
    for pid, actual in histories.items():
        if pid in planned:
            timeline = planned[pid]
            expected_changes = [
                (parse_date(value), owner)
                for value, owner in timeline.get("changes", [])
            ]
            expected = timeline["root"], expected_changes
            if expected_changes != sorted(expected_changes):
                report.error(f"Province {pid} planned ownership dates are not sorted")
            dates = [value for value, _ in expected_changes]
            if len(dates) != len(set(dates)):
                report.error(f"Province {pid} has duplicate planned ownership dates")
            previous = timeline["root"]
            for changed, owner in expected_changes:
                if not campaign_start <= changed < campaign_end:
                    report.error(f"Province {pid} ownership change lies outside campaign: {changed}")
                if owner == previous:
                    report.error(f"Province {pid} has no-op ownership change on {changed}: {owner}")
                previous = owner
        else:
            source = province_history_file(game_root / "history" / "provinces", pid)
            if not source:
                report.error(f"Cannot locate vanilla ownership baseline for province {pid}")
                continue
            expected = parse_province_state(
                source.read_text(encoding="cp1252"), pid, report
            )
        if actual != expected:
            report.error(
                f"Province {pid} generated ownership timeline differs from its "
                f"{'explicit plan' if pid in planned else 'vanilla baseline'}: "
                f"actual={actual}, expected={expected}"
            )


def expected_interval_rows(histories, history_plan):
    campaign_start = parse_date(history_plan["campaign_start"])
    campaign_end = parse_date(history_plan["campaign_end_exclusive"])
    rows = {}
    for pid, parsed in histories.items():
        owner = owner_at(parsed, campaign_start)
        cursor = campaign_start
        intervals = []
        for changed, new_owner in parsed[1]:
            if changed <= campaign_start or changed >= campaign_end:
                continue
            if new_owner == owner:
                continue
            intervals.append((cursor, changed, owner))
            cursor = changed
            owner = new_owner
        intervals.append((cursor, campaign_end, owner))
        rows[pid] = intervals
    return rows


def validate_interval_audit(histories, history_plan, report):
    path = SCRIPT_DIR / "generated" / "ownership_intervals.csv"
    if not path.exists():
        report.error("Generated ownership_intervals.csv is missing")
        return 0
    actual = defaultdict(list)
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            pid = int(row["province_id"])
            actual[pid].append((
                parse_date(row["start_inclusive"]),
                parse_date(row["end_exclusive"]),
                row["owner"],
            ))
    expected = expected_interval_rows(histories, history_plan)
    if dict(actual) != expected:
        mismatches = [
            pid for pid in sorted(set(actual) | set(expected))
            if actual.get(pid) != expected.get(pid)
        ]
        report.error(f"ownership_intervals.csv differs from generated histories: {mismatches}")
    return sum(len(rows) for rows in expected.values())


def validate_every_campaign_day(
    histories: dict,
    history_plan: dict,
    new_tags: set[str],
    capitals: dict[str, int],
    report: Report,
):
    campaign_start = parse_date(history_plan["campaign_start"])
    campaign_end = parse_date(history_plan["campaign_end_exclusive"])
    changes_by_date = defaultdict(list)
    current_owners = {
        pid: owner_at(parsed, campaign_start)
        for pid, parsed in histories.items()
    }
    for pid, parsed in histories.items():
        for changed, owner in parsed[1]:
            if campaign_start < changed < campaign_end:
                changes_by_date[changed].append((pid, owner))

    intervals = history_plan["subject_intervals"]
    subject_starts = defaultdict(list)
    subject_ends = defaultdict(list)
    active_subjects = defaultdict(set)
    for overlord, subject, start_text, end_text in intervals:
        start, end = parse_date(start_text), parse_date(end_text)
        if not campaign_start <= start < end <= campaign_end:
            report.error(
                f"Subject interval lies outside campaign or is empty: "
                f"{overlord}->{subject} {start_text}..{end_text}"
            )
        subject_starts[start].append((subject, overlord))
        subject_ends[end].append((subject, overlord))
        if start <= campaign_start < end:
            active_subjects[subject].add(overlord)

    error_signatures = set()
    presence_open = {}
    presence_segments = defaultdict(list)
    previous_presence = {tag: False for tag in new_tags}
    max_owner_count = 0
    verified_days = 0
    when = campaign_start
    while when < campaign_end:
        if when != campaign_start:
            for pid, owner in changes_by_date.get(when, []):
                current_owners[pid] = owner
            for subject, overlord in subject_ends.get(when, []):
                active_subjects[subject].discard(overlord)
            for subject, overlord in subject_starts.get(when, []):
                active_subjects[subject].add(overlord)

        holdings = defaultdict(list)
        for pid, owner in current_owners.items():
            holdings[owner].append(pid)
        max_owner_count = max(max_owner_count, len(holdings))

        for tag in new_tags:
            owns_land = bool(holdings.get(tag))
            if owns_land and not previous_presence[tag]:
                presence_open[tag] = when
            elif previous_presence[tag] and not owns_land:
                presence_segments[tag].append((presence_open.pop(tag), when))
            previous_presence[tag] = owns_land

            overlords = active_subjects.get(tag, set())
            if owns_land:
                capital = capitals.get(tag)
                if capital not in holdings[tag]:
                    signature = ("capital", tag)
                    if signature not in error_signatures:
                        report.error(
                            f"{date_text(when)}: {tag} owns {holdings[tag]} "
                            f"but not capital {capital}"
                        )
                        error_signatures.add(signature)
                if len(overlords) != 1:
                    signature = ("overlord_count", tag)
                    if signature not in error_signatures:
                        report.error(
                            f"{date_text(when)}: landed {tag} has "
                            f"{len(overlords)} overlords: {sorted(overlords)}"
                        )
                        error_signatures.add(signature)
            elif overlords:
                signature = ("ghost_subject", tag)
                if signature not in error_signatures:
                    report.error(
                        f"{date_text(when)}: extinct {tag} remains subject to "
                        f"{sorted(overlords)}"
                    )
                    error_signatures.add(signature)

        verified_days += 1
        when += timedelta(days=1)

    for tag, was_present in previous_presence.items():
        if was_present:
            presence_segments[tag].append((presence_open[tag], campaign_end))
    country_rows = {country["tag"]: country for country in history_plan["countries"]}
    for tag, country in country_rows.items():
        expected = [(parse_date(country["start"]), parse_date(country["end"]))]
        if presence_segments.get(tag, []) != expected:
            report.error(
                f"{tag} landed-presence intervals are {presence_segments.get(tag, [])}, "
                f"expected {expected}"
            )
    return verified_days, max_owner_count


def brace_balance(path: Path, report: Report):
    text = path.read_text(encoding="cp1252", errors="replace")
    depth = 0
    in_quote = False
    escaped = False
    for char in text:
        if escaped:
            escaped = False
        elif char == "\\" and in_quote:
            escaped = True
        elif char == '"':
            in_quote = not in_quote
        elif not in_quote and char == "{":
            depth += 1
        elif not in_quote and char == "}":
            depth -= 1
            if depth < 0:
                report.error(f"{path} closes more braces than it opens")
                return
    if depth != 0 or in_quote:
        report.error(f"{path} has unbalanced braces/quotes: depth={depth}, in_quote={in_quote}")


def load_main_clausewitz_parser(main_mod: Path, report: Report):
    """Load the main mod's duplicate-preserving parser without importing its package."""

    parser_path = main_mod / "tools" / "jxp_validation" / "clausewitz.py"
    if not parser_path.is_file():
        report.error(f"Main-mod Clausewitz parser is missing: {parser_path}")
        return None

    module_name = f"_jxp_main_clausewitz_{abs(hash(parser_path.resolve()))}"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, parser_path)
    if spec is None or spec.loader is None:
        report.error(f"Could not load main-mod Clausewitz parser: {parser_path}")
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - defensive error reporting
        sys.modules.pop(module_name, None)
        report.error(f"Could not execute main-mod Clausewitz parser {parser_path}: {exc}")
        return None
    return module


def read_main_national_idea_count(main_mod: Path, report: Report) -> int | None:
    """Read the authoritative idea-slot count from the main validation contract."""

    contract_path = main_mod / "tools" / "jxp_validation" / "ideas.py"
    if not contract_path.is_file():
        report.error(f"Main-mod national idea contract is missing: {contract_path}")
        return None
    try:
        tree = ast.parse(
            contract_path.read_text(encoding="utf-8"),
            filename=str(contract_path),
        )
    except (OSError, SyntaxError, UnicodeError) as exc:
        report.error(f"Could not parse main-mod national idea contract {contract_path}: {exc}")
        return None

    values = []
    for node in tree.body:
        value_node = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "NATIONAL_IDEA_COUNT"
            for target in node.targets
        ):
            value_node = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "NATIONAL_IDEA_COUNT"
        ):
            value_node = node.value
        if value_node is not None:
            try:
                values.append(ast.literal_eval(value_node))
            except (ValueError, TypeError):
                values.append(None)

    if len(values) != 1 or type(values[0]) is not int:
        report.error(
            "Main-mod national idea contract must define exactly one integer "
            f"NATIONAL_IDEA_COUNT; found {values}"
        )
        return None
    if values[0] != 7:
        report.error(
            "Main-mod NATIONAL_IDEA_COUNT contract drifted from the EU4 UI limit: "
            f"expected 7, found {values[0]}"
        )
        return None
    return values[0]


def read_builder_ship_name_suffixes(report: Report) -> tuple[str, ...]:
    """Read the generated ship-name suffix contract without importing the builder."""

    builder_path = BUILDER_DIR / "build_countries.py"
    try:
        tree = ast.parse(builder_path.read_text(encoding="utf-8"), filename=str(builder_path))
    except (OSError, SyntaxError, UnicodeError) as exc:
        report.error(f"Could not parse country builder {builder_path}: {exc}")
        return ()

    values: list[object] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "MAP_SHIP_NAME_SUFFIXES"
            for target in node.targets
        ):
            try:
                values.append(ast.literal_eval(node.value))
            except (ValueError, TypeError):
                values.append(None)
    if len(values) != 1 or not isinstance(values[0], tuple):
        report.error(
            "Country builder must define exactly one literal MAP_SHIP_NAME_SUFFIXES tuple"
        )
        return ()
    suffixes = values[0]
    if (
        len(suffixes) < MINIMUM_SAFE_SHIP_NAMES
        or len(suffixes) != len(set(suffixes))
        or any(
            not isinstance(suffix, str)
            or not suffix.isascii()
            or not suffix.isalnum()
            for suffix in suffixes
        )
    ):
        report.error(
            f"MAP_SHIP_NAME_SUFFIXES must contain at least {MINIMUM_SAFE_SHIP_NAMES} "
            "unique non-empty ASCII-alphanumeric suffixes"
        )
        return ()
    return suffixes


def expected_map_ship_names(country: dict, suffixes: tuple[str, ...]) -> tuple[str, ...]:
    stem = re.sub(r"[^A-Za-z0-9]", "", str(country["name"])) or str(country["tag"])
    return tuple(f"{stem}{suffix}Maru" for suffix in suffixes)


def scan_country_ship_names(root: Path) -> set[str]:
    names: set[str] = set()
    country_root = root / "common" / "countries"
    if not country_root.exists():
        return names
    for path in country_root.rglob("*.txt"):
        text = read_gameplay_text(path)
        match = re.search(r"(?ms)^ship_names\s*=\s*\{(.*?)^\}", text)
        if match is not None:
            names.update(re.findall(r'"([^"\r\n]+)"', match.group(1)))
    return names


def validate_global_ship_name_registry(
    generated_names: list[str],
    expected_total: int,
    baseline_names: set[str],
    report: Report,
) -> None:
    generated_folds = [name.casefold() for name in generated_names]
    generated_set = set(generated_folds)
    baseline_folds = {name.casefold() for name in baseline_names}
    collisions = sorted(generated_set & baseline_folds)
    if len(generated_names) != expected_total:
        report.error(
            f"Generated map ship-name registry has {len(generated_names)} entries; "
            f"expected {expected_total}"
        )
    if len(generated_set) != len(generated_names):
        report.error(
            "Generated map ship-name registry is not globally unique: "
            f"{len(generated_names)} entries / {len(generated_set)} case-insensitive distinct"
        )
    if collisions:
        report.error(
            "Generated map ship names collide with the pinned game/main VFS: "
            f"{collisions[:20]}"
        )


def validate_country_ship_names(
    path: Path,
    expected: tuple[str, ...],
    tag: str,
    report: Report,
) -> tuple[str, ...]:
    text = read_gameplay_text(path)
    match = re.search(r"(?ms)^ship_names\s*=\s*\{(.*?)^\}", text)
    if match is None:
        report.error(f"Country {tag} lacks a root ship_names block")
        return ()
    names = tuple(re.findall(r'"([^"\r\n]+)"', match.group(1)))
    residue = re.sub(r'"[^"\r\n]+"', "", match.group(1))
    residue = re.sub(r"(?m)#.*$", "", residue)
    if residue.strip():
        report.error(f"Country {tag} ship_names contains unquoted or malformed entries")
    if names != expected:
        report.error(
            f"Country {tag} ship-name pool is {len(names)} entries and does not "
            f"match the {len(expected)}-entry generated safety contract"
        )
    return names


def parsed_trigger_tags(trigger, parser) -> list[str]:
    """Return tags only when the activation trigger is exactly one direct OR."""

    selectors = [
        entry.value
        for entry in trigger.entries
        if entry.key == "OR"
        and entry.operator == "="
        and isinstance(entry.value, parser.Object)
    ]
    if len(trigger.entries) != 1 or len(selectors) != 1:
        return []
    tag_container = selectors[0]
    if any(
        entry.key != "tag"
        or entry.operator != "="
        or not isinstance(entry.value, parser.Scalar)
        for entry in tag_container.entries
    ):
        return []
    return [
        entry.value.text
        for entry in tag_container.entries
        if entry.key == "tag"
        and entry.operator == "="
        and isinstance(entry.value, parser.Scalar)
    ]


def validate_ideas(
    tags: set[str],
    report: Report,
    main_mod: Path,
    map_mod: Path = MOD_ROOT,
    idea_source_path: Path | None = None,
    consolidated_path: Path | None = None,
):
    stale_runtime = map_mod / "common" / "ideas" / "jxp_map_new_daimyo_ideas.txt"
    if stale_runtime.exists():
        report.error(
            "Companion map must not ship a second runtime idea file; map groups belong "
            "to the main consolidated registry tail"
        )
    path = idea_source_path or (
        main_mod
        / "tools"
        / "jxp_validation"
        / "idea_sources"
        / "jxp_map_daimyo_ideas.txt"
    )
    if not path.is_file():
        report.error("Missing consolidated companion idea source jxp_map_daimyo_ideas.txt")
        return
    expected_idea_count = read_main_national_idea_count(main_mod, report)
    parser = load_main_clausewitz_parser(main_mod, report)
    if parser is None:
        return
    try:
        document = parser.parse_file(path)
    except Exception as exc:
        report.error(f"Could not parse companion national ideas {path}: {exc}")
        return

    expected_groups = {f"{tag}_ideas": tag for tag in tags}
    expected_names = set(expected_groups) | {"jxp_map_new_daimyo_ideas"}
    groups = {}
    for entry in document.root.entries:
        if (
            entry.key in expected_names
            and entry.operator == "="
            and isinstance(entry.value, parser.Object)
        ):
            if entry.key in groups:
                report.error(f"Companion idea group {entry.key} is defined more than once")
            groups[entry.key] = entry
        else:
            label = entry.key if entry.key is not None else "<bare value>"
            report.error(
                f"ideas.top_level_member [{path.name}:{entry.line}]: "
                f"unexpected root member {label!r}"
            )
    missing_groups = sorted(expected_names - set(groups))
    if missing_groups:
        report.error(f"Companion identity idea groups are missing: {missing_groups}")

    mechanical_signatures = {}
    metadata = IDEA_OBJECT_METADATA | IDEA_SCALAR_METADATA
    identity_plan_path = (
        map_mod / "tools" / "jxp_map_builder" / "daimyo_identity_plan.json"
    )
    identity_plan = json.loads(identity_plan_path.read_text(encoding="utf-8"))
    strength_floors = {"A": (15, 4), "B": (13, 2), "C": (12, 1)}
    for group_name, group_entry in groups.items():
        body = group_entry.value
        required_objects = {}
        for required in ("start", "bonus", "trigger"):
            matches = [entry for entry in body.entries if entry.key == required]
            if len(matches) != 1 or not isinstance(matches[0].value, parser.Object):
                report.error(
                    f"{group_name} requires exactly one top-level {required} object; "
                    f"found {len(matches)}"
                )
            else:
                required_objects[required] = matches[0].value
        free_members = [entry for entry in body.entries if entry.key == "free"]
        if (
            len(free_members) != 1
            or free_members[0].operator != "="
            or not isinstance(free_members[0].value, parser.Scalar)
            or free_members[0].value.text != "yes"
        ):
            report.error(f"{group_name} requires exactly one top-level free = yes")

        idea_entries = []
        for entry in body.entries:
            key = entry.key
            if key in metadata:
                expected_type = parser.Object if key in IDEA_OBJECT_METADATA else parser.Scalar
                if entry.operator != "=" or not isinstance(entry.value, expected_type):
                    expected_kind = "object" if key in IDEA_OBJECT_METADATA else "scalar"
                    report.error(
                        f"ideas.member_type [{path.name}:{entry.line}]: "
                        f"{group_name}.{key} must be {expected_kind}"
                    )
                continue
            if key is None or entry.operator != "=" or not isinstance(entry.value, parser.Object):
                report.error(
                    f"ideas.unexpected_member [{path.name}:{entry.line}]: "
                    f"unexpected {group_name} member {key!r}"
                )
                continue
            idea_entries.append(entry)
        idea_keys = [entry.key for entry in idea_entries]
        if expected_idea_count is not None and len(idea_keys) != expected_idea_count:
            report.error(
                f"{group_name} has {len(idea_keys)} ideas, expected exactly "
                f"{expected_idea_count}: {idea_keys}"
            )
        if len(set(idea_keys)) != len(idea_keys):
            report.error(f"{group_name} repeats idea keys: {idea_keys}")

        trigger = required_objects.get("trigger")
        direct_tags = [
            entry.value.text
            for entry in trigger.entries
            if entry.key == "tag" and isinstance(entry.value, parser.Scalar)
        ] if trigger is not None else []
        if group_name == "jxp_map_new_daimyo_ideas":
            always_values = [
                entry.value.text
                for entry in trigger.entries
                if entry.key == "always" and isinstance(entry.value, parser.Scalar)
            ] if trigger is not None else []
            if direct_tags or always_values != ["no"] or (trigger is not None and len(trigger.entries) != 1):
                report.error(
                    "Legacy jxp_map_new_daimyo_ideas must be an exact always = no tombstone"
                )
            continue

        expected_tag = expected_groups[group_name]
        expected_flag = f"jxp_map_origin_{expected_tag.lower()}"
        stage_values = [
            entry.value.text
            for entry in trigger.entries
            if entry.key == "jxp_is_daimyo_stage_trigger"
            and isinstance(entry.value, parser.Scalar)
        ] if trigger is not None else []
        flag_values = [
            entry.value.text
            for entry in trigger.entries
            if entry.key == "has_country_flag"
            and isinstance(entry.value, parser.Scalar)
        ] if trigger is not None else []
        if (
            direct_tags
            or stage_values != ["yes"]
            or flag_values != [expected_flag]
            or trigger is None
            or len(trigger.entries) != 2
        ):
            report.error(
                f"{group_name} must use exact daimyo-stage + {expected_flag} activation; "
                f"found tags={direct_tags}, stage={stage_values}, flags={flag_values}"
            )

        mechanical_blocks = [required_objects.get("start")]
        mechanical_blocks.extend(entry.value for entry in idea_entries)
        mechanical_blocks.append(required_objects.get("bonus"))
        signature = tuple(
            tuple(
                sorted(
                    (member.key, member.value.text)
                    for member in block.entries
                    if member.key is not None and isinstance(member.value, parser.Scalar)
                )
            )
            if block is not None else ()
            for block in mechanical_blocks
        )
        if signature in mechanical_signatures:
            report.error(
                f"{group_name} mechanically clones {mechanical_signatures[signature]}"
            )
        mechanical_signatures[signature] = group_name
        modifier_entries = sum(len(block) for block in signature)
        dual_ideas = sum(len(block) >= 2 for block in signature[1:-1])
        tier = identity_plan["tags"][expected_tag]["tier"]
        min_entries, min_dual = strength_floors[tier]
        if modifier_entries < min_entries or dual_ideas < min_dual:
            report.error(
                f"{group_name} tier {tier} has {modifier_entries} modifier entries / "
                f"{dual_ideas} dual ideas; expected at least {min_entries} / {min_dual}"
            )

    if expected_idea_count is not None:
        registry_path = consolidated_path or (
            main_mod / "common" / "ideas" / "00_country_ideas.txt"
        )
        try:
            consolidated = parser.parse_file(registry_path)
            consolidated_keys = [
                entry.key
                for entry in consolidated.root.entries
                if entry.key is not None
                and entry.operator == "="
                and isinstance(entry.value, parser.Object)
            ]
            expected_tail = [entry.key for entry in document.root.entries]
            if consolidated_keys[-len(expected_tail):] != expected_tail:
                report.error(
                    "Companion idea groups are not the exact tail of the main consolidated registry"
                )
        except Exception as exc:
            report.error(f"Could not verify consolidated companion idea tail: {exc}")
        report.note(
            f"Companion national idea contract: {len(tags)}/{len(tags)} flag-gated groups "
            f"plus one inactive legacy tombstone in the consolidated registry tail; "
            f"every active group uses start + "
            f"{expected_idea_count} ideas + bonus"
        )


def validate_idea_runtime_contract(
    tags: set[str],
    report: Report,
    main_mod: Path,
    map_mod: Path = MOD_ROOT,
):
    """Keep fresh initialization and old-save idea repair mutually safe."""

    parser = load_main_clausewitz_parser(main_mod, report)
    if parser is None:
        return

    def document(path: Path):
        if not path.is_file():
            report.error(f"Missing national-idea runtime contract file: {path}")
            return None
        try:
            return parser.parse_file(path)
        except Exception as exc:
            report.error(f"Could not parse national-idea runtime contract {path}: {exc}")
            return None

    def top_object(doc, key: str):
        if doc is None:
            return None
        matches = [
            entry.value
            for entry in doc.root.entries
            if entry.key == key and isinstance(entry.value, parser.Object)
        ]
        if len(matches) != 1:
            report.error(f"National-idea runtime contract requires one {key}; found {len(matches)}")
            return None
        return matches[0]

    def scalar_values(obj, key: str):
        if obj is None:
            return []
        values = []
        for entry in obj.entries:
            if entry.key == key and isinstance(entry.value, parser.Scalar):
                values.append(entry.value.text)
            if isinstance(entry.value, parser.Object):
                values.extend(scalar_values(entry.value, key))
        return values

    def scalar_lines(obj, key: str, value: str):
        if obj is None:
            return []
        lines = []
        for entry in obj.entries:
            if (
                entry.key == key
                and isinstance(entry.value, parser.Scalar)
                and entry.value.text == value
            ):
                lines.append(entry.line)
            if isinstance(entry.value, parser.Object):
                lines.extend(scalar_lines(entry.value, key, value))
        return lines

    trigger_path = map_mod / "common" / "scripted_triggers" / "jxp_map_triggers.txt"
    trigger_doc = document(trigger_path)
    exact_trigger = top_object(trigger_doc, "jxp_map_has_expected_identity_ideas_trigger")
    exact_pairs = set()
    if exact_trigger is not None:
        or_blocks = [
            entry.value
            for entry in exact_trigger.entries
            if entry.key == "OR" and isinstance(entry.value, parser.Object)
        ]
        if len(or_blocks) != 1:
            report.error("Expected map identity trigger must contain exactly one OR block")
        else:
            for entry in or_blocks[0].entries:
                if entry.key != "AND" or not isinstance(entry.value, parser.Object):
                    report.error(
                        "Expected map identity trigger may contain only AND tag/group pairs"
                    )
                    continue
                pair_tags = scalar_values(entry.value, "tag")
                pair_groups = scalar_values(entry.value, "has_idea_group")
                if len(pair_tags) != 1 or pair_groups != [f"{pair_tags[0]}_ideas"]:
                    report.error(
                        f"Malformed expected map identity pair: tags={pair_tags}, groups={pair_groups}"
                    )
                    continue
                exact_pairs.add((pair_tags[0], pair_groups[0]))
    expected_pairs = {(tag, f"{tag}_ideas") for tag in tags}
    if exact_pairs != expected_pairs:
        report.error(
            "Expected map identity trigger coverage drifted: "
            f"missing={sorted(expected_pairs - exact_pairs)}, "
            f"extra={sorted(exact_pairs - expected_pairs)}"
        )

    any_trigger = top_object(trigger_doc, "jxp_map_has_any_identity_idea_group_trigger")
    actual_any_groups = set(scalar_values(any_trigger, "has_idea_group"))
    expected_any_groups = {group for _, group in expected_pairs} | {
        "jxp_map_new_daimyo_ideas"
    }
    if actual_any_groups != expected_any_groups:
        report.error(
            "Any-map-identity trigger coverage drifted: "
            f"missing={sorted(expected_any_groups - actual_any_groups)}, "
            f"extra={sorted(actual_any_groups - expected_any_groups)}"
        )

    migration_postcondition = top_object(
        trigger_doc, "jxp_map_idea_identity_v014_postcondition_trigger"
    )
    if migration_postcondition is None:
        report.error("Map v0.14 idea migration lacks a transaction postcondition")
    else:
        required_postcondition_values = (
            ("has_custom_ideas", "yes", 1),
            ("jxp_map_is_new_daimyo_tag_trigger", "yes", 2),
            ("jxp_map_has_expected_identity_ideas_trigger", "yes", 1),
            ("has_idea_group", "jxp_map_new_daimyo_ideas", 1),
            ("jxp_uses_route_national_ideas_trigger", "yes", 2),
            ("jxp_has_expected_route_national_ideas_trigger", "yes", 1),
            ("jxp_map_has_any_identity_idea_group_trigger", "yes", 1),
        )
        for key, value, count in required_postcondition_values:
            values = scalar_values(migration_postcondition, key)
            if values.count(value) != count or any(item != value for item in values):
                report.error(
                    "Map v0.14 idea migration postcondition has the wrong "
                    f"{key} contract: {values}"
                )
        if scalar_values(migration_postcondition, "has_country_flag"):
            report.error("Map v0.14 idea migration postcondition must be markerless")

    any_origin_trigger = top_object(trigger_doc, "jxp_map_has_any_origin_trigger")
    actual_origin_flags = scalar_values(any_origin_trigger, "has_country_flag")
    expected_origin_flags = {f"jxp_map_origin_{tag.lower()}" for tag in tags}
    if (
        set(actual_origin_flags) != expected_origin_flags
        or len(actual_origin_flags) != len(expected_origin_flags)
    ):
        report.error(
            "Any-map-origin trigger coverage drifted: "
            f"missing={sorted(expected_origin_flags - set(actual_origin_flags))}, "
            f"extra={sorted(set(actual_origin_flags) - expected_origin_flags)}, "
            f"duplicates={sorted(flag for flag in set(actual_origin_flags) if actual_origin_flags.count(flag) > 1)}"
        )

    effects_path = map_mod / "common" / "scripted_effects" / "jxp_map_effects.txt"
    effects_doc = document(effects_path)
    record_origin = top_object(effects_doc, "jxp_map_record_origin_effect")
    actual_origin_pairs = []
    if record_origin is not None:
        for entry in record_origin.entries:
            if entry.key != "if" or not isinstance(entry.value, parser.Object):
                report.error("Map origin recorder may contain only exact if branches")
                continue
            limits = [
                child.value
                for child in entry.value.entries
                if child.key == "limit" and isinstance(child.value, parser.Object)
            ]
            if len(limits) != 1:
                report.error("Each map origin recorder branch requires exactly one limit")
                continue
            limit = limits[0]
            pair_tags = [
                child.value.text
                for child in limit.entries
                if child.key == "tag" and isinstance(child.value, parser.Scalar)
            ]
            pair_flags = [
                child.value.text
                for child in entry.value.entries
                if child.key == "set_country_flag"
                and isinstance(child.value, parser.Scalar)
            ]
            not_blocks = [
                child.value
                for child in limit.entries
                if child.key == "NOT" and isinstance(child.value, parser.Object)
            ]
            not_entries = not_blocks[0].entries if len(not_blocks) == 1 else []
            guards = [
                child.value.text
                for child in not_entries
                if child.key == "jxp_map_has_any_origin_trigger"
                and isinstance(child.value, parser.Scalar)
            ]
            if (
                len(entry.value.entries) != 2
                or len(limit.entries) != 2
                or len(pair_tags) != 1
                or pair_flags != [f"jxp_map_origin_{pair_tags[0].lower()}"]
                or len(not_blocks) != 1
                or len(not_entries) != 1
                or guards != ["yes"]
            ):
                report.error(
                    "Malformed map origin recorder branch: "
                    f"tags={pair_tags}, flags={pair_flags}, guards={guards}"
                )
                continue
            actual_origin_pairs.append((pair_tags[0], pair_flags[0]))
    expected_origin_pairs = {
        (tag, f"jxp_map_origin_{tag.lower()}") for tag in tags
    }
    actual_origin_pair_set = set(actual_origin_pairs)
    duplicate_origin_pairs = sorted(
        pair for pair, count in Counter(actual_origin_pairs).items() if count > 1
    )
    if (
        actual_origin_pair_set != expected_origin_pairs
        or len(actual_origin_pairs) != len(expected_origin_pairs)
    ):
        report.error(
            "Map origin recorder coverage drifted: "
            f"missing={sorted(expected_origin_pairs - actual_origin_pair_set)}, "
            f"extra={sorted(actual_origin_pair_set - expected_origin_pairs)}, "
            f"duplicates={duplicate_origin_pairs}"
        )

    initialize = top_object(effects_doc, "jxp_map_initialize_effect")
    identity_sync = top_object(effects_doc, "jxp_map_sync_identity_ideas_effect")
    record_lines = scalar_lines(
        initialize, "jxp_map_record_origin_effect", "yes"
    )
    sync_lines = scalar_lines(
        initialize, "jxp_map_sync_identity_ideas_effect", "yes"
    )
    migration_lines = scalar_lines(
        initialize, "jxp_map_migrate_identity_v012_effect", "yes"
    ) + scalar_lines(
        initialize, "jxp_map_migrate_idea_identity_v014_effect", "yes"
    )
    if len(record_lines) != 1 or len(sync_lines) != 1 or len(migration_lines) != 2:
        report.error(
            "Map initialization must record origin once, run one postcondition idea "
            "sync, and then invoke both migrations"
        )
    elif not record_lines[0] < sync_lines[0] < min(migration_lines):
        report.error("Map initialization must record origin before idea sync and migrations")

    if scalar_values(identity_sync, "swap_free_idea_group") != ["yes"]:
        report.error("Map identity sync must contain exactly one guarded free-idea swap")
    for key, value in (
        ("jxp_map_is_new_daimyo_tag_trigger", "yes"),
        ("jxp_is_daimyo_stage_trigger", "yes"),
        ("jxp_map_has_any_origin_trigger", "yes"),
        ("has_custom_ideas", "no"),
        ("jxp_map_has_expected_identity_ideas_trigger", "yes"),
    ):
        if scalar_values(identity_sync, key) != [value]:
            report.error(f"Map identity sync lacks exact guard {key} = {value}")
    if scalar_values(identity_sync, "has_country_flag"):
        report.error("Map identity sync must not be gated by a migration marker")
    if scalar_values(identity_sync, "has_idea_group") != ["jxp_map_new_daimyo_ideas"]:
        report.error(
            "Map identity sync must retry a serialized shared pre-identity idea group"
        )

    legacy_migration = top_object(effects_doc, "jxp_map_migrate_identity_v012_effect")
    current_migration = top_object(
        effects_doc, "jxp_map_migrate_idea_identity_v014_effect"
    )
    if scalar_values(legacy_migration, "swap_free_idea_group"):
        report.error("Legacy map migration must delegate free-idea changes to the canonical sync")
    if scalar_values(legacy_migration, "jxp_map_sync_identity_ideas_effect") != ["yes"]:
        report.error("Legacy map identity migration does not call the canonical idea sync")
    if scalar_values(current_migration, "swap_free_idea_group"):
        report.error("Current map migration must delegate free-idea changes to the canonical sync")
    for key, value in (
        ("jxp_map_sync_identity_ideas_effect", "yes"),
        ("jxp_map_has_any_identity_idea_group_trigger", "yes"),
        ("jxp_force_sync_route_national_ideas_effect", "yes"),
        ("jxp_sync_route_national_ideas_effect", "yes"),
    ):
        if value not in scalar_values(current_migration, key):
            report.error(f"Current map identity migration lacks {key} = {value}")

    marker = "jxp_map_idea_identity_migration_v014"
    postcondition_key = "jxp_map_idea_identity_v014_postcondition_trigger"
    marker_guards = scalar_lines(current_migration, "has_country_flag", marker)
    marker_clears = scalar_lines(current_migration, "clr_country_flag", marker)
    marker_sets = scalar_lines(current_migration, "set_country_flag", marker)
    postcondition_lines = scalar_lines(current_migration, postcondition_key, "yes")
    action_lines = []
    for key in (
        "jxp_map_sync_identity_ideas_effect",
        "jxp_force_sync_route_national_ideas_effect",
        "jxp_sync_route_national_ideas_effect",
    ):
        action_lines.extend(scalar_lines(current_migration, key, "yes"))
    if len(marker_guards) != 1 or len(postcondition_lines) != 2:
        report.error(
            "Map v0.14 idea migration must retry when its marker is present but "
            "the postcondition is false"
        )
    if len(marker_clears) != 1:
        report.error("Map v0.14 idea migration must clear its marker before retrying")
    if len(marker_sets) != 1:
        report.error("Map v0.14 idea migration must set its marker exactly once")
    if (
        len(marker_clears) == 1
        and len(marker_sets) == 1
        and action_lines
        and not marker_clears[0] < min(action_lines) <= max(action_lines) < marker_sets[0]
    ):
        report.error(
            "Map v0.14 idea migration must repair before committing its marker"
        )

    transaction_ifs = [
        entry.value
        for entry in (current_migration.entries if current_migration is not None else [])
        if entry.key == "if" and isinstance(entry.value, parser.Object)
    ]
    commit_branches = []
    if len(transaction_ifs) == 1:
        transaction = transaction_ifs[0]
        for entry in transaction.entries:
            if (
                entry.key == "if"
                and isinstance(entry.value, parser.Object)
                and marker in scalar_values(entry.value, "set_country_flag")
            ):
                commit_branches.append(entry.value)
    if len(commit_branches) != 1:
        report.error(
            "Map v0.14 idea migration must have one postcondition commit branch"
        )
    else:
        limits = [
            entry.value
            for entry in commit_branches[0].entries
            if entry.key == "limit" and isinstance(entry.value, parser.Object)
        ]
        if (
            len(limits) != 1
            or len(limits[0].entries) != 1
            or scalar_values(limits[0], postcondition_key) != ["yes"]
        ):
            report.error(
                "Map v0.14 idea migration may commit its marker only after the "
                "exact postcondition"
            )

    events_path = map_mod / "events" / "jxp_map_events.txt"
    events_text = read_gameplay_text(events_path) if events_path.is_file() else ""
    for required in (
        "id = jxp_map.102",
        "jxp_map_has_any_identity_idea_group_trigger = yes",
        "jxp_force_sync_route_national_ideas_effect = yes",
        "jxp_sync_route_national_ideas_effect = yes",
    ):
        if required not in events_text:
            report.error(f"Post-tag map idea repair lacks exact contract text: {required}")

    on_actions_path = map_mod / "common" / "on_actions" / "jxp_map_on_actions.txt"
    on_actions_text = (
        read_gameplay_text(on_actions_path) if on_actions_path.is_file() else ""
    )
    if "jxp_map_migrate_idea_identity_v014_effect = yes" not in on_actions_text:
        report.error("Map startup does not invoke the 0.14 idea identity migration")

    if not report.errors:
        report.note(
            f"Companion idea runtime contract: {len(tags)} exact tag/group guards, "
            f"{len(tags)} origin fallback pairs, markerless idempotent fresh initialization, "
            "and forced wrong-stack cleanup"
        )


def validate_area_localisation_plan(localisation_plan, source, report):
    area_labels = localisation_plan.get("areas", {})
    if not isinstance(area_labels, dict):
        report.error("Localisation plan areas must be an object")
        return

    duplicate_labels = sorted(
        label
        for label, count in Counter(str(value) for value in area_labels.values()).items()
        if count > 1
    )
    if duplicate_labels:
        report.error(f"Custom area localisation labels are duplicated: {duplicate_labels}")

    # "东海" is already the Chinese display name of east_china_sea_area.
    # This Japanese land area is the historical Tokaido circuit instead.
    if area_labels.get("jxp_tokai_area") != "东海道":
        report.error("jxp_tokai_area must display as 东海道, not the East China Sea label 东海")

    source_values = dict(
        re.findall(r'(?m)^\s*([^\s:#]+):\d+\s+"([^"]*)"\s*$', source)
    )
    for key, expected in sorted(area_labels.items()):
        if source_values.get(key) != expected:
            report.error(
                f"Source localisation for {key} is {source_values.get(key)!r}, "
                f"expected {expected!r} from localisation_plan.json"
            )


def validate_localisation(plan, history_plan, report):
    source_path = MOD_ROOT / "localisation_source" / "jxp_map_l_english_utf8_source.yml"
    active_path = MOD_ROOT / "localisation" / "jxp_map_l_english.yml"
    source = source_path.read_text(encoding="utf-8-sig")
    localisation_plan = json.loads(
        (BUILDER_DIR / "localisation_plan.json").read_text(encoding="utf-8")
    )
    validate_area_localisation_plan(localisation_plan, source, report)
    required = set()
    for province in plan["new_provinces"]:
        required.update({f"PROV{province['id']}", f"PROV_ADJ{province['id']}"})
    for country in history_plan["countries"]:
        required.update({country["tag"], f"{country['tag']}_ADJ"})
    required.update(localisation_plan.get("areas", {}))
    required.update({"jxp_map_new_daimyo_ideas", "jxp_map_new_daimyo_ideas_start", "jxp_map_new_daimyo_ideas_bonus"})
    for key in (
        "jxp_map_castle_network", "jxp_map_land_survey", "jxp_map_kokujin_compacts",
        "jxp_map_market_towns", "jxp_map_coastal_routes", "jxp_map_house_codes", "jxp_map_provincial_identity",
    ):
        required.update({key, f"{key}_desc"})
    for country in history_plan["countries"]:
        tag = country["tag"]
        required.update({f"{tag}_ideas", f"{tag}_ideas_start", f"{tag}_ideas_bonus"})
        for index in range(1, 8):
            key = f"jxp_map_{tag.lower()}_identity_{index}"
            required.update({key, f"{key}_desc"})
    keys = set(re.findall(r"(?m)^\s*([^\s:#]+):\d+\s+", source))
    missing = required - keys
    if missing:
        report.error(f"Source localisation misses {len(missing)} keys: {sorted(missing)}")
    active_bytes = active_path.read_bytes()
    if not active_bytes.startswith(b"\xef\xbb\xbf"):
        report.error("Active localisation lacks UTF-8 BOM")
    active = active_bytes.decode("utf-8-sig")
    if re.search(r"[\u3400-\u9fff]", active):
        report.error("Active localisation contains raw CJK instead of EU4SpecialEscape bytes")


def main():
    args = parse_args()
    report = Report()
    plan = json.loads((BUILDER_DIR / "province_plan.json").read_text(encoding="utf-8"))
    history_plan = json.loads((BUILDER_DIR / "history_plan.json").read_text(encoding="utf-8"))
    expected_ids = sorted(set(plan["existing_japan_ids"]) | {item["id"] for item in plan["new_provinces"]})
    histories = {}
    history_texts = {}
    dev_totals = Counter()
    province_development = {}
    history_dir = MOD_ROOT / "history" / "provinces"
    for pid in expected_ids:
        matches = sorted(history_dir.glob(f"{pid} - *.txt"))
        if len(matches) != 1:
            report.error(f"Province {pid} has {len(matches)} history files")
            continue
        text = matches[0].read_text(encoding="cp1252")
        history_texts[pid] = text
        histories[pid] = parse_province_state(text, pid, report)
        province_development[pid] = {}
        for attribute in ("base_tax", "base_production", "base_manpower"):
            value = root_token(text, attribute)
            if value is None or not value.isdigit() or int(value) < 1:
                report.error(f"Province {pid} has invalid {attribute}: {value}")
            else:
                dev_totals[attribute] += int(value)
                province_development[pid][attribute] = int(value)
    validate_timeline_contract(
        plan, history_plan, histories, args.game_root.resolve(), report
    )
    validate_core_action_safety(
        history_texts,
        plan,
        history_plan,
        args.game_root.resolve(),
        report,
    )
    validate_toyotomi_core_contract(history_texts, history_plan, report)
    expected_dev = Counter({key: int(value) for key, value in plan["target_development"].items()})
    vanilla_dev_total = 0
    for pid in plan["existing_japan_ids"]:
        source = province_history_file(
            args.game_root.resolve() / "history" / "provinces", int(pid)
        )
        if not source:
            report.error(f"Cannot calculate vanilla development baseline for province {pid}")
            continue
        source_text = source.read_text(encoding="cp1252")
        for attribute in ("base_tax", "base_production", "base_manpower"):
            value = root_token(source_text, attribute)
            if value and value.isdigit():
                vanilla_dev_total += int(value)
    if dev_totals != expected_dev:
        report.error(f"Development totals are {dict(dev_totals)}, expected {dict(expected_dev)}")
    else:
        report.note(
            f"Development totals close at {sum(dev_totals.values())}: "
            f"{dict(dev_totals)} "
            f"(+{sum(dev_totals.values()) - vanilla_dev_total} over vanilla)"
        )
    default_minimum = int(history_plan["minimum_total_development"])
    minimum_overrides = {
        int(pid): int(value)
        for pid, value in history_plan.get("minimum_total_development_overrides", {}).items()
    }
    for pid, values in province_development.items():
        total = sum(values.values())
        minimum = minimum_overrides.get(pid, default_minimum)
        if total < minimum:
            report.error(
                f"Province {pid} has {total} development, below planned minimum {minimum}"
            )

    new_tags = {country["tag"] for country in history_plan["countries"]}
    ship_name_suffixes = read_builder_ship_name_suffixes(report)
    generated_ship_names: list[str] = []
    game_tags = scan_tags(args.game_root.resolve())
    main_tags = scan_tags(args.main_mod.resolve())
    mod_tags = scan_tags(MOD_ROOT)
    missing_tags = new_tags - mod_tags
    if missing_tags:
        report.error(f"Missing companion country tags: {sorted(missing_tags)}")
    collisions = new_tags & (game_tags | main_tags)
    if collisions:
        report.error(f"New tags collide with game/main mod: {sorted(collisions)}")
    all_tags = game_tags | main_tags | mod_tags
    for pid, parsed in histories.items():
        owners = {parsed[0]} | {owner for _, owner in parsed[1]}
        unknown = owners - all_tags
        if unknown:
            report.error(f"Province {pid} uses unregistered owner tags: {sorted(unknown)}")

    capitals = {}
    for country in history_plan["countries"]:
        tag = country["tag"]
        path = country_history_file(tag)
        if not path:
            report.error(f"Country {tag} does not have exactly one history file")
            continue
        text = read_gameplay_text(path)
        capital = root_token(text, "capital")
        if capital is None or int(capital) != int(country["capital"]):
            report.error(f"Country {tag} capital is {capital}, expected {country['capital']}")
        expected_origin_flag = f"jxp_map_origin_{tag.lower()}"
        start_flags = [
            flag
            for changed, body in iter_dated_blocks(text)
            if changed == country["start"]
            for flag in re.findall(r"\bset_country_flag\s*=\s*([A-Za-z0-9_]+)", body)
        ]
        if start_flags.count(expected_origin_flag) != 1:
            report.error(
                f"Country {tag} must set {expected_origin_flag} exactly once on "
                f"{country['start']}; found {start_flags}"
            )
        capitals[tag] = int(country["capital"])
        country_definition_matches = list((MOD_ROOT / "common" / "countries").glob(f"JXP {country['name']}.txt"))
        if len(country_definition_matches) != 1:
            report.error(f"Country {tag} definition is missing")
        elif ship_name_suffixes:
            expected_ship_names = expected_map_ship_names(country, ship_name_suffixes)
            generated_ship_names.extend(
                validate_country_ship_names(
                    country_definition_matches[0], expected_ship_names, tag, report
                )
            )
        flag = MOD_ROOT / "gfx" / "flags" / f"{tag}.tga"
        if not flag.exists():
            report.error(f"Country {tag} flag is missing")
        else:
            image = Image.open(flag)
            if image.size != (128, 128) or image.mode != "RGB":
                report.error(f"Country {tag} flag has {image.size}/{image.mode}, expected 128x128 RGB")

    intervals = history_plan["subject_intervals"]
    interval_count = validate_interval_audit(histories, history_plan, report)
    verified_days, max_owner_count = validate_every_campaign_day(
        histories, history_plan, new_tags, capitals, report
    )

    # Confirm the generated diplomacy file contains every planned interval once.
    diplomacy = (MOD_ROOT / "history" / "diplomacy" / "JXP_map_daimyo_relations.txt").read_text(encoding="cp1252")
    for overlord, subject, start, end in intervals:
        pattern = rf"first\s*=\s*{overlord}.*?second\s*=\s*{subject}.*?start_date\s*=\s*{re.escape(start)}.*?end_date\s*=\s*{re.escape(end)}"
        if len(re.findall(pattern, diplomacy, flags=re.S)) != 1:
            report.error(f"Diplomacy interval is missing/duplicated: {overlord}->{subject} {start}..{end}")

    validate_ideas(new_tags, report, args.main_mod.resolve())
    validate_idea_runtime_contract(new_tags, report, args.main_mod.resolve())
    validate_localisation(plan, history_plan, report)
    for directory in (MOD_ROOT / "history", MOD_ROOT / "common"):
        for path in directory.rglob("*.txt"):
            brace_balance(path, report)
    report.note(
        f"Evaluated all {verified_days} selectable campaign days; "
        f"{interval_count} continuous province-owner intervals; "
        f"peak owner count {max_owner_count}"
    )
    report.note(f"Validated {len(new_tags)} new country histories and {len(intervals)} subject intervals")
    if ship_name_suffixes:
        baseline_ship_names = scan_country_ship_names(args.game_root.resolve())
        baseline_ship_names.update(scan_country_ship_names(args.main_mod.resolve()))
        expected_total = len(new_tags) * len(ship_name_suffixes)
        validate_global_ship_name_registry(
            generated_ship_names,
            expected_total,
            baseline_ship_names,
            report,
        )
        report.note(
            f"Validated {len(new_tags)} globally unique country ship-name pools at "
            f"{len(ship_name_suffixes)} safe ASCII entries each"
        )
    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
