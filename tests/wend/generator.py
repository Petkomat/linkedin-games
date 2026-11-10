"""Random solvable Wend boards for stress tests.

A random path through every cell of the grid (a zig-zag scrambled by
"backbite" moves) is cut into pieces of 3 to 8 tiles, and a random dictionary
word of the right length is written along each piece.
"""

from __future__ import annotations

import random
from functools import cache

from engines.wend import Puzzle
from engines.wend.dictionary import words_of_length

SHORTEST, LONGEST = 3, 8


def random_puzzle(n: int, seed: int) -> Puzzle:
    rng = random.Random(seed)
    path = _random_path(n, rng)
    lengths = _random_lengths(len(path), rng)
    board = [[""] * n for _ in range(n)]
    start = 0
    for length in lengths:
        word = rng.choice(_sorted_words(length))
        for (r, c), letter in zip(path[start : start + length], word):
            board[r][c] = letter
        start += length
    return Puzzle(tuple(tuple(row) for row in board), tuple(lengths))


@cache
def _sorted_words(length: int) -> tuple[str, ...]:
    return tuple(sorted(words_of_length(length)[0]))  # sorted: sets have no fixed order


def _random_lengths(total: int, rng: random.Random) -> list[int]:
    lengths = []
    while total:
        length = rng.randint(SHORTEST, LONGEST)
        if length == total or total - length >= SHORTEST:
            lengths.append(length)
            total -= length
    return lengths


def _random_path(n: int, rng: random.Random) -> list[tuple[int, int]]:
    path = [(r, c if r % 2 == 0 else n - 1 - c) for r in range(n) for c in range(n)]
    for _ in range(20 * n * n):
        if rng.random() < 0.5:
            path.reverse()
        r, c = path[-1]
        steps = [
            step
            for step in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= step[0] < n and 0 <= step[1] < n and step != path[-2]
        ]
        i = path.index(rng.choice(steps))
        path[i + 1 :] = path[i + 1 :][::-1]  # still visits every cell once
    return path
