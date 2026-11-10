"""uv run python -m engines.patches screenshot.png [-o solution.png]"""

from __future__ import annotations

import sys

from ..common import run_cli
from .model import Puzzle
from .ocr import scan
from .render import render_solution, solution_text
from .solver import solve


def describe(puzzle: Puzzle) -> str:
    lines = [f"Grid {puzzle.rows}x{puzzle.cols}, {len(puzzle.roots)} roots:"]
    for root in sorted(puzzle.roots, key=lambda r: (r.row, r.col)):
        size = "?" if root.size is None else root.size
        lines.append(f"  ({root.row}, {root.col}) {root.shape.value:<6} size {size}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(
        run_cli(
            "patches", None, scan=scan, solve=solve, describe_puzzle=describe,
            describe_solution=lambda p, s: solution_text(p.rows, p.cols, s),
            render=render_solution,
        )
    )
