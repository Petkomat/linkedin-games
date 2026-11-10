"""uv run python -m engines.wend screenshot.png [-o solution.png]"""

from __future__ import annotations

import sys

from ..common import run_cli
from .ocr import scan
from .render import puzzle_text, render_solution, solution_text
from .solver import solve

if __name__ == "__main__":
    sys.exit(
        run_cli(
            "wend", None, scan=scan, solve=solve,
            describe_puzzle=lambda p: f"Read:\n{puzzle_text(p)}",
            describe_solution=solution_text,
            render=render_solution,
        )
    )
