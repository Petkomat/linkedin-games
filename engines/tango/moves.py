"""The clicks that enter a Tango solution the way the solver found it.

Cells are filled in the order the solver deduced or guessed them. When a guess
fails, the cells it led to are cleared again, newest first.

On LinkedIn a click moves a cell along empty -> sun -> moon -> empty.
"""

from __future__ import annotations

from ..common.actions import Action, Click, Think
from ..common.trace import Put, traced
from .model import Puzzle, Symbol
from .solver import solve

CLICKS_TO = {Symbol.SUN: 1, Symbol.MOON: 2}  # from empty to the symbol
CLICKS_BACK = {Symbol.SUN: 2, Symbol.MOON: 1}  # from the symbol back to empty


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(solve, puzzle)
    if steps is None:
        return None
    actions: list[Action] = []
    for step in steps:
        if isinstance(step, Think):
            actions.append(step)
            continue
        cell, symbol = step.item
        actions.append(Click(cell, (CLICKS_TO if isinstance(step, Put) else CLICKS_BACK)[symbol]))
    return actions
