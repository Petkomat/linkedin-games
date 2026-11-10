"""Read a sudoku from a screenshot.

1. Find the grid (`engines.vision.grid`).
2. In each cell, "ink" is how much darker a pixel is than the cell's own
   background (its median), so highlighted cells work too. Enough ink means
   the cell holds a given.
3. The ink is read by the shared HOG digit reader (`engines.vision.glyphs`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, find_grid, load_rgb, read_number
from .model import Puzzle

CELL_INSET = 0.12  # of the pitch; clears the thick box borders
MIN_INK = 0.01  # share of a cell's pixels that must be ink for a given


@dataclass(frozen=True)
class Scan:
    """What `scan` saw: the puzzle plus where its grid is in the image."""

    puzzle: Puzzle
    grid: GridGeometry  # where the grid is in the image


def read_puzzle(image: ImageSource) -> Puzzle:
    return scan(image).puzzle


def scan(image: ImageSource) -> Scan:
    rgb = load_rgb(image)
    grid = find_grid(rgb)
    rows = []
    for row in range(grid.rows):
        digits = []
        for col in range(grid.cols):
            ink = _ink(grid.cell_pixels(rgb, row, col, inset=CELL_INSET))
            has_digit = (ink > 0.5).mean() >= MIN_INK
            digits.append((read_number(ink) or 0) if has_digit else 0)
        rows.append(tuple(digits))
    return Scan(Puzzle(tuple(rows)), grid)


def _ink(cell: np.ndarray) -> np.ndarray:
    """0..1 darkness relative to the cell's background."""
    gray = cell.mean(axis=2)
    return np.clip((np.median(gray) - gray) / 128, 0, 1)
