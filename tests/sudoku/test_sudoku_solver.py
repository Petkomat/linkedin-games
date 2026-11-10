import pytest

from engines.sudoku import Puzzle, solve
from tests.helpers import solve_within

from .boards import SUDOKU1, grid


def test_solves_the_sudoku1_example():
    # Solved by hand from examples/sudoku/sudoku1.png (6x6, boxes of 2 rows x 3 columns).
    assert solve(Puzzle(SUDOKU1)) == grid("""
        1 2 3 | 4 5 6
        5 4 6 | 2 1 3
        2 3 4 | 5 6 1
        6 5 1 | 3 2 4
        4 6 2 | 1 3 5
        3 1 5 | 6 4 2
    """)


def test_contradictory_givens_have_no_solution():
    # The sudoku1 answer with the first two digits swapped: rows still fine,
    # but columns 0 and 1 now hold two 2s and two 1s.
    swapped = grid("""
        2 1 3 | 4 5 6
        5 4 6 | 2 1 3
        2 3 4 | 5 6 1
        6 5 1 | 3 2 4
        4 6 2 | 1 3 5
        3 1 5 | 6 4 2
    """)

    assert solve(Puzzle(swapped)) is None


HARD_9X9 = {
    "inkala_2012": "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..",
    "anti_brute_force": "..............3.85..1.2.......5.7.....4...1...9.......5......73..2.1........4...9",
    "ai_escargot": "1....7.9..3..2...8..96..5....53..9...1..8...26....4...3......1..4......7..7...3..",
    "easter_monster": "1.......2.9.4...5...6...7...5.9.3.......7.......85..4.7.....6...3...9.8...2.....1",
}


def assert_is_completion(puzzle: Puzzle, answer) -> None:
    n = puzzle.size
    digits = set(range(1, n + 1))
    box_rows, box_cols = puzzle.box
    assert answer is not None
    for r in range(n):
        for c in range(n):
            assert puzzle.grid[r][c] in (0, answer[r][c]), f"given at {(r, c)} changed"
    for i in range(n):
        assert set(answer[i]) == digits, f"row {i}"
        assert {answer[r][i] for r in range(n)} == digits, f"column {i}"
        top, left = box_rows * (i // (n // box_cols)), box_cols * (i % (n // box_cols))
        box = {answer[r][c] for r in range(top, top + box_rows) for c in range(left, left + box_cols)}
        assert box == digits, f"box {i}"


@pytest.mark.parametrize("name", HARD_9X9)
def test_solves_famously_hard_9x9_sudokus_quickly(name):
    line = HARD_9X9[name]
    puzzle = Puzzle(tuple(tuple(int(ch) if ch != "." else 0 for ch in line[i : i + 9]) for i in range(0, 81, 9)))

    assert_is_completion(puzzle, solve_within(solve, puzzle, seconds=1.0))
