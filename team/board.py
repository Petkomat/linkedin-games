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

    recaps: dict[str, tuple[tuple[int, int], dict[str, Any]]] = {}  # by run: its log's stamp, and its recap
    lock = threading.Lock()

    def recapped(run: str) -> dict[str, Any]:
        """A run's recap and latest step, read again only once its log has changed."""
        path = logs / f"{run}.jsonl"
        if not (RUN.match(run) and path.is_file()):
            return {**recap([]), "last": "", "html": ""}
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        if run not in recaps or recaps[run][0] != stamp:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            steps, found = transcript(lines), recap(lines)
            recaps[run] = (stamp, {**found, "last": steps[-1] if steps else "", "html": markdown(found["summary"], repo)})
        return recaps[run][1]

    def snapshot() -> dict[str, Any]:
        now = state()
        working = {agent["agent"] for agent in now["agents"]}
        runs = sorted(logs.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:RECENT] if logs.exists() else []
        with lock:
            agents = []
            for agent in now["agents"]:
                found = recapped(agent["agent"])
                agents.append({**agent, "last": found["last"], "model": found["model"]})
            recent = []
            for run in (p.stem for p in runs):
                found = recapped(run)
                status = found["status"] or ("running" if run in working else "stopped")
                recent.append({"agent": run, **run_name(run), **found, "status": status})
            for gone in set(recaps) - working - {p.stem for p in runs}:
                del recaps[gone]
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


# The page: plain HTML, CSS and JavaScript, nothing loaded from elsewhere. Every
# text from the state is escaped where it's put in; a summary's HTML comes
# from markdown(), which escaped it already.
PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LinkedIn games team</title>
<style>
:root {
  color-scheme: light dark;
  --bg: #f4f6f8; --card: #fff; --text: #1f2328; --muted: #656d76; --line: #d8dee4; --zebra: #f8fafb;
  --hover: #f0f5fc; --accent: #0a66c2; --code: #eff2f5; --banner: #fff8e1; --banner-line: #f0c75e;
  --shadow: 0 1px 2px rgba(31, 35, 40, .05), 0 6px 18px rgba(31, 35, 40, .06); --ink: 82%;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117; --card: #161b22; --text: #e6edf3; --muted: #8d96a0; --line: #30363d; --zebra: #1a2029;
    --hover: #1c2433; --accent: #4493f8; --code: #262c36; --banner: #2b2111; --banner-line: #9e6a03;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 6px 18px rgba(0, 0, 0, .25); --ink: 55%;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
a { color: var(--accent); text-decoration: none; } a:hover { text-decoration: underline; }
code, pre, .step { font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; }

header { display: flex; align-items: center; gap: .9rem; padding: .9rem 1.5rem; color: #fff;
  background: linear-gradient(120deg, #0a66c2, #004182); box-shadow: 0 2px 10px rgba(0, 0, 0, .15); }
header h1 { margin: 0; font-size: 1.2rem; font-weight: 650; letter-spacing: -.01em; }
header p { margin: 0; font-size: 12.5px; opacity: .85; }
header a { color: inherit; text-decoration: underline dotted; }
.logo { display: grid; grid-template-columns: repeat(2, 11px); gap: 3px; flex: none; }
.logo i { width: 11px; height: 11px; border-radius: 3px; background: rgba(255, 255, 255, .92); }
.logo i:nth-child(2) { background: #f5c75d; } .logo i:nth-child(3) { background: #8cc8ff; }
.live { margin-left: auto; display: flex; align-items: center; gap: .45rem; font-size: 12px; white-space: nowrap; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #3fb950; animation: pulse 2s infinite; }
.dot.off { background: #f85149; animation: none; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(63, 185, 80, .6); } 70%, 100% { box-shadow: 0 0 0 7px rgba(63, 185, 80, 0); } }

main { max-width: 1180px; margin: 1.25rem auto 2rem; padding: 0 1.25rem; display: grid; gap: 1rem; }
.column { display: grid; gap: 1rem; min-width: 0; align-content: start; }
@media (min-width: 1500px) {
  main { max-width: 1720px; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start; }
  .side { position: sticky; top: 1rem; } #log { height: calc(100vh - 8.5rem); }
}
.card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; box-shadow: var(--shadow); padding: .85rem 1.1rem 1rem; min-width: 0; }
h2 { margin: 0 0 .65rem; display: flex; align-items: center; gap: .5rem; color: var(--muted);
  font-size: 12px; font-weight: 650; text-transform: uppercase; letter-spacing: .07em; }
.count { min-width: 1.5rem; padding: 0 .45rem; border-radius: 999px; background: var(--code); color: var(--text);
  font-size: 11px; line-height: 18px; text-align: center; letter-spacing: 0; }
.count.hot { background: #fbca04; color: #1f2328; } .count.bad { background: #cf222e; color: #fff; }
.problem { padding: .35rem 0; border-top: 1px solid var(--line); font: 12px/1.5 ui-monospace, Consolas, monospace; overflow-wrap: anywhere; }
.problem:first-child { border-top: 0; }
.empty { margin: 0; color: var(--muted); font-style: italic; }
.banner { margin: 0; padding: .65rem 1rem; border: 1px solid var(--banner-line); border-radius: 10px; background: var(--banner); }

table { width: 100%; border-collapse: collapse; }
td { padding: .45rem .55rem; border-top: 1px solid var(--line); vertical-align: middle; }
tr:first-child td { border-top: 0; }
tr:nth-child(even) td { background: var(--zebra); }
tr:hover td { background: var(--hover); }
td.narrow { width: 1%; white-space: nowrap; } td.end { width: 1%; white-space: nowrap; text-align: right; }

.pill { display: inline-flex; align-items: center; gap: .3rem; padding: 0 7px; border-radius: 999px; white-space: nowrap;
  font-size: 12px; font-weight: 500; line-height: 18px;
  background: color-mix(in srgb, var(--c) 14%, var(--card)); color: color-mix(in srgb, var(--c) var(--ink), var(--text));
  border: 1px solid color-mix(in srgb, var(--c) 45%, transparent); }
.pill.status { font-weight: 650; }
.pill.status::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.pill.working::before { animation: blink 1.4s infinite; }
@keyframes blink { 50% { opacity: .25; } }

.runs { display: grid; gap: .6rem; }
.run { padding: .6rem .85rem .65rem; border: 1px solid var(--line); border-left: 4px solid var(--role); border-radius: 10px;
  cursor: pointer; transition: background .15s, box-shadow .15s; min-width: 0; }
.run:hover { background: var(--hover); }
.run:focus-visible, .run.chosen { outline: none; box-shadow: 0 0 0 2px var(--accent); }
.head { display: flex; flex-wrap: wrap; align-items: center; gap: .3rem .6rem; }
.role { font-weight: 650; }
.when { color: var(--muted); font-size: 12.5px; }
.task { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1 1 12rem; }
.pills { margin-left: auto; display: flex; flex-wrap: wrap; gap: .3rem; }
.run h3 { margin: .3rem 0 0; font-size: 14px; font-weight: 600; line-height: 1.4; }
.step { margin-top: .3rem; color: var(--muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.md { margin-top: .3rem; max-height: 15rem; overflow: auto; font-size: 13.5px; overflow-wrap: anywhere; }
.md > :first-child { margin-top: 0; } .md > :last-child { margin-bottom: 0; }
.md p, .md ul, .md ol, .md pre { margin: .4rem 0; } .md ul, .md ol { padding-left: 1.3rem; }
.md h4 { margin: .6rem 0 .2rem; font-size: 13.5px; }
.md code { padding: .1rem .3rem; border-radius: 5px; background: var(--code); font-size: 12px; }
.md pre { padding: .55rem .7rem; border-radius: 8px; background: var(--code); overflow: auto; }
.md pre code { padding: 0; background: none; }

.logtitle { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.logtitle a { text-transform: none; letter-spacing: 0; font-weight: 500; }
.logtitle .name { text-transform: none; letter-spacing: 0; color: var(--text); font-family: ui-monospace, Consolas, monospace; font-weight: 500; }
#log { margin: 0; height: 30rem; overflow: auto; padding: .8rem 1rem; border-radius: 8px; background: #0d1117; color: #c9d1d9;
  font-size: 12px; line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }
#log.idle { color: #8b949e; font-style: italic; }
.l-say { color: #e6edf3; } .l-tool { color: #79c0ff; } .l-out { color: #8b949e; } .l-end { color: #7ee787; font-weight: 600; }
.l-wait { color: #e3b341; } .l-start { color: #d2a8ff; }
</style></head><body>
<header>
  <span class="logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
  <div><h1>LinkedIn games team</h1><p id="repo">Bots for LinkedIn's daily puzzles, and the agents that build them</p></div>
  <span class="live"><span class="dot" id="dot"></span><span id="updated">connecting…</span></span>
</header>
<main>
  <div class="column">
    <div id="paused"></div>
    <section class="card"><h2>Waiting for you <span class="count" id="you-n"></span></h2><div id="you"></div></section>
    <section class="card"><h2>Working now <span class="count" id="agents-n"></span></h2><div id="agents" class="runs"></div></section>
    <section class="card"><h2>Queue <span class="count" id="queue-n"></span></h2><div id="queue"></div></section>
    <section class="card"><h2>Recent runs <span class="count" id="recent-n"></span></h2><div id="recent" class="runs"></div></section>
    <section class="card" id="problems-card" hidden><h2>Problems <span class="count bad" id="problems-n"></span></h2><div id="problems"></div></section>
  </div>
  <section class="card side"><h2 class="logtitle" id="logtitle">Log</h2><pre id="log" class="idle">Click a run to see its log.</pre></section>
</main>
<script>
const $ = id => document.getElementById(id);
let chosen = null, repo = "", logText = null;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const link = n => n == null ? "" : repo
  ? `<a href="https://github.com/${esc(repo)}/issues/${esc(n)}" target="_blank" rel="noopener">#${esc(n)}</a>` : `#${esc(n)}`;
const time = s => s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h ${Math.floor(s % 3600 / 60)}m`;
function when(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return String(iso);
  const hm = d.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
  return d.toDateString() === new Date().toDateString() ? `today, ${hm}` : `${d.toLocaleDateString([], {day: "numeric", month: "short"})}, ${hm}`;
}

// Pills in the style of GitHub labels; the colours of roles and stages follow the team's labels.
const COLOURS = {green: "#1a7f37", amber: "#9a6700", red: "#cf222e", orange: "#bc4c00", blue: "#0969da",
  purple: "#8250df", teal: "#1b7c83", pink: "#bf3989", grey: "#6e7781"};
const TONE = {
  ready: "green", approve: "green", done: "green", stuck: "red", error: "red", "needs-human": "orange",
  changes: "amber", wait: "amber", blocked: "amber", running: "blue", split: "pink",
  triage: "teal", "project-manager": "teal", develop: "blue", developer: "blue",
  review: "purple", reviewer: "purple", ops: "green", operator: "green",
};
const colour = word => COLOURS[TONE[word]] || COLOURS.grey;
const pill = (text, hex, kind = "") => `<span class="pill ${kind}" style="--c:${hex}">${esc(text)}</span>`;
const status = s => pill(s, colour(s), s === "running" ? "status working" : "status");
const model = m => !m ? "" : pill(String(m).replace(/^claude-/, "").replace(/-(\d+)-(\d+)(-\d{8})?$/, " $1.$2"),
  COLOURS[/opus/.test(m) ? "purple" : /sonnet/.test(m) ? "orange" : /haiku/.test(m) ? "teal" : "grey"], "model");
const roleName = r => String(r || "").split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

function card(run, inner) {
  return `<article class="run${run.agent === chosen ? " chosen" : ""}" data-run="${esc(run.agent)}" tabindex="0" style="--role:${colour(run.role)}">${inner}</article>`;
}
const working = a => card(a,
  `<div class="head"><span class="role">${esc(roleName(a.role))}</span>${link(a.issue)}<span class="task">${esc(a.title)}</span>
   <span class="pills">${pill(a.stage, colour(a.stage))}${model(a.model)}${pill(`working ${time(a.seconds)}`, COLOURS.blue, "status working")}</span></div>
   <div class="step" title="${esc(a.last)}">${esc(a.last || "starting…")}</div>`);
const ran = r => card(r,
  `<div class="head"><span class="role">${esc(r.role ? roleName(r.role) : r.agent)}</span>
   ${r.started ? `<span class="when" title="${esc(r.agent)}">started at ${esc(when(r.started))}</span>` : ""}${link(r.issue)}
   <span class="pills">${model(r.model)}${status(r.status)}</span></div>
   ${r.title ? `<h3>${esc(r.title)}</h3>` : ""}
   ${r.html ? `<div class="md">${r.html}</div>` : r.last ? `<div class="step" title="${esc(r.last)}">${esc(r.last)}</div>` : ""}`);

const drawn = new WeakMap();  // a card -> the HTML it was drawn from
function cards(id, items, draw, empty) {
  // Redraw only the cards that changed, so a summary keeps its scroll and a selection stays.
  const box = $(id), old = new Map([...box.children].map(e => [e.dataset.run, e]));
  if (!items.length) { box.innerHTML = `<p class="empty">${empty}</p>`; return; }
  items.forEach((item, i) => {
    const html = draw(item);
    let el = old.get(item.agent);
    old.delete(item.agent);
    if (!el || drawn.get(el) !== html) {
      const t = document.createElement("template");
      t.innerHTML = html;
      const fresh = t.content.firstElementChild;
      drawn.set(fresh, html);
      if (el) el.replaceWith(fresh);
      el = fresh;
    }
    if (box.children[i] !== el) box.insertBefore(el, box.children[i] || null);
  });
  old.forEach(e => e.remove());
}
const shown = {};
function put(id, html) { if (shown[id] !== html) $(id).innerHTML = shown[id] = html; }
function table(id, items, row, empty) {
  put(id, items.length ? `<table><tbody>${items.map(row).join("")}</tbody></table>` : `<p class="empty">${empty}</p>`);
}
function count(id, n, hot = false) { const el = $(id); el.textContent = n; el.classList.toggle("hot", hot && n > 0); }

async function refresh() {
  let state;
  try {
    state = await (await fetch("/state.json", {cache: "no-store"})).json();
  } catch (error) {
    $("dot").classList.add("off");
    $("updated").textContent = "can't reach the team: is it running?";
    return;
  }
  repo = state.repo;
  $("dot").classList.remove("off");
  $("updated").textContent = `updated ${new Date().toLocaleTimeString()}`;
  if (repo) put("repo", `Bots for LinkedIn's daily puzzles, and the agents that build them · <a href="https://github.com/${esc(repo)}" target="_blank" rel="noopener">${esc(repo)}</a>`);
  put("paused", state.paused_until ? `<p class="banner">⏸ Paused by Claude's usage limit until <b>${esc(when(state.paused_until))}</b>.</p>` : "");
  table("you", state.waiting_for_you, w => `<tr><td class="narrow">${link(w.issue)}</td><td>${esc(w.title)}</td><td class="end">${
    w.reason === "ready" ? pill("ready to merge: review the PR", COLOURS.green, "status") : pill("needs your decision", COLOURS.orange, "status")}</td></tr>`, "Nothing waits for you.");
  cards("agents", state.agents, working, "No agent is working.");
  table("queue", state.queue, q => `<tr><td class="narrow">${link(q.issue)}</td><td>${esc(q.title)}</td><td class="end">${pill(q.stage, colour(q.stage))}</td></tr>`, "Empty.");
  cards("recent", state.recent, ran, "None yet.");
  count("you-n", state.waiting_for_you.length, true); count("agents-n", state.agents.length);
  count("queue-n", state.queue.length); count("recent-n", state.recent.length);
  const problems = state.errors || [];  // the orchestrator's latest, newest last
  $("problems-card").hidden = !problems.length;
  count("problems-n", problems.length);
  put("problems", problems.slice().reverse().map(p => `<div class="problem">${esc(p)}</div>`).join(""));
  if (chosen) await showLog();
}

const KINDS = [["💬", "l-say"], ["▶", "l-tool"], ["  ↳", "l-out"], ["■", "l-end"], ["⏸", "l-wait"], ["started", "l-start"]];
async function showLog() {
  const response = await fetch(`/log/${encodeURIComponent(chosen)}`, {cache: "no-store"});
  const text = response.ok ? await response.text() : "No log yet.";
  if (text === logText) return;
  const log = $("log"), atEnd = logText === null || log.scrollTop + log.clientHeight >= log.scrollHeight - 20;
  log.innerHTML = text.split("\n").map(line => `<span class="${(KINDS.find(([p]) => line.startsWith(p)) || ["", ""])[1]}">${esc(line)}</span>`).join("\n");
  log.classList.remove("idle");
  logText = text;
  if (atEnd) log.scrollTop = log.scrollHeight;
}
function choose(run) {
  chosen = run;
  logText = null;
  $("logtitle").innerHTML = `Log <span class="name">${esc(run)}</span> <a href="/prompt/${encodeURIComponent(run)}" target="_blank" rel="noopener">its prompt ↗</a>`;
  refresh();
}
document.addEventListener("click", e => {
  const run = e.target.closest("[data-run]");
  if (run && !e.target.closest("a") && !String(getSelection())) choose(run.dataset.run);  // selecting text isn't choosing
});
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target.dataset && e.target.dataset.run) choose(e.target.dataset.run);
});
refresh(); setInterval(refresh, 2000);
</script></body></html>
"""
