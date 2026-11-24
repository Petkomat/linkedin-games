"""uv run --extra browser python -m engines.play <game> [<game> ...] [--profile DIR] [--close-after S]
uv run --extra browser python -m engines.play all [--close-after S]
uv run --extra browser python -m engines.play --login

Opens today's game on LinkedIn in Chrome, reads the board from a screenshot,
solves it and enters the moves with the mouse. The games show their board
straight away; none of them has a start button. Several games are played one
after another in the same tab; "all" is every game. The games hub is looked
at once, first, and a game it shows as played today is skipped without
opening it.

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
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .browser import Player
from .games import GAMES, HUB_URL, Game
from .hub import not_played_today
from .report import report
from .result import looks_blank
from .timing import Pauses, Tempo

PROFILE = Path.home() / ".linkedin-games" / "chrome-profile"
PLAYS = Path("plays")  # final screenshots, one folder per game
LOGIN_URL = "https://www.linkedin.com/login"
LOGIN_PAGES = ("/login", "/authwall", "/checkpoint", "/uas/", "/signup")
SESSION_COOKIE = "li_at"  # LinkedIn's login cookie


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    if args.login:
        return _log_in_by_hand(args.profile)
    save_as = (lambda game, started: args.output) if args.output else screenshot_path

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            args.profile, channel="chrome", headless=False, no_viewport=True, chromium_sandbox=True
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        player = Player(page, tempo=Tempo(Pauses(args.pause, args.shortest_pause, args.pause_tail)))
        code = run(player, args.games, args.wait, args.close_after, save_as=save_as)
        browser.close()
    return code


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """The command line, checked; `games` is the games to play, in the order
    named, each once ("all" is every game)."""
    parser = argparse.ArgumentParser(
        prog="python -m engines.play", description="Play today's LinkedIn games in Chrome."
    )
    parser.add_argument(
        "games", nargs="*", metavar="game",
        help=f"{', '.join(sorted(GAMES))}, or all; several are played one after another"
    )
    parser.add_argument(
        "--login", action="store_true", help="log in in an ordinary Chrome window, then exit"
    )
    parser.add_argument("--profile", type=Path, default=PROFILE, help=f"default: {PROFILE}")
    parser.add_argument("--pause", type=float, default=2.0, help="average seconds before a move (default 2)")
    parser.add_argument("--pause-tail", type=float, default=0.9, help="how often moves take much longer (log-normal shape, default 0.9)")
    parser.add_argument("--shortest-pause", type=float, default=1.5, help="never shorter than this (default 1.5)")
    parser.add_argument("--wait", type=float, default=60, help="seconds to wait for the board")
    parser.add_argument(
        "--close-after", type=float, metavar="S",
        help="close the browser S seconds after the end (default: wait until you close it);"
        " with several games, each finished game also stays S seconds before the next opens"
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="final screenshot of one game, with the solution next to it as .md;"
        " default plays/<game>/<date>_<time>.png"
    )
    args = parser.parse_args(argv)
    if args.login:
        return args
    if not args.games:
        parser.error("name a game, or use --login")
    unknown = [name for name in args.games if name not in GAMES and name != "all"]
    if unknown:
        parser.error(f"no game called {', '.join(unknown)}; choose from {', '.join(sorted(GAMES))}, or all")
    if args.shortest_pause > args.pause:
        parser.error("--shortest-pause can't be longer than --pause")
    if args.close_after is not None and args.close_after < 0:
        parser.error("--close-after can't be negative")
    names = list(GAMES) if "all" in args.games else dict.fromkeys(args.games)
    args.games = [GAMES[name] for name in names]
    if args.output and len(args.games) > 1:
        parser.error("-o saves one game's screenshot; name one game")
    return args


def screenshot_path(game: Game, started: datetime) -> Path:
    """plays/<game>/<date>_<time>.png. Names sort by time, and use no ':', which
    Windows doesn't allow in file names."""
    return PLAYS / game.name / f"{started:%Y-%m-%d_%H-%M-%S}.png"


def run(
    player: Player,
    games: Sequence[Game],
    board_wait: float,
    close_after: float | None = None,
    hub: str = HUB_URL,
    save_as: Callable[[Game, datetime], Path] = screenshot_path,
) -> int:
    """The signed-in play of `games`, one after another on the player's page,
    as the command line runs it; returns its exit code.

    After making sure the user is logged in, it looks at the games hub once,
    in a tab of its own (see hub.not_played_today). A game the hub shows as
    played today is skipped at once: its page isn't opened and no move is
    made. The others are opened and played in order (see `play`), each saved
    as save_as(game, the time it was opened) says. Between two games the
    finished one stays on screen for `close_after` s (none without it); the
    last one is left open as `leave_open` says. If every game is skipped,
    the page isn't left open. Exit code 0 if every game was played or
    skipped, 1 if any found no board it could read and solve."""
    page = player.page
    _log_in(page)
    to_play = not_played_today(page.context, games, hub)
    for game in games:
        if game not in to_play:
            print(f"{game.title}: already played today; skipped.")
    if not to_play:
        return 0
    page.bring_to_front()  # back from the hub's tab
    code = 0
    for number, game in enumerate(to_play):
        if number and close_after:
            page.wait_for_timeout(close_after * 1000)  # the finished game stays on screen
        started = datetime.now()
        _open(page, game)
        output = save_as(game, started)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not play(player, game, output, board_wait, started):
            code = 1
    leave_open(page, close_after)
    return code


def play(player: Player, game: Game, output: Path, board_wait: float, started: datetime) -> bool:
    """Wait for the board on the player's page, solve it and play it. Saves the
    solution next to `output` as .md as soon as it's solved, and the final
    screen (see Player.final_screen) as `output`. False if no board read and
    solved within `board_wait` s; `output` then shows what was there."""
    board = player.wait_for_board(game, board_wait)
    if board is None:
        player.screenshot().save(output)
        print(f"No solvable board on screen after {board_wait:.0f} s; see {output}")
        return False
    seen, actions = board
    solution = output.with_suffix(".md")
    solution.write_text(report(game, seen.puzzle, started), encoding="utf-8")
    print(f"Solved; the solution is in {solution}. Playing {len(actions)} moves...")
    player.perform(actions, seen.grid)
    final = player.final_screen(game)
    final.save(output)
    if looks_blank(final):
        print(f"The page still looked blank {player.result_wait.limit:.0f} s after the last move.")
    print(f"Done; the screen is in {output}")
    return True


def leave_open(page: Page, close_after: float | None = None) -> None:
    """Keep the page open until the user closes its window (or presses Ctrl+C).
    With close_after, close it after that many seconds instead, so games can be
    played one after another without anyone at the keyboard."""
    if page.is_closed():
        return
    if close_after is None:
        print("Close the browser window when you're done looking.")
    try:
        # timeout=0 waits for ever, so a zero close_after becomes 1 ms
        page.wait_for_event("close", timeout=0 if close_after is None else max(close_after * 1000, 1))
    except PlaywrightTimeoutError:
        page.close()
    except KeyboardInterrupt:
        pass


def _log_in(page: Page) -> None:
    """Make sure the user is logged in.

    LinkedIn lets guests play, so without the login check a fresh profile
    would play today's puzzle as a guest instead of on the user's account.
    """
    if not _logged_in(page):
        page.goto(LOGIN_URL)
        _wait_for_login(page)


def _open(page: Page, game: Game) -> None:
    """Go to the game, logging in again if the login has expired."""
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
