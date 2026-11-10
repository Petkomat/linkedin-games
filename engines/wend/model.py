"""Domain model for LinkedIn Wend.

The board is a grid of letter tiles, some cells grey (no tile). Find the hidden
words of the given lengths: each word runs along a path of tiles, stepping up,
down, left or right, and every tile is used by exactly one word.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common import Cell

__all__ = ["Cell", "Grid", "Puzzle", "Word"]

Grid = tuple[tuple[str | None, ...], ...]  # rows of letters; None marks a grey cell


@dataclass(frozen=True)
class Puzzle:
    letters: Grid
    lengths: tuple[int, ...]  # lengths of the hidden words


@dataclass(frozen=True)
class Word:
    text: str
    path: tuple[Cell, ...]  # the tiles in reading order
