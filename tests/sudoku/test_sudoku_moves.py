"""Seam: moves(puzzle), replayed on a model of LinkedIn's Mini Sudoku controls."""

from engines.common.actions import Click, Press, Think
from engines.sudoku import Puzzle
from engines.sudoku.moves import moves

from .boards import SUDOKU1, grid

# Nine digits of the sudoku1 answer: too few to deduce everything, and the
# solver's first guess fails.
GUESSWORK = Puzzle(grid("""
    . . . | . . 6
    . . . | . 1 .
    2 . 4 | 5 . .
    . . . | . . .
    4 . . | 1 3 .
    . . . | . . 2
"""))


def play(puzzle: Puzzle, actions) -> list[dict]:
    """A click selects a cell; a digit key fills it in and Backspace empties it.

    Returns the board after every key press. Givens can't be changed.
    """
    cells = {(r, c): d for r, row in enumerate(puzzle.grid) for c, d in enumerate(row)}
    selected = None
    history = []
    for action in actions:
        if isinstance(action, Think):
            continue
        if isinstance(action, Click):
            selected = action.cell
            continue
        assert isinstance(action, Press), f"Sudoku is played by clicking and typing, not {action}"
        assert selected is not None, "a key was pressed before any cell was selected"
        assert puzzle.grid[selected[0]][selected[1]] == 0, f"the given at {selected} can't be changed"
        cells[selected] = 0 if action.key == "Backspace" else int(action.key)
        history.append(dict(cells))
    return history


def as_grid(cells: dict, n: int):
    return tuple(tuple(cells[r, c] for c in range(n)) for r in range(n))


def test_the_moves_fill_in_the_answer():
    assert as_grid(play(Puzzle(SUDOKU1), moves(Puzzle(SUDOKU1)))[-1], 6) == grid("""
        1 2 3 | 4 5 6
        5 4 6 | 2 1 3
        2 3 4 | 5 6 1
        6 5 1 | 3 2 4
        4 6 2 | 1 3 5
        3 1 5 | 6 4 2
    """)


def test_a_failed_guess_is_typed_in_and_then_corrected():
    history = play(GUESSWORK, moves(GUESSWORK))
    answer = history[-1]

    assert 0 not in answer.values(), "every cell is filled in the end"
    assert any(
        digit not in (0, answer[cell]) for shown in history for cell, digit in shown.items()
    ), "a digit that isn't in the answer was shown on the way"
