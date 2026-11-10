from engines.tango import read_puzzle
from tests.helpers import example

from .boards import TANGO1, TANGO2, TANGO2_EQUAL, TANGO2_OPPOSITE


def test_reads_the_suns_and_moons():
    puzzle = read_puzzle(example("tango", "tango1.png"))

    assert puzzle.givens == TANGO1


def test_ignores_the_players_moves():
    puzzle = read_puzzle(example("tango", "tango2.png"))

    assert puzzle.givens == TANGO2


def test_reads_the_equal_and_opposite_signs():
    puzzle = read_puzzle(example("tango", "tango2.png"))

    assert puzzle.equal == TANGO2_EQUAL
    assert puzzle.opposite == TANGO2_OPPOSITE
