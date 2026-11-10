"""Seam: the whole player in a real browser, on a local page instead of LinkedIn.

The page shows an example screenshot and records every mouse and key event.
The player screenshots the page, reads and solves the board, and plays its
moves; the recorded events must hit the cells of the moves worked out from the
original screenshot file.
"""

from __future__ import annotations

import base64
from math import ceil, floor

import pytest
from PIL import Image

from engines.common.actions import Click, Drag, Press
from engines.play.browser import Player
from engines.play.games import GAMES
from engines.vision import GridGeometry
from tests.helpers import example

sync_api = pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

SCALE = 2  # a high-resolution screen: two screenshot pixels per page pixel

RECORDER = """<script>
window.events = [];
for (const type of ["pointerdown", "pointermove", "pointerup"]) {
  addEventListener(type, (e) => {
    if (type !== "pointermove" || e.buttons) events.push({type, x: e.clientX, y: e.clientY});
  });
}
addEventListener("keydown", (e) => events.push({type: "keydown", key: e.key}));
</script>"""


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        try:
            chrome = playwright.chromium.launch(channel="chrome")
        except sync_api.Error as error:
            pytest.skip(f"Playwright can't start Chrome: {error}")
        yield chrome
        chrome.close()


def page_showing(browser, screenshot):
    """A page that shows `screenshot` pixel for pixel and records input events."""
    width, height = Image.open(screenshot).size
    page = browser.new_page(
        device_scale_factor=SCALE,
        viewport={"width": ceil(width / SCALE), "height": ceil(height / SCALE)},
    )
    mime = "jpeg" if screenshot.suffix == ".jpg" else "png"
    data = base64.b64encode(screenshot.read_bytes()).decode()
    page.set_content(
        # draggable=false: pressing on an image and moving would start the
        # browser's own drag-and-drop, which swallows the pointer events.
        f"<body style='margin:0'><img draggable='false' src='data:image/{mime};base64,{data}' "
        f"style='display:block;width:{width / SCALE}px;height:{height / SCALE}px'>{RECORDER}</body>"
    )
    return page


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

    Player(page, pause=0).play(rules)

    recorded = gestures(page.evaluate("events"), original.grid)
    assert same_gestures(recorded, one_by_one(rules.moves(original.puzzle)))
