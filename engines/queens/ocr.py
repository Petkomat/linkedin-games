"""Read a Queens board from a screenshot.

1. Find the grid (`engines.vision.grid`).
2. Each cell's colour is the median of its light pixels, which leaves out any
   queen or cross already drawn on it and the borders.
3. Cells whose colours are close belong to the same region. LinkedIn gives
   every region its own clearly different pastel colour.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, find_grid, load_rgb
from .model import Puzzle

CELL_INSET = 0.15  # of the pitch; clears the thick region borders
# Max RGB distance between two cells of one region. On queens1, cells of one
# region match exactly and the closest two regions (orange, yellow) are 50 apart.
SAME_REGION = 25.0


@dataclass(frozen=True)
class Scan:
    """What `scan` saw: the puzzle, where its grid is, and each region's colour."""

    puzzle: Puzzle
    grid: GridGeometry
    colors: tuple[tuple[int, int, int], ...]  # indexed by region label


def read_puzzle(image: ImageSource) -> Puzzle:
    return scan(image).puzzle


def scan(image: ImageSource) -> Scan:
    rgb = load_rgb(image)
    grid = find_grid(rgb)
    palette: list[np.ndarray] = []
    regions = []
    for row in range(grid.rows):
        labels = []
        for col in range(grid.cols):
            color = _cell_color(grid.cell_pixels(rgb, row, col, inset=CELL_INSET))
            labels.append(_label(color, palette))
        regions.append(tuple(labels))
    colors = tuple(tuple(int(v) for v in c) for c in palette)
    return Scan(Puzzle(tuple(regions)), grid, colors)


def _cell_color(cell: np.ndarray) -> np.ndarray:
    pixels = cell.reshape(-1, 3)
    brightness = pixels.mean(axis=1)
    light = pixels[brightness >= np.percentile(brightness, 40)]
    return np.median(light, axis=0)


def _label(color: np.ndarray, palette: list[np.ndarray]) -> int:
    """Index of the palette colour within SAME_REGION of `color`, adding it if new."""
    for label, known in enumerate(palette):
        if np.linalg.norm(color - known) <= SAME_REGION:
            return label
    palette.append(color)
    return len(palette) - 1
