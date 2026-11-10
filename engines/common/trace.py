"""The order in which a solver puts things on the board and takes them back.

A player who replays a trace makes the solver's guesses, wrong ones included,
and undoes them when they fail, instead of entering the answer in reading order.

Solvers call `put` for everything they place (a queen, a digit, a word) and,
when a guess fails, `back_to(mark)` to take off everything placed since
`mark()`, newest first. A depth-first search only ever undoes its latest
moves, so that is all a trace needs.

The trace is also cut into *thoughts*, each starting with a `Think`. A player
stops to think once per thought and then makes its moves in a quick burst:
- every lone `put` is a thought of its own;
- the puts inside `with trace.thought():` are one thought, e.g. the cells of a
  Tango line deduced together;
- taking back a failed guess with `back_to` is one thought.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from .actions import Think


@dataclass(frozen=True)
class Put:
    item: Hashable


@dataclass(frozen=True)
class Take:
    item: Hashable


Step = Put | Take | Think


class Trace:
    def __init__(self) -> None:
        self.steps: list[Step] = []
        self._on_board: list[Hashable] = []
        self._in_thought = False  # inside `with thought()`
        self._thought_begun = False  # ... and it has put something already

    def put(self, item: Hashable) -> None:
        if not (self._in_thought and self._thought_begun):
            self.steps.append(Think())
            self._thought_begun = self._in_thought
        self.steps.append(Put(item))
        self._on_board.append(item)

    def mark(self) -> int:
        return len(self._on_board)

    def back_to(self, mark: int) -> None:
        if len(self._on_board) > mark:
            self.steps.append(Think())
        while len(self._on_board) > mark:
            self.steps.append(Take(self._on_board.pop()))

    @contextmanager
    def thought(self) -> Iterator[None]:
        """Everything put inside is one thought. One that puts nothing leaves no trace."""
        self._in_thought, self._thought_begun = True, False
        try:
            yield
        finally:
            self._in_thought = self._thought_begun = False


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
        elif isinstance(step, Take):
            board.discard(step.item)
    return board
