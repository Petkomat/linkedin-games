"""Read a Wend board from a screenshot.

1. Find the grid (`engines.vision.grid`).
2. A cell is grey (no tile) if its middle is a flat mid grey. Tiles are white,
   or green / pink while the player is selecting them, so colour tells them
   apart.
3. A tile's letter is its dark pixels, read by the shared HOG glyph reader
   (`engines.vision.glyphs`).
4. Below the board, each word is a row of light grey squares, one square per
   letter. Rows of flat light-grey pixels are cut into runs, and the runs
   about as wide as the row is tall are counted. The wide grey Undo button
   is not square, so it doesn't count.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, find_grid, load_rgb, read_letter
from .model import Puzzle

CELL_INSET = 0.15  # of the pitch
GREY_BELOW = 215  # grey cells measure ~178; tiles ~250, highlighted tiles ~190-240
FLAT = 20  # max - min channel below this is colourless
INK_BELOW = 128  # letters are near black, or dark green / brown on a highlight
UNREADABLE = "?"  # a tile without a letter: no word can use it
SQUARE_SHADE = (215, 236)  # the length squares (~228) between the card (~249) and page (~239)
SQUARE_FIT = 0.25  # a square's width may differ this much from its row's height


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
    letters = tuple(
        tuple(_letter(grid.cell_pixels(rgb, r, c, inset=CELL_INSET)) for c in range(grid.cols))
        for r in range(grid.rows)
    )
    return Scan(Puzzle(letters, _word_lengths(rgb, grid)), grid)


def _word_lengths(rgb: np.ndarray, grid: GridGeometry) -> tuple[int, ...]:
    """Squares per row in the rows of grey squares below the board (top to bottom)."""
    below = rgb[round(grid.ys.end + 0.1 * grid.pitch) :, : round(grid.xs.end)]
    gray = below.mean(axis=2)
    low, high = SQUARE_SHADE
    shaded = (below.max(axis=2) - below.min(axis=2) < FLAT) & (gray >= low) & (gray <= high)
    lengths = []
    for rows in _runs(np.flatnonzero(shaded.any(axis=1))):
        height = len(rows)
        columns = _runs(np.flatnonzero(shaded[rows].any(axis=0)))
        squares = sum(abs(len(run) / height - 1) <= SQUARE_FIT for run in columns)
        if squares:
            lengths.append(squares)
    return tuple(lengths)


def _runs(indices: np.ndarray) -> list[np.ndarray]:
    """Split sorted indices into runs of consecutive values."""
    if indices.size == 0:
        return []
    return np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)


def _letter(cell: np.ndarray) -> str | None:
    if _is_grey(cell):
        return None
    ink = (cell.mean(axis=2) < INK_BELOW).astype(float)
    return read_letter(ink) or UNREADABLE


def _is_grey(cell: np.ndarray) -> bool:
    background = np.median(cell.reshape(-1, 3), axis=0)
    return background.max() - background.min() < FLAT and background.mean() < GREY_BELOW
