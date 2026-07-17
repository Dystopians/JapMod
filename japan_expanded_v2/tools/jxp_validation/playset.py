"""Audit the deployed JXP playset and make critical conflicts order-independent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path, PurePosixPath
import re

from .clausewitz import CP1252_TO_UNICODE
from .core import CheckResult


RUNTIME_ROOTS = {
    "common",
    "decisions",
    "events",
    "gfx",
    "history",
    "interface",
    "localisation",
    "map",
    "missions",
}
REVIEW_ARTIFACTS = (
    "tools/jxp_visualizer/generate_visualizer.py",
    "tools/jxp_visualizer/jxp_visualizer.html",
    "tools/jxp_visualizer/test_generate_visualizer.py",
)
DEVELOPMENT_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "preview",
    "previews",
    "source",
    "sources",
}
DEVELOPMENT_FILE_SUFFIXES = {".cs", ".kra", ".md", ".ps1", ".psd", ".py", ".pyc", ".pyo", ".xcf"}
BOOKMARK_DATES = (
    date(1586, 1, 1),
    date(1598, 5, 23),
    date(1600, 10, 21),
    date(1615, 6, 3),
    date(1615, 6, 4),
)
DATE_BLOCK_RE = re.compile(r"(?m)^[ \t]*(\d+\.\d+\.\d+)\s*=\s*\{")
OWNER_RE = re.compile(r"(?m)^\s*owner\s*=\s*([A-Z0-9_]+)\b")
PATH_RE = re.compile(r'(?m)^\s*path\s*=\s*"([^"]+)"')
CUSTOM_AREA_RE = re.compile(rb"(?m)^\s*(jxp_[A-Za-z0-9_]+_area)\s*=")
AREA_LOCALISATION_RE = re.compile(
    r'(?m)^\s*([^\s:#]+_area):\d+\s+"([^"]*)"\s*(?:#.*)?$'
)
LOCALISATION_HEADER_RE = re.compile(r"(?m)^\s*l_english\s*:\s*$")
SPECIAL_ESCAPE_MARKERS = {0x10, 0x11, 0x12, 0x13}
UNICODE_TO_CP1252 = {value: key for key, value in CP1252_TO_UNICODE.items()}


@dataclass(frozen=True)
class Layer:
    reference: str
    descriptor: Path
    root: Path


def _parse_date(value: str) -> date:
    return date(*(int(part) for part in value.split(".")))


def _block_end(text: str, opening: int) -> int:
    depth = 0
    in_quote = False
    escaped = False
    cursor = opening
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
        elif char == "{" and not in_quote:
            depth += 1
        elif char == "}" and not in_quote:
            depth -= 1
            if depth == 0:
                return cursor + 1
        cursor += 1
    raise ValueError("unclosed Clausewitz block")


def owner_at(payload: bytes, when: date) -> str:
    """Return one province owner from raw EU4 history bytes."""

    # Ownership tokens are ASCII. Latin-1 keeps every byte reversible even
    # when a translation mod stores province display names in another codepage.
    text = payload.decode("latin-1")
    matches = list(DATE_BLOCK_RE.finditer(text))
    prefix = text[: matches[0].start()] if matches else text
    roots = OWNER_RE.findall(prefix)
    if len(roots) != 1:
        raise ValueError(f"expected one root owner, found {roots}")
    owner = roots[0]
    changes: list[tuple[date, int, str]] = []
    for match in matches:
        opening = text.find("{", match.start(), match.end())
        end = _block_end(text, opening)
        values = OWNER_RE.findall(text[match.start() : end])
        if values:
            changes.append((_parse_date(match.group(1)), match.start(), values[-1]))
    for changed, _position, value in sorted(changes):
        if changed <= when:
            owner = value
    return owner


def _runtime_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for top in sorted(RUNTIME_ROOTS):
        directory = root / top
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                relative_path = path.relative_to(root)
                directory_parts = tuple(part.lower() for part in relative_path.parts[:-1])
                if (
                    any(
                        part in DEVELOPMENT_DIRECTORY_NAMES or part.startswith("backup")
                        for part in directory_parts
                    )
                    or relative_path.suffix.lower() in DEVELOPMENT_FILE_SUFFIXES
                ):
                    continue
                relative = relative_path.as_posix()
                files[relative] = path
    return files


def _descriptor_root(descriptor: Path, user_data: Path) -> Path:
    text = descriptor.read_text(encoding="utf-8-sig")
    match = PATH_RE.search(text)
    if match is None:
        raise ValueError(f"descriptor has no ordinary path: {descriptor}")
    raw = match.group(1).replace("/", "\\")
    path = Path(raw)
    if not path.is_absolute():
        path = user_data / path
    return path.resolve()


def enabled_layers(user_data: Path, dlc_load_path: Path | None = None) -> tuple[Layer, ...]:
    """Resolve enabled descriptors in the launcher-recorded order."""

    user_data = user_data.resolve()
    source = (dlc_load_path or user_data / "dlc_load.json").resolve()
    value = json.loads(source.read_text(encoding="utf-8-sig"))
    references = value.get("enabled_mods")
    if not isinstance(references, list) or not all(isinstance(item, str) for item in references):
        raise ValueError(f"invalid enabled_mods in {source}")
    layers: list[Layer] = []
    for reference in references:
        relative = PurePosixPath(reference)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe descriptor reference: {reference}")
        descriptor = user_data.joinpath(*relative.parts)
        if not descriptor.is_file():
            raise ValueError(f"enabled descriptor is missing: {descriptor}")
        root = _descriptor_root(descriptor, user_data)
        if not root.is_dir():
            raise ValueError(f"enabled mod path is missing: {root}")
        layers.append(Layer(reference, descriptor, root))
    return tuple(layers)


def _providers(layers: tuple[Layer, ...], game_root: Path, relative: str) -> tuple[tuple[str, Path], ...]:
    found = tuple(
        (layer.reference, layer.root.joinpath(*PurePosixPath(relative).parts))
        for layer in layers
        if layer.root.joinpath(*PurePosixPath(relative).parts).is_file()
    )
    if found:
        return found
    vanilla = game_root.joinpath(*PurePosixPath(relative).parts)
    return (("<vanilla>", vanilla),)


def _escaped_character_byte(character: str) -> int:
    codepoint = ord(character)
    if codepoint in UNICODE_TO_CP1252:
        return UNICODE_TO_CP1252[codepoint]
    if codepoint <= 0xFF:
        return codepoint
    raise UnicodeError(f"EU4SpecialEscape triplet contains non-byte character U+{codepoint:04X}")


def _decode_localisation_payload(payload: bytes) -> str:
    """Decode ordinary or EU4SpecialEscape localisation into readable text."""

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = payload.decode("cp1252")
    if not any(ord(character) in SPECIAL_ESCAPE_MARKERS for character in text):
        return text

    output: list[str] = []
    index = 0
    while index < len(text):
        marker = ord(text[index])
        if marker not in SPECIAL_ESCAPE_MARKERS:
            output.append(text[index])
            index += 1
            continue
        if index + 2 >= len(text):
            raise UnicodeError("truncated EU4SpecialEscape localisation triplet")
        low = _escaped_character_byte(text[index + 1])
        high = _escaped_character_byte(text[index + 2])
        if marker in {0x11, 0x13}:
            low -= 14
        if marker in {0x12, 0x13}:
            high += 9
        if not 0 <= low <= 0xFF or not 0 <= high <= 0xFF:
            raise UnicodeError("invalid EU4SpecialEscape localisation triplet")
        codepoint = (high << 8) | low
        if 0xE100 < codepoint < 0xEA00:
            codepoint -= 0xE000
        output.append(chr(codepoint))
        index += 3
    return "".join(output)


def _custom_area_keys(map_root: Path) -> set[str]:
    area_path = map_root / "map" / "area.txt"
    if not area_path.is_file():
        return set()
    return {
        match.group(1).decode("ascii")
        for match in CUSTOM_AREA_RE.finditer(area_path.read_bytes())
    }


def _area_localisation_definitions(
    roots: tuple[tuple[str, Path], ...],
) -> tuple[dict[str, dict[str, set[str]]], list[tuple[str, str]], int]:
    definitions: dict[str, dict[str, set[str]]] = {}
    failures: list[tuple[str, str]] = []
    inspected = 0
    seen_roots: set[Path] = set()
    for reference, root in roots:
        resolved = root.resolve()
        if resolved in seen_roots:
            continue
        seen_roots.add(resolved)
        localisation_root = resolved / "localisation"
        if not localisation_root.is_dir():
            continue
        for path in sorted(localisation_root.rglob("*.yml")):
            payload = path.read_bytes()
            if b"_area" not in payload:
                continue
            inspected += 1
            relative = path.relative_to(resolved).as_posix()
            source = f"{reference}:{relative}"
            try:
                text = _decode_localisation_payload(payload)
            except (UnicodeError, ValueError) as exc:
                failures.append((source, str(exc)))
                continue
            if LOCALISATION_HEADER_RE.search(text) is None:
                continue
            for match in AREA_LOCALISATION_RE.finditer(text):
                key = match.group(1)
                label = match.group(2).strip()
                if not label:
                    continue
                definitions.setdefault(key, {}).setdefault(label, set()).add(source)
    return definitions, failures, inspected


def _audit_custom_area_labels(
    result: CheckResult,
    layers: tuple[Layer, ...],
    game_root: Path,
    expected_map_root: Path,
) -> None:
    custom_keys = _custom_area_keys(expected_map_root)
    roots = (("<vanilla>", game_root.resolve()),) + tuple(
        (layer.reference, layer.root) for layer in layers
    )
    definitions, failures, inspected = _area_localisation_definitions(roots)
    for source, message in failures:
        result.add(
            "playset.area_localisation_read",
            f"cannot decode an enabled area localisation provider: {message}",
            source,
        )

    labels_to_keys: dict[str, set[str]] = {}
    for key, labels in definitions.items():
        for label in labels:
            labels_to_keys.setdefault(label, set()).add(key)

    collisions: set[tuple[str, str, str]] = set()
    for custom_key in sorted(custom_keys):
        labels = definitions.get(custom_key)
        if not labels:
            result.add(
                "playset.area_localisation_missing",
                "custom map area has no l_english localisation in the enabled playset",
                custom_key,
            )
            continue
        for label in labels:
            for other_key in labels_to_keys.get(label, set()) - {custom_key}:
                collisions.add((custom_key, label, other_key))
    for custom_key, label, other_key in sorted(collisions):
        result.add(
            "playset.area_localisation_collision",
            f"custom area {custom_key} and {other_key} both render as {label!r}",
            custom_key,
        )

    result.metrics["custom_area_keys"] = len(custom_keys)
    result.metrics["area_localisation_files"] = inspected
    result.metrics["custom_area_label_collisions"] = len(collisions)


def audit_active_playset(
    user_data: Path,
    game_root: Path,
    expected_main_root: Path,
    expected_map_root: Path,
    dlc_load_path: Path | None = None,
) -> CheckResult:
    """Prove deployed bytes and convergent ODA/TOY history for every provider."""

    result = CheckResult("Active JXP order-independent compatibility playset")
    try:
        layers = enabled_layers(user_data, dlc_load_path)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        result.add("playset.read", str(exc), str(dlc_load_path or user_data / "dlc_load.json"))
        return result

    by_reference = {layer.reference: layer for layer in layers}
    main_reference = "mod/japan_expanded_v2.mod"
    map_reference = "mod/japan_expanded_v2_map.mod"
    if main_reference not in by_reference or map_reference not in by_reference:
        result.add(
            "playset.jxp_missing",
            "the active playset must enable both the JXP companion map and main mod",
            str(dlc_load_path or user_data / "dlc_load.json"),
        )
        return result
    main_files = _runtime_files(expected_main_root.resolve())
    map_files = _runtime_files(expected_map_root.resolve())
    expected_files = {**main_files, **map_files}
    collisions = 0
    stale = 0
    divergent = 0
    external_converged = 0
    for reference, files in ((main_reference, main_files), (map_reference, map_files)):
        deployed_root = by_reference[reference].root
        for relative, expected_source in sorted(files.items()):
            deployed = deployed_root.joinpath(*PurePosixPath(relative).parts)
            if not deployed.is_file() or deployed.read_bytes() != expected_source.read_bytes():
                stale += 1
                result.add(
                    "playset.deployed_stale",
                    f"deployed {reference} bytes differ from the repository source",
                    relative,
                )
        deployed_files = _runtime_files(deployed_root)
        for relative in sorted(set(deployed_files) - set(files)):
            stale += 1
            result.add(
                "playset.deployed_orphan",
                f"deployed {reference} contains a runtime file absent from repository source",
                relative,
            )

    current_review_artifacts = 0
    deployed_main_root = by_reference[main_reference].root
    for relative in REVIEW_ARTIFACTS:
        parts = PurePosixPath(relative).parts
        expected = expected_main_root.joinpath(*parts)
        deployed = deployed_main_root.joinpath(*parts)
        if not expected.is_file():
            result.add(
                "playset.review_artifact_source_missing",
                "repository review artifact is missing",
                relative,
            )
        elif not deployed.is_file() or deployed.read_bytes() != expected.read_bytes():
            result.add(
                "playset.review_artifact_stale",
                "deployed visual-review artifact is missing or differs from repository source",
                relative,
            )
        else:
            current_review_artifacts += 1

    for relative in sorted(expected_files):
        providers = _providers(layers, game_root, relative)
        if len(providers) > 1:
            collisions += 1
        external = [
            (reference, path)
            for reference, path in providers
            if reference not in {main_reference, map_reference, "<vanilla>"}
        ]
        if not external:
            continue
        authoritative = map_files.get(relative, main_files.get(relative))
        assert authoritative is not None
        expected_bytes = authoritative.read_bytes()
        mismatches = [reference for reference, path in external if path.read_bytes() != expected_bytes]
        if mismatches:
            divergent += 1
            result.add(
                "playset.conflict_divergence",
                "external provider differs from JXP authoritative bytes; result depends on engine order: "
                f"{mismatches}",
                relative,
            )
        else:
            external_converged += 1

    province_files = {
        relative: path
        for relative, path in map_files.items()
        if relative.startswith("history/provinces/") and relative.endswith(".txt")
    }
    for when in BOOKMARK_DATES:
        possible_oda: list[int] = []
        authoritative_toy: list[int] = []
        for relative, expected_path in sorted(province_files.items()):
            try:
                expected_owner = owner_at(expected_path.read_bytes(), when)
                owners = {
                    owner_at(path.read_bytes(), when)
                    for _provider, path in _providers(layers, game_root, relative)
                }
            except (OSError, UnicodeError, ValueError) as exc:
                result.add("playset.bookmark_read", str(exc), relative)
                continue
            province_id = int(Path(relative).name.split(" ", 1)[0])
            if "ODA" in owners:
                possible_oda.append(province_id)
            if expected_owner == "TOY":
                authoritative_toy.append(province_id)
        if when >= date(1586, 1, 1) and possible_oda:
            result.add(
                "playset.post_handoff_oda_provider",
                "at least one enabled provider can leave ODA landed on "
                f"{when.isoformat()}: {sorted(possible_oda)}",
                "history/provinces",
            )
        result.metrics[f"bookmark_{when.isoformat()}_possible_oda"] = len(possible_oda)
        result.metrics[f"bookmark_{when.isoformat()}_authoritative_toy"] = len(authoritative_toy)

    _audit_custom_area_labels(result, layers, game_root, expected_map_root)

    result.metrics["enabled_layers"] = len(layers)
    result.metrics["runtime_files"] = len(expected_files)
    result.metrics["colliding_runtime_paths"] = collisions
    result.metrics["divergent_external_conflicts"] = divergent
    result.metrics["converged_external_conflicts"] = external_converged
    result.metrics["stale_deployed_files"] = stale
    result.metrics["current_review_artifacts"] = current_review_artifacts
    result.metrics["bookmark_dates"] = len(BOOKMARK_DATES)
    result.summary = (
        f"{len(layers)} layers, {len(expected_files)} runtime files, "
        f"{collisions} collisions, {divergent} divergent external providers, "
        f"{stale} stale deployed files, "
        f"{result.metrics.get('custom_area_label_collisions', 0)} custom area label collisions; "
        f"{len(result.issues)} issue(s)"
    )
    return result
