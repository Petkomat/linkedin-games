"""Seam: moves(puzzle), replayed on a model of LinkedIn's Patches controls."""

from engines.common.actions import Click, Drag, Think
from engines.patches import Puzzle, Rect
from engines.patches.moves import moves

from .boards import PATCHES3_ANSWER, PATCHES3_ROOTS
from .generator import random_puzzle

# A 5x5 board with 10 roots on which the solver's first guess fails.
GUESSWORK = random_puzzle(5, seed=8)


def cells_of(rect: Rect) -> set[tuple[int, int]]:
    return {
        (r, c)
        for r in range(rect.top, rect.top + rect.height)
        for c in range(rect.left, rect.left + rect.width)
    }


def play(actions) -> list[set[Rect]]:
    """A drag draws the patch spanned by the cells it starts and ends on; a
    click on a patch removes it. Returns the patches after every action."""
    patches: set[Rect] = set()
    history = []
    for action in actions:
        if isinstance(action, Think):
            continue
        if isinstance(action, Drag):
            (r1, c1), (r2, c2) = action.cells[0], action.cells[-1]
            patch = Rect(min(r1, r2), min(c1, c2), abs(r1 - r2) + 1, abs(c1 - c2) + 1)
            assert not any(cells_of(patch) & cells_of(p) for p in patches), f"{patch} overlaps"
            patches.add(patch)
        else:
            assert isinstance(action, Click), f"Patches is played by dragging and clicking, not {action}"
            hit = [p for p in patches if action.cell in cells_of(p)]
            assert hit, f"{action.cell} is not in a patch"
            patches.remove(hit[0])
        history.append(set(patches))
    return history


def test_the_moves_draw_the_answer():
    puzzle = Puzzle(rows=6, cols=6, roots=tuple(PATCHES3_ROOTS.values()))

    assert play(moves(puzzle))[-1] == set(PATCHES3_ANSWER.values())


def test_a_failed_guess_is_drawn_and_then_removed():
    history = play(moves(GUESSWORK))
    answer = history[-1]

    assert sum(p.height * p.width for p in answer) == 25, "the patches cover the board in the end"
    assert any(shown - answer for shown in history), "a patch that isn't in the answer was drawn"
