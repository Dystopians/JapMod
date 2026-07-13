#!/usr/bin/env python3
"""Create pinned, old-save-safe EU4 1.37.5 Japanese mission overrides for JXP."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reflow_missions_v023 import matching_brace


OVERRIDE_FILES = ("Japanese_Missions.txt", "DOM_Japanese_Missions.txt")
EXCLUSION = "NOT = { jxp_use_custom_missions_trigger = yes }"
LOAD_DISABLE_MARKER = "# JXP_OVERRIDE_DISABLE_VANILLA_SERIES"
POTENTIAL_DISABLE_MARKER = "# JXP_OVERRIDE_DISABLE_VANILLA_POTENTIAL"
QUARANTINE_MARKER = "# JXP_OVERRIDE_TOMBSTONE_LEGACY_SERIES"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def top_level_blocks(text: str) -> tuple[tuple[str, int, int], ...]:
    pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)[ \t]*=[ \t]*\{")
    blocks: list[tuple[str, int, int]] = []
    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        closing = matching_brace(text, opening)
        blocks.append((match.group(1), match.start(), closing + 1))
    return tuple(blocks)


def add_exclusion(block: str, key: str) -> tuple[str, bool]:
    match = re.search(rf"(?m)^\t{re.escape(key)}[ \t]*=[ \t]*\{{", block)
    if match is None:
        return block, False
    opening = block.find("{", match.start(), match.end())
    closing = matching_brace(block, opening)
    if EXCLUSION in block[opening : closing + 1]:
        return block, False
    line_end = block.find("\n", opening)
    if line_end == -1:
        raise ValueError(f"{key} block is not multiline")
    insertion = f"\t\t{EXCLUSION}\n"
    return block[: line_end + 1] + insertion + block[line_end + 1 :], True


def disable_on_load(block: str) -> tuple[str, bool]:
    """Prevent a pinned vanilla series from entering the mission candidate pool.

    ``potential_on_load`` is evaluated without a country scope. A country-scoped
    scripted trigger placed there therefore cannot exclude the vanilla tree.
    JXP owns every Japanese/daimyo mission profile, so the pinned vanilla series
    must be disabled unconditionally at this global preload gate.
    """

    if LOAD_DISABLE_MARKER in block:
        return block, False

    match = re.search(r"(?m)^\tpotential_on_load[ \t]*=[ \t]*\{", block)
    if match is not None:
        opening = block.find("{", match.start(), match.end())
        line_end = block.find("\n", opening)
        if line_end == -1:
            raise ValueError("potential_on_load block is not multiline")
        insertion = f"\t\t{LOAD_DISABLE_MARKER}\n\t\talways = no\n"
        return block[: line_end + 1] + insertion + block[line_end + 1 :], True

    potential = re.search(r"(?m)^\tpotential[ \t]*=[ \t]*\{", block)
    if potential is None:
        raise ValueError("mission series has neither potential nor insertion point")
    insertion = (
        "\tpotential_on_load = {\n"
        f"\t\t{LOAD_DISABLE_MARKER}\n"
        "\t\talways = no\n"
        "\t}\n"
    )
    return block[: potential.start()] + insertion + block[potential.start() :], True


def disable_potential(block: str) -> tuple[str, bool]:
    """Keep replaced vanilla Japanese series false in country scope as well."""

    if POTENTIAL_DISABLE_MARKER in block:
        return block, False
    match = re.search(r"(?m)^\tpotential[ \t]*=[ \t]*\{", block)
    if match is None:
        raise ValueError("mission series has no potential block")
    opening = block.find("{", match.start(), match.end())
    line_end = block.find("\n", opening)
    if line_end == -1:
        raise ValueError("potential block is not multiline")
    insertion = f"\t\t{POTENTIAL_DISABLE_MARKER}\n\t\talways = no\n"
    return block[: line_end + 1] + insertion + block[line_end + 1 :], True


def retain_legacy_series_key(block: str, series_name: str) -> tuple[str, bool]:
    """Keep an inactive definition under the exact key serialized by old saves.

    ``swap_non_generic_missions`` can only reconcile a saved mission-series key
    when that key still resolves in the current mission registry.  Renaming the
    group strands the serialized series beside the replacement tree.
    """

    if QUARANTINE_MARKER in block:
        return block, False
    header = re.compile(rf"(?m)^{re.escape(series_name)}([ \t]*=[ \t]*\{{)")
    match = header.search(block)
    if match is None:
        raise ValueError(f"could not retain legacy mission series {series_name}")
    return block[: match.start()] + f"{QUARANTINE_MARKER}\n" + block[match.start() :], True


def route_legacy_mission_swaps(block: str) -> tuple[str, int]:
    """Keep legacy mission effects on the canonical delayed refresh path."""

    return re.subn(
        r"\bswap_non_generic_missions[ \t]*=[ \t]*yes\b",
        "jxp_refresh_route_missions_effect = yes",
        block,
    )


def patch_potentials(text: str, source_name: str) -> tuple[str, int]:
    updated = text
    inserted = 0
    for series_name, start, end in reversed(top_level_blocks(text)):
        block = updated[start:end]
        if re.search(r"(?m)^\tpotential[ \t]*=[ \t]*\{", block) is None:
            raise ValueError(
                f"top-level mission series {series_name} in {source_name} has no potential"
            )
        block, load_inserted = disable_on_load(block)
        block, potential_inserted = add_exclusion(block, "potential")
        block, country_disable_inserted = disable_potential(block)
        block, _ = retain_legacy_series_key(block, series_name)
        block, _ = route_legacy_mission_swaps(block)
        updated = updated[:start] + block + updated[end:]
        if load_inserted or potential_inserted or country_disable_inserted:
            inserted += 1
    return updated, inserted


def main() -> int:
    mod_root = Path(__file__).resolve().parents[2]
    game_root = Path(r"D:\Steam\steamapps\common\Europa Universalis IV")
    manifest_path = SCRIPT_DIR / "vanilla_1_37_5_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        Path(item["path"]).name: item["sha256"].casefold()
        for item in manifest["files"]
    }
    mission_root = (mod_root / "missions").resolve()
    total_groups = 0
    for file_name in OVERRIDE_FILES:
        source = (game_root / "missions" / file_name).resolve()
        target = (mission_root / file_name).resolve()
        if source.parent != (game_root / "missions").resolve():
            raise ValueError(f"source escaped mission directory: {source}")
        if target.parent != mission_root:
            raise ValueError(f"target escaped mod mission directory: {target}")
        if sha256(source) != expected.get(file_name):
            raise ValueError(f"vanilla source hash changed for {file_name}")
        text = source.read_text(encoding="utf-8-sig")
        patched, inserted = patch_potentials(text, file_name)
        if inserted == 0:
            raise ValueError(f"no mission groups patched in {file_name}")
        target.write_text(patched, encoding="utf-8", newline="")
        total_groups += inserted
        print(f"Created {target.name}: patched {inserted} mission-series potentials.")
    print(f"Created {len(OVERRIDE_FILES)} pinned overrides; patched_groups={total_groups}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
