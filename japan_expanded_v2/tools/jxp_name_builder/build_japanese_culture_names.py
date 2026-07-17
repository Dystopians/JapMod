#!/usr/bin/env python3
"""Build expanded Japanese dynasty pools from the pinned EU4 culture file."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import ModuleType


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
SOURCE_PATH = SCRIPT_DIR / "japanese_common_surnames.json"
ENCODER_PATH = (
    MOD_ROOT.parent
    / "skills"
    / "eu4-modding"
    / "scripts"
    / "encode_eu4_special_gameplay.py"
)
VANILLA_RELATIVE = Path("common/cultures/00_cultures.txt")
OUTPUT_RELATIVE = VANILLA_RELATIVE
PINNED_VANILLA_SHA256 = (
    "9192d84d620c2ab696d95f5d4f57c386f789814e2b3c7be0963a8425a738ffa0"
)
GENERATED_MARKER = "# JXP_COMMON_JAPANESE_SURNAMES_V1"
CULTURES = ("togoku", "japanese", "kyushuan")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_encoder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_jxp_culture_name_encoder",
        ENCODER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load gameplay-name encoder: {ENCODER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("encode_gameplay_text", "decode_gameplay_bytes"):
        if not callable(getattr(module, name, None)):
            raise RuntimeError(f"Gameplay-name encoder lacks {name}")
    return module


def _matching_brace(text: str, opening: int) -> int:
    depth = 0
    quoted = False
    commented = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if commented:
            if char in "\r\n":
                commented = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            commented = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
            if depth < 0:
                break
    raise RuntimeError(f"Unmatched opening brace at byte-preserving offset {opening}")


def _block_span(text: str, pattern: str, start: int, end: int) -> tuple[int, int]:
    match = re.search(pattern, text[start:end], flags=re.MULTILINE)
    if match is None:
        raise RuntimeError(f"Cannot locate block matching {pattern!r}")
    absolute_start = start + match.start()
    opening = text.find("{", absolute_start, start + match.end())
    return absolute_start, _matching_brace(text, opening) + 1


def _source_surnames() -> tuple[str, ...]:
    payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != "jxp_japanese_common_surnames/v1":
        raise RuntimeError(f"Unexpected surname schema in {SOURCE_PATH}")
    surnames = tuple(payload.get("surnames", ()))
    if not surnames or len(surnames) != len(set(surnames)):
        raise RuntimeError("Japanese common surname source is empty or duplicated")
    invalid = [name for name in surnames if re.search(r'[\s{}"#]', name)]
    if invalid:
        raise RuntimeError(f"Surnames contain Clausewitz delimiters: {invalid}")
    return surnames


def _render_name_lines(
    surnames: tuple[str, ...],
    newline: str,
    encoder: ModuleType,
) -> str:
    lines = [f"\t\t\t{GENERATED_MARKER}"]
    width = 8
    for offset in range(0, len(surnames), width):
        lines.append("\t\t\t" + " ".join(surnames[offset : offset + width]))
    readable = newline.join(lines) + newline
    return encoder.encode_gameplay_text(readable).decode("latin-1")


def _dynasty_spans(text: str) -> tuple[tuple[str, int, int], ...]:
    group_start, group_end = _block_span(
        text,
        r"^japanese_g[ \t]*=[ \t]*\{",
        0,
        len(text),
    )
    spans: list[tuple[str, int, int]] = []
    for culture in CULTURES:
        culture_start, culture_end = _block_span(
            text,
            rf"^\t{culture}[ \t]*=[ \t]*\{{",
            group_start,
            group_end,
        )
        dynasty_start, dynasty_end = _block_span(
            text,
            r"^\t\tdynasty_names[ \t]*=[ \t]*\{",
            culture_start,
            culture_end,
        )
        spans.append((culture, dynasty_start, dynasty_end))
    return tuple(spans)


def build_cultures(game_root: Path) -> bytes:
    vanilla_path = game_root / VANILLA_RELATIVE
    vanilla = vanilla_path.read_bytes()
    actual_hash = _sha256(vanilla)
    if actual_hash != PINNED_VANILLA_SHA256:
        raise RuntimeError(
            f"Pinned vanilla 00_cultures.txt hash mismatch: {actual_hash}"
        )

    text = vanilla.decode("latin-1")
    newline = "\r\n" if "\r\n" in text else "\n"
    surnames = _source_surnames()
    encoder = _load_encoder()
    insertion = _render_name_lines(surnames, newline, encoder)

    edits: list[tuple[int, str]] = []
    for culture, dynasty_start, dynasty_end in _dynasty_spans(text):
        closing = dynasty_end - 1
        closing_line = text.rfind("\n", dynasty_start, closing) + 1
        body = text[dynasty_start:dynasty_end]
        readable_body = encoder.decode_gameplay_bytes(body.encode("latin-1"))
        for surname in surnames:
            if surname in readable_body:
                raise RuntimeError(
                    f"{surname} already exists in pinned {culture} dynasty pool"
                )
        edits.append((closing_line, insertion))

    output = text
    for offset, payload in sorted(edits, reverse=True):
        output = output[:offset] + payload + output[offset:]

    if output.count(GENERATED_MARKER) != len(CULTURES):
        raise RuntimeError("Generated Japanese surname markers are incomplete")
    for culture, dynasty_start, dynasty_end in _dynasty_spans(output):
        body = output[dynasty_start:dynasty_end].encode("latin-1")
        readable_body = encoder.decode_gameplay_bytes(body)
        missing = [surname for surname in surnames if surname not in readable_body]
        if missing:
            raise RuntimeError(
                f"Generated {culture} dynasty pool lost surnames: {missing}"
            )
    return output.encode("latin-1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--mod-root", type=Path, default=MOD_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = build_cultures(args.game_root)
    output = args.mod_root / OUTPUT_RELATIVE
    if args.check:
        if not output.is_file() or output.read_bytes() != expected:
            raise SystemExit(f"Japanese culture-name registry is stale: {output}")
        mode = "check"
        written = 0
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(expected)
        mode = "write"
        written = 1

    print(
        json.dumps(
            {
                "schema": "jxp_japanese_culture_names/v1",
                "mode": mode,
                "output": output.as_posix(),
                "cultures": list(CULTURES),
                "surnames_per_culture": len(_source_surnames()),
                "bytes": len(expected),
                "sha256": _sha256(expected),
                "written": written,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
