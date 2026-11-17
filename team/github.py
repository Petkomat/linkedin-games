"""GitHub through the `gh` CLI, as the team bot: GH_TOKEN in the environment
decides who gh acts as. Every command names the repository and runs outside
any checkout, so gh never touches a local branch."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Callable
from datetime import datetime
from typing import Any

from .model import Comment, Issue, PullRequest

Run = Callable[..., str]  # (args, stdin=None) -> standard output


def gh(env: dict[str, str] | None = None) -> Run:
    """Run the real gh, raising with its error message when it fails."""

    def run(args: list[str], stdin: str | None = None) -> str:
        done = subprocess.run(
            ["gh", *args], input=stdin, capture_output=True, text=True, encoding="utf-8", env=env, cwd=tempfile.gettempdir()
        )
        if done.returncode:
            raise RuntimeError(f"gh {' '.join(args[:3])}: {done.stderr.strip() or done.stdout.strip()}")
        return done.stdout

    return run


def _time(text: str) -> datetime:
    """GitHub's UTC time as a local time without a zone, like datetime.now()."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)


class GhGitHub:
    def __init__(self, repo: str, run: Run, owner: str = "") -> None:
        self.repo, self.run = repo, run
        self.owner = owner or repo.split("/")[0]

    def _gh(self, *args: str, stdin: str | None = None) -> str:
        return self.run([*args, "--repo", self.repo], stdin=stdin)

    def _json(self, *args: str) -> Any:
        return json.loads(self._gh(*args) or "null")

    # Issues.

    def open_issues(self) -> list[Issue]:
        fields = "number,title,body,author,labels,assignees,createdAt,updatedAt"
        return [
            Issue(
                i["number"],
                i["title"],
                i.get("body") or "",
                i["author"]["login"],
                frozenset(label["name"] for label in i["labels"]),
                _time(i["createdAt"]),
                _time(i["updatedAt"]),
                frozenset(person["login"] for person in i.get("assignees") or ()),
            )
            for i in self._json("issue", "list", "--state", "open", "--limit", "200", "--json", fields)
        ]

    def comments_on(self, number: int) -> list[Comment]:
        comments = self._json("issue", "view", str(number), "--json", "comments")["comments"]
        return [Comment(c["author"]["login"], c["body"], _time(c["createdAt"])) for c in comments]

    def comment(self, number: int, body: str) -> None:
        self._gh("issue", "comment", str(number), "--body-file", "-", stdin=body)

    def add_labels(self, number: int, labels: set[str]) -> None:
        self._gh("issue", "edit", str(number), "--add-label", ",".join(sorted(labels)))

    def remove_labels(self, number: int, labels: set[str]) -> None:
        self._gh("issue", "edit", str(number), "--remove-label", ",".join(sorted(labels)))

    def close(self, number: int, not_planned: bool = False) -> None:
        self._gh("issue", "close", str(number), "--reason", "not planned" if not_planned else "completed")

    def assign(self, number: int, login: str) -> None:
        self._gh("issue", "edit", str(number), "--add-assignee", login)

    def create_issue(self, title: str, body: str, labels: set[str]) -> int:
        url = self._gh("issue", "create", "--title", title, "--body-file", "-", "--label", ",".join(sorted(labels)), stdin=body)
        return int(url.strip().rstrip("/").split("/")[-1])

    def all_issues(self, label: str) -> list[Issue]:
        """Open and closed issues with this label, for the Scout and the Watcher."""
        fields = "number,title,body,author,labels,createdAt,updatedAt"
        return [
            Issue(i["number"], i["title"], i.get("body") or "", i["author"]["login"], frozenset(x["name"] for x in i["labels"]), _time(i["createdAt"]), _time(i["updatedAt"]))
            for i in self._json("issue", "list", "--state", "all", "--label", label, "--limit", "500", "--json", fields)
        ]

    # Pull requests.

    def pull_request(self, branch: str) -> PullRequest | None:
        found = self._json("pr", "list", "--head", branch, "--state", "open", "--json", "number,headRefName,url,latestReviews")
        if not found:
            return None
        pr = found[0]
        mine = [r for r in pr.get("latestReviews") or [] if r["author"]["login"] == self.owner]
        review = mine[-1] if mine else None
        return PullRequest(
            pr["number"],
            pr["headRefName"],
            pr["url"],
            review["state"] if review else None,
            review.get("body", "") if review else "",
            _time(review["submittedAt"]) if review and review.get("submittedAt") else None,
        )

    def open_pull_request(self, branch: str, title: str, body: str) -> PullRequest:
        self._gh("pr", "create", "--head", branch, "--base", "main", "--title", title, "--body-file", "-", stdin=body)
        pr = self.pull_request(branch)
        if pr is None:
            raise RuntimeError(f"gh created no PR for {branch}")
        return pr

    def reviews_on(self, pr: int) -> list[Comment]:
        """What was said on a PR, its reviews and its comments, oldest first."""
        found = self._json("pr", "view", str(pr), "--json", "reviews,comments")
        said = [Comment(r["author"]["login"], r.get("body", ""), _time(r["submittedAt"])) for r in found.get("reviews") or [] if r.get("submittedAt")]
        said += [Comment(c["author"]["login"], c.get("body", ""), _time(c["createdAt"])) for c in found.get("comments") or []]
        return sorted(said, key=lambda c: c.created)

    def review(self, pr: int, body: str) -> None:
        self._gh("pr", "review", str(pr), "--comment", "--body-file", "-", stdin=body)

    def request_review(self, pr: int, user: str) -> None:
        self._gh("pr", "edit", str(pr), "--add-reviewer", user)

    def merge(self, pr: int) -> None:
        self._gh("pr", "merge", str(pr), "--squash", "--delete-branch")

    # For the Watcher.

    def main_ci_failed(self, workflow: str = "tests.yml") -> bool:
        runs = self._json("run", "list", "--workflow", workflow, "--branch", "main", "--limit", "1", "--json", "conclusion,status")
        return bool(runs) and runs[0].get("status") == "completed" and runs[0].get("conclusion") == "failure"
