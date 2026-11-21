"""The board: a page on localhost that shows who works on what, with each
run's log as readable lines."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from team.board import markdown, recap, run_name, serve, transcript

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


def test_a_run_s_name_gives_its_role_task_and_start():
    assert run_name("20261117-090000-developer-7") == {"role": "developer", "issue": 7, "started": "2026-11-17T09:00:00"}
    assert run_name("20261120-112334-operator34") == {"role": "operator", "issue": 34, "started": "2026-11-20T11:23:34"}
    assert run_name("20261121-235959-project-manager-12") == {"role": "project-manager", "issue": 12, "started": "2026-11-21T23:59:59"}
    assert run_name("20261121-080000-scout") == {"role": "scout", "issue": None, "started": "2026-11-21T08:00:00"}


def test_a_run_name_of_another_shape_gives_nothing():
    for name in ("notes", "20261399-250000-developer-7", "developer-7"):
        assert run_name(name) == {"role": None, "issue": None, "started": None}


def stream(*messages: dict) -> list[str]:
    return [json.dumps(m) for m in ({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"}, *messages)]


def ended(**result) -> dict:
    return {"type": "result", "subtype": "success", "is_error": False, "result": "", **result}


# The issue's sample: an Operator's verdict.
OPERATOR_VERDICT = {
    "status": "ready",
    "summary": "PR #36 was already based on the current origin/main, so the rebase changed nothing and the push was a no-op. `uv run pytest` passes, 677 tests.",
    "title": "Sumbreak refuses a tile whose mark matches no digit, instead of reading it as the nearest digit",
}


def test_a_verdict_gives_the_run_s_status_title_and_summary():
    run = recap(stream(ended(structured_output=OPERATOR_VERDICT)))

    assert run["model"] == "claude-sonnet-5-5"
    assert (run["status"], run["title"], run["summary"]) == ("ready", OPERATOR_VERDICT["title"], OPERATOR_VERDICT["summary"])


def test_a_project_manager_s_and_a_reviewer_s_verdict_give_their_decision_and_text():
    manager = recap(stream(ended(structured_output={"decision": "wait", "comment": "Wait for **#36**.", "after": 36, "stage": "develop"})))
    reviewer = recap(stream(ended(structured_output={"decision": "changes", "review": "1. The OCR misreads 7."})))

    assert (manager["status"], manager["title"], manager["summary"]) == ("wait", "", "Wait for **#36**.")
    assert (reviewer["status"], reviewer["summary"]) == ("changes", "1. The OCR misreads 7.")


def test_a_verdict_of_another_shape_shows_as_it_is():
    run = recap(stream(ended(structured_output={"verdict": "ok", "note": "Done"})))

    assert (run["status"], run["summary"]) == ("verdict", '{"verdict": "ok", "note": "Done"}')


def test_a_run_that_ended_without_a_verdict_says_how_it_ended():
    finished = recap(stream(ended(result="I fixed it.\n\n- one\n- two")))
    failed = recap(stream(ended(subtype="error_during_execution", is_error=True, result="Claude AI usage limit reached")))
    cut_short = recap(stream(ended(subtype="error_max_turns", is_error=True, result="")))

    assert (finished["status"], finished["title"], finished["summary"]) == ("ended", "", "I fixed it.\n\n- one\n- two")
    assert (failed["status"], failed["summary"]) == ("error", "Claude AI usage limit reached")
    assert (cut_short["status"], cut_short["summary"]) == ("error", "error_max_turns")


def test_a_run_without_a_result_has_no_status_yet():
    run = recap(stream({"type": "assistant", "message": {"content": [{"type": "text", "text": "Reading."}]}}))

    assert (run["model"], run["status"], run["summary"]) == ("claude-sonnet-5-5", None, "")
    assert recap([]) == {"model": None, "status": None, "title": "", "summary": ""}


def test_a_summary_s_markdown_is_escaped_first():
    assert markdown("<script>alert('x')</script> & \"y\"") == "<p>&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp; &quot;y&quot;</p>"


def test_a_summary_keeps_its_paragraphs_and_line_breaks():
    assert markdown("One\ntwo\n\n\nThree\r\n") == "<p>One<br>two</p><p>Three</p>"
    assert markdown("") == ""


def test_a_summary_s_code_blocks_keep_their_lines_as_they_are():
    text = "Run:\n```bash\nuv run pytest <x>\n  **not bold**\n\nlast\n```\nDone."

    assert markdown(text) == "<p>Run:</p><pre><code>uv run pytest &lt;x&gt;\n  **not bold**\n\nlast</code></pre><p>Done.</p>"
    assert markdown("```\nnever closed") == "<pre><code>never closed</code></pre>"


def test_a_summary_s_inline_code_bold_and_italics():
    text = "`a **b** <i>` and **bold** and *it*, but 5 * 3 * 2 stays"

    assert markdown(text) == "<p><code>a **b** &lt;i&gt;</code> and <strong>bold</strong> and <em>it</em>, but 5 * 3 * 2 stays</p>"


def test_a_summary_s_lists_and_headings():
    text = "## What changed\nFixed:\n- one\n* two\n  and more\n\n1. first\n2) second\nAfter."

    assert markdown(text) == (
        "<h4>What changed</h4><p>Fixed:</p><ul><li>one</li><li>two<br>and more</li></ul>"
        "<ol><li>first</li><li>second</li></ol><p>After.</p>"
    )
    assert markdown("#36 is no heading") == "<p>#36 is no heading</p>"


def test_a_summary_links_its_tasks_and_web_links():
    text = "PR #36 (see [the **run**](https://github.com/o/r/actions/runs/1?a=1&b=2)), not `#37` nor x#38"

    assert markdown(text, repo="o/r") == (
        '<p>PR <a href="https://github.com/o/r/issues/36" target="_blank" rel="noopener">#36</a>'
        ' (see <a href="https://github.com/o/r/actions/runs/1?a=1&amp;b=2" target="_blank" rel="noopener">the <strong>run</strong></a>),'
        " not <code>#37</code> nor x#38</p>"
    )
    assert markdown("PR #36") == "<p>PR #36</p>"  # no repo, no link


def test_a_summary_s_links_go_nowhere_but_the_web():
    assert markdown("[x](javascript:alert(1))") == "<p>[x](javascript:alert(1))</p>"
    assert markdown('[x](https://a.b/"onclick="y)') == '<p><a href="https://a.b/&quot;onclick=&quot;y" target="_blank" rel="noopener">x</a></p>'


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
