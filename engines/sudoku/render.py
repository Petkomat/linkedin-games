"""Draw a sudoku solution on top of the original screenshot."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..vision import ImageSource, open_image
from .model import Grid
from .ocr import Scan

FILL_COLOR = (10, 102, 194)  # blue, so the filled-in digits stand out from the givens


def render_solution(image: ImageSource, seen: Scan, solution: Grid) -> Image.Image:
    """Return the screenshot with every empty cell filled in."""
    out = open_image(image).convert("RGB")
    draw = ImageDraw.Draw(out)
    font = ImageFont.load_default(size=round(0.45 * seen.grid.pitch))
    for r, row in enumerate(solution):
        for c, digit in enumerate(row):
            if seen.puzzle.grid[r][c]:
                continue
            draw.text(seen.grid.center(r, c), str(digit), fill=FILL_COLOR, font=font, anchor="mm")
    return out


def grid_text(grid: Grid, box: tuple[int, int]) -> str:
    """The grid as text, with '.' for empty cells and lines between boxes."""
    box_rows, box_cols = box
    lines = []
    for r, row in enumerate(grid):
        if r and r % box_rows == 0:
            lines.append("-" * (2 * len(row) + 2 * (len(row) // box_cols - 1) - 1))
        cells = [str(d) if d else "." for d in row]
        groups = [" ".join(cells[i : i + box_cols]) for i in range(0, len(cells), box_cols)]
        lines.append(" | ".join(groups))
    return "\n".join(lines)
