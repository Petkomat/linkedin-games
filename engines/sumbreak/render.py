"""Sumbreak solutions as text, and drawn on the screenshot."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..common.text import board_text
from ..vision import ImageSource, open_image
from .model import Merge, Puzzle
from .ocr import Scan

ARROWS = {(0, 1): ">", (0, -1): "<", (1, 0): "v", (-1, 0): "^"}
ARROW_COLOR = (10, 102, 194)  # LinkedIn blue, on every colour of tile


def board_numbers(puzzle: Puzzle) -> str:
    """The board as read: each tile's number, right-aligned; . is an empty cell."""
    width = max(len(str(n)) for row in puzzle.numbers for n in row if n is not None)
    return board_text([[("." if n is None else str(n)).rjust(width) for n in row] for row in puzzle.numbers])


def solution_text(puzzle: Puzzle, merges: list[Merge]) -> str:
    """Each tile as the merge in which it is dragged away (1 is the first) and
    an arrow to the neighbour it goes onto; * is the tile left at the end."""
    cells = [["." if n is None else "*" for n in row] for row in puzzle.numbers]
    for step, merge in enumerate(merges, start=1):
        (r, c), (r2, c2) = merge.source, merge.target
        cells[r][c] = f"{step}{ARROWS[r2 - r, c2 - c]}"
    width = max(len(cell) for row in cells for cell in row)
    return board_text([[cell.rjust(width) for cell in row] for row in cells])


def render_solution(image: ImageSource, seen: Scan, merges: list[Merge]) -> Image.Image:
    """The screenshot with an arrow for every merge, from the tile dragged to
    the neighbour it goes onto, numbered in the order they are made."""
    out = open_image(image).convert("RGB")
    draw = ImageDraw.Draw(out)
    grid = seen.grid
    font = ImageFont.load_default(size=max(10, round(0.2 * grid.pitch)))
    width = max(2, round(0.04 * grid.pitch))
    for step, merge in enumerate(merges, start=1):
        (x0, y0), (x1, y1) = grid.center(*merge.source), grid.center(*merge.target)
        dx, dy = (x1 - x0) / grid.pitch, (y1 - y0) / grid.pitch  # one of them is 0, the other 1 or -1
        start = (x0 + 0.3 * dx * grid.pitch, y0 + 0.3 * dy * grid.pitch)
        tip = (x1 - 0.3 * dx * grid.pitch, y1 - 0.3 * dy * grid.pitch)
        draw.line((start, tip), fill=ARROW_COLOR, width=width)
        head = 0.12 * grid.pitch
        draw.polygon(
            [tip, (tip[0] - head * dx - head * dy / 2, tip[1] - head * dy - head * dx / 2),
             (tip[0] - head * dx + head * dy / 2, tip[1] - head * dy + head * dx / 2)],
            fill=ARROW_COLOR,
        )  # fmt: skip
        label = ((start[0] + tip[0]) / 2 + 0.12 * grid.pitch * dy, (start[1] + tip[1]) / 2 - 0.12 * grid.pitch * dx)
        draw.text(label, str(step), fill=ARROW_COLOR, font=font, anchor="mm", stroke_width=2, stroke_fill="white")
    return out
