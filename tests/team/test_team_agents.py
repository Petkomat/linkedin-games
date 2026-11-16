"""How an agent is started (the `claude` command line for each role) and what
its stream of output means when it ends."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from team.agents import command, outcome
from team.model import Failed, Job, UsageLimited, Verdict
from team.roles import DEVELOPER, PROJECT_MANAGER, REVIEWER

STREAMS = Path(__file__).parent / "streams"


def job(role: str = "developer", resume: bool = False) -> Job:
    return Job(role, 7, "New game: Sumbreak", "Build it.", "team/7-new-game-sumbreak", "5f0c-session", resume)


def option(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def allowed(argv: list[str]) -> list[str]:
    start = argv.index("--allowedTools") + 1
    end = next((i for i in range(start, len(argv)) if argv[i].startswith("-")), len(argv))
    return argv[start:end]


def test_an_agent_runs_headless_and_streams_its_work():
    argv = command(job(), DEVELOPER)

    assert argv[:2] == ["claude", "-p"]
    assert option(argv, "--output-format") == "stream-json"
    assert "--verbose" in argv


def test_each_role_has_its_model():
    assert option(command(job(), DEVELOPER), "--model") == "opus"
    assert option(command(job("reviewer"), REVIEWER), "--model") == "opus"
    assert option(command(job("project-manager"), PROJECT_MANAGER), "--model") == "sonnet"


def test_nothing_outside_a_role_s_list_is_allowed_and_nothing_asks():
    argv = command(job(), DEVELOPER)

    assert option(argv, "--permission-mode") == "dontAsk"
    assert "--dangerously-skip-permissions" not in argv
    assert {"Edit", "Write", "Bash(uv run *)", "Bash(git push *)"} <= set(allowed(argv))
    assert not any("merge" in rule or rule == "Bash" for rule in allowed(argv))


def test_reviewers_and_the_project_manager_cannot_edit():
    for role, name in ((REVIEWER, "reviewer"), (PROJECT_MANAGER, "project-manager")):
        rules = allowed(command(job(name), role)) if "--allowedTools" in command(job(name), role) else []
        assert "Edit" not in rules and "Write" not in rules


def test_commits_carry_no_claude_attribution():
    settings = json.loads(option(command(job(), DEVELOPER), "--settings"))

    assert settings["attribution"] == {"commit": "", "pr": ""}
    assert settings["includeCoAuthoredBy"] is False


def test_the_run_must_end_with_the_role_s_verdict():
    schema = json.loads(option(command(job(), DEVELOPER), "--json-schema"))

    assert schema["properties"]["status"]["enum"] == ["ready", "stuck"]
    assert "status" in schema["required"]


def test_a_first_run_names_its_session_and_a_later_one_resumes_it():
    assert option(command(job(), DEVELOPER), "--session-id") == "5f0c-session"
    argv = command(job(resume=True), DEVELOPER)
    assert option(argv, "--resume") == "5f0c-session"
    assert "--session-id" not in argv


def test_a_finished_run_gives_its_verdict():
    lines = (STREAMS / "verdict.jsonl").read_text(encoding="utf-8").splitlines()

    assert outcome(lines, exit_code=0) == Verdict({"verdict": "ok", "note": "Done"})


def test_a_run_that_hits_the_usage_limit_says_when_it_resets():
    lines = [
        json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": 1794852000, "rateLimitType": "five_hour"}}),
        json.dumps({"type": "result", "subtype": "error_during_execution", "is_error": True, "result": "Claude usage limit reached"}),
    ]

    assert outcome(lines, exit_code=1) == UsageLimited(datetime.fromtimestamp(1794852000))


def test_a_run_that_crashes_is_a_failure_with_a_reason():
    lines = [json.dumps({"type": "system", "subtype": "init"})]

    result = outcome(lines, exit_code=3)

    assert isinstance(result, Failed)
    assert "3" in result.reason


def test_a_run_that_ends_in_an_error_is_a_failure_with_its_message():
    lines = [json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True, "result": "Reached the turn limit"})]

    assert outcome(lines, exit_code=1) == Failed("Reached the turn limit")
