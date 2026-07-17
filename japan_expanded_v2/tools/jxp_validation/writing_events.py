"""Executable contract for JXP-013 low-frequency event interventions."""

from __future__ import annotations

from pathlib import Path
import re

from .clausewitz import (
    Document,
    Object,
    Scalar,
    entries_named,
    find_assignments,
    find_objects,
    first_object,
    first_scalar,
    walk_entries,
)
from .core import CheckResult, ValidationContext


SOURCE_LOC_FILE = Path(
    "localisation_source/jxp_78_writing_choices_l_english_utf8_source.yml"
)
ACTIVE_LOC_FILE = Path("localisation/jxp_78_writing_choices_l_english.yml")

TARGETS: dict[Path, dict[str, str]] = {
    Path("events/jxp_ikko_events.txt"): {
        "jxp_ikko.2": "jxp_ikko_terauchi_seen",
        "jxp_ikko.3": "jxp_ikko_monto_militia_seen",
        "jxp_ikko.4": "jxp_ikko_ishiyama_seen",
        "jxp_ikko.5": "jxp_ikko_kinri_seen",
        "jxp_ikko.7": "jxp_ikko_commonwealth_seen",
    },
    Path("events/jxp_wokou_events.txt"): {
        "jxp_wokou.2": "jxp_wokou_letters_seen",
        "jxp_wokou.3": "jxp_tsushima_brokers_seen",
        "jxp_wokou.4": "jxp_setouchi_pilots_seen",
        "jxp_wokou.5": "jxp_ryukyu_gate_seen",
        "jxp_wokou.6": "jxp_ming_sea_smugglers_seen",
    },
    Path("events/jxp_route_events.txt"): {
        "jxp_rangaku.1": "jxp_rangaku_bureau_seen",
        "jxp_confucian.1": "jxp_confucian_academy_seen",
    },
    Path("events/jxp_kaikyo_events.txt"): {
        "jxp_kaikyo.2": "jxp_halal_port_law_done",
        "jxp_kaikyo.3": "jxp_hajj_fleet_done",
        "jxp_kaikyo.7": "jxp_kaikyo_qadi_courts_seen",
        "jxp_kaikyo.8": "jxp_kaikyo_south_sea_compact_seen",
    },
    Path("events/jxp_reformed_events.txt"): {
        "jxp_reformed.2": "jxp_reformed_scriptures_done",
        "jxp_reformed.3": "jxp_reformed_covenant_done",
        "jxp_reformed.7": "jxp_reformed_oranda_schools_seen",
        "jxp_reformed.8": "jxp_reformed_elder_ports_seen",
    },
    Path("events/jxp_kirishitan_events.txt"): {
        "jxp_kirishitan.8": "jxp_nagasaki_bishopric_seen",
        "jxp_kirishitan.10": "jxp_kirishitan_oceanic_orders_seen",
    },
}

CORE_IDENTITY_MODIFIERS = {
    "jxp_peasant_commonwealth",
    "jxp_halal_port_law",
    "jxp_reformed_court_covenant",
}
RAW_CJK = re.compile(r"[\u3400-\u9fff]")
LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d+\s+"(.*)"\s*$')
MECHANICAL_PROSE = re.compile(r"[0-9+%§$]")


def _document(
    context: ValidationContext, relative: Path, result: CheckResult
) -> Document | None:
    path = context.mod_root / relative
    if not path.is_file():
        result.add("writing_events.file_missing", "contract file is missing", relative.as_posix())
        return None
    document = context.document(path)
    if document is None:
        result.add(
            "writing_events.parse",
            context.parse_errors.get(path.resolve(), "could not parse contract file"),
            relative.as_posix(),
        )
    return document


def _events(document: Document | None) -> dict[str, Object]:
    found: dict[str, Object] = {}
    if document is None:
        return found
    for entry in document.root.entries:
        if entry.key not in {"country_event", "province_event"} or not isinstance(
            entry.value, Object
        ):
            continue
        event_id = first_scalar(entry.value, "id")
        if event_id:
            found[event_id] = entry.value
    return found


def _options(event: Object | None) -> tuple[Object, ...]:
    if event is None:
        return ()
    return tuple(
        entry.value
        for entry in entries_named(event, "option")
        if isinstance(entry.value, Object)
    )


def _is_slow_visible_event(event: Object) -> bool:
    if first_scalar(event, "hidden") == "yes":
        return False
    timing = first_object(event, "mean_time_to_happen")
    if timing is None:
        return False
    thresholds = (("days", 1440.0), ("months", 48.0), ("years", 4.0))
    for key, floor in thresholds:
        value = first_scalar(timing, key)
        if value is None:
            continue
        try:
            return float(value) >= floor
        except ValueError:
            return False
    return False


def _signature(option: Object, completion_flag: str) -> tuple[tuple[str, str], ...]:
    signature: list[tuple[str, str]] = []
    for path, entry in walk_entries(option):
        if not isinstance(entry.value, Scalar) or entry.key == "name":
            continue
        if entry.key == "set_country_flag" and entry.value.text == completion_flag:
            continue
        signature.append(("/".join(path + ((entry.key or "{}"),)), entry.value.text))
    return tuple(signature)


def _has_real_cost(option: Object) -> bool:
    for _path, entry in walk_entries(option):
        if not isinstance(entry.value, Scalar) or entry.key is None:
            continue
        if entry.key.startswith("jxp_subtract_") and entry.value.text == "yes":
            return True
        if entry.key.startswith("add_"):
            try:
                if float(entry.value.text) < 0:
                    return True
            except ValueError:
                pass
    return False


def _check_modifier_durations(
    option: Object, event_id: str, result: CheckResult, source: Path
) -> None:
    for key in ("add_country_modifier", "add_province_modifier"):
        for _path, entry in find_objects(option, key):
            assert isinstance(entry.value, Object)
            name = first_scalar(entry.value, "name")
            duration = first_scalar(entry.value, "duration")
            if duration is None:
                result.add(
                    "writing_events.modifier_duration",
                    f"{event_id}.b adds {name or '<unnamed>'} without a duration",
                    source.as_posix(),
                )
                continue
            try:
                value = int(duration)
            except ValueError:
                value = 0
            if value == -1 and name not in CORE_IDENTITY_MODIFIERS:
                result.add(
                    "writing_events.permanent_reward",
                    f"{event_id}.b adds non-identity permanent modifier {name}",
                    source.as_posix(),
                )
            elif value == 0 or value < -1:
                result.add(
                    "writing_events.modifier_duration",
                    f"{event_id}.b has invalid modifier duration {duration}",
                    source.as_posix(),
                )


def _localisation_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    # Escaped payloads may contain CP1252 control-code characters that Python's
    # splitlines() treats as separators; EU4 localisation records split only on LF.
    for line in text.split("\n"):
        match = LOC_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def _check_localisation(context: ValidationContext, result: CheckResult) -> int:
    expected = {f"{event_id}.b" for events in TARGETS.values() for event_id in events}
    source_path = context.mod_root / SOURCE_LOC_FILE
    active_path = context.mod_root / ACTIVE_LOC_FILE
    if not source_path.is_file() or not active_path.is_file():
        result.add(
            "writing_events.localisation_missing",
            "source or active choice localisation is missing",
            SOURCE_LOC_FILE.as_posix(),
        )
        return 0
    source = source_path.read_text(encoding="utf-8-sig")
    active_bytes = active_path.read_bytes()
    active = active_bytes.decode("utf-8-sig")
    source_values = _localisation_values(source)
    active_values = _localisation_values(active)
    for label, values, relative in (
        ("source", source_values, SOURCE_LOC_FILE),
        ("active", active_values, ACTIVE_LOC_FILE),
    ):
        missing = sorted(expected - set(values))
        if missing:
            result.add(
                "writing_events.localisation_keys",
                f"{label} localisation misses {missing}",
                relative.as_posix(),
            )
    for key in sorted(expected):
        prose = source_values.get(key, "")
        if not prose or MECHANICAL_PROSE.search(prose):
            result.add(
                "writing_events.prose",
                f"{key} must be narrative prose without numeric/mechanical notation",
                SOURCE_LOC_FILE.as_posix(),
            )
    if not active_bytes.startswith(b"\xef\xbb\xbf") or RAW_CJK.search(active):
        result.add(
            "writing_events.localisation_pipeline",
            "active choice localisation must be BOM-prefixed and EU4SpecialEscape encoded",
            ACTIVE_LOC_FILE.as_posix(),
        )
    return len(expected & set(source_values) & set(active_values))


def check_writing_events(context: ValidationContext) -> CheckResult:
    """Return the JXP-013 low-frequency choice and prose contract."""

    result = CheckResult("Low-frequency event choices and narrative tradeoffs")
    documents: dict[Path, Document | None] = {
        relative: _document(context, relative, result) for relative in TARGETS
    }
    improved = 0
    tradeoffs = 0

    for relative, contracts in TARGETS.items():
        events = _events(documents[relative])
        for event_id, completion_flag in contracts.items():
            event = events.get(event_id)
            options = _options(event)
            names = tuple(first_scalar(option, "name") for option in options)
            if event is None or names != (f"{event_id}.a", f"{event_id}.b"):
                result.add(
                    "writing_events.choice_pair",
                    f"{event_id} must expose exactly the .a/.b intervention pair",
                    relative.as_posix(),
                )
                continue
            improved += 1
            if not _is_slow_visible_event(event):
                result.add(
                    "writing_events.classification",
                    f"{event_id} is no longer a visible low-frequency event",
                    relative.as_posix(),
                )
            for suffix, option in zip(("a", "b"), options, strict=True):
                if not find_assignments(option, "set_country_flag", completion_flag):
                    result.add(
                        "writing_events.completion_flag",
                        f"{event_id}.{suffix} does not close {completion_flag}",
                        relative.as_posix(),
                    )
            if _signature(options[0], completion_flag) == _signature(
                options[1], completion_flag
            ):
                result.add(
                    "writing_events.distinct_outcome",
                    f"{event_id} choices have identical gameplay outcomes",
                    relative.as_posix(),
                )
            if not _has_real_cost(options[1]):
                result.add(
                    "writing_events.tradeoff",
                    f"{event_id}.b lacks a real resource or policy cost",
                    relative.as_posix(),
                )
            else:
                tradeoffs += 1
            _check_modifier_durations(options[1], event_id, result, relative)

    # The target inventory is intentionally the complete set of slow, visible,
    # one-choice events. Hidden dispatchers and short conversion setup events are excluded.
    remaining: list[str] = []
    event_root = context.mod_root / "events"
    for path in sorted(event_root.glob("*.txt")):
        document = context.document(path)
        for event_id, event in _events(document).items():
            if _is_slow_visible_event(event) and len(_options(event)) < 2:
                remaining.append(event_id)
    if remaining:
        result.add(
            "writing_events.remaining_single_choice",
            f"slow visible events still have fewer than two choices: {sorted(remaining)}",
            "events",
        )

    localisation = _check_localisation(context, result)
    total = sum(len(events) for events in TARGETS.values())
    result.metrics.update(
        {
            "target_events": total,
            "improved_events": improved,
            "tradeoff_choices": tradeoffs,
            "localised_choices": localisation,
            "remaining_slow_single_choice": len(remaining),
        }
    )
    result.summary = (
        f"{improved}/{total} low-frequency events expose paired choices; "
        f"{tradeoffs}/{total} alternatives carry real costs; "
        f"{localisation}/{total} narrative labels; {len(remaining)} remaining single-choice"
    )
    result.notes.append(
        "Hidden dispatchers, migrations, cleanup events, and sub-four-year setup pulses are excluded."
    )
    return result
