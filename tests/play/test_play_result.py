"""Seam: the screen the player saves after its last move.

LinkedIn may show an empty page for a while on its way from the board to its
result screen: its top bar over a flat grey page. Some games play an animation
first, such as Sumbreak's tiles scattering across the page. The player waits
until the page shows something else and holds still, the finished board or the
result screen, which may have no grid at all. How long it waits is measured on
a stand-in clock.
"""

from __future__ import annotations

import io
import math
import random

import numpy as np
import pytest
from PIL import Image, ImageDraw

from engines.play.browser import Player
from engines.play.games import GAMES
from engines.play.result import ResultWait, looks_alike, looks_blank
from tests.helpers import example

from .clock import StandInClock

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


CONFETTI = [(30, 140, 60), (40, 80, 220), (140, 60, 200), (240, 60, 120), (250, 200, 60), (250, 170, 120)]


def with_confetti(page: Image.Image, seed: int, bits: int = 300) -> Image.Image:
    """`page` with `bits` bits of confetti over the middle third of its width.
    Each is 4-8 by 10-18 pixels on a 1280-pixel-wide page, as on
    zip-result1.png, which has about half as many."""
    page = page.copy()
    draw, rng = ImageDraw.Draw(page), random.Random(seed)
    size = page.width / 1280
    for _ in range(bits):
        x = rng.uniform(page.width / 3 - 50 * size, page.width * 2 / 3 + 50 * size)
        y = rng.uniform(page.height * 0.1, page.height)
        across, down = rng.uniform(4, 8) * size, rng.uniform(10, 18) * size
        if rng.random() < 0.5:
            across, down = down, across
        draw.rectangle((x, y, x + across, y + down), fill=rng.choice(CONFETTI))
    return page


def scattered(t: float, seed: int = 1, tiles: int = 7) -> Image.Image:
    """queens2.png with its board cut into `tiles` x `tiles` tiles that fly
    off in all directions, turning as they go, `t` of the way out: the way
    Sumbreak's board scatters across the page after its last move."""
    page = page_without_grid()
    board = Image.open(example("queens", "queens2.png")).convert("RGB").crop(GRID)
    rng = random.Random(seed)
    side = board.width / tiles
    for row in range(tiles):
        for col in range(tiles):
            tile = board.crop((round(col * side), round(row * side), round((col + 1) * side), round((row + 1) * side)))
            heading, reach = rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1.5) * page.width * t
            x = GRID[0] + col * side + math.cos(heading) * reach
            y = GRID[1] + row * side + math.sin(heading) * reach
            turned = tile.rotate(rng.uniform(-180, 180) * t, expand=True, fillcolor=CARD)
            page.paste(turned, (round(x), round(y)))
    return page


@pytest.mark.parametrize("scale", [1.0, 0.5])
def test_a_result_screen_with_its_confetti_still_falling_looks_alike_a_second_later(scale):
    result = Image.open(example("zip", "zip-result1.png")).convert("RGB")

    assert looks_alike(scaled(with_confetti(result, seed=1), scale), scaled(with_confetti(result, seed=2), scale))


@pytest.mark.parametrize("scale", [1.0, 0.5])
def test_a_board_scattering_across_the_page_does_not_look_alike_a_moment_later(scale):
    for early, late in [(0.05, 0.15), (0.1, 0.3), (0.3, 0.6)]:
        assert not looks_alike(scaled(scattered(early), scale), scaled(scattered(late), scale)), (early, late)
    assert not looks_alike(scaled(board(), scale), scaled(scattered(0.05), scale))


def test_a_screen_fading_in_does_not_look_alike_once_it_is_in_but_the_last_of_a_fade_does():
    empty = Image.new("RGB", board().size, PAGE_GREY)

    assert not looks_alike(Image.blend(empty, board(), 0.5), board())
    assert looks_alike(Image.blend(empty, board(), 0.95), board())


def test_the_board_and_the_result_screen_do_not_look_alike():
    assert not looks_alike(board(), page_without_grid())
    assert not looks_alike(board(), Image.open(example("zip", "zip-result1.png")))  # nor screens of different sizes


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
        # Encoded once here: saving a 3747x1955 PNG for every look is slow.
        self.frames = tuple(png_bytes(frame) for frame in frames)
        self.shots = 0

    def screenshot(self) -> bytes:
        png = self.frames[min(self.shots, len(self.frames) - 1)]
        self.shots += 1
        return png


def png_bytes(frame: Image.Image) -> bytes:
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
    page, clock = Frames(blank_page()), StandInClock()
    wait = ResultWait(first_look=0.1, limit=0.6, poll=0.1)

    final = Player(page, result_wait=wait, clock=clock).final_screen()

    assert clock.now() == pytest.approx(0.6)
    assert page.shots > 2, "it kept looking"
    assert same(final, blank_page())


def test_a_page_that_shows_something_at_the_first_look_is_taken_at_once():
    # Queens, Tango and Mini Sudoku have always shown their board 2 s after the last move.
    page, clock = Frames(board()), StandInClock()
    wait = ResultWait(first_look=0.3, limit=10, poll=0.1)

    final = Player(page, result_wait=wait, clock=clock).final_screen()

    assert clock.now() == pytest.approx(0.3)
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
    page, clock = Frames(blank_page(), board()), StandInClock()
    wait = ResultWait(first_look=0, limit=0.3, poll=0.05, settle=5)

    final = Player(page, result_wait=wait, clock=clock).final_screen()

    assert clock.now() == pytest.approx(0.3), "not the 5 s of settling"
    assert same(final, board())
