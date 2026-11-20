from engines.sudoku import read_puzzle
from tests.helpers import example

from .boards import SUDOKU1


def filled(grid) -> set[tuple[int, int]]:
    return {(r, c) for r, row in enumerate(grid) for c, digit in enumerate(row) if digit}


def test_reads_a_6x6_grid():
    puzzle = read_puzzle(example("sudoku", "sudoku1.png"))

    assert puzzle.size == 6


def test_finds_which_cells_hold_a_given():
    puzzle = read_puzzle(example("sudoku", "sudoku1.png"))

    assert filled(puzzle.grid) == filled(SUDOKU1)


def test_reads_every_given():
    puzzle = read_puzzle(example("sudoku", "sudoku1.png"))

    assert puzzle.grid == SUDOKU1
