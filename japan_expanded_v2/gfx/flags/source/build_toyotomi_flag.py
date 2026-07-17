#!/usr/bin/env python3
"""Render the deterministic Toyotomi go-shichi-no-kiri flag assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


SOURCE_DIR = Path(__file__).resolve().parent
FLAG_DIR = SOURCE_DIR.parent
CANVAS = 1024
BACKGROUND = (72, 43, 91)
CREST = (239, 194, 73)
OUTLINE = (48, 29, 59)


def scaled_polygon(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]]) -> None:
    draw.polygon(points, fill=CREST, outline=OUTLINE, width=12)


def flower_cluster(
    draw: ImageDraw.ImageDraw,
    *,
    center_x: int,
    top_y: int,
    count: int,
    width: int,
) -> None:
    radius = 27
    for index in range(count):
        offset = index - (count - 1) / 2
        x = round(center_x + offset * width / max(count - 1, 1))
        y = round(top_y + abs(offset) * 9)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=CREST,
            outline=OUTLINE,
            width=9,
        )
    draw.rounded_rectangle(
        (center_x - 15, top_y + 23, center_x + 15, 535),
        radius=12,
        fill=CREST,
        outline=OUTLINE,
        width=7,
    )


def render() -> Image.Image:
    image = Image.new("RGB", (CANVAS, CANVAS), BACKGROUND)
    draw = ImageDraw.Draw(image)

    flower_cluster(draw, center_x=365, top_y=245, count=5, width=185)
    flower_cluster(draw, center_x=512, top_y=180, count=7, width=250)
    flower_cluster(draw, center_x=659, top_y=245, count=5, width=185)

    # Three paulownia leaves: a tall central leaf and two outward-facing leaves.
    scaled_polygon(
        draw,
        [
            (512, 495),
            (617, 585),
            (602, 795),
            (512, 895),
            (422, 795),
            (407, 585),
        ],
    )
    scaled_polygon(
        draw,
        [
            (466, 558),
            (385, 532),
            (262, 602),
            (197, 758),
            (333, 788),
            (458, 712),
        ],
    )
    scaled_polygon(
        draw,
        [
            (558, 558),
            (639, 532),
            (762, 602),
            (827, 758),
            (691, 788),
            (566, 712),
        ],
    )

    # Shallow veins keep the mon readable after EU4 downsizes the flag.
    for start, end in (
        ((512, 568), (512, 826)),
        ((430, 600), (252, 728)),
        ((594, 600), (772, 728)),
    ):
        draw.line((start, end), fill=OUTLINE, width=13)
    return image


def main() -> int:
    source = render()
    preview = source.resize((128, 128), Image.Resampling.LANCZOS)
    preview.save(SOURCE_DIR / "TOY_128_preview.png", format="PNG", optimize=True)
    preview.save(FLAG_DIR / "TOY.tga", format="TGA")
    print("Rendered TOY_128_preview.png and 128x128 24-bit TOY.tga")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
