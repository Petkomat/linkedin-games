"""Random solvable Queens puzzles, for stress tests.

Places N queens that share no row or column and don't touch. Each queen then
seeds a region, and the regions grow one random frontier cell at a time until
they cover the board. The planted queens solve the puzzle, though other
solutions may exist.
"""

from __future__ import annotations

import random

from engines.queens import Puzzle


def random_puzzle(n: int, seed: int) -> Puzzle:
    rng = random.Random(seed)
    queens = _random_queens(n, rng)
    owner = [[-1] * n for _ in range(n)]
    frontier = []
    for label, (r, c) in enumerate(queens):
        owner[r][c] = label
        frontier.append((r, c))
    while frontier:
        r, c = frontier.pop(rng.randrange(len(frontier)))
        free = [
            (r + dr, c + dc)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= r + dr < n and 0 <= c + dc < n and owner[r + dr][c + dc] < 0
        ]
        if not free:
            continue
        nr, nc = rng.choice(free)
        owner[nr][nc] = owner[r][c]
        frontier += [(r, c), (nr, nc)]
    return Puzzle(tuple(tuple(row) for row in owner))


def _random_queens(n: int, rng: random.Random) -> list[tuple[int, int]]:
    cols: list[int] = []

    def place(row: int) -> bool:
        if row == n:
            return True
        options = [c for c in range(n) if c not in cols and (not cols or abs(c - cols[-1]) > 1)]
        rng.shuffle(options)
        for c in options:
            cols.append(c)
            if place(row + 1):
                return True
            cols.pop()
        return False

    if not place(0):
        raise ValueError(f"no queen layout for n={n}")
    return list(enumerate(cols))
