"""Backtracking Queens solver.

Each row, column and region is a *unit* that needs exactly one queen. The
cells where a queen may still go form one bitmask. A queen clears its row,
column, region and its 8 neighbours from it.

At every node, every open unit's free cells are counted:
  * none left -> dead end;
  * one left  -> that queen is forced;
  * otherwise we branch on the unit with the fewest free cells (as in the
    Patches and Sudoku solvers), trying each of its cells.
The search stops at the first solution. Every queen it places, forced or
guessed, and every queen it takes back is written to `trace`.
"""

from __future__ import annotations

from ..common.bits import set_bits
from ..common.trace import Trace
from .model import Cell, Puzzle


def solve(puzzle: Puzzle, trace: Trace | None = None) -> list[Cell] | None:
    trace = Trace() if trace is None else trace
    n = puzzle.size
    labels = sorted({label for row in puzzle.regions for label in row})
    if len(labels) != n:
        return None  # one queen per row means exactly n regions can be served
    units, units_of, blocked = _layout(puzzle, labels)

    def search(free: int, open_units: tuple[int, ...]) -> list[int] | None:
        if not open_units:
            return []
        best_options, best_count = 0, n * n + 1
        for u in open_units:
            options = units[u] & free
            count = options.bit_count()
            if count == 0:
                return None
            if count < best_count:
                best_options, best_count = options, count
                if count == 1:
                    break  # forced
        mark = trace.mark()
        for cell in set_bits(best_options):
            trace.put(divmod(cell, n))
            rest = tuple(u for u in open_units if u not in units_of[cell])
            found = search(free & ~blocked[cell], rest)
            if found is not None:
                return [cell, *found]
            trace.back_to(mark)
        return None

    queens = search((1 << (n * n)) - 1, tuple(range(3 * n)))
    return None if queens is None else sorted(divmod(cell, n) for cell in queens)


def _layout(puzzle: Puzzle, labels: list[int]) -> tuple[list[int], list[tuple[int, int, int]], list[int]]:
    """Unit masks (rows, then columns, then regions), each cell's three units,
    and for each cell the cells a queen there rules out (itself included)."""
    n = puzzle.size
    region_of = {label: i for i, label in enumerate(labels)}
    units = [0] * (3 * n)
    units_of: list[tuple[int, int, int]] = []
    for cell in range(n * n):
        r, c = divmod(cell, n)
        own = (r, n + c, 2 * n + region_of[puzzle.regions[r][c]])
        for u in own:
            units[u] |= 1 << cell
        units_of.append(own)

    blocked = []
    for cell in range(n * n):
        r, c = divmod(cell, n)
        mask = units[units_of[cell][0]] | units[units_of[cell][1]] | units[units_of[cell][2]]
        for rr in range(max(0, r - 1), min(n, r + 2)):
            for cc in range(max(0, c - 1), min(n, c + 2)):
                mask |= 1 << (rr * n + cc)
        blocked.append(mask)
    return units, units_of, blocked
