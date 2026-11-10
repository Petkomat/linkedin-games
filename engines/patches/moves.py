"""The drags and clicks that enter a Patches solution the way the solver found it.

Patches are drawn in the order the solver placed them. When a guess fails, the
patches it led to are removed again, newest first.

On LinkedIn a patch is drawn by dragging from one of its corners to the
opposite one, and clicking a patch removes it.
"""

from __future__ import annotations

from ..common.actions import Action, Click, Drag, Think
from ..common.trace import Put, Step, traced
from .model import Puzzle, Rect
from .solver import solve


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(solve, puzzle)
    if steps is None:
        return None
    return [_action(step) for step in steps]


def _action(step: Step) -> Action:
    if isinstance(step, Think):
        return step
    return _draw(step.item) if isinstance(step, Put) else _remove(step.item)


def _draw(rect: Rect) -> Drag:
    return Drag(((rect.top, rect.left), (rect.top + rect.height - 1, rect.left + rect.width - 1)))


def _remove(rect: Rect) -> Click:
    return Click((rect.top, rect.left))
