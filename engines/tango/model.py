"""Domain model for LinkedIn Tango.

Fill an N x N grid (N even) with suns and moons so that:
  * no more than two equal symbols are next to each other in a row or column;
  * every row and column holds N/2 suns and N/2 moons;
  * two cells joined by '=' hold the same symbol, and by 'x' opposite ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..common import Cell, Edge

__all__ = ["Cell", "Edge", "Grid", "Puzzle", "Symbol"]


class Symbol(Enum):
    SUN = "S"
    MOON = "M"


Grid = tuple[tuple[Symbol | None, ...], ...]  # rows; None marks an empty cell


@dataclass(frozen=True)
class Puzzle:
    givens: Grid
    equal: frozenset[Edge] = frozenset()  # '=' signs
    opposite: frozenset[Edge] = frozenset()  # 'x' signs

    @property
    def size(self) -> int:
        return len(self.givens)
