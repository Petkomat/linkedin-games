"""The command line every engine shares: screenshot in, solution PNG out.

    uv run python -m engines.<game> screenshot.png [-o solution.png]
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image


def run_cli(
    game: str,
    argv: list[str] | None,
    *,
    scan: Callable[[Path], Any],
    solve: Callable[[Any], Any | None],
    describe_puzzle: Callable[[Any], str],
    describe_solution: Callable[[Any, Any], str],
    render: Callable[[Path, Any, Any], Image.Image],
) -> int:
    """Read, solve and draw one screenshot; returns the process exit code.

    `scan(path)` returns something with a `.puzzle`. That object is handed to
    `render` so it can draw on the screenshot where the grid was found.
    """
    parser = argparse.ArgumentParser(
        prog=f"python -m engines.{game}", description=f"Solve a {game} screenshot."
    )
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="default: <screenshot>_solved.png")
    args = parser.parse_args(argv)
    output = args.output or args.screenshot.with_name(f"{args.screenshot.stem}_solved.png")

    seen = scan(args.screenshot)
    print(describe_puzzle(seen.puzzle))

    started = time.perf_counter()
    solution = solve(seen.puzzle)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if solution is None:
        print(f"No solution ({elapsed_ms:.1f} ms) - the screenshot was probably misread.")
        return 1

    print(f"Solved in {elapsed_ms:.1f} ms:\n{describe_solution(seen.puzzle, solution)}")
    render(args.screenshot, seen, solution).save(output)
    print(f"Wrote {output}")
    return 0
