"""Domain model for LinkedIn Queens.

An N x N grid is split into N coloured regions. Place N queens so that every
row, every column and every region holds exactly one, and no two queens touch,
not even diagonally.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common import Cell

__all__ = ["Cell", "Puzzle"]


@dataclass(frozen=True)
class Puzzle:
    regions: tuple[tuple[int, ...], ...]  # region label of every cell, row by row

    @property
    def size(self) -> int:
        return len(self.regions)
