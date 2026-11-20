import pytest

from engines.patches import Root, Shape, read_puzzle
from tests.helpers import example


def test_reads_the_grid_size():
    puzzle = read_puzzle(example("patches", "patches1.png"))

    assert (puzzle.rows, puzzle.cols) == (5, 5)


def test_finds_the_root_cells_despite_a_half_drawn_patch():
    # patches1 has a patch being dragged over (1,0)-(2,1), plus the mouse cursor.
    puzzle = read_puzzle(example("patches", "patches1.png"))

    assert {(r.row, r.col) for r in puzzle.roots} == {(0, 0), (1, 0), (3, 4), (4, 4)}


@pytest.mark.parametrize(
    "screenshot, shapes",
    [
        (
            "patches1.png",
            {(0, 0): Shape.WIDE, (1, 0): Shape.TALL, (3, 4): Shape.SQUARE, (4, 4): Shape.WIDE},
        ),
        (
            "patches2.png",
            {
                (0, 0): Shape.SQUARE, (0, 5): Shape.SQUARE,
                (2, 0): Shape.ANY, (2, 2): Shape.TALL,
                (3, 3): Shape.TALL, (3, 5): Shape.ANY,
                (5, 0): Shape.SQUARE, (5, 5): Shape.SQUARE,
            },
        ),
    ],
)
def test_reads_the_badge_shapes(screenshot, shapes):
    puzzle = read_puzzle(example("patches", screenshot))

    assert {(r.row, r.col): r.shape for r in puzzle.roots} == shapes


def test_reads_the_whole_patches1_puzzle():
    puzzle = read_puzzle(example("patches", "patches1.png"))

    assert (puzzle.rows, puzzle.cols) == (5, 5)
    assert set(puzzle.roots) == {
        Root(0, 0, Shape.WIDE, 5),
        Root(1, 0, Shape.TALL, 8),
        Root(3, 4, Shape.SQUARE, 9),
        Root(4, 4, Shape.WIDE, 3),
    }
