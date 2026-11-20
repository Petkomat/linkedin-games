import pytest
from PIL import Image, ImageDraw, ImageFont

from engines.sudoku import read_puzzle
from engines.vision import Unreadable
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


def test_a_sign_in_a_cell_is_refused_not_read_as_a_digit_or_an_empty_cell():
    # The top left cell of sudoku1.png is empty and white, its middle at
    # (65, 59); the givens are 17 px tall, in (26, 26, 26).
    page = Image.open(example("sudoku", "sudoku1.png")).convert("RGB")
    ImageDraw.Draw(page).text((65, 59), "+", fill=(26, 26, 26), font=ImageFont.load_default(size=24), anchor="mm")

    with pytest.raises(Unreadable):
        read_puzzle(page)
