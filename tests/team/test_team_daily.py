"""The daily guest run's view of what is built: the slugs of the registered
games, which the Scout leaves out of the hub's new games."""

from __future__ import annotations

import pytest

from engines.play.games import GAMES

pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")

from team.daily import built_slugs  # noqa: E402

HUB = "https://www.linkedin.com/games/"


def test_the_built_slugs_are_the_registered_games_slugs():
    assert built_slugs() == {game.slug for game in GAMES.values()}
    assert built_slugs() == {"patches", "queens", "mini-sudoku", "sumbreak", "tango", "wend", "zip"}


def test_each_game_is_at_its_slug_on_the_hub():
    for game in GAMES.values():
        assert game.url == f"{HUB}{game.slug}/"
    assert GAMES["sudoku"].url == "https://www.linkedin.com/games/mini-sudoku/"
