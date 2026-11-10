"""The drags that enter a Wend solution the way the solver found it.

Words are dragged in the order the solver tried them, decoys included: real
words that aren't among the hidden ones.

On LinkedIn a word is entered by dragging from its first letter to its last.
The game knows the hidden words: one of them stays on the board once found,
and any other word is rejected and vanishes. So taking a word back needs no
input, and a hidden word the solver drops and later places again is already
on the board and isn't dragged twice.
"""

from __future__ import annotations

from ..common.actions import Action, Drag
from ..common.trace import Put, left_on_board, traced
from .model import Puzzle
from .solver import solve


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(solve, puzzle)
    if steps is None:
        return None
    hidden = left_on_board(steps)
    found = set()
    actions: list[Action] = []
    for step in steps:
        if isinstance(step, Put) and step.item not in found:
            actions.append(Drag(step.item.path))
            if step.item in hidden:
                found.add(step.item)
    return actions
