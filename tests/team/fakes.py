"""In-memory stand-ins for GitHub and for the agent starter, so the
orchestrator's tests run without the network or Claude."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from team.model import STAGE, Comment, Issue, Job, Outcome, PullRequest

T0 = datetime(2026, 11, 17, 9, 0)


class FakeGitHub:
    def __init__(self, owner: str = "owner", bot: str = "team-bot") -> None:
        self.owner, self.bot = owner, bot
        self.issues: dict[int, Issue] = {}
        self.closed: dict[int, str] = {}  # number -> "completed" or "not planned"
        self.comments: dict[int, list[Comment]] = {}
        self.prs: dict[str, PullRequest] = {}  # by branch
        self.pr_bodies: dict[int, str] = {}
        self.reviews: dict[int, list[Comment]] = {}  # by PR number
        self.review_requests: list[tuple[int, str]] = []
        self.merged: list[int] = []
        self.merge_error: Exception | None = None
        self.now = T0

    # The interface the orchestrator uses.

    def open_issues(self) -> list[Issue]:
        return [issue for number, issue in sorted(self.issues.items()) if number not in self.closed]

    def comments_on(self, number: int) -> list[Comment]:
        return list(self.comments.get(number, []))

    def comment(self, number: int, body: str) -> None:
        self.add_comment(number, self.bot, body)

    def add_labels(self, number: int, labels: set[str]) -> None:
        issue = self.issues[number]
        self.issues[number] = replace(issue, labels=issue.labels | labels, updated=self.now)

    def remove_labels(self, number: int, labels: set[str]) -> None:
        issue = self.issues[number]
        self.issues[number] = replace(issue, labels=issue.labels - labels, updated=self.now)

    def close(self, number: int, not_planned: bool = False) -> None:
        self.closed[number] = "not planned" if not_planned else "completed"

    def pull_request(self, branch: str) -> PullRequest | None:
        return self.prs.get(branch)

    def open_pull_request(self, branch: str, title: str, body: str) -> PullRequest:
        number = 100 + len(self.prs)
        pr = PullRequest(number, branch, f"https://github.test/pull/{number}")
        self.prs[branch] = pr
        self.pr_bodies[number] = body
        return pr

    def reviews_on(self, pr: int) -> list[Comment]:
        return list(self.reviews.get(pr, []))

    def review(self, pr: int, body: str) -> None:
        self.reviews.setdefault(pr, []).append(Comment(self.bot, body, self.now))

    def request_review(self, pr: int, user: str) -> None:
        self.review_requests.append((pr, user))

    def merge(self, pr: int) -> None:
        if self.merge_error:
            raise self.merge_error
        self.merged.append(pr)

    # The interface the Scout and the Watcher use (as the daily workflow).

    def create_issue(self, title: str, body: str, labels: set[str]) -> int:
        return self.open_issue(title, author="github-actions[bot]", labels=tuple(labels), body=body)

    def all_issues(self, label: str) -> list[Issue]:
        return [issue for _, issue in sorted(self.issues.items()) if label in issue.labels]

    # Helpers for the tests.

    def open_issue(self, title: str, author: str | None = None, labels: tuple[str, ...] = (), body: str = "", age: timedelta = timedelta()) -> int:
        number = len(self.issues) + 1
        when = self.now - age
        self.issues[number] = Issue(number, title, body, author or self.owner, frozenset(labels), when, when)
        return number

    def add_comment(self, number: int, author: str, body: str) -> None:
        self.comments.setdefault(number, []).append(Comment(author, body, self.now))

    def stage(self, number: int) -> str | None:
        return self.issues[number].stage

    def labels(self, number: int) -> set[str]:
        return set(self.issues[number].labels)

    def set_stage(self, number: int, stage: str) -> None:
        old = {label for label in self.issues[number].labels if label.startswith(STAGE)}
        self.remove_labels(number, old)
        self.add_labels(number, {STAGE + stage})

    def owner_reviews(self, branch: str, state: str, body: str = "") -> None:
        self.prs[branch] = replace(self.prs[branch], owner_review=state, owner_review_body=body, owner_review_at=self.now)


class FakeAgents:
    """Starts nothing; the test says how each run ends."""

    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.outcomes: dict[str, Outcome] = {}
        self.stopped: list[str] = []
        self.cleaned: list[int] = []
        self.done: set[str] = set()

    def start(self, job: Job) -> str:
        agent = f"{job.role}-{job.issue}-{len(self.jobs) + 1}"
        self.jobs[agent] = job
        return agent

    def poll(self, agent: str) -> Outcome | None:
        return self.outcomes.pop(agent, None)

    def stop(self, agent: str) -> None:
        self.stopped.append(agent)

    def clean_up(self, issue: int) -> None:
        self.cleaned.append(issue)

    # Helpers for the tests.

    def running(self) -> list[tuple[str, int]]:
        over = self.done | set(self.stopped)
        return [(job.role, job.issue) for agent, job in self.jobs.items() if agent not in over]

    def finish(self, role: str, issue: int, outcome: Outcome) -> Job:
        """End the latest run of `role` on `issue` with `outcome`."""
        agent = next(a for a, job in reversed(self.jobs.items()) if job.role == role and job.issue == issue)
        self.outcomes[agent] = outcome
        self.done.add(agent)
        return self.jobs[agent]

    def last_job(self, role: str, issue: int) -> Job:
        return next(job for job in reversed(self.jobs.values()) if job.role == role and job.issue == issue)
