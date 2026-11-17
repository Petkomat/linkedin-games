"""Seams: the play on the user's account, on a local page instead of LinkedIn;
where the command line saves the screenshot of a play, and how long it keeps
the browser open afterwards."""

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

from .pages import page_showing
from .test_play_in_browser import presses

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from engines.play.__main__ import leave_open, play, screenshot_path  # noqa: E402

STARTED = datetime(2026, 11, 17, 9, 30)


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
    path = screenshot_path("zip", datetime(2026, 11, 10, 14, 3, 7))

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
