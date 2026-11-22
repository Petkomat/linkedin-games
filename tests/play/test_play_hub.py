"""Seam: does a game card's picture on LinkedIn's games hub carry the check of
a game played today?

On the signed-in hub, a played game's card picture (48x48 CSS px, an SVG) is
the game's icon with a dark green disc (#057642, about 23 CSS px wide,
centred) and a white check cut out of it. Unplayed cards show the icon alone.

The owner's hub screenshot (examples/hub/signed-in-hub1.png) didn't reach this
branch, so the pictures here are drawn: icons with and without the disc and
check, antialiased like a browser draws an SVG, at the screen scales Windows
offers.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from engines.play.hub import shows_played_check

CHECK_GREEN = (5, 118, 66)  # #057642, the disc's colour, from the issue
ICON = 48  # CSS px across a card's picture
DISC = 23  # CSS px across the disc
SUPERSAMPLE = 4  # drawn this many times bigger and shrunk, which antialiases the edges

PURPLE = ((112, 72, 200), (230, 110, 160))
ORANGE = ((250, 140, 40), (250, 210, 80))
LIGHT_GREEN = ((80, 190, 120), (150, 220, 170))  # green, but far from the disc's


def picture(scale: float = 1, played: bool = False, colours=PURPLE, speck: float = 0) -> Image.Image:
    """A card's picture as a screen with `scale` device px per CSS px shows it:
    a game icon (a gradient from top to bottom with a white frame on it) and,
    if `played`, the disc with its check. `speck` adds a dot of the disc's
    green this many CSS px across, off the middle."""
    size = round(ICON * scale)
    big = size * SUPERSAMPLE
    px = scale * SUPERSAMPLE  # drawing px per CSS px
    top, bottom = (np.array(c, dtype=float) for c in colours)
    t = np.linspace(0, 1, big)[:, None]
    rows = top * (1 - t) + bottom * t
    image = Image.fromarray(np.repeat(rows[:, None, :], big, axis=1).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([8 * px, 8 * px, 40 * px, 40 * px], radius=6 * px, outline="white", width=round(3 * px))
    middle = big / 2
    if played:
        r = DISC / 2 * px
        draw.ellipse([middle - r, middle - r, middle + r, middle + r], fill=CHECK_GREEN)
        check = [(middle - 5 * px, middle), (middle - 1.5 * px, middle + 4 * px), (middle + 5.5 * px, middle - 4 * px)]
        draw.line(check, fill="white", width=round(3 * px), joint="curve")
    if speck:
        r = speck / 2 * px
        x, y = 14 * px, 14 * px
        draw.ellipse([x - r, y - r, x + r, y + r], fill=CHECK_GREEN)
    return image.resize((size, size), Image.Resampling.BOX)


def test_a_played_picture_shows_the_check_and_an_unplayed_one_does_not():
    assert shows_played_check(picture(played=True))
    assert not shows_played_check(picture(played=False))


SCALES = [1, 1.25, 1.5, 2]  # device px per CSS px: Windows' display scales; 2 on a high-resolution screen


@pytest.mark.parametrize("colours", [PURPLE, ORANGE, LIGHT_GREEN], ids=["purple", "orange", "light green"])
@pytest.mark.parametrize("scale", SCALES)
def test_every_icon_shows_the_check_only_when_played_at_any_scale(scale, colours):
    assert shows_played_check(picture(scale, played=True, colours=colours))
    assert not shows_played_check(picture(scale, played=False, colours=colours))


@pytest.mark.parametrize("played", [True, False])
def test_a_picture_enlarged_twice_keeps_its_verdict(played):
    # As a 1x screenshot of the hub would look on a 2x screen.
    small = picture(1, played=played)
    enlarged = small.resize((small.width * 2, small.height * 2), Image.Resampling.BICUBIC)

    assert shows_played_check(enlarged) == played


def test_a_picture_not_drawn_yet_shows_no_check():
    assert not shows_played_check(Image.new("RGB", (96, 96), "white"))


@pytest.mark.parametrize("scale", SCALES)
def test_a_speck_of_the_green_is_not_the_check_at_any_scale(scale):
    # A dot 10 CSS px across has a fifth of the disc's area. At 2x that is
    # about 300 device px, as many as the whole disc has at 1x.
    assert not shows_played_check(picture(scale, speck=10))
