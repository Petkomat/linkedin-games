"""Seams: where the command line saves the screenshot of a play, and how long
it keeps the browser open afterwards."""

import time
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from engines.play.__main__ import leave_open, screenshot_path  # noqa: E402


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
