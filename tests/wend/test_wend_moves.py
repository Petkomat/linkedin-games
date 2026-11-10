"""Seam: moves(puzzle), replayed on a model of LinkedIn's Wend controls."""

import pytest

from engines.common.actions import Click, Drag, Think
from engines.wend import Puzzle, solve
from engines.wend.dictionary import english_words
from engines.wend.moves import moves

from .boards import WEND2, WEND2_ANSWER, WEND3, WEND3_ANSWER
from .generator import random_puzzle

# A 5x5 board full of decoys (BAWD, NIL, SWAY, ...) that the solver tries
# before it finds the six hidden words.
GUESSWORK = random_puzzle(5, seed=0)


def play(hidden: set[tuple], actions) -> list[list[tuple]]:
    """A drag from a word's first letter to its last places it, whether the
    word is hidden or not. A hidden word gets a tick and stays for good;
    clicking the first letter of any other placed word removes it.
    Returns the placed words' paths after every action."""
    placed: list[tuple] = []
    history = []
    for action in actions:
        if isinstance(action, Think):
            continue
        if isinstance(action, Drag):
            taken = {cell for path in placed for cell in path}
            assert not taken & set(action.cells), f"{action.cells} runs over a word still on the board"
            placed.append(action.cells)
        else:
            assert isinstance(action, Click), f"Wend is played by dragging and clicking, not {action}"
            starting_here = [path for path in placed if path[0] == action.cell]
            assert starting_here, f"no word on the board starts at {action.cell}"
            assert starting_here[0] not in hidden, f"{starting_here[0]} has a tick: it must stay"
            placed.remove(starting_here[0])
        history.append(list(placed))
    return history


def paths(words) -> set[tuple]:
    return {word.path for word in words}


def test_the_moves_find_every_hidden_word():
    actions = moves(Puzzle(WEND2, lengths=(3, 4, 5, 6)))

    assert set(play(paths(WEND2_ANSWER), actions)[-1]) == paths(WEND2_ANSWER)


def test_wrong_words_are_removed_before_their_tiles_are_used_again():
    # On the first live run, ESS stayed on the board and SETS turned it into TESS.
    history = play(paths(WEND3_ANSWER), moves(Puzzle(WEND3, lengths=(3, 4, 5, 7))))

    assert set(history[-1]) == paths(WEND3_ANSWER)
    assert any(set(placed) - paths(WEND3_ANSWER) for placed in history), "it tried wrong words"


def test_decoy_words_are_tried_on_the_way():
    answer = set(solve(GUESSWORK))
    actions = moves(GUESSWORK)
    drags = [a for a in actions if isinstance(a, Drag)]

    spelled = ["".join(GUESSWORK.letters[r][c] for r, c in a.cells) for a in drags]
    assert set(play(paths(answer), actions)[-1]) == paths(answer)
    assert len(drags) > len(answer), "some drags were decoys, removed again"
    assert set(spelled) <= english_words(), "every drag spells a real word"


def test_a_ticked_word_is_never_removed_or_dragged_again():
    # The solver drops the hidden YAWS once and places it again later. On the
    # board it has its tick by then, so it stays, and is dragged only once.
    answer = paths(solve(GUESSWORK))
    actions = moves(GUESSWORK)

    dragged = [a.cells for a in actions if isinstance(a, Drag)]
    assert set(play(answer, actions)[-1]) == answer
    assert all(dragged.count(path) == 1 for path in answer)


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("n", [5, 6])
def test_random_boards_are_entered_without_breaking_the_controls(n, seed):
    puzzle = random_puzzle(n, seed)
    answer = paths(solve(puzzle))

    assert set(play(answer, moves(puzzle))[-1]) == answer
