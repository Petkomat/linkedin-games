"""Boards shared by the sudoku tests."""

from tests.helpers import text_grid


def grid(text: str) -> tuple[tuple[int, ...], ...]:
    """Digits as text, '.' for an empty cell (see `text_grid`)."""
    return tuple(tuple(0 if ch == "." else int(ch) for ch in row) for row in text_grid(text))


# Typed in from examples/sudoku/sudoku1.png.
SUDOKU1 = grid("""
    . 2 3 | 4 5 6
    . 4 6 | 2 . 3
    . . 4 | . 6 1
    . . . | 3 2 4
    4 . . | . 3 5
    3 1 . | . . .
""")
