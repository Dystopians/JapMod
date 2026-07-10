#!/usr/bin/env python3
"""One-command entrypoint for the Japan Expanded 0.25.0 validation suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jxp_validation.assets import check_localisation, check_sprites_and_dds
from jxp_validation.compatibility import check_release_compatibility
from jxp_validation.core import (
    TARGET_VERSION,
    CheckResult,
    ValidationContext,
    check_metadata,
    check_script_parsing,
)
from jxp_validation.effective_topology import check_effective_topology
from jxp_validation.ideas import check_route_ideas
from jxp_validation.mission_refresh import check_mission_refresh
from jxp_validation.missions import check_missions
from jxp_validation.reforms import check_reforms
from jxp_validation.religion import check_confucian_bridge
from jxp_validation.shared_ledger import check_shared_development_ledger


def default_mod_root() -> Path:
    return Path(__file__).resolve().parents[2]


def auto_detect_game_root() -> Path | None:
    candidates = (
        Path(r"D:\Steam\steamapps\common\Europa Universalis IV"),
        Path.cwd(),
    )
    for candidate in candidates:
        if (
            (candidate / "launcher-settings.json").is_file()
            and (candidate / "missions").is_dir()
        ):
            return candidate.resolve()
    return None


def run_checks(
    mod_root: Path,
    game_root: Path,
    expected_version: str,
) -> tuple[CheckResult, ...]:
    context = ValidationContext(mod_root)
    return (
        check_metadata(context, expected_version),
        check_script_parsing(context),
        check_missions(context),
        check_mission_refresh(context),
        check_route_ideas(context, game_root),
        check_reforms(context),
        check_confucian_bridge(context),
        check_release_compatibility(context),
        check_localisation(context),
        check_sprites_and_dds(context),
        check_effective_topology(context, game_root),
        check_shared_development_ledger(context),
    )


def _location(source: str | None, line: int | None) -> str:
    if source is None:
        return ""
    return f"{source}:{line}" if line is not None else source


def print_text_report(
    mod_root: Path,
    game_root: Path,
    expected_version: str,
    results: Sequence[CheckResult],
    verbose: bool,
    max_details: int,
) -> None:
    print(f"Japan Expanded validation target {expected_version}")
    print(f"Mod root: {mod_root}")
    print(f"Game root: {game_root}")
    print()
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.summary}")
        visible_issues = result.issues if max_details == 0 else result.issues[:max_details]
        for issue in visible_issues:
            location = _location(issue.source, issue.line)
            prefix = f"  - {issue.code}"
            if location:
                prefix += f" [{location}]"
            print(f"{prefix}: {issue.message}")
        if max_details and len(result.issues) > max_details:
            print(f"  - ... {len(result.issues) - max_details} additional issue(s) hidden")
        if verbose:
            for note in result.notes:
                print(f"    {note}")

    failed_checks = sum(not result.passed for result in results)
    issue_count = sum(len(result.issues) for result in results)
    print()
    if failed_checks:
        print(
            f"FAILED: {failed_checks}/{len(results)} checks failed with "
            f"{issue_count} issue(s)."
        )
    else:
        print(f"PASS: all {len(results)} checks passed.")


def json_report(
    mod_root: Path,
    game_root: Path,
    expected_version: str,
    results: Sequence[CheckResult],
) -> dict[str, object]:
    return {
        "target_version": expected_version,
        "mod_root": str(mod_root),
        "game_root": str(game_root),
        "passed": all(result.passed for result in results),
        "failed_checks": sum(not result.passed for result in results),
        "issue_count": sum(len(result.issues) for result in results),
        "checks": [result.to_dict() for result in results],
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the staged Japan Expanded EU4 mod without modifying gameplay files."
    )
    parser.add_argument(
        "--mod-root",
        type=Path,
        default=default_mod_root(),
        help="mod root (defaults to the ancestor of this tools directory)",
    )
    parser.add_argument(
        "--expected-version",
        default=TARGET_VERSION,
        help=f"required descriptor version (default: {TARGET_VERSION})",
    )
    parser.add_argument(
        "--game-root",
        type=Path,
        default=None,
        help=(
            "EU4 1.37.5 game root; auto-detects "
            r"D:\Steam\steamapps\common\Europa Universalis IV when present"
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="include representative mission-profile occupancy summaries",
    )
    parser.add_argument(
        "--max-details",
        type=int,
        default=50,
        metavar="N",
        help="maximum issues printed per check; 0 prints all (default: 50)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    if args.max_details < 0:
        print("error: --max-details must be zero or positive", file=sys.stderr)
        return 2

    mod_root = args.mod_root.expanduser().resolve()
    required = (mod_root / "common", mod_root / "missions", mod_root / "descriptor.mod")
    if not mod_root.is_dir() or not all(path.exists() for path in required):
        print(f"error: {mod_root} does not look like a staged EU4 mod root", file=sys.stderr)
        return 2

    detected_game_root = args.game_root or auto_detect_game_root()
    if detected_game_root is None:
        print(
            "error: could not auto-detect the EU4 game root; pass --game-root",
            file=sys.stderr,
        )
        return 2
    game_root = detected_game_root.expanduser().resolve()
    if not (
        game_root.is_dir()
        and (game_root / "launcher-settings.json").is_file()
        and (game_root / "missions").is_dir()
    ):
        print(f"error: {game_root} does not look like an EU4 game root", file=sys.stderr)
        return 2

    try:
        results = run_checks(mod_root, game_root, args.expected_version)
    except Exception as exc:  # Defensive CLI boundary; validation issues should not traceback.
        print(f"error: validator crashed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                json_report(mod_root, game_root, args.expected_version, results),
                indent=2,
            )
        )
    else:
        print_text_report(
            mod_root,
            game_root,
            args.expected_version,
            results,
            args.verbose,
            args.max_details,
        )
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
