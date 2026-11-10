import pytest

from engines.wend import Puzzle, Word, solve
from engines.wend.dictionary import english_words
from tests.helpers import solve_within

from .boards import WEND1, WEND2
from .generator import random_puzzle


def assert_obeys_the_rules(puzzle: Puzzle, answer) -> None:
    assert answer is not None
    assert sorted(len(word.text) for word in answer) == sorted(puzzle.lengths)
    for word in answer:
        assert word.text in english_words(), word.text
        assert "".join(puzzle.letters[r][c] for r, c in word.path) == word.text
        for (r1, c1), (r2, c2) in zip(word.path, word.path[1:]):
            assert abs(r1 - r2) + abs(c1 - c2) == 1, f"{word.text} jumps"
    used = [cell for word in answer for cell in word.path]
    tiles = [
        (r, c)
        for r, row in enumerate(puzzle.letters)
        for c, letter in enumerate(row)
        if letter is not None
    ]
    assert sorted(used) == tiles, "every tile is used exactly once"


def test_solves_the_wend1_example():
    # Solved by hand: the top row bends down into WISDOM, FOUND runs along
    # the bottom, and DONE climbs the right edge.
    answer = solve(Puzzle(WEND1, lengths=(3, 4, 5, 6)))

    assert set(answer) == {
        Word("WIN", ((1, 0), (2, 0), (2, 1))),
        Word("DONE", ((4, 4), (3, 4), (2, 4), (2, 3))),
        Word("FOUND", ((3, 0), (4, 0), (4, 1), (4, 2), (4, 3))),
        Word("WISDOM", ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 4))),
    }


def test_solves_the_wend2_example():
    # Solved by hand. The H can only join O, so it starts HOLD; that leaves
    # W-I-N in the corner, ALIGN around the L, and ENGINE on the right.
    answer = solve(Puzzle(WEND2, lengths=(3, 4, 5, 6)))

    assert set(answer) == {
        Word("WIN", ((0, 0), (1, 0), (2, 0))),
        Word("HOLD", ((3, 2), (3, 3), (3, 4), (4, 4))),
        Word("ALIGN", ((1, 1), (2, 1), (3, 1), (3, 0), (4, 0))),
        Word("ENGINE", ((1, 2), (1, 3), (2, 3), (2, 4), (1, 4), (0, 4))),
    }


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("n", [7, 8])
def test_solves_random_large_boards_quickly(n, seed):
    puzzle = random_puzzle(n, seed)

    assert_obeys_the_rules(puzzle, solve_within(solve, puzzle, seconds=1.0))
