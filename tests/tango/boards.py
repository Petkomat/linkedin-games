"""Boards shared by the tango tests."""

from engines.tango import Symbol
from tests.helpers import text_grid

_SYMBOLS = {"S": Symbol.SUN, "M": Symbol.MOON, ".": None}


def board(text: str) -> tuple[tuple[Symbol | None, ...], ...]:
    """S for sun, M for moon, '.' for empty (see `text_grid`)."""
    return tuple(tuple(_SYMBOLS[ch] for ch in row) for row in text_grid(text))


def edges(*pairs: tuple[tuple[int, int], tuple[int, int]]) -> frozenset[frozenset[tuple[int, int]]]:
    return frozenset(frozenset(pair) for pair in pairs)


# Typed in from examples/tango/tango1.png (4x4, no = / x signs).
TANGO1 = board("""
    S . M .
    S . S .
    . M . S
    . S . S
""")

# Typed in from examples/tango/tango2.png (6x6, a game in progress). Only the
# grey cells are the puzzle; the symbols on white cells are the player's moves.
TANGO2 = board("""
    . . . . S S
    . . . . S M
    . . . . . .
    . . . . . .
    S M . . . .
    M M . . . .
""")
TANGO2_EQUAL = edges(((2, 0), (2, 1)), ((4, 3), (4, 4)), ((4, 3), (5, 3)))
TANGO2_OPPOSITE = edges(
    ((0, 2), (1, 2)),
    ((1, 1), (1, 2)),
    ((1, 1), (2, 1)),
    ((3, 4), (3, 5)),
    ((3, 4), (4, 4)),
)
