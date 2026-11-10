"""Read a Patches puzzle from a screenshot.

The pipeline:
  1. Find the grid (`engines.vision.grid`).
  2. In every cell, look for a badge: a blob of clearly non-background colour
     that reaches the cell's centre.
  3. Its outline gives the shape (see `_classify_shape`).
  4. Light pixels enclosed by the badge are the number (see `engines.vision.glyphs`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, find_grid, load_rgb, read_number
from ..vision.morphology import crop, erode, fill_holes, grow
from .model import Puzzle, Root, Shape


@dataclass(frozen=True)
class Scan:
    """What `scan` saw: the puzzle plus where it is and how it looks."""

    puzzle: Puzzle
    grid: GridGeometry  # where the grid is in the image
    colors: dict[Root, tuple[int, int, int]]  # badge colour of each root


def read_puzzle(image: ImageSource) -> Puzzle:
    return scan(image).puzzle


def scan(image: ImageSource) -> Scan:
    rgb = load_rgb(image)
    grid = find_grid(rgb)
    colors = {}
    for row in range(grid.rows):
        for col in range(grid.cols):
            cell = grid.cell_pixels(rgb, row, col)
            badge = _find_badge(cell)
            if badge is not None:
                size = read_number(_digit_ink(cell, badge))
                colors[Root(row, col, _classify_shape(badge), size)] = _badge_color(cell, badge)
    puzzle = Puzzle(rows=grid.rows, cols=grid.cols, roots=tuple(colors))
    return Scan(puzzle, grid, colors)


def _find_badge(cell: np.ndarray, min_contrast: float = 60) -> np.ndarray | None:
    """Mask of the badge centred in the cell, or None if the cell is plain.

    Pixels count as badge if their colour is far from the cell's background,
    which is the median colour of the cell's outer ring (white on a fresh
    board, the patch colour on a part-drawn one). Badges are centred in their
    cell, so we keep only the blob that reaches the centre.
    """
    h, w = cell.shape[:2]
    band = max(2, round(0.08 * min(h, w)))
    ring = np.concatenate(
        [cell[:band].reshape(-1, 3), cell[-band:].reshape(-1, 3),
         cell[:, :band].reshape(-1, 3), cell[:, -band:].reshape(-1, 3)]
    )
    background = np.median(ring, axis=0)
    mask = np.sqrt(((cell - background) ** 2).sum(axis=2)) > min_contrast

    seed = np.zeros_like(mask)
    cy, cx, r = h // 2, w // 2, max(1, min(h, w) // 10)
    seed[cy - r : cy + r + 1, cx - r : cx + r + 1] = True
    blob = grow(seed, mask)
    if not blob.any() or max(crop(blob).shape) < 0.3 * min(h, w):
        return None  # nothing, or too small (e.g. the size label of a solved patch)
    return blob


def _classify_shape(badge: np.ndarray) -> Shape:
    """Square, tall and wide badges are filled rounded rectangles. The "any"
    badge is a plus sign of overlapping tiles, so its bounding-box corners are
    mostly empty."""
    box = crop(badge)
    h, w = box.shape
    k = max(1, round(0.2 * min(h, w)))
    corners = np.mean([box[:k, :k].mean(), box[:k, -k:].mean(),
                       box[-k:, :k].mean(), box[-k:, -k:].mean()])
    if corners < 0.6:
        return Shape.ANY
    if w > 1.25 * h:
        return Shape.WIDE
    if h > 1.25 * w:
        return Shape.TALL
    return Shape.SQUARE


def _digit_ink(cell: np.ndarray, badge: np.ndarray) -> np.ndarray:
    """0..1 map of how much each pixel looks like the badge's white number.

    Only the badge's interior counts: its anti-aliased rim is light too. A
    pixel's lowest RGB channel is near 255 for white and low for the badge's
    saturated colour, which works whatever the badge's hue.
    """
    interior = erode(fill_holes(badge), max(1, round(0.1 * min(crop(badge).shape))))
    lowest = cell.min(axis=2).astype(float)
    badge_level = np.median(lowest[badge])
    whiteness = np.clip((lowest - badge_level) / max(1.0, 255 - badge_level), 0, 1)
    return np.where(interior, whiteness, 0.0)


def _badge_color(cell: np.ndarray, badge: np.ndarray) -> tuple[int, int, int]:
    """Median of the badge's most saturated quarter (ignores the light arms of "any")."""
    pixels = cell[badge]
    lowest = pixels.min(axis=1)
    solid = pixels[lowest <= np.percentile(lowest, 25)]
    return tuple(int(v) for v in np.median(solid, axis=0))
