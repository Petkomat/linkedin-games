"""LinkedIn's games hub, as the signed-in player sees it: which games were
played today."""

from __future__ import annotations

import math

import numpy as np

from ..vision import ImageSource, load_rgb

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
