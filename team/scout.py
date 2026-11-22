"""The Scout: finds games on LinkedIn's games hub that are neither built nor
already known (in work, or declined), and files one task for each."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urlparse

from engines.play.games import page_url

from .model import NEW_GAME, Issue
from .watcher import incident

MARK = re.compile(r"<!-- scout (\{.*?\}) -->")

# Lines of a "How to play" dialog that aren't rules: what LinkedIn adds for
# screen readers, and the dialog's buttons (matched whole, in any case).
SCREEN_READER = re.compile(r"Dialog content (start|end)\.|\d[\d,]*\+? notifications?", re.IGNORECASE)
BUTTONS = {"play", "play game", "start", "start game", "let's play", "continue", "resume", "resume game",
           "back to game", "got it", "ok", "done", "next", "back", "skip", "close", "dismiss"}  # fmt: skip
POLL = 0.5  # s between two reads of a "How to play" dialog
STILL = 3  # reads in a row with the same rules before the dialog counts as loaded


def rules_lines(dialog: str) -> list[str]:
    """The rules in the text of a game's "How to play" dialog: its heading
    (the first line) and the lines after it, without blank lines, screen-reader
    lines or button labels. Empty if nothing is left after the heading: the
    dialog hasn't loaded its rules (yet)."""
    lines = (" ".join(line.split()) for line in dialog.splitlines())
    kept = [line for line in lines if line and not SCREEN_READER.fullmatch(line) and line.lower() not in BUTTONS]
    return kept if len(kept) > 1 else []


def wait_for_rules(
    read: Callable[[], str],
    seconds: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """The text of a "How to play" dialog once it has loaded: `read()` again
    every POLL s until it has rules and they have been the same STILL reads in
    a row. LinkedIn shows the dialog's heading first and its rules a moment
    later. At the limit of `seconds`, the last text read."""
    deadline = clock() + seconds
    text = read()
    same = 1
    while not (same >= STILL and rules_lines(text)) and clock() + POLL <= deadline:
        sleep(POLL)
        latest = read()
        same = same + 1 if rules_lines(latest) == rules_lines(text) else 1
        text = latest
    return text


def how_to_play(dialog: str) -> str:
    """The rules part of a new game's task, from the text of its "How to play"
    dialog ("" if there was no dialog)."""
    lines = rules_lines(dialog)
    if not lines:
        return "The Scout couldn't read the rules. Open the game as a guest and click its ? button."
    quoted = "\n>\n".join(f"> {line}" for line in lines)
    return f"## How to play, as LinkedIn shows a guest\n\n{quoted}"


@dataclass(frozen=True)
class HubGame:
    name: str
    slug: str

    @property
    def url(self) -> str:
        return page_url(self.slug)


class GitHub(Protocol):
    def open_issues(self) -> list[Issue]: ...
    def all_issues(self, label: str) -> list[Issue]: ...
    def create_issue(self, title: str, body: str, labels: set[str]) -> int: ...
    def comment(self, number: int, body: str) -> None: ...


class _Cards(HTMLParser):
    """The hub's game cards: <a class="game-entrypoint-card" href=".../games/<slug>/">
    holding <p class="font-semibold">Name</p>."""

    def __init__(self) -> None:
        super().__init__()
        self.games: list[HubGame] = []
        self._slug: str | None = None
        self._name: list[str] | None = None
        self._alt = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        classes = (found.get("class") or "").split()
        if tag == "a" and "game-entrypoint-card" in classes:
            parts = [p for p in urlparse(found.get("href") or "").path.split("/") if p]
            self._slug = parts[1] if len(parts) >= 2 and parts[0] == "games" else None
            self._alt = ""
        elif self._slug and tag == "img" and found.get("alt"):
            self._alt = found["alt"] or ""
        elif self._slug and tag == "p" and "font-semibold" in classes:
            self._name = []

    def handle_data(self, data: str) -> None:
        if self._name is not None:
            self._name.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._name is not None and self._slug:
            self.games.append(HubGame(" ".join("".join(self._name).split()) or self._alt, self._slug))
            self._name, self._slug = None, None
        elif tag == "a" and self._slug:  # a card without a name paragraph
            self.games.append(HubGame(self._alt or self._slug, self._slug))
            self._slug = None


def hub_games(html: str) -> list[HubGame]:
    cards = _Cards()
    cards.feed(html)
    return cards.games


def new_games(hub: list[HubGame], built: set[str], known: set[str]) -> list[HubGame]:
    return [game for game in hub if game.slug not in built | known]


def known_slugs(github: GitHub) -> set[str]:
    """Games that already have a task, open or closed (declined ones included)."""
    return {json.loads(m.group(1))["slug"] for issue in github.all_issues(NEW_GAME) for m in [MARK.search(issue.body)] if m}


def scout(github: GitHub, html: str, built: set[str], describe: Callable[[HubGame], str], run_url: str) -> list[int]:
    """File a task for each new game on the hub; returns their numbers.
    `describe` tells what a guest sees of the game (its rules)."""
    games = hub_games(html)
    if not games:
        incident(github, "hub", "The Scout can't read LinkedIn's games hub",
                 f"The games hub showed no game cards: LinkedIn changed the page or blocked the guest. Run: {run_url}.", run_url)  # fmt: skip
        return []
    run = run_url.rstrip("/").split("/")[-1]
    opened = []
    for game in new_games(games, built, known_slugs(github)):
        body = "\n\n".join([
            f"LinkedIn has a game the team hasn't built: **{game.name}**, at {game.url}.",
            describe(game),
            f"The Scout found it in {run_url}. A guest screenshot of today's board is scout/{game.slug}.png "
            f"in that run's `daily` artifact: `gh run download {run} -n daily`.",
            f"<!-- scout {json.dumps({'slug': game.slug})} -->",
        ])  # fmt: skip
        opened.append(github.create_issue(f"New game: {game.name}", body, {NEW_GAME}))
    return opened
