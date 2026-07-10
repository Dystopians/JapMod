#!/usr/bin/env python3
"""Convert UTF-8 EU4 localisation text to EU4SpecialEscape-compatible text.

This mirrors the public EU4SpecialEscape algorithm used by EU4 double-byte
language patches. The output is UTF-8 with BOM, but non-CP1252 characters are
encoded as EU4 special escape triplets so the game does not replace them with
question marks.
"""

from __future__ import annotations

import argparse
from pathlib import Path


CP1252_TO_UCS2 = {
    0x80: 0x20AC,
    0x82: 0x201A,
    0x83: 0x0192,
    0x84: 0x201E,
    0x85: 0x2026,
    0x86: 0x2020,
    0x87: 0x2021,
    0x88: 0x02C6,
    0x89: 0x2030,
    0x8A: 0x0160,
    0x8B: 0x2039,
    0x8C: 0x0152,
    0x8E: 0x017D,
    0x91: 0x2018,
    0x92: 0x2019,
    0x93: 0x201C,
    0x94: 0x201D,
    0x95: 0x2022,
    0x96: 0x2013,
    0x97: 0x2014,
    0x98: 0x02DC,
    0x99: 0x2122,
    0x9A: 0x0161,
    0x9B: 0x203A,
    0x9C: 0x0153,
    0x9E: 0x017E,
    0x9F: 0x0178,
}

UCS2_TO_CP1252 = {v: k for k, v in CP1252_TO_UCS2.items()}

SPECIAL_BYTES = {
    0xA4,
    0xA3,
    0xA7,
    0x24,
    0x5B,
    0x00,
    0x5C,
    0x20,
    0x0D,
    0x0A,
    0x22,
    0x7B,
    0x7D,
    0x40,
    0x80,
    0x7E,
    0x2F,
    0xBD,
    0x3B,
    0x5D,
    0x5F,
    0x3D,
    0x23,
    0x3F,
    0x3A,
}


def cp1252_to_char(byte_value: int) -> str:
    return chr(CP1252_TO_UCS2.get(byte_value, byte_value))


def ucs2_to_cp1252(codepoint: int) -> int:
    return UCS2_TO_CP1252.get(codepoint, codepoint)


def iter_utf16_code_units(text: str):
    for char in text:
        codepoint = ord(char)
        if codepoint <= 0xFFFF:
            yield codepoint
            continue
        codepoint -= 0x10000
        yield 0xD800 + (codepoint >> 10)
        yield 0xDC00 + (codepoint & 0x3FF)


def escape_code_unit(codepoint: int) -> str:
    if ucs2_to_cp1252(codepoint) != codepoint:
        return chr(codepoint)

    if 0x100 < codepoint < 0xA00:
        codepoint += 0xE000

    high = (codepoint >> 8) & 0xFF
    low = codepoint & 0xFF
    if high == 0:
        return chr(codepoint)

    escape_char = 0x10
    if high in SPECIAL_BYTES:
        escape_char += 2
    if low in SPECIAL_BYTES:
        escape_char += 1

    if escape_char == 0x11:
        low += 14
    elif escape_char == 0x12:
        high -= 9
    elif escape_char == 0x13:
        low += 14
        high -= 9

    return chr(escape_char) + cp1252_to_char(low) + cp1252_to_char(high)


def escape_text(text: str) -> str:
    return "".join(escape_code_unit(cp) for cp in iter_utf16_code_units(text))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--backup",
        type=Path,
        help="Optional path to save the original UTF-8 source before overwriting.",
    )
    args = parser.parse_args()

    source_bytes = args.input.read_bytes()
    text = source_bytes.decode("utf-8-sig")
    if args.backup and not args.backup.exists():
        args.backup.parent.mkdir(parents=True, exist_ok=True)
        args.backup.write_bytes(source_bytes)

    escaped = escape_text(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(escaped.encode("utf-8-sig"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
