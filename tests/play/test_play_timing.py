"""Seam: how long the player waits before each move."""

import random
from statistics import mean, median

from engines.common.actions import Click, Press, Think
from engines.play.timing import Pauses, Tempo

PAUSES = Pauses(mean=2.0, shortest=1.5)


def draws(pauses: Pauses, n: int = 20_000) -> list[float]:
    rng = random.Random(0)
    return sorted(pauses.draw(rng) for _ in range(n))


def test_thinking_takes_two_seconds_on_average_and_never_less_than_one_and_a_half():
    pauses = draws(PAUSES)

    assert pauses[0] >= 1.5
    assert abs(mean(pauses) - 2.0) < 0.03


def test_most_moves_come_quicker_than_the_average_and_a_few_take_much_longer():
    pauses = draws(PAUSES)

    assert median(pauses) < 1.9
    assert pauses[int(0.99 * len(pauses))] > 3.5, "1 move in 100 takes over 3.5 s"


def test_no_pauses_for_tests():
    assert Pauses(mean=0, shortest=0, tail=0).draw(random.Random(0)) == 0


def test_the_player_thinks_once_per_thought_and_then_moves_in_a_quick_burst():
    # One thought: two cells deduced together. Then a second thought.
    actions = [Think(), Click((0, 0)), Click((0, 1)), Think(), Click((1, 0))]

    waits = Tempo().waits(actions, random.Random(0))

    assert [action for _, action in waits] == [Click((0, 0)), Click((0, 1)), Click((1, 0))]
    (think1, _), (burst, _), (think2, _) = waits
    assert think1 >= 1.5
    assert think2 >= 1.5
    assert 0.3 <= burst <= 0.8


def test_a_key_is_typed_right_after_the_click_that_selected_its_cell():
    waits = Tempo().waits([Think(), Click((2, 3)), Press("4")], random.Random(0))

    assert waits[1] == (0.3, Press("4"))
