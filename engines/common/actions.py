"""What a player does to a board, in cells: the input a game's moves are made of.

Moves are kept in board terms so they can be tested without a browser; the
player in engines.play turns cells into mouse positions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import Cell


@dataclass(frozen=True)
class Click:
    """Click a cell `times` times in a row."""

    cell: Cell
    times: int = 1


@dataclass(frozen=True)
class Drag:
    """Press the mouse on the first cell, move through the others in order and
    release it on the last."""

    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class Press:
    """Press a key, named as Playwright names them: "4", "Backspace"."""

    key: str


@dataclass(frozen=True)
class Think:
    """Stop to think: the moves after it, up to the next Think, come from one
    deduction (or one guess) and are made in a quick burst."""


Action = Click | Drag | Press | Think
