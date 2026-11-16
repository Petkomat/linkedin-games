"""uv run --extra browser python -m team.daily --out DIR

The daily guest run, in GitHub Actions: the Scout looks for new games and the
Watcher checks every built game, then both file their issues. One fresh
headless Chrome, never logged in; each page is opened once, nothing is
retried, and a blocked hub stops the run.

Needs GH_TOKEN (the workflow's token) and GITHUB_REPOSITORY; GITHUB_RUN_ID
and GITHUB_SERVER_URL make the issues link to the run.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from engines.play.check import START_WAIT, VIEWPORT, check_all, click_start_screens
from engines.play.games import GAMES

from .github import GhGitHub, gh
from .scout import HUB, HubGame, scout
from .watcher import incident, watch

SETTLE = 5.0  # s for a new game's board to show after its start screens
RULES_WAIT = 15.0  # s to look for the ? button
RULES = ("[aria-label='Tutorial']", "button:has-text('How to play')")  # LinkedIn's "?" button
DIALOGS = ("[role=dialog]", "dialog", ".artdeco-modal")
SCREEN_READER = {"Dialog content start.", "Dialog content end."}  # lines LinkedIn adds for screen readers


def built_slugs() -> set[str]:
    return {[p for p in urlparse(game.url).path.split("/") if p][1] for game in GAMES.values()}


def describe(browser: Browser, out: Path) -> Callable[[HubGame], str]:
    """What a guest sees of a new game: its rules (behind the ? button), and a
    screenshot of today's board saved as <out>/<slug>.png."""

    def look(game: HubGame) -> str:
        page = browser.new_page(viewport=VIEWPORT)
        try:
            page.goto(game.url)
            rules = _rules(page)
            page.keyboard.press("Escape")
            click_start_screens(page, START_WAIT)
            page.wait_for_timeout(SETTLE * 1000)
            out.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out / f"{game.slug}.png"), full_page=True)
        finally:
            page.close()
        if not rules:
            return "The Scout couldn't read the rules. Open the game as a guest and click its ? button."
        lines = [line for line in rules.splitlines() if line.strip() not in SCREEN_READER]
        quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in lines)
        return f"## How to play, as LinkedIn shows a guest\n\n{quoted}"

    return look


def _rules(page: Page, seconds: float = RULES_WAIT) -> str:
    """Click the game's ? button, in whichever frame it shows up within
    `seconds`, and read the dialog it opens."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for frame in page.frames:  # some games run in an iframe that loads late
            for selector in RULES:
                try:
                    button = frame.locator(selector).filter(visible=True)
                    if not button.count():
                        continue
                    button.first.click()
                    text = frame.locator(", ".join(DIALOGS)).filter(visible=True)
                    text.first.wait_for(timeout=5000)
                    return text.first.inner_text().strip()
                except PlaywrightError:  # frames come and go
                    continue
        page.wait_for_timeout(500)
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m team.daily", description=__doc__.splitlines()[2])
    parser.add_argument("--out", type=Path, default=Path("daily"))
    args = parser.parse_args(argv)
    repo = os.environ["GITHUB_REPOSITORY"]
    run_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', 'local')}"
    github = GhGitHub(repo, gh(dict(os.environ)))
    now = datetime.now()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        try:
            page = browser.new_page(viewport=VIEWPORT)
            response = page.goto(HUB)
            status = response.status if response else 0
            html = page.content()
            page.close()
            if status in (429, 999) or status >= 500:
                incident(github, "blocked", "LinkedIn blocked today's guest check",
                         f"The games hub answered HTTP {status}, so the daily run stopped there. Run: {run_url}.", run_url, now)  # fmt: skip
                print(f"The hub answered {status}; stopping.")
                return 0
            found = scout(github, html, built_slugs(), describe(browser, args.out / "scout"), run_url)
            print(f"Scout: {len(found)} new game(s) {found}")
            results = check_all(sorted(GAMES), args.out / "checks", browser)
        finally:
            browser.close()
    titles = {name: game.title for name, game in GAMES.items()}
    opened = watch(github, results, titles, run_url, now, ci_failed=github.main_ci_failed())
    print(f"Watcher: {len(opened)} new incident(s) {opened}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
