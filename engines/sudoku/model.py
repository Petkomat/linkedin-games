"""Domain model for LinkedIn Mini Sudoku (and other N x N sudokus).

Every row, column and box must hold the digits 1..N once each. LinkedIn's
board is 6x6 with boxes of 2 rows x 3 columns. Other sizes get the most
square box shape that divides N (9 -> 3x3, 4 -> 2x2, 8 -> 2x4).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isqrt

Grid = tuple[tuple[int, ...], ...]  # rows of digits; 0 marks an empty cell


@dataclass(frozen=True)
class Puzzle:
    grid: Grid

    @property
    def size(self) -> int:
        return len(self.grid)

    @property
    def box(self) -> tuple[int, int]:
        """(rows, cols) of one box."""
        rows = max(d for d in range(1, isqrt(self.size) + 1) if self.size % d == 0)
        return rows, self.size // rows
