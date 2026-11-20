import numpy as np
import pytest
from PIL import Image, ImageDraw

from engines.sumbreak import DOUBLE, Puzzle
from engines.sumbreak.ocr import read_puzzle, scan
from tests.helpers import example

from .boards import SUMBREAK1, SUMBREAK4, SUMBREAK5, board
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


@pytest.mark.parametrize("scale", [1, 2])
def test_reads_x2_tiles_as_tiles_that_double_not_as_a_2(scale):
    # Its "x2" is printed in a greyish purple on a pale diamond, and the x is
    # smaller than the 2.
    page = Image.open(example("sumbreak", "sumbreak5.png"))
    page = page.resize((scale * page.width, scale * page.height), Image.LANCZOS)

    assert read_puzzle(page) == SUMBREAK5


def sumbreak5_with_its_top_x2_showing(sign: str) -> Image.Image:
    """sumbreak5.png with the 2 of its top x2 tile rubbed out, and for "x4"
    the 4 of the tile below printed there instead, in the x2's ink.

    The 2 spans x 643-654, y 201-219 on a pale diamond; the 4 below spans
    x 633-647, y 333-351, and its ink is darker than 122."""
    pixels = np.asarray(Image.open(example("sumbreak", "sumbreak5.png")).convert("RGB")).copy()
    four = pixels[333:352, 633:648].mean(axis=2) < 122
    pixels[199:222, 641:658] = (230, 191, 255)
    if sign == "x4":
        pixels[201:220, 643:658][four] = (87, 55, 94)
    return Image.fromarray(pixels)


@pytest.mark.parametrize(
    "sign",
    [
        "x",  # as the result screen's icon shows it (sumbreak-result1.png)
        "x4",  # no board has shown one, so what it does is not known
    ],
)
def test_a_tile_with_a_sign_other_than_x2_is_refused_not_read_as_a_number(sign):
    with pytest.raises(ValueError, match=f"showing {sign} in row 1, column 2"):
        scan(sumbreak5_with_its_top_x2_showing(sign))


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


X2_BOARD = random_puzzle(6, 6, seed=1, spread=3, doubles=4)


@pytest.mark.parametrize(
    ("circles", "star"),
    [
        (False, None),  # a square with a pale diamond
        (True, 0.85),  # a starburst, whose points may be shallow
        (True, 0.7),  # or deep: it fills too little of its box to pass as a tile
    ],
)
@pytest.mark.parametrize("scale", [1, 2])
def test_reads_x2_tiles_on_a_large_board(circles, star, scale):
    assert read_puzzle(drawn(X2_BOARD, circles, scale, star=star)) == X2_BOARD


@pytest.mark.parametrize("scale", [1, 2])
def test_a_shape_on_a_cell_that_is_no_tile_is_refused_not_read_as_an_empty_cell(scale):
    # A starburst so spiky that it fills a third of its box, like no tile seen.
    row, col = next((r, c) for r, line in enumerate(X2_BOARD.numbers) for c, tile in enumerate(line) if tile == DOUBLE)

    with pytest.raises(ValueError, match=f"row {row + 1}, column {col + 1}"):
        scan(drawn(X2_BOARD, circles=True, scale=scale, star=0.4))


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
