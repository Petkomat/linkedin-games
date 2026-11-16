"""uv run --extra browser python -m engines.play.guest shot <slug-or-url> --out FILE.png
uv run --extra browser python -m engines.play.guest play <game> --out DIR [--url URL]

LinkedIn's games as a guest, for the agent team: never logged in, always in a
fresh headless Chrome, so the user's account and daily puzzles are never
touched.

shot  saves what a game's page shows after its start screens, for any game,
      including one that isn't built yet (a slug like "sumbreak", or a URL).
play  reads, solves and plays a built game with the usual human-like player,
      and saves DIR/<game>.png (the final board), <game>.md (the solution)
      and <game>.webm (a video of the play). Exits with 1 if it couldn't read
      or solve the board.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright

from .browser import Player
from .check import BOARD_WAIT, START_WAIT, VIEWPORT, click_start_screens, start_and_read
from .games import GAMES, Game
from .report import report

GAMES_URL = "https://www.linkedin.com/games/{}/"
SETTLE = 5.0  # s for the board to show after the start screens, before a shot
RESULT_WAIT = 2.0  # s after the last move before the final screenshot


def game_url(slug_or_url: str) -> str:
    """A LinkedIn game's page from its slug; a URL as it is."""
    return slug_or_url if "://" in slug_or_url else GAMES_URL.format(slug_or_url)


@contextmanager
def recorded_page(browser: Browser, video: Path, **context: Any) -> Iterator[Page]:
    """A page in a new browser context (no cookies, no login), filmed. The video
    is saved to `video` when the block ends. `context` adds new_context options."""
    with tempfile.TemporaryDirectory() as frames:
        browser_context = browser.new_context(**{"viewport": VIEWPORT, **context, "record_video_dir": frames})
        page = browser_context.new_page()
        try:
            yield page
        finally:
            browser_context.close()  # a video is complete only once its page is closed
            if page.video:
                video.parent.mkdir(parents=True, exist_ok=True)
                page.video.save_as(video)


def shot(page: Page, out: Path, start_wait: float = START_WAIT, settle: float = SETTLE) -> None:
    """Click through the start screens on `page`, give the board `settle` s to
    show, and save the whole page to `out`."""
    click_start_screens(page, start_wait)
    page.mouse.move(0, 0)  # a pointer resting over a cell highlights it
    time.sleep(settle)
    out.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=out, full_page=True)


def play(
    page: Page,
    game: Game,
    out: Path,
    player: Player | None = None,
    start_wait: float = START_WAIT,
    board_wait: float = BOARD_WAIT,
) -> bool:
    """Start `game` on `page`, read and solve it, and play it like a person.
    Saves out/<game>.md as soon as it's solved and out/<game>.png at the end.
    False if no board read and solved; the png then shows what was there."""
    player = player or Player(page)
    board = start_and_read(page, player, game, start_wait, board_wait)
    out.mkdir(parents=True, exist_ok=True)
    if board is None:
        player.screenshot().save(out / f"{game.name}.png")
        return False
    seen, actions = board
    (out / f"{game.name}.md").write_text(report(game, seen.puzzle, datetime.now()), encoding="utf-8")
    player.perform(actions, seen.grid)
    time.sleep(RESULT_WAIT)  # let the game take the last move and show its result
    player.screenshot().save(out / f"{game.name}.png")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m engines.play.guest", description="LinkedIn's games as a guest.")
    commands = parser.add_subparsers(dest="command", required=True)
    shoot = commands.add_parser("shot", help="save what a game's page shows a guest")
    shoot.add_argument("game", help='a slug, like "sumbreak", or a URL')
    shoot.add_argument("--out", type=Path, required=True, help="the png to save")
    player = commands.add_parser("play", help="play a built game as a guest, on video")
    player.add_argument("game", choices=sorted(GAMES))
    player.add_argument("--out", type=Path, required=True, help="folder for <game>.png, .md and .webm")
    player.add_argument("--url", help="another page than the game's own, for testing")
    args = parser.parse_args(argv)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)  # never a logged-in profile
        try:
            if args.command == "shot":
                page = browser.new_page(viewport=VIEWPORT)
                page.goto(game_url(args.game))
                shot(page, args.out)
                print(f"Saved {args.out}")
                return 0
            game = GAMES[args.game]
            with recorded_page(browser, args.out / f"{game.name}.webm") as page:
                page.goto(args.url or game.url)
                played = play(page, game, args.out)
        finally:
            browser.close()
    print(f"{'Played' if played else 'No solvable board'}; see {args.out}")
    return 0 if played else 1


if __name__ == "__main__":
    sys.exit(main())
