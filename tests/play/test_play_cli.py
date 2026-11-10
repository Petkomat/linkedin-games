"""Seam: where the command line saves the screenshot of a play."""

from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from engines.play.__main__ import screenshot_path  # noqa: E402


def test_each_play_is_saved_under_its_game_named_by_when_it_started():
    path = screenshot_path("zip", datetime(2026, 11, 10, 14, 3, 7))

    assert path == Path("plays") / "zip" / "2026-11-10_14-03-07.png"
