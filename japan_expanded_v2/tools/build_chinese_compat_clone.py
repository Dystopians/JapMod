#!/usr/bin/env python3
"""Build or audit the local Chinese supplementary compatibility clone."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jxp_validation.chinese_compat import audit_compat_clone, build_compat_clone


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENCODER = REPO_ROOT / "skills/eu4-modding/scripts/encode_eu4_special_gameplay.py"
DEFAULT_LOCALISATION_ENCODER = (
    REPO_ROOT / "skills/eu4-modding/scripts/escape_eu4_special_localisation.py"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--outer-descriptor", required=True, type=Path)
    parser.add_argument("--main-mod", required=True, type=Path)
    parser.add_argument("--map-mod", required=True, type=Path)
    parser.add_argument("--game-root", required=True, type=Path)
    parser.add_argument("--encoder-script", type=Path, default=DEFAULT_ENCODER)
    parser.add_argument(
        "--localisation-encoder-script",
        type=Path,
        default=DEFAULT_LOCALISATION_ENCODER,
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        result = audit_compat_clone(
            args.source,
            args.target,
            args.outer_descriptor,
            args.main_mod,
            args.map_mod,
            args.game_root,
            args.encoder_script,
            args.localisation_encoder_script,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 1 if result.issues else 0
    result = build_compat_clone(
        args.source,
        args.target,
        args.outer_descriptor,
        args.main_mod,
        args.map_mod,
        args.game_root,
        args.encoder_script,
        args.localisation_encoder_script,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
