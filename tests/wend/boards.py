"""Boards shared by the wend tests."""

from engines.wend import Word
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

# Solved by hand: the top row bends down into WISDOM, FOUND runs along the
# bottom, and DONE climbs the right edge.
WEND1_ANSWER = {
    Word("WIN", ((1, 0), (2, 0), (2, 1))),
    Word("DONE", ((4, 4), (3, 4), (2, 4), (2, 3))),
    Word("FOUND", ((3, 0), (4, 0), (4, 1), (4, 2), (4, 3))),
    Word("WISDOM", ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 4))),
}

# Solved by hand. The H can only join O, so it starts HOLD; that leaves W-I-N
# in the corner, ALIGN around the L, and ENGINE on the right.
WEND2_ANSWER = {
    Word("WIN", ((0, 0), (1, 0), (2, 0))),
    Word("HOLD", ((3, 2), (3, 3), (3, 4), (4, 4))),
    Word("ALIGN", ((1, 1), (2, 1), (3, 1), (3, 0), (4, 0))),
    Word("ENGINE", ((1, 2), (1, 3), (2, 3), (2, 4), (1, 4), (0, 4))),
}
