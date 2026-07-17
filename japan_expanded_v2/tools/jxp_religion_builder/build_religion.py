#!/usr/bin/env python3
"""Build the pinned EU4 1.37.5 religion registry and Shinshu rebel type."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
RELIGION_RELATIVE = Path("common/religions/00_religion.txt")
REBEL_SOURCE_RELATIVE = Path("common/rebel_types/mahayana.txt")
REBEL_OUTPUT_RELATIVE = Path("common/rebel_types/jxp_a_95_jodo_shinshu.txt")
MANIFEST_PATH = SCRIPT_DIR / "generated_religion_manifest.json"

VANILLA_RELIGION_SHA256 = "609e2d235f3441c64b895d9faf3927bbf1399149cffa955137ab2d070b9645a6"
VANILLA_MAHAYANA_REBEL_SHA256 = "6069db79fd15ecdb7ac69495a3b99d8566a647534ffdf2e4c0838088f666b343"

JODO_BLOCK = """\
\tjodo_shinshu = {
\t\tcolor = { 176 102 153 }
\t\t# A12 remains runtime-gated. Reuse the pinned Mahayana frame until then.
\t\ticon = 23
\t\tallowed_conversion = {
\t\t\tmahayana
\t\t\tshinto
\t\t}
\t\tcountry = {
\t\t\ttolerance_heretic = 2
\t\t\tglobal_unrest = -1
\t\t\tproduction_efficiency = 0.05
\t\t}
\t\tcountry_as_secondary = {
\t\t\ttolerance_own = 1
\t\t\tglobal_manpower_modifier = 0.05
\t\t}
\t\ton_convert = {
\t\t\tadd_prestige = -100
\t\t\tadd_stability = -1
\t\t\tadd_country_modifier = {
\t\t\t\tname = "conversion_zeal"
\t\t\t\tduration = 3650
\t\t\t}
\t\t}

\t\tharmonized_modifier = harmonized_mahayana

\t\theretic = { IKKO }

\t\tuses_karma = yes
\t}

"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one pinned anchor, found {count}")
    return text.replace(old, new, 1)


def build_religion(vanilla: bytes) -> bytes:
    text = vanilla.decode("cp1252")
    nl = "\r\n" if "\r\n" in text else "\n"
    mahayana_anchor = (
        f"\t\tallowed_conversion = {{{nl}"
        f"\t\t\tvajrayana{nl}"
        f"\t\t\tbuddhism #Theravada{nl}"
        f"\t\t}}"
    )
    mahayana_replacement = (
        f"\t\tallowed_conversion = {{{nl}"
        f"\t\t\tvajrayana{nl}"
        f"\t\t\tbuddhism #Theravada{nl}"
        f"\t\t\tjodo_shinshu{nl}"
        f"\t\t}}"
    )
    text = replace_once(text, mahayana_anchor, mahayana_replacement, "Mahayana conversion bridge")
    text = replace_once(
        text,
        f"\tconfucianism = {{{nl}",
        JODO_BLOCK.replace("\n", nl) + f"\tconfucianism = {{{nl}",
        "Jodo Shinshu insertion",
    )
    confucian_anchor = (
        f"\tconfucianism = {{{nl}"
        f"\t\tcolor = {{ 214 229 140 }}{nl}"
        f"\t\ticon = 9{nl}"
        f"\t\tcountry = {{"
    )
    confucian_replacement = (
        f"\tconfucianism = {{{nl}"
        f"\t\tcolor = {{ 214 229 140 }}{nl}"
        f"\t\ticon = 9{nl}"
        f"\t\tallowed_center_conversion = {{{nl}"
        f"\t\t\tshinto{nl}"
        f"\t\t}}{nl}"
        f"\t\tcountry = {{"
    )
    text = replace_once(text, confucian_anchor, confucian_replacement, "Confucian incident bridge")
    return text.encode("cp1252")


def build_rebel(vanilla: bytes) -> bytes:
    text = vanilla.decode("cp1252")
    if text.count("mahayana") < 15:
        raise RuntimeError("Pinned Mahayana rebel source no longer has the expected religious surface")
    text = text.replace("Mahayana", "Jodo Shinshu").replace("mahayana", "jodo_shinshu")
    # Vanilla contains legacy trailing tabs/spaces.  Normalize them so the
    # generated file remains deterministic and clean when first added to Git.
    text = re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)
    return text.encode("cp1252")


def main() -> int:
    args = parse_args()
    game_root = args.game_root.resolve()
    religion_source = (game_root / RELIGION_RELATIVE).read_bytes()
    rebel_source = (game_root / REBEL_SOURCE_RELATIVE).read_bytes()
    actual_religion_hash = sha256(religion_source)
    actual_rebel_hash = sha256(rebel_source)
    if actual_religion_hash != VANILLA_RELIGION_SHA256:
        raise RuntimeError(
            f"Unsupported vanilla religion registry: {actual_religion_hash} != {VANILLA_RELIGION_SHA256}"
        )
    if actual_rebel_hash != VANILLA_MAHAYANA_REBEL_SHA256:
        raise RuntimeError(
            f"Unsupported Mahayana rebel source: {actual_rebel_hash} != {VANILLA_MAHAYANA_REBEL_SHA256}"
        )

    outputs = {
        RELIGION_RELATIVE: build_religion(religion_source),
        REBEL_OUTPUT_RELATIVE: build_rebel(rebel_source),
    }
    manifest = {
        "schema_version": 1,
        "eu4_version": "1.37.5.0",
        "vanilla_religion_sha256": VANILLA_RELIGION_SHA256,
        "vanilla_mahayana_rebel_sha256": VANILLA_MAHAYANA_REBEL_SHA256,
        "religion": "jodo_shinshu",
        "religion_group": "eastern",
        "uses_karma": True,
        "temporary_icon_frame": 23,
        "a12_custom_icon_status": "PENDING_RUNTIME_MILESTONE",
        "outputs": {str(path).replace("\\", "/"): sha256(data) for path, data in outputs.items()},
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")

    drift: list[str] = []
    for relative, expected in outputs.items():
        destination = MOD_ROOT / relative
        if args.check:
            if not destination.exists() or destination.read_bytes() != expected:
                drift.append(str(relative).replace("\\", "/"))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(expected)
    if args.check:
        if not MANIFEST_PATH.exists() or MANIFEST_PATH.read_bytes() != manifest_bytes:
            drift.append(str(MANIFEST_PATH.relative_to(MOD_ROOT)).replace("\\", "/"))
        if drift:
            raise RuntimeError("Generated religion drift: " + ", ".join(drift))
        print("Religion generator check passed: pinned 1.37.5 registry, Shinshu, and rebel type match")
    else:
        MANIFEST_PATH.write_bytes(manifest_bytes)
        print("Generated pinned religion registry and Jodo Shinshu rebel type")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
