"""Starting agents: each run is the unmodified `claude` CLI in headless mode,
in its task's git worktree, with its role's model and permissions, streaming
its work to a log file and ending with a verdict."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

from .model import Failed, Job, Outcome, UsageLimited, Verdict
from .roles import BY_NAME, Role

# The owner wants no Claude attribution on commits or PRs.
SETTINGS = {"attribution": {"commit": "", "pr": ""}, "includeCoAuthoredBy": False}
LIMIT_TEXT = re.compile(r"usage limit|limit reached|rate limit", re.IGNORECASE)


def command(job: Job, role: Role, claude: str = "claude") -> list[str]:
    """The command line of one run; the prompt goes to its standard input."""
    argv = [
        claude, "-p",
        "--output-format", "stream-json", "--verbose",
        "--model", role.model,
        "--permission-mode", "dontAsk",
        "--json-schema", json.dumps(role.schema),
        "--settings", json.dumps(SETTINGS),
        "--name", f"{role.name} #{job.issue}",
    ]  # fmt: skip
    argv += ["--resume", job.session] if job.resume else ["--session-id", job.session]
    if role.allowed:
        argv += ["--allowedTools", *role.allowed]  # last: it takes every argument up to the next option
    return argv


def outcome(lines: Iterable[str], exit_code: int | None) -> Outcome:
    """What a finished run's stream-json output amounts to."""
    result, resets = None, None
    for line in lines:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("type") == "rate_limit_event":
            info = message.get("rate_limit_info", {})
            if info.get("status") == "rejected":
                resets = info.get("resetsAt")
        elif message.get("type") == "result":
            result = message
    if result and not result.get("is_error") and isinstance(result.get("structured_output"), dict):
        return Verdict(result["structured_output"])
    text = str(result.get("result") or result.get("subtype")) if result else ""
    if resets is not None or LIMIT_TEXT.search(text):
        return UsageLimited(datetime.fromtimestamp(resets) if resets else datetime.now() + timedelta(hours=1))
    if result is None:
        return Failed(f"claude exited with {exit_code} before finishing")
    return Failed(text if result.get("is_error") else "it ended without a verdict")


class ClaudeAgents:
    """Runs agents as `claude` processes: one git worktree per task, one log per run."""

    def __init__(self, repo: Path, worktrees: Path, logs: Path, env: dict[str, str], claude: str | None = None) -> None:
        self.repo, self.worktrees, self.logs = repo, worktrees, logs
        self.env = env
        self.claude = claude or shutil.which("claude") or "claude"
        self.runs: dict[str, subprocess.Popen[bytes]] = {}

    def start(self, job: Job) -> str:
        role = BY_NAME[job.role]
        agent = f"{datetime.now():%Y%m%d-%H%M%S}-{job.role}-{job.issue}"
        self.logs.mkdir(parents=True, exist_ok=True)
        prompt = self.logs / f"{agent}.prompt.md"
        prompt.write_text(job.prompt, encoding="utf-8")
        cwd = self.worktree(job.issue, job.branch) if job.branch else self.main()
        with prompt.open("rb") as stdin, self.log(agent).open("wb") as stdout, (self.logs / f"{agent}.err").open("wb") as stderr:
            self.runs[agent] = subprocess.Popen(command(job, role, self.claude), cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr, env=self.env)
        return agent

    def poll(self, agent: str) -> Outcome | None:
        run = self.runs.get(agent)
        if run is None:
            return Failed("the orchestrator lost track of this run")
        code = run.poll()
        if code is None:
            return None
        del self.runs[agent]
        lines = self.log(agent).read_text(encoding="utf-8", errors="replace").splitlines()
        result = outcome(lines, code)
        if isinstance(result, Failed) and not lines:
            error = (self.logs / f"{agent}.err").read_text(encoding="utf-8", errors="replace").strip()
            result = Failed(f"{result.reason}: {error[-300:]}" if error else result.reason)
        return result

    def stop(self, agent: str) -> None:
        run = self.runs.pop(agent, None)
        if run is None or run.poll() is not None:
            return
        if os.name == "nt":  # claude starts children of its own; end the whole tree
            subprocess.run(["taskkill", "/PID", str(run.pid), "/T", "/F"], capture_output=True)
        else:
            run.kill()

    def clean_up(self, issue: int) -> None:
        path = self.worktrees / str(issue)
        if path.exists():
            self._git("worktree", "remove", "--force", str(path))
        self._git("worktree", "prune")

    def log(self, agent: str) -> Path:
        return self.logs / f"{agent}.jsonl"

    def worktree(self, issue: int, branch: str) -> Path:
        """The task's worktree on its branch: made from the branch on GitHub if
        it's there, else from main. Later runs on the task reuse it."""
        path = self.worktrees / str(issue)
        if path.exists():
            return path
        self._git("fetch", "origin")
        on_github = self._git("ls-remote", "--heads", "origin", branch).stdout.strip()
        self._git("worktree", "add", "-B", branch, str(path), f"origin/{branch}" if on_github else "origin/main")
        return path

    def main(self) -> Path:
        """A read-only checkout of main as it is on GitHub, for roles without a
        branch of their own: never the owner's working copy."""
        path = self.worktrees / "main"
        self._git("fetch", "origin")
        if path.exists():
            subprocess.run(["git", "-C", str(path), "checkout", "--detach", "--force", "origin/main"], capture_output=True, env=self.env, check=True)
        else:
            self._git("worktree", "add", "--detach", str(path), "origin/main")
        return path

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, env=self.env, check=True)
