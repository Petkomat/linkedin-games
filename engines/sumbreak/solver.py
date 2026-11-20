"""Backtracking Sumbreak solver.

Numbers only grow, so a tile with the smallest number on the board can only
ever merge with another tile of that number or with a x2 tile, and that tile
has to be its neighbour already (a x2 tile that took another number first
shows at least twice the smallest). Every smallest tile must merge (or nothing
could be left but itself), so the smallest tiles are paired off first. Each
one is a unit whose options are its merges: with a neighbour with the same
number or a x2 neighbour, either of them dragged onto the other.

A merge is not an option if it leaves a board that can no longer end in one
tile, which shows in one of four ways:
  * the tiles fall apart into groups with empty cells between them, which can
    never meet again;
  * a number has no neighbour with its number, a smaller one that could
    double up to it, or a x2 tile: its neighbours only grow or leave, so it
    is stuck;
  * the smallest tiles can't each get a partner of their own;
  * the tiles up to some number, in a group that touches and has no x2 tile,
    can't add up to tiles of twice that number.

The search branches on the unit with the fewest options: one with none is a
dead end, and one with a single option is forced. Boards it has already seen
fail are not searched again. The search stops at the first solution. Every
merge it makes, and every merge it takes back, is written to `trace`.

Two x2 tiles are never merged: no board has shown what that would do.
"""

from __future__ import annotations

from ..common.trace import Trace
from .model import DOUBLE, Cell, Merge, Puzzle, Tile, merged

Tiles = dict[Cell, Tile]


def solve(puzzle: Puzzle, trace: Trace | None = None) -> list[Merge] | None:
    trace = Trace() if trace is None else trace
    failed: set[frozenset[tuple[Cell, Tile]]] = set()

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
    numbers = _numbers(tiles)
    if len(tiles) > 1 and (
        not numbers
        or not all(_doubles_to(min(numbers), number) for number in numbers)
        or _split(tiles)
        or _unpaired(tiles)
        or _uneven(tiles)
        or any(_stuck(cell, tiles) for cell in tiles)
    ):
        return None
    return search(tiles)


def _numbers(tiles: Tiles) -> list[int]:
    return [number for number in tiles.values() if number != DOUBLE]


def _options(tiles: Tiles) -> list[tuple[Merge, Tiles]]:
    """The merges of the smallest tile with the fewest that don't lead to a
    dead board, each with the board it leaves."""
    smallest = min(_numbers(tiles))
    best: list[tuple[Merge, Tiles]] | None = None
    for cell, number in tiles.items():
        if number != smallest:
            continue
        options = []
        for other in _neighbours(cell):
            if tiles.get(other) in (number, DOUBLE):
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
    after[merge.target] = merged(after.pop(merge.source), after[merge.target])
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
    """Has the number on `cell` no neighbour that has, or could double up to,
    its number, nor a x2 tile? A x2 tile merges with any number, so it is
    never stuck; one cut off from the rest is `_split`."""
    number = tiles[cell]
    if number == DOUBLE:
        return False
    return not any(
        tiles[other] == DOUBLE or _doubles_to(tiles[other], number) for other in _neighbours(cell) if other in tiles
    )


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
    no whole number of tiles of 2t, even with what its x2 tiles can add?

    Until they reach 2t, such tiles can only merge with each other or with a
    x2 tile next to them (the others are bigger), and they can't stay below
    it, so each group ends up as tiles of 2t. A merge of two of them keeps
    the group's sum; a x2 tile adds the number it doubles, the smallest
    number doubled a few times and at most t. So a group that is r short of
    a multiple of 2t needs at least as many x2 tiles as r has ones in
    binary, counted in smallest numbers. x2 tiles count as low for every t,
    which joins the groups they touch. Every number is the smallest doubled,
    which `solve` checks first."""
    numbers = _numbers(tiles)
    smallest, largest = min(numbers), max(numbers)
    t = 2 * smallest  # for t = smallest, `_unpaired` asks more
    while t < largest:
        low = {cell for cell, number in tiles.items() if number == DOUBLE or number <= t}
        while low:
            group = _group(next(iter(low)), low)
            low -= group
            doubles = sum(tiles[cell] == DOUBLE for cell in group)
            short = -sum(tiles[cell] for cell in group if tiles[cell] != DOUBLE) % (2 * t)
            if (short // smallest).bit_count() > doubles:
                return True
        t *= 2
    return False


def _unpaired(tiles: Tiles) -> bool:
    """Can't each smallest tile get a partner of its own, a neighbour with
    its number or a x2 tile?

    Each smallest tile first merges with one of them, and a partner takes
    only one. Neighbours are on cells of different colours of a chessboard,
    so partners are a matching between the light and the dark cells, which
    grows one augmenting path at a time. If the smallest tiles on dark cells
    can all get partners, and so can those on light cells, one matching
    gives them all one (Mendelsohn and Dulmage's theorem)."""
    smallest = min(_numbers(tiles))
    cells = {cell for cell, number in tiles.items() if number == smallest}
    partners = cells | {cell for cell, number in tiles.items() if number == DOUBLE}
    if partners == cells and 2 * sum(sum(cell) % 2 for cell in cells) != len(cells):
        return True  # without x2 tiles, as many smallest tiles on dark cells as on light ones
    for colour in (0, 1):
        partner: dict[Cell, Cell] = {}  # a partner's cell -> the smallest tile it takes

        def pair(cell: Cell, tried: set[Cell]) -> bool:
            for other in _neighbours(cell):
                if other in partners and other not in tried:
                    tried.add(other)
                    if other not in partner or pair(partner[other], tried):
                        partner[other] = cell
                        return True
            return False

        if not all(pair(cell, set()) for cell in cells if sum(cell) % 2 == colour):
            return True
        if partners == cells:
            return False  # as many on both sides, and all of one side paired: all are
    return False


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
