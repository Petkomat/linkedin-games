from engines.zip import Puzzle, solve
from tests.helpers import solve_within


def assert_is_solution(puzzle: Puzzle, path) -> None:
    """Check `path` against the rules of Zip, for puzzles with many solutions."""
    assert path is not None
    every_cell = [(r, c) for r in range(puzzle.rows) for c in range(puzzle.cols)]
    assert sorted(path) == every_cell, "must visit every cell exactly once"
    for a, b in zip(path, path[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, f"{a}->{b} is not a step"
        assert frozenset({a, b}) not in puzzle.walls, f"{a}->{b} crosses a wall"
    numbers_in_visit_order = [puzzle.numbers[c] for c in path if c in puzzle.numbers]
    assert numbers_in_visit_order == list(range(1, len(puzzle.numbers) + 1))
    assert path[0] in puzzle.numbers and path[-1] in puzzle.numbers


def test_two_adjacent_numbers_are_joined_directly():
    puzzle = Puzzle(rows=1, cols=2, numbers={(0, 0): 1, (0, 1): 2})

    assert solve(puzzle) == [(0, 0), (0, 1)]


def test_path_detours_through_every_empty_cell():
    puzzle = Puzzle(rows=2, cols=2, numbers={(0, 0): 1, (1, 0): 2})

    assert solve(puzzle) == [(0, 0), (0, 1), (1, 1), (1, 0)]


def test_numbers_are_visited_in_increasing_order():
    # Only two paths cover this 3x3 grid from (0,0) to (2,0); the other one
    # reaches 3 at (1,1) before 2 at (0,2).
    puzzle = Puzzle(
        rows=3, cols=3, numbers={(0, 0): 1, (0, 2): 2, (1, 1): 3, (2, 0): 4}
    )

    assert solve(puzzle) == [
        (0, 0), (0, 1), (0, 2),
        (1, 2), (2, 2), (2, 1),
        (1, 1), (1, 0), (2, 0),
    ]  # fmt: skip


def test_unsolvable_puzzle_has_no_solution():
    # A 2x2 grid cannot be covered by a path between diagonal corners.
    puzzle = Puzzle(rows=2, cols=2, numbers={(0, 0): 1, (1, 1): 2})

    assert solve(puzzle) is None


def test_path_never_crosses_a_wall():
    # Without the wall, the path could also start by going down from (0,0).
    puzzle = Puzzle(
        rows=3,
        cols=3,
        numbers={(0, 0): 1, (2, 0): 2},
        walls={frozenset({(0, 0), (1, 0)})},
    )

    assert solve(puzzle) == [
        (0, 0), (0, 1), (0, 2),
        (1, 2), (2, 2), (2, 1),
        (1, 1), (1, 0), (2, 0),
    ]  # fmt: skip


def test_solves_example_zip1():
    # examples/zip/zip1.png
    puzzle = Puzzle(
        rows=6,
        cols=6,
        numbers={
            (0, 0): 1, (5, 5): 2, (4, 1): 3, (2, 1): 4,
            (3, 4): 5, (3, 2): 6, (1, 4): 7, (2, 3): 8,
        },
    )  # fmt: skip

    assert solve(puzzle) == [
        (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0),
        (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
        (4, 5), (4, 4), (4, 3), (4, 2), (4, 1),
        (3, 1), (2, 1), (1, 1), (0, 1),
        (0, 2), (0, 3), (0, 4), (0, 5),
        (1, 5), (2, 5), (3, 5), (3, 4), (3, 3), (3, 2),
        (2, 2), (1, 2), (1, 3), (1, 4), (2, 4), (2, 3),
    ]  # fmt: skip


def test_solves_example_zip2_with_walls():
    # examples/zip/zip2.jpg
    puzzle = Puzzle(
        rows=6,
        cols=6,
        numbers={
            (1, 1): 1, (0, 5): 2, (1, 4): 3, (2, 3): 4,
            (4, 4): 5, (4, 1): 6, (3, 2): 7, (5, 0): 8,
        },
        walls={
            frozenset({(1, 1), (1, 2)}),
            frozenset({(1, 2), (1, 3)}),
            frozenset({(1, 4), (2, 4)}),
            frozenset({(2, 1), (3, 1)}),
            frozenset({(2, 2), (3, 2)}),
            frozenset({(2, 3), (3, 3)}),
            frozenset({(2, 4), (3, 4)}),
            frozenset({(3, 1), (4, 1)}),
            frozenset({(4, 2), (4, 3)}),
            frozenset({(4, 3), (4, 4)}),
        },
    )  # fmt: skip

    assert solve(puzzle) == [
        (1, 1), (0, 1), (0, 0), (1, 0), (2, 0), (2, 1), (2, 2),
        (1, 2), (0, 2), (0, 3), (0, 4), (0, 5),
        (1, 5), (1, 4), (1, 3), (2, 3), (2, 4), (2, 5),
        (3, 5), (4, 5), (5, 5), (5, 4), (4, 4),
        (3, 4), (3, 3), (4, 3), (5, 3), (5, 2), (5, 1), (4, 1),
        (4, 2), (3, 2), (3, 1), (3, 0), (4, 0), (5, 0),
    ]  # fmt: skip


def test_solves_a_sparse_8x8_quickly():
    # Few numbers on a big grid leave a huge search space; plain backtracking
    # needs minutes here.
    puzzle = Puzzle(
        rows=8,
        cols=8,
        numbers={
            (3, 4): 1, (7, 7): 2, (4, 7): 3, (1, 7): 4,
            (4, 0): 5, (6, 3): 6, (4, 3): 7, (1, 3): 8,
        },
    )  # fmt: skip

    path = solve_within(solve, puzzle, seconds=2.0)

    assert_is_solution(puzzle, path)


def test_solves_a_10x10_quickly():
    puzzle = Puzzle(
        rows=10,
        cols=10,
        numbers={
            (4, 3): 1, (4, 4): 2, (6, 5): 3, (2, 8): 4, (7, 6): 5, (8, 6): 6,
            (8, 9): 7, (9, 8): 8, (9, 7): 9, (8, 4): 10, (9, 4): 11, (5, 1): 12,
            (6, 1): 13, (7, 1): 14, (5, 2): 15, (1, 5): 16, (0, 4): 17, (1, 7): 18,
        },
    )  # fmt: skip

    path = solve_within(solve, puzzle, seconds=2.0)

    assert_is_solution(puzzle, path)
