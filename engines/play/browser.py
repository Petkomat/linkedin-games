"""Play a board on a Playwright page: screenshot in, mouse and keyboard out."""

from __future__ import annotations

import io
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from PIL import Image

from ..common.actions import Action, Click, Drag
from ..vision import GridGeometry
from .games import Game
from .screen import Screen

if TYPE_CHECKING:
    from playwright.sync_api import Page

DRAG_STEPS = 4  # mouse-move events from one cell to the next, so the page sees the way between


class Player:
    """Reads the board on `page` and enters moves with the mouse.

    `pause` is the time in seconds between two actions, so the page can keep up.
    """

    def __init__(self, page: Page, pause: float = 0.1) -> None:
        self.page = page
        self.pause = pause

    def screenshot(self) -> Image.Image:
        """What is on screen now, in device pixels."""
        return Image.open(io.BytesIO(self.page.screenshot()))

    @property
    def scale(self) -> float:
        return float(self.page.evaluate("window.devicePixelRatio"))

    def play(self, game: Game) -> list[Action] | None:
        """Read, solve and play the board on screen; returns the moves made, or None."""
        board = self.read(game)
        if board is None:
            return None
        seen, actions = board
        self.perform(actions, seen.grid)
        return actions

    def read(self, game: Game) -> tuple[Any, list[Action]] | None:
        """The board on screen and the moves that solve it; None if there is no
        board on screen (yet) or it can't be solved, which means it was misread."""
        try:
            seen = game.scan(self.screenshot())
        except ValueError:  # no grid in the screenshot
            return None
        actions = game.moves(seen.puzzle)
        return None if actions is None else (seen, actions)

    def perform(self, actions: Iterable[Action], grid: GridGeometry) -> None:
        screen = Screen(grid, self.scale)
        mouse = self.page.mouse
        for action in actions:
            if isinstance(action, Click):
                x, y = screen.point(action.cell)
                for _ in range(action.times):
                    mouse.click(x, y)
            elif isinstance(action, Drag):
                start, *rest = (screen.point(cell) for cell in action.cells)
                mouse.move(*start)
                mouse.down()
                for x, y in rest:
                    mouse.move(x, y, steps=DRAG_STEPS)
                    time.sleep(self.pause / 5)
                mouse.up()
            else:
                self.page.keyboard.press(action.key)
            time.sleep(self.pause)
