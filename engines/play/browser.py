"""Play a board on a Playwright page: screenshot in, mouse and keyboard out."""

from __future__ import annotations

import io
import random
import time
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from PIL import Image

from ..common import Cell
from ..common.actions import Action, Button, Click, Drag
from ..vision import GridGeometry
from .games import Game
from .motion import Hand, drag, spot
from .result import ResultWait, looks_alike, looks_blank
from .screen import Screen
from .timing import Tempo

if TYPE_CHECKING:
    from playwright.sync_api import Page

RETRY = 1.0  # s between two looks at the screen while waiting for the board


class Clock:
    """The time the player keeps: the machine's own clock."""

    def now(self) -> float:
        """Seconds since some fixed moment, to the microsecond; never set back."""
        return time.perf_counter()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class Player:
    """Reads the board on `page` and enters moves with the mouse and keyboard.

    It waits before each move as `tempo` says: a thinking pause at the start
    of each thought, then a quick burst. The mouse is pressed and released on
    random spots of their cells, never exactly on the middle, and drags move
    like `hand` (see `motion`). Random draws come from `rng`. After the last
    move, it waits for the game's result as `result_wait` says. Every wait is
    timed by `clock`.
    """

    def __init__(
        self,
        page: Page,
        tempo: Tempo | None = None,
        rng: random.Random | None = None,
        hand: Hand | None = None,
        result_wait: ResultWait | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.page = page
        self.tempo = tempo or Tempo()
        self.rng = rng or random.Random()
        self.hand = hand or Hand()
        self.result_wait = result_wait or ResultWait()
        self.clock = clock or Clock()

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

    def wait_for_board(
        self, game: Game, seconds: float, before_each_look: Callable[[], object] | None = None
    ) -> tuple[Any, list[Action]] | None:
        """`read`, once the same board has been read twice in a row (so a board
        that is still fading in isn't used); None after `seconds`. Calls
        `before_each_look`, if given, before each read."""
        clock = self.clock
        deadline = clock.now() + seconds
        previous = None
        while True:
            if before_each_look is not None:
                before_each_look()
            board = self.read(game)
            if board is not None and previous is not None and board[0].puzzle == previous[0].puzzle:
                return board
            if clock.now() + RETRY > deadline:
                return None
            previous = board
            clock.sleep(RETRY)

    def final_screen(self) -> Image.Image:
        """The screen to save after the last move: the finished board or the
        game's result screen, once it holds still. On its way from one to the
        other, LinkedIn may play an animation and show an empty page for a
        while, so a screen counts only once it isn't blank and the next look
        is alike (see `looks_blank` and `looks_alike`). Looks are timed as
        `result_wait` says. At its limit, the last screenshot taken."""
        wait, clock = self.result_wait, self.clock
        deadline = clock.now() + wait.limit
        clock.sleep(min(wait.first_look, wait.limit))
        shown = self.screenshot()
        blank = looks_blank(shown)
        while (left := deadline - clock.now()) > 0:
            clock.sleep(min(wait.poll if blank else wait.settle, left))
            seen = self.screenshot()
            seen_blank = looks_blank(seen)
            if not blank and not seen_blank and looks_alike(shown, seen):
                return seen
            shown, blank = seen, seen_blank
        return shown

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
            self.clock.sleep(wait)
            if isinstance(action, Click):
                row, col = action.cell
                d_row, d_col = spot(self.rng)
                x, y = screen.position(row + d_row, col + d_col)
                for _ in range(action.times):  # a double click hits the same spot twice
                    mouse.click(x, y)
            elif isinstance(action, Drag):
                self._drag(screen, action.cells)
            elif isinstance(action, Button):
                self._click_button(action.label)
            else:
                self.page.keyboard.press(action.key)

    def _click_button(self, label: str) -> None:
        """Click a random spot well inside the visible button that says `label`.

        A button off the board isn't in the scan, so it is looked up on the
        page, in whichever frame it is, like the start screens' buttons."""
        from playwright.sync_api import Error as PlaywrightError  # the browser extra, only needed here

        for frame in self.page.frames:
            button = frame.get_by_role("button", name=label, exact=True).filter(visible=True)
            try:
                box = button.first.bounding_box() if button.count() else None
            except PlaywrightError:  # tracking and captcha iframes come and go
                continue
            if box:  # in page pixels, wherever the frame is
                d_row, d_col = spot(self.rng)
                self.page.mouse.click(box["x"] + box["width"] * (0.5 + d_col), box["y"] + box["height"] * (0.5 + d_row))
                return
        raise RuntimeError(f"no {label} button on the page")

    def _drag(self, screen: Screen, cells: tuple[Cell, ...]) -> None:
        """Press, move along the hand's timeline as the clock runs, release."""
        timeline = drag(cells, self.rng, self.hand)
        mouse, clock = self.page.mouse, self.clock
        mouse.move(*screen.position(*timeline[0][1:]))
        mouse.down()
        pressed = clock.now()
        for seconds, row, col in timeline[1:]:
            clock.sleep(max(0.0, pressed + seconds - clock.now()))
            mouse.move(*screen.position(row, col))
        mouse.up()
