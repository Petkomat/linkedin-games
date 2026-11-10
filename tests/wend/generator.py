"""Random solvable Wend boards for stress tests.

A random path through every cell of the grid (`tests.helpers.random_path`)
is cut into pieces of 3 to 8 tiles, and a random dictionary
word of the right length is written along each piece.
"""

from __future__ import annotations

import random
from functools import cache

from engines.wend import Puzzle
from engines.wend.dictionary import words_of_length
from tests.helpers import random_path

SHORTEST, LONGEST = 3, 8


def random_puzzle(n: int, seed: int) -> Puzzle:
    rng = random.Random(seed)
    path = random_path(n, rng)
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
