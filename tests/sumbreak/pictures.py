"""Sumbreak boards drawn the way LinkedIn draws them, for boards bigger than
the one real screenshot.

Tiles are squares, or circles that grow with their number, in LinkedIn's
colours (read from its page's SVG), on its pale card. The numbers are in
Pillow's own font, so this checks finding the board and its cells more than
reading digits, which the real screenshots check.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from engines.sumbreak import Puzzle

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
BOARD = 384  # px across at scale 1, as on LinkedIn's 3x3 board
MARGIN = 200


def drawn(puzzle: Puzzle, circles: bool = False, scale: int = 1) -> Image.Image:
    """`puzzle` drawn on a page, at `scale` pixels per page pixel."""
    pitch = scale * BOARD / puzzle.cols
    side = 0.9 * pitch
    largest = max(n for row in puzzle.numbers for n in row if n is not None)
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
