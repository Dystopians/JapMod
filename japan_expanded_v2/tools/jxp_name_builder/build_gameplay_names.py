#!/usr/bin/env python3
"""Build canonical gameplay bytes for JXP route-country names."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
SOURCE_ROOT = SCRIPT_DIR / "source"
ENCODER_PATH = (
    MOD_ROOT.parent
    / "skills"
    / "eu4-modding"
    / "scripts"
    / "encode_eu4_special_gameplay.py"
)
ROUTE_COUNTRY_FILES = (
    "CJP - Confucian Wa.txt",
    "EJP - Yamato Court.txt",
    "IJP - Ikko Commonwealth.txt",
    "KJP - Kirishitan Japan.txt",
    "RFJ - Reformed Japan.txt",
    "SJP - Sultanate of Wa.txt",
    "WAK - Wokou Confederacy.txt",
)
COLONIAL_COUNTRY_FILES = (
    "HKK - Northern Star Sea Realm.txt",
    "NJF - Southern Japan Town Federation.txt",
    "NYA - New Yamato.txt",
    "OIA - Oceanic Island Alliance.txt",
    "TPF - Two Ocean Federation.txt",
)
COUNTRY_FILES_BY_DIRECTORY = {
    "history/countries": ROUTE_COUNTRY_FILES,
    "common/countries": ROUTE_COUNTRY_FILES + COLONIAL_COUNTRY_FILES,
}


def _load_encoder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_jxp_name_encoder", ENCODER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load gameplay-name encoder: {ENCODER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("encode_gameplay_text", "decode_gameplay_bytes"):
        if not callable(getattr(module, name, None)):
            raise RuntimeError(f"gameplay-name encoder lacks {name}")
    return module


def _pairs() -> tuple[tuple[Path, Path], ...]:
    pairs = []
    for directory, country_files in COUNTRY_FILES_BY_DIRECTORY.items():
        source_directory = SOURCE_ROOT / directory
        actual = {path.name for path in source_directory.glob("*.txt")}
        expected = set(country_files)
        if actual != expected:
            raise RuntimeError(
                f"{source_directory} has an unexpected source set: "
                f"missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}"
            )
        for name in country_files:
            pairs.append((source_directory / name, MOD_ROOT / directory / name))
    return tuple(pairs)


def build(*, check: bool) -> dict[str, object]:
    encoder = _load_encoder()
    mismatches: list[str] = []
    written = 0
    for source, active in _pairs():
        readable = source.read_bytes().decode("utf-8-sig")
        expected = encoder.encode_gameplay_text(readable)
        if expected.startswith(b"\xef\xbb\xbf"):
            raise RuntimeError(f"encoder produced a BOM: {source}")
        actual = active.read_bytes() if active.is_file() else None
        relative = active.relative_to(MOD_ROOT).as_posix()
        if actual != expected:
            mismatches.append(relative)
            if not check:
                active.parent.mkdir(parents=True, exist_ok=True)
                active.write_bytes(expected)
                written += 1
        if not check:
            round_trip = encoder.decode_gameplay_bytes(active.read_bytes())
            if round_trip != readable:
                raise RuntimeError(f"gameplay-name round trip failed: {relative}")
    result = {
        "schema": "jxp_gameplay_name_build/v1",
        "mode": "check" if check else "write",
        "source_files": len(_pairs()),
        "mismatches": mismatches,
        "written": written,
        "encoding": "EU4SpecialEscape-CP1252-no-BOM",
    }
    if check and mismatches:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(check=args.check), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
