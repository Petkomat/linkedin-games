"""Sumbreak's rules, as a check on any list of merges, for boards with many solutions."""

from __future__ import annotations

from engines.sumbreak import DOUBLE, Merge, Puzzle


def merged(dragged, onto):
    """What a merge leaves on the cell it is dropped on, as tried on LinkedIn
    on 2026-11-20: two equal numbers add up, and a x2 tile doubles the number
    it meets, whichever of them is dragged. Two x2 tiles don't merge."""
    assert DOUBLE in (dragged, onto) or dragged == onto, f"{dragged} and {onto} don't merge"
    assert (dragged, onto) != (DOUBLE, DOUBLE), "two x2 tiles don't merge"
    if dragged == DOUBLE:
        return 2 * onto
    if onto == DOUBLE:
        return 2 * dragged
    return dragged + onto


def tiles_after(puzzle: Puzzle, merges: list[Merge]) -> dict[tuple[int, int], int | str]:
    """The tiles left after making `merges` in order, failing on any merge the
    game wouldn't take."""
    tiles = puzzle.tiles()
    for merge in merges:
        (r1, c1), (r2, c2) = merge.source, merge.target
        assert abs(r1 - r2) + abs(c1 - c2) == 1, f"{merge}: not neighbours"
        assert merge.source in tiles and merge.target in tiles, f"{merge}: an empty cell"
        tiles[merge.target] = merged(tiles.pop(merge.source), tiles[merge.target])
    return tiles


def assert_is_solution(puzzle: Puzzle, merges) -> None:
    """Fail unless `merges` leave one tile on the board."""
    assert merges is not None
    assert len(tiles_after(puzzle, merges)) == 1, "one tile must remain"
