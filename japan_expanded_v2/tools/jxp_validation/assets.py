"""Active localisation, custom sprite, and reform DDS validation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import struct

from .clausewitz import Object, Scalar, find_objects, first_scalar
from .core import CheckResult, ValidationContext


UTF8_BOM = b"\xef\xbb\xbf"
REFORM_SPRITE_PREFIX = "government_reform_jxp_"
REFORM_ICON_DIRECTORY = Path("gfx/interface/government_reform_icons")


@dataclass(frozen=True, slots=True)
class Sprite:
    name: str
    texture: str | None
    source: Path
    line: int


def _is_cjk(character: str) -> bool:
    codepoint = ord(character)
    return any(
        start <= codepoint <= end
        for start, end in (
            (0x1100, 0x11FF),  # Hangul Jamo
            (0x2E80, 0x303F),  # CJK radicals, symbols, punctuation
            (0x3040, 0x30FF),  # Hiragana and Katakana
            (0x3130, 0x318F),  # Hangul compatibility Jamo
            (0x31F0, 0x31FF),  # Katakana phonetic extensions
            (0x3400, 0x4DBF),  # CJK Extension A
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0xAC00, 0xD7AF),  # Hangul syllables
            (0xF900, 0xFAFF),  # CJK compatibility ideographs
            (0xFF65, 0xFF9F),  # Half-width Katakana
            (0x20000, 0x2FA1F),  # Supplementary CJK planes
        )
    )


def check_localisation(context: ValidationContext) -> CheckResult:
    result = CheckResult("Active localisation")
    localisation_root = context.mod_root / "localisation"
    files = (
        tuple(sorted(localisation_root.rglob("*.yml"), key=lambda path: context.relative(path).casefold()))
        if localisation_root.is_dir()
        else ()
    )
    if not files:
        result.add(
            "localisation.files_missing",
            "active localisation contains no .yml files",
            "localisation",
        )

    cjk_files = 0
    for source in files:
        data = source.read_bytes()
        relative = context.relative(source)
        if not data.startswith(UTF8_BOM):
            result.add(
                "localisation.bom",
                "active localisation file must begin with a UTF-8 BOM",
                relative,
            )
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            result.add(
                "localisation.encoding",
                f"active localisation is not valid UTF-8: {exc}",
                relative,
                exc.start + 1,
            )
            continue

        first_hit: tuple[int, int, str] | None = None
        for line_number, line in enumerate(text.splitlines(), start=1):
            for column, character in enumerate(line, start=1):
                if _is_cjk(character):
                    first_hit = (line_number, column, character)
                    break
            if first_hit is not None:
                break
        if first_hit is not None:
            cjk_files += 1
            line_number, column, character = first_hit
            result.add(
                "localisation.raw_cjk",
                f"raw CJK character U+{ord(character):04X} at column {column}",
                relative,
                line_number,
            )

    result.metrics.update({"files": len(files), "files_with_raw_cjk": cjk_files})
    result.summary = f"{len(files)} UTF-8-BOM active files; {cjk_files} with raw CJK"
    return result


def validate_reform_dds_bytes(data: bytes) -> tuple[str, ...]:
    """Return format/alpha errors for expected 57x57 RGBA DDS bytes."""

    errors: list[str] = []
    if len(data) < 128:
        return (f"DDS is only {len(data)} bytes; expected at least 128",)
    if data[:4] != b"DDS ":
        return ("missing DDS magic",)

    header_size = struct.unpack_from("<I", data, 4)[0]
    flags = struct.unpack_from("<I", data, 8)[0]
    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    pitch = struct.unpack_from("<I", data, 20)[0]
    pixel_format_size = struct.unpack_from("<I", data, 76)[0]
    pixel_flags = struct.unpack_from("<I", data, 80)[0]
    four_cc = data[84:88]
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    red_mask = struct.unpack_from("<I", data, 92)[0]
    green_mask = struct.unpack_from("<I", data, 96)[0]
    blue_mask = struct.unpack_from("<I", data, 100)[0]
    alpha_mask = struct.unpack_from("<I", data, 104)[0]

    if header_size != 124:
        errors.append(f"DDS header size is {header_size}; expected 124")
    if pixel_format_size != 32:
        errors.append(f"DDS pixel-format size is {pixel_format_size}; expected 32")
    if (width, height) != (57, 57):
        errors.append(f"dimensions are {width}x{height}; expected 57x57")

    data_offset = 128
    alpha_values: list[int] = []
    if four_cc == b"DX10":
        if len(data) < 148:
            errors.append("DX10 DDS header is truncated")
            return tuple(errors)
        dxgi_format = struct.unpack_from("<I", data, 128)[0]
        if dxgi_format not in {28, 29, 87, 91}:
            errors.append(f"DX10 format {dxgi_format} is not uncompressed RGBA/BGRA")
        data_offset = 148
        row_pitch = width * 4
        required_size = data_offset + row_pitch * height
        if len(data) < required_size:
            errors.append(
                f"pixel data is truncated ({len(data)} bytes; need at least {required_size})"
            )
        else:
            for row in range(height):
                start = data_offset + row * row_pitch
                alpha_values.extend(data[start + 3 : start + width * 4 : 4])
    else:
        if not (pixel_flags & 0x40):
            errors.append("pixel format is not RGB")
        if not (pixel_flags & 0x1):
            errors.append("pixel format does not declare alpha pixels")
        if pixel_flags & 0x4:
            errors.append(f"compressed/FourCC DDS format {four_cc!r} is not RGBA")
        if rgb_bits != 32:
            errors.append(f"RGB bit depth is {rgb_bits}; expected 32")
        masks = (red_mask, green_mask, blue_mask, alpha_mask)
        if any(mask == 0 for mask in masks):
            errors.append(
                "RGBA channel masks must all be nonzero "
                f"(R={red_mask:#x}, G={green_mask:#x}, B={blue_mask:#x}, A={alpha_mask:#x})"
            )
        combined = 0
        overlap = False
        for mask in masks:
            if combined & mask:
                overlap = True
            combined |= mask
        if overlap:
            errors.append("RGBA channel masks overlap")

        row_pitch = pitch if flags & 0x8 and pitch >= width * 4 else width * 4
        required_size = data_offset + row_pitch * height
        if len(data) < required_size:
            errors.append(
                f"pixel data is truncated ({len(data)} bytes; need at least {required_size})"
            )
        elif alpha_mask:
            shift = (alpha_mask & -alpha_mask).bit_length() - 1
            for row in range(height):
                row_start = data_offset + row * row_pitch
                for column in range(width):
                    pixel = struct.unpack_from("<I", data, row_start + column * 4)[0]
                    alpha_values.append((pixel & alpha_mask) >> shift)

    if alpha_values and not any(value > 0 for value in alpha_values):
        errors.append("alpha channel is blank (all pixels are fully transparent)")
    elif not alpha_values and not any("truncated" in error for error in errors):
        errors.append("could not read an alpha channel")
    return tuple(errors)


def validate_reform_dds(path: Path) -> tuple[str, ...]:
    """Return format/alpha errors for one expected 57x57 RGBA DDS file."""

    try:
        data = path.read_bytes()
    except OSError as exc:
        return (f"cannot read DDS: {exc}",)
    return validate_reform_dds_bytes(data)


def _collect_sprites(context: ValidationContext, result: CheckResult) -> tuple[Sprite, ...]:
    interface_root = context.mod_root / "interface"
    sprites: list[Sprite] = []
    if not interface_root.is_dir():
        result.add("sprite.interface_missing", "interface directory is missing", "interface")
        return ()

    for source in sorted(interface_root.rglob("*.gfx"), key=lambda path: context.relative(path).casefold()):
        document = context.document(source)
        if document is None:
            result.add(
                "sprite.gfx_parse",
                context.parse_errors.get(source.resolve(), "could not parse .gfx file"),
                context.relative(source),
            )
            continue
        for _path, entry in find_objects(document.root, "spriteType"):
            body = entry.value
            assert isinstance(body, Object)
            name = first_scalar(body, "name")
            if name is None:
                result.add(
                    "sprite.name_missing",
                    "spriteType has no scalar name",
                    context.relative(source),
                    entry.line,
                )
                continue
            sprites.append(Sprite(name, first_scalar(body, "texturefile"), source, entry.line))
    return tuple(sprites)


def _resolve_texture(context: ValidationContext, texture: str) -> Path | None:
    normalized = texture.replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or any(":" in part for part in pure.parts):
        return None
    candidate = context.mod_root.joinpath(*pure.parts).resolve()
    try:
        candidate.relative_to(context.mod_root)
    except ValueError:
        return None
    return candidate


def check_sprites_and_dds(context: ValidationContext) -> CheckResult:
    result = CheckResult("JXP sprites and reform DDS")
    sprites = _collect_sprites(context, result)
    sprites_by_name: dict[str, list[Sprite]] = defaultdict(list)
    for sprite in sprites:
        sprites_by_name[sprite.name].append(sprite)
    for name, declarations in sorted(sprites_by_name.items()):
        if len(declarations) > 1:
            first = declarations[0]
            for duplicate in declarations[1:]:
                result.add(
                    "sprite.duplicate",
                    f"sprite {name} is also declared at "
                    f"{context.relative(first.source)}:{first.line}",
                    context.relative(duplicate.source),
                    duplicate.line,
                )

    references: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    for occurrence in context.assignment_occurrences("icon"):
        if occurrence.value.startswith("GFX_jxp_"):
            references[occurrence.value].append((occurrence.source, occurrence.entry.line))
        elif (
            occurrence.value.startswith("jxp_")
            and occurrence.source.parent.name == "government_reforms"
        ):
            references[f"government_reform_{occurrence.value}"].append(
                (occurrence.source, occurrence.entry.line)
            )
    for name, locations in sorted(references.items()):
        if name not in sprites_by_name:
            for source, line in locations:
                result.add(
                    "sprite.reference_missing",
                    f"referenced JXP icon sprite {name} is not declared",
                    context.relative(source),
                    line,
                )

    custom_sprites = tuple(sprite for sprite in sprites if "jxp_" in sprite.name)
    reform_sprites = tuple(
        sprite for sprite in custom_sprites if sprite.name.startswith(REFORM_SPRITE_PREFIX)
    )
    if not reform_sprites:
        result.add(
            "sprite.reform_declarations_missing",
            "no government_reform_jxp_* sprites are declared",
            "interface",
        )

    resolved_textures: dict[str, Path] = {}
    for sprite in custom_sprites:
        if not sprite.texture:
            result.add(
                "sprite.texture_missing_field",
                f"custom sprite {sprite.name} has no texturefile",
                context.relative(sprite.source),
                sprite.line,
            )
            continue
        resolved = _resolve_texture(context, sprite.texture)
        if resolved is None:
            result.add(
                "sprite.texture_path",
                f"custom sprite {sprite.name} uses unsafe texture path {sprite.texture!r}",
                context.relative(sprite.source),
                sprite.line,
            )
            continue
        resolved_textures[sprite.name] = resolved
        if not resolved.is_file():
            result.add(
                "sprite.texture_file_missing",
                f"custom sprite {sprite.name} references missing texture "
                f"{context.relative(resolved)}",
                context.relative(sprite.source),
                sprite.line,
            )

    reform_directory = context.mod_root / REFORM_ICON_DIRECTORY
    actual_reform_dds = set(
        path.resolve() for path in reform_directory.glob("*.dds") if path.is_file()
    ) if reform_directory.is_dir() else set()
    declared_reform_dds = {
        resolved_textures[sprite.name]
        for sprite in reform_sprites
        if sprite.name in resolved_textures
        and resolved_textures[sprite.name].suffix.casefold() == ".dds"
    }
    for sprite in reform_sprites:
        resolved = resolved_textures.get(sprite.name)
        if resolved is not None and resolved.suffix.casefold() != ".dds":
            result.add(
                "sprite.reform_texture_type",
                f"reform sprite {sprite.name} must reference a DDS texture",
                context.relative(sprite.source),
                sprite.line,
            )

    reform_dds = actual_reform_dds | declared_reform_dds
    if not actual_reform_dds:
        result.add(
            "dds.reform_files_missing",
            "no reform DDS files exist directly in gfx/interface/government_reform_icons",
            REFORM_ICON_DIRECTORY.as_posix(),
        )
    for source in sorted(reform_dds, key=lambda path: context.relative(path).casefold()):
        if not source.is_file():
            continue
        for error in validate_reform_dds(source):
            result.add(
                "dds.reform_invalid",
                error,
                context.relative(source),
            )

    result.metrics.update(
        {
            "custom_sprite_declarations": len(custom_sprites),
            "referenced_custom_sprites": len(references),
            "reform_sprite_declarations": len(reform_sprites),
            "reform_dds_files": len(actual_reform_dds),
        }
    )
    result.summary = (
        f"{len(references)} referenced JXP sprites; {len(reform_sprites)} reform sprites; "
        f"{len(actual_reform_dds)} reform DDS files"
    )
    return result
