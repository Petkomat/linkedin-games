"""uv run python -m engines.queens screenshot.png [-o solution.png]"""

from __future__ import annotations

import sys

from ..common import run_cli
from .ocr import scan
from .render import regions_text, render_solution, solution_text
from .solver import solve

if __name__ == "__main__":
    sys.exit(
        run_cli(
            "queens", None, scan=scan, solve=solve,
            describe_puzzle=lambda p: f"Read {p.size}x{p.size} regions:\n{regions_text(p)}",
            describe_solution=solution_text,
            render=render_solution,
        )
    )
