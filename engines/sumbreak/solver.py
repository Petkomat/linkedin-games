"""Backtracking Sumbreak solver.

Numbers only grow, so a tile with the smallest number on the board can only
ever merge with another tile of that number, and that tile has to be its
neighbour already. Every smallest tile must merge (or nothing could be left
but itself), so the smallest tiles are paired off first. Each one is a unit
whose options are its merges: onto a neighbour with the same number, or that
neighbour onto it.

A merge is not an option if it leaves a board that can no longer end in one
tile, which shows in one of three ways:
  * the tiles fall apart into groups with empty cells between them, which can
    never meet again;
  * a tile has no neighbour with its number, or a smaller one that could
    double up to it: its neighbours only grow or leave, so it is stuck;
  * the smallest tiles that touch form a group of an odd size, so they can't
    all be paired off.

The search branches on the unit with the fewest options: one with none is a
dead end, and one with a single option is forced. Boards it has already seen
fail are not searched again. The search stops at the first solution. Every
merge it makes, and every merge it takes back, is written to `trace`.
"""

from __future__ import annotations

from ..common.trace import Trace
from .model import Cell, Merge, Puzzle

Tiles = dict[Cell, int]


def solve(puzzle: Puzzle, trace: Trace | None = None) -> list[Merge] | None:
    trace = Trace() if trace is None else trace
    failed: set[frozenset[tuple[Cell, int]]] = set()

    def search(tiles: Tiles) -> list[Merge] | None:
        if len(tiles) <= 1:
            return []
        key = frozenset(tiles.items())
        if key in failed:
            return None
        mark = trace.mark()
        for merge, after in _options(tiles):
            trace.put(merge)
            found = search(after)
            if found is not None:
                return [merge, *found]
            trace.back_to(mark)
        failed.add(key)
        return None

    tiles = puzzle.tiles()
    if len(tiles) > 1 and (
        not all(_doubles_to(min(tiles.values()), number) for number in tiles.values())
        or _split(tiles)
        or _unpaired(tiles)
        or _uneven(tiles)
        or any(_stuck(cell, tiles) for cell in tiles)
    ):
        return None
    return search(tiles)


def _options(tiles: Tiles) -> list[tuple[Merge, Tiles]]:
    """The merges of the smallest tile with the fewest that don't lead to a
    dead board, each with the board it leaves."""
    smallest = min(tiles.values())
    best: list[tuple[Merge, Tiles]] | None = None
    for cell, number in tiles.items():
        if number != smallest:
            continue
        options = []
        for other in _neighbours(cell):
            if tiles.get(other) == number:
                for merge in (Merge(cell, other), Merge(other, cell)):
                    after = _after(tiles, merge)
                    if not _dead(after, merge):
                        options.append((merge, after))
        if best is None or len(options) < len(best):
            best = options
            if len(best) <= 1:
                break  # a dead end, or a forced merge
    # Holes at the edge of the board first: one in the middle is more likely
    # to cut the tiles apart later.
    return sorted(best or [], key=lambda option: _touching(option[0].source, option[1]))


def _touching(cell: Cell, tiles: Tiles) -> int:
    return sum(other in tiles for other in _neighbours(cell))


def _after(tiles: Tiles, merge: Merge) -> Tiles:
    after = dict(tiles)
    after[merge.target] += after.pop(merge.source)
    return after


def _dead(tiles: Tiles, merge: Merge) -> bool:
    """Can `tiles`, just after `merge`, no longer end in one tile? Only the
    merged tile and the neighbours of the cell it left can have got stuck."""
    if len(tiles) == 1:
        return False
    beside_hole = [cell for cell in _neighbours(merge.source) if cell in tiles]
    if any(_stuck(cell, tiles) for cell in (merge.target, *beside_hole)):
        return True
    # A hole next to one tile can't cut the others apart.
    return (len(beside_hole) > 1 and _split(tiles)) or _unpaired(tiles) or _uneven(tiles)


def _stuck(cell: Cell, tiles: Tiles) -> bool:
    """Has the tile on `cell` no neighbour that has, or could double up to, its number?"""
    number = tiles[cell]
    return not any(_doubles_to(tiles[other], number) for other in _neighbours(cell) if other in tiles)


def _doubles_to(small: int, big: int) -> bool:
    """Is `big` `small` doubled 0 or more times?"""
    if big % small:
        return False
    times = big // small
    return times & (times - 1) == 0


def _split(tiles: Tiles) -> bool:
    """Are there empty cells between some tiles and the rest?"""
    return len(_group(next(iter(tiles)), tiles)) < len(tiles)


def _uneven(tiles: Tiles) -> bool:
    """Do the tiles up to some number t, in a group that touches, add up to
    no whole number of tiles of 2t?

    Until they reach 2t, such tiles can only merge with each other (the
    others are bigger), and they can't stay below it, so each group's sum
    must be made of 2t tiles. Every number is the smallest doubled, which
    `solve` checks first."""
    smallest, largest = min(tiles.values()), max(tiles.values())
    t = 2 * smallest  # for t = smallest, `_unpaired` asks more
    while t < largest:
        low = {cell for cell, number in tiles.items() if number <= t}
        while low:
            group = _group(next(iter(low)), low)
            if sum(tiles[cell] for cell in group) % (2 * t):
                return True
            low -= group
        t *= 2
    return False


def _unpaired(tiles: Tiles) -> bool:
    """Can't the smallest tiles all be paired off, each with a neighbour?

    Neighbours are on cells of different colours of a chessboard, so pairs
    are a matching between the light and the dark cells, which grows one
    augmenting path at a time."""
    smallest = min(tiles.values())
    cells = {cell for cell, number in tiles.items() if number == smallest}
    dark = [cell for cell in cells if sum(cell) % 2]
    if 2 * len(dark) != len(cells):
        return True
    partner: dict[Cell, Cell] = {}  # light cell -> its dark partner

    def pair(cell: Cell, tried: set[Cell]) -> bool:
        for other in _neighbours(cell):
            if other in cells and other not in tried:
                tried.add(other)
                if other not in partner or pair(partner[other], tried):
                    partner[other] = cell
                    return True
        return False

    return not all(pair(cell, set()) for cell in dark)


def _group(start: Cell, cells) -> set[Cell]:
    """The cells of `cells` that can be reached from `start` through neighbours in `cells`."""
    seen = {start}
    todo = [start]
    while todo:
        for other in _neighbours(todo.pop()):
            if other in cells and other not in seen:
                seen.add(other)
                todo.append(other)
    return seen


def _neighbours(cell: Cell) -> tuple[Cell, ...]:
    r, c = cell
    return (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)
