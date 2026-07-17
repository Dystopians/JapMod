#!/usr/bin/env python3
"""Encode or decode EU4SpecialEscape bytes in Clausewitz gameplay files.

Community double-byte patches do not decode ordinary UTF-8 literals in
``history`` and ``common/countries`` reliably.  Keep a readable UTF-8 source,
then generate the active gameplay file as BOM-free CP1252 bytes containing the
same EU4SpecialEscape triplets used by compatible Chinese language mods.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType


ESCAPE_SCRIPT = Path(__file__).with_name("escape_eu4_special_localisation.py")


def _load_escape_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_eu4_special_escape", ESCAPE_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {ESCAPE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encode_gameplay_text(text: str) -> bytes:
    """Return BOM-free active gameplay bytes for readable Unicode text."""

    escape_module = _load_escape_module()
    escaped = escape_module.escape_text(text)
    payload = bytearray()
    for char in escaped:
        codepoint = ord(char)
        if codepoint in escape_module.UCS2_TO_CP1252:
            payload.append(escape_module.UCS2_TO_CP1252[codepoint])
        elif codepoint <= 0xFF:
            # CP1252 leaves five byte values undefined.  EU4SpecialEscape may
            # still use those raw values inside a triplet, so a normal codec
            # encoder is too strict for the gameplay-byte contract.
            payload.append(codepoint)
        else:
            payload.extend(char.encode("cp1252"))
    return bytes(payload)


def decode_gameplay_bytes(payload: bytes) -> str:
    """Decode BOM-free EU4SpecialEscape gameplay bytes to readable Unicode."""

    escape_module = _load_escape_module()
    result: list[str] = []
    index = 0
    while index < len(payload):
        marker = payload[index]
        if marker not in {0x10, 0x11, 0x12, 0x13}:
            end = index + 1
            while end < len(payload) and payload[end] not in {0x10, 0x11, 0x12, 0x13}:
                end += 1
            result.extend(
                chr(escape_module.CP1252_TO_UCS2.get(byte, byte))
                for byte in payload[index:end]
            )
            index = end
            continue
        if index + 2 >= len(payload):
            raise UnicodeDecodeError(
                "eu4-special-escape",
                payload,
                index,
                len(payload),
                "truncated EU4SpecialEscape triplet",
            )
        low = payload[index + 1]
        high = payload[index + 2]
        if marker in {0x11, 0x13}:
            low -= 14
        if marker in {0x12, 0x13}:
            high += 9
        codepoint = (high << 8) | low
        if 0xE100 < codepoint < 0xEA00:
            codepoint -= 0xE000
        result.append(chr(codepoint))
        index += 3
    return "".join(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--decode",
        action="store_true",
        help="decode an active gameplay file back to UTF-8 instead of encoding it",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.decode:
        text = decode_gameplay_bytes(args.input.read_bytes())
        args.output.write_text(text, encoding="utf-8", newline="")
    else:
        text = args.input.read_bytes().decode("utf-8-sig")
        args.output.write_bytes(encode_gameplay_text(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
