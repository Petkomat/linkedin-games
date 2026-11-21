"""The board: a page on localhost showing which agent works on what, what
waits for the owner, and every run's log as readable lines."""

from __future__ import annotations

import html
import json
import re
import threading
from collections.abc import Callable, Iterable
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

RUN = re.compile(r"^[\w-]+$")  # a run's name; nothing that could leave the log folder
RECENT = 15
# A run's name as team/agents.py gives it: when it started, the role, the task.
NAME = re.compile(r"^(\d{8}-\d{6})-([a-z]+(?:-[a-z]+)*?)-?(\d+)?$")


def run_name(name: str) -> dict[str, Any]:
    """The role, task and start of a run named like 20261120-112334-operator-34."""
    found = NAME.match(name)
    try:
        started = datetime.strptime(found.group(1), "%Y%m%d-%H%M%S") if found else None
    except ValueError:
        started = None
    if found is None or started is None:
        return {"role": None, "issue": None, "started": None}
    issue = found.group(3)
    return {"role": found.group(2), "issue": int(issue) if issue else None, "started": started.isoformat()}


def transcript(lines: Iterable[str]) -> list[str]:
    """A run's stream-json output as one readable line per step."""
    out: list[str] = []
    for line in lines:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = message.get("type")
        if kind == "system" and message.get("subtype") == "init":
            out.append(f"started ({message.get('model', '?')})")
        elif kind == "assistant":
            for part in message.get("message", {}).get("content", []):
                if part.get("type") == "text" and part.get("text", "").strip():
                    out.append(f"💬 {part['text'].strip()}")
                elif part.get("type") == "tool_use":
                    out.append(f"▶ {part.get('name')}: {_gist(part.get('input', {}))}")
        elif kind == "user":
            for part in message.get("message", {}).get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    out.append(f"  ↳ {_first_line(part.get('content'))}")
        elif kind == "rate_limit_event" and message.get("rate_limit_info", {}).get("status") == "rejected":
            out.append("⏸ usage limit reached")
        elif kind == "result":
            if isinstance(message.get("structured_output"), dict):
                out.append(f"■ verdict: {json.dumps(message['structured_output'])}")
            else:
                out.append(f"■ ended: {message.get('result') or message.get('subtype')}")
    return out


def recap(lines: Iterable[str]) -> dict[str, Any]:
    """What a run's stream-json output amounts to: its model, and the status,
    title and summary of the verdict it ended with."""
    model, result = None, None
    for line in lines:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("type") == "system" and message.get("subtype") == "init":
            model = message.get("model")
        elif message.get("type") == "result":
            result = message
    verdict = result.get("structured_output") if result else None
    status, title, summary = None, "", ""
    if isinstance(verdict, dict):
        status = _first(verdict, STATUS_FIELDS)
        summary = _first(verdict, SUMMARY_FIELDS)
        if status is None and summary is None:  # a verdict of no role's shape
            status, summary = "verdict", json.dumps(verdict, ensure_ascii=False)
        status, title, summary = status or "verdict", str(verdict.get("title") or ""), summary or ""
    elif result is not None:
        status, summary = "error" if result.get("is_error") else "ended", str(result.get("result") or result.get("subtype") or "")
    return {"model": model, "status": status, "title": title, "summary": summary}


# A verdict's deciding field and its text, by role (see team/roles.py).
STATUS_FIELDS = ("status", "decision")
SUMMARY_FIELDS = ("summary", "comment", "review")


def _first(verdict: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    return next((str(verdict[f]) for f in fields if verdict.get(f)), None)


def markdown(text: str, repo: str = "") -> str:
    """A summary's markdown as HTML: paragraphs and line breaks, headings,
    lists, code blocks and inline code, bold, italics, web links, and #n as a
    link to the repo's issue n. Everything is escaped first, so no HTML in it
    reaches the page."""
    out: list[str] = []
    paragraph: list[str] = []  # the open paragraph's lines
    items: list[list[str]] = []  # the open list's items, each its lines
    kind = "ul"  # that list's tag
    code: list[str] | None = None  # the open code block's lines

    def flush() -> None:
        if paragraph:
            out.append(f"<p>{'<br>'.join(paragraph)}</p>")
            paragraph.clear()
        if items:
            out.append(f"<{kind}>{''.join('<li>' + '<br>'.join(item) + '</li>' for item in items)}</{kind}>")
            items.clear()

    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if code is not None:
            if stripped.startswith("```"):
                out.append(_code(code))
                code = None
            else:
                code.append(line)
        elif stripped.startswith("```"):
            flush()
            code = []
        elif not stripped:
            flush()
        elif heading := HEADING.match(stripped):
            flush()
            out.append(f"<h4>{_inline(heading.group(1), repo)}</h4>")
        elif item := ITEM.match(line):
            tag = "ul" if item.group(1) else "ol"
            if paragraph or tag != kind:
                flush()
            kind = tag
            items.append([_inline(item.group(2), repo)])
        elif items and line[0].isspace():  # an item's next line
            items[-1].append(_inline(stripped, repo))
        else:
            if items:
                flush()
            paragraph.append(_inline(stripped, repo))
    flush()
    if code is not None:  # never closed: code to the end
        out.append(_code(code))
    return "".join(out)


HEADING = re.compile(r"^#{1,6}\s+(.*)$")
ITEM = re.compile(r"^\s*(?:([-*+])|\d+[.)])\s+(.*)$")  # a bullet, or a number


def _code(lines: list[str]) -> str:
    return f"<pre><code>{html.escape(chr(10).join(lines).rstrip())}</code></pre>"


INLINE_CODE = re.compile(r"`([^`\n]+)`")
# These match text already escaped, so a link's address can't hold a quote or an angle bracket.
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")  # web links only: no javascript: and the like
TASK = re.compile(r"(?<![\w&#/])#(\d+)\b")  # #36, an issue or PR
BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])")


def _inline(line: str, repo: str) -> str:
    """One line's inline markdown; code spans are left as they are."""
    parts = INLINE_CODE.split(line)  # odd ones are code
    return "".join(f"<code>{html.escape(part)}</code>" if i % 2 else _linked(html.escape(part), repo) for i, part in enumerate(parts))


def _linked(escaped: str, repo: str) -> str:
    out, at = [], 0
    for link in LINK.finditer(escaped):
        out += [_styled(escaped[at : link.start()], repo), _anchor(link.group(2), _styled(link.group(1), ""))]
        at = link.end()
    return "".join([*out, _styled(escaped[at:], repo)])


def _styled(escaped: str, repo: str) -> str:
    if repo:
        escaped = TASK.sub(lambda task: _anchor(f"https://github.com/{html.escape(repo)}/issues/{task.group(1)}", task.group(0)), escaped)
    escaped = BOLD.sub(r"<strong>\1</strong>", escaped)
    return ITALIC.sub(r"<em>\1</em>", escaped)


def _anchor(url: str, text: str) -> str:
    return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'


def _gist(arguments: dict[str, Any]) -> str:
    for key in ("command", "file_path", "pattern", "skill", "url", "description", "prompt"):
        if key in arguments:
            return " ".join(str(arguments[key]).split())[:200]
    return json.dumps(arguments)[:200]


def _first_line(content: Any) -> str:
    if isinstance(content, list):
        content = " ".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
    lines = str(content or "").strip().splitlines() or [""]
    return lines[0][:200] + (" …" if len(lines) > 1 else "")


def serve(state: Callable[[], dict[str, Any]], logs: Path, port: int = 8765, repo: str = "", on_stop: Callable[[], None] | None = None) -> ThreadingHTTPServer:
    """Start the board on localhost in a background thread."""

    def read(run: str, suffix: str) -> str | None:
        path = logs / f"{run}{suffix}"
        return path.read_text(encoding="utf-8", errors="replace") if RUN.match(run) and path.is_file() else None

    def snapshot() -> dict[str, Any]:
        now = state()
        agents = []
        for agent in now["agents"]:
            steps = transcript((read(agent["agent"], ".jsonl") or "").splitlines())
            agents.append({**agent, "last": steps[-1] if steps else ""})
        runs = sorted(logs.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:RECENT] if logs.exists() else []
        recent = [{"agent": p.stem, "last": (transcript(p.read_text(encoding="utf-8", errors="replace").splitlines()) or [""])[-1]} for p in runs]
        return {**now, "agents": agents, "recent": recent, "repo": repo}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server's name)
            path = self.path.split("?")[0]
            if path == "/":
                self._send(PAGE, "text/html")
            elif path == "/state.json":
                self._send(json.dumps(snapshot()), "application/json")
            elif path.startswith(("/log/", "/prompt/")):
                kind, run = path.strip("/").split("/", 1)
                text = read(run, ".jsonl" if kind == "log" else ".prompt.md")
                if text is None:
                    self.send_error(404)
                else:
                    self._send("\n".join(transcript(text.splitlines())) if kind == "log" else text, "text/plain")
            else:
                self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/stop" and on_stop:
                self._send("stopping", "text/plain")
                threading.Thread(target=on_stop, daemon=True).start()
            else:
                self.send_error(404)

        def _send(self, body: str, kind: str) -> None:
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", f"{kind}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: Any) -> None:  # quiet
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>LinkedIn games team</title>
<style>
 body { font: 14px/1.4 system-ui, sans-serif; margin: 1.5rem; color: #222; }
 h1 { font-size: 1.3rem; } h2 { font-size: 1.05rem; margin-top: 1.5rem; }
 table { border-collapse: collapse; width: 100%; }
 td, th { text-align: left; padding: .3rem .6rem; border-bottom: 1px solid #ddd; vertical-align: top; }
 tr.run { cursor: pointer; } tr.run:hover, tr.chosen { background: #eef4ff; }
 .last { color: #555; font-family: ui-monospace, monospace; font-size: 12px; }
 .you { background: #fff4d6; } .paused { background: #ffe0e0; padding: .5rem; }
 pre { background: #111; color: #ddd; padding: .8rem; height: 28rem; overflow: auto; white-space: pre-wrap; font-size: 12px; }
 .muted { color: #888; }
</style></head><body>
<h1>LinkedIn games team</h1>
<div id="paused"></div>
<h2>Waiting for you</h2><table id="you"></table>
<h2>Working now</h2><table id="agents"></table>
<h2>Queue</h2><table id="queue"></table>
<h2>Recent runs</h2><table id="recent"></table>
<h2 id="logtitle">Log</h2><pre id="log" class="muted">Click a run to see its log.</pre>
<script>
let chosen = null, repo = "";
const esc = s => String(s ?? "").replace(/[&<>]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]));
const link = n => repo ? `<a href="https://github.com/${repo}/issues/${n}" target="_blank">#${n}</a>` : `#${n}`;
const time = s => s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h ${Math.floor(s % 3600 / 60)}m`;
function rows(id, items, row, empty) {
  document.getElementById(id).innerHTML = items.length ? items.map(row).join("") : `<tr><td class="muted">${empty}</td></tr>`;
}
async function refresh() {
  const state = await (await fetch("/state.json")).json();
  repo = state.repo;
  document.getElementById("paused").innerHTML = state.paused_until ? `<p class="paused">Paused by Claude's usage limit until ${esc(state.paused_until)}</p>` : "";
  rows("you", state.waiting_for_you, w => `<tr class="you"><td>${link(w.issue)}</td><td>${esc(w.title)}</td><td>${w.reason === "ready" ? "ready to merge: review the PR" : "needs your decision"}</td></tr>`, "Nothing.");
  rows("agents", state.agents, a => `<tr class="run ${a.agent === chosen ? "chosen" : ""}" onclick="choose('${a.agent}')"><td>${esc(a.role)}</td><td>${link(a.issue)}</td><td>${esc(a.title)}</td><td>${esc(a.stage)}</td><td>${time(a.seconds)}</td><td class="last">${esc(a.last)}</td></tr>`, "No agent is working.");
  rows("queue", state.queue, q => `<tr><td>${link(q.issue)}</td><td>${esc(q.title)}</td><td>${esc(q.stage)}</td></tr>`, "Empty.");
  rows("recent", state.recent, r => `<tr class="run ${r.agent === chosen ? "chosen" : ""}" onclick="choose('${r.agent}')"><td>${esc(r.agent)}</td><td class="last">${esc(r.last)}</td></tr>`, "None yet.");
  if (chosen) {
    const log = document.getElementById("log"), atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;
    log.textContent = await (await fetch(`/log/${chosen}`)).text();
    log.classList.remove("muted");
    if (atEnd) log.scrollTop = log.scrollHeight;
  }
}
function choose(agent) {
  chosen = agent;
  document.getElementById("logtitle").innerHTML = `Log: ${esc(agent)} <a href="/prompt/${agent}" target="_blank">(its prompt)</a>`;
  refresh();
}
refresh(); setInterval(refresh, 2000);
</script></body></html>
"""
