"""Zip solutions as text."""

from __future__ import annotations

from ..common.text import board_text
from .model import Cell, Puzzle


def path_text(puzzle: Puzzle, path: list[Cell]) -> str:
    """Each cell shows when the path visits it (1 = the start), right-aligned."""
    order = {cell: i for i, cell in enumerate(path, start=1)}
    width = len(str(len(path)))
    return board_text([[str(order[r, c]).rjust(width) for c in range(puzzle.cols)] for r in range(puzzle.rows)])
