#!/usr/bin/env python3
"""Build the JXP daimyo subject contract from the pinned EU4 1.37.5 file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
VANILLA_RELATIVE = Path("common/subject_types/00_subject_types.txt")
OUTPUT_RELATIVE = VANILLA_RELATIVE
PINNED_VANILLA_SHA256 = (
    "81706ed7cd5f707c6b5ff94bd7fb9a5be8487335c0076879bfe02d4bc3eadfce"
)
GENERATED_MARKER = "# JXP_DAIMYO_SELECTIVE_CALL_TO_ARMS_V1"
PROPERTY_LINES = (
    "joins_overlords_wars = no",
    "can_be_co_belligerented = yes",
    "must_accept_cta_from_overlord = yes",
    "can_gain_favors = yes",
    "favors_cost_to_join_offensive_wars = 20",
    "favors_cost_to_join_defensive_wars = 10",
    "opinion_cost_to_join_offensive_wars = 40",
    "opinion_cost_to_join_defensive_wars = 20",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_contract(game_root: Path) -> bytes:
    source = game_root / VANILLA_RELATIVE
    vanilla = source.read_bytes()
    actual_hash = _sha256(vanilla)
    if actual_hash != PINNED_VANILLA_SHA256:
        raise RuntimeError(
            "Pinned vanilla 00_subject_types.txt hash mismatch: "
            f"{actual_hash}"
        )

    match = re.search(
        rb"(?m)^daimyo_vassal[ \t]*=[ \t]*\{\r?\n"
        rb"[ \t]*copy_from[ \t]*=[ \t]*vassal\r?\n"
        rb"[ \t]*count[ \t]*=[ \t]*vassal\r?\n",
        vanilla,
    )
    if match is None:
        raise RuntimeError("Cannot locate the full vanilla daimyo_vassal block")

    newline = b"\r\n" if b"\r\n" in vanilla else b"\n"
    properties = vanilla.find(b"\t# Properties:", match.end())
    if properties < 0:
        raise RuntimeError("daimyo_vassal block has no Properties marker")
    insertion_at = vanilla.find(newline, properties)
    if insertion_at < 0:
        raise RuntimeError("daimyo_vassal Properties marker has no line ending")
    insertion_at += len(newline)

    rendered_lines = [GENERATED_MARKER, *PROPERTY_LINES]
    insertion = b"".join(
        b"\t" + line.encode("ascii") + newline for line in rendered_lines
    )
    output = vanilla[:insertion_at] + insertion + vanilla[insertion_at:]

    if output.count(GENERATED_MARKER.encode("ascii")) != 1:
        raise RuntimeError("Generated subject contract marker is not unique")
    for property_line in PROPERTY_LINES:
        if output.count(("\t" + property_line).encode("ascii")) < 1:
            raise RuntimeError(f"Generated subject contract lost {property_line}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--mod-root", type=Path, default=MOD_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = build_contract(args.game_root)
    output = args.mod_root / OUTPUT_RELATIVE
    if args.check:
        if not output.is_file() or output.read_bytes() != expected:
            raise SystemExit(f"Shogunate subject contract is stale: {output}")
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
                "schema": "jxp_shogunate_contract/v1",
                "mode": mode,
                "output": output.as_posix(),
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
