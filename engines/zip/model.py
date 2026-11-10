"""Domain model for LinkedIn Zip.

A puzzle is a grid in which some cells carry the numbers 1..N. A solution is a
single path that starts on 1, visits the numbers in increasing order, ends on
N and passes through every cell exactly once, moving only between orthogonally
adjacent cells. Some puzzles also have walls (thick lines) between adjacent
cells, which the path may not cross.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass

from ..common.types import Cell, Edge

Wall = Edge  # a wall between two orthogonally adjacent cells


@dataclass(frozen=True)
class Puzzle:
    rows: int
    cols: int
    numbers: Mapping[Cell, int]
    walls: AbstractSet[Wall] = frozenset()
