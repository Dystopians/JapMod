#!/usr/bin/env python3
"""Generate one static review page from the main JXP mod plus this map overlay."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
COMPANION_ROOT = SCRIPT_DIR.parents[1]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-mod", type=Path, required=True)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--companion-mod", type=Path, default=COMPANION_ROOT)
    parser.add_argument("--output", type=Path, default=SCRIPT_DIR / "jxp_combined_visualizer.html")
    return parser.parse_args()


def copy_overlay(source_root: Path, target_root: Path):
    folders = [
        "missions", "decisions", "events", "localisation_source",
        "common/scripted_effects", "common/scripted_triggers", "common/event_modifiers",
    ]
    for relative in folders:
        source = source_root / relative
        if source.exists():
            shutil.copytree(source, target_root / relative, dirs_exist_ok=True)


def load_generator(path: Path):
    spec = importlib.util.spec_from_file_location("jxp_visualizer_generator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    args = parse_args()
    main_mod = args.main_mod.resolve()
    companion = args.companion_mod.resolve()
    game_root = args.game_root.resolve()
    generator_path = main_mod / "tools" / "jxp_visualizer" / "generate_visualizer.py"
    if not generator_path.exists():
        raise RuntimeError(f"Main visualizer generator is missing: {generator_path}")
    generator = load_generator(generator_path)
    with tempfile.TemporaryDirectory(prefix="jxp_combined_visualizer_") as temporary:
        staging = Path(temporary)
        copy_overlay(main_mod, staging)
        copy_overlay(companion, staging)
        data = generator.build_data(staging, game_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(generator.html_page(data), encoding="utf-8", newline="\r\n")
    print(f"Wrote {args.output}")
    print(
        f"Counts: {data['counts']['missionGroups']} mission groups, "
        f"{data['counts']['missions']} missions, {data['counts']['decisions']} decisions, "
        f"{data['counts']['events']} events, {data['counts']['missingLocalisation']} missing localisation keys"
    )
    if data["warnings"]:
        print("Warnings:")
        for warning in data["warnings"]:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
