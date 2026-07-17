"""Validate post-1586 wars and the Imjin occupation/controller contract."""

from __future__ import annotations

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import re

from .clausewitz import (
    Object,
    Scalar,
    entries_named,
    first_object,
    first_scalar,
    read_clausewitz_text,
)
from .core import CheckResult, ValidationContext


TOYOTOMI_START = date(1586, 1, 1)
IMJIN_START = date(1592, 5, 25)

WAR_ACTIONS: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "SubjugationOfKyushu.txt": {
        "1586.7.1": {"add_attacker": ("TOY",), "add_defender": ("SMZ",)},
        "1587.4.28": {"rem_attacker": ("TOY",), "rem_defender": ("SMZ",)},
    },
    "SubjugationOfKanto.txt": {
        "1590.2.1": {"add_attacker": ("TOY",), "add_defender": ("HJO",)},
        "1590.8.4": {"rem_attacker": ("TOY",), "rem_defender": ("HJO",)},
    },
    "KoreanSevenYearsWar.txt": {
        "1592.5.25": {
            "add_attacker": ("TOY", "SMZ", "MRI", "CSK"),
            "add_defender": ("KOR",),
        },
        "1592.8.1": {"add_defender": ("MNG",)},
        "1598.12.24": {
            "rem_attacker": ("TOY", "SMZ", "MRI", "CSK"),
            "rem_defender": ("KOR", "MNG"),
        },
    },
    "SekigaharaCampaign.txt": {
        "1598.12.25": {
            "add_attacker": ("TKG", "IKE", "HSK", "MAE", "DTE"),
            "add_defender": ("SMZ", "MRI", "TOY", "CSK", "UES"),
        },
        "1600.10.21": {
            "rem_attacker": ("TKG", "IKE", "HSK", "MAE", "DTE"),
            "rem_defender": ("SMZ", "MRI", "TOY", "CSK", "UES"),
        },
    },
}

WAR_GOAL_PROVINCES = {
    "SubjugationOfKyushu.txt": "1012",
    "SubjugationOfKanto.txt": "1028",
    "KoreanSevenYearsWar.txt": "736",
    "SekigaharaCampaign.txt": "1012",
}

WAR_DISPLAY_NAMES = {
    "SubjugationOfKyushu.txt": "\u5f81\u670d\u4e5d\u5dde",
    "SubjugationOfKanto.txt": "\u5f81\u670d\u5173\u4e1c",
    "KoreanSevenYearsWar.txt": "\u58ec\u8fb0\u502d\u4e71",
    "SekigaharaCampaign.txt": "\u5173\u539f\u4e4b\u6218",
}

BATTLE_EXPECTATIONS = {
    "\u91dc\u5c71": ("1592.5.26", "2745", "TOY", "KOR", "yes"),
    "\u5fe0\u5dde": ("1592.6.6", "4229", "TOY", "KOR", "yes"),
    "\u7389\u6d66": ("1592.6.16", "1376", "TOY", "KOR", "no"),
    "\u4e34\u6d25\u6c5f": ("1592.7.7", "735", "TOY", "KOR", "yes"),
    "\u95f2\u5c71\u5c9b": ("1592.8.14", "1376", "TOY", "KOR", "no"),
    "\u5e73\u58e4": ("1593.2.8", "1845", "TOY", "MNG", "no"),
    "\u78a7\u8e44\u9986": ("1593.2.27", "735", "TOY", "MNG", "yes"),
    "\u6f06\u5ddd\u6881": ("1597.8.27", "1376", "TOY", "KOR", "yes"),
    "\u9e23\u6881": ("1597.10.26", "1376", "TOY", "KOR", "no"),
}

OCCUPATION_INTERVALS: dict[int, tuple[tuple[date, date], ...]] = {
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

ACTION_KEYS = ("add_attacker", "add_defender", "rem_attacker", "rem_defender")
DATE_RE = re.compile(r"^\d+\.\d+\.\d+$")
GAMEPLAY_ENCODER = (
    Path(__file__).resolve().parents[3]
    / "skills/eu4-modding/scripts/encode_eu4_special_gameplay.py"
)


def _parse_date(value: str) -> date:
    return date(*(int(part) for part in value.split(".")))


def _values(obj: Object | None, key: str) -> tuple[str, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value.text
        for entry in entries_named(obj, key)
        if isinstance(entry.value, Scalar)
    )


def _last_value(obj: Object, key: str) -> str | None:
    values = _values(obj, key)
    return values[-1] if values else None


def _document(
    context: ValidationContext, relative: str, result: CheckResult
):
    path = context.mod_root / relative
    if not path.is_file():
        result.add("imjin.file_missing", "required dated-history override is missing", relative)
        return None
    document = context.document(path)
    if document is None:
        result.add(
            "imjin.parse",
            context.parse_errors.get(path.resolve(), "could not parse file"),
            relative,
        )
    return document


def _dated_objects(root: Object) -> dict[str, Object]:
    result: dict[str, Object] = {}
    for entry in root.entries:
        if entry.key and DATE_RE.fullmatch(entry.key) and isinstance(entry.value, Object):
            result[entry.key] = entry.value
    return result


def _canonical_gameplay_bytes(text: str) -> bytes:
    spec = importlib.util.spec_from_file_location(
        "_jxp_imjin_gameplay_encoder", GAMEPLAY_ENCODER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load gameplay encoder: {GAMEPLAY_ENCODER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.encode_gameplay_text(text)


def _check_wars(context: ValidationContext, result: CheckResult) -> None:
    documents = {}
    for filename, dates in WAR_ACTIONS.items():
        relative = f"history/wars/{filename}"
        document = _document(context, relative, result)
        if document is None:
            continue
        documents[filename] = document
        path = context.mod_root / relative
        text = read_clausewitz_text(path)
        payload = path.read_bytes()
        try:
            canonical = _canonical_gameplay_bytes(text)
        except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
            result.add(
                "imjin.war_display_encoding_pipeline",
                f"cannot reproduce canonical gameplay encoding: {exc}",
                relative,
            )
        else:
            if payload.startswith(b"\xef\xbb\xbf") or payload != canonical:
                result.add(
                    "imjin.war_display_encoding",
                    "war history with Chinese literal names must use canonical BOM-free EU4SpecialEscape bytes",
                    relative,
                )
        actual_display_name = first_scalar(document.root, "name")
        expected_display_name = WAR_DISPLAY_NAMES[filename]
        if actual_display_name != expected_display_name:
            result.add(
                "imjin.war_display_name",
                f"war name is {actual_display_name!r}; expected {expected_display_name!r}",
                relative,
            )
        if re.search(r"\bODA\b", text):
            result.add(
                "imjin.post_succession_oda",
                "post-1586 war history still names ODA instead of TOY",
                relative,
            )
        goal = first_object(document.root, "war_goal")
        if (
            first_scalar(goal, "type") != "take_claim"
            or first_scalar(goal, "casus_belli") != "cb_conquest"
            or first_scalar(goal, "province") != WAR_GOAL_PROVINCES[filename]
        ):
            result.add(
                "imjin.war_goal",
                "war goal drifted from the pinned 1.37.5 historical contract",
                relative,
            )
        dated = _dated_objects(document.root)
        for when, expected_actions in dates.items():
            block = dated.get(when)
            if block is None:
                result.add(
                    "imjin.war_date_missing",
                    f"required war-history date {when} is missing",
                    relative,
                )
                continue
            actual_actions = {
                key: _values(block, key) for key in ACTION_KEYS if _values(block, key)
            }
            if actual_actions != expected_actions:
                result.add(
                    "imjin.war_sides",
                    f"{when} sides are {actual_actions}; expected {expected_actions}",
                    relative,
                )

    korean = documents.get("KoreanSevenYearsWar.txt")
    if korean is None:
        return
    actual_battles: dict[str, tuple[str, str, str, str, str]] = {}
    for when, block in _dated_objects(korean.root).items():
        for battle_entry in entries_named(block, "battle"):
            if not isinstance(battle_entry.value, Object):
                continue
            battle = battle_entry.value
            name = first_scalar(battle, "name")
            attacker = first_object(battle, "attacker")
            defender = first_object(battle, "defender")
            if name:
                actual_battles[name] = (
                    when,
                    first_scalar(battle, "location") or "",
                    first_scalar(attacker, "country") or "",
                    first_scalar(defender, "country") or "",
                    first_scalar(battle, "result") or "",
                )
    if actual_battles != BATTLE_EXPECTATIONS:
        result.add(
            "imjin.battle_contract",
            f"battle country/location contract drifted: {actual_battles}",
            "history/wars/KoreanSevenYearsWar.txt",
        )
    result.metrics["imjin_battles"] = len(actual_battles)


def _province_timeline(root: Object, key: str, fallback: str | None = None):
    initial = first_scalar(root, key) or fallback
    if initial is None:
        raise ValueError(f"missing root {key}")
    changes: list[tuple[date, str]] = []
    for raw_date, block in _dated_objects(root).items():
        value = _last_value(block, key)
        if value is not None:
            changes.append((_parse_date(raw_date), value))
    return initial, tuple(sorted(changes))


def _state_at(timeline: tuple[str, tuple[tuple[date, str], ...]], when: date) -> str:
    value, changes = timeline
    for changed, replacement in changes:
        if changed <= when:
            value = replacement
    return value


def _province_path(context: ValidationContext, province_id: int) -> Path | None:
    matches = sorted((context.mod_root / "history/provinces").glob(f"{province_id} - *.txt"))
    return matches[0] if len(matches) == 1 else None


def _expected_controller(province_id: int, when: date) -> str:
    return (
        "TOY"
        if any(start <= when < end for start, end in OCCUPATION_INTERVALS[province_id])
        else "KOR"
    )


def _check_provinces(context: ValidationContext, result: CheckResult) -> None:
    timelines: dict[int, tuple[tuple[str, tuple[tuple[date, str], ...]], tuple[str, tuple[tuple[date, str], ...]]]] = {}
    boundary_dates = {date(1592, 5, 24), date(1592, 5, 25), date(1598, 12, 24)}
    for province_id, intervals in OCCUPATION_INTERVALS.items():
        path = _province_path(context, province_id)
        if path is None:
            result.add(
                "imjin.province_file",
                f"province {province_id} must have exactly one override",
                "history/provinces",
            )
            continue
        relative = context.relative(path)
        document = _document(context, relative, result)
        if document is None:
            continue
        try:
            owner = _province_timeline(document.root, "owner")
            controller = _province_timeline(
                document.root, "controller", fallback=owner[0]
            )
        except ValueError as exc:
            result.add("imjin.province_state", str(exc), relative)
            continue
        timelines[province_id] = (owner, controller)
        dated = _dated_objects(document.root)
        for start, end in intervals:
            start_block = dated.get(f"{start.year}.{start.month}.{start.day}")
            end_block = dated.get(f"{end.year}.{end.month}.{end.day}")
            start_controller = (
                _last_value(start_block, "controller") if start_block else None
            )
            end_controller = _last_value(end_block, "controller") if end_block else None
            if start_controller != "TOY":
                result.add(
                    "imjin.occupation_start",
                    f"province {province_id} lacks TOY control on {start}",
                    relative,
                )
            if end_controller != "KOR":
                result.add(
                    "imjin.occupation_end",
                    f"province {province_id} lacks KOR recovery on {end}",
                    relative,
                )
            boundary_dates.update(
                {start - timedelta(days=1), start, end - timedelta(days=1), end}
            )
        if province_id == 2741:
            for wrong_date in ("1597.9.26", "1597.11.1"):
                block = dated.get(wrong_date)
                if block is not None and _last_value(block, "controller") is not None:
                    result.add(
                        "imjin.jeju_occupation",
                        "Jeju must not receive the mainland Battle of Namwon occupation",
                        relative,
                    )
        for when, value in (*owner[1], *controller[1]):
            if when >= TOYOTOMI_START and value == "ODA":
                result.add(
                    "imjin.province_oda",
                    f"province {province_id} restores ODA state on {when}",
                    relative,
                )

    for when in sorted(boundary_dates):
        expected_toy = {
            province_id
            for province_id in OCCUPATION_INTERVALS
            if _expected_controller(province_id, when) == "TOY"
        }
        actual_toy = {
            province_id
            for province_id, (owner, controller) in timelines.items()
            if _state_at(controller, when) == "TOY"
        }
        wrong_owners = {
            province_id: _state_at(owner, when)
            for province_id, (owner, _controller) in timelines.items()
            if _state_at(owner, when) != "KOR"
        }
        if actual_toy != expected_toy:
            result.add(
                "imjin.occupation_snapshot",
                f"{when} TOY-controlled provinces are {sorted(actual_toy)}; expected {sorted(expected_toy)}",
                "history/provinces",
            )
        if wrong_owners:
            result.add(
                "imjin.korean_ownership",
                f"{when} Korean ownership drifted: {wrong_owners}",
                "history/provinces",
            )
    result.metrics["imjin_provinces"] = len(timelines)
    result.metrics["imjin_occupation_intervals"] = sum(
        len(intervals) for intervals in OCCUPATION_INTERVALS.values()
    )
    result.metrics["imjin_occupation_snapshots"] = len(boundary_dates)


def _check_participant_subjects(context: ValidationContext, result: CheckResult) -> None:
    relative = "history/diplomacy/Japanese_alliances.txt"
    document = _document(context, relative, result)
    if document is None:
        return
    active_subjects: set[str] = set()
    for entry in entries_named(document.root, "vassal"):
        if not isinstance(entry.value, Object):
            continue
        block = entry.value
        first = first_scalar(block, "first")
        second = first_scalar(block, "second")
        start = first_scalar(block, "start_date")
        end = first_scalar(block, "end_date")
        if not all((first, second, start, end)):
            continue
        start_date = _parse_date(start)
        end_date = _parse_date(end)
        if first == "ODA" and end_date > TOYOTOMI_START:
            result.add(
                "imjin.oda_subject",
                f"ODA remains overlord of {second} after the Toyotomi succession",
                relative,
            )
        if first == "TOY" and start_date <= IMJIN_START < end_date:
            active_subjects.add(second)
    required = {"SMZ", "MRI", "CSK"}
    if not required <= active_subjects:
        result.add(
            "imjin.participant_subject",
            f"Imjin co-belligerents are not all TOY subjects on 1592.5.25: {sorted(active_subjects)}",
            relative,
        )
    result.metrics["imjin_toyotomi_subjects"] = len(active_subjects)


def check_imjin_history(context: ValidationContext) -> CheckResult:
    """Return the complete post-succession war and Korean occupation audit."""

    result = CheckResult("Toyotomi wars and Imjin occupation history")
    _check_wars(context, result)
    _check_provinces(context, result)
    _check_participant_subjects(context, result)
    result.metrics["post_succession_wars"] = len(WAR_ACTIONS)
    result.summary = (
        f"{result.metrics.get('post_succession_wars', 0)} wars, "
        f"{result.metrics.get('imjin_battles', 0)} battles, "
        f"{result.metrics.get('imjin_provinces', 0)} Korean provinces, "
        f"{result.metrics.get('imjin_occupation_intervals', 0)} occupation intervals; "
        f"{len(result.issues)} issue(s)"
    )
    return result
