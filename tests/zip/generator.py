"""Random solvable Zip puzzles, for stress tests.

A random path through every cell (`tests.helpers.random_path`) gets the
numbers 1..k on k of its cells, both ends included. That path solves the
puzzle, though other solutions may exist.
"""

from __future__ import annotations

import random

from engines.zip import Puzzle
from tests.helpers import random_path


def random_puzzle(n: int, seed: int, numbers: int) -> Puzzle:
    rng = random.Random(seed)
    path = random_path(n, rng)
    marked = [0, *sorted(rng.sample(range(1, len(path) - 1), numbers - 2)), len(path) - 1]
    return Puzzle(n, n, {path[i]: k for k, i in enumerate(marked, start=1)})
