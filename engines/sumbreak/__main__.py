"""uv run python -m engines.sumbreak screenshot.png [-o solution.png]"""

from __future__ import annotations

import sys

from ..common import run_cli
from .ocr import scan
from .render import board_numbers, render_solution, solution_text
from .solver import solve

if __name__ == "__main__":
    sys.exit(
        run_cli(
            "sumbreak", None, scan=scan, solve=solve,
            describe_puzzle=lambda p: f"Read {p.rows}x{p.cols} tiles:\n{board_numbers(p)}",
            describe_solution=solution_text,
            render=render_solution,
        )
    )
