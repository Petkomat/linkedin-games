"""Sumbreak's rules, as a check on any list of merges, for boards with many solutions."""

from __future__ import annotations

from engines.sumbreak import Merge, Puzzle


def tiles_after(puzzle: Puzzle, merges: list[Merge]) -> dict[tuple[int, int], int]:
    """The tiles left after making `merges` in order, failing on any merge the
    game wouldn't take."""
    tiles = {
        (r, c): number
        for r, row in enumerate(puzzle.numbers)
        for c, number in enumerate(row)
        if number is not None
    }
    for merge in merges:
        (r1, c1), (r2, c2) = merge.source, merge.target
        assert abs(r1 - r2) + abs(c1 - c2) == 1, f"{merge}: not neighbours"
        assert merge.source in tiles and merge.target in tiles, f"{merge}: an empty cell"
        assert tiles[merge.source] == tiles[merge.target], f"{merge}: different numbers"
        tiles[merge.target] += tiles.pop(merge.source)
    return tiles


def assert_is_solution(puzzle: Puzzle, merges) -> None:
    """Fail unless `merges` leave one tile on the board."""
    assert merges is not None
    assert len(tiles_after(puzzle, merges)) == 1, "one tile must remain"
