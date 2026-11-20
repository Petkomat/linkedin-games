"""After the last move: how long to wait for the game's result, when the
screen counts as blank, and when two looks at it show the same."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from ..vision import load_rgb, open_image

TOP = 0.1  # LinkedIn's top bar, and the game's bar under it, sit in about the top tenth
FLAT = 10  # a row whose colours differ by no more than this (of 255) shows nothing
SOME = 0.1  # the page shows something if at least this share of its rows does
BLOCKS = 8  # two looks are compared in square blocks, this many across the page
NEAR = 24  # a block whose average colour moves by no more than this (of 255) still looks the same
STILL = 0.05  # two looks are alike if less than this share of their blocks moved


@dataclass(frozen=True)
class ResultWait:
    """How the player waits for the screen to save after its last move.

    It first looks `first_look` s after the last move, which gives the game
    time to take it. While the page is blank (see `looks_blank`), and for a
    game whose result comes after a blank page (`Game.result_after_blank`)
    until the page was blank, it looks again every `poll` s. Otherwise, a
    look that shows something is checked `settle` s later: if that look is
    alike (see `looks_alike`) and isn't blank, the screen holds still and is
    saved; if not, the waiting goes on from there.
    It ends `limit` s after the last move at the latest.
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
    pixels = load_rgb(screenshot)
    left, top, right, bottom = _page(*pixels.shape[1::-1])
    page = pixels[top:bottom, left:right]
    spread = (page.max(axis=1) - page.min(axis=1)).max(axis=1)  # per row, the most of any colour
    return bool((spread > FLAT).mean() < SOME)


def looks_alike(first: Image.Image, second: Image.Image) -> bool:
    """True if two screenshots show the same page, give or take small things
    moving on it, such as confetti still falling on a result screen or the
    last of a fade. A board whose tiles fly across the page, or a screen still
    fading in, is not alike from one look to the next.

    The part `looks_blank` looks at is cut into square blocks, BLOCKS across,
    and each block's average colour is compared: a bit of confetti hardly
    moves the average of its block, while a tile or a whole page does.
    Screenshots of different sizes are not alike."""
    first, second = open_image(first), open_image(second)
    if first.size != second.size:
        return False
    moved = np.abs(_blocks(first) - _blocks(second)).max(axis=2) > NEAR  # per block, the most of any colour
    return bool(moved.mean() < STILL)


def _page(width: int, height: int) -> tuple[int, int, int, int]:
    """The box (left, top, right, bottom) of a screenshot that shows the game:
    below the top bars, in the middle third."""
    return width // 3, round(height * TOP), width - width // 3, height


def _blocks(screenshot: Image.Image) -> np.ndarray:
    """The average colour of each block of the page, as `looks_alike` compares them."""
    page = screenshot.convert("RGB").crop(_page(*screenshot.size))
    across = BLOCKS
    down = max(1, round(page.height * across / page.width))
    return np.asarray(page.resize((across, down), Image.Resampling.BOX), dtype=np.int16)
