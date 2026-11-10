"""Draw a Wend solution on top of the original screenshot."""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..common.text import board_text, letter
from ..vision import ImageSource, open_image
from .model import Puzzle, Word
from .ocr import Scan

# One colour per word, see-through so the letters stay readable.
COLORS = ((76, 175, 80), (33, 150, 243), (255, 152, 0), (156, 39, 176), (233, 30, 99), (0, 150, 136))
ALPHA = 120
PILL_WIDTH = 0.55  # of the pitch


def render_solution(image: ImageSource, seen: Scan, words: list[Word]) -> Image.Image:
    """Return the screenshot with every word drawn as a pill through its tiles."""
    out = open_image(image).convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    width = round(PILL_WIDTH * seen.grid.pitch)
    for i, word in enumerate(words):
        color = (*COLORS[i % len(COLORS)], ALPHA)
        points = [seen.grid.center(r, c) for r, c in word.path]
        draw.line(points, fill=color, width=width, joint="curve")
        for x, y in (points[0], points[-1]):  # round ends
            draw.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=color)
    return Image.alpha_composite(out, layer).convert("RGB")


def puzzle_text(puzzle: Puzzle) -> str:
    board = board_text([["#" if ch is None else ch for ch in row] for row in puzzle.letters])
    lengths = ", ".join(map(str, puzzle.lengths)) or "none found"
    return f"{board}\nWord lengths: {lengths}"


def solution_text(puzzle: Puzzle, words: list[Word]) -> str:
    """The words, then the board with each tile labelled by its word."""
    rows = [["#" for _ in row] for row in puzzle.letters]
    for i, word in enumerate(words):
        for r, c in word.path:
            rows[r][c] = letter(i)
    names = ", ".join(f"{letter(i)} {word.text}" for i, word in enumerate(words))
    return f"{names}\n{board_text(rows)}"
