import pytest

from engines.queens import Puzzle, solve
from tests.helpers import solve_within

from .boards import QUEENS1, regions
from .generator import random_puzzle


def assert_obeys_the_rules(puzzle: Puzzle, queens) -> None:
    n = puzzle.size
    assert queens is not None
    assert sorted(r for r, _ in queens) == list(range(n)), "one queen per row"
    assert sorted(c for _, c in queens) == list(range(n)), "one queen per column"
    assert len({puzzle.regions[r][c] for r, c in queens}) == n, "one queen per region"
    for i, (r1, c1) in enumerate(queens):
        for r2, c2 in queens[i + 1 :]:
            assert max(abs(r1 - r2), abs(c1 - c2)) > 1, f"{(r1, c1)} touches {(r2, c2)}"


def test_solves_the_queens1_example():
    # Solved by hand; the two queens already on the screenshot agree.
    assert solve(Puzzle(QUEENS1)) == [(0, 5), (1, 2), (2, 4), (3, 6), (4, 0), (5, 3), (6, 1)]


def test_every_region_needs_a_queen():
    # Five regions but only four queens fit: E would stay empty.
    five_regions = regions("""
        A A B B
        A A B B
        C C D E
        C C D D
    """)

    assert solve(Puzzle(five_regions)) is None


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("n", [12, 14, 16])
def test_solves_random_large_boards_quickly(n, seed):
    puzzle = random_puzzle(n, seed)

    assert_obeys_the_rules(puzzle, solve_within(solve, puzzle, seconds=1.0))
