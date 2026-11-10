"""Draw a Tango solution on top of the original screenshot."""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..common.text import board_text
from ..vision import ImageSource, open_image
from .model import Grid, Puzzle, Symbol
from .ocr import Scan

# Lighter than the givens, so the filled-in cells stand out.
SUN_COLOR = (255, 200, 90)
MOON_COLOR = (120, 160, 235)
CELL_COLOR = (255, 255, 255)  # non-given cells are white
# Wipes the player's own symbol but stays clear of the signs on the borders.
WIPE_INSET = 0.18


def render_solution(image: ImageSource, seen: Scan, solution: Grid) -> Image.Image:
    """Return the screenshot with a sun or moon drawn in every cell that is not given.

    Whatever the player had already placed there is wiped first.
    """
    out = open_image(image).convert("RGB")
    draw = ImageDraw.Draw(out)
    for r, row in enumerate(solution):
        for c, symbol in enumerate(row):
            if seen.puzzle.givens[r][c] is None:
                draw.rectangle(seen.grid.box(r, c, inset=WIPE_INSET), fill=CELL_COLOR)
                box = tuple(round(v) for v in seen.grid.box(r, c, inset=0.3))
                _draw_symbol(out, box, symbol)
    return out


def grid_text(grid: Grid) -> str:
    return board_text([["." if s is None else s.value for s in row] for row in grid])


def puzzle_text(puzzle: Puzzle) -> str:
    """The givens, with each '=' / 'x' sign drawn between the two cells it joins."""

    def sign(a: tuple[int, int], b: tuple[int, int]) -> str | None:
        edge = frozenset((a, b))
        if edge in puzzle.equal:
            return "="
        if edge in puzzle.opposite:
            return "x"
        return None

    n = puzzle.size
    lines = []
    for r, row in enumerate(puzzle.givens):
        cells = ["." if s is None else s.value for s in row]
        lines.append(
            cells[0] + "".join((sign((r, c - 1), (r, c)) or " ") + cells[c] for c in range(1, n))
        )
        if r + 1 < n:
            between = " ".join(sign((r, c), (r + 1, c)) or " " for c in range(n)).rstrip()
            if between:
                lines.append(between)
    return "\n".join(lines)


def _draw_symbol(image: Image.Image, box: tuple[int, ...], symbol: Symbol) -> None:
    x0, y0, x1, y1 = box
    if symbol is Symbol.SUN:
        ImageDraw.Draw(image).ellipse(box, fill=SUN_COLOR)
        return
    # Moon: a disc with an offset disc cut out of it.
    w, h = x1 - x0, y1 - y0
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, w - 1, h - 1), fill=255)
    draw.ellipse((w // 3, -h // 6, w + w // 3, h - h // 6), fill=0)
    image.paste(Image.new("RGB", (w, h), MOON_COLOR), (x0, y0), mask)
