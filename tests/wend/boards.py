"""Boards shared by the wend tests."""

from tests.helpers import text_grid


def letters(text: str) -> tuple[tuple[str | None, ...], ...]:
    """One letter per tile, '#' for a grey (blocked) cell (see `text_grid`)."""
    return tuple(tuple(None if ch == "#" else ch for ch in row) for row in text_grid(text))


# Typed in from examples/wend/wend1.png. Its list of word lengths is cropped
# off; the words found by hand are 3, 4, 5 and 6 letters long.
WEND1 = letters("""
    W I S D O
    W # # # M
    I N # E N
    F # # # O
    O U N D D
""")

# Typed in from examples/wend/wend2.png: words of 3, 4, 5 and 6 letters.
WEND2 = letters("""
    W # # # E
    I A E N N
    N L # G I
    G I H O L
    N # # # D
""")
