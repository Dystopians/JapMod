#!/usr/bin/env python3
"""Build the one-file JXP national-idea registry for EU4 1.37.5."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

try:
    from .reflow_missions_v023 import matching_brace
except ImportError:
    from reflow_missions_v023 import matching_brace


PINNED_VANILLA_SHA256 = "31e61848278c9756803124a95a5dc83257c198642607a2b27875fff9009fc6d3"
VANILLA_RELATIVE = Path("common/ideas/00_country_ideas.txt")
OUTPUT_RELATIVE = Path("common/ideas/00_country_ideas.txt")
SOURCE_FILENAMES = (
    "00_basic_z1_jxp_15_daimyo_ideas.txt",
    "00_basic_z2_jxp_17_minor_daimyo_ideas.txt",
    "00_basic_z3_jxp_18_remaining_daimyo_ideas.txt",
    "jxp_70_toyotomi_ideas.txt",
    "jxp_route_ideas.txt",
    "jxp_b_colonial_state_ideas.txt",
)
APPEND_SOURCE_FILENAMES = ("jxp_map_daimyo_ideas.txt",)
GENERATED_MARKER = "# JXP_CONSOLIDATED_NATIONAL_IDEA_REGISTRY_V1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_generated_text(text: str) -> str:
    """Keep generated Clausewitz text deterministic and diff-clean."""
    lines: list[str] = []
    for line in text.splitlines():
        clean = line.rstrip(" \t")
        indent = re.match(r"^[ \t]+", clean)
        if indent:
            clean = indent.group(0).expandtabs(4) + clean[indent.end() :]
        lines.append(clean)
    return "\n".join(lines) + "\n"


def top_level_blocks(text: str) -> tuple[tuple[str, int, int], ...]:
    pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)[ \t]*=[ \t]*\{")
    blocks: list[tuple[str, int, int]] = []
    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        closing = matching_brace(text, opening)
        blocks.append((match.group(1), match.start(), closing + 1))
    return tuple(blocks)


def _groups_from_files(
    source_root: Path,
    filenames: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    groups: list[tuple[str, str]] = []
    seen: set[str] = set()
    for filename in filenames:
        source = source_root / filename
        if not source.is_file():
            raise RuntimeError(f"Missing national-idea source: {source}")
        text = source.read_text(encoding="utf-8-sig")
        blocks = top_level_blocks(text)
        if not blocks:
            raise RuntimeError(f"National-idea source has no groups: {source}")
        for key, start, end in blocks:
            if not key.endswith("_ideas"):
                raise RuntimeError(f"Unexpected top-level key {key} in {source}")
            if key in seen:
                raise RuntimeError(f"Duplicate authored national-idea group: {key}")
            seen.add(key)
            groups.append((key, text[start:end].strip()))
    return tuple(groups)


def source_groups(source_root: Path) -> tuple[tuple[str, str], ...]:
    return _groups_from_files(source_root, SOURCE_FILENAMES)


def appended_source_groups(source_root: Path) -> tuple[tuple[str, str], ...]:
    """Groups kept at the registry tail so EU4 logs every companion ID."""

    return _groups_from_files(source_root, APPEND_SOURCE_FILENAMES)


def build_registry(game_root: Path, source_root: Path) -> bytes:
    vanilla_path = game_root / VANILLA_RELATIVE
    vanilla_bytes = vanilla_path.read_bytes()
    actual_sha = _sha256(vanilla_bytes)
    if actual_sha != PINNED_VANILLA_SHA256:
        raise RuntimeError(
            f"Pinned vanilla 00_country_ideas.txt hash mismatch: {actual_sha}"
        )
    vanilla = vanilla_bytes.decode("utf-8-sig")
    authored = source_groups(source_root)
    appended = appended_source_groups(source_root)
    authored_keys = [key for key, _block in (*authored, *appended)]
    if len(authored_keys) != len(set(authored_keys)):
        raise RuntimeError("Duplicate authored group across primary and companion sources")
    authored_ids = {key for key, _block in (*authored, *appended)}

    vanilla_blocks = top_level_blocks(vanilla)
    vanilla_ids = [key for key, _start, _end in vanilla_blocks]
    duplicate_vanilla = sorted(
        key for key in set(vanilla_ids) if vanilla_ids.count(key) != 1
    )
    if duplicate_vanilla:
        raise RuntimeError(
            "Pinned vanilla registry has duplicate groups: "
            + ", ".join(duplicate_vanilla)
        )

    stripped = vanilla
    for key, start, end in reversed(vanilla_blocks):
        if key in authored_ids:
            stripped = stripped[:start] + stripped[end:]

    authored_text = "\n\n".join(block for _key, block in authored)
    appended_text = "\n\n".join(block for _key, block in appended)
    header = (
        f"{GENERATED_MARKER}\n"
        "# Generated from the pinned vanilla registry plus JXP idea_sources.\n"
        "# Do not add a second runtime .txt file under common/ideas.\n\n"
    )
    rendered = _normalize_generated_text(
        header
        + authored_text
        + "\n\n"
        + stripped.lstrip("\ufeff\r\n")
        + "\n\n# JXP companion-map idea groups; keep this section last for runtime observability.\n"
        + appended_text
    )
    output_ids = [key for key, _start, _end in top_level_blocks(rendered)]
    if len(output_ids) != len(set(output_ids)):
        raise RuntimeError("Generated national-idea registry contains duplicate group IDs")
    missing = authored_ids - set(output_ids)
    if missing:
        raise RuntimeError("Generated registry lost authored groups: " + ", ".join(sorted(missing)))
    if rendered.startswith("\ufeff"):
        raise RuntimeError("Generated gameplay registry must be BOM-free")
    return rendered.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument(
        "--mod-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source_root = args.mod_root / "tools" / "jxp_validation" / "idea_sources"
    expected = build_registry(args.game_root, source_root)
    output = args.mod_root / OUTPUT_RELATIVE
    if args.check:
        if not output.is_file() or output.read_bytes() != expected:
            raise SystemExit(f"Consolidated national-idea registry is stale: {output}")
        print(f"Consolidated national-idea registry is current: {output}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(expected)
    print(
        f"Wrote {output} ({len(source_groups(source_root))} authored groups, "
        f"{len(appended_source_groups(source_root))} companion-tail groups, "
        f"{len(expected)} bytes, sha256={_sha256(expected)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
