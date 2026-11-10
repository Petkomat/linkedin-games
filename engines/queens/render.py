"""Draw a Queens solution on top of the original screenshot."""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..common.text import board_text, letter
from ..vision import ImageSource, open_image
from .model import Cell, Puzzle
from .ocr import Scan

QUEEN_COLOR = (10, 102, 194)  # blue, so placed queens stand out from black ones


def render_solution(image: ImageSource, seen: Scan, queens: list[Cell]) -> Image.Image:
    """Return the screenshot with a crown drawn on every queen's cell."""
    out = open_image(image).convert("RGB")
    draw = ImageDraw.Draw(out)
    for row, col in queens:
        draw.polygon(_crown(seen.grid.box(row, col, inset=0.25)), fill=QUEEN_COLOR)
    return out


def regions_text(puzzle: Puzzle) -> str:
    return board_text([[letter(label) for label in row] for row in puzzle.regions])


def solution_text(puzzle: Puzzle, queens: list[Cell]) -> str:
    """The region map in lower case with each queen as a capital Q."""
    rows = [[letter(label).lower() for label in row] for row in puzzle.regions]
    for r, c in queens:
        rows[r][c] = "Q"
    return board_text(rows)


def _crown(box: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    """Outline of a three-pointed crown filling `box`."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    points = [(0, 1), (0, 0.15), (0.25, 0.55), (0.5, 0), (0.75, 0.55), (1, 0.15), (1, 1)]
    return [(x0 + px * w, y0 + py * h) for px, py in points]
