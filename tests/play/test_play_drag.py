"""Seam: the player's drags on a stand-in page and clock, without a browser.

How long a drag takes and how many steps it glides in, on the clock the
player keeps, so a busy machine can't change the outcome. The browser test
(test_play_in_browser.py) checks that a real page sees the glide.
"""

from __future__ import annotations

import random

from engines.play.browser import Player
from engines.play.games import GAMES
from engines.play.timing import INSTANT as NO_WAITING
from tests.helpers import example

from .clock import StandInClock

MOVE_TAKES = 0.005  # s: a mouse move on a busy machine, well under a frame (1/60 s)


class StandInMouse:
    """Records what is done with it and when, by `clock`; each move takes
    `move_takes` s of that clock, and the page sees it at the end."""

    def __init__(self, clock: StandInClock, move_takes: float) -> None:
        self.clock, self.move_takes, self.events = clock, move_takes, []

    def move(self, x: float, y: float) -> None:
        self.clock.spend(self.move_takes)
        self.events.append(("move", self.clock.now()))

    def down(self) -> None:
        self.events.append(("down", self.clock.now()))

    def up(self) -> None:
        self.events.append(("up", self.clock.now()))

    def click(self, x: float, y: float) -> None:
        self.events.append(("click", self.clock.now()))


class StandInPage:
    """Stands in for a Playwright page that shows `screenshot` at scale 1."""

    def __init__(self, screenshot, mouse: StandInMouse) -> None:
        self.png = screenshot.read_bytes()
        self.mouse = mouse

    def screenshot(self) -> bytes:
        return self.png

    def evaluate(self, expression: str) -> float:
        assert expression == "window.devicePixelRatio"
        return 1.0


def play_patches1(move_takes: float = 0.0) -> list[tuple[float, int]]:
    """Plays patches1.png, with each mouse move taking `move_takes` s; returns
    (seconds from press to release, moves in between) for each drag."""
    clock = StandInClock()
    mouse = StandInMouse(clock, move_takes)
    page = StandInPage(example("patches", "patches1.png"), mouse)

    Player(page, tempo=NO_WAITING, rng=random.Random(1), clock=clock).play(GAMES["patches"])

    drags, moves = [], 0
    for kind, at in mouse.events:
        if kind == "down":
            pressed, moves = at, 0
        elif kind == "move":
            moves += 1
        elif kind == "up":
            drags.append((at - pressed, moves))
    return drags


def test_a_patch_is_drawn_in_a_smooth_half_second_drag():
    drags = play_patches1()

    assert drags
    assert all(0.45 <= seconds <= 0.8 for seconds, _ in drags), "about half a second each"
    assert all(moves >= 10 for _, moves in drags), "the mouse glides; it doesn't jump"


def test_a_drag_keeps_to_its_time_when_each_mouse_move_takes_a_while():
    # The player waits for each step's time since the press, not a step's
    # length after the last move, so the time the moves take doesn't add up.
    idle, busy = play_patches1(), play_patches1(move_takes=MOVE_TAKES)

    assert [moves for _, moves in busy] == [moves for _, moves in idle]
    assert all(b <= i + MOVE_TAKES + 1e-9 for (b, _), (i, _) in zip(busy, idle)), "late by the last move at most"
