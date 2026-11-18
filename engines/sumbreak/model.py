"""Domain model for LinkedIn Sumbreak.

A grid of numbered tiles. Dragging a tile onto an orthogonal neighbour with
the same number merges them: the neighbour now shows their sum, and the
dragged tile's cell stays empty for the rest of the game. Tiles never move, so
a merge never reaches across an empty cell or along a diagonal. Merge until
one tile remains.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common import Cell

__all__ = ["Cell", "Merge", "Puzzle"]


@dataclass(frozen=True)
class Puzzle:
    numbers: tuple[tuple[int | None, ...], ...]  # row by row; None is an empty cell

    @property
    def rows(self) -> int:
        return len(self.numbers)

    @property
    def cols(self) -> int:
        return len(self.numbers[0]) if self.numbers else 0

    def tiles(self) -> dict[Cell, int]:
        """Every tile's number, by cell."""
        return {
            (r, c): number
            for r, row in enumerate(self.numbers)
            for c, number in enumerate(row)
            if number is not None
        }


@dataclass(frozen=True)
class Merge:
    """Drag the tile on `source` onto its neighbour `target`, which keeps the sum."""

    source: Cell
    target: Cell
