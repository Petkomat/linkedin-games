"""Backtracking sudoku solver with constraint propagation.

State: a bitmask of still-possible digits per cell (bit d set = d possible).
Placing a digit removes it from every peer (same row, column or box), and each
removal propagates:
  * a cell left with one candidate is *forced* to it (naked single);
  * a digit left with one possible cell in a unit is *forced* there
    (hidden single);
  * a cell with no candidates, or a digit with no cell in some unit, is a
    dead end.
Once nothing more is forced, we branch on the empty cell with the fewest
candidates, as in the Patches solver. The search stops at the first solution.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from ..common.bits import set_bits
from .model import Grid, Puzzle


@dataclass(frozen=True)
class _Geometry:
    n: int
    units_of: tuple[tuple[tuple[int, ...], ...], ...]  # per cell: its row, column, box
    peers: tuple[tuple[int, ...], ...]  # per cell: every other cell sharing a unit


def solve(puzzle: Puzzle) -> Grid | None:
    n = puzzle.size
    geo = _geometry(n, *puzzle.box)
    candidates = [(1 << (n + 1)) - 2] * (n * n)  # bits 1..n
    for cell in range(n * n):
        digit = puzzle.grid[cell // n][cell % n]
        if digit and not _assign(candidates, cell, digit, geo):
            return None  # the givens contradict each other
    solved = _search(candidates, geo)
    if solved is None:
        return None
    digits = [mask.bit_length() - 1 for mask in solved]
    return tuple(tuple(digits[r * n : (r + 1) * n]) for r in range(n))


def _search(candidates: list[int], geo: _Geometry) -> list[int] | None:
    open_cells = [i for i, mask in enumerate(candidates) if mask & (mask - 1)]
    if not open_cells:
        return candidates
    cell = min(open_cells, key=lambda i: candidates[i].bit_count())
    for digit in set_bits(candidates[cell]):
        trial = candidates.copy()
        if _assign(trial, cell, digit, geo):
            solved = _search(trial, geo)
            if solved is not None:
                return solved
    return None


def _assign(candidates: list[int], cell: int, digit: int, geo: _Geometry) -> bool:
    """Make `digit` the only candidate of `cell`; False on a contradiction."""
    others = candidates[cell] & ~(1 << digit)
    return all(_eliminate(candidates, cell, d, geo) for d in set_bits(others))


def _eliminate(candidates: list[int], cell: int, digit: int, geo: _Geometry) -> bool:
    """Rule `digit` out for `cell` and propagate; False on a contradiction."""
    bit = 1 << digit
    if not candidates[cell] & bit:
        return True
    candidates[cell] &= ~bit
    left = candidates[cell]
    if not left:
        return False
    if not left & (left - 1):  # naked single: clear it from the peers
        last = left.bit_length() - 1
        if not all(_eliminate(candidates, p, last, geo) for p in geo.peers[cell]):
            return False
    for unit in geo.units_of[cell]:  # hidden single: where can `digit` still go?
        places = [c for c in unit if candidates[c] & bit]
        if not places:
            return False
        if len(places) == 1 and not _assign(candidates, places[0], digit, geo):
            return False
    return True


@cache
def _geometry(n: int, box_rows: int, box_cols: int) -> _Geometry:
    rows = [tuple(r * n + c for c in range(n)) for r in range(n)]
    cols = [tuple(r * n + c for r in range(n)) for c in range(n)]
    boxes = [
        tuple(
            (top + r) * n + left + c for r in range(box_rows) for c in range(box_cols)
        )
        for top in range(0, n, box_rows)
        for left in range(0, n, box_cols)
    ]
    units_of = tuple(
        tuple(unit for unit in rows + cols + boxes if cell in unit) for cell in range(n * n)
    )
    peers = tuple(
        tuple(sorted({p for unit in units_of[cell] for p in unit} - {cell}))
        for cell in range(n * n)
    )
    return _Geometry(n, units_of, peers)
