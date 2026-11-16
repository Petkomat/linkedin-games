"""Seam: the guest tools the agent team uses, on local pages instead of LinkedIn.

`shot` saves what a game's page shows a guest (for boards of a game that isn't
built yet); `play` reads, solves and plays a built game as a guest, and keeps
a video, the final board and the solution for the PR.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from PIL import Image

from engines.play.games import GAMES
from engines.play.motion import INSTANT
from engines.play.timing import INSTANT as NO_WAITING
from tests.helpers import example

from .pages import SCALE, page_file, page_showing
from .test_play_in_browser import gestures, one_by_one, same_gestures

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from engines.play.browser import Player  # noqa: E402
from engines.play.guest import game_url, play, recorded_page, shot  # noqa: E402


def test_a_slug_is_a_linkedin_game_page_and_a_url_stays_as_it_is():
    assert game_url("sumbreak") == "https://www.linkedin.com/games/sumbreak/"
    assert game_url("file:///C:/pages/queens.html") == "file:///C:/pages/queens.html"


def test_a_shot_clicks_the_start_screen_away_and_saves_the_board(browser, tmp_path):
    page = page_showing(browser, example("queens", "queens1.png"), behind_start_screen=True)

    shot(page, tmp_path / "queens.png", start_wait=5, settle=0.5)

    queens = GAMES["queens"]
    saved = queens.scan(Image.open(tmp_path / "queens.png"))
    assert saved.puzzle == queens.scan(example("queens", "queens1.png")).puzzle


def test_the_shot_command_opens_any_page_in_a_fresh_browser(tmp_path):
    # A new game isn't in the registry yet; the command takes its page as it is.
    url = page_file(tmp_path, example("tango", "tango1.png"), behind_start_screen=True)

    done = subprocess.run(
        [sys.executable, "-m", "engines.play.guest", "shot", url, "--out", str(tmp_path / "new" / "board.png")],
        capture_output=True, text=True, timeout=120, check=False,
    )

    assert done.returncode == 0, done.stderr
    tango = GAMES["tango"]
    saved = tango.scan(Image.open(tmp_path / "new" / "board.png"))
    assert saved.puzzle == tango.scan(example("tango", "tango1.png")).puzzle


def test_a_guest_play_enters_the_moves_and_keeps_a_video_the_final_board_and_the_solution(browser, tmp_path):
    queens = GAMES["queens"]
    original = queens.scan(example("queens", "queens1.png"))
    url = page_file(tmp_path, example("queens", "queens1.png"), scale=SCALE, behind_start_screen=True)
    out = tmp_path / "out"

    with recorded_page(browser, out / "queens.webm", device_scale_factor=SCALE) as page:
        page.goto(url)
        played = play(page, queens, out, Player(page, tempo=NO_WAITING, hand=INSTANT), start_wait=5, board_wait=8)
        recorded = gestures(page.evaluate("events"), original.grid)

    assert played
    _start_click, *moves = recorded  # "Start game" lies over the board's first row
    assert same_gestures(moves, one_by_one(queens.moves(original.puzzle)))
    assert "Q" in (out / "queens.md").read_text(encoding="utf-8")
    assert Image.open(out / "queens.png").size[0] > 0
    assert (out / "queens.webm").stat().st_size > 0


def test_a_guest_play_without_a_board_plays_nothing_and_keeps_what_it_saw(browser, tmp_path):
    blank = tmp_path / "blank.html"
    blank.write_text("<p>Sign in to play</p>", encoding="utf-8")
    out = tmp_path / "out"

    with recorded_page(browser, out / "zip.webm") as page:
        page.goto(blank.as_uri())
        played = play(page, GAMES["zip"], out, Player(page, tempo=NO_WAITING, hand=INSTANT), start_wait=0, board_wait=2)

    assert not played
    assert (out / "zip.png").exists()
    assert not (out / "zip.md").exists()
