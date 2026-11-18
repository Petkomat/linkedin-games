"""Seam: the live check on local pages instead of LinkedIn. It reads and solves
the board, saves what it saw, and plays nothing."""

import pytest

from engines.play.games import GAMES
from tests.helpers import example

from .pages import page_file, page_showing

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from engines.play.check import check_all, check_game  # noqa: E402


def test_a_board_that_reads_and_solves_passes_and_its_solution_is_saved(browser, tmp_path):
    page = page_showing(browser, example("sudoku", "sudoku1.png"))

    assert check_game(page, GAMES["sudoku"], tmp_path, start_wait=0, board_wait=5)
    assert (tmp_path / "sudoku.png").exists()
    assert "1 2 3 | 4 5 6" in (tmp_path / "sudoku.md").read_text(encoding="utf-8")
    assert page.evaluate("events") == [], "nothing was played"


def test_a_start_screen_is_clicked_away_first(browser, tmp_path):
    page = page_showing(browser, example("queens", "queens1.png"), behind_start_screen=True)

    assert check_game(page, GAMES["queens"], tmp_path, start_wait=5, board_wait=5)


def test_an_intro_and_then_a_start_screen_are_both_clicked_away(browser, tmp_path):
    # Mini Sudoku showed guests an intro ("Solve now") on GitHub's machines.
    page = page_showing(browser, example("sudoku", "sudoku1.png"), behind_start_screen=True, behind_intro=True)

    assert check_game(page, GAMES["sudoku"], tmp_path, start_wait=5, board_wait=5)


def test_a_start_screen_that_shows_up_late_is_still_clicked_away(browser, tmp_path):
    # GitHub's machines are slow: the screen may come after the first look for it.
    page = page_showing(browser, example("queens", "queens1.png"), behind_start_screen=True, screens_after_ms=2500)

    assert check_game(page, GAMES["queens"], tmp_path, start_wait=1, board_wait=8)


def test_the_board_is_read_as_soon_as_a_late_start_screen_is_gone(browser, tmp_path):
    # A screen halfway through the wait leaves 4 s, plenty to read the board
    # twice, as long as no time goes on looking for more start screens.
    page = page_showing(browser, example("queens", "queens1.png"), behind_start_screen=True, screens_after_ms=4000)

    assert check_game(page, GAMES["queens"], tmp_path, start_wait=1, board_wait=8)


def test_a_start_screen_inside_an_iframe_is_clicked_away(browser, tmp_path):
    # LinkedIn runs Mini Sudoku, intro included, in an iframe.
    page = page_showing(
        browser, example("sudoku", "sudoku1.png"), behind_start_screen=True, behind_intro=True, in_iframe=True
    )

    assert check_game(page, GAMES["sudoku"], tmp_path, start_wait=5, board_wait=8)


def test_a_page_without_a_board_fails_and_keeps_a_screenshot_of_what_it_saw(browser, tmp_path):
    page = browser.new_page()
    page.set_content("<p>Sign in to play</p>")

    assert not check_game(page, GAMES["zip"], tmp_path, start_wait=0, board_wait=2)
    assert (tmp_path / "zip.png").exists()
    assert not (tmp_path / "zip.md").exists()


def test_every_game_is_checked_on_its_own_page_and_reported_by_name(browser, tmp_path):
    # What the Watcher runs every day: one verdict per game.
    blank = tmp_path / "blank.html"
    blank.write_text("<p>Sign in to play</p>", encoding="utf-8")
    urls = {
        "queens": page_file(tmp_path, example("queens", "queens1.png"), behind_start_screen=True),
        "sudoku": page_file(tmp_path, example("sudoku", "sudoku1.png")),
        "zip": blank.as_uri(),
    }

    verdicts = check_all(["queens", "sudoku", "zip"], tmp_path / "out", browser, urls, start_wait=1, board_wait=5)

    assert verdicts == {"queens": True, "sudoku": True, "zip": False}
    assert (tmp_path / "out" / "zip.png").exists(), "what the failed check saw"
