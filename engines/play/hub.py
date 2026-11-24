"""LinkedIn's games hub, as the signed-in player sees it: which games were
played today."""

from __future__ import annotations

import contextlib
import io
import math
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import numpy as np
from PIL import Image

from ..vision import ImageSource, load_rgb
from .games import HUB_URL

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

    from .games import Game

HUB_WAIT = 10.0  # s for the hub to load
CARD_WAIT = 10.0  # s for a game's card picture to show and be drawn, once the hub has loaded
# Resolves once the img has arrived and can be drawn; fails if it can't be, or after `ms`.
DRAWN = """(img, ms) => Promise.race([
  img.decode(),
  new Promise((_, fail) => setTimeout(() => fail(new Error(`picture not drawn after ${ms} ms`)), ms)),
])"""

CHECK_GREEN = (5, 118, 66)  # #057642, the disc behind the check on a played game's picture
NEAR = 25  # a pixel is the check's green if no colour is further than this (of 255) from it
ICON = 48  # CSS px across a card's picture
DISC = 23  # CSS px across the disc
PLAYED_SHARE = 1 / 3  # the picture shows the check if at least this share of a disc's area is its green


def shows_played_check(picture: ImageSource) -> bool:
    """True if a game card's picture carries the hub's check for a game played
    today: a disc of CHECK_GREEN in the middle, with a white check cut out of it.

    The picture is ICON CSS px across, so its size in pixels says the screen's
    scale, and the disc's area grows with the picture's area."""
    pixels = load_rgb(picture)
    green = (np.abs(pixels - CHECK_GREEN) <= NEAR).all(axis=2)
    height, width = green.shape
    disc = math.pi * (DISC / 2) ** 2 * (width * height) / ICON**2  # in the picture's pixels
    return bool(green.sum() >= PLAYED_SHARE * disc)


def played_today(context: BrowserContext, game: Game, hub: str = HUB_URL, card_wait: float = CARD_WAIT) -> bool:
    """True if the hub shows `game`'s card with the check of a game played
    today; see `not_played_today`, which this asks about one game."""
    return not not_played_today(context, [game], hub, card_wait)


def not_played_today(
    context: BrowserContext, games: Sequence[Game], hub: str = HUB_URL, card_wait: float = CARD_WAIT
) -> list[Game]:
    """The games out of `games`, in their order, that the hub doesn't show as
    played today: their card has no check (see `shows_played_check`). The hub
    is opened once, and every game's card is read on it.

    A game counts as not played, and is played as usual, also when the hub
    doesn't load within HUB_WAIT s, has no card for it, or anything else goes
    wrong; each such game gets a line that says why. Each card has `card_wait`
    s to show and its picture to be drawn. Once the hub has been loaded that
    long, a card that isn't on it is given up on at once, so a hub without
    any of the cards costs one `card_wait`, not one per game.

    The hub is opened in a tab of its own in `context`, closed afterwards, so
    whatever it does can't get in the way of the game's page. In the same
    tab, after a hub that failed to load, Chrome was still opening its error
    page when the game's page was opened, and that stopped the game's page."""
    from playwright.sync_api import Error as PlaywrightError  # the browser extra, only needed here

    tab = None
    try:
        tab = context.new_page()
        tab.goto(hub, wait_until="domcontentloaded", timeout=HUB_WAIT * 1000)
        cards_due = time.monotonic() + card_wait
        return [game for game in games if not _shows_played(tab, game, card_wait, cards_due)]
    except PlaywrightError as error:
        for game in games:
            _cannot_tell(game, _reason(error))
        return list(games)
    finally:
        if tab is not None:
            with contextlib.suppress(PlaywrightError):
                tab.close()


def _shows_played(tab: Page, game: Game, card_wait: float, cards_due: float) -> bool:
    """True if `game`'s card on the hub in `tab` shows the check; False, with
    a line that says why, if it can't be read."""
    from playwright.sync_api import Error as PlaywrightError

    picture = tab.locator(_card(game.url)).locator("img").first
    deadline = time.monotonic() + card_wait

    def left() -> float:  # ms; Playwright waits for ever on 0
        return max(1.0, (deadline - time.monotonic()) * 1000)

    try:
        if time.monotonic() >= cards_due and picture.count() == 0:
            _cannot_tell(game, "no card for it")
            return False
        picture.wait_for(state="visible", timeout=left())
        picture.scroll_into_view_if_needed(timeout=left())  # a lazy picture loads only once in view
        picture.evaluate(DRAWN, left())  # its box shows before the picture has arrived
        shot = picture.screenshot(timeout=left())
    except PlaywrightError as error:
        _cannot_tell(game, _reason(error))
        return False
    return shows_played_check(Image.open(io.BytesIO(shot)))


def _cannot_tell(game: Game, reason: str) -> None:
    print(f"Couldn't see on the hub whether {game.title} was played today ({reason}); opening it.")


def _reason(error: Exception) -> str:
    """The first line of `error`'s message, or its kind if it has none."""
    return str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__


def _card(url: str) -> str:
    """A CSS selector for a hub card that links to the game at `url`: by its
    path, as the signed-in hub links ("/games/zip/"), or by the whole address,
    with or without a query ("?trk=games_hub")."""
    forms = (url, urlparse(url).path)
    return ", ".join(f'a[href="{form}"], a[href^="{form}?"]' for form in forms)
