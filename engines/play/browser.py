"""Play a board on a Playwright page: screenshot in, mouse and keyboard out."""

from __future__ import annotations

import io
import random
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from PIL import Image

from ..common import Cell
from ..common.actions import Action, Click, Drag
from ..vision import GridGeometry
from .games import Game
from .motion import Hand, drag, spot
from .screen import Screen
from .timing import Tempo

if TYPE_CHECKING:
    from playwright.sync_api import Page



class Player:
    """Reads the board on `page` and enters moves with the mouse and keyboard.

    It waits before each move as `tempo` says: a thinking pause at the start
    of each thought, then a quick burst. The mouse is pressed and released on
    random spots of their cells, never exactly on the middle, and drags move
    like `hand` (see `motion`). Random draws come from `rng`.
    """

    def __init__(
        self,
        page: Page,
        tempo: Tempo | None = None,
        rng: random.Random | None = None,
        hand: Hand | None = None,
    ) -> None:
        self.page = page
        self.tempo = tempo or Tempo()
        self.rng = rng or random.Random()
        self.hand = hand or Hand()

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
        for wait, action in self.tempo.waits(actions, self.rng):
            time.sleep(wait)
            if isinstance(action, Click):
                row, col = action.cell
                d_row, d_col = spot(self.rng)
                x, y = screen.position(row + d_row, col + d_col)
                for _ in range(action.times):  # a double click hits the same spot twice
                    mouse.click(x, y)
            elif isinstance(action, Drag):
                self._drag(screen, action.cells)
            else:
                self.page.keyboard.press(action.key)

    def _drag(self, screen: Screen, cells: tuple[Cell, ...]) -> None:
        """Press, move along the hand's timeline as the clock runs, release."""
        timeline = drag(cells, self.rng, self.hand)
        mouse = self.page.mouse
        mouse.move(*screen.position(*timeline[0][1:]))
        mouse.down()
        pressed = time.perf_counter()
        for seconds, row, col in timeline[1:]:
            time.sleep(max(0.0, pressed + seconds - time.perf_counter()))
            mouse.move(*screen.position(row, col))
        mouse.up()
