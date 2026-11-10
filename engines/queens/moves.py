"""The clicks that enter a Queens solution the way the solver found it.

Queens go down in the order the solver placed them, and its failed guesses are
placed and then taken off again, as a person trying things out would.

On LinkedIn a click moves a cell along empty -> X -> queen -> empty, so a
queen takes two clicks and taking it back one more.
"""

from __future__ import annotations

from ..common.actions import Action, Click, Think
from ..common.trace import Put, Step, traced
from .model import Puzzle
from .solver import solve

QUEEN_CLICKS = 2  # empty -> X -> queen
REMOVE_CLICKS = 1  # queen -> empty


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(solve, puzzle)
    if steps is None:
        return None
    return [_action(step) for step in steps]


def _action(step: Step) -> Action:
    if isinstance(step, Think):
        return step
    return Click(step.item, QUEEN_CLICKS if isinstance(step, Put) else REMOVE_CLICKS)
