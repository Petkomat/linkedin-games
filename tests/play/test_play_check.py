"""Seam: the live check on local pages instead of LinkedIn. It reads and solves
the board, saves what it saw, and plays nothing."""

import pytest

from engines.play.games import GAMES
from tests.helpers import example

from .pages import page_showing

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from engines.play.check import check_game  # noqa: E402


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


def test_a_page_without_a_board_fails_and_keeps_a_screenshot_of_what_it_saw(browser, tmp_path):
    page = browser.new_page()
    page.set_content("<p>Sign in to play</p>")

    assert not check_game(page, GAMES["zip"], tmp_path, start_wait=0, board_wait=2)
    assert (tmp_path / "zip.png").exists()
    assert not (tmp_path / "zip.md").exists()
