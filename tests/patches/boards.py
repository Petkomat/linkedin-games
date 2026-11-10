"""Boards shared by the patches tests."""

from engines.patches import Rect, Root, Shape

# examples/patches/patches3.png, which shows the board already solved. Roots
# are named by their colour.
PATCHES3_ROOTS = {
    "blue": Root(0, 1, Shape.ANY, 5),
    "gold": Root(0, 3, Shape.ANY, 3),
    "orange": Root(1, 5, Shape.ANY, 3),
    "red": Root(2, 0, Shape.ANY, 3),
    "purple": Root(2, 2, Shape.WIDE),
    "green": Root(3, 3, Shape.SQUARE),
    "teal": Root(3, 5, Shape.ANY, 3),
    "gray": Root(4, 0, Shape.ANY, 3),
    "magenta": Root(5, 2, Shape.ANY, 3),
    "brown": Root(5, 4, Shape.ANY, 3),
}
PATCHES3_ANSWER = {
    "red": Rect(0, 0, 3, 1),
    "blue": Rect(0, 1, 5, 1),
    "gold": Rect(0, 2, 1, 3),
    "orange": Rect(0, 5, 3, 1),
    "purple": Rect(1, 2, 2, 3),
    "gray": Rect(3, 0, 3, 1),
    "green": Rect(3, 2, 2, 2),
    "brown": Rect(3, 4, 3, 1),
    "teal": Rect(3, 5, 3, 1),
    "magenta": Rect(5, 1, 1, 3),
}
