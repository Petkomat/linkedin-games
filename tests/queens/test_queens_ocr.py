from engines.queens import read_puzzle
from tests.helpers import example

from .boards import QUEENS1, QUEENS2


def partition(regions) -> set[frozenset[tuple[int, int]]]:
    """The regions as sets of cells, so the labels themselves don't matter."""
    cells: dict[int, set[tuple[int, int]]] = {}
    for r, row in enumerate(regions):
        for c, label in enumerate(row):
            cells.setdefault(label, set()).add((r, c))
    return {frozenset(group) for group in cells.values()}


def test_reads_the_regions_ignoring_placed_queens():
    # queens1.png already has two queens on it; they must not change any region.
    puzzle = read_puzzle(example("queens", "queens1.png"))

    assert partition(puzzle.regions) == partition(QUEENS1)


def test_reads_a_high_resolution_board():
    # The thick outer frame is too wide for the line finder at full size, which
    # used to see only the 6x6 inside it.
    puzzle = read_puzzle(example("queens", "queens2.png"))

    assert partition(puzzle.regions) == partition(QUEENS2)
