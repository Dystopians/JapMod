#!/usr/bin/env python3
"""Audit deployed JXP bytes and order-independent external compatibility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jxp_validation.playset import audit_active_playset


REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-data", required=True, type=Path)
    parser.add_argument("--game-root", required=True, type=Path)
    parser.add_argument("--dlc-load", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit_active_playset(
        args.user_data,
        args.game_root,
        REPO_ROOT / "japan_expanded_v2",
        REPO_ROOT / "japan_expanded_v2_map",
        args.dlc_load,
    )
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.summary)
        for issue in result.issues:
            print(f"ERROR [{issue.code}] {issue.source}: {issue.message}")
        for key, value in sorted(result.metrics.items()):
            print(f"{key}={value}")
    return 1 if result.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
