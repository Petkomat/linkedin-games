"""Seam: moves(puzzle), replayed on a model of LinkedIn's Queens controls."""

from engines.common.actions import Click, Think
from engines.queens import Puzzle
from engines.queens.moves import moves

from .boards import QUEENS1, regions

# tests/queens/generator.py's 5x5 board for seed 3. Nothing is forced at the
# start, and the solver's first guesses are wrong.
GUESSWORK = regions("""
    A A A A B
    A C E B B
    C C E E D
    C C E E D
    C C E E D
""")

# A click moves the cell one step along this cycle, wrapping back to empty.
CYCLE = ("empty", "X", "queen")


def play(actions) -> list[dict[tuple[int, int], str]]:
    """Click through `actions` on an empty board; the board after every click."""
    board: dict[tuple[int, int], str] = {}
    history = []
    for action in actions:
        if isinstance(action, Think):
            continue
        assert isinstance(action, Click), f"Queens is played by clicking, not {action}"
        step = CYCLE.index(board.get(action.cell, "empty")) + action.times
        board[action.cell] = CYCLE[step % len(CYCLE)]
        history.append({cell: mark for cell, mark in board.items() if mark != "empty"})
    return history


def queens(board) -> set[tuple[int, int]]:
    return {cell for cell, mark in board.items() if mark == "queen"}


def test_the_moves_leave_exactly_the_answer_on_the_board():
    final = play(moves(Puzzle(QUEENS1)))[-1]

    assert queens(final) == {(0, 5), (1, 2), (2, 4), (3, 6), (4, 0), (5, 3), (6, 1)}
    assert set(final.values()) == {"queen"}, "no X marks are left behind"


def test_wrong_guesses_are_entered_and_then_taken_back():
    history = play(moves(Puzzle(GUESSWORK)))
    answer = queens(history[-1])

    assert len(answer) == 5
    assert set(history[-1].values()) == {"queen"}
    assert any(queens(board) - answer for board in history), "the guesses that failed are shown"
