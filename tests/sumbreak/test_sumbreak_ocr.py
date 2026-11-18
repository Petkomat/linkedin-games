import pytest
from PIL import Image, ImageDraw

from engines.sumbreak import Puzzle
from engines.sumbreak.ocr import read_puzzle, scan
from tests.helpers import example

from .boards import SUMBREAK1, SUMBREAK4, board
from .generator import random_puzzle
from .pictures import MARGIN, drawn


@pytest.mark.parametrize(
    "screenshot",
    [
        "sumbreak1.png",  # square tiles
        "sumbreak2.png",  # circles that grow with the number, which LinkedIn shows some guests
        "sumbreak3.png",  # circles on a high-resolution screen (devicePixelRatio 2)
    ],
)
def test_reads_the_board_drawn_with_squares_or_circles(screenshot):
    assert read_puzzle(example("sumbreak", screenshot)) == SUMBREAK1


def test_reads_square_tiles_on_a_high_resolution_screen():
    page = Image.open(example("sumbreak", "sumbreak1.png"))

    assert read_puzzle(page.resize((2 * page.width, 2 * page.height), Image.LANCZOS)) == SUMBREAK1


def test_an_emptied_cell_is_no_tile():
    assert read_puzzle(example("sumbreak", "sumbreak4.png")) == SUMBREAK4


@pytest.mark.parametrize(
    ("screenshot", "middle", "pitch"),
    [
        # The top left square spans x 448-567 and y 149-268, and the next one
        # starts 132.5 px further on.
        ("sumbreak1.png", (507.5, 208.5), 132.5),
        # Measured on sumbreak2.png: the circles' middles are at x 509, 640,
        # 771 and y 210, 341, 472; this is the same page at twice the pixels.
        ("sumbreak3.png", (1018, 420), 262),
    ],
)
def test_finds_the_cells_where_the_mouse_must_go(screenshot, middle, pitch):
    grid = scan(example("sumbreak", screenshot)).grid

    assert grid.center(0, 0) == pytest.approx(middle, abs=2)
    assert grid.pitch == pytest.approx(pitch, abs=1)


@pytest.mark.parametrize("circles", [False, True])
@pytest.mark.parametrize("scale", [1, 2])
def test_reads_a_large_board_with_empty_cells(circles, scale):
    numbers = [list(row) for row in random_puzzle(6, 6, seed=1, spread=3).numbers]
    numbers[0][0] = numbers[2][3] = numbers[5][5] = None
    puzzle = Puzzle(tuple(tuple(row) for row in numbers))

    seen = scan(drawn(puzzle, circles, scale))

    assert seen.puzzle == puzzle
    assert seen.grid.center(0, 0) == pytest.approx(((MARGIN + 32) * scale, (MARGIN + 32) * scale), abs=1)


def test_coloured_things_above_the_board_are_not_part_of_it():
    # A signed-in member's top bar has LinkedIn's blue logo, a red dot and a
    # round photo in a row, and they may sit right above columns of tiles.
    puzzle = random_puzzle(4, 4, seed=1, spread=3)
    page = drawn(puzzle)
    draw = ImageDraw.Draw(page)
    x = MARGIN + 1.5 * 96  # above the middle of the second column (4 columns of 96 px)
    draw.rounded_rectangle((20, 20, 70, 70), radius=6, fill=(10, 102, 194))
    draw.ellipse((x - 25, 20, x + 25, 70), fill=(233, 30, 99))
    draw.ellipse((x + 2 * 96 - 20, 25, x + 2 * 96 + 20, 65), fill=(204, 16, 34))  # above the fourth

    assert read_puzzle(page) == puzzle


def test_a_board_with_a_single_tile_left_is_no_board():
    # What LinkedIn shows for a moment after the last merge
    with pytest.raises(ValueError):
        scan(drawn(board("128")))


def test_the_result_screen_is_no_board():
    # Its Sumbreak icon is a 2x2 board of numbers; no real board is that small.
    with pytest.raises(ValueError):
        scan(example("sumbreak", "sumbreak-result1.png"))
