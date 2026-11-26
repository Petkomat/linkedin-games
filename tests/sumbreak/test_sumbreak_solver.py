import pytest

from engines.sumbreak import DOUBLE, solve
from tests.helpers import solve_within

from .boards import SUMBREAK1, SUMBREAK5, SUMBREAK8, SUMBREAK10, board
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


def test_solves_the_sumbreak8_example_the_first_4x4_board():
    merges = solve(SUMBREAK8)

    assert_is_solution(SUMBREAK8, merges)
    assert list(tiles_after(SUMBREAK8, merges).values()) == [1024]


def test_solves_the_sumbreak10_example_whose_x4_tile_multiplies_what_it_meets_by_4():
    # 1 1 2 / 8 x4 2 / 32 8 4: the numbers add up to 58, so the x4 tile must
    # take a 2 (the two 1s merged), which adds 6 and makes 64.
    merges = solve(SUMBREAK10)

    assert list(tiles_after(SUMBREAK10, merges).values()) == [64]


@pytest.mark.parametrize(
    "text",
    [
        "1 2 \n 2 1",  # the 1s only touch at a corner
        "1 1 1",  # an odd 1 out: 3 is no 2, 4, 8, ...
        "2 2 . 4",  # the 4 sits across an empty cell from the 2s
        "4 x2 1",  # a x2 tile doubles one number, and then 8 and 1 or 4 and 2 are left
        "x2 x2",  # no board has shown that two x2 tiles merge, so they never are
    ],
)
def test_a_board_that_cant_end_in_one_tile_has_no_solution(text):
    assert solve(board(text)) is None


@pytest.mark.parametrize(
    "text",
    [
        "x2 1 2",  # only the x2 tile dragged onto the 1 leaves its 2 next to the 2
        "1 x2 \n . 2",  # only the 1 dragged onto the x2 tile leaves its 2 next to the 2
        "8 x2 \n 4 4",  # 4 + 4 meets the 8, and x2 doubles their 16
    ],
)
def test_a_x2_tile_merges_with_any_number_next_to_it_either_way_round(text):
    puzzle = board(text)

    assert_is_solution(puzzle, solve(puzzle))


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize(("n", "seconds"), [(3, 1.0), (5, 1.0), (7, 1.0), (8, 3.0)])
def test_solves_random_boards_small_and_large_quickly(n, seconds, seed):
    # The boards are crowded with small numbers, which pair up in the most ways.
    puzzle = random_puzzle(n, n, seed)

    assert_is_solution(puzzle, solve_within(solve, puzzle, seconds))


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize(("n", "doubles", "seconds"), [(3, 2, 1.0), (5, 3, 1.0), (7, 6, 2.0), (8, 8, 3.0)])
def test_solves_random_boards_with_x2_tiles_small_and_large_quickly(n, doubles, seconds, seed):
    # sumbreak5 has 2 on 3x3. A x2 tile goes with any number, so the more of
    # them, the more ways to try: an eighth of the cells on big boards.
    puzzle = random_puzzle(n, n, seed, doubles=doubles)

    assert sum(row.count(DOUBLE) for row in puzzle.numbers) == doubles
    assert_is_solution(puzzle, solve_within(solve, puzzle, seconds))


@pytest.mark.parametrize("seed", range(10))
def test_solves_boards_with_numbers_as_spread_out_as_sumbreak1s(seed):
    puzzle = random_puzzle(6, 6, seed, spread=3)

    assert_is_solution(puzzle, solve_within(solve, puzzle, seconds=1.0))
