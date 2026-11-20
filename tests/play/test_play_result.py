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


class Moving(Frames):
    """Stands in for a page whose screenshots are `frames` over and over: an
    animation that never ends."""

    def screenshot(self) -> bytes:
        png = self.frames[self.shots % len(self.frames)]
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


def faint_dashes() -> Image.Image:
    """The blank page with short grey dashes on every fourth row, like faint
    text: not blank, yet it hardly moves the average colour of any block."""
    page = blank_page()
    draw = ImageDraw.Draw(page)
    for y in range(TOP_BARS, page.height, 4):
        draw.line((page.width // 3 + 10, y, page.width // 2, y), fill=(200, 200, 200))
    return page


def final_screen(page: Frames, wait: ResultWait | None = None, game: str = "queens") -> tuple[Image.Image, float]:
    """The player's final screen of `game` on `page`, and when it was taken on
    a stand-in clock started at the last move. By default the player waits as
    it does on LinkedIn: a first look 2 s after the last move, then looks 1 s
    apart."""
    clock = StandInClock()
    final = Player(page, result_wait=wait or ResultWait(), clock=clock).final_screen(GAMES[game])
    return final, clock.now()


# Sumbreak, measured on sumbreak5.png, a guest's whole window (1280x1600)
SUMBREAK_CARD = (416, 81, 864, 648)  # the card with the board and its buttons
SUMBREAK_CELLS = (448, 580, 712), (149, 281, 414)  # the left edges of its columns, the top edges of its rows
SUMBREAK_CELL = 120  # a cell's side
EMPTY_CELL = (233, 227, 220)
LINKEDIN_BLUE = (10, 102, 194)


def sumbreak_tiles() -> list[Image.Image]:
    """The eight tiles of sumbreak5.png, row by row; its ninth cell is empty."""
    page = Image.open(example("sumbreak", "sumbreak5.png")).convert("RGB")
    xs, ys = SUMBREAK_CELLS
    tiles = [page.crop((x, y, x + SUMBREAK_CELL, y + SUMBREAK_CELL)) for y in ys for x in xs]
    return [tile for tile in tiles if tile.getpixel((60, 10)) != EMPTY_CELL]


def lone_tile() -> Image.Image:
    """sumbreak5.png with all but its last tile merged away: the board right
    after the last merge."""
    page = Image.open(example("sumbreak", "sumbreak5.png")).convert("RGB")
    draw = ImageDraw.Draw(page)
    xs, ys = SUMBREAK_CELLS
    for y in ys:
        for x in xs:
            if (x, y) != (xs[-1], ys[-1]):
                draw.rounded_rectangle((x, y, x + SUMBREAK_CELL - 1, y + SUMBREAK_CELL - 1), 8, fill=EMPTY_CELL)
    return page


def fallen_tiles() -> Image.Image:
    """sumbreak5.png's tiles fallen to the bottom of the window, in a heap two
    tiles high, slightly turned, and the card gone: the way Sumbreak's tiles
    lay at the bottom of an otherwise empty page after its last merge on
    2026-11-20."""
    page = Image.open(example("sumbreak", "sumbreak5.png")).convert("RGB")
    ImageDraw.Draw(page).rectangle(SUMBREAK_CARD, fill=PAGE_GREY)
    rng = random.Random(1)
    tiles = sumbreak_tiles()
    for row, heap in enumerate((tiles[:5], tiles[5:])):
        left = page.width // 2 - len(heap) * SUMBREAK_CELL // 2
        top = page.height - (row + 1) * (SUMBREAK_CELL - 10)
        for i, tile in enumerate(heap):
            turned = tile.rotate(rng.uniform(-12, 12), expand=True, fillcolor=PAGE_GREY)
            page.paste(turned, (left + i * SUMBREAK_CELL, top - (turned.height - SUMBREAK_CELL)))
    return page


def logo_page() -> Image.Image:
    """An empty page with LinkedIn's logo, a blue square, in its middle: what
    LinkedIn shows between Sumbreak's fallen tiles and its result screen."""
    page = Image.new("RGB", (1280, 1600), PAGE_GREY)
    middle_x, middle_y = page.width // 2, page.height // 2
    ImageDraw.Draw(page).rounded_rectangle((middle_x - 28, middle_y - 28, middle_x + 28, middle_y + 28), 6, fill=LINKEDIN_BLUE)
    return page


def sumbreak_result() -> Image.Image:
    return Image.open(example("sumbreak", "sumbreak-result1.png")).convert("RGB")


def test_sumbreaks_fallen_tiles_are_not_saved_however_long_they_lie_still():
    # The guest play on 2026-11-20: after the last merge the lone tile showed,
    # then the tiles fell to the bottom of the page and lay there, then came an
    # empty page with LinkedIn's logo, then the result screen.
    fallen = fallen_tiles()
    assert not looks_blank(fallen) and looks_blank(logo_page())
    page = Frames(lone_tile(), fallen, fallen, fallen, fallen, logo_page(), sumbreak_result())

    final, taken = final_screen(page, game="sumbreak")

    assert same(final, sumbreak_result())
    assert taken == pytest.approx(9), "the result showed at 8 s and held still at 9 s"


def test_a_board_that_already_holds_still_is_taken_at_the_second_look():
    # Queens, Tango and Mini Sudoku have always shown their board 2 s after the last move.
    page = Frames(board())

    final, taken = final_screen(page)

    assert taken == pytest.approx(3)
    assert page.shots == 2
    assert same(final, board())


def test_blank_screens_are_waited_out_and_the_first_screen_that_holds_still_is_kept():
    page = Frames(blank_page(), blank_page(), blank_page(), board())

    final, taken = final_screen(page)

    assert taken == pytest.approx(6)  # blank at 2, 3 and 4 s; the board at 5 and 6 s
    assert same(final, board())


def test_a_page_that_stays_blank_is_waited_for_until_the_limit_and_then_taken_as_it_is():
    page = Frames(blank_page())

    final, taken = final_screen(page, ResultWait(limit=6))

    assert taken == pytest.approx(6)
    assert page.shots == 5, "it kept looking, at 2, 3, 4, 5 and 6 s"
    assert same(final, blank_page())


def test_a_moving_frame_then_a_blank_page_then_the_result_saves_the_result():
    # Sumbreak on 2026-11-18: its tiles scattered, the page went blank, and
    # the result screen showed up 5-6 s after the last move.
    page = Frames(scattered(0.1), blank_page(), blank_page(), page_without_grid())

    final, taken = final_screen(page)

    assert taken == pytest.approx(6)
    assert same(final, page_without_grid())


def test_of_two_different_moving_frames_and_a_steady_result_the_steady_one_is_saved():
    page = Frames(scattered(0.05), scattered(0.15), page_without_grid())

    final, taken = final_screen(page)

    assert taken == pytest.approx(5)
    assert same(final, page_without_grid())


def test_a_screen_that_never_holds_still_is_taken_as_last_seen_at_the_limit():
    frames = scattered(0.05), scattered(0.15), scattered(0.3)
    page = Moving(*frames)

    final, taken = final_screen(page, ResultWait(limit=6))

    assert taken == pytest.approx(6)
    assert page.shots == 5
    assert same(final, frames[1]), "the fifth look"


def test_a_screen_that_has_just_shown_up_gets_time_to_finish_fading_in():
    fading_in = Image.blend(blank_page(), board(), 0.3)
    assert not looks_blank(fading_in)
    page = Frames(blank_page(), fading_in, board())

    final, taken = final_screen(page)

    assert taken == pytest.approx(5)
    assert same(final, board())


def test_a_blank_look_never_holds_still_with_the_one_before_it():
    faint = faint_dashes()
    assert not looks_blank(faint) and looks_alike(faint, blank_page())
    page = Frames(faint, blank_page(), blank_page(), page_without_grid())

    final, _ = final_screen(page)

    assert same(final, page_without_grid())


def test_the_second_look_comes_at_the_limit_at_the_latest():
    page = Frames(blank_page(), board())

    final, taken = final_screen(page, ResultWait(first_look=0, limit=0.3, poll=0.05, settle=5))

    assert taken == pytest.approx(0.3), "not the 5 s of settling"
    assert same(final, board())


class TimedFrames(Frames):
    """Frames whose screenshots are taken on `clock`: `looks` says when each
    one was taken, and each takes `each_look_takes` s, as taking and decoding
    a 3747x1955 screenshot can on a busy machine."""

    def __init__(self, *frames: Image.Image, clock: StandInClock, each_look_takes: float) -> None:
        super().__init__(*frames)
        self.clock = clock
        self.each_look_takes = each_look_takes
        self.looks: list[float] = []

    def screenshot(self) -> bytes:
        self.looks.append(self.clock.now())
        self.clock.spend(self.each_look_takes)
        return super().screenshot()


# On a busy machine, taking and decoding one screenshot can take seconds.


def test_a_first_look_that_ends_after_the_limit_is_taken_as_it_is():
    clock = StandInClock()
    page = TimedFrames(blank_page(), board(), clock=clock, each_look_takes=3)

    final = Player(page, result_wait=ResultWait(limit=4), clock=clock).final_screen(GAMES["queens"])

    assert page.looks == [2], "no look after the limit"
    assert clock.now() == 5
    assert same(final, blank_page())


def test_slow_looks_at_a_blank_page_still_stop_at_the_limit():
    clock = StandInClock()
    page = TimedFrames(blank_page(), clock=clock, each_look_takes=0.5)

    final = Player(page, result_wait=ResultWait(limit=6), clock=clock).final_screen(GAMES["queens"])

    assert page.looks == [2, 3.5, 5, 6], "a second's wait between looks, and the last wait cut short by the limit"
    assert same(final, blank_page())


def test_a_screen_that_shows_up_at_the_limit_on_a_busy_machine_is_taken_without_a_second_look():
    clock = StandInClock()
    page = TimedFrames(blank_page(), board(), clock=clock, each_look_takes=1.5)

    final = Player(page, result_wait=ResultWait(limit=4), clock=clock).final_screen(GAMES["queens"])

    assert page.looks == [2, 4], "the board showed at 4 s, and that look took until 5.5 s"
    assert same(final, board())


def test_on_a_busy_machine_the_second_look_comes_a_second_after_the_first_one_ends():
    clock = StandInClock()
    page = TimedFrames(board(), clock=clock, each_look_takes=1.5)

    final = Player(page, result_wait=ResultWait(), clock=clock).final_screen(GAMES["queens"])

    assert page.looks == [2, 4.5], "the first look took until 3.5 s"
    assert clock.now() == 6
    assert same(final, board())
