"""When the player moves: thinking before each thought, then a quick burst."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass, field

from ..common.actions import Action, Press, Think


@dataclass(frozen=True)
class Pauses:
    """Seconds of thinking: never below `shortest`, `mean` on average, with a
    long tail of slow moves.

    The time above `shortest` has a log-normal distribution, the usual shape of
    human response times: most moves come soon after `shortest`, and now and
    then one takes much longer. `tail` is the log-normal's shape; 0 makes every
    pause exactly `mean`. With the defaults, the median is 1.83 s, 1 move in 10
    takes over 2.6 s and 1 in 100 over 4.2 s.
    """

    mean: float = 2.0
    shortest: float = 1.5
    tail: float = 0.9

    def draw(self, rng: random.Random) -> float:
        above = self.mean - self.shortest
        if above <= 0:
            return self.shortest
        return self.shortest + rng.lognormvariate(math.log(above) - self.tail**2 / 2, self.tail)


@dataclass(frozen=True)
class Tempo:
    """How long to wait before each move.

    A `Think` marks the start of a thought: the move after it waits a thinking
    pause, and the other moves of the thought follow `burst` seconds apart. A
    key press waits only `key_delay` after the click that selected its cell.
    """

    think: Pauses = field(default_factory=Pauses)
    burst: tuple[float, float] = (0.3, 0.8)
    key_delay: float = 0.3

    def waits(self, actions: Iterable[Action], rng: random.Random) -> list[tuple[float, Action]]:
        """(seconds to wait, action) for every action but the Think markers."""
        timed = []
        thinking = True  # the first move always comes after a look at the board
        for action in actions:
            if isinstance(action, Think):
                thinking = True
            elif isinstance(action, Press):
                timed.append((self.key_delay, action))
            else:
                timed.append((self.think.draw(rng) if thinking else rng.uniform(*self.burst), action))
                thinking = False
        return timed


INSTANT = Tempo(Pauses(0, 0, 0), (0, 0), 0)  # for tests: the same moves, without waiting
