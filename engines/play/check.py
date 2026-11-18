"""uv run --extra browser python -m engines.play.check [game ...] [--out DIR]

Checks that the solvers still work on LinkedIn: opens each game as a guest
(not logged in) in headless Chrome and reads and solves today's board, without
playing it. For each game it saves <out>/<game>.png (what it saw) and, if
solved, <game>.md (the solution). It exits with 1 if any game failed. The
agent team's Watcher runs it every day (team/daily.py, .github/workflows/daily.yml).
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from ..common.actions import Action
from .browser import Player
from .games import GAMES, Game
from .report import report

# Guests see a start screen before the board, and on some machines Mini Sudoku
# shows an intro before that.
START_BUTTONS = ("Start game", "Solve now")
START_WAIT = 10.0  # s to look for the first one
NEXT_SCREEN_WAIT = 3.0  # s to look for another one after a click
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

    verdicts = check_all(args.games or sorted(GAMES), args.out)
    failed = [name for name, solved in verdicts.items() if not solved]
    if failed:
        print(f"Not read or not solved: {', '.join(failed)}; see the screenshots in {args.out}")
    return 1 if failed else 0


def check_all(
    names: Iterable[str],
    out: Path,
    browser: Browser | None = None,
    urls: Mapping[str, str] | None = None,
    start_wait: float = START_WAIT,
    board_wait: float = BOARD_WAIT,
) -> dict[str, bool]:
    """Check each game as a guest: {name: read and solved}. Prints a line per
    game as it goes, and saves what each check saw in `out` (see check_game).

    Without a `browser`, it starts a fresh headless Chrome, never a logged-in
    profile. `urls` opens other pages than LinkedIn's."""
    if browser is None:
        with sync_playwright() as playwright:
            chrome = playwright.chromium.launch(channel="chrome", headless=True)
            try:
                return check_all(names, out, chrome, urls, start_wait, board_wait)
            finally:
                chrome.close()
    urls = urls or {}
    verdicts = {}
    for name in names:
        game = GAMES[name]
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(urls.get(name, game.url))
        verdicts[name] = solved = check_game(page, game, out, start_wait, board_wait)
        print(f"{name:8} {'ok' if solved else 'FAILED'}", flush=True)
        if not solved:
            print(f"         {_describe(page)}", flush=True)
        page.close()
    return verdicts


def check_game(page: Page, game: Game, folder: Path, start_wait: float = START_WAIT, board_wait: float = BOARD_WAIT) -> bool:
    """Start the game on `page` if it shows a start screen, then read and solve
    its board. Saves <folder>/<game>.png, and <game>.md if solved."""
    player = Player(page)
    board = start_and_read(page, player, game, start_wait, board_wait)
    folder.mkdir(parents=True, exist_ok=True)
    player.screenshot().save(folder / f"{game.name}.png")
    if board is None:
        return False
    seen, _ = board
    (folder / f"{game.name}.md").write_text(report(game, seen.puzzle, datetime.now()), encoding="utf-8")
    return True


def start_and_read(
    page: Page, player: Player, game: Game, start_wait: float = START_WAIT, board_wait: float = BOARD_WAIT
) -> tuple[Any, list[Action]] | None:
    """Click through the start screens on `page`, then wait for a board that
    reads and solves, as Player.wait_for_board; None after `board_wait` s.

    A slow page may show its start screen only later, so before each look at
    the board it clicks any start screen that has turned up. It doesn't wait
    for another one after that click: the next look will find it."""
    deadline = time.monotonic() + board_wait
    click_start_screens(page, start_wait)
    page.mouse.move(0, 0)  # a pointer resting over a cell highlights it

    def click_late_start_screen() -> None:
        if _click_start_button(page, 0):
            page.mouse.move(0, 0)

    return player.wait_for_board(game, max(0.0, deadline - time.monotonic()), click_late_start_screen)


def _describe(page: Page) -> str:
    """Where the page is and what can be clicked on it, for the log of a failed check."""
    texts = page.locator("button, a, [role=button], [tabindex]").filter(visible=True).all_inner_texts()
    short = sorted({" ".join(t.split()) for t in texts if 0 < len(t.strip()) <= 40})
    return f"at {page.url}; clickable: {', '.join(short[:25]) or 'nothing'}"


def click_start_screens(page: Page, seconds: float) -> None:
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
