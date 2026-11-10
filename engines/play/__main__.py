"""uv run --extra browser python -m engines.play <game> [--profile DIR]
uv run --extra browser python -m engines.play --login

Opens today's game on LinkedIn in Chrome, reads the board from a screenshot,
solves it and enters the moves with the mouse. The games show their board
straight away; none of them has a start button.

The login is kept in the profile folder. Google refuses to sign in inside a
browser that is being remote-controlled, so to sign in with Google, run
--login first: it opens an ordinary Chrome window on the same profile.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from .browser import Player
from .games import GAMES, Game
from .report import report
from .timing import Pauses, Tempo

PROFILE = Path.home() / ".linkedin-games" / "chrome-profile"
PLAYS = Path("plays")  # final screenshots, one folder per game
LOGIN_URL = "https://www.linkedin.com/login"
LOGIN_PAGES = ("/login", "/authwall", "/checkpoint", "/uas/", "/signup")
SESSION_COOKIE = "li_at"  # LinkedIn's login cookie
RESULT_WAIT = 2.0  # s after the last move before the final screenshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m engines.play", description="Play today's LinkedIn game in Chrome."
    )
    parser.add_argument("game", nargs="?", choices=sorted(GAMES))
    parser.add_argument(
        "--login", action="store_true", help="log in in an ordinary Chrome window, then exit"
    )
    parser.add_argument("--profile", type=Path, default=PROFILE, help=f"default: {PROFILE}")
    parser.add_argument("--pause", type=float, default=2.0, help="average seconds before a move (default 2)")
    parser.add_argument("--pause-tail", type=float, default=0.9, help="how often moves take much longer (log-normal shape, default 0.9)")
    parser.add_argument("--shortest-pause", type=float, default=1.5, help="never shorter than this (default 1.5)")
    parser.add_argument("--wait", type=float, default=60, help="seconds to wait for the board")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="final screenshot, with the solution next to it as .md; default plays/<game>/<date>_<time>.png"
    )
    args = parser.parse_args(argv)
    if args.login:
        return _log_in_by_hand(args.profile)
    if args.game is None:
        parser.error("name a game, or use --login")
    if args.shortest_pause > args.pause:
        parser.error("--shortest-pause can't be longer than --pause")
    game = GAMES[args.game]
    started = datetime.now()
    output = args.output or screenshot_path(game.name, started)
    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            args.profile, channel="chrome", headless=False, no_viewport=True, chromium_sandbox=True
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        _open(page, game)
        player = Player(page, tempo=Tempo(Pauses(args.pause, args.shortest_pause, args.pause_tail)))
        board = player.wait_for_board(game, args.wait)
        if board is None:
            player.screenshot().save(output)
            print(f"No solvable board on screen after {args.wait:.0f} s; see {output}")
            _leave_open(page)
            return 1
        seen, actions = board
        solution = output.with_suffix(".md")
        solution.write_text(report(game, seen.puzzle, started), encoding="utf-8")
        print(f"Solved; the solution is in {solution}. Playing {len(actions)} moves...")
        player.perform(actions, seen.grid)
        time.sleep(RESULT_WAIT)  # let the game take the last move and show its result
        player.screenshot().save(output)
        print(f"Done; the screen is in {output}")
        _leave_open(page)
    return 0


def screenshot_path(game: str, started: datetime) -> Path:
    """plays/<game>/<date>_<time>.png. Names sort by time, and use no ':', which
    Windows doesn't allow in file names."""
    return PLAYS / game / f"{started:%Y-%m-%d_%H-%M-%S}.png"


def _leave_open(page: Page) -> None:
    """Keep the browser open until the user closes its window (or presses Ctrl+C)."""
    print("Close the browser window when you're done looking.")
    try:
        page.wait_for_event("close", timeout=0)
    except KeyboardInterrupt:
        pass


def _open(page: Page, game: Game) -> None:
    """Make sure the user is logged in, then go to the game.

    LinkedIn lets guests play, so without the login check a fresh profile
    would play today's puzzle as a guest instead of on the user's account.
    """
    if not _logged_in(page):
        page.goto(LOGIN_URL)
        _wait_for_login(page)
    page.goto(game.url)
    if _is_login(page.url):  # the login expired
        _wait_for_login(page)
        page.goto(game.url)


def _log_in_by_hand(profile: Path) -> int:
    """Open an ordinary Chrome window (not remote-controlled) on the profile."""
    chrome = _find_chrome()
    if chrome is None:
        print("Chrome not found; install it, or log in with email and password instead.")
        return 1
    print("Log in to LinkedIn in the Chrome window that opens, then close the window.")
    subprocess.run([chrome, f"--user-data-dir={profile}", "--no-first-run", LOGIN_URL], check=False)
    return 0


def _find_chrome() -> str | None:
    installed = (
        Path(os.environ.get(folder, "")) / "Google" / "Chrome" / "Application" / "chrome.exe"
        for folder in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")
    )
    found = next((str(path) for path in installed if path.is_file()), None)
    return found or shutil.which("google-chrome") or shutil.which("chrome")


def _logged_in(page: Page) -> bool:
    return any(c["name"] == SESSION_COOKIE for c in page.context.cookies("https://www.linkedin.com"))


def _wait_for_login(page: Page) -> None:
    if _is_login(page.url):
        print(
            "Log in in the browser window; I'll wait. Google sign-in doesn't work in this"
            " window: use email and password, or stop (Ctrl+C) and run with --login first."
        )
        page.wait_for_url(lambda url: not _is_login(url), timeout=0)


def _is_login(url: str) -> bool:
    return any(marker in url for marker in LOGIN_PAGES)


if __name__ == "__main__":
    sys.exit(main())
