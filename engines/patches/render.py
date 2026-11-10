"""Draw a solution on top of the original screenshot."""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..common.text import board_text, letter
from ..vision import ImageSource, open_image
from .model import Rect, Root
from .ocr import Scan


def render_solution(image: ImageSource, seen: Scan, solution: dict[Root, Rect]) -> Image.Image:
    """Return the screenshot with each patch filled in its badge's colour."""
    base = open_image(image).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    pitch = seen.grid.pitch
    for root, rect in solution.items():
        r, g, b = seen.colors[root]
        box = seen.grid.box(rect.top, rect.left, rect.height, rect.width, inset=0.04)
        draw.rounded_rectangle(
            box, radius=round(0.12 * pitch), fill=(r, g, b, 90),
            outline=(r, g, b, 255), width=max(2, round(0.03 * pitch)),
        )
    return Image.alpha_composite(base, overlay)


def solution_text(rows: int, cols: int, solution: dict[Root, Rect]) -> str:
    """The tiling as letters, one per patch (A, B, ...) in reading order of roots."""
    grid = [["?"] * cols for _ in range(rows)]
    ordered = sorted(solution.items(), key=lambda kv: (kv[0].row, kv[0].col))
    for i, (_, rect) in enumerate(ordered):
        for r in range(rect.top, rect.top + rect.height):
            for c in range(rect.left, rect.left + rect.width):
                grid[r][c] = letter(i)
    return board_text(grid)
