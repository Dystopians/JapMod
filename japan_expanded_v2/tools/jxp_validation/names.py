"""Audit Chinese display names across the maintained JXP release surface.

The game does not localise literal ruler and leader names.  This audit therefore
checks the actual Clausewitz literals, the companion generator source that owns
its generated countries, and the source/active EU4SpecialEscape localisation
pairs.  Romanised identifiers used only for tags, filenames, and script keys
remain valid and are deliberately outside the display-name contract.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType

try:
    from .clausewitz import (
        ClausewitzParseError,
        Object,
        Scalar,
        bare_scalars,
        entries_named,
        parse_file,
        walk_entries,
    )
except ImportError:  # pragma: no cover - direct-script entry point
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from jxp_validation.clausewitz import (
        ClausewitzParseError,
        Object,
        Scalar,
        bare_scalars,
        entries_named,
        parse_file,
        walk_entries,
    )

try:
    from .core import CheckResult, ValidationContext
except ImportError:  # pragma: no cover - direct-script entry point
    from jxp_validation.core import CheckResult, ValidationContext


LATIN_RE = re.compile(r"[A-Za-z\u00c0-\u024f]")
POOL_NUMBER_RE = re.compile(r"\s+#\d+\s*$")
PERSON_OBJECT_RE = re.compile(
    r"^(?:(?:create|define)_)?"
    r"(?:monarch|ruler|heir|consort|queen|leader|general|admiral|"
    r"explorer|conquistador|advisor)$",
    re.IGNORECASE,
)
LOCALISATION_LINE_RE = re.compile(r'^\s*[^\s:#]+:\d+\s+"(.*)"\s*$')

NON_JAPANESE_LITERAL_NAMES = frozenset(
    {
        "Dom Justo",
        "Gracia",
        "Harun",
        "Hidayat",
        "Ibrahim",
        "Joosten",
        "Maria",
        "Musa",
        "Suleiman",
        "Umar",
        "Yusuf",
    }
)

# These legacy spellings are prohibited in localisation values as well as in
# literal person-name contexts.  TOY is included before its separate history
# slice lands so that it cannot reintroduce romanised Toyotomi rulers.
LEGACY_JAPANESE_ROMAJI = frozenset(
    {
        "Abe", "Akai", "Anekoji", "Arai", "Arima", "Ashina", "Aya",
        "Azai", "Daihoji", "Date", "Dosan", "Fujiwara", "Hachisuka",
        "Harunobu", "Hasekura", "Hatakeyama", "Hattori", "Hayashi", "Hidetsugu",
        "Hideyori", "Hideyoshi", "Hidetada", "Hikohito", "Hirado",
        "Honganji", "Honda", "Honma", "Hosokawa", "Iemasa", "Iemitsu",
        "Ieyasu", "Ii", "Innoshima", "Ishiyama", "Ito", "Junnyo",
        "Kaga", "Kanehisa", "Katsushige", "Kazuhito", "Kazutoyo",
        "Kennyo", "Kimotsuki", "Kitabatake", "Kondo", "Konishi", "Konoe",
        "Kosa", "Kosa-no-Mikado", "Kujo", "Kunekiyo", "Kurushima",
        "Kuroda", "Kyogoku", "Masanobu", "Masachika", "Matsudaira",
        "Matsumae", "Matsuura", "Mihito", "Minamoto", "Miyoshi",
        "Mochikiyo", "Mochiuji", "Mochizumi", "Mogami", "Morinobu",
        "Moritane", "Mori", "Motohiro", "Motohito", "Muneharu",
        "Murakami", "Nabeshima", "Nagamasa", "Nagashige", "Nagatsugu",
        "Nagasaki", "Nagayoshi", "Naito", "Naoie", "Negoro", "Nobuhide",
        "Nobunaga", "Nobutada", "Norimochi", "Noshima", "Oda", "Ogyu",
        "Okiko", "Okubo", "Omura", "Osaki", "Otomo", "Razansai",
        "Rennyo", "Rokkaku", "Ryu", "Ryukyu", "Ryuzoji", "Sadayori",
        "Sadashi", "Saika", "Saionji", "Saito", "Sakai", "Sakakibara",
        "Sagara", "Sanjo", "Satomi", "Seika", "Shimozuma", "Shimotsuma",
        "Shimazu", "Shonyo", "So", "Soma", "Soya", "Sukemasa",
        "Sumitada", "Suzuki", "Tadayoshi", "Taira", "Takamasa",
        "Takamichi", "Takanobu", "Takayama", "Takeda", "Takeyoshi",
        "Tamenobu", "Tachibana", "Togashi", "Tokisue", "Tokugawa",
        "Toku", "Tomohito", "Tomoko", "Torii", "Toshiko", "Toyotomi", "Tsugaru",
        "Tsunenaga", "Tsushima", "Ukita", "Watanabe", "Yamaga",
        "Yamato", "Yamauchi", "Yasuhito", "Yorinaga", "Yoshiharu",
        "Yoshihiro", "Yoshihisa", "Yoshimune", "Yoshishige", "Yoshitada",
        "Yoshizane", "Yukihiro",
    }
)

REQUIRED_MAIN_COUNTRY_FILES = {
    "CJP - Confucian Wa.txt": (8, 10),
    "EJP - Yamato Court.txt": (8, 10),
    "IJP - Ikko Commonwealth.txt": (8, 12),
    "KJP - Kirishitan Japan.txt": (10, 11),
    "RFJ - Reformed Japan.txt": (8, 11),
    "SJP - Sultanate of Wa.txt": (9, 11),
    "WAK - Wokou Confederacy.txt": (8, 12),
    "HKK - Northern Star Sea Realm.txt": (7, 13),
    "NJF - Southern Japan Town Federation.txt": (7, 13),
    "NYA - New Yamato.txt": (7, 13),
    "OIA - Oceanic Island Alliance.txt": (7, 13),
    "TPF - Two Ocean Federation.txt": (7, 13),
}
REQUIRED_MAIN_HISTORY_FILES = frozenset(
    {
        "CJP - Confucian Wa.txt",
        "EJP - Yamato Court.txt",
        "IJP - Ikko Commonwealth.txt",
        "KJP - Kirishitan Japan.txt",
        "RFJ - Reformed Japan.txt",
        "SJP - Sultanate of Wa.txt",
        "WAK - Wokou Confederacy.txt",
    }
)
EXPECTED_FOREIGN_MONARCHS = {
    "KJP - Kirishitan Japan.txt": frozenset({"Dom Justo", "Maria", "Gracia"}),
    "RFJ - Reformed Japan.txt": frozenset({"Joosten"}),
    "SJP - Sultanate of Wa.txt": frozenset(
        {"Yusuf", "Harun", "Musa", "Ibrahim", "Umar", "Hidayat", "Suleiman"}
    ),
}
EXPECTED_FOREIGN_LEADERS = {
    "SJP - Sultanate of Wa.txt": frozenset(
        {"Yusuf", "Musa", "Ibrahim", "Hidayat"}
    )
}
GAMEPLAY_SCRIPT_DIRECTORIES = (
    "events",
    "missions",
    "decisions",
    "common/scripted_effects",
    "common/on_actions",
)
GENERATED_CULTURE_MARKER = b"# JXP_COMMON_JAPANESE_SURNAMES_V1"


@dataclass(frozen=True, slots=True)
class NameIssue:
    code: str
    path: Path
    line: int
    message: str


@dataclass(slots=True)
class NameAudit:
    issues: list[NameIssue] = field(default_factory=list)
    stats: Counter[str] = field(default_factory=Counter)

    def add(self, code: str, path: Path, line: int, message: str) -> None:
        self.issues.append(NameIssue(code, path, line, message))


def normalize_pool_name(value: str) -> str:
    return POOL_NUMBER_RE.sub("", value).strip()


def is_untranslated_person_literal(
    value: str,
    *,
    allow_non_japanese: bool = True,
) -> bool:
    """Return true when a display-name literal still contains Latin text."""

    normalized = normalize_pool_name(value)
    if not LATIN_RE.search(normalized):
        return False
    if allow_non_japanese and normalized in NON_JAPANESE_LITERAL_NAMES:
        return False
    if normalized.startswith("$") and normalized.endswith("$"):
        return False
    return True


def _relative(path: Path, repo_root: Path) -> Path:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return path


def _parse(path: Path, audit: NameAudit, repo_root: Path):
    try:
        return parse_file(path)
    except (ClausewitzParseError, OSError, UnicodeError) as exc:
        audit.add(
            "names.parse_error",
            _relative(path, repo_root),
            0,
            f"could not parse name-bearing Clausewitz file: {exc}",
        )
        return None


def _audit_literal(
    audit: NameAudit,
    repo_root: Path,
    source: Path,
    line: int,
    value: str,
    context: str,
    *,
    allow_non_japanese: bool = True,
) -> None:
    if not is_untranslated_person_literal(
        value,
        allow_non_japanese=allow_non_japanese,
    ):
        return
    audit.add(
        "names.romaji_literal",
        _relative(source, repo_root),
        line,
        f"{context} remains a Latin-script person name: {value!r}",
    )


def _direct_person_values(obj: Object) -> list[tuple[str, Scalar]]:
    return [
        (entry.key, entry.value)
        for entry in obj.entries
        if entry.key in {"name", "dynasty"} and isinstance(entry.value, Scalar)
    ]


def _scan_country_histories(
    roots: tuple[Path, ...],
    main_root: Path,
    audit: NameAudit,
    repo_root: Path,
) -> dict[Path, tuple[str, ...]]:
    values_by_file: dict[Path, tuple[str, ...]] = {}
    main_history_dir = main_root / "history" / "countries"
    main_names = {path.name for path in main_history_dir.glob("*.txt")}
    for missing in sorted(REQUIRED_MAIN_HISTORY_FILES - main_names):
        audit.add(
            "names.required_history_missing",
            _relative(main_history_dir / missing, repo_root),
            0,
            "required main-mod country history is missing",
        )

    for root in roots:
        directory = root / "history" / "countries"
        for path in sorted(directory.glob("*.txt")):
            document = _parse(path, audit, repo_root)
            if document is None:
                continue
            collected: list[str] = []
            for _parents, entry in walk_entries(document.root):
                if not isinstance(entry.value, Object) or not PERSON_OBJECT_RE.fullmatch(
                    entry.key or ""
                ):
                    continue
                for field_name, scalar in _direct_person_values(entry.value):
                    collected.append(scalar.text)
                    audit.stats["country_history_literals"] += 1
                    _audit_literal(
                        audit,
                        repo_root,
                        path,
                        scalar.line,
                        scalar.text,
                        f"{entry.key}.{field_name}",
                    )
            values_by_file[path] = tuple(collected)
            if root == main_root and path.name in REQUIRED_MAIN_HISTORY_FILES:
                if len(collected) != 2:
                    audit.add(
                        "names.main_history_shape",
                        _relative(path, repo_root),
                        0,
                        f"expected one initial name+dynasty pair, found {len(collected)} literals",
                    )

    sjp_history = main_history_dir / "SJP - Sultanate of Wa.txt"
    if "Yusuf" not in values_by_file.get(sjp_history, ()):
        audit.add(
            "names.foreign_name_changed",
            _relative(sjp_history, repo_root),
            0,
            "the non-Japanese ruler name Yusuf must remain unchanged",
        )
    return values_by_file


def _single_pool(
    document,
    pool_name: str,
    path: Path,
    audit: NameAudit,
    repo_root: Path,
) -> Object | None:
    entries = entries_named(document.root, pool_name)
    objects = [entry.value for entry in entries if isinstance(entry.value, Object)]
    if len(entries) != 1 or len(objects) != 1:
        audit.add(
            "names.pool_shape",
            _relative(path, repo_root),
            entries[0].line if entries else 0,
            f"expected exactly one {pool_name} object, found {len(entries)}",
        )
        return None
    return objects[0]


def _scan_country_pools(
    roots: tuple[Path, ...],
    main_root: Path,
    audit: NameAudit,
    repo_root: Path,
) -> dict[Path, tuple[tuple[str, ...], tuple[str, ...]]]:
    values_by_file: dict[Path, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    main_country_dir = main_root / "common" / "countries"
    main_names = {path.name for path in main_country_dir.glob("*.txt")}
    for missing in sorted(set(REQUIRED_MAIN_COUNTRY_FILES) - main_names):
        audit.add(
            "names.required_country_missing",
            _relative(main_country_dir / missing, repo_root),
            0,
            "required main-mod country definition is missing",
        )

    for root in roots:
        directory = root / "common" / "countries"
        for path in sorted(directory.glob("*.txt")):
            document = _parse(path, audit, repo_root)
            if document is None:
                continue
            monarch_pool = _single_pool(
                document, "monarch_names", path, audit, repo_root
            )
            leader_pool = _single_pool(
                document, "leader_names", path, audit, repo_root
            )
            monarch_values: list[str] = []
            leader_values: list[str] = []
            if monarch_pool is not None:
                for entry in monarch_pool.entries:
                    if entry.key is None:
                        audit.add(
                            "names.monarch_pool_member",
                            _relative(path, repo_root),
                            entry.line,
                            "monarch_names contains a value without a weighted name key",
                        )
                        continue
                    value = normalize_pool_name(entry.key)
                    monarch_values.append(value)
                    audit.stats["monarch_pool_entries"] += 1
                    _audit_literal(
                        audit,
                        repo_root,
                        path,
                        entry.line,
                        value,
                        "monarch_names",
                    )
            if leader_pool is not None:
                for scalar in bare_scalars(leader_pool):
                    leader_values.append(scalar.text)
                    audit.stats["leader_pool_entries"] += 1
                    _audit_literal(
                        audit,
                        repo_root,
                        path,
                        scalar.line,
                        scalar.text,
                        "leader_names",
                    )
            values_by_file[path] = (tuple(monarch_values), tuple(leader_values))

            expected = REQUIRED_MAIN_COUNTRY_FILES.get(path.name) if root == main_root else None
            if expected is not None and expected != (
                len(monarch_values),
                len(leader_values),
            ):
                audit.add(
                    "names.main_pool_count",
                    _relative(path, repo_root),
                    0,
                    "name-pool size changed: expected "
                    f"{expected[0]} monarch/{expected[1]} leader names, found "
                    f"{len(monarch_values)}/{len(leader_values)}",
                )

    for filename, expected in EXPECTED_FOREIGN_MONARCHS.items():
        path = main_country_dir / filename
        actual = set(values_by_file.get(path, ((), ()))[0])
        missing = expected - actual
        if missing:
            audit.add(
                "names.foreign_name_changed",
                _relative(path, repo_root),
                0,
                f"non-Japanese monarch names changed or disappeared: {sorted(missing)}",
            )
    for filename, expected in EXPECTED_FOREIGN_LEADERS.items():
        path = main_country_dir / filename
        actual = set(values_by_file.get(path, ((), ()))[1])
        missing = expected - actual
        if missing:
            audit.add(
                "names.foreign_name_changed",
                _relative(path, repo_root),
                0,
                f"non-Japanese leader names changed or disappeared: {sorted(missing)}",
            )
    return values_by_file


def _scan_culture_pools(
    roots: tuple[Path, ...],
    audit: NameAudit,
    repo_root: Path,
) -> None:
    pool_keys = {"male_names", "female_names", "dynasty_names"}
    for root in roots:
        for path in sorted((root / "common" / "cultures").glob("*.txt")):
            try:
                payload = path.read_bytes()
            except OSError as exc:
                audit.add(
                    "names.culture_registry_read",
                    _relative(path, repo_root),
                    0,
                    f"cannot read culture registry: {exc}",
                )
                continue
            if GENERATED_CULTURE_MARKER in payload:
                source = (
                    root
                    / "tools"
                    / "jxp_name_builder"
                    / "japanese_common_surnames.json"
                )
                surnames: list[str] = []
                try:
                    surnames = json.loads(source.read_text(encoding="utf-8"))[
                        "surnames"
                    ]
                    encoder = _load_escape_module(
                        repo_root
                        / "skills"
                        / "eu4-modding"
                        / "scripts"
                        / "encode_eu4_special_gameplay.py"
                    )
                    sections = payload.split(GENERATED_CULTURE_MARKER)[1:]
                    if len(sections) != 3:
                        raise ValueError(
                            f"expected 3 generated surname sections, found {len(sections)}"
                        )
                    for section in sections:
                        closing = section.find(b"\n\t\t}")
                        if closing < 0:
                            raise ValueError(
                                "generated surname section has no dynasty-pool terminator"
                            )
                        readable = encoder.decode_gameplay_bytes(
                            GENERATED_CULTURE_MARKER + section[:closing]
                        )
                        missing = [
                            surname for surname in surnames if surname not in readable
                        ]
                        if missing:
                            raise ValueError(
                                f"generated surname section is missing {missing}"
                            )
                except (OSError, KeyError, TypeError, ValueError, UnicodeError) as exc:
                    audit.add(
                        "names.generated_culture_registry",
                        _relative(path, repo_root),
                        0,
                        f"generated Japanese surname registry is invalid: {exc}",
                    )
                audit.stats["culture_pool_entries"] += len(surnames) * 3
                audit.stats["generated_culture_registries"] += 1
                continue
            document = _parse(path, audit, repo_root)
            if document is None:
                continue
            for _parents, entry in walk_entries(document.root):
                if entry.key not in pool_keys or not isinstance(entry.value, Object):
                    continue
                for scalar in bare_scalars(entry.value):
                    audit.stats["culture_pool_entries"] += 1
                    _audit_literal(
                        audit,
                        repo_root,
                        path,
                        scalar.line,
                        scalar.text,
                        entry.key,
                    )


def _looks_like_script_key(value: Scalar) -> bool:
    if value.quoted:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_.:-]+", value.text)) and (
        "_" in value.text or "." in value.text
    )


def _scan_scripted_people(
    roots: tuple[Path, ...],
    audit: NameAudit,
    repo_root: Path,
) -> None:
    seen: set[Path] = set()
    for root in roots:
        for relative_directory in GAMEPLAY_SCRIPT_DIRECTORIES:
            directory = root / relative_directory
            for path in sorted(directory.rglob("*.txt")):
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                document = _parse(path, audit, repo_root)
                if document is None:
                    continue
                for _parents, entry in walk_entries(document.root):
                    if not isinstance(entry.value, Object) or not PERSON_OBJECT_RE.fullmatch(
                        entry.key or ""
                    ):
                        continue
                    audit.stats["scripted_person_objects"] += 1
                    for field_name, scalar in _direct_person_values(entry.value):
                        if _looks_like_script_key(scalar):
                            audit.stats["scripted_person_name_keys"] += 1
                            continue
                        audit.stats["scripted_person_literals"] += 1
                        _audit_literal(
                            audit,
                            repo_root,
                            path,
                            scalar.line,
                            scalar.text,
                            f"{entry.key}.{field_name}",
                        )


def _load_escape_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_jxp_eu4_escape", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scan_gameplay_name_encoding(
    main_root: Path,
    map_root: Path,
    audit: NameAudit,
    repo_root: Path,
) -> None:
    encoder_path = (
        repo_root
        / "skills"
        / "eu4-modding"
        / "scripts"
        / "encode_eu4_special_gameplay.py"
    )
    try:
        encoder = _load_escape_module(encoder_path)
        encode = encoder.encode_gameplay_text
        decode = encoder.decode_gameplay_bytes
    except (OSError, ImportError, AttributeError) as exc:
        audit.add(
            "names.gameplay_encoder_missing",
            _relative(encoder_path, repo_root),
            0,
            f"cannot load canonical gameplay-name encoder: {exc}",
        )
        return

    source_root = main_root / "tools" / "jxp_name_builder" / "source"
    source_sets = {
        "history/countries": set(REQUIRED_MAIN_HISTORY_FILES),
        "common/countries": set(REQUIRED_MAIN_COUNTRY_FILES),
    }
    for directory, expected_names in source_sets.items():
        source_directory = source_root / directory
        actual_names = {path.name for path in source_directory.glob("*.txt")}
        if actual_names != expected_names:
            audit.add(
                "names.gameplay_source_set",
                _relative(source_directory, repo_root),
                0,
                "route-country gameplay-name source set drifted: "
                f"missing={sorted(expected_names - actual_names)}, "
                f"extra={sorted(actual_names - expected_names)}",
            )
        for filename in sorted(expected_names):
            source = source_directory / filename
            active = main_root / directory / filename
            try:
                readable = source.read_bytes().decode("utf-8-sig")
                expected = encode(readable)
                actual = active.read_bytes()
            except (OSError, UnicodeError, ValueError) as exc:
                audit.add(
                    "names.gameplay_source_read",
                    _relative(source, repo_root),
                    0,
                    f"cannot reproduce route-country gameplay-name bytes: {exc}",
                )
                continue
            if actual != expected:
                audit.add(
                    "names.gameplay_source_drift",
                    _relative(active, repo_root),
                    0,
                    f"active gameplay-name bytes differ from {source.name}",
                )
            audit.stats["gameplay_source_pairs"] += 1

    checked = 0
    for root in (main_root, map_root):
        for relative_directory in ("history/countries", "common/countries"):
            for path in sorted((root / relative_directory).glob("*.txt")):
                try:
                    payload = path.read_bytes()
                    readable = decode(payload)
                    canonical = encode(readable)
                except (OSError, UnicodeError, ValueError) as exc:
                    audit.add(
                        "names.gameplay_encoding_read",
                        _relative(path, repo_root),
                        0,
                        f"cannot decode gameplay-name file: {exc}",
                    )
                    continue
                if payload.startswith(b"\xef\xbb\xbf"):
                    audit.add(
                        "names.gameplay_encoding_bom",
                        _relative(path, repo_root),
                        0,
                        "gameplay-name file must be BOM-free",
                    )
                try:
                    utf8_text = payload.decode("utf-8-sig")
                except UnicodeDecodeError:
                    utf8_text = ""
                if re.search(r"[\u3400-\u9fff]", utf8_text):
                    audit.add(
                        "names.gameplay_encoding_raw_cjk",
                        _relative(path, repo_root),
                        0,
                        "active gameplay-name file contains raw UTF-8 CJK",
                    )
                if payload != canonical:
                    audit.add(
                        "names.gameplay_encoding_noncanonical",
                        _relative(path, repo_root),
                        0,
                        "active gameplay-name bytes are not canonical EU4SpecialEscape",
                    )
                checked += 1
    audit.stats["gameplay_encoded_files"] = checked


def _legacy_romaji_in_value(value: str) -> tuple[str, ...]:
    found = []
    for name in sorted(LEGACY_JAPANESE_ROMAJI, key=lambda item: (-len(item), item)):
        if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", value):
            found.append(name)
    return tuple(found)


def _scan_localisation_values(
    path: Path,
    text: str,
    audit: NameAudit,
    repo_root: Path,
) -> None:
    for line_number, line in enumerate(text.splitlines(), 1):
        match = LOCALISATION_LINE_RE.match(line)
        if not match:
            continue
        audit.stats["localisation_values"] += 1
        legacy = _legacy_romaji_in_value(match.group(1))
        if legacy:
            audit.add(
                "names.localisation_romaji",
                _relative(path, repo_root),
                line_number,
                f"localisation value retains Japanese romaji: {list(legacy)}",
            )


def _scan_localisation_pipeline(
    roots: tuple[Path, ...],
    audit: NameAudit,
    repo_root: Path,
) -> None:
    escape_path = (
        repo_root
        / "skills"
        / "eu4-modding"
        / "scripts"
        / "escape_eu4_special_localisation.py"
    )
    try:
        escape_text = _load_escape_module(escape_path).escape_text
    except (OSError, ImportError, AttributeError) as exc:
        audit.add(
            "names.escape_pipeline_missing",
            _relative(escape_path, repo_root),
            0,
            f"cannot load canonical EU4SpecialEscape converter: {exc}",
        )
        return

    for root in roots:
        source_directory = root / "localisation_source"
        for source in sorted(source_directory.glob("*_utf8_source.yml")):
            active = root / "localisation" / source.name.replace("_utf8_source", "")
            source_bytes = source.read_bytes()
            source_text = source_bytes.decode("utf-8-sig")
            _scan_localisation_values(source, source_text, audit, repo_root)
            if not active.is_file():
                audit.add(
                    "names.active_localisation_missing",
                    _relative(active, repo_root),
                    0,
                    "active localisation counterpart is missing",
                )
                continue
            expected = escape_text(source_text).encode("utf-8-sig")
            actual = active.read_bytes()
            if actual != expected:
                audit.add(
                    "names.localisation_pipeline_drift",
                    _relative(active, repo_root),
                    0,
                    f"active localisation is not the exact escaped form of {source.name}",
                )
            try:
                active_text = actual.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                audit.add(
                    "names.active_localisation_encoding",
                    _relative(active, repo_root),
                    0,
                    f"active localisation is not UTF-8: {exc}",
                )
                continue
            if re.search(r"[\u3400-\u9fff]", active_text):
                audit.add(
                    "names.active_localisation_raw_cjk",
                    _relative(active, repo_root),
                    0,
                    "active localisation contains raw CJK instead of escaped bytes",
                )
            _scan_localisation_values(active, active_text, audit, repo_root)
            audit.stats["localisation_pairs"] += 1


def _first_person_object(document, key: str) -> Object | None:
    for _parents, entry in walk_entries(document.root):
        if entry.key == key and isinstance(entry.value, Object):
            return entry.value
    return None


def _map_generation_contract(
    map_root: Path,
    pool_values: dict[Path, tuple[tuple[str, ...], tuple[str, ...]]],
    audit: NameAudit,
    repo_root: Path,
) -> None:
    builder = map_root / "tools" / "jxp_map_builder"
    plan_path = builder / "history_plan.json"
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        audit.add(
            "names.map_plan_error",
            _relative(plan_path, repo_root),
            0,
            f"cannot read companion history plan: {exc}",
        )
        return
    countries = plan.get("countries", [])
    tags = [country.get("tag") for country in countries]
    if len(countries) != 30 or len(set(tags)) != 30:
        audit.add(
            "names.map_plan_country_count",
            _relative(plan_path, repo_root),
            0,
            f"expected 30 unique companion country records, found {len(countries)}",
        )

    for country in countries:
        tag = country.get("tag", "<missing>")
        ruler = country.get("ruler_zh")
        dynasty = country.get("dynasty_zh")
        for field_name, value in (("ruler_zh", ruler), ("dynasty_zh", dynasty)):
            if not isinstance(value, str) or not value:
                audit.add(
                    "names.map_plan_chinese_name",
                    _relative(plan_path, repo_root),
                    0,
                    f"{tag} lacks non-empty {field_name}",
                )
            elif is_untranslated_person_literal(value, allow_non_japanese=False):
                audit.add(
                    "names.map_plan_chinese_name",
                    _relative(plan_path, repo_root),
                    0,
                    f"{tag}.{field_name} remains Latin-script: {value!r}",
                )
        if not isinstance(ruler, str) or not isinstance(dynasty, str):
            continue

        history_matches = sorted(
            (map_root / "history" / "countries").glob(f"{tag} - *.txt")
        )
        if len(history_matches) != 1:
            audit.add(
                "names.map_history_sync",
                _relative(map_root / "history" / "countries", repo_root),
                0,
                f"{tag} has {len(history_matches)} generated history files",
            )
            continue
        history_document = _parse(history_matches[0], audit, repo_root)
        monarch = (
            _first_person_object(history_document, "monarch")
            if history_document is not None
            else None
        )
        values = {
            key: scalar.text for key, scalar in _direct_person_values(monarch)
        } if monarch is not None else {}
        if values.get("name") != ruler or values.get("dynasty") != dynasty:
            audit.add(
                "names.map_history_sync",
                _relative(history_matches[0], repo_root),
                0,
                f"{tag} generated history differs from ruler_zh/dynasty_zh",
            )

        definition = map_root / "common" / "countries" / f"JXP {country['name']}.txt"
        monarch_names, leader_names = pool_values.get(definition, ((), ()))
        if ruler not in monarch_names or dynasty not in leader_names:
            audit.add(
                "names.map_pool_sync",
                _relative(definition, repo_root),
                0,
                f"{tag} generated pools do not contain {ruler!r}/{dynasty!r}",
            )
        if (len(monarch_names), len(leader_names)) != (7, 13):
            audit.add(
                "names.map_pool_count",
                _relative(definition, repo_root),
                0,
                "companion pool size changed: expected 7 monarch/13 leader names, "
                f"found {len(monarch_names)}/{len(leader_names)}",
            )
        audit.stats["map_source_records"] += 1

    generator_path = builder / "build_countries.py"
    try:
        generator = generator_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        audit.add(
            "names.map_generator_error",
            _relative(generator_path, repo_root),
            0,
            f"cannot read companion country generator: {exc}",
        )
        return
    required_fragments = (
        'country["ruler_zh"]',
        'country["dynasty_zh"]',
        "MAP_MONARCH_NAME_FALLBACKS",
        "MAP_LEADER_NAMES",
        "GAMEPLAY_ENCODER",
        "load_gameplay_encoder",
        "encode_gameplay_text",
        "write_bytes",
    )
    for fragment in required_fragments:
        if fragment not in generator:
            audit.add(
                "names.map_generator_contract",
                _relative(generator_path, repo_root),
                0,
                f"companion generator is missing Chinese-name contract {fragment!r}",
            )


def audit_japanese_names(
    main_root: Path,
    map_root: Path | None = None,
    repo_root: Path | None = None,
) -> NameAudit:
    main_root = main_root.resolve()
    repo_root = (repo_root or main_root.parent).resolve()
    map_root = (map_root or repo_root / "japan_expanded_v2_map").resolve()
    roots = tuple(root for root in (main_root, map_root) if root.is_dir())
    audit = NameAudit()
    if map_root.is_dir():
        _scan_gameplay_name_encoding(
            main_root, map_root, audit, repo_root
        )
    _scan_country_histories(roots, main_root, audit, repo_root)
    pool_values = _scan_country_pools(roots, main_root, audit, repo_root)
    _scan_culture_pools(roots, audit, repo_root)
    _scan_scripted_people(roots, audit, repo_root)
    _scan_localisation_pipeline(roots, audit, repo_root)
    if map_root.is_dir():
        _map_generation_contract(map_root, pool_values, audit, repo_root)
    else:
        audit.add(
            "names.map_mod_missing",
            _relative(map_root, repo_root),
            0,
            "mandatory companion mod is missing from the release surface",
        )
    audit.issues.sort(key=lambda issue: (issue.path.as_posix(), issue.line, issue.code))
    return audit


def check_japanese_names(context: ValidationContext) -> CheckResult:
    """Adapt the cross-mod name audit to the shared release-gate interface."""

    result = CheckResult("Chinese Japanese-person display names")
    repo_root = context.mod_root.parent
    audit = audit_japanese_names(
        context.mod_root,
        repo_root / "japan_expanded_v2_map",
        repo_root,
    )
    for issue in audit.issues:
        result.add(
            issue.code,
            issue.message,
            issue.path.as_posix(),
            issue.line or None,
        )
    result.metrics.update(dict(audit.stats))
    result.summary = (
        f"{audit.stats['country_history_literals']} history literals, "
        f"{audit.stats['monarch_pool_entries']} monarch-pool entries, "
        f"{audit.stats['leader_pool_entries']} leader-pool entries, "
        f"{audit.stats['gameplay_encoded_files']} encoded gameplay files, "
        f"{audit.stats['map_source_records']} companion source records; "
        f"{len(audit.issues)} issue(s)"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    default_main = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-mod", type=Path, default=default_main)
    parser.add_argument("--map-mod", type=Path)
    parser.add_argument("--repo-root", type=Path)
    args = parser.parse_args(argv)
    audit = audit_japanese_names(args.main_mod, args.map_mod, args.repo_root)
    for issue in audit.issues:
        location = f"{issue.path}:{issue.line}" if issue.line else str(issue.path)
        print(f"ERROR [{issue.code}] {location}: {issue.message}")
    print(
        "NAME AUDIT: "
        f"history={audit.stats['country_history_literals']}, "
        f"monarch_pool={audit.stats['monarch_pool_entries']}, "
        f"leader_pool={audit.stats['leader_pool_entries']}, "
        f"scripted_named={audit.stats['scripted_person_literals']}, "
        f"gameplay_encoded={audit.stats['gameplay_encoded_files']}, "
        f"map_sources={audit.stats['map_source_records']}, "
        f"localisation_pairs={audit.stats['localisation_pairs']}, "
        f"issues={len(audit.issues)}"
    )
    return 1 if audit.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
