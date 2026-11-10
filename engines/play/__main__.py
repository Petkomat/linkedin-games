"""uv run --extra browser python -m engines.play <game> [--profile DIR]

Opens today's game on LinkedIn in Chrome, starts it, reads the board from a
screenshot, solves it and enters the moves with the mouse. The first time,
log in in the browser window; the login is kept in the profile folder.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from .browser import Player
from .games import GAMES, Game

PROFILE = Path.home() / ".linkedin-games" / "chrome-profile"
LOGIN_PAGES = ("/login", "/authwall", "/checkpoint", "/uas/", "/signup")
START_BUTTON = re.compile(r"^\s*(start|play|resume)\b", re.IGNORECASE)
START_WAIT = 10.0  # s to look for a start button before assuming the board is showing
RETRY = 1.0  # s between two looks at the screen while waiting for the board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m engines.play", description="Play today's LinkedIn game in Chrome."
    )
    parser.add_argument("game", choices=sorted(GAMES))
    parser.add_argument("--profile", type=Path, default=PROFILE, help=f"default: {PROFILE}")
    parser.add_argument("--pause", type=float, default=0.15, help="seconds between moves")
    parser.add_argument("--wait", type=float, default=60, help="seconds to wait for the board")
    parser.add_argument("-o", "--output", type=Path, help="final screenshot; default <game>_played.png")
    args = parser.parse_args(argv)
    game = GAMES[args.game]
    output = args.output or Path(f"{game.name}_played.png")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            args.profile, channel="chrome", headless=False, no_viewport=True
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        _open(page, game)
        player = Player(page, pause=args.pause)
        board = _wait_for_board(player, game, args.wait)
        if board is None:
            player.screenshot().save(output)
            print(f"No solvable board on screen after {args.wait:.0f} s; see {output}")
            return 1
        seen, actions = board
        print(f"Playing {len(actions)} moves...")
        player.perform(actions, seen.grid)
        time.sleep(2)  # let the game show its result
        player.screenshot().save(output)
        print(f"Done; the screen is in {output}")
        browser.close()
    return 0


def _open(page: Page, game: Game) -> None:
    """Go to the game, waiting for the user to log in if LinkedIn asks, and start it."""
    page.goto(game.url)
    if _is_login(page.url):
        print("Log in in the browser window; I'll wait.")
        page.wait_for_url(lambda url: not _is_login(url), timeout=0)
        page.goto(game.url)
    if not _press_start(page):
        print("No start button found; press it yourself if the board isn't showing.")


def _is_login(url: str) -> bool:
    return any(marker in url for marker in LOGIN_PAGES)


def _press_start(page: Page) -> bool:
    """Click the game's start button, which may sit in an iframe."""
    deadline = time.monotonic() + START_WAIT
    while time.monotonic() < deadline:
        for frame in page.frames:
            button = frame.get_by_role("button", name=START_BUTTON).first
            if button.count() and button.is_visible():
                button.click()
                return True
        time.sleep(RETRY / 2)
    return False


def _wait_for_board(player: Player, game: Game, seconds: float):
    """The board and its moves, once the same board has been read twice in a row
    (so a board that is still fading in isn't played); None after `seconds`."""
    deadline = time.monotonic() + seconds
    previous = None
    while time.monotonic() < deadline:
        board = player.read(game)
        if board is not None and previous is not None and board[0].puzzle == previous[0].puzzle:
            return board
        previous = board
        time.sleep(RETRY)
    return None


if __name__ == "__main__":
    sys.exit(main())
