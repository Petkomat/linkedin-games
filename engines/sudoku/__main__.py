"""uv run python -m engines.sudoku screenshot.png [-o solution.png]"""

from __future__ import annotations

import sys

from ..common import run_cli
from .ocr import scan
from .render import grid_text, render_solution
from .solver import solve

if __name__ == "__main__":
    sys.exit(
        run_cli(
            "sudoku", None, scan=scan, solve=solve,
            describe_puzzle=lambda p: f"Read {p.size}x{p.size}:\n{grid_text(p.grid, p.box)}",
            describe_solution=lambda p, s: grid_text(s, p.box),
            render=render_solution,
        )
    )
