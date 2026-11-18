"""The drags that enter a Sumbreak solution the way the solver found it.

Each merge is a drag from the tile onto its neighbour, which keeps the sum.
LinkedIn's Undo button takes back the last merge, so a guess that failed
after a few merges is taken back with that many clicks on Undo, newest first,
as the solver took it back.

On a big board the solver may take back dozens of merges. A person tries a
few things on the board and then thinks harder instead, so only the first
WRONG_MERGES merges that fail are made; the solver's later dead ends are
thought through without touching the board.
"""

from __future__ import annotations

from ..common.actions import Action, Button, Drag, Think
from ..common.trace import Put, Step, Take, traced
from .model import Puzzle
from .solver import solve

WRONG_MERGES = 5
UNDO = Button("Undo")


def moves(puzzle: Puzzle) -> list[Action] | None:
    steps = traced(solve, puzzle)
    if steps is None:
        return None
    actions: list[Action] = []
    shown: list[bool] = []  # for each merge on the board, newest last: was it made?
    wrong = 0
    failed = _failed(steps)
    for i, step in enumerate(steps):
        if isinstance(step, Think):
            actions.append(step)
        elif isinstance(step, Put):
            # A merge that fails is made while few have been, and only on top
            # of merges that were made too.
            made = i not in failed or (wrong < WRONG_MERGES and all(shown))
            wrong += made and i in failed
            shown.append(made)
            if made:
                actions.append(Drag((step.item.source, step.item.target)))
        elif shown.pop():
            actions.append(UNDO)
    return actions


def _failed(steps: list[Step]) -> set[int]:
    """The positions in `steps` of the merges that are taken back later."""
    on_board: list[int] = []
    failed = set()
    for i, step in enumerate(steps):
        if isinstance(step, Put):
            on_board.append(i)
        elif isinstance(step, Take):
            failed.add(on_board.pop())
    return failed
