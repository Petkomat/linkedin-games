import pytest

from engines.sumbreak import solve
from tests.helpers import solve_within

from .boards import SUMBREAK1, SUMBREAK5, board
from .generator import random_puzzle
from .rules import assert_is_solution, tiles_after


def test_solves_the_sumbreak1_example():
    merges = solve(SUMBREAK1)

    assert_is_solution(SUMBREAK1, merges)
    assert len(merges) == 8


def test_solves_the_sumbreak5_example_whose_x2_tiles_double_what_they_meet():
    # 1 x2 1 / . 4 1 / 16 x2 4: the numbers add up to 27, so only doubling
    # makes one tile of them. A guest won it with 32 left.
    merges = solve(SUMBREAK5)

    assert list(tiles_after(SUMBREAK5, merges).values()) == [32]


@pytest.mark.parametrize(
    "text",
    [
        "1 2 \n 2 1",  # the 1s only touch at a corner
        "1 1 1",  # an odd 1 out: 3 is no 2, 4, 8, ...
        "2 2 . 4",  # the 4 sits across an empty cell from the 2s
    ],
)
def test_a_board_that_cant_end_in_one_tile_has_no_solution(text):
    assert solve(board(text)) is None


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize(("n", "seconds"), [(3, 1.0), (5, 1.0), (7, 1.0), (8, 3.0)])
def test_solves_random_boards_small_and_large_quickly(n, seconds, seed):
    # The boards are crowded with small numbers, which pair up in the most ways.
    puzzle = random_puzzle(n, n, seed)

    assert_is_solution(puzzle, solve_within(solve, puzzle, seconds))


@pytest.mark.parametrize("seed", range(10))
def test_solves_boards_with_numbers_as_spread_out_as_sumbreak1s(seed):
    puzzle = random_puzzle(6, 6, seed, spread=3)

    assert_is_solution(puzzle, solve_within(solve, puzzle, seconds=1.0))
