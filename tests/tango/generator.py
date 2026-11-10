"""Random solvable Tango puzzles, for stress tests.

Builds a random valid board (see `_random_board`), then reveals a random
share of its cells and of the signs between neighbours. The hidden board solves
the puzzle, though other solutions may exist.
"""

from __future__ import annotations

import itertools
import random

from engines.tango import Puzzle, Symbol


def random_puzzle(n: int, seed: int, givens: float = 0.25, signs: float = 0.1) -> Puzzle:
    rng = random.Random(seed)
    answer = _random_board(n, rng)
    shown = tuple(
        tuple(answer[r][c] if rng.random() < givens else None for c in range(n)) for r in range(n)
    )
    equal, opposite = set(), set()
    for r, c in itertools.product(range(n), repeat=2):
        for nr, nc in ((r + 1, c), (r, c + 1)):
            if nr < n and nc < n and rng.random() < signs:
                same = answer[r][c] == answer[nr][nc]
                (equal if same else opposite).add(frozenset({(r, c), (nr, nc)}))
    return Puzzle(shown, frozenset(equal), frozenset(opposite))


def _random_board(n: int, rng: random.Random) -> list[tuple[Symbol, ...]]:
    """A random valid board, by mixing a checkerboard with count-preserving flips.

    Flipping a 2x2 "switch" (S M / M S <-> M S / S M) keeps every row and column
    count. A flip that makes three equal neighbours is undone.
    """
    board = [[(r + c) % 2 for c in range(n)] for r in range(n)]  # 1 = sun
    for _ in range(30 * n * n):
        r1, r2 = rng.sample(range(n), 2)
        c1, c2 = rng.sample(range(n), 2)
        if not board[r1][c1] == board[r2][c2] != board[r1][c2] == board[r2][c1]:
            continue
        for r, c in ((r1, c1), (r1, c2), (r2, c1), (r2, c2)):
            board[r][c] ^= 1
        touched = [board[r1], board[r2], [row[c1] for row in board], [row[c2] for row in board]]
        if any(_has_triple(line) for line in touched):
            for r, c in ((r1, c1), (r1, c2), (r2, c1), (r2, c2)):
                board[r][c] ^= 1
    return [tuple(Symbol.SUN if v else Symbol.MOON for v in row) for row in board]


def _has_triple(line) -> bool:
    return any(line[i] == line[i + 1] == line[i + 2] for i in range(len(line) - 2))
