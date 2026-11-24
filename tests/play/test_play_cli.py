"""Seams: the play on the user's account, on a local page instead of LinkedIn;
where the command line saves the screenshot of a play, and how long it keeps
the browser open afterwards; skipping a game the hub shows as played today."""

import dataclasses
import re
import time
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from engines.play.browser import Player
from engines.play.games import GAMES
from engines.play.motion import INSTANT
from engines.play.result import ResultWait
from engines.play.timing import INSTANT as NO_WAITING
from tests.helpers import example

from .pages import SCALE, hub_html, hub_page, local_site, page_file, page_showing, showing
from .test_play_in_browser import presses

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from engines.play.__main__ import leave_open, play, run, screenshot_path  # noqa: E402

STARTED = datetime(2026, 11, 17, 9, 30)
LINKEDIN = re.compile(r"^https?://([^/]*\.)?linkedin\.com/")


@pytest.fixture
def linkedin() -> list[str]:
    """The addresses on LinkedIn the signed-in page tried to open."""
    return []


@pytest.fixture
def signed_in(browser, linkedin):
    """A page that looks signed in to LinkedIn (it has the login cookie) on a
    2x screen as big as queens1.png, and can't reach LinkedIn at all."""
    _, viewport = showing(example("queens", "queens1.png"))
    context = browser.new_context(device_scale_factor=SCALE, viewport=viewport)
    context.add_cookies([{"name": "li_at", "value": "stand-in", "url": "https://www.linkedin.com"}])
    context.route(LINKEDIN, lambda route: (linkedin.append(route.request.url), route.abort()))
    yield context.new_page()
    context.close()


def fast_player(page) -> Player:
    return Player(page, tempo=NO_WAITING, hand=INSTANT, result_wait=ResultWait(first_look=0.2, limit=2, poll=0.2, settle=0.2))


def on_a_local_page(folder: Path, game: str, screenshot: str):
    """`game`, with a local page that shows its example `screenshot` for its own."""
    return dataclasses.replace(GAMES[game], url=page_file(folder, example(game, screenshot), scale=SCALE))


def into(folder: Path):
    """Where `run` saves each game's play: folder/<game>.png."""
    return lambda game, started: folder / f"{game.name}.png"


def test_a_game_the_hub_shows_as_played_today_is_skipped_without_opening_it(signed_in, linkedin, tmp_path, capsys):
    hub = hub_page(tmp_path, ("Queens", "/games/queens/", True), ("Tango", "/games/tango/", False))
    plays = tmp_path / "plays"

    code = run(fast_player(signed_in), [GAMES["queens"]], board_wait=5, hub=hub, save_as=into(plays))

    assert code == 0
    assert capsys.readouterr().out.splitlines()[-1] == "Queens: already played today; skipped."
    assert linkedin == []  # Queens' page was never opened
    assert signed_in.url == "about:blank"
    assert not plays.exists()  # not even an empty folder for the play
    assert not signed_in.is_closed()  # main closes the browser at once; nothing waits for --close-after


def test_when_the_hub_does_not_load_the_game_is_opened_and_played(signed_in, linkedin, tmp_path, capsys):
    # The hub is LinkedIn's own here, and LinkedIn can't be reached. Chrome
    # then opens its error page in the hub's tab, which must not stop the
    # game's page from opening.
    queens = on_a_local_page(tmp_path, "queens", "queens1.png")

    code = run(fast_player(signed_in), [queens], board_wait=5, close_after=0, save_as=into(tmp_path))

    assert linkedin == ["https://www.linkedin.com/games/"]
    assert code == 0
    assert queens.scan(Image.open(tmp_path / "queens.png")).puzzle == queens.scan(example("queens", "queens1.png")).puzzle
    printed = capsys.readouterr().out
    assert "skipped" not in printed
    assert "Done" in printed


def test_a_game_the_hub_shows_as_not_played_is_opened_and_played(signed_in, tmp_path, capsys):
    queens = on_a_local_page(tmp_path, "queens", "queens1.png")
    hub = hub_page(tmp_path, ("Queens", queens.url, False))  # its card links to the whole address

    code = run(fast_player(signed_in), [queens], board_wait=5, close_after=0, hub=hub, save_as=into(tmp_path))

    assert code == 0
    assert (tmp_path / "queens.png").exists()
    assert "Done" in capsys.readouterr().out


def test_several_games_look_at_the_hub_once_skip_the_played_ones_and_play_the_rest(
    signed_in, linkedin, tmp_path, capsys
):
    queens = on_a_local_page(tmp_path, "queens", "queens1.png")
    sudoku = on_a_local_page(tmp_path, "sudoku", "sudoku1.png")
    page = hub_html(
        ("Queens", queens.url, False),
        ("Tango", "/games/tango/", True),
        ("Sudoku", sudoku.url, False),
        ("Zip", "/games/zip/", True),
    )
    games = [queens, GAMES["tango"], sudoku, GAMES["zip"]]

    with local_site(lambda path: (page, "text/html")) as (hub, asked):
        code = run(fast_player(signed_in), games, board_wait=5, close_after=0, hub=hub, save_as=into(tmp_path))

    assert code == 0
    assert asked.count("/") == 1
    assert linkedin == []  # Tango's and Zip's pages were never opened
    printed = capsys.readouterr().out.splitlines()
    assert "Tango: already played today; skipped." in printed
    assert "Zip: already played today; skipped." in printed
    assert sum(line.startswith("Done") for line in printed) == 2
    for game, screenshot in ((queens, "queens1.png"), (sudoku, "sudoku1.png")):
        played = game.scan(Image.open(tmp_path / f"{game.name}.png")).puzzle
        assert played == game.scan(example(game.name, screenshot)).puzzle


def test_a_game_without_a_board_fails_the_run_but_the_games_after_it_are_still_played(signed_in, tmp_path, capsys):
    nothing = tmp_path / "nothing.html"
    nothing.write_text("<body></body>", encoding="utf-8")
    tango = dataclasses.replace(GAMES["tango"], url=nothing.as_uri())
    queens = on_a_local_page(tmp_path, "queens", "queens1.png")
    hub = hub_page(tmp_path, ("Tango", tango.url, False), ("Queens", queens.url, False))

    code = run(fast_player(signed_in), [tango, queens], board_wait=2, close_after=0, hub=hub, save_as=into(tmp_path))

    assert code == 1
    assert (tmp_path / "queens.png").exists()
    printed = capsys.readouterr().out
    assert "No solvable board" in printed
    assert "Done" in printed


def test_a_play_saves_the_solution_and_what_shows_after_a_blank_page(browser, tmp_path, capsys):
    # Zip and Wend went blank for more than 2 s on their way to the result screen.
    queens = GAMES["queens"]
    page = page_showing(
        browser, example("queens", "queens1.png"), blank_after_moves=presses("queens", "queens1.png"), back_after_ms=2500
    )
    player = Player(page, tempo=NO_WAITING, hand=INSTANT, result_wait=ResultWait(first_look=0.5, limit=10, poll=0.2, settle=0.2))
    output = tmp_path / "queens.png"

    played = play(player, queens, output, board_wait=5, started=STARTED)

    assert played
    assert queens.scan(Image.open(output)).puzzle == queens.scan(example("queens", "queens1.png")).puzzle
    assert "Q" in output.with_suffix(".md").read_text(encoding="utf-8")
    assert "Done" in capsys.readouterr().out


def test_a_play_whose_page_stays_blank_is_still_done_and_says_the_page_looked_blank(browser, tmp_path, capsys):
    page = page_showing(browser, example("queens", "queens1.png"), blank_after_moves=presses("queens", "queens1.png"))
    player = Player(page, tempo=NO_WAITING, hand=INSTANT, result_wait=ResultWait(first_look=0.2, limit=1, poll=0.2, settle=0))
    output = tmp_path / "queens.png"

    played = play(player, GAMES["queens"], output, board_wait=5, started=STARTED)

    assert played
    assert output.exists()
    printed = capsys.readouterr().out
    assert "looked blank" in printed
    assert "Done" in printed


def test_each_play_is_saved_under_its_game_named_by_when_it_started():
    path = screenshot_path(GAMES["zip"], datetime(2026, 11, 10, 14, 3, 7))

    assert path == Path("plays") / "zip" / "2026-11-10_14-03-07.png"


def test_with_close_after_the_page_stays_that_long_and_then_closes(browser):
    # For playing several games in a row: nobody has to close each window.
    page = browser.new_page()

    started = time.monotonic()
    leave_open(page, close_after=0.5)

    assert 0.5 <= time.monotonic() - started < 5
    assert page.is_closed()


def test_a_page_the_user_already_closed_is_left_alone(browser):
    page = browser.new_page()
    page.close()

    leave_open(page, close_after=0.5)

    assert page.is_closed()
