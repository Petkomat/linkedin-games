"""Boards shared by the Sumbreak tests."""

from __future__ import annotations

from engines.sumbreak import DOUBLE, Puzzle


def board(text: str) -> Puzzle:
    """A board typed as numbers separated by spaces, one line per row; "." is an
    empty cell and "x2" a tile that doubles what it merges with."""
    return Puzzle(
        tuple(
            tuple(None if word == "." else DOUBLE if word == "x2" else int(word) for word in line.split())
            for line in text.strip().splitlines()
            if line.strip()
        )
    )


# Typed in from examples/sumbreak/sumbreak1.png, the first daily board
# (2026-11-18). sumbreak2.png and sumbreak3.png show the same board with
# circles for tiles, which LinkedIn shows some guests instead of squares.
SUMBREAK1 = board("""
     1  1 64
     4  2 32
     4  4 16
""")

# Typed in from examples/sumbreak/sumbreak4.png: sumbreak1 three merges on,
# with two empty cells. The 4 on top has no neighbour left that it could ever
# merge with: a dead end, played on purpose to try the controls.
SUMBREAK4 = board("""
     .  4 64
     4  . 32
     4  4 16
""")

# Typed in from examples/sumbreak/sumbreak5.png, the daily board of
# 2026-11-20. Its two purple tiles show "x2" ("Multiply by 2" to a screen
# reader), and one cell is empty from the start. A guest won it with 7 merges
# ending in 32.
SUMBREAK5 = board("""
     1 x2  1
     .  4  1
    16 x2  4
""")
