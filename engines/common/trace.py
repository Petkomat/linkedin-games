"""The order in which a solver puts things on the board and takes them back.

A player who replays a trace makes the solver's guesses, wrong ones included,
and undoes them when they fail, instead of entering the answer in reading order.

Solvers call `put` for everything they place (a queen, a digit, a word) and,
when a guess fails, `back_to(mark)` to take off everything placed since
`mark()`, newest first. A depth-first search only ever undoes its latest
moves, so that is all a trace needs.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Put:
    item: Hashable


@dataclass(frozen=True)
class Take:
    item: Hashable


Step = Put | Take


class Trace:
    def __init__(self) -> None:
        self.steps: list[Step] = []
        self._on_board: list[Hashable] = []

    def put(self, item: Hashable) -> None:
        self.steps.append(Put(item))
        self._on_board.append(item)

    def mark(self) -> int:
        return len(self._on_board)

    def back_to(self, mark: int) -> None:
        while len(self._on_board) > mark:
            self.steps.append(Take(self._on_board.pop()))


def traced(solve: Callable[[Any, Trace], Any | None], puzzle: Any) -> list[Step] | None:
    """The steps `solve` took to solve `puzzle`, or None if it has no solution."""
    trace = Trace()
    return None if solve(puzzle, trace) is None else trace.steps


def left_on_board(steps: list[Step]) -> set[Hashable]:
    """What is still on the board after `steps`: the solution."""
    board: set[Hashable] = set()
    for step in steps:
        if isinstance(step, Put):
            board.add(step.item)
        else:
            board.discard(step.item)
    return board
