"""The clicks and key presses that enter a Mini Sudoku solution the way the
solver found it.

Digits are typed in the order the solver settled them, by deduction or by a
guess. When a guess fails, the cells it led to are emptied again, newest first.

On LinkedIn a click selects a cell, a digit key fills it in and Backspace
empties it.
"""

from __future__ import annotations

from ..common.actions import Action, Click, Press, Think
from ..common.trace import Put, traced
from .model import Puzzle
from .solver import solve

ERASE = "Backspace"


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(solve, puzzle)
    if steps is None:
        return None
    actions: list[Action] = []
    for step in steps:
        if isinstance(step, Think):
            actions.append(step)
            continue
        (r, c), digit = step.item
        if puzzle.grid[r][c]:
            continue  # a given: the solver settles it too, but it's already on the board
        actions += [Click((r, c)), Press(str(digit) if isinstance(step, Put) else ERASE)]
    return actions
