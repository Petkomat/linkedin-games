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

import base64
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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


# In the browser: a local page stands in for the hub, with cards as the owner
# describes them, a[href="/games/<slug>/"] around a 48x48 SVG picture.

ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#7048c8"/><stop offset="1" stop-color="#e66ea0"/></linearGradient></defs>'
    '<rect width="48" height="48" rx="8" fill="url(#g)"/>{check}</svg>'
)
CHECK_SVG = (
    '<circle cx="24" cy="24" r="11.5" fill="#057642"/>'
    '<path d="M19 24 l3.5 4 l7 -8" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
)


def hub_page(folder, *cards: tuple[str, str, bool]) -> str:
    """The URL of a local hub with a card for each (title, href, played)."""
    items = "".join(
        f'<li><a href="{href}"><img width="48" height="48" alt="" '
        f'src="data:image/svg+xml;base64,{_base64(ICON_SVG.format(check=CHECK_SVG if played else ""))}">'
        f"<p>{title}</p></a></li>"
        for title, href, played in cards
    )
    path = folder / "hub.html"
    path.write_text(f"<body style='margin:0;background:#f4f2ee'><ul>{items}</ul></body>", encoding="utf-8")
    return path.as_uri()


def _base64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


@pytest.fixture
def page(browser):
    page = browser.new_page(device_scale_factor=2)  # a high-resolution screen
    yield page
    page.close()


TODAY = [("Queens", "/games/queens/", True), ("Tango", "/games/tango/", False), ("Zip", "/games/zip/", True)]


@pytest.mark.parametrize(("game", "played"), [("queens", True), ("tango", False), ("zip", True)])
def test_the_hub_says_which_games_were_played_today(page, tmp_path, game, played):
    from engines.play.games import GAMES
    from engines.play.hub import played_today

    assert played_today(page, GAMES[game], hub_page(tmp_path, *TODAY)) == played


def test_a_card_that_links_by_the_whole_address_counts_too(page, tmp_path):
    # As the guests' hub links its cards (see tests/team/test_team_scout.py).
    from engines.play.games import GAMES
    from engines.play.hub import played_today

    hub = hub_page(tmp_path, ("Wend", "https://www.linkedin.com/games/wend/?trk=games_hub", True))

    assert played_today(page, GAMES["wend"], hub)


def test_a_hub_without_the_games_card_lets_it_be_played_and_says_so_soon(page, tmp_path, capsys):
    from engines.play.games import GAMES
    from engines.play.hub import played_today

    hub = hub_page(tmp_path, *TODAY)
    started = time.monotonic()

    assert not played_today(page, GAMES["patches"], hub, card_wait=1)
    assert time.monotonic() - started < 5
    assert "Patches" in capsys.readouterr().out


@pytest.fixture
def slow_hub():
    """The URL of a hub on a local server whose card pictures (Queens played,
    Tango not) arrive a second after the page, as on a slow line: the
    pictures' boxes show before the pictures do."""

    class Hub(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server's name)
            if self.path.startswith("/icon/"):
                time.sleep(1)
                body, kind = ICON_SVG.format(check=CHECK_SVG if "checked" in self.path else "").encode(), "image/svg+xml"
            else:
                cards = (("queens", "checked"), ("tango", "plain"))
                body, kind = "".join(
                    f'<a href="/games/{slug}/"><img width="48" height="48" alt="" src="/icon/{icon}.svg"></a>'
                    for slug, icon in cards
                ).encode(), "text/html"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Hub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


@pytest.mark.parametrize(("game", "played"), [("queens", True), ("tango", False)])
def test_a_card_picture_that_arrives_late_is_read_once_it_has_arrived(page, slow_hub, game, played):
    from engines.play.games import GAMES
    from engines.play.hub import played_today

    assert played_today(page, GAMES[game], slow_hub) == played


def test_a_hub_that_does_not_load_lets_the_game_be_played(page, tmp_path):
    from engines.play.games import GAMES
    from engines.play.hub import played_today

    assert not played_today(page, GAMES["queens"], (tmp_path / "nowhere.html").as_uri())
