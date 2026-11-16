"""The Scout: finds games on LinkedIn's games hub that are neither built nor
already known (in work, or declined), and files one task for each."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urlparse

from .model import NEW_GAME, Issue
from .watcher import incident

HUB = "https://www.linkedin.com/games/"
MARK = re.compile(r"<!-- scout (\{.*?\}) -->")


@dataclass(frozen=True)
class HubGame:
    name: str
    slug: str

    @property
    def url(self) -> str:
        return f"{HUB}{self.slug}/"


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
