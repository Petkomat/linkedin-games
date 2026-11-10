"""Line-pattern solver for Tango.

Every row and column is a *line* with a list of candidate *patterns*: n-bit
masks (bit i = 1 means sun on the line's i-th cell) with n/2 suns, no three
equal neighbours, and agreeing with the '=' / 'x' signs inside that line. All
signs sit between neighbours, so every sign lies inside exactly one line.

Propagation: drop a line's patterns that clash with its known cells. A cell on
which all remaining patterns agree is fixed, which narrows the crossing line,
and so on. A line with no pattern left is a dead end.

Search: as in the other solvers, branch on the line with the fewest patterns
left, trying each of them. The search stops at the first solution. Every cell
it fills in, by deduction or by a guess, and every cell it clears again when a
guess fails is written to `trace`. The cells one line settles at once are
one thought.
"""

from __future__ import annotations

from functools import cache, reduce
from operator import and_, or_

from ..common.trace import Trace
from .model import Grid, Puzzle, Symbol

Cells = list[int | None]  # per cell (row-major): 1 sun, 0 moon, None unknown


def solve(puzzle: Puzzle, trace: Trace | None = None) -> Grid | None:
    trace = Trace() if trace is None else trace
    n = puzzle.size
    if n % 2:
        return None
    lines = [tuple(r * n + c for c in range(n)) for r in range(n)]
    lines += [tuple(r * n + c for r in range(n)) for c in range(n)]
    crossing = [(n + cell % n, cell // n) for cell in range(n * n)]  # (column, row) line ids

    patterns = [_with_signs(_patterns(n), _signs_in(puzzle, line, n)) for line in lines]
    cells: Cells = [
        None if s is None else int(s is Symbol.SUN) for row in puzzle.givens for s in row
    ]

    def propagate(patterns: list[list[int]], cells: Cells, queue: set[int]) -> bool:
        while queue:
            line = queue.pop()
            known = mask = 0
            for i, cell in enumerate(lines[line]):
                if cells[cell] is not None:
                    mask |= 1 << i
                    known |= cells[cell] << i
            kept = [p for p in patterns[line] if not (p ^ known) & mask]
            if not kept:
                return False
            patterns[line] = kept
            always, ever = reduce(and_, kept), reduce(or_, kept)
            with trace.thought():  # the cells this line settles are seen together
                for i, cell in enumerate(lines[line]):
                    if cells[cell] is None and (always >> i & 1 or not ever >> i & 1):
                        cells[cell] = always >> i & 1
                        trace.put((divmod(cell, n), Symbol.SUN if cells[cell] else Symbol.MOON))
                        queue.update(crossing[cell])
        return True

    def search(patterns: list[list[int]], cells: Cells) -> Cells | None:
        open_lines = [line for line, options in enumerate(patterns) if len(options) > 1]
        if not open_lines:
            return cells
        line = min(open_lines, key=lambda line: len(patterns[line]))
        mark = trace.mark()
        for pattern in patterns[line]:
            trial_patterns, trial_cells = patterns.copy(), cells.copy()
            trial_patterns[line] = [pattern]
            if propagate(trial_patterns, trial_cells, {line}):
                solved = search(trial_patterns, trial_cells)
                if solved is not None:
                    return solved
            trace.back_to(mark)
        return None

    if not propagate(patterns, cells, set(range(2 * n))):
        return None
    solved = search(patterns, cells)
    if solved is None:
        return None
    symbols = [Symbol.SUN if v else Symbol.MOON for v in solved]
    return tuple(tuple(symbols[r * n : (r + 1) * n]) for r in range(n))


@cache
def _patterns(n: int) -> tuple[int, ...]:
    """All n-bit lines with n/2 suns and no three equal neighbours."""
    full = (1 << n) - 1
    return tuple(
        p
        for p in range(1 << n)
        if p.bit_count() == n // 2
        and not p & p >> 1 & p >> 2
        and not (q := ~p & full) & q >> 1 & q >> 2
    )


def _signs_in(puzzle: Puzzle, line: tuple[int, ...], n: int) -> list[tuple[int, bool]]:
    """(i, same) for each sign between the line's i-th and (i+1)-th cells."""
    signs = []
    for i in range(n - 1):
        edge = frozenset({divmod(line[i], n), divmod(line[i + 1], n)})
        if edge in puzzle.equal:
            signs.append((i, True))
        elif edge in puzzle.opposite:
            signs.append((i, False))
    return signs


def _with_signs(patterns: tuple[int, ...], signs: list[tuple[int, bool]]) -> list[int]:
    return [p for p in patterns if all(((p >> i ^ p >> (i + 1)) & 1) != same for i, same in signs)]
