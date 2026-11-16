"""uv run python -m team run | stop | labels

run     the orchestrator, with its board on http://127.0.0.1:8765
stop    stop a running orchestrator and its agents
labels  create the team's labels on GitHub (once)

The team bot's account comes from ~/.linkedin-games/team.env:
    GH_TOKEN=...          the bot's token (classic, repo and workflow scopes)
    TEAM_BOT=...          the bot's login
    TEAM_BOT_EMAIL=...    its email, for commits
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

from .agents import ClaudeAgents
from .board import serve
from .github import GhGitHub, gh
from .orchestrator import Orchestrator
from .roles import BY_NAME

HOME = Path.home() / ".linkedin-games"
ENV_FILE = HOME / "team.env"
LOGS = HOME / "team" / "logs"
JOURNAL = HOME / "team" / "orchestrator.log"
REPO_DIR = Path(__file__).resolve().parent.parent
ROLE_TEXTS = Path(__file__).resolve().parent / "roles"
PORT = 8765

LABELS = {
    "stage:triage": ("c5def5", "The Project Manager decides what this is"),
    "stage:develop": ("1d76db", "The Developer works on it"),
    "stage:review": ("5319e7", "The Reviewer judges the PR"),
    "stage:ops": ("0e8a16", "The Operator gets it ready to merge"),
    "stage:ready": ("fbca04", "Waits for the owner's approval"),
    "needs-human": ("d93f0b", "Waits for the owner's decision"),
    "kind:incident": ("b60205", "A built game or the team broke"),
    "kind:new-game": ("0052cc", "A new game on LinkedIn"),
    "declined": ("cccccc", "A knowledge game: not built"),
}


def settings() -> dict[str, str]:
    """team.env on top of the environment, plus the bot's identity for git."""
    env = dict(os.environ)
    if not ENV_FILE.exists():
        sys.exit(f"Missing {ENV_FILE}: see `python -m team --help`.")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    missing = [key for key in ("GH_TOKEN", "TEAM_BOT", "TEAM_BOT_EMAIL") if not env.get(key)]
    if missing:
        sys.exit(f"{ENV_FILE} lacks {', '.join(missing)}.")
    bot, email = env["TEAM_BOT"], env["TEAM_BOT_EMAIL"]
    env.update(GIT_AUTHOR_NAME=bot, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME=bot, GIT_COMMITTER_EMAIL=email)
    # git pushes as the bot too: drop the owner's credential helpers, ask gh (which reads GH_TOKEN)
    env.update(
        GIT_CONFIG_COUNT="2",
        GIT_CONFIG_KEY_0="credential.helper", GIT_CONFIG_VALUE_0="",
        GIT_CONFIG_KEY_1="credential.helper", GIT_CONFIG_VALUE_1="!gh auth git-credential",
    )  # fmt: skip
    return env


def repo_name() -> str:
    url = subprocess.run(["git", "-C", str(REPO_DIR), "remote", "get-url", "origin"], capture_output=True, text=True, check=True).stdout
    found = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?\s*$", url)
    if not found:
        sys.exit(f"origin is not a GitHub repository: {url.strip()}")
    return found.group(1)


def prompts() -> dict[str, str]:
    shared = (ROLE_TEXTS / "conventions.md").read_text(encoding="utf-8")
    return {name: shared + "\n\n" + (ROLE_TEXTS / f"{name}.md").read_text(encoding="utf-8") for name in BY_NAME}


def say(text: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {text}"
    print(line, flush=True)
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("a", encoding="utf-8") as journal:
        print(line, file=journal)


def run(interval: float, port: int) -> None:
    env, repo = settings(), repo_name()
    owner = repo.split("/")[0]
    github = GhGitHub(repo, gh(env), owner=owner)
    agents = ClaudeAgents(REPO_DIR, REPO_DIR.parent / f"{REPO_DIR.name}-team", LOGS, env)
    team = Orchestrator(github, agents, owner=owner, bot=env["TEAM_BOT"], prompts=prompts())
    lock, stopping = threading.Lock(), threading.Event()

    def snapshot() -> dict:
        with lock:
            return team.snapshot(datetime.now())

    server = serve(snapshot, LOGS, port, repo, on_stop=stopping.set)
    say(f"The team works on {repo} as {env['TEAM_BOT']}. Board: http://127.0.0.1:{port}")
    errors = 0
    try:
        while not stopping.is_set():
            with lock:
                try:
                    team.tick(datetime.now())
                except Exception as error:  # GitHub unreachable, say: try again next tick
                    say(f"tick failed: {error}")
                for message in team.errors[errors:]:
                    say(message)
                errors = len(team.errors)
            stopping.wait(interval)
    except KeyboardInterrupt:
        pass
    finally:
        say("Stopping the agents.")
        with lock:
            team.stop()
        server.shutdown()


def stop(port: int) -> None:
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/stop", method="POST"), timeout=5)
        print("The team is stopping.")
    except OSError:
        print("No team is running.")


def labels() -> None:
    env, repo = settings(), repo_name()
    run_gh = gh(env)
    for name, (color, description) in LABELS.items():
        run_gh(["label", "create", name, "--color", color, "--description", description, "--force", "--repo", repo])
        print(f"label {name}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m team", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("run", "stop", "labels"))
    parser.add_argument("--interval", type=float, default=60, help="seconds between looks at GitHub (default 60)")
    parser.add_argument("--port", type=int, default=PORT, help=f"the board's port (default {PORT})")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")  # a hidden console may not take every character
    if args.command == "run":
        run(args.interval, args.port)
    elif args.command == "stop":
        stop(args.port)
    else:
        labels()


if __name__ == "__main__":
    main()
