"""After the last move: how long to wait for the game's result, and when the
screen counts as blank."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

TOP = 0.1  # LinkedIn's top bar, and the game's bar under it, sit in about the top tenth
FLAT = 10  # a row whose colours differ by no more than this (of 255) shows nothing
SOME = 0.1  # the page shows something if at least this share of its rows does


@dataclass(frozen=True)
class ResultWait:
    """How the player waits for the screen to save after its last move.

    It first looks `first_look` s after the last move, which gives the game
    time to take it. While the page is blank (see `looks_blank`), it looks
    again every `poll` s, until `limit` s after the last move. A screen that
    shows up after a blank one gets `settle` s more to finish fading in.
    """

    first_look: float = 2.0
    limit: float = 20.0
    poll: float = 1.0
    settle: float = 1.0


def looks_blank(screenshot: Image.Image) -> bool:
    """True if the page below its top bar is (almost) one flat colour, as on
    LinkedIn's empty grey page between a game's board and its result screen.

    Only the middle third is looked at, where LinkedIn puts its games, so
    LinkedIn's messaging box in the bottom right corner doesn't count."""
    pixels = np.asarray(screenshot.convert("RGB"), dtype=np.int16)
    height, width, _ = pixels.shape
    page = pixels[round(height * TOP) :, width // 3 : width - width // 3]
    spread = (page.max(axis=1) - page.min(axis=1)).max(axis=1)  # per row, the most of any colour
    return bool((spread > FLAT).mean() < SOME)
