"""Seam: the screen the player saves after its last move.

LinkedIn may show an empty page for a while on its way from the board to its
result screen: its top bar over a flat grey page. The player waits until the
page shows something else, the finished board or the result screen, which may
have no grid at all.
"""

from __future__ import annotations

import io
import time

import numpy as np
import pytest
from PIL import Image, ImageDraw

from engines.play.browser import Player
from engines.play.games import GAMES
from engines.play.result import ResultWait, looks_blank
from tests.helpers import example

# Measured on queens2.png, a whole LinkedIn page
PAGE_GREY = (244, 242, 238)  # the page's background
TOP_BARS = 279  # rows of LinkedIn's bar and the game's bar at the top
CARD = (248, 250, 253)  # the background of the card the board is on
GRID = (1330, 372, 2380, 1418)  # the board, thick border included


def scaled(image: Image.Image, scale: float) -> Image.Image:
    """`image` as a screen with `scale` times the pixels would show it."""
    return image if scale == 1 else image.resize((round(image.width * scale), round(image.height * scale)))


def blank_page() -> Image.Image:
    """LinkedIn's top bars over an empty grey page: queens2.png without its game."""
    page = Image.open(example("queens", "queens2.png")).convert("RGB")
    blank = Image.new("RGB", page.size, PAGE_GREY)
    blank.paste(page.crop((0, 0, page.width, TOP_BARS)))
    return blank


def page_without_grid() -> Image.Image:
    """queens2.png with its board painted over: the card with its buttons and
    texts is left, the way a result screen may show no grid."""
    page = Image.open(example("queens", "queens2.png")).convert("RGB")
    ImageDraw.Draw(page).rectangle(GRID, fill=CARD)
    return page


@pytest.mark.parametrize("scale", [1.0, 0.5])
def test_the_top_bar_over_an_empty_grey_page_is_blank(scale):
    assert looks_blank(scaled(blank_page(), scale))


def test_an_empty_page_with_linkedins_messaging_box_is_still_blank():
    # tango2.png, a signed-in page in a video frame, with only its bars, the
    # messaging box in the bottom right corner and the video's black edges kept
    page = Image.open(example("tango", "tango2.png")).convert("RGB")
    blank = Image.new("RGB", page.size, (241, 240, 236))
    for kept in [(0, 0, 1280, 93), (970, 630, 1280, 684), (0, 684, 1280, 720)]:
        blank.paste(page.crop(kept), kept[:2])

    assert looks_blank(blank)


@pytest.mark.parametrize(
    ("game", "screenshot"),
    [("queens", "queens2.png"), ("tango", "tango2.png"), ("wend", "wend2.png"), ("zip", "zip2.jpg")],
)
@pytest.mark.parametrize("scale", [1.0, 0.5])
def test_a_whole_page_with_a_board_is_not_blank(game, screenshot, scale):
    assert not looks_blank(scaled(Image.open(example(game, screenshot)), scale))


@pytest.mark.parametrize("scale", [1.0, 0.5])
def test_linkedins_result_screen_is_not_blank(scale):
    # A guest's Zip result screen on 2026-11-17, confetti still falling; the
    # profile photos of other members are painted over.
    screen = scaled(Image.open(example("zip", "zip-result1.png")), scale)

    with pytest.raises(ValueError):
        GAMES["zip"].scan(screen)  # no grid on it
    assert not looks_blank(screen)


@pytest.mark.parametrize("scale", [1.0, 0.5])
def test_a_page_with_no_grid_but_buttons_and_text_is_not_blank(scale):
    page = scaled(page_without_grid(), scale)

    with pytest.raises(ValueError):
        GAMES["queens"].scan(page)  # so reading the board can't tell a result screen from a blank one
    assert not looks_blank(page)


class Frames:
    """Stands in for a Playwright page whose screenshots are `frames`, one
    after another, and the last one for ever after."""

    def __init__(self, *frames: Image.Image) -> None:
        self.frames = frames
        self.shots = 0

    def screenshot(self) -> bytes:
        frame = self.frames[min(self.shots, len(self.frames) - 1)]
        self.shots += 1
        png = io.BytesIO()
        frame.save(png, "PNG")
        return png.getvalue()


def same(a: Image.Image, b: Image.Image) -> bool:
    return np.array_equal(np.asarray(a.convert("RGB")), np.asarray(b.convert("RGB")))


def board() -> Image.Image:
    return Image.open(example("queens", "queens2.png")).convert("RGB")


QUICK = ResultWait(first_look=0, limit=5, poll=0.01, settle=0)


def test_blank_screens_are_waited_out_and_the_first_one_that_shows_something_is_kept():
    page = Frames(blank_page(), blank_page(), blank_page(), board())

    final = Player(page, result_wait=QUICK).final_screen()

    assert same(final, board())


def test_a_page_that_stays_blank_is_waited_for_until_the_limit_and_then_taken_as_it_is():
    page = Frames(blank_page())
    wait = ResultWait(first_look=0.1, limit=0.6, poll=0.1)

    started = time.monotonic()
    final = Player(page, result_wait=wait).final_screen()

    assert 0.6 <= time.monotonic() - started < 1.2
    assert page.shots > 2, "it kept looking"
    assert same(final, blank_page())


def test_a_page_that_shows_something_at_the_first_look_is_taken_at_once():
    # Queens, Tango and Mini Sudoku have always shown their board 2 s after the last move.
    page = Frames(board())
    wait = ResultWait(first_look=0.3, limit=10, poll=0.1)

    started = time.monotonic()
    final = Player(page, result_wait=wait).final_screen()

    assert 0.3 <= time.monotonic() - started < 0.8
    assert page.shots == 1
    assert same(final, board())


def test_a_screen_that_has_just_shown_up_gets_time_to_finish_fading_in():
    fading_in = Image.blend(blank_page(), board(), 0.3)
    assert not looks_blank(fading_in)
    page = Frames(blank_page(), fading_in, board())

    final = Player(page, result_wait=ResultWait(first_look=0, limit=5, poll=0.01, settle=0.2)).final_screen()

    assert same(final, board())


def test_a_screen_that_shows_up_and_goes_again_is_kept():
    page = Frames(blank_page(), board(), blank_page())

    final = Player(page, result_wait=ResultWait(first_look=0, limit=5, poll=0.01, settle=0.1)).final_screen()

    assert same(final, board())


def test_the_settling_ends_at_the_limit_too():
    page = Frames(blank_page(), board())
    wait = ResultWait(first_look=0, limit=0.3, poll=0.05, settle=5)

    started = time.monotonic()
    final = Player(page, result_wait=wait).final_screen()

    assert time.monotonic() - started < 0.8
    assert same(final, board())
