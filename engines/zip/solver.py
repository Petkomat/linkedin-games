"""Constraint-propagation search for a Zip path.

Instead of walking the path from 1, the solver decides for pairs of adjacent
cells whether the path runs between them (a *link*). Linked cells form path
*fragments*, which must stay consistent with the rules:

* every cell has exactly two links, except the path's ends (1 and N): one;
* a link may not close a fragment into a loop, nor join the fragment holding
  1 to the one holding N while cells are still left out;
* the numbers along a fragment are consecutive and in order: a piece of the
  final path that holds 3 and 5 must also hold 4, between them.

Whenever a cell has exactly as many usable links left as it still needs, it
takes all of them. Such forced links cascade from corners, walls and numbers
across the whole board; the search only branches (link or forbid one edge of
the most constrained cell) when propagation stalls.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..common.trace import Trace
from .model import Cell, Puzzle


def solve(puzzle: Puzzle) -> list[Cell] | None:
    board = _Board(puzzle)
    try:
        state = _State(board)
        state.propagate(range(board.size))
        solved = _search(state)
    except _Contradiction:
        return None
    return None if solved is None else [board.cell(i) for i in solved.path()]


def walk(puzzle: Puzzle, trace: Trace | None = None) -> list[Cell] | None:
    """Find the path by drawing it from 1, the way a player does.

    The path's end moves on one cell at a time, and backs up when every way
    on fails. The same propagation as in `solve` looks ahead: a step whose
    forced links lead to a contradiction is never taken, and links forced
    further along are simply followed. Every cell the end moves onto, and
    every cell it backs off, is written to `trace`.

    Branching only at the path's end, not at the most constrained cell, makes
    this slower than `solve` on big, sparse boards.
    """
    trace = Trace() if trace is None else trace
    board = _Board(puzzle)
    try:
        state = _State(board)
        state.propagate(range(board.size))
    except _Contradiction:
        return None
    trace.put(board.cell(board.start))
    path = _draw(state, [board.start], trace)
    return None if path is None else [board.cell(i) for i in path]


def _draw(state: _State, path: list[int], trace: Trace) -> list[int] | None:
    """`path` (the cells drawn so far, from 1) extended to a solution, or None."""
    if len(path) == state.board.size:
        return path
    end = path[-1]
    behind = path[-2] if len(path) > 1 else None
    forced = [cell for cell in state.links[end] if cell != behind]
    mark = trace.mark()
    for step in forced or state.options(end):
        attempt = state
        if not forced:
            attempt = state.copy()
            try:
                attempt.propagate(attempt.link(end, step))
            except _Contradiction:
                continue  # seen to fail at a glance, so never drawn
        trace.put(state.board.cell(step))
        found = _draw(attempt, [*path, step], trace)
        if found is not None:
            return found
        trace.back_to(mark)
    return None


class _Contradiction(Exception):
    """The partial solution can no longer be completed."""


class _Board:
    """Static facts about the puzzle; cells are indexed row-major."""

    def __init__(self, puzzle: Puzzle) -> None:
        self.cols = puzzle.cols
        self.size = puzzle.rows * puzzle.cols
        self.number: list[int | None] = [None] * self.size
        for (r, c), n in puzzle.numbers.items():
            self.number[r * self.cols + c] = n
        self.start = self.number.index(1)
        self.end = self.number.index(max(puzzle.numbers.values()))
        self.need = [2] * self.size
        self.need[self.start] = self.need[self.end] = 1
        self.adjacent = [
            [
                nr * self.cols + nc
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
                if 0 <= nr < puzzle.rows
                and 0 <= nc < puzzle.cols
                and frozenset({(r, c), (nr, nc)}) not in puzzle.walls
            ]
            for r in range(puzzle.rows)
            for c in range(puzzle.cols)
        ]

    def cell(self, index: int) -> Cell:
        return divmod(index, self.cols)


class _State:
    """Links decided so far, plus bookkeeping about the fragments they form.

    For a cell at the end of a fragment (a lone cell is a fragment of its own),
    `far_end` is the fragment's other end and `first`/`last` are the first and
    last number met when walking the fragment from this end (None if it holds
    no numbers). Entries for cells inside a fragment are stale and never read.
    """

    def __init__(self, board: _Board) -> None:
        self.board = board
        self.links: list[list[int]] = [[] for _ in range(board.size)]
        self.far_end = list(range(board.size))
        self.first = list(board.number)
        self.last = list(board.number)
        self.forbidden: set[tuple[int, int]] = set()
        self.link_count = 0

    def copy(self) -> _State:
        clone = object.__new__(_State)
        clone.board = self.board
        clone.links = [list(partners) for partners in self.links]
        clone.far_end = list(self.far_end)
        clone.first = list(self.first)
        clone.last = list(self.last)
        clone.forbidden = set(self.forbidden)
        clone.link_count = self.link_count
        return clone

    def is_complete(self) -> bool:
        # Loops are never allowed, so size - 1 links form one spanning path.
        return self.link_count == self.board.size - 1

    def room(self, cell: int) -> int:
        return self.board.need[cell] - len(self.links[cell])

    def options(self, cell: int) -> list[int]:
        """Neighbours `cell` could still be linked to."""
        return [
            other
            for other in self.board.adjacent[cell]
            if self.room(other) > 0
            and _edge(cell, other) not in self.forbidden
            and self._can_link(cell, other)
        ]

    def _can_link(self, a: int, b: int) -> bool:
        end_a, end_b = self.far_end[a], self.far_end[b]
        if end_a == b:  # same fragment: the link would close a loop
            return False
        board = self.board
        joins_both_path_ends = {end_a, end_b} == {board.start, board.end}
        if joins_both_path_ends and self.link_count + 1 < board.size - 1:
            return False
        return _numbers_continue(
            (self.first[end_a], self.last[end_a]), (self.first[b], self.last[b])
        )

    def link(self, a: int, b: int) -> list[int]:
        """Link two fragment ends; returns the cells whose options changed."""
        end_a, end_b = self.far_end[a], self.far_end[b]
        first = self.first[end_a] if self.first[end_a] is not None else self.first[b]
        last = self.last[b] if self.last[b] is not None else self.last[end_a]
        self.links[a].append(b)
        self.links[b].append(a)
        self.far_end[end_a], self.far_end[end_b] = end_b, end_a
        self.first[end_a], self.last[end_a] = first, last
        self.first[end_b], self.last[end_b] = last, first
        self.link_count += 1
        return self._around(a, b, end_a, end_b)

    def forbid(self, a: int, b: int) -> list[int]:
        """Rule out linking a and b; returns the cells whose options changed."""
        self.forbidden.add(_edge(a, b))
        return self._around(a, b)

    def _around(self, *cells: int) -> list[int]:
        touched = list(cells)
        for cell in cells:
            touched.extend(self.board.adjacent[cell])
        return touched

    def propagate(self, cells: Iterable[int]) -> None:
        """Take every forced link reachable from `cells`, or raise _Contradiction."""
        queue = list(cells)
        while queue:
            cell = queue.pop()
            room = self.room(cell)
            if room == 0:
                continue
            options = self.options(cell)
            if len(options) < room:
                raise _Contradiction
            if len(options) > room:
                continue
            for other in options:
                # Taking one forced link can invalidate the other one.
                if self.room(other) == 0 or not self._can_link(cell, other):
                    raise _Contradiction
                queue.extend(self.link(cell, other))

    def branching_edge(self) -> tuple[int, int]:
        """An edge of the cell with the fewest spare options."""
        best: tuple[int, int, int] | None = None
        for cell in range(self.board.size):
            room = self.room(cell)
            if room == 0:
                continue
            options = self.options(cell)
            spare = len(options) - room
            if spare < 0:
                raise _Contradiction
            if best is None or spare < best[0]:
                best = (spare, cell, options[0])
        assert best is not None, "an incomplete state has a cell with room"
        return best[1], best[2]

    def path(self) -> list[int]:
        path, previous = [self.board.start], None
        while len(path) < self.board.size:
            current = path[-1]
            following = next(n for n in self.links[current] if n != previous)
            path.append(following)
            previous = current
        return path


def _search(state: _State) -> _State | None:
    if state.is_complete():
        return state
    cell, other = state.branching_edge()
    for decide in (_State.link, _State.forbid):
        attempt = state.copy()
        try:
            attempt.propagate(decide(attempt, cell, other))
        except _Contradiction:
            continue
        solved = _search(attempt)
        if solved is not None:
            return solved
    return None


def _numbers_continue(
    before: tuple[int | None, int | None], after: tuple[int | None, int | None]
) -> bool:
    """Can a fragment numbered `before` be followed by one numbered `after`?

    Each argument is the (first, last) number met walking in path direction.
    """
    if before[0] is None or after[0] is None:
        return True
    (first_a, last_a), (first_b, last_b) = before, after
    ascending = first_a <= last_a and first_b == last_a + 1 and first_b <= last_b
    descending = first_a >= last_a and first_b == last_a - 1 and first_b >= last_b
    return ascending or descending


def _edge(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)
