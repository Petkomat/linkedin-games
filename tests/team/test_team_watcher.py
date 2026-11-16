"""The Watcher: turns the daily guest check, CI on main and a silent team
into incidents, one open incident per problem."""

from __future__ import annotations

from datetime import timedelta

from team.watcher import watch

from .fakes import T0, FakeGitHub

TITLES = {"queens": "Queens", "zip": "Zip", "tango": "Tango"}
RUN = "https://github.com/owner/linkedin-games/actions/runs/42"


def incidents(github: FakeGitHub):
    return [issue for issue in github.open_issues() if "kind:incident" in issue.labels]


def test_a_game_that_fails_today_is_an_incident_with_the_run_that_saw_it():
    github = FakeGitHub()

    watch(github, {"queens": True, "zip": False, "tango": True}, TITLES, RUN, T0)

    [incident] = incidents(github)
    assert "Zip" in incident.title
    assert RUN in incident.body
    assert incident.author == "github-actions[bot]"


def test_the_same_failure_the_next_day_is_a_comment_not_a_new_incident():
    github = FakeGitHub()
    watch(github, {"queens": True, "zip": False, "tango": True}, TITLES, RUN, T0)

    watch(github, {"queens": True, "zip": False, "tango": True}, TITLES, RUN + "3", T0 + timedelta(days=1))

    [incident] = incidents(github)
    assert RUN + "3" in github.comments_on(incident.number)[-1].body


def test_every_game_failing_at_once_is_one_blocked_incident():
    github = FakeGitHub()

    watch(github, {"queens": False, "zip": False, "tango": False}, TITLES, RUN, T0)

    [incident] = incidents(github)
    assert "block" in incident.title.lower()


def test_red_tests_on_main_are_an_incident():
    github = FakeGitHub()

    watch(github, {"queens": True}, TITLES, RUN, T0, ci_failed=True)

    [incident] = incidents(github)
    assert "tests" in incident.title.lower()


def test_a_team_that_has_not_touched_its_tasks_for_a_day_is_an_incident():
    github = FakeGitHub()
    github.open_issue("Zip misreads", labels=("stage:develop",), age=timedelta(hours=30))
    github.open_issue("Waits for the owner", labels=("stage:ready",), age=timedelta(days=3))

    watch(github, {"queens": True}, TITLES, RUN, T0)

    [incident] = incidents(github)
    assert "#1" in incident.body


def test_a_waiting_owner_or_a_busy_team_is_no_incident():
    github = FakeGitHub()
    github.open_issue("Waits for the owner", labels=("stage:develop", "needs-human"), age=timedelta(days=3))
    github.open_issue("Being worked on", labels=("stage:review",), age=timedelta(hours=2))

    watch(github, {"queens": True, "zip": True}, TITLES, RUN, T0)

    assert incidents(github) == []
