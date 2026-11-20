"""Sumbreak boards drawn the way LinkedIn draws them, for boards bigger than
the one real screenshot.

Tiles are squares, or circles that grow with their number, in LinkedIn's
colours (read from its page's SVG), on its pale card. The numbers are in
Pillow's own font, so this checks finding the board and its cells more than
reading digits, which the real screenshots check.

A x2 tile is purple with "×2" in a greyish purple, as on sumbreak5.png: a
square with a pale diamond, or, in the look with circles, a starburst (only
seen on a result screen's icon, so its points are a guess). Pillow's font has
no ×, so it is drawn as two strokes.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

from engines.sumbreak import DOUBLE, Puzzle

PAGE = (244, 242, 238)
CARD = (248, 250, 253)
EMPTY = (233, 226, 220)  # an emptied square
# (tile, number) colours for 1, 2, 4, ... in turn; 1, 2, 4, 16, 32 and 64 are LinkedIn's
COLOURS = [
    ((152, 164, 255), (44, 54, 137)),
    ((103, 195, 255), (0, 77, 127)),
    ((54, 219, 255), (0, 93, 113)),
    ((240, 160, 255), (110, 40, 130)),
    ((163, 241, 154), (20, 110, 20)),
    ((218, 228, 113), (95, 102, 0)),
    ((245, 212, 95), (110, 92, 0)),
    ((255, 177, 97), (130, 70, 0)),
]
DOUBLE_TILE, DIAMOND, DOUBLE_INK = (214, 149, 255), (230, 191, 255), (87, 55, 94)  # read from sumbreak5.png
STAR_POINTS = 12
BOARD = 384  # px across at scale 1, as on LinkedIn's 3x3 board
MARGIN = 200


def drawn(puzzle: Puzzle, circles: bool = False, scale: int = 1, star: float | None = None) -> Image.Image:
    """`puzzle` drawn on a page, at `scale` pixels per page pixel. A starburst's
    points go in to `star` of its radius (0.85 if None)."""
    star = 0.85 if star is None else star
    pitch = scale * BOARD / puzzle.cols
    side = 0.9 * pitch
    largest = max(n for row in puzzle.numbers for n in row if n is not None and n != DOUBLE)
    width = round(2 * MARGIN * scale + BOARD * scale)
    page = Image.new("RGB", (width, width), PAGE)
    draw = ImageDraw.Draw(page)
    draw.rectangle((MARGIN * scale / 2, MARGIN * scale / 2, width - MARGIN * scale / 2, width - MARGIN * scale / 2), fill=CARD)
    font = ImageFont.load_default(size=max(10, round(0.18 * pitch)))
    for r, row in enumerate(puzzle.numbers):
        for c, number in enumerate(row):
            x, y = MARGIN * scale + (c + 0.5) * pitch, MARGIN * scale + (r + 0.5) * pitch
            if number is None:
                if not circles:
                    draw.rounded_rectangle(_box(x, y, side), radius=side / 15, fill=EMPTY)
                continue
            if number == DOUBLE:
                if circles:
                    draw.polygon(_star(x, y, 0.35 * pitch, star), fill=DOUBLE_TILE)
                else:
                    draw.rounded_rectangle(_box(x, y, side), radius=side / 15, fill=DOUBLE_TILE)
                    draw.regular_polygon((x, y, 0.38 * side), 4, rotation=45, fill=DIAMOND)
                _times_two(draw, x, y, font)
                continue
            fill, ink = COLOURS[(number.bit_length() - 1) % len(COLOURS)]
            if circles:  # from 0.4 of a cell across for 1 to 0.85 for the biggest number
                grown = (number.bit_length() - 1) / max(1, largest.bit_length() - 1)
                draw.ellipse(_box(x, y, pitch * (0.4 + 0.45 * grown)), fill=fill)
            else:
                draw.rounded_rectangle(_box(x, y, side), radius=side / 15, fill=fill)
            draw.text((x, y), str(number), fill=ink, font=font, anchor="mm")
    return page


def _box(x: float, y: float, side: float) -> tuple[float, float, float, float]:
    return x - side / 2, y - side / 2, x + side / 2, y + side / 2


def _star(x: float, y: float, radius: float, inner: float) -> list[tuple[float, float]]:
    """The corners of a starburst around (x, y), its points going in to `inner` of `radius`."""
    corners = []
    for k in range(2 * STAR_POINTS):
        reach = radius if k % 2 == 0 else inner * radius
        angle = math.pi * k / STAR_POINTS - math.pi / 2
        corners.append((x + reach * math.cos(angle), y + reach * math.sin(angle)))
    return corners


def _times_two(draw: ImageDraw.ImageDraw, x: float, y: float, font) -> None:
    """ "×2" around (x, y), the × 0.6 as tall as the 2, as LinkedIn prints it."""
    left, top, right, bottom = draw.textbbox((0, 0), "2", font=font, anchor="lt")
    width, height = right - left, bottom - top
    times = 0.6 * height
    start = x - (times + 0.5 * times + width) / 2
    two = start + 1.5 * times
    draw.text((two, y), "2", fill=DOUBLE_INK, font=font, anchor="lm")
    _, top, _, bottom = draw.textbbox((two, y), "2", font=font, anchor="lm")
    middle, stroke = (top + bottom) / 2, max(1, round(height / 8))
    for sign in (-1, 1):
        draw.line((start, middle - sign * times / 2, start + times, middle + sign * times / 2), fill=DOUBLE_INK, width=stroke)
