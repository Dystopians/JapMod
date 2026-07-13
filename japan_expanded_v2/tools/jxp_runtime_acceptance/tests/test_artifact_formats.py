from __future__ import annotations

import base64
from hashlib import sha256
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib


TOOLS_ROOT = Path(__file__).resolve().parents[2]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from jxp_runtime_acceptance import runtime_acceptance as runtime


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _write_indexed_png_without_palette(path: Path) -> Path:
    width = height = 64
    scanlines = (b"\x00" + b"\x00" * width) * height
    path.write_bytes(
        b"".join(
            (
                b"\x89PNG\r\n\x1a\n",
                _png_chunk(
                    b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0)
                ),
                _png_chunk(b"IDAT", zlib.compress(scanlines)),
                _png_chunk(b"IEND", b""),
            )
        )
    )
    return path


_VALID_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8L"
    "CwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUF"
    "BQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4e"
    "Hh4eHh4eHh4eHh4eHh4eHh7/wAARCABAAEADASIAAhEBAxEB/8QAHwAAAQUBAQ"
    "EBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAA"
    "QRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NT"
    "Y3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJ"
    "WWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5u"
    "fo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8"
    "QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSM"
    "zUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGV"
    "mZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm"
    "6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEA"
    "PwDyGiiiv0A+HCiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiii"
    "gAooooAKKKKACiiigAooooAKKKKAP/Z"
)


def _jpeg_segment(marker: int, body: bytes) -> bytes:
    return b"\xff" + bytes((marker,)) + struct.pack(">H", len(body) + 2) + body


def _write_tableless_jpeg(path: Path) -> Path:
    frame = b"\x08" + struct.pack(">HH", 64, 64) + b"\x01\x01\x11\x00"
    scan = b"\x01\x01\x00\x00\x3f\x00"
    path.write_bytes(
        b"\xff\xd8"
        + _jpeg_segment(0xE0, b"spoof" * 12)
        + _jpeg_segment(0xC0, frame)
        + _jpeg_segment(0xDA, scan)
        + b"\x11" * 64
        + b"\xff\xd9"
    )
    return path


def _write_bmp(path: Path, bits_per_pixel: int) -> Path:
    width = height = 64
    row_stride = ((width * bits_per_pixel + 31) // 32) * 4
    pixels = bytes((20, 80, 140)) * width * height if bits_per_pixel == 24 else b"\x00" * (row_stride * height)
    pixel_offset = 54
    size = pixel_offset + len(pixels)
    header = (
        b"BM"
        + struct.pack("<IHHI", size, 0, 0, pixel_offset)
        + struct.pack(
            "<IiiHHIIiiII",
            40,
            width,
            height,
            1,
            bits_per_pixel,
            0,
            len(pixels),
            2835,
            2835,
            0,
            0,
        )
    )
    path.write_bytes(header + pixels)
    return path


def _write_rle_tga(path: Path) -> Path:
    width = height = 64
    header = struct.pack(
        "<BBBHHBHHHHBB",
        0,
        0,
        10,
        0,
        0,
        0,
        0,
        0,
        width,
        height,
        24,
        0,
    )
    packets = b"".join(b"\xff" + bytes((20, 80, 140)) for _ in range(32))
    path.write_bytes(header + packets)
    return path


def _structured_text_gamestate(marker: str) -> bytes:
    prefix = (
        'EU4txt\nplayers_countries={\n\t"Player"\n\t"JPN"\n}\n'
        "gameplaysettings={\n\tsetgameplayoptions={ 0 0 0 }\n}\n"
        "countries={\n\tJPN={\n\t\tcapital=1020\n\t}\n}\nfixture_data={\n"
    ).encode("ascii")
    payload = bytearray(prefix)
    counter = 0
    while len(payload) < 300 * 1024:
        digest = sha256(f"{marker}:{counter}".encode("utf-8")).hexdigest()
        payload.extend(f'\titem="{digest}"\n'.encode("ascii"))
        counter += 1
    payload.extend(b"}\n")
    return bytes(payload)


def _write_structured_eu4(path: Path) -> Path:
    meta = bytearray((
        "EU4txt\n"
        "date=1444.11.11\n"
        'save_game="fixture.eu4"\n'
        'player="JPN"\n'
        "savegame_version={\n"
        "\tfirst=1\n\tsecond=37\n\tthird=5\n\tforth=0\n\tname=\"Inca\"\n"
        "}\n"
        "dlc_enabled={\n\t\"Mandate of Heaven\"\n}\n"
        "meta_fixture={\n"
    ).encode("ascii"))
    counter = 0
    while len(meta) < 1024:
        digest = sha256(f"meta:{counter}".encode()).hexdigest()
        meta.extend(f'\titem="{digest}"\n'.encode("ascii"))
        counter += 1
    meta.extend(b"}\n")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("meta", bytes(meta))
        archive.writestr("gamestate", _structured_text_gamestate("valid"))
    return path


class ArtifactFormatTests(unittest.TestCase):
    def test_png_requires_palette_for_indexed_colour(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_indexed_png_without_palette(Path(temporary) / "indexed.png")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_image_artifact(path)

    def test_jpeg_requires_real_tables_and_full_decoder_accepts_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.jpg"
            valid.write_bytes(_VALID_JPEG)
            self.assertEqual("jpeg", runtime._validate_image_artifact(valid)["format"])
            spoof = _write_tableless_jpeg(root / "spoof.jpg")
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_image_artifact(spoof)

    def test_bmp_indexed_colour_requires_a_palette(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = _write_bmp(root / "valid.bmp", 24)
            self.assertEqual("bmp", runtime._validate_image_artifact(valid)["format"])
            spoof = _write_bmp(root / "missing-palette.bmp", 8)
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_image_artifact(spoof)

    def test_tga_rle_truecolour_is_decoded_to_the_exact_pixel_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_rle_tga(Path(temporary) / "valid-rle.tga")
            self.assertEqual("tga", runtime._validate_image_artifact(path)["format"])

    def test_eu4_text_tokens_and_zip_headers_do_not_authenticate_garbage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            text_spoof = root / "text-spoof.eu4"
            text_spoof.write_bytes(
                b"EU4txt\n" + b"x" * 2048 + b"date=1.1.1\nplayer=X\nsavegame_version={\n"
            )
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_eu4_save(text_spoof)

            zip_spoof = root / "zip-spoof.eu4"
            with zipfile.ZipFile(zip_spoof, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("meta", b"EU4bin" + b"m" * 512)
                archive.writestr("gamestate", b"EU4bin" + b"g" * 4096)
            with self.assertRaises(runtime.AcceptanceError):
                runtime._validate_eu4_save(zip_spoof)

    def test_structured_eu4_zip_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = _write_structured_eu4(Path(temporary) / "valid.eu4")
            self.assertEqual("eu4zip", runtime._validate_eu4_save(path)["format"])


if __name__ == "__main__":
    unittest.main()
