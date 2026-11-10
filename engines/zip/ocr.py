"""Read a Zip board from a screenshot.

1. Find the grid (`engines.vision.grid`).
2. A number is printed in white on a black disc in the middle of its cell.
   The white pixels inside the disc go to the shared glyph reader. (Only
   clearly white ones: counting the grey edges of the strokes too closes the
   gap in a blurry 6, which then reads as 8.)
3. A wall is a thick black bar on the border between two cells. Grid lines are
   thin and grey, and the path the player draws is coloured, so near-black
   pixels around a border's midpoint mean a wall.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, find_grid, load_rgb, read_number
from ..vision.morphology import erode, fill_holes
from .model import Puzzle

CELL_INSET = 0.2  # of the pitch; the disc (half a cell across) still fits
BLACK = 80  # pixels whose brightest channel is below this are black
WHITE = 160  # pixels whose darkest channel is above this are white
DISC = 0.3  # share of a cell's middle that is black when it holds a number (~0.55 vs < 0.15)
RIM = 2  # px of the disc's anti-aliased edge left out of the number
WALL_LENGTH, WALL_WIDTH = 0.6, 0.2  # of the pitch: the window along / across a border
WALL = 0.4  # share of the window that is black on a wall (> 0.8 vs 0)


@dataclass(frozen=True)
class Scan:
    """What `scan` saw: the puzzle plus where its grid is in the image."""

    puzzle: Puzzle
    grid: GridGeometry


def read_puzzle(image: ImageSource) -> Puzzle:
    return scan(image).puzzle


def scan(image: ImageSource) -> Scan:
    rgb = load_rgb(image)
    grid = find_grid(rgb)
    black = rgb.max(axis=2) < BLACK
    numbers = {}
    for r in range(grid.rows):
        for c in range(grid.cols):
            number = _number(grid.cell_pixels(rgb, r, c, inset=CELL_INSET))
            if number is not None:
                numbers[r, c] = number
    walls = frozenset(
        frozenset((a, b)) for a, b, middle in grid.borders() if _is_wall(black, grid, a, b, middle)
    )
    return Scan(Puzzle(grid.rows, grid.cols, numbers, walls), grid)


def _number(cell: np.ndarray) -> int | None:
    """The number on the cell's black disc, or None if there is no disc."""
    black = cell.max(axis=2) < BLACK
    if black.mean() < DISC:
        return None
    disc = erode(fill_holes(black), RIM)
    return read_number((disc & (cell.min(axis=2) > WHITE)).astype(float))


def _is_wall(black: np.ndarray, grid: GridGeometry, a, b, middle: tuple[float, float]) -> bool:
    x, y = middle
    along, across = WALL_LENGTH * grid.pitch / 2, WALL_WIDTH * grid.pitch / 2
    if a[0] == b[0]:  # side by side: the border is vertical
        window = black[round(y - along) : round(y + along), round(x - across) : round(x + across)]
    else:
        window = black[round(y - across) : round(y + across), round(x - along) : round(x + along)]
    return window.mean() >= WALL
