"""The games the player can play: where they are, and how to read, solve and
write them down."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..common.actions import Action
from ..patches import moves as patches_moves
from ..patches import ocr as patches_ocr
from ..patches import render as patches_render
from ..patches import solver as patches_solver
from ..queens import moves as queens_moves
from ..queens import ocr as queens_ocr
from ..queens import render as queens_render
from ..queens import solver as queens_solver
from ..sudoku import moves as sudoku_moves
from ..sudoku import ocr as sudoku_ocr
from ..sudoku import render as sudoku_render
from ..sudoku import solver as sudoku_solver
from ..tango import moves as tango_moves
from ..tango import ocr as tango_ocr
from ..tango import render as tango_render
from ..tango import solver as tango_solver
from ..vision import ImageSource
from ..wend import moves as wend_moves
from ..wend import ocr as wend_ocr
from ..wend import render as wend_render
from ..wend import solver as wend_solver
from ..zip import moves as zip_moves
from ..zip import ocr as zip_ocr
from ..zip import render as zip_render
from ..zip import solver as zip_solver


@dataclass(frozen=True)
class Game:
    name: str
    title: str
    url: str
    scan: Callable[[ImageSource], Any]  # returns a scan with .puzzle and .grid
    moves: Callable[[Any], list[Action] | None]  # None if the puzzle has no solution
    solve: Callable[[Any], Any | None]
    solution_text: Callable[[Any, Any], str]  # (puzzle, solution) -> a readable table
    legend: str  # what the table's symbols mean


def _linkedin(slug: str, **game: Any) -> Game:
    return Game(url=f"https://www.linkedin.com/games/{slug}/", **game)


GAMES = {
    game.name: game
    for game in (
        _linkedin(
            "patches", name="patches", title="Patches",
            scan=patches_ocr.scan, moves=patches_moves.moves, solve=patches_solver.solve,
            solution_text=lambda p, s: patches_render.solution_text(p.rows, p.cols, s),
            legend="Each letter is one patch.",
        ),
        _linkedin(
            "queens", name="queens", title="Queens",
            scan=queens_ocr.scan, moves=queens_moves.moves, solve=queens_solver.solve,
            solution_text=queens_render.solution_text,
            legend="Q is a queen; small letters are the colour regions.",
        ),
        _linkedin(
            "mini-sudoku", name="sudoku", title="Sudoku",
            scan=sudoku_ocr.scan, moves=sudoku_moves.moves, solve=sudoku_solver.solve,
            solution_text=lambda p, s: sudoku_render.grid_text(s, p.box),
            legend="Lines separate the boxes.",
        ),
        _linkedin(
            "tango", name="tango", title="Tango",
            scan=tango_ocr.scan, moves=tango_moves.moves, solve=tango_solver.solve,
            solution_text=lambda p, s: tango_render.grid_text(s),
            legend="S is a sun, M a moon.",
        ),
        _linkedin(
            "wend", name="wend", title="Wend",
            scan=wend_ocr.scan, moves=wend_moves.moves, solve=wend_solver.solve,
            solution_text=wend_render.solution_text,
            legend="Each tile shows the letter of its word, listed on top; # is no tile.",
        ),
        _linkedin(
            "zip", name="zip", title="Zip",
            scan=zip_ocr.scan, moves=zip_moves.moves, solve=zip_solver.solve,
            solution_text=zip_render.path_text,
            legend="The order in which the path visits each cell; 1 is the start.",
        ),
    )
}  # fmt: skip
