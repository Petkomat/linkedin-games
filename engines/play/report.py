"""The readable solution saved next to each play's screenshot."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .games import Game


def report(game: Game, puzzle: Any, started: datetime) -> str:
    """Markdown: a title, the solution as a table, and a legend."""
    table = game.solution_text(puzzle, game.solve(puzzle))
    return f"# {game.title}, {started:%Y-%m-%d %H:%M:%S}\n\n```\n{table}\n```\n\n{game.legend}\n"
