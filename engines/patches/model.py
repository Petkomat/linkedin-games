"""Domain model for LinkedIn Patches.

A puzzle is a grid with a set of *roots*: marked cells, each of which must end
up in exactly one rectangle ("patch") of the root's shape and, if given, size.
The patches must tile the whole grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Shape(Enum):
    SQUARE = "square"  # height == width
    TALL = "tall"  # height > width
    WIDE = "wide"  # width > height
    ANY = "any"  # any of the above


@dataclass(frozen=True)
class Root:
    row: int
    col: int
    shape: Shape
    size: int | None = None  # required area, if the badge shows a number


@dataclass(frozen=True)
class Rect:
    top: int
    left: int
    height: int
    width: int


@dataclass(frozen=True)
class Puzzle:
    rows: int
    cols: int
    roots: tuple[Root, ...]
