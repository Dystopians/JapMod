#!/usr/bin/env python3
"""Build or verify the complete Agent A socioeconomic content surface."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
BUILDERS = (
    "build_estates.py",
    "build_economy.py",
    "build_missions_routes.py",
    "build_integration.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-root",
        type=Path,
        required=True,
        help="EU4 1.37.5 installation used for the byte-pinned estate inputs",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    for name in BUILDERS:
        command = [sys.executable, str(HERE / name)]
        if name == "build_estates.py":
            command.extend(("--game-root", str(args.game_root)))
        if args.check:
            command.append("--check")
        completed = subprocess.run(command, check=False)
        if completed.returncode:
            print(f"ERROR: {name} failed with exit code {completed.returncode}", file=sys.stderr)
            return completed.returncode
    print(
        "PASS: socioeconomic authority is current"
        if args.check
        else "PASS: socioeconomic authority regenerated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
