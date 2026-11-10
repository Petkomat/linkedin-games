"""uv run --extra browser python -m engines.play.check [game ...] [--out DIR]

Checks that the solvers still work on LinkedIn: opens each game as a guest
(not logged in) in headless Chrome and reads and solves today's board, without
playing it. For each game it saves <out>/<game>.png (what it saw) and, if
solved, <game>.md (the solution). It exits with 1 if any game failed. GitHub
Actions runs it twice a week (.github/workflows/live-check.yml).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

from .browser import Player
from .games import GAMES, Game
from .report import report

# Guests see a start screen before the board, and on some machines Mini Sudoku
# shows an intro before that.
START_BUTTONS = ("Start game", "Solve now")
START_WAIT = 10.0  # s to look for the first one
NEXT_SCREEN_WAIT = 3.0  # s to look for another one after a click
LOOK_AGAIN = 3.0  # s of reading the board before looking for a late start screen again
MAX_SCREENS = 3
BOARD_WAIT = 30.0  # s to wait for a board that reads and solves
VIEWPORT = {"width": 1280, "height": 1600}  # tall enough for Wend's word lengths under the board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m engines.play.check", description=__doc__.splitlines()[2])
    parser.add_argument("games", nargs="*", help=f"any of {', '.join(sorted(GAMES))}; default: all")
    parser.add_argument("--out", type=Path, default=Path("checks"), help="default: checks/")
    args = parser.parse_args(argv)
    unknown = sorted(set(args.games) - set(GAMES))
    if unknown:
        parser.error(f"no such game: {', '.join(unknown)}")

    failed = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        for name in args.games or sorted(GAMES):
            game = GAMES[name]
            page = browser.new_page(viewport=VIEWPORT)
            page.goto(game.url)
            solved = check_game(page, game, args.out)
            print(f"{name:8} {'ok' if solved else 'FAILED'}", flush=True)
            if not solved:
                failed.append(name)
                print(f"         {_describe(page)}", flush=True)
            page.close()
        browser.close()
    if failed:
        print(f"Not read or not solved: {', '.join(failed)}; see the screenshots in {args.out}")
    return 1 if failed else 0


def check_game(page: Page, game: Game, folder: Path, start_wait: float = START_WAIT, board_wait: float = BOARD_WAIT) -> bool:
    """Start the game on `page` if it shows a start screen, then read and solve
    its board. Saves <folder>/<game>.png, and <game>.md if solved.

    A slow page may show its start screen only later, so while waiting for
    the board it keeps clicking any start screen that turns up."""
    player = Player(page)
    deadline = time.monotonic() + board_wait
    _start(page, start_wait)
    while True:
        page.mouse.move(0, 0)  # a pointer resting over a cell highlights it
        board = player.wait_for_board(game, min(LOOK_AGAIN, max(0.0, deadline - time.monotonic())))
        if board is not None or time.monotonic() >= deadline:
            break
        _start(page, 0)
    folder.mkdir(parents=True, exist_ok=True)
    player.screenshot().save(folder / f"{game.name}.png")
    if board is None:
        return False
    seen, _ = board
    (folder / f"{game.name}.md").write_text(report(game, seen.puzzle, datetime.now()), encoding="utf-8")
    return True


def _describe(page: Page) -> str:
    """Where the page is and what can be clicked on it, for the log of a failed check."""
    texts = page.locator("button, a, [role=button], [tabindex]").filter(visible=True).all_inner_texts()
    short = sorted({" ".join(t.split()) for t in texts if 0 < len(t.strip()) <= 40})
    return f"at {page.url}; clickable: {', '.join(short[:25]) or 'nothing'}"


def _start(page: Page, seconds: float) -> None:
    """Click through the start screens: whichever START_BUTTONS shows up, the
    first within `seconds` and each next one within NEXT_SCREEN_WAIT."""
    for _ in range(MAX_SCREENS):
        if not _click_start_button(page, seconds):
            return
        seconds = NEXT_SCREEN_WAIT


def _click_start_button(page: Page, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        for frame in page.frames:  # Mini Sudoku runs in an iframe
            for label in START_BUTTONS:
                button = frame.get_by_text(label, exact=True).filter(visible=True)  # pages hide spare copies
                try:
                    if not button.count():
                        continue
                    button.first.click()
                    button.first.wait_for(state="detached", timeout=NEXT_SCREEN_WAIT * 1000)
                except PlaywrightError:  # tracking and captcha iframes come and go
                    continue
                return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.5)


if __name__ == "__main__":
    sys.exit(main())
