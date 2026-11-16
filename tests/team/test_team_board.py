"""The board: a page on localhost that shows who works on what, with each
run's log as readable lines."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from team.board import serve, transcript

SNAPSHOT = {
    "agents": [{"agent": "20261117-090000-developer-7", "role": "developer", "issue": 7, "title": "New game: Sumbreak", "stage": "develop", "branch": "team/7-new-game-sumbreak", "seconds": 180}],
    "waiting_for_you": [{"issue": 5, "title": "May I add scipy?", "reason": "needs-human"}],
    "queue": [],
    "paused_until": None,
}

STREAM = [
    {"type": "system", "subtype": "init", "model": "claude-opus-5-5"},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll start with a failing test."}]}},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "uv run pytest tests/sumbreak"}}]}},
    {"type": "user", "message": {"content": [{"type": "tool_result", "content": "1 failed in 0.2s\nmore"}]}},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "engines/sumbreak/solver.py", "old_string": "a", "new_string": "b"}}]}},
    {"type": "result", "subtype": "success", "is_error": False, "result": "", "structured_output": {"status": "ready", "summary": "Sumbreak solved."}},
]


@pytest.fixture
def board(tmp_path: Path):
    lines = [json.dumps(m) for m in STREAM]
    (tmp_path / "20261117-090000-developer-7.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (tmp_path / "20261117-090000-developer-7.prompt.md").write_text("Build Sumbreak.", encoding="utf-8")
    server = serve(lambda: SNAPSHOT, tmp_path, port=0, repo="owner/linkedin-games")
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def test_a_log_reads_as_what_the_agent_did():
    lines = transcript(json.dumps(m) for m in STREAM)

    assert lines == [
        "started (claude-opus-5-5)",
        "💬 I'll start with a failing test.",
        "▶ Bash: uv run pytest tests/sumbreak",
        "  ↳ 1 failed in 0.2s …",
        "▶ Edit: engines/sumbreak/solver.py",
        '■ verdict: {"status": "ready", "summary": "Sumbreak solved."}',
    ]


def test_the_state_shows_each_agent_with_its_latest_action(board):
    state = json.loads(get(board + "/state.json"))

    [agent] = state["agents"]
    assert (agent["role"], agent["issue"], agent["seconds"]) == ("developer", 7, 180)
    assert agent["last"] == '■ verdict: {"status": "ready", "summary": "Sumbreak solved."}'
    assert state["waiting_for_you"] == SNAPSHOT["waiting_for_you"]
    assert state["repo"] == "owner/linkedin-games"
    assert state["recent"][0]["agent"] == "20261117-090000-developer-7"


def test_each_run_s_log_and_prompt_can_be_read(board):
    assert "▶ Bash: uv run pytest tests/sumbreak" in get(board + "/log/20261117-090000-developer-7")
    assert get(board + "/prompt/20261117-090000-developer-7") == "Build Sumbreak."


def test_the_page_is_served(board):
    assert "<title>LinkedIn games team</title>" in get(board + "/")


def test_unknown_runs_and_paths_are_not_found(board):
    for path in ("/log/nobody", "/log/..%2F..%2Fsecret", "/nothing"):
        with pytest.raises(urllib.error.HTTPError) as error:
            get(board + path)
        assert error.value.code == 404
