"""Boards shared by the queens tests."""

from tests.helpers import text_grid


def regions(text: str) -> tuple[tuple[int, ...], ...]:
    """A region map typed as one letter per cell; letters become 0, 1, 2, ..."""
    labels: dict[str, int] = {}
    return tuple(
        tuple(labels.setdefault(ch, len(labels)) for ch in row) for row in text_grid(text)
    )


# Typed in from examples/queens/queens1.png: Purple, Orange, Green, Blue,
# Whitish grey, Red, Yellow.
QUEENS1 = regions("""
    P P O O O B B
    P O O G O O B
    P O G G G O W
    P O O G O O W
    P R O O O R R
    R R R Y R R R
    R R R R R R R
""")

# Typed in from examples/queens/queens2.png, a full LinkedIn page on a
# high-resolution screen (8x8): Purple, Orange, Blue, Green, Whitish grey, Red,
# Yellow, Tan.
QUEENS2 = regions("""
    P O O B G G G W
    P P O B B G G W
    R P P P P G G W
    R R P P P P G W
    Y Y P P P P G P
    T Y P P P P P P
    T T T P P P P P
    T T T T T P P P
""")
