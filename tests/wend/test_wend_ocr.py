import pytest

from engines.wend import read_puzzle
from tests.helpers import example

from .boards import WEND1, WEND2


@pytest.mark.parametrize(("screenshot", "board"), [("wend1.png", WEND1), ("wend2.png", WEND2)])
def test_finds_the_grey_cells(screenshot, board):
    puzzle = read_puzzle(example("wend", screenshot))

    assert [[letter is None for letter in row] for row in puzzle.letters] == [
        [letter is None for letter in row] for row in board
    ]


@pytest.mark.parametrize(("screenshot", "board"), [("wend1.png", WEND1), ("wend2.png", WEND2)])
def test_reads_the_letters(screenshot, board):
    puzzle = read_puzzle(example("wend", screenshot))

    assert puzzle.letters == board


def test_reads_the_word_lengths_from_the_squares_below_the_board():
    puzzle = read_puzzle(example("wend", "wend2.png"))

    assert puzzle.lengths == (3, 4, 5, 6)
