"""Helpers shared by every game's tests."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def example(game: str, filename: str) -> Path:
    """Path of a screenshot in examples/<game>/."""
    return EXAMPLES / game / filename


def text_grid(text: str) -> list[list[str]]:
    """A board typed as text: one character per cell, one line per row.

    Spaces and '|' are ignored, and so are lines without cells (blank lines or
    '---' separators), so boards can be laid out readably.
    """
    rows = []
    for line in text.strip().splitlines():
        cells = [ch for ch in line if ch not in " |\t-"]
        if cells:
            rows.append(cells)
    return rows


def solve_within(solve: Callable[[Any], Any], puzzle: Any, seconds: float) -> Any:
    """`solve(puzzle)`, failing the test if it takes longer than `seconds`.

    The solver runs in a daemon thread, so a runaway search fails the test
    instead of hanging the whole run.
    """
    result = {}
    worker = threading.Thread(target=lambda: result.update(answer=solve(puzzle)), daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        pytest.fail(f"solve() took longer than {seconds}s")
    return result["answer"]
