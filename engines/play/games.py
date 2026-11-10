"""The games the player can play: where they are and how to read and solve them."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from ..common.actions import Action
from ..patches import moves as patches_moves
from ..patches import ocr as patches_ocr
from ..queens import moves as queens_moves
from ..queens import ocr as queens_ocr
from ..sudoku import moves as sudoku_moves
from ..sudoku import ocr as sudoku_ocr
from ..tango import moves as tango_moves
from ..tango import ocr as tango_ocr
from ..vision import ImageSource
from ..wend import moves as wend_moves
from ..wend import ocr as wend_ocr
from ..zip import moves as zip_moves
from ..zip import ocr as zip_ocr


@dataclass(frozen=True)
class Game:
    name: str
    url: str
    scan: Callable[[ImageSource], Any]  # returns a scan with .puzzle and .grid
    moves: Callable[[Any], list[Action] | None]  # None if the puzzle has no solution


def _linkedin(name: str, slug: str, ocr: ModuleType, moves: ModuleType) -> Game:
    return Game(name, f"https://www.linkedin.com/games/{slug}/", ocr.scan, moves.moves)


GAMES = {
    game.name: game
    for game in (
        _linkedin("patches", "patches", patches_ocr, patches_moves),
        _linkedin("queens", "queens", queens_ocr, queens_moves),
        _linkedin("sudoku", "mini-sudoku", sudoku_ocr, sudoku_moves),
        _linkedin("tango", "tango", tango_ocr, tango_moves),
        _linkedin("wend", "wend", wend_ocr, wend_moves),
        _linkedin("zip", "zip", zip_ocr, zip_moves),
    )
}
