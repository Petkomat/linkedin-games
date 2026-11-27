"""Seam: moves(puzzle), replayed on a model of LinkedIn's Sumbreak controls."""

import pytest

from engines.common.actions import Button, Drag, Think
from engines.sumbreak.moves import moves
from tests.helpers import solve_within

from .boards import SUMBREAK1, SUMBREAK5, SUMBREAK8, SUMBREAK10, board
from .generator import random_puzzle
from .rules import merged

# tests/sumbreak/generator.py's 3x3 board for seed 221: the solver merges
# the wrong 1s first and finds out three merges later.
GUESSWORK = board("""
    1 4 2
    1 2 1
    2 2 1
""")

# Its 5x5 board for seed 9, on which the solver takes back 30 merges.
LONG_SEARCH = random_puzzle(5, 5, seed=9)


def play(puzzle, actions) -> list[dict[tuple[int, int], int | str]]:
    """Dragging a tile onto a neighbour with the same number merges them into
    the neighbour, and so does dragging a x2 or x4 tile onto a number or a
    number onto one (rules.merged); the Undo button takes back the last merge.
    Returns the tiles after every move."""
    tiles = puzzle.tiles()
    made: list[dict[tuple[int, int], int | str]] = []
    history = []
    for action in actions:
        if isinstance(action, Think):
            continue
        if isinstance(action, Button):
            assert action.label == "Undo", f"Sumbreak has no {action.label} to press"
            assert made, "nothing to undo"
            tiles = made.pop()
        else:
            assert isinstance(action, Drag), f"Sumbreak is played by dragging, not {action}"
            source, target = action.cells
            assert abs(source[0] - target[0]) + abs(source[1] - target[1]) == 1, f"{action}: not neighbours"
            assert source in tiles and target in tiles, f"{action}: an empty cell"
            made.append(dict(tiles))
            tiles[target] = merged(tiles.pop(source), tiles[target])
        history.append(dict(tiles))
    return history


def undos(actions) -> int:
    return sum(isinstance(action, Button) for action in actions)


def test_the_moves_leave_one_tile_with_everything_added_up():
    final = play(SUMBREAK1, moves(SUMBREAK1))[-1]

    assert list(final.values()) == [128]


def test_the_moves_play_out_the_first_4x4_board():
    final = play(SUMBREAK8, moves(SUMBREAK8))[-1]

    assert list(final.values()) == [1024]


def test_x2_tiles_double_what_they_are_dragged_onto_or_what_is_dragged_onto_them():
    final = play(SUMBREAK5, moves(SUMBREAK5))[-1]

    assert list(final.values()) == [32]


def test_a_x4_tile_multiplies_what_it_is_dragged_onto_or_what_is_dragged_onto_it_by_4():
    final = play(SUMBREAK10, moves(SUMBREAK10))[-1]

    assert list(final.values()) == [64]


def test_wrong_merges_are_made_and_then_undone():
    actions = moves(GUESSWORK)

    assert list(play(GUESSWORK, actions)[-1].values()) == [16]
    assert undos(actions) > 0, "the merges that failed are shown"


def test_a_long_search_shows_a_few_wrong_merges_not_all_of_them():
    # A person tries a few things before thinking it all through, not 30.
    actions = moves(LONG_SEARCH)

    assert len(play(LONG_SEARCH, actions)[-1]) == 1
    assert 0 < undos(actions) <= 5


@pytest.mark.parametrize(("doubles", "quadruples"), [(0, 0), (4, 0), (2, 2)])
@pytest.mark.parametrize("seed", range(10))
def test_every_move_on_random_large_boards_is_one_the_game_takes(seed, doubles, quadruples):
    puzzle = random_puzzle(6, 6, seed, doubles=doubles, quadruples=quadruples)

    actions = solve_within(moves, puzzle, seconds=1.0)

    assert len(play(puzzle, actions)[-1]) == 1
    assert undos(actions) <= 5
