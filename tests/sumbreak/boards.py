"""Boards shared by the Sumbreak tests."""

from __future__ import annotations

from engines.sumbreak import Puzzle


def board(text: str) -> Puzzle:
    """A board typed as numbers separated by spaces, one line per row; "." is an
    empty cell."""
    return Puzzle(
        tuple(
            tuple(None if word == "." else int(word) for word in line.split())
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
