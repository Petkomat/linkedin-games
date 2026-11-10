"""The drag that enters a Zip solution the way a player draws it.

`walk` draws the path from 1 and backs up out of dead ends. The mouse follows
the end of that path: onto each cell the path moves to, and back again over
each cell it gives up.

On LinkedIn the path is drawn by pressing on 1 and dragging through the
cells. Moving back onto the cell before the end takes the end back.
"""

from __future__ import annotations

from ..common.actions import Action, Drag, Think
from ..common.trace import Put, traced
from .model import Cell, Puzzle
from .solver import walk


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(walk, puzzle)
    if steps is None:
        return None
    path: list[Cell] = []
    mouse: list[Cell] = []
    for step in steps:
        if isinstance(step, Think):
            continue  # one drag: the hand's own hesitations are in engines.play.motion
        if isinstance(step, Put):
            path.append(step.item)
        else:
            path.pop()
        mouse.append(path[-1])
    return [Think(), Drag(tuple(mouse))]
