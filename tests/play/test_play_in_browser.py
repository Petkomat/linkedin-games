"""Seam: the whole player in a real browser, on a local page instead of LinkedIn.

The page shows an example screenshot and records every mouse and key event.
The player screenshots the page, reads and solves the board, and plays its
moves; the recorded events must hit the cells of the moves worked out from the
original screenshot file.
"""

from __future__ import annotations

import random
from math import floor

import pytest

from engines.common.actions import Click, Drag, Press, Think
from engines.play.browser import Player
from engines.play.games import GAMES
from engines.play.motion import INSTANT
from engines.play.timing import INSTANT as NO_WAITING
from engines.vision import GridGeometry
from tests.helpers import example

from .pages import SCALE, page_showing

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")


def instant_player(page, rng=None) -> Player:
    """A player that doesn't wait for anything."""
    return Player(page, tempo=NO_WAITING, rng=rng, hand=INSTANT)


def cell_at(grid: GridGeometry, x: float, y: float) -> tuple[int, int]:
    return floor((y - grid.ys.start) / grid.ys.pitch), floor((x - grid.xs.start) / grid.xs.pitch)


def gestures(events, grid: GridGeometry) -> list:
    """Recorded events as actions on the original screenshot's cells: a press
    and release on one cell is a click, otherwise a drag through every cell
    the pointer crossed."""
    out, pressed = [], []
    for event in events:
        if event["type"] == "keydown":
            out.append(Press(event["key"]))
            continue
        cell = cell_at(grid, event["x"] * SCALE, event["y"] * SCALE)
        if event["type"] == "pointerdown":
            pressed = [cell]
        elif cell != pressed[-1]:
            pressed.append(cell)
        if event["type"] == "pointerup":
            out.append(Click(pressed[0]) if len(pressed) == 1 else Drag(tuple(pressed)))
    return out


def one_by_one(actions) -> list:
    """Actions with every multiple click written as single clicks."""
    return [
        Click(a.cell) if isinstance(a, Click) else a
        for a in actions
        if not isinstance(a, Think)
        for _ in range(a.times if isinstance(a, Click) else 1)
    ]


def same_gestures(recorded, expected) -> bool:
    """Equal, except that a drag may cross more cells than it names: going from
    one corner of a patch to the other crosses the cells in between."""
    if len(recorded) != len(expected):
        return False
    return all(
        _passes_through(r.cells, e.cells) if isinstance(r, Drag) and isinstance(e, Drag) else r == e
        for r, e in zip(recorded, expected)
    )


def _passes_through(crossed, named) -> bool:
    """Starts and ends on the named cells and crosses the others in order."""
    rest = iter(crossed)
    return crossed[0] == named[0] and crossed[-1] == named[-1] and all(c in rest for c in named)


@pytest.mark.parametrize(
    ("game", "screenshot"),
    [
        ("patches", "patches1.png"),
        ("queens", "queens1.png"),
        ("queens", "queens2.png"),  # a whole LinkedIn page, high resolution
        ("sudoku", "sudoku1.png"),
        ("tango", "tango2.png"),
        ("wend", "wend2.png"),
        ("zip", "zip2.jpg"),
    ],
)
def test_the_player_enters_the_moves_on_the_board(browser, game, screenshot):
    rules = GAMES[game]
    original = rules.scan(example(game, screenshot))
    page = page_showing(browser, example(game, screenshot))

    instant_player(page).play(rules)

    recorded = gestures(page.evaluate("events"), original.grid)
    assert same_gestures(recorded, one_by_one(rules.moves(original.puzzle)))


@pytest.mark.parametrize(("game", "screenshot"), [("queens", "queens1.png"), ("patches", "patches1.png")])
def test_the_mouse_is_pressed_and_released_on_random_spots_well_inside_cells(browser, game, screenshot):
    # Queens is clicked; Patches is dragged from corner to corner and clicked.
    rules = GAMES[game]
    original = rules.scan(example(game, screenshot))
    page = page_showing(browser, example(game, screenshot))

    instant_player(page, random.Random(1)).play(rules)

    spots = [
        offset_in_cell(original.grid, event["x"] * SCALE, event["y"] * SCALE)
        for event in page.evaluate("events")
        if event["type"] in ("pointerdown", "pointerup")
    ]
    assert max(max(abs(dx), abs(dy)) for dx, dy in spots) > 0.1, "not always the middle"
    assert all(max(abs(dx), abs(dy)) < 0.35 for dx, dy in spots), "never near an edge"


def offset_in_cell(grid: GridGeometry, x: float, y: float) -> tuple[float, float]:
    """Where (x, y) is in its cell: (dx, dy) from the middle, in cells."""
    middle_x, middle_y = grid.center(*cell_at(grid, x, y))
    return (x - middle_x) / grid.xs.pitch, (y - middle_y) / grid.ys.pitch


def test_a_patch_is_drawn_in_a_smooth_half_second_drag(browser):
    rules = GAMES["patches"]
    page = page_showing(browser, example("patches", "patches1.png"))
    player = Player(page, tempo=NO_WAITING, rng=random.Random(1))

    player.play(rules)

    drags, moves = [], 0
    for event in page.evaluate("events"):
        if event["type"] == "pointerdown":
            pressed, moves = event["t"], 0
        elif event["type"] == "pointermove":
            moves += 1
        elif event["type"] == "pointerup" and moves:
            drags.append((event["t"] - pressed, moves))
    assert drags
    assert all(450 <= ms <= 800 for ms, _ in drags), "about half a second each"
    assert all(moves >= 10 for _, moves in drags), "the mouse glides; it doesn't jump"
