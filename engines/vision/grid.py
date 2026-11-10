"""Find a puzzle grid in a screenshot.

Grid lines are thin and darker than the pixels on either side ("ridges"). Per
column (and per row) we count ridge pixels. The evenly spaced peaks of that
profile with the most cells between them give the lattice.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

MIN_PITCH = 12  # px; smaller cells could not hold anything readable
MIN_CELLS = 4  # no LinkedIn board is smaller; fewer evenly spaced lines can be a line of text
MAX_CELLS = 15
SQUARE = 0.05  # how far from square (column / row spacing) cells may look
CROSSED = 0.15  # a grid line crosses a row if it is a ridge for this share of the row's height


@dataclass(frozen=True)
class Lattice:
    """Evenly spaced grid lines along one axis: start, start + pitch, ..."""

    start: float
    pitch: float
    cells: int

    @property
    def end(self) -> float:
        return self.start + self.pitch * self.cells


@dataclass(frozen=True)
class GridGeometry:
    """Where a grid sits in an image: its vertical (xs) and horizontal (ys) lines."""

    xs: Lattice
    ys: Lattice

    @property
    def rows(self) -> int:
        return self.ys.cells

    @property
    def cols(self) -> int:
        return self.xs.cells

    @property
    def pitch(self) -> float:
        return (self.xs.pitch + self.ys.pitch) / 2

    def box(
        self, top: int, left: int, height: int = 1, width: int = 1, inset: float = 0.0
    ) -> tuple[float, float, float, float]:
        """Pixel box (x0, y0, x1, y1) of a block of cells, shrunk by `inset` x pitch."""
        return (
            self.xs.start + self.xs.pitch * (left + inset),
            self.ys.start + self.ys.pitch * (top + inset),
            self.xs.start + self.xs.pitch * (left + width - inset),
            self.ys.start + self.ys.pitch * (top + height - inset),
        )

    def center(self, row: int, col: int) -> tuple[float, float]:
        """Pixel (x, y) of a cell's centre."""
        return self.xs.start + self.xs.pitch * (col + 0.5), self.ys.start + self.ys.pitch * (row + 0.5)

    def cell_pixels(self, rgb: np.ndarray, row: int, col: int, inset: float = 0.05) -> np.ndarray:
        """The cell's pixels, inset by a fraction of the pitch so grid lines are left out."""
        x0, y0, x1, y1 = self.box(row, col, inset=inset)
        return rgb[round(y0) : round(y1), round(x0) : round(x1)]

    def borders(self) -> Iterator[tuple[tuple[int, int], tuple[int, int], tuple[float, float]]]:
        """Every pair of side-by-side or stacked cells, with the pixel (x, y) of
        the middle of the border between them."""
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = self.center(r, c)
                if c + 1 < self.cols:
                    yield (r, c), (r, c + 1), (x + self.xs.pitch / 2, y)
                if r + 1 < self.rows:
                    yield (r, c), (r + 1, c), (x, y + self.ys.pitch / 2)


def find_grid(rgb: np.ndarray) -> GridGeometry:
    """Locate the grid: the evenly spaced lines with the most cells between them.

    On high-resolution screenshots, the thick lines are too wide for the ridge
    finder. Then it finds oblong cells (wend2), or only the inside of the
    board, missing its thick outer frame (queens2: the 6x6 inside an 8x8). So
    the search is repeated on a half-size copy, where those lines are thin.
    That grid wins if its cells are square (as on every LinkedIn board) and
    either the full-size cells aren't, or it is a bigger square board.
    """
    gray = rgb.mean(axis=2)
    grid = _lattices_or_none(gray)
    half = _lattices_or_none(_half_size(gray))
    if half is not None and _has_square_cells(half):
        if grid is None or not _has_square_cells(grid) or _bigger_board(half, grid):
            return GridGeometry(_doubled(half.xs), _doubled(half.ys))
    if grid is None:
        raise ValueError("could not find a grid in the image")
    return grid


def _lattices_or_none(gray: np.ndarray) -> GridGeometry | None:
    try:
        return _find_lattices(gray)
    except ValueError:
        return None


def _has_square_cells(grid: GridGeometry) -> bool:
    return abs(grid.xs.pitch / grid.ys.pitch - 1) <= SQUARE


def _bigger_board(half: GridGeometry, full: GridGeometry) -> bool:
    """Is the half-size grid a square board with more cells than the full-size one?"""
    return half.rows == half.cols and half.rows * half.cols > full.rows * full.cols


def _half_size(gray: np.ndarray) -> np.ndarray:
    """Average every 2x2 block of pixels."""
    h, w = gray.shape[0] // 2 * 2, gray.shape[1] // 2 * 2
    return gray[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def _doubled(lattice: Lattice) -> Lattice:
    """A lattice found at half size, in full-size pixels (half-size pixel i covers 2i and 2i + 1)."""
    return Lattice(2 * lattice.start + 0.5, 2 * lattice.pitch, lattice.cells)


def _find_lattices(gray: np.ndarray) -> GridGeometry:
    xs = _fit_lattice(_peaks(_ridge_profile(gray)))
    # Count horizontal ridges only between the vertical grid borders, and then
    # vertical ridges only between the horizontal ones, so other UI is ignored.
    ys = _fit_lattice(_peaks(_ridge_profile(gray[:, _span(xs)].T)))
    xs = _fit_lattice(_peaks(_ridge_profile(gray[_span(ys), :])))
    ys = _drop_extra_ends(gray, xs, ys)
    xs = _drop_extra_ends(gray.T, ys, xs)
    return GridGeometry(xs, ys)


def _drop_extra_ends(gray: np.ndarray, columns: Lattice, rows: Lattice) -> Lattice:
    """`rows` without the end rows that `columns` don't run through.

    LinkedIn boards are square. More rows than columns means a line of the UI
    above or below the board happens to sit one row's height away (zip2's
    buttons), and the board's columns don't run through that extra row.
    """
    for last in (True, False):
        while rows.cells > columns.cells and not _crossed(gray, columns, _end_band(rows, last)):
            start = rows.start if last else rows.start + rows.pitch
            rows = Lattice(start, rows.pitch, rows.cells - 1)
    return rows


def _end_band(lattice: Lattice, last: bool) -> slice:
    """Pixel rows of the lattice's first or last cell."""
    start = lattice.end - lattice.pitch if last else lattice.start
    return slice(round(start), round(start + lattice.pitch))


def _crossed(gray: np.ndarray, columns: Lattice, band: slice) -> bool:
    """Do at least half of the column lines show up as ridges within the pixel
    rows `band`? Lines may be partly hidden by what's drawn on the board."""
    rows = gray[band]
    profile = _ridge_profile(rows)
    reach = max(2, round(0.05 * columns.pitch))
    lines = [round(columns.start + k * columns.pitch) for k in range(columns.cells + 1)]
    seen = sum(
        profile[max(0, x - reach) : x + reach + 1].max(initial=0) >= CROSSED * rows.shape[0]
        for x in lines
    )
    return 2 * seen >= len(lines)


def _span(lattice: Lattice) -> slice:
    return slice(int(lattice.start), int(np.ceil(lattice.end)) + 1)


def _ridge_profile(gray: np.ndarray, contrast: float = 6, reaches: tuple[int, ...] = (2, 4)) -> np.ndarray:
    """For every column, how many pixels are darker than both pixels `reach` px away.

    A reach of 2 finds hairlines, and 4 finds lines up to ~7 px thick (sudoku
    box borders), whose middle is not darker than pixels 2 px away.
    """
    m = max(reaches)
    mid = gray[:, m:-m]
    ridge = np.zeros(mid.shape, dtype=bool)
    for r in reaches:
        left, right = gray[:, m - r : -m - r], gray[:, m + r : gray.shape[1] - m + r]
        ridge |= (mid < left - contrast) & (mid < right - contrast)
    return np.pad(ridge.sum(axis=0), m)


def _peaks(profile: np.ndarray, rel: float = 0.25) -> list[float]:
    """Centres of runs of columns whose ridge count is a good part of the max."""
    if not profile.any():  # a blank image, e.g. a page still loading
        raise ValueError("could not find a grid in the image")
    strong = np.flatnonzero(profile >= rel * profile.max())
    peaks, run = [], [strong[0]]
    for i in strong[1:]:
        if i - run[-1] <= 2:
            run.append(i)
        else:
            peaks.append(run)
            run = [i]
    peaks.append(run)
    return [float(np.average(r, weights=profile[r])) for r in peaks]


def _fit_lattice(peaks: list[float]) -> Lattice:
    """The evenly spaced run of peaks with the most cells."""
    best: Lattice | None = None
    for i, first in enumerate(peaks):
        for last in peaks[i + 1 :]:
            for cells in range(1, MAX_CELLS + 1):
                pitch = (last - first) / cells
                if pitch < MIN_PITCH:
                    break
                tol = max(2.0, 0.05 * pitch)
                lines = (first + k * pitch for k in range(cells + 1))
                if all(min(abs(p - line) for p in peaks) <= tol for line in lines):
                    if best is None or cells > best.cells:
                        best = Lattice(first, pitch, cells)
    if best is None or best.cells < MIN_CELLS:
        raise ValueError("could not find a grid in the image")
    return best
