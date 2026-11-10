"""Random solvable Patches puzzles, for stress tests.

Tiles the grid with random rectangles, then drops one root into each, keeping
or hiding its shape and size at random. The tiling it started from is a valid
answer, so every generated puzzle can be solved.
"""

from __future__ import annotations

import random

from engines.patches import Puzzle, Rect, Root, Shape


def random_puzzle(n: int, seed: int, max_side: int = 4, hide: float = 0.5) -> Puzzle:
    rng = random.Random(seed)
    owner = [[None] * n for _ in range(n)]
    rects = []
    for r in range(n):
        for c in range(n):
            if owner[r][c] is not None:
                continue
            free_w = 0
            while c + free_w < n and owner[r][c + free_w] is None and free_w < max_side:
                free_w += 1
            w = rng.randint(1, free_w)
            free_h = 0
            while (
                r + free_h < n
                and free_h < max_side
                and all(owner[r + free_h][cc] is None for cc in range(c, c + w))
            ):
                free_h += 1
            h = rng.randint(1, free_h)
            rect = Rect(r, c, h, w)
            for rr in range(r, r + h):
                for cc in range(c, c + w):
                    owner[rr][cc] = rect
            rects.append(rect)

    roots = []
    for rect in rects:
        row = rng.randrange(rect.top, rect.top + rect.height)
        col = rng.randrange(rect.left, rect.left + rect.width)
        shape = _shape_of(rect) if rng.random() > hide else Shape.ANY
        size = rect.height * rect.width if rng.random() > hide else None
        roots.append(Root(row, col, shape, size))
    return Puzzle(n, n, tuple(roots))


def _shape_of(rect: Rect) -> Shape:
    if rect.height == rect.width:
        return Shape.SQUARE
    return Shape.TALL if rect.height > rect.width else Shape.WIDE
