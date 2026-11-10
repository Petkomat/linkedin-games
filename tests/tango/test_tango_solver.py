import pytest

from engines.tango import Puzzle, Symbol, solve
from tests.helpers import solve_within

from .boards import TANGO1, TANGO2, TANGO2_EQUAL, TANGO2_OPPOSITE, board
from .generator import random_puzzle


def assert_obeys_the_rules(puzzle: Puzzle, answer) -> None:
    n = puzzle.size
    assert answer is not None
    lines = [list(row) for row in answer] + [[answer[r][c] for r in range(n)] for c in range(n)]
    for line in lines:
        assert line.count(Symbol.SUN) == line.count(Symbol.MOON) == n // 2, line
        assert not any(line[i] == line[i + 1] == line[i + 2] for i in range(n - 2)), line
    for r in range(n):
        for c in range(n):
            assert puzzle.givens[r][c] in (None, answer[r][c]), f"given at {(r, c)} changed"
    for edge in puzzle.equal | puzzle.opposite:
        (r1, c1), (r2, c2) = edge
        same = answer[r1][c1] == answer[r2][c2]
        assert same == (edge in puzzle.equal), f"sign at {sorted(edge)} broken"


def test_solves_the_tango1_example():
    # Solved by hand from the screenshot.
    assert solve(Puzzle(TANGO1)) == board("""
        S S M M
        S M S M
        M M S S
        M S M S
    """)


def test_solves_the_tango2_example_with_signs():
    # The player's moves in the screenshot, with the six empty cells finished
    # by hand.
    puzzle = Puzzle(TANGO2, equal=TANGO2_EQUAL, opposite=TANGO2_OPPOSITE)

    assert solve(puzzle) == board("""
        M S M M S S
        S M S M S M
        S S M S M M
        M S S M M S
        S M M S S M
        M M S S M S
    """)


def test_contradictory_givens_have_no_solution():
    # The tango1 answer with (0,1) and (0,2) swapped: columns 1 and 2 now
    # hold three moons and three suns in a row.
    swapped = board("""
        S M S M
        S M S M
        M M S S
        M S M S
    """)

    assert solve(Puzzle(swapped)) is None


def test_signs_decide_the_board():
    # Only (0,0) is given. Brute force over all 4x4 boards shows these four
    # signs leave exactly one answer; ignoring them leaves 45.
    puzzle = Puzzle(
        board("""
            S . . .
            . . . .
            . . . .
            . . . .
        """),
        equal=frozenset({
            frozenset({(0, 0), (0, 1)}),
            frozenset({(0, 0), (1, 0)}),
            frozenset({(1, 2), (2, 2)}),
        }),
        opposite=frozenset({frozenset({(0, 1), (0, 2)})}),
    )

    assert solve(puzzle) == board("""
        S S M M
        S M S M
        M M S S
        M S M S
    """)


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("n", [12, 14])
def test_solves_random_large_boards_quickly(n, seed):
    puzzle = random_puzzle(n, seed)

    assert_obeys_the_rules(puzzle, solve_within(solve, puzzle, seconds=1.0))
