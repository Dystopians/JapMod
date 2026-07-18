#!/usr/bin/env python3
"""Generate inactive aliases for mission-series keys polluted by an old UTF-8 BOM."""

from __future__ import annotations

import argparse
from pathlib import Path


FILE_PREFIX = "jxp_00_legacy_bom_"
LEGACY_BOM_SERIES = {
    "jxp_daimyo_domain_missions": 1,
    "jxp_japan_eastasia_missions": 4,
    "jxp_kirishitan_deep_missions": 4,
    "jxp_shinto_branch_missions": 4,
}


def alias_file_name(series_name: str) -> str:
    return f"{FILE_PREFIX}{series_name.removeprefix('jxp_')}.txt"


def render_alias(series_name: str, slot: int) -> bytes:
    text = f"""{series_name} = {{
\tslot = {slot}
\tgeneric = no
\tai = no
\tpotential_on_load = {{ always = no }}
\tpotential = {{ always = no }}
}}
"""
    # EU4 1.37.5 serialized the leading BOM as part of the first mission-series
    # key. The byte prefix is intentional: it lets old saves resolve and evict
    # that bad key during the canonical delayed mission refresh.
    return b"\xef\xbb\xbf" + text.encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail without writing when an expected legacy alias has drifted",
    )
    args = parser.parse_args()

    mod_root = Path(__file__).resolve().parents[2]
    mission_root = mod_root / "missions"
    if not args.check:
        mission_root.mkdir(parents=True, exist_ok=True)
    drift: list[Path] = []
    for series_name, slot in sorted(LEGACY_BOM_SERIES.items()):
        target = mission_root / alias_file_name(series_name)
        payload = render_alias(series_name, slot)
        if args.check:
            if not target.is_file() or target.read_bytes() != payload:
                drift.append(target)
            continue
        target.write_bytes(payload)
        print(f"Created {target.name}: inactive BOM alias for {series_name}.")
    if drift:
        for target in drift:
            print(f"DRIFT: {target}")
        return 1
    if args.check:
        print(f"PASS: {len(LEGACY_BOM_SERIES)} legacy BOM aliases are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
