"""Backtracking search for Wend.

1. For every word length asked for, list each path of tiles that spells a word
   of that length (a *placement*). A path is abandoned as soon as its letters
   stop being the start of any such word.
2. Choose placements so that every tile is used exactly once and each length
   is used as often as asked (an exact cover). Branch on the free tile that
   the fewest placements can still cover: none means a dead end, and one
   means a forced move.

Every word the search places, and every word it drops again when it hits a
dead end, is written to `trace`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from ..common.bits import set_bits
from ..common.trace import Trace
from .dictionary import words_of_length
from .model import Cell, Puzzle, Word

Placement = tuple[int, Word]  # (mask of the tiles it uses, the word)


def solve(puzzle: Puzzle, trace: Trace | None = None) -> list[Word] | None:
    tiles = [
        (r, c)
        for r, row in enumerate(puzzle.letters)
        for c, letter in enumerate(row)
        if letter is not None
    ]
    if sum(puzzle.lengths) != len(tiles):
        return None
    bit = {cell: 1 << i for i, cell in enumerate(tiles)}
    covering: list[list[Placement]] = [[] for _ in tiles]
    for n in set(puzzle.lengths):
        for placement in _spelled_paths(puzzle, n, bit):
            for i in set_bits(placement[0]):
                covering[i].append(placement)
    trace = Trace() if trace is None else trace
    return _search(covering, Counter(puzzle.lengths), 0, (1 << len(tiles)) - 1, trace)


def _search(
    covering: list[list[Placement]], need: Counter[int], used: int, every_tile: int, trace: Trace
) -> list[Word] | None:
    if used == every_tile:
        return []
    fewest: list[Placement] | None = None
    for i in set_bits(every_tile & ~used):
        fits = [p for p in covering[i] if not p[0] & used and need[len(p[1].text)]]
        if fewest is None or len(fits) < len(fewest):
            fewest = fits
            if not fits:
                return None
    mark = trace.mark()
    for mask, word in fewest:
        trace.put(word)
        need[len(word.text)] -= 1
        rest = _search(covering, need, used | mask, every_tile, trace)
        need[len(word.text)] += 1
        if rest is not None:
            return [word, *rest]
        trace.back_to(mark)
    return None


def _spelled_paths(puzzle: Puzzle, n: int, bit: dict[Cell, int]) -> Iterator[tuple[int, Word]]:
    """(tile mask, word) for every path of n tiles that spells an n-letter word."""
    words, prefixes = words_of_length(n)
    letters = puzzle.letters

    def extend(path: list[Cell], text: str, mask: int) -> Iterator[tuple[int, Word]]:
        if len(path) == n:
            if text in words:
                yield mask, Word(text, tuple(path))
            return
        r, c = path[-1]
        for step in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if step in bit and not bit[step] & mask:
                longer = text + letters[step[0]][step[1]]
                if len(longer) == n or longer in prefixes:
                    path.append(step)
                    yield from extend(path, longer, mask | bit[step])
                    path.pop()

    for start in bit:
        first = letters[start[0]][start[1]]
        if first in prefixes:
            yield from extend([start], first, bit[start])
