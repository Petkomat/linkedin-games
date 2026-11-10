"""Seam: moves(puzzle), replayed on a model of LinkedIn's Zip controls."""

import pytest

from engines.common.actions import Drag, Think
from engines.zip.moves import moves
from tests.helpers import solve_within

from .boards import ZIP2, ZIP2_ANSWER
from .generator import random_puzzle
from .rules import assert_is_solution

# A 6x6 board with 8 numbers on which drawing from 1 runs into dead ends.
GUESSWORK = random_puzzle(6, seed=1, numbers=8)


def play(puzzle, actions) -> list[list[tuple[int, int]]]:
    """The path is drawn in one drag that starts on 1. Moving onto a free
    neighbour of the path's end extends the path; moving back onto the cell
    before the end takes the end back. Returns the path after every move."""
    (drag,) = [a for a in actions if not isinstance(a, Think)]  # Zip is drawn in a single drag
    assert isinstance(drag, Drag), f"Zip is drawn by dragging, not {drag}"
    start, *moved_to = drag.cells
    assert puzzle.numbers.get(start) == 1, "the drag starts on 1"
    path = [start]
    history = [list(path)]
    for cell in moved_to:
        if len(path) > 1 and cell == path[-2]:
            path.pop()
        else:
            (r1, c1), (r2, c2) = path[-1], cell
            assert abs(r1 - r2) + abs(c1 - c2) == 1, f"{path[-1]} -> {cell} is not a step"
            assert cell not in path, f"{cell} is on the path already"
            assert frozenset({path[-1], cell}) not in puzzle.walls, f"{path[-1]} -> {cell} crosses a wall"
            path.append(cell)
        history.append(list(path))
    return history


def test_the_drag_draws_the_answer():
    assert play(ZIP2, moves(ZIP2))[-1] == ZIP2_ANSWER


def test_dead_ends_are_drawn_and_then_taken_back():
    history = play(GUESSWORK, moves(GUESSWORK))

    assert_is_solution(GUESSWORK, history[-1])
    assert any(len(after) < len(before) for before, after in zip(history, history[1:])), (
        "the path backed up on the way"
    )


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize(("n", "numbers"), [(7, 10), (8, 12)])
def test_draws_random_boards_of_linkedin_sizes_quickly(n, numbers, seed):
    puzzle = random_puzzle(n, seed, numbers)

    history = play(puzzle, solve_within(moves, puzzle, seconds=1.0))

    assert_is_solution(puzzle, history[-1])
