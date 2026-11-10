"""Boards shared by the zip tests."""

from engines.zip import Puzzle

# Typed in from examples/zip/zip1.png (a game in progress, no walls).
ZIP1 = Puzzle(
    rows=6,
    cols=6,
    numbers={
        (0, 0): 1, (5, 5): 2, (4, 1): 3, (2, 1): 4,
        (3, 4): 5, (3, 2): 6, (1, 4): 7, (2, 3): 8,
    },
)  # fmt: skip

ZIP1_ANSWER = [
    (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0),
    (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
    (4, 5), (4, 4), (4, 3), (4, 2), (4, 1),
    (3, 1), (2, 1), (1, 1), (0, 1),
    (0, 2), (0, 3), (0, 4), (0, 5),
    (1, 5), (2, 5), (3, 5), (3, 4), (3, 3), (3, 2),
    (2, 2), (1, 2), (1, 3), (1, 4), (2, 4), (2, 3),
]  # fmt: skip

# Typed in from examples/zip/zip2.jpg (a video frame of a game in progress).
ZIP2 = Puzzle(
    rows=6,
    cols=6,
    numbers={
        (1, 1): 1, (0, 5): 2, (1, 4): 3, (2, 3): 4,
        (4, 4): 5, (4, 1): 6, (3, 2): 7, (5, 0): 8,
    },
    walls=frozenset({
        frozenset({(1, 1), (1, 2)}),
        frozenset({(1, 2), (1, 3)}),
        frozenset({(1, 4), (2, 4)}),
        frozenset({(2, 1), (3, 1)}),
        frozenset({(2, 2), (3, 2)}),
        frozenset({(2, 3), (3, 3)}),
        frozenset({(2, 4), (3, 4)}),
        frozenset({(3, 1), (4, 1)}),
        frozenset({(4, 2), (4, 3)}),
        frozenset({(4, 3), (4, 4)}),
    }),
)  # fmt: skip

ZIP2_ANSWER = [
    (1, 1), (0, 1), (0, 0), (1, 0), (2, 0), (2, 1), (2, 2),
    (1, 2), (0, 2), (0, 3), (0, 4), (0, 5),
    (1, 5), (1, 4), (1, 3), (2, 3), (2, 4), (2, 5),
    (3, 5), (4, 5), (5, 5), (5, 4), (4, 4),
    (3, 4), (3, 3), (4, 3), (5, 3), (5, 2), (5, 1), (4, 1),
    (4, 2), (3, 2), (3, 1), (3, 0), (4, 0), (5, 0),
]  # fmt: skip
