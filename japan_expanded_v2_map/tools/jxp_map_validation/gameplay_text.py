"""Read Clausewitz text across UTF-8, CP1252, and EU4SpecialEscape files."""

from __future__ import annotations

from pathlib import Path


CP1252_TO_UNICODE = {
    0x80: 0x20AC, 0x82: 0x201A, 0x83: 0x0192, 0x84: 0x201E,
    0x85: 0x2026, 0x86: 0x2020, 0x87: 0x2021, 0x88: 0x02C6,
    0x89: 0x2030, 0x8A: 0x0160, 0x8B: 0x2039, 0x8C: 0x0152,
    0x8E: 0x017D, 0x91: 0x2018, 0x92: 0x2019, 0x93: 0x201C,
    0x94: 0x201D, 0x95: 0x2022, 0x96: 0x2013, 0x97: 0x2014,
    0x98: 0x02DC, 0x99: 0x2122, 0x9A: 0x0161, 0x9B: 0x203A,
    0x9C: 0x0153, 0x9E: 0x017E, 0x9F: 0x0178,
}
MARKERS = {0x10, 0x11, 0x12, 0x13}


def decode_eu4_special_gameplay(data: bytes) -> str:
    output = []
    index = 0
    while index < len(data):
        marker = data[index]
        if marker not in MARKERS:
            output.append(chr(CP1252_TO_UNICODE.get(marker, marker)))
            index += 1
            continue
        if index + 2 >= len(data):
            raise UnicodeDecodeError(
                "eu4-special-escape",
                data,
                index,
                len(data),
                "truncated EU4SpecialEscape triplet",
            )
        low, high = data[index + 1], data[index + 2]
        if marker in {0x11, 0x13}:
            low -= 14
        if marker in {0x12, 0x13}:
            high += 9
        codepoint = (high << 8) | low
        if 0xE100 < codepoint < 0xEA00:
            codepoint -= 0xE000
        output.append(chr(codepoint))
        index += 3
    return "".join(output)


def read_gameplay_text(path: Path) -> str:
    data = path.read_bytes()
    if any(marker in data for marker in MARKERS):
        return decode_eu4_special_gameplay(data)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")
