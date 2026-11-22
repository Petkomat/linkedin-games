"""LinkedIn's games hub, as the signed-in player sees it: which games were
played today."""

from __future__ import annotations

import contextlib
import io
import math
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import numpy as np
from PIL import Image

from ..vision import ImageSource, load_rgb

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext

    from .games import Game

HUB_URL = "https://www.linkedin.com/games/"  # the hub: a card for each game
HUB_WAIT = 10.0  # s for the hub to load
CARD_WAIT = 10.0  # s for the game's card picture to show and be drawn, once the hub has loaded
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
    today (see `shows_played_check`).

    False if it shows the card without the check, and also if the hub doesn't
    load within HUB_WAIT s, has no card for the game within `card_wait` s
    more, or anything else goes wrong: then the game is played as usual.

    The hub is opened in a tab of its own in `context`, closed afterwards, so
    whatever it does can't get in the way of the game's page: after a hub
    that failed to load, Chrome would still be opening its error page when
    the game's page is opened in the same tab, which stops that."""
    from playwright.sync_api import Error as PlaywrightError  # the browser extra, only needed here

    tab = None
    try:
        tab = context.new_page()
        tab.goto(hub, wait_until="domcontentloaded", timeout=HUB_WAIT * 1000)
        deadline = time.monotonic() + card_wait

        def left() -> float:  # ms; Playwright waits for ever on 0
            return max(1.0, (deadline - time.monotonic()) * 1000)

        picture = tab.locator(_card(game.url)).locator("img").first
        picture.wait_for(state="visible", timeout=left())
        picture.scroll_into_view_if_needed(timeout=left())  # a lazy picture loads only once in view
        picture.evaluate(DRAWN, left())  # its box shows before the picture has arrived
        shot = picture.screenshot(timeout=left())
    except PlaywrightError as error:
        reason = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
        print(f"Couldn't see on the hub whether {game.title} was played today ({reason}); opening it.")
        return False
    finally:
        if tab is not None:
            with contextlib.suppress(PlaywrightError):
                tab.close()
    return shows_played_check(Image.open(io.BytesIO(shot)))


def _card(url: str) -> str:
    """A CSS selector for a hub card that links to the game at `url`: by its
    path, as the signed-in hub links ("/games/zip/"), or by the whole address,
    with or without a query ("?trk=games_hub")."""
    forms = (url, urlparse(url).path)
    return ", ".join(f'a[href="{form}"], a[href^="{form}?"]' for form in forms)
