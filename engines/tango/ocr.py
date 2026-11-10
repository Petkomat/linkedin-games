"""Read a Tango board from a screenshot.

1. Find the grid (`engines.vision.grid`).
2. A cell holds a symbol if enough of its pixels are strongly saturated: the
   board itself is white and light grey. Suns are orange and moons are blue,
   so comparing the red and blue channels of those pixels tells them apart.
   Only symbols on a grey cell are part of the puzzle. Symbols on white cells
   are the player's moves, so they're ignored.
3. Signs sit on the midpoint of the border between two cells, drawn in dark
   grey ink. '=' is two bars with a gap between them, while 'x' is a single
   stroke, so the number of separate bands of inked rows tells them apart.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, find_grid, load_rgb
from .model import Cell, Edge, Puzzle, Symbol

CELL_INSET = 0.15  # of the pitch
SATURATED = 80  # max - min channel above this counts as icon colour
MIN_ICON = 0.03  # share of a cell's pixels that must be icon colour
GIVEN_SHADE = 246  # pre-filled cells are grey (~235); the others are white (255)
SIGN_REACH = 0.15  # of the pitch: half the size of the window around a border midpoint
INK = 150  # unsaturated pixels darker than this are sign ink
MIN_SIGN = 0.02  # share of the window's pixels that must be ink


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
    givens = tuple(
        tuple(_given(grid.cell_pixels(rgb, r, c, inset=CELL_INSET)) for c in range(grid.cols))
        for r in range(grid.rows)
    )
    signs = {"=": set(), "x": set()}
    for edge, (x, y) in _borders(grid):
        reach = SIGN_REACH * grid.pitch
        window = rgb[round(y - reach) : round(y + reach) + 1, round(x - reach) : round(x + reach) + 1]
        sign = _sign(window)
        if sign:
            signs[sign].add(edge)
    return Scan(Puzzle(givens, frozenset(signs["="]), frozenset(signs["x"])), grid)


def _borders(grid: GridGeometry) -> Iterator[tuple[Edge, tuple[float, float]]]:
    """Every pair of neighbouring cells, with the pixel midpoint of their shared border."""
    for r in range(grid.rows):
        for c in range(grid.cols):
            x, y = grid.center(r, c)
            if c + 1 < grid.cols:
                yield _edge((r, c), (r, c + 1)), (x + grid.xs.pitch / 2, y)
            if r + 1 < grid.rows:
                yield _edge((r, c), (r + 1, c)), (x, y + grid.ys.pitch / 2)


def _edge(a: Cell, b: Cell) -> Edge:
    return frozenset((a, b))


def _sign(window: np.ndarray) -> str | None:
    """'=', 'x' or None for the pixels around a border midpoint."""
    gray = window.mean(axis=2)
    ink = (gray < INK) & (window.max(axis=2) - window.min(axis=2) <= SATURATED)
    if ink.sum() < MIN_SIGN * ink.size:
        return None
    inked_rows = ink.any(axis=1).astype(int)
    bands = inked_rows[0] + np.count_nonzero(np.diff(inked_rows) == 1)
    return "=" if bands >= 2 else "x"


def _given(cell: np.ndarray) -> Symbol | None:
    """The cell's symbol if it is pre-filled (on a grey cell), else None."""
    pixels = cell.reshape(-1, 3)
    saturated = (pixels.max(axis=1) - pixels.min(axis=1)) > SATURATED
    icon, background = pixels[saturated], pixels[~saturated]
    if len(icon) < MIN_ICON * len(pixels) or np.median(background.mean(axis=1)) > GIVEN_SHADE:
        return None
    red, blue = icon[:, 0].mean(), icon[:, 2].mean()
    return Symbol.SUN if red > blue else Symbol.MOON
