import pytest

from engines.wend import Puzzle, solve
from engines.wend.dictionary import english_words
from tests.helpers import solve_within

from .boards import WEND1, WEND1_ANSWER, WEND2, WEND2_ANSWER
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
    assert set(solve(Puzzle(WEND1, lengths=(3, 4, 5, 6)))) == WEND1_ANSWER


def test_solves_the_wend2_example():
    assert set(solve(Puzzle(WEND2, lengths=(3, 4, 5, 6)))) == WEND2_ANSWER


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("n", [7, 8])
def test_solves_random_large_boards_quickly(n, seed):
    puzzle = random_puzzle(n, seed)

    assert_obeys_the_rules(puzzle, solve_within(solve, puzzle, seconds=1.0))
