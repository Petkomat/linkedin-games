"""Zip's rules, as a check on any path, for puzzles with many solutions."""

from engines.zip import Puzzle


def assert_is_solution(puzzle: Puzzle, path) -> None:
    """Fail unless `path` solves `puzzle`."""
    assert path is not None
    every_cell = [(r, c) for r in range(puzzle.rows) for c in range(puzzle.cols)]
    assert sorted(path) == every_cell, "must visit every cell exactly once"
    for a, b in zip(path, path[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, f"{a}->{b} is not a step"
        assert frozenset({a, b}) not in puzzle.walls, f"{a}->{b} crosses a wall"
    numbers_in_visit_order = [puzzle.numbers[c] for c in path if c in puzzle.numbers]
    assert numbers_in_visit_order == list(range(1, len(puzzle.numbers) + 1))
    assert path[0] in puzzle.numbers and path[-1] in puzzle.numbers
