#!/usr/bin/env python3
"""Generate the exact-path vanilla wargoal registry with one bounded patch."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


MOD_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = MOD_ROOT / "common" / "wargoal_types" / "00_wargoal_types.txt"
RELATIVE_SOURCE = Path("common/wargoal_types/00_wargoal_types.txt")
EXPECTED_SHA256 = "ec45a5a221b762a326fab4f29099e39b6461665072d53fa398ac466f38617600"

REPLACEMENT = """annex_country_japan = {
\ttype = take_capital
\t
\tattacker = {
\t\tbadboy_factor = 0.75
\t\tprestige_factor = 1
\t\tpeace_cost_factor = 1.0\t
\t\t
\t\tallowed_provinces = {
\t\t\tregion = japan_region
\t\t\towner = {
\t\t\t\tculture_group = japanese_g
\t\t\t\tjxp_is_daimyo_stage_trigger = yes
\t\t\t}
\t\t\tROOT = { jxp_is_daimyo_stage_trigger = yes }
\t\t}

\t\tpeace_options = {
\t\t\tpo_demand_provinces
\t\t}
\t\t
\t\tallow_annex = yes
\t}
\t
\tdefender = {
\t\tbadboy_factor = 1
\t\tprestige_factor = 1
\t\tpeace_cost_factor = 1

\t\tpeace_options = {
\t\t\tpo_demand_provinces
\t\t}
\t}

\twar_name = PRIMITIVE_WAR_NAME
}"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def block_span(text: str, key: str) -> tuple[int, int]:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"missing top-level block: {key}")
    start = match.start()
    brace = text.find("{", match.start(), match.end())
    depth = 0
    quoted = False
    escaped = False
    comment = False
    for index in range(brace, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
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
            comment = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise ValueError(f"unterminated top-level block: {key}")


def expected_bytes(game_root: Path) -> bytes:
    source = game_root / RELATIVE_SOURCE
    vanilla = source.read_bytes()
    actual = sha256(vanilla)
    if actual != EXPECTED_SHA256:
        raise ValueError(
            f"pinned EU4 1.37.5 wargoal registry drift: expected {EXPECTED_SHA256}, got {actual}"
        )
    text = vanilla.decode("utf-8-sig")
    start, end = block_span(text, "annex_country_japan")
    patched = text[:start] + REPLACEMENT + text[end:]
    if patched.count("annex_country_japan = {") != 1:
        raise ValueError("annex_country_japan patch is not unique")
    return patched.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        expected = expected_bytes(args.game_root)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != expected:
            print(f"ERROR: generated wargoal registry drift: {OUTPUT}", file=sys.stderr)
            return 1
        print(
            "Internal wargoal registry check passed "
            f"({len(expected)} bytes, sha256={sha256(expected)})"
        )
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(expected)
    print(
        f"Wrote {OUTPUT} ({len(expected)} bytes, sha256={sha256(expected)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
