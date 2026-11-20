"""Random solvable Sumbreak boards, for stress tests.

A board is built backwards from its last tile: one tile on a random cell of
an empty grid is broken in two again and again, the new part going to an
empty neighbour, until every cell holds a tile. A break makes two halves, or,
for a board with x2 tiles, a half and a x2 tile, either of them on the new
cell. Played forwards, the breaks are merges, so every board this makes can be
solved, though often in other ways too. A board that runs out of tiles to
break before it is full (they are all 1s or x2 tiles, or have no empty
neighbour) is thrown away and built again, starting from a bigger number after
a few tries.
"""

from __future__ import annotations

import random

from engines.sumbreak import DOUBLE, Puzzle

TRIES = 20  # boards to throw away before starting from a bigger number


def random_puzzle(rows: int, cols: int, seed: int, spread: int = 0, doubles: int = 0) -> Puzzle:
    """A full board with `doubles` x2 tiles. The last tile is the smallest
    power of 2 that could fill it, doubled `spread` times: the bigger, the
    more different the numbers. sumbreak1 is 128 on 3x3, a spread of 3."""
    rng = random.Random(seed)
    power = (rows * cols - 1 - doubles).bit_length() + spread
    while True:
        for _ in range(TRIES):
            tiles = _broken(rows, cols, 1 << power, doubles, rng)
            if tiles is not None:
                return Puzzle(tuple(tuple(tiles[r, c] for c in range(cols)) for r in range(rows)))
        power += 1


def _broken(rows: int, cols: int, total: int, doubles: int, rng: random.Random) -> dict[tuple[int, int], int | str] | None:
    tiles: dict[tuple[int, int], int | str] = {(rng.randrange(rows), rng.randrange(cols)): total}
    doubling = set(rng.sample(range(rows * cols - 1), doubles))  # which breaks leave a x2 tile
    while len(tiles) < rows * cols:
        breaks = [
            (cell, free)
            for cell, number in tiles.items()
            if number != DOUBLE and number > 1
            for free in _neighbours(cell, rows, cols)
            if free not in tiles
        ]
        if not breaks:
            return None
        cell, free = rng.choice(breaks)
        half = tiles[cell] // 2
        tiles[cell] = tiles[free] = half
        if len(tiles) - 2 in doubling:
            tiles[rng.choice((cell, free))] = DOUBLE
    return tiles


def _neighbours(cell: tuple[int, int], rows: int, cols: int) -> list[tuple[int, int]]:
    r, c = cell
    return [(r + dr, c + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)) if 0 <= r + dr < rows and 0 <= c + dc < cols]
