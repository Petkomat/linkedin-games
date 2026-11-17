"""The real GitHub adapter: what it reads out of `gh`'s JSON, and which `gh`
commands it sends. `gh` itself is replaced by recorded answers."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from team.github import GhGitHub

REPO = "owner/linkedin-games"


class Gh:
    """Answers `gh` commands from a table and remembers what was asked."""

    def __init__(self, answers: dict[str, object] | None = None) -> None:
        self.answers = answers or {}
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, args: list[str], stdin: str | None = None) -> str:
        self.calls.append((args, stdin))
        for prefix, answer in self.answers.items():
            if " ".join(args).startswith(prefix):
                return answer if isinstance(answer, str) else json.dumps(answer)
        return ""


def local(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)


def issue(number: int, login: str, labels: list[str], assignees: tuple[str, ...] = ()) -> dict[str, object]:
    return {
        "number": number,
        "title": f"Task {number}",
        "body": "Details.",
        "author": {"login": login, "is_bot": login.startswith("app/")},
        "labels": [{"name": name, "color": "ededed"} for name in labels],
        "assignees": [{"login": name, "name": ""} for name in assignees],
        "createdAt": "2026-11-17T08:00:00Z",
        "updatedAt": "2026-11-17T09:30:00Z",
    }


def test_open_issues_come_with_their_author_labels_assignees_and_times():
    gh = Gh({"issue list": [issue(7, "app/github-actions", ["kind:new-game", "stage:triage"], assignees=("team-bot",))]})

    [task] = GhGitHub(REPO, gh).open_issues()

    assert (task.number, task.author, task.stage) == (7, "app/github-actions", "triage")
    assert task.labels == {"kind:new-game", "stage:triage"}
    assert task.assignees == {"team-bot"}
    assert task.created == local("2026-11-17T08:00:00Z")
    assert task.updated == local("2026-11-17T09:30:00Z")
    assert gh.calls[0][0][-2:] == ["--repo", REPO]


def test_comments_are_read_with_their_authors():
    gh = Gh({"issue view 7": {"comments": [{"author": {"login": "owner"}, "body": "It's the 10x10 one.", "createdAt": "2026-11-17T10:00:00Z"}]}})

    [comment] = GhGitHub(REPO, gh).comments_on(7)

    assert (comment.author, comment.body, comment.created) == ("owner", "It's the 10x10 one.", local("2026-11-17T10:00:00Z"))


def test_a_pr_is_found_by_its_branch_with_the_owner_s_latest_review():
    pr = {
        "number": 12,
        "headRefName": "team/7-new-game-sumbreak",
        "url": "https://github.com/owner/linkedin-games/pull/12",
        "latestReviews": [
            {"author": {"login": "team-bot"}, "state": "COMMENTED", "body": "Review 1 of 3", "submittedAt": "2026-11-17T11:00:00Z"},
            {"author": {"login": "owner"}, "state": "APPROVED", "body": "Ship it.", "submittedAt": "2026-11-17T12:00:00Z"},
        ],
    }
    gh = Gh({"pr list": [pr]})

    found = GhGitHub(REPO, gh, owner="owner").pull_request("team/7-new-game-sumbreak")

    assert found is not None
    assert (found.number, found.owner_review, found.owner_review_body) == (12, "APPROVED", "Ship it.")
    assert found.owner_review_at == local("2026-11-17T12:00:00Z")
    args = gh.calls[0][0]
    assert args[args.index("--head") + 1] == "team/7-new-game-sumbreak"


def test_no_pr_for_a_branch_is_none():
    assert GhGitHub(REPO, Gh({"pr list": []})).pull_request("team/7-x") is None


def test_writing_sends_these_gh_commands():
    gh = Gh({"pr list": [{"number": 12, "headRefName": "team/7-x", "url": "u", "latestReviews": []}]})
    github = GhGitHub(REPO, gh)

    github.comment(7, "Hello")
    github.add_labels(7, {"stage:develop"})
    github.remove_labels(7, {"stage:triage"})
    github.close(7, not_planned=True)
    github.assign(7, "team-bot")
    github.review(12, "Review 1 of 3")
    github.merge(12)

    sent = [(" ".join(args[: args.index("--repo")]), stdin) for args, stdin in gh.calls if args[0] != "pr" or args[1] != "list"]
    assert sent[:6] == [
        ("issue comment 7 --body-file -", "Hello"),
        ("issue edit 7 --add-label stage:develop", None),
        ("issue edit 7 --remove-label stage:triage", None),
        ("issue close 7 --reason not planned", None),
        ("issue edit 7 --add-assignee team-bot", None),
        ("pr review 12 --comment --body-file -", "Review 1 of 3"),
    ]
    assert sent[6][0] == "pr merge 12 --squash --delete-branch"


def test_a_review_is_requested_through_the_rest_api():
    # `gh pr edit --add-reviewer` also reads the repo's teams, which a token
    # with only the repo scope may not: it failed for the team's account.
    gh = Gh()

    GhGitHub(REPO, gh).request_review(12, "owner")

    assert gh.calls == [(["api", "-X", "POST", f"repos/{REPO}/pulls/12/requested_reviewers", "-f", "reviewers[]=owner"], None)]


def test_a_part_becomes_a_sub_issue_of_its_task_by_the_part_s_id():
    # gh has no command for sub-issues; GitHub's API wants the issue's id, not its number.
    gh = Gh({f"api repos/{REPO}/issues/13": "4242\n"})

    GhGitHub(REPO, gh).add_sub_issue(7, 13)

    assert gh.calls[-1][0] == ["api", "-X", "POST", f"repos/{REPO}/issues/7/sub_issues", "-F", "sub_issue_id=4242"]


def test_opening_a_pr_returns_it():
    gh = Gh({"pr create": "https://github.com/owner/linkedin-games/pull/13\n", "pr list": [{"number": 13, "headRefName": "team/7-x", "url": "u", "latestReviews": []}]})

    pr = GhGitHub(REPO, gh).open_pull_request("team/7-x", "Sumbreak", "Closes #7")

    assert pr.number == 13
    create = next(args for args, _ in gh.calls if args[:2] == ["pr", "create"])
    assert create[create.index("--head") + 1] == "team/7-x"
    assert create[create.index("--base") + 1] == "main"


def test_reviews_and_comments_on_a_pr_are_read_with_their_authors_oldest_first():
    # The owner may answer on the PR rather than on the issue.
    review = {"author": {"login": "team-bot"}, "body": "Review 1 of 3", "submittedAt": "2026-11-17T11:00:00Z", "state": "COMMENTED"}
    comment = {"author": {"login": "owner"}, "body": "Run the tests this time.", "createdAt": "2026-11-17T12:00:00Z"}
    gh = Gh({"pr view 12": {"reviews": [review], "comments": [comment]}})

    said = GhGitHub(REPO, gh).reviews_on(12)

    assert [(c.author, c.body) for c in said] == [("team-bot", "Review 1 of 3"), ("owner", "Run the tests this time.")]


def test_times_are_local():
    assert local("2026-11-17T08:00:00Z").tzinfo is None
    assert local("2026-11-17T08:00:00Z") == datetime(2026, 11, 17, 8, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
