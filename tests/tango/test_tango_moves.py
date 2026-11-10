"""Seam: moves(puzzle), replayed on a model of LinkedIn's Tango controls."""

from engines.common.actions import Click, Think
from engines.tango import Puzzle, Symbol
from engines.tango.moves import moves

from .boards import TANGO2, TANGO2_EQUAL, TANGO2_OPPOSITE, board, edges

# tests/tango/generator.py's 6x6 board for seed 20 (givens=0.2, signs=0.05):
# the givens and signs don't settle it, and the solver's first guess fails.
GUESSWORK = Puzzle(
    board("""
        . S . . M .
        . . . S . .
        . M . . . .
        M . S . M .
        . S . . . M
        . . . . S .
    """),
    equal=edges(((2, 5), (3, 5))),
    opposite=edges(((0, 2), (0, 3)), ((3, 5), (4, 5))),
)

# A click moves a cell one step along this cycle, wrapping back to empty.
CYCLE = (None, Symbol.SUN, Symbol.MOON)


def play(puzzle: Puzzle, actions) -> list[dict]:
    """Click through `actions` starting from the givens; the board after every click."""
    cells = {(r, c): s for r, row in enumerate(puzzle.givens) for c, s in enumerate(row)}
    history = []
    for action in actions:
        if isinstance(action, Think):
            continue
        assert isinstance(action, Click), f"Tango is played by clicking, not {action}"
        r, c = action.cell
        assert puzzle.givens[r][c] is None, f"the given at {action.cell} can't be changed"
        cells[action.cell] = CYCLE[(CYCLE.index(cells[action.cell]) + action.times) % len(CYCLE)]
        history.append(dict(cells))
    return history


def as_board(cells: dict, n: int):
    return tuple(tuple(cells[r, c] for c in range(n)) for r in range(n))


def test_the_moves_fill_in_the_answer():
    puzzle = Puzzle(TANGO2, equal=TANGO2_EQUAL, opposite=TANGO2_OPPOSITE)

    assert as_board(play(puzzle, moves(puzzle))[-1], 6) == board("""
        M S M M S S
        S M S M S M
        S S M S M M
        M S S M M S
        S M M S S M
        M M S S M S
    """)


def test_a_failed_guess_is_entered_and_then_corrected():
    history = play(GUESSWORK, moves(GUESSWORK))
    answer = history[-1]

    assert None not in answer.values(), "every cell is filled in the end"
    assert any(
        symbol not in (None, answer[cell]) for shown in history for cell, symbol in shown.items()
    ), "a symbol that isn't in the answer was shown on the way"


def test_the_cells_of_a_deduced_line_go_in_together_after_one_think():
    actions = moves(Puzzle(TANGO2, equal=TANGO2_EQUAL, opposite=TANGO2_OPPOSITE))

    thoughts = [[]]
    for action in actions:
        if isinstance(action, Think):
            thoughts.append([])
        else:
            thoughts[-1].append(action)
    assert thoughts[0] == [], "it thinks before the first move"
    assert max(len(thought) for thought in thoughts) > 1, "a whole line in one burst"
