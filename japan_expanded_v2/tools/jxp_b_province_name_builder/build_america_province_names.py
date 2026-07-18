#!/usr/bin/env python3
"""Build Japanese-culture dynamic province names for the Americas."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import ModuleType
import unicodedata


SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
PLAN_PATH = SCRIPT_DIR / "america_japanese_names.json"
OUTPUT_RELATIVE = Path("common/province_names/japanese_g.txt")
SOURCE_RELATIVE = Path(
    "tools/jxp_b_province_name_builder/"
    "generated_japanese_g_america_utf8_source.txt"
)
ENCODER_PATH = (
    MOD_ROOT.parent
    / "skills"
    / "eu4-modding"
    / "scripts"
    / "encode_eu4_special_gameplay.py"
)
SCHEMA = "jxp_b_america_japanese_names/v2"
MARKER = "# JXP_B_AMERICAS_JAPANESE_NAMES_V2"
REGION_MARKER = "# JXP_REGION"
VALID_NAME = re.compile(r"^[A-Za-z][A-Za-z-]*$")
VALID_ROOT = re.compile(r"^[A-Z][A-Za-z]*$")
VALID_SUFFIX = re.compile(r"^[a-z]+$")
VALID_HAN_NAME = re.compile(r"^[\u3400-\u4DBF\u4E00-\u9FFF]+$")
VALID_KINDS = {
    "imperial_shorthand",
    "modern_exonym",
    "phonetic_exonym",
    "sengoku_foundation",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_id_hash(ids: list[int] | set[int]) -> str:
    payload = ",".join(str(value) for value in sorted(ids)).encode("ascii")
    return _sha256(payload)


def _load_encoder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_jxp_b_america_gameplay_encoder",
        ENCODER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load gameplay-name encoder: {ENCODER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("encode_gameplay_text", "decode_gameplay_bytes"):
        if not callable(getattr(module, name, None)):
            raise RuntimeError(f"Gameplay-name encoder lacks {name}")
    return module


def _load_plan(path: Path = PLAN_PATH) -> dict[str, object]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    return _validate_plan(plan, str(path))


def _validate_plan(
    plan: dict[str, object],
    source: str = "<in-memory America-name plan>",
) -> dict[str, object]:
    if plan.get("schema") != SCHEMA:
        raise RuntimeError(f"Unexpected America-name schema in {source}")

    pins = plan.get("pins")
    if not isinstance(pins, dict) or not pins:
        raise RuntimeError("America-name plan has no pinned game inputs")
    for relative, digest in pins.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise RuntimeError("America-name pins must be path/hash strings")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError(f"Invalid pinned SHA-256 for {relative}")

    expected = plan.get("expected_region_counts")
    regions = plan.get("regions")
    if not isinstance(expected, dict) or not isinstance(regions, dict):
        raise RuntimeError("America-name plan lacks region contracts")
    if list(expected) != list(regions):
        raise RuntimeError("Region order differs between counts and design blocks")
    if sum(expected.values()) != 778:
        raise RuntimeError("America-name plan must cover exactly 778 provinces")

    for key, region in regions.items():
        if not re.fullmatch(r"colonial_[a-z_]+", key):
            raise RuntimeError(f"Invalid colonial-region key: {key}")
        if not isinstance(region, dict):
            raise RuntimeError(f"Region design is not an object: {key}")
        roots = region.get("roots")
        han_roots = region.get("han_roots")
        suffixes = region.get("suffixes")
        han_suffixes = region.get("han_suffixes")
        if not all(
            isinstance(values, list)
            for values in (roots, han_roots, suffixes, han_suffixes)
        ):
            raise RuntimeError(f"Region has no naming grammar: {key}")
        assert isinstance(roots, list)
        assert isinstance(han_roots, list)
        assert isinstance(suffixes, list)
        assert isinstance(han_suffixes, list)
        if len(roots) != len(han_roots) or len(suffixes) != len(han_suffixes):
            raise RuntimeError(f"Region Roman/Han grammar is misaligned: {key}")
        if len(roots) != len(set(roots)) or len(suffixes) != len(set(suffixes)):
            raise RuntimeError(f"Region naming grammar is duplicated: {key}")
        if len(han_roots) != len(set(han_roots)) or len(han_suffixes) != len(
            set(han_suffixes)
        ):
            raise RuntimeError(f"Region Han naming grammar is duplicated: {key}")
        if not all(isinstance(root, str) and VALID_ROOT.fullmatch(root) for root in roots):
            raise RuntimeError(f"Region has an invalid name root: {key}")
        if not all(
            isinstance(suffix, str) and VALID_SUFFIX.fullmatch(suffix)
            for suffix in suffixes
        ):
            raise RuntimeError(f"Region has an invalid name suffix: {key}")
        if not all(
            isinstance(root, str) and VALID_HAN_NAME.fullmatch(root)
            for root in han_roots
        ):
            raise RuntimeError(f"Region has an invalid Han name root: {key}")
        if not all(
            isinstance(suffix, str) and VALID_HAN_NAME.fullmatch(suffix)
            for suffix in han_suffixes
        ):
            raise RuntimeError(f"Region has an invalid Han name suffix: {key}")
        if len(roots) * len(suffixes) < expected[key]:
            raise RuntimeError(f"Region name pool is smaller than its province set: {key}")

    preserved = plan.get("preserved_vanilla_ids")
    if not isinstance(preserved, list) or preserved != [893, 2021]:
        raise RuntimeError("Pinned vanilla New World name inheritance drifted")
    preserved_han = plan.get("preserved_han_names")
    if not isinstance(preserved_han, dict) or set(preserved_han) != {
        str(value) for value in preserved
    }:
        raise RuntimeError("Preserved New World names lack exact Han counterparts")
    if not all(
        isinstance(name, str) and VALID_HAN_NAME.fullmatch(name)
        for name in preserved_han.values()
    ):
        raise RuntimeError("Preserved New World Han names contain unsafe text")

    overrides = plan.get("overrides")
    if not isinstance(overrides, dict) or not overrides:
        raise RuntimeError("America-name plan has no curated exonyms")
    override_names: list[str] = []
    for raw_id, payload in overrides.items():
        if not raw_id.isdigit() or not isinstance(payload, dict):
            raise RuntimeError(f"Invalid curated override entry: {raw_id}")
        if set(payload) != {"name", "kind", "note"}:
            raise RuntimeError(f"Curated override fields drifted: {raw_id}")
        name = payload["name"]
        if not isinstance(name, str) or not VALID_NAME.fullmatch(name):
            raise RuntimeError(f"Invalid curated Japanese exonym: {raw_id}={name!r}")
        if payload["kind"] not in VALID_KINDS:
            raise RuntimeError(f"Invalid curated exonym class: {raw_id}")
        if not isinstance(payload["note"], str) or not payload["note"].strip():
            raise RuntimeError(f"Curated override lacks rationale: {raw_id}")
        override_names.append(name.casefold())
    duplicates = [name for name, count in Counter(override_names).items() if count > 1]
    if duplicates:
        raise RuntimeError(f"Curated Japanese exonyms are duplicated: {duplicates}")
    curated_han = plan.get("curated_han_names")
    if not isinstance(curated_han, dict) or set(curated_han) != set(overrides):
        raise RuntimeError("Curated Japanese exonyms lack exact Han counterparts")
    if not all(
        isinstance(name, str) and VALID_HAN_NAME.fullmatch(name)
        for name in curated_han.values()
    ):
        raise RuntimeError("Curated Han exonyms contain unsafe text")
    all_explicit_han = list(preserved_han.values()) + list(curated_han.values())
    if len(all_explicit_han) != len(set(all_explicit_han)):
        raise RuntimeError("Explicit Han exonyms are duplicated")
    return plan


def _matching_brace(text: str, opening: int) -> int:
    depth = 0
    quoted = False
    commented = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if commented:
            if char in "\r\n":
                commented = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == "#":
            commented = True
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
            if depth < 0:
                break
    raise RuntimeError(f"Unmatched opening brace at offset {opening}")


def _colonial_regions(text: str) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    pattern = re.compile(r"^(colonial_[a-z_]+)\s*=\s*\{", re.MULTILINE)
    for match in pattern.finditer(text):
        key = match.group(1)
        opening = text.find("{", match.start(), match.end())
        block = text[opening : _matching_brace(text, opening) + 1]
        provinces_match = re.search(
            r"^\s*provinces\s*=\s*\{",
            block,
            flags=re.MULTILINE,
        )
        if provinces_match is None:
            raise RuntimeError(f"Colonial region has no province block: {key}")
        provinces_opening = block.find(
            "{",
            provinces_match.start(),
            provinces_match.end(),
        )
        provinces_closing = _matching_brace(block, provinces_opening)
        body = block[provinces_opening + 1 : provinces_closing]
        uncommented = "\n".join(line.split("#", 1)[0] for line in body.splitlines())
        ids = [int(value) for value in re.findall(r"\b\d+\b", uncommented)]
        if not ids or len(ids) != len(set(ids)):
            raise RuntimeError(f"Colonial region is empty or repeats IDs: {key}")
        result[key] = ids
    return result


def _localised_province_names(paths: list[Path]) -> dict[int, str]:
    names: dict[int, str] = {}
    pattern = re.compile(r'^\s*PROV(\d+):\d+\s+"([^"]*)"', re.MULTILINE)
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        for match in pattern.finditer(text):
            names[int(match.group(1))] = match.group(2)
    return names


def _ascii_comment(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = decomposed.encode("ascii", errors="ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.replace("#", "")).strip() or "Province"


def _replace_direct_name(text: str, province_id: int, han_name: str) -> str:
    pattern = re.compile(
        rf'^(?P<prefix>\s*{province_id}\s*=\s*)"[^"]+"',
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one direct Japanese name for province {province_id}, "
            f"found {len(matches)}"
        )
    return pattern.sub(
        lambda match: f'{match.group("prefix")}"{han_name}"',
        text,
        count=1,
    )


def _candidate_pool(region: dict[str, object]) -> list[tuple[str, str]]:
    roots = region["roots"]
    han_roots = region["han_roots"]
    suffixes = region["suffixes"]
    han_suffixes = region["han_suffixes"]
    assert isinstance(roots, list)
    assert isinstance(han_roots, list)
    assert isinstance(suffixes, list)
    assert isinstance(han_suffixes, list)
    return [
        (f"{root}{suffix}", f"{han_root}{han_suffix}")
        for root, han_root in zip(roots, han_roots, strict=True)
        for suffix, han_suffix in zip(suffixes, han_suffixes, strict=True)
    ]


def _allocate_generated_name(
    region_key: str,
    province_id: int,
    candidates: list[tuple[str, str]],
    used: set[str],
) -> tuple[str, str]:
    digest = hashlib.sha256(f"{region_key}:{province_id}".encode("ascii")).digest()
    start = int.from_bytes(digest[:8], "big") % len(candidates)
    for offset in range(len(candidates)):
        candidate = candidates[(start + offset) % len(candidates)]
        if candidate[0].casefold() not in used:
            used.add(candidate[0].casefold())
            return candidate
    raise RuntimeError(f"Japanese name pool exhausted for {region_key}")


def _verify_pins(game_root: Path, plan: dict[str, object]) -> dict[str, bytes]:
    pins = plan["pins"]
    assert isinstance(pins, dict)
    payloads: dict[str, bytes] = {}
    for relative, expected in pins.items():
        path = game_root / relative
        if not path.is_file():
            raise RuntimeError(f"Pinned EU4 input is missing: {path}")
        payload = path.read_bytes()
        actual = _sha256(payload)
        if actual != expected:
            raise RuntimeError(
                f"Pinned EU4 input drifted: {relative} expected={expected} actual={actual}"
            )
        payloads[relative] = payload
    return payloads


def build_artifacts(
    game_root: Path,
    *,
    plan_path: Path = PLAN_PATH,
) -> tuple[str, bytes, dict[str, object]]:
    plan = _load_plan(plan_path)
    payloads = _verify_pins(game_root, plan)
    vanilla = payloads["common/province_names/japanese_g.txt"]
    colonial_text = payloads[
        "common/colonial_regions/00_colonial_regions.txt"
    ].decode("cp1252")
    available_regions = _colonial_regions(colonial_text)

    expected_counts = plan["expected_region_counts"]
    region_designs = plan["regions"]
    preserved = set(plan["preserved_vanilla_ids"])
    preserved_han = plan["preserved_han_names"]
    overrides = plan["overrides"]
    curated_han = plan["curated_han_names"]
    assert isinstance(expected_counts, dict)
    assert isinstance(region_designs, dict)
    assert isinstance(preserved_han, dict)
    assert isinstance(overrides, dict)
    assert isinstance(curated_han, dict)

    region_ids: dict[str, list[int]] = {}
    all_america_ids: list[int] = []
    for key, expected_count in expected_counts.items():
        ids = available_regions.get(key)
        if ids is None:
            raise RuntimeError(f"Pinned colonial region disappeared: {key}")
        if len(ids) != expected_count:
            raise RuntimeError(
                f"Pinned colonial region count drifted: {key}={len(ids)} "
                f"expected={expected_count}"
            )
        region_ids[key] = ids
        all_america_ids.extend(ids)
    if len(all_america_ids) != len(set(all_america_ids)):
        raise RuntimeError("American colonial regions overlap province IDs")
    if _canonical_id_hash(all_america_ids) != plan["america_id_set_sha256"]:
        raise RuntimeError("Pinned American colonial province set drifted")

    vanilla_text = vanilla.decode("cp1252")
    vanilla_ids = {
        int(value)
        for value in re.findall(r"^\s*(\d+)\s*=", vanilla_text, flags=re.MULTILINE)
    }
    inherited = vanilla_ids.intersection(all_america_ids)
    if inherited != preserved:
        raise RuntimeError(
            f"Vanilla Japanese New World inheritance drifted: {sorted(inherited)}"
        )

    added_ids = set(all_america_ids) - preserved
    if _canonical_id_hash(added_ids) != plan["added_id_set_sha256"]:
        raise RuntimeError("Generated American province set drifted")

    localisation_paths = [
        game_root / "localisation/prov_names_l_english.yml",
        game_root / "localisation/north_america_redone_l_english.yml",
    ]
    base_names = _localised_province_names(localisation_paths)
    missing_base_names = sorted(set(all_america_ids) - set(base_names))
    if missing_base_names:
        raise RuntimeError(
            f"Pinned English province names are incomplete: {missing_base_names}"
        )

    override_ids = {int(value) for value in overrides}
    invalid_override_ids = sorted(override_ids - added_ids)
    if invalid_override_ids:
        raise RuntimeError(
            f"Curated overrides are outside generated America IDs: {invalid_override_ids}"
        )

    quoted_vanilla_names = {
        value.casefold() for value in re.findall(r'"([^"]+)"', vanilla_text)
    }
    override_names = {
        payload["name"].casefold() for payload in overrides.values()
    }
    collisions = sorted(quoted_vanilla_names.intersection(override_names))
    if collisions:
        raise RuntimeError(f"Curated exonyms collide with vanilla names: {collisions}")
    used_names = quoted_vanilla_names | override_names

    assigned_roman: dict[int, str] = {}
    assigned_han: dict[int, str] = {}
    used_han = set(preserved_han.values()) | set(curated_han.values())
    generated_count = 0
    override_count = 0
    for key, ids in region_ids.items():
        candidates = _candidate_pool(region_designs[key])
        for province_id in ids:
            if province_id in preserved:
                continue
            override = overrides.get(str(province_id))
            if override is not None:
                assigned_roman[province_id] = override["name"]
                assigned_han[province_id] = curated_han[str(province_id)]
                override_count += 1
                continue
            roman_name, han_name = _allocate_generated_name(
                key,
                province_id,
                candidates,
                used_names,
            )
            if han_name in used_han:
                raise RuntimeError(
                    f"Generated Han exonym is duplicated: {province_id}={han_name}"
                )
            used_han.add(han_name)
            assigned_roman[province_id] = roman_name
            assigned_han[province_id] = han_name
            generated_count += 1

    if set(assigned_roman) != added_ids or set(assigned_han) != added_ids:
        raise RuntimeError("Japanese America assignment lost or added province IDs")
    if len({name.casefold() for name in assigned_roman.values()}) != len(
        assigned_roman
    ):
        raise RuntimeError("Japanese America assignment repeats display names")
    if any(not VALID_NAME.fullmatch(name) for name in assigned_roman.values()):
        raise RuntimeError("Japanese America assignment contains unsafe text")
    all_han_names = {
        int(province_id): name for province_id, name in preserved_han.items()
    }
    all_han_names.update(assigned_han)
    if set(all_han_names) != set(all_america_ids):
        raise RuntimeError("Han America assignment lost or added province IDs")
    if len(set(all_han_names.values())) != len(all_han_names):
        raise RuntimeError("Han America assignment repeats display names")
    if any(not VALID_HAN_NAME.fullmatch(name) for name in all_han_names.values()):
        raise RuntimeError("Han America assignment contains unsafe text")

    readable_vanilla = vanilla_text
    for raw_id, han_name in preserved_han.items():
        readable_vanilla = _replace_direct_name(
            readable_vanilla,
            int(raw_id),
            han_name,
        )
    newline = "\r\n" if "\r\n" in vanilla_text else "\n"
    lines = [
        MARKER,
        "# Generated from pinned EU4 1.37.5 colonial-region IDs.",
        "# Han names preserve Sengoku-Edo foundations and later imperial shorthand.",
        "# Active bytes use BOM-free EU4SpecialEscape for the Chinese patch.",
        "# Edit the UTF-8 JSON plan and rebuild; do not hand-edit this registry.",
        "",
    ]
    for key, ids in region_ids.items():
        inherited_count = sum(province_id in preserved for province_id in ids)
        added_count = len(ids) - inherited_count
        lines.append(
            f"{REGION_MARKER} {key} total={len(ids)} "
            f"inherited={inherited_count} added={added_count}"
        )
        for province_id in ids:
            if province_id in preserved:
                continue
            comment = _ascii_comment(base_names[province_id])
            lines.append(
                f'{province_id} = "{assigned_han[province_id]}"\t'
                f'# JPN {assigned_roman[province_id]} | {comment}'
            )
        lines.append("")
    readable_source = (
        readable_vanilla.rstrip("\r\n")
        + newline
        + newline
        + newline.join(lines)
    )
    encoder = _load_encoder()
    output = encoder.encode_gameplay_text(readable_source)
    if output.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError("Gameplay province-name output must not carry a UTF-8 BOM")
    if encoder.decode_gameplay_bytes(output) != readable_source:
        raise RuntimeError("Gameplay province-name EU4SpecialEscape round-trip failed")

    kind_counts = Counter(payload["kind"] for payload in overrides.values())
    stats: dict[str, object] = {
        "schema": "jxp_b_america_province_name_build/v2",
        "game_version": plan["game_version"],
        "regions": len(region_ids),
        "american_provinces": len(all_america_ids),
        "inherited_vanilla": len(preserved),
        "curated_exonyms": override_count,
        "generated_regional_names": generated_count,
        "added_entries": len(assigned_han),
        "han_names": len(all_han_names),
        "curated_kinds": dict(sorted(kind_counts.items())),
        "encoding": "EU4SpecialEscape-CP1252-no-BOM",
        "source_sha256": _sha256(readable_source.encode("utf-8")),
        "source_bytes": len(readable_source.encode("utf-8")),
        "output_sha256": _sha256(output),
        "output_bytes": len(output),
    }
    return readable_source, output, stats


def build_output(
    game_root: Path,
    *,
    plan_path: Path = PLAN_PATH,
) -> tuple[bytes, dict[str, object]]:
    _, output, stats = build_artifacts(game_root, plan_path=plan_path)
    return output, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--mod-root", type=Path, default=MOD_ROOT)
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source_text, expected, stats = build_artifacts(
        args.game_root,
        plan_path=args.plan,
    )
    output = args.mod_root / OUTPUT_RELATIVE
    source_output = args.mod_root / SOURCE_RELATIVE
    expected_source = source_text.encode("utf-8")
    if args.check:
        if not output.is_file() or output.read_bytes() != expected:
            raise SystemExit(f"Japanese America province-name registry is stale: {output}")
        if not source_output.is_file() or source_output.read_bytes() != expected_source:
            raise SystemExit(
                f"Japanese America readable name source is stale: {source_output}"
            )
        mode = "check"
        written = 0
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        source_output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(expected)
        source_output.write_bytes(expected_source)
        mode = "write"
        written = 2

    stats.update(
        {
            "mode": mode,
            "output": output.as_posix(),
            "source_output": source_output.as_posix(),
            "written": written,
        }
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
