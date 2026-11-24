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

import time

import numpy as np
import pytest
from PIL import Image, ImageDraw

from engines.play.games import GAMES
from engines.play.hub import not_played_today, played_today, shows_played_check

from .pages import card_svg, hub_html, hub_page, local_site

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


# In the browser: a local page stands in for the hub (see pages.hub_page).


@pytest.fixture
def context(browser):
    context = browser.new_context(device_scale_factor=2)  # a high-resolution screen
    yield context
    context.close()


TODAY = [("Queens", "/games/queens/", True), ("Tango", "/games/tango/", False), ("Zip", "/games/zip/", True)]


@pytest.mark.parametrize(("game", "played"), [("queens", True), ("tango", False), ("zip", True)])
def test_the_hub_says_which_games_were_played_today(context, tmp_path, game, played):
    assert played_today(context, GAMES[game], hub_page(tmp_path, *TODAY)) == played


def test_the_hub_is_looked_at_in_a_tab_that_is_closed_afterwards(context, tmp_path):
    game_page = context.new_page()

    played_today(context, GAMES["queens"], hub_page(tmp_path, *TODAY))

    assert context.pages == [game_page]
    assert game_page.url == "about:blank"


def test_a_card_that_links_by_the_whole_address_counts_too(context, tmp_path):
    # As the guests' hub links its cards (see tests/team/test_team_scout.py).
    hub = hub_page(tmp_path, ("Wend", "https://www.linkedin.com/games/wend/?trk=games_hub", True))

    assert played_today(context, GAMES["wend"], hub)


def test_a_hub_without_the_games_card_lets_it_be_played_and_says_so_soon(context, tmp_path, capsys):
    hub = hub_page(tmp_path, *TODAY)
    started = time.monotonic()

    assert not played_today(context, GAMES["patches"], hub, card_wait=1)
    assert time.monotonic() - started < 5
    assert "Patches" in capsys.readouterr().out
    assert context.pages == []


@pytest.fixture
def slow_hub():
    """The URL of a hub on a local server whose card pictures (Queens played,
    Tango not) arrive a second after the page, as on a slow line: the
    pictures' boxes show before the pictures do."""

    def answer(path: str) -> tuple[str, str]:
        if path.startswith("/icon/"):
            time.sleep(1)
            return card_svg(played="checked" in path), "image/svg+xml"
        cards = (("queens", "checked"), ("tango", "plain"))
        return "".join(
            f'<a href="/games/{slug}/"><img width="48" height="48" alt="" src="/icon/{icon}.svg"></a>'
            for slug, icon in cards
        ), "text/html"

    with local_site(answer) as (url, _):
        yield url


@pytest.mark.parametrize(("game", "played"), [("queens", True), ("tango", False)])
def test_a_card_picture_that_arrives_late_is_read_once_it_has_arrived(context, slow_hub, game, played):
    assert played_today(context, GAMES[game], slow_hub) == played


def test_a_hub_that_does_not_load_lets_the_game_be_played(context, tmp_path):
    assert not played_today(context, GAMES["queens"], (tmp_path / "nowhere.html").as_uri())
    assert context.pages == []


# Several games: the hub is opened once, and each game's card read on it.


@pytest.fixture
def served_hub():
    """TODAY's hub on a local server: its address, and the paths asked for."""
    page = hub_html(*TODAY)
    with local_site(lambda path: (page, "text/html")) as site:
        yield site


def test_one_look_at_the_hub_tells_which_of_several_games_are_still_to_play(context, served_hub, capsys):
    hub, asked = served_hub
    games = [GAMES[name] for name in ("zip", "tango", "patches", "queens")]  # no card for Patches

    still_to_play = not_played_today(context, games, hub, card_wait=1)

    assert still_to_play == [GAMES["tango"], GAMES["patches"]]
    assert asked.count("/") == 1
    assert context.pages == []
    assert "whether Patches was played" in capsys.readouterr().out


def test_a_hub_with_none_of_the_cards_costs_one_wait_not_one_per_game(context, tmp_path, capsys):
    # As after LinkedIn changed how its cards link: each game is played.
    hub = hub_page(tmp_path, ("Pinpoint", "/games/pinpoint/", True))
    games = [GAMES[name] for name in ("patches", "queens", "sudoku", "wend", "zip")]
    started = time.monotonic()

    still_to_play = not_played_today(context, games, hub, card_wait=1)

    assert time.monotonic() - started < 3  # one card_wait per game would be 5 s
    assert still_to_play == games
    printed = capsys.readouterr().out
    assert all(f"whether {game.title} was played" in printed for game in games)
    assert context.pages == []


def test_a_hub_that_does_not_load_lets_every_game_be_played_and_says_so_for_each(context, tmp_path, capsys):
    games = [GAMES[name] for name in ("queens", "tango")]

    assert not_played_today(context, games, (tmp_path / "nowhere.html").as_uri()) == games
    printed = capsys.readouterr().out.splitlines()
    assert [line.split(" was played")[0] for line in printed] == [
        "Couldn't see on the hub whether Queens",
        "Couldn't see on the hub whether Tango",
    ]
    assert context.pages == []
