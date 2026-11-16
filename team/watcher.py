"""The Watcher: turns problems into incidents. It watches the daily guest
check of every built game, the tests on main, and the team itself (tasks
nobody has touched for a day: the owner's machine is off, or the
orchestrator died). One problem keeps one open incident; seeing it again
adds a comment."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Protocol

from .model import DEVELOP, INCIDENT, NEEDS_HUMAN, OPS, REVIEW, TRIAGE, Issue

MARK = re.compile(r"<!-- watch (\{.*?\}) -->")
AT_WORK = {TRIAGE, DEVELOP, REVIEW, OPS}  # stages where an agent should be busy
SILENCE = timedelta(hours=24)


class GitHub(Protocol):
    def open_issues(self) -> list[Issue]: ...
    def create_issue(self, title: str, body: str, labels: set[str]) -> int: ...
    def comment(self, number: int, body: str) -> None: ...


def incident(github: GitHub, key: str, title: str, body: str, run_url: str, when: datetime | None = None) -> int | None:
    """Open an incident for `key`, or note on the open one that it happened again.
    Returns the new incident's number, or None."""
    for issue in github.open_issues():
        if INCIDENT in issue.labels and _key(issue.body) == key:
            github.comment(issue.number, f"Seen again on {(when or datetime.now()):%Y-%m-%d}: {run_url}")
            return None
    marker = json.dumps({"watch": key})
    return github.create_issue(title, f"{body}\n\n<!-- watch {marker} -->", {INCIDENT})


def _key(body: str) -> str | None:
    found = MARK.search(body)
    return json.loads(found.group(1)).get("watch") if found else None


def watch(
    github: GitHub, results: dict[str, bool], titles: dict[str, str], run_url: str, now: datetime, ci_failed: bool = False
) -> list[int]:
    """File today's incidents. `results` says, per game, whether the guest
    check read and solved today's board."""
    opened: list[int | None] = []
    run = run_url.rstrip("/").split("/")[-1]
    failed = [game for game, ok in results.items() if not ok]
    if len(results) > 1 and len(failed) == len(results):
        opened.append(incident(
            github, "blocked", "LinkedIn blocked today's guest check",
            f"No game could be read today: LinkedIn may have blocked the guest browser or changed every page. Run: {run_url}. "
            f"Screenshots: `gh run download {run} -n daily`.",
            run_url, now,
        ))  # fmt: skip
    else:
        for game in failed:
            title = titles.get(game, game)
            opened.append(incident(
                github, f"game:{game}", f"{title} no longer reads or solves today's board",
                f"The daily guest check couldn't read or solve today's {title} board. Run: {run_url}. "
                f"What it saw is checks/{game}.png in the run's `daily` artifact: `gh run download {run} -n daily`.",
                run_url, now,
            ))  # fmt: skip
    if ci_failed:
        opened.append(incident(github, "ci", "The tests fail on main", f"The latest test run on main failed. Seen by {run_url}.", run_url, now))
    silent = [
        issue for issue in github.open_issues()
        if issue.stage in AT_WORK and NEEDS_HUMAN not in issue.labels and now - issue.updated > SILENCE and _key(issue.body) != "team"
    ]  # fmt: skip
    if silent:
        listed = "\n".join(f"- #{issue.number} {issue.title} ({issue.stage}, last change {issue.updated:%Y-%m-%d %H:%M})" for issue in silent)
        opened.append(incident(
            github, "team", "The team hasn't worked on its tasks for a day",
            f"These tasks wait for an agent but nothing happened to them for {SILENCE.total_seconds() / 3600:.0f} hours. "
            f"Is the owner's machine off, or did the orchestrator stop?\n\n{listed}",
            run_url, now,
        ))  # fmt: skip
    return [number for number in opened if number is not None]
