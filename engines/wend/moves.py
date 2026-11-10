"""The drags and clicks that enter a Wend solution the way the solver found it.

Words are dragged in the order the solver tried them, decoys included: real
words that aren't among the hidden ones. A decoy the solver drops is removed
again.

On LinkedIn a word is entered by dragging from its first letter to its last.
Any real word stays on the board. A hidden word gets a tick: it is correct,
and it can't and mustn't be removed. Any other word is removed by clicking its
first letter. A decoy left on the board gets in the way: starting the next
drag on one of its tiles extends it instead (ESS + T became TESS on the first
live run).

The solver doesn't see the ticks, so it sometimes drops a hidden word and
places it again later, or tries a decoy across a hidden word's tiles. A player
who sees the tick would do neither. So a ticked word stays and is dragged only
once, and a decoy that would cross it is not tried.
"""

from __future__ import annotations

from ..common.actions import Action, Click, Drag, Think
from ..common.trace import Put, left_on_board, traced
from .model import Puzzle, Word
from .solver import solve


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(solve, puzzle)
    if steps is None:
        return None
    hidden = left_on_board(steps)  # the solution: these get a tick
    ticked: set[Word] = set()
    not_tried: set[Word] = set()  # decoys across a ticked word
    actions: list[Action] = []
    for step in steps:
        if isinstance(step, Think):
            actions.append(step)
            continue
        word = step.item
        if isinstance(step, Put):
            if word in ticked:
                continue
            if any(set(word.path) & set(other.path) for other in ticked):
                not_tried.add(word)
                continue
            actions.append(Drag(word.path))
            if word in hidden:
                ticked.add(word)
        elif word in not_tried:
            not_tried.discard(word)
        elif word not in ticked:
            actions.append(Click(word.path[0]))
    return actions
