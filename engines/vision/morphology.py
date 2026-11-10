"""Small binary-image helpers on boolean numpy arrays (no scipy needed)."""

from __future__ import annotations

import numpy as np


def grow(seed: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Flood fill: the 4-connected part of `mask` that touches `seed`."""
    blob = seed & mask
    while True:
        grown = blob.copy()
        grown[1:] |= blob[:-1]
        grown[:-1] |= blob[1:]
        grown[:, 1:] |= blob[:, :-1]
        grown[:, :-1] |= blob[:, 1:]
        grown &= mask
        if np.array_equal(grown, blob):
            return blob
        blob = grown


def erode(mask: np.ndarray, steps: int) -> np.ndarray:
    for _ in range(steps):
        inner = mask.copy()
        inner[1:] &= mask[:-1]
        inner[:-1] &= mask[1:]
        inner[:, 1:] &= mask[:, :-1]
        inner[:, :-1] &= mask[:, 1:]
        mask = inner
    return mask


def fill_holes(mask: np.ndarray) -> np.ndarray:
    """`mask` plus every background pixel not reachable from the border."""
    border = np.zeros_like(mask)
    border[[0, -1], :] = True
    border[:, [0, -1]] = True
    return ~grow(border & ~mask, ~mask)


def count_holes(mask: np.ndarray, min_area: int) -> int:
    """Enclosed background regions of at least `min_area` pixels."""
    holes = fill_holes(mask) & ~mask
    count = 0
    while holes.any():
        seed = np.zeros_like(holes)
        seed[tuple(np.argwhere(holes)[0])] = True
        region = grow(seed, holes)
        holes &= ~region
        count += region.sum() >= min_area
    return count


def bbox(mask: np.ndarray) -> tuple[slice, slice]:
    """Row and column slices of the bounding box of the True pixels."""
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    return slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1)


def crop(mask: np.ndarray) -> np.ndarray:
    """`mask` cut down to the bounding box of its True pixels."""
    return mask[bbox(mask)]
