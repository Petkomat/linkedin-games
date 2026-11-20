"""Domain model for LinkedIn Sumbreak.

A grid of tiles, most of them numbered. Dragging a tile onto an orthogonal
neighbour with the same number merges them: the neighbour now shows their sum,
and the dragged tile's cell stays empty for the rest of the game. A x2 tile
(DOUBLE) merges with any number next to it, either way round, and the cell it
is dropped on shows that number doubled. Tiles never move, so a merge never
reaches across an empty cell or along a diagonal. Merge until one tile remains.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common import Cell

__all__ = ["DOUBLE", "Cell", "Merge", "Puzzle", "Tile", "merged"]

DOUBLE = "x2"  # the tile that doubles the number it merges with
Tile = int | str  # a number, or DOUBLE


@dataclass(frozen=True)
class Puzzle:
    numbers: tuple[tuple[Tile | None, ...], ...]  # row by row; None is an empty cell

    @property
    def rows(self) -> int:
        return len(self.numbers)

    @property
    def cols(self) -> int:
        return len(self.numbers[0]) if self.numbers else 0

    def tiles(self) -> dict[Cell, Tile]:
        """Every tile, by cell."""
        return {
            (r, c): number
            for r, row in enumerate(self.numbers)
            for c, number in enumerate(row)
            if number is not None
        }


@dataclass(frozen=True)
class Merge:
    """Drag the tile on `source` onto its neighbour `target`, which keeps the result."""

    source: Cell
    target: Cell


def merged(dragged: Tile, onto: Tile) -> int:
    """What a merge leaves on the cell it is dropped on: two equal numbers add
    up, and a x2 tile doubles the number it meets, whichever of them is dragged."""
    if dragged == DOUBLE:
        return 2 * onto
    if onto == DOUBLE:
        return 2 * dragged
    return dragged + onto
