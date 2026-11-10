"""Seam: moves(puzzle), replayed on a model of LinkedIn's Wend controls."""

from engines.common.actions import Drag
from engines.wend import Puzzle, solve
from engines.wend.dictionary import english_words
from engines.wend.moves import moves

from .boards import WEND2, WEND2_ANSWER
from .generator import random_puzzle

# A 5x5 board full of decoys (BAWD, NIL, SWAY, ...) that the solver tries
# before it finds the six hidden words.
GUESSWORK = random_puzzle(5, seed=0)


def play(answer, actions) -> list[set]:
    """A drag from a hidden word's first letter to its last finds the word,
    which stays on the board; any other drag is rejected and leaves nothing.
    Returns the words found after every drag."""
    found = set()
    history = []
    for action in actions:
        assert isinstance(action, Drag), f"Wend is played by dragging, not {action}"
        word = next((w for w in answer if w.path == action.cells), None)
        assert word not in found, f"{word} was found already"
        if word is not None:
            found.add(word)
        history.append(set(found))
    return history


def test_the_moves_find_every_hidden_word():
    actions = moves(Puzzle(WEND2, lengths=(3, 4, 5, 6)))

    assert play(WEND2_ANSWER, actions)[-1] == WEND2_ANSWER


def test_decoy_words_are_tried_on_the_way():
    answer = set(solve(GUESSWORK))
    actions = moves(GUESSWORK)

    spelled = ["".join(GUESSWORK.letters[r][c] for r, c in a.cells) for a in actions]
    assert play(answer, actions)[-1] == answer
    assert len(actions) > len(answer), "some drags were decoys the game rejected"
    assert set(spelled) <= english_words(), "every drag spells a real word"
