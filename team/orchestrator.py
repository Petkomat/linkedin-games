"""The orchestrator: reads the tasks from GitHub, starts the agent each one
needs, and moves a task to its next stage when its agent is done.

Routing is fixed here; agents use judgement only inside their own stage.
GitHub is the only state: the stage is a label, and everything the routing
needs to remember (failed runs, reviews, branches, sessions) is in the team
bot's comments, as a hidden marker after the readable text.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any, Protocol

from .model import (
    BLOCKED,
    DECLINED,
    DEVELOP,
    INCIDENT,
    NEEDS_HUMAN,
    NEW_GAME,
    OPS,
    READY,
    REVIEW,
    SPLIT,
    STAGE,
    TRIAGE,
    Comment,
    Failed,
    Issue,
    Job,
    Outcome,
    PullRequest,
    Running,
    UsageLimited,
    Verdict,
)
from .roles import BY_NAME, MAX_FOUND, MAX_PARTS, ROLES, Role


class GitHub(Protocol):
    def open_issues(self) -> list[Issue]: ...
    def comments_on(self, number: int) -> list[Comment]: ...
    def comment(self, number: int, body: str) -> None: ...
    def add_labels(self, number: int, labels: set[str]) -> None: ...
    def remove_labels(self, number: int, labels: set[str]) -> None: ...
    def close(self, number: int, not_planned: bool = False) -> None: ...
    def assign(self, number: int, login: str) -> None: ...
    def create_issue(self, title: str, body: str, labels: set[str]) -> int: ...
    def add_sub_issue(self, parent: int, child: int) -> None: ...
    def pull_request(self, branch: str) -> PullRequest | None: ...
    def open_pull_request(self, branch: str, title: str, body: str) -> PullRequest: ...
    def reviews_on(self, pr: int) -> list[Comment]: ...
    def review(self, pr: int, body: str) -> None: ...
    def request_review(self, pr: int, user: str) -> None: ...
    def merge(self, pr: int) -> None: ...


class Agents(Protocol):
    def start(self, job: Job) -> str: ...
    def poll(self, agent: str) -> Outcome | None: ...
    def stop(self, agent: str) -> None: ...
    def clean_up(self, issue: int) -> None: ...


ACTIONS_BOT = ("github-actions[bot]", "app/github-actions")  # how GitHub names the daily workflow
MARKER = re.compile(r"<!-- team (\{.*?\}) -->")
MAX_REVIEWS = 3
PARAGRAPH = "\n\n"


class Orchestrator:
    def __init__(self, github: GitHub, agents: Agents, owner: str, bot: str, prompts: dict[str, str] | None = None) -> None:
        self.github, self.agents = github, agents
        self.owner, self.bot = owner, bot
        self.trusted = {owner, bot, *ACTIONS_BOT}
        self.prompts = prompts if prompts is not None else {}
        self.running: dict[int, Running] = {}  # by issue number
        self.paused_until: datetime | None = None  # Claude's usage limit
        self.tasks: list[Issue] = []  # as of the last tick, for the board
        self.errors: list[str] = []  # the latest problems, for the board

    def tick(self, now: datetime) -> None:
        self._collect(now)
        try:
            self._route(now)
        finally:
            self.tasks = sorted(self._tasks(), key=_priority)

    def stop(self) -> None:
        """Stop every agent; their tasks start over when the team runs again."""
        for run in self.running.values():
            self.agents.stop(run.agent)
        self.running.clear()

    def snapshot(self, now: datetime) -> dict[str, Any]:
        """Who works on what, what waits for the owner, and what waits for a free agent."""
        agents = [
            {
                "agent": run.agent,
                "role": run.job.role,
                "issue": number,
                "title": run.job.title,
                "stage": run.stage,
                "branch": run.job.branch,
                "seconds": int((now - run.started).total_seconds()),
            }
            for number, run in self.running.items()
        ]
        waiting = [
            {"issue": t.number, "title": t.title, "reason": NEEDS_HUMAN if NEEDS_HUMAN in t.labels else READY}
            for t in self.tasks
            if NEEDS_HUMAN in t.labels or t.stage == READY
        ]
        queue = [
            {"issue": t.number, "title": t.title, "stage": BLOCKED if BLOCKED in t.labels else t.stage}
            for t in self.tasks
            if t.stage in ROLES and NEEDS_HUMAN not in t.labels and t.number not in self.running
        ]
        paused = self.paused_until.isoformat() if self.paused_until and now < self.paused_until else None
        return {"agents": agents, "waiting_for_you": waiting, "queue": queue, "paused_until": paused, "errors": self.errors[-10:]}

    def _route(self, now: datetime) -> None:
        for issue in self._tasks():
            if issue.stage is None and NEEDS_HUMAN not in issue.labels:
                self._guarded(issue.number, self.github.add_labels, issue.number, {STAGE + TRIAGE})
            elif issue.stage == READY and NEEDS_HUMAN not in issue.labels:
                self._guarded(issue.number, self._await_owner, issue)
            elif issue.stage == SPLIT and NEEDS_HUMAN not in issue.labels:
                self._guarded(issue.number, self._follow_parts, issue)
        if self.paused_until and now < self.paused_until:
            return
        for issue in sorted(self._tasks(), key=_priority):
            role = ROLES.get(issue.stage or "")
            if role is None or {NEEDS_HUMAN, BLOCKED} & issue.labels or issue.number in self.running:
                continue
            if sum(1 for run in self.running.values() if run.job.role == role.name) < role.slots:
                self._guarded(issue.number, self._start, role, issue, now)

    def _guarded(self, number: int, action: Any, *args: Any) -> None:
        """Do one task's step; if GitHub or git fails, note it and go on with
        the other tasks. The step is tried again next tick."""
        try:
            action(*args)
        except Exception as error:
            self.errors.append(f"{datetime.now():%H:%M:%S} #{number}: {error}")
            del self.errors[:-50]

    # Reading GitHub.

    def _tasks(self) -> list[Issue]:
        return [issue for issue in self.github.open_issues() if issue.author in self.trusted]

    def _task(self, number: int) -> Issue | None:
        return next((issue for issue in self._tasks() if issue.number == number), None)

    def _events(self, number: int) -> list[dict[str, Any]]:
        """What the team bot wrote down about a task, oldest first."""
        return [
            {**json.loads(m), "at": c.created}
            for c in self.github.comments_on(number)
            if c.author == self.bot
            for m in MARKER.findall(c.body)
        ]

    def _branch(self, issue: Issue) -> str:
        recorded = [e["branch"] for e in self._events(issue.number) if "branch" in e]
        if recorded:
            return recorded[0]
        slug = re.sub(r"[^a-z0-9]+", "-", issue.title.lower()).strip("-")[:40].rstrip("-")
        return f"team/{issue.number}-{slug}"

    # Starting and collecting agents.

    def _start(self, role: Role, issue: Issue, now: datetime) -> None:
        branch = self._branch(issue) if role.worktree else None
        sessions = [e["session"] for e in self._events(issue.number) if e.get("role") == role.name and "session" in e]
        session, resume = (sessions[-1], True) if sessions else (str(uuid.uuid4()), False)
        job = Job(role.name, issue.number, issue.title, self._prompt(role, issue, branch), branch, session, resume)
        self.running[issue.number] = Running(self.agents.start(job), job, issue.stage or "", now)
        if not issue.assignees:  # the team does the work, so it's the assignee; never instead of a person
            self._guarded(issue.number, self.github.assign, issue.number, self.bot)

    def _prompt(self, role: Role, issue: Issue, branch: str | None) -> str:
        """The role's instructions, then the task as trusted people wrote it.
        Nothing written by anyone else reaches an agent."""
        parts = [self.prompts.get(role.name, ""), f"# Your task: issue #{issue.number}, {issue.title}"]
        if branch:
            parts.append(f"Your working directory is a git worktree of the branch `{branch}`.")
        if role.stage == REVIEW:
            done = sum(1 for e in self._events(issue.number) if e.get("role") == "reviewer")
            parts.append(f"This is review {done + 1} of {MAX_REVIEWS}.")
        if role.stage == TRIAGE:
            others = [f"- #{t.number} {t.title} ({', '.join(sorted(t.labels))})" for t in self._tasks() if t.number != issue.number]
            parts.append("## The other open tasks" + PARAGRAPH + ("\n".join(others) or "(none)"))
        parts.append("## The issue" + PARAGRAPH + (issue.body.strip() or "(no description)"))
        said = [c for c in self.github.comments_on(issue.number) if c.author in self.trusted]
        if said:
            parts.append("## Comments on the issue, oldest first" + PARAGRAPH + PARAGRAPH.join(_quote(c) for c in said))
        pr = self.github.pull_request(branch) if branch else None
        if pr:
            parts.append(f"## Its PR: #{pr.number}, {pr.url}")
            reviews = [c for c in self.github.reviews_on(pr.number) if c.author in self.trusted]
            if pr.owner_review_body:
                reviews.append(Comment(self.owner, pr.owner_review_body, issue.updated))
            if reviews:
                parts.append("## Reviews and comments on the PR, oldest first" + PARAGRAPH + PARAGRAPH.join(_quote(c) for c in reviews))
        return PARAGRAPH.join(part for part in parts if part)

    def _collect(self, now: datetime) -> None:
        for number, run in list(self.running.items()):
            outcome = self.agents.poll(run.agent)
            timeout = ROLES[run.stage].timeout
            if outcome is None and now - run.started > timeout:
                self.agents.stop(run.agent)
                outcome = Failed(f"timed out after {timeout}")
            if outcome is None:
                continue
            del self.running[number]
            issue = self._task(number)
            if issue is None or issue.stage != run.stage:
                continue  # closed or moved by the owner meanwhile
            self._guarded(number, self._apply, run, issue, outcome)

    def _apply(self, run: Running, issue: Issue, outcome: Outcome) -> None:
        if isinstance(outcome, Verdict):
            role = BY_NAME[run.job.role]
            if outcome.data.get(role.key) not in role.answers:
                self._failed(run, issue, f"it answered {json.dumps(outcome.data)[:200]}, which isn't a verdict")
                return
            handle = {
                "project-manager": self._triage,
                "developer": self._developed,
                "reviewer": self._reviewed,
                "operator": self._operated,
            }[run.job.role]
            handle(run, issue, outcome.data)
            self._file_found(run, issue, outcome.data.get("found"))
        elif isinstance(outcome, UsageLimited):
            self.paused_until = max(outcome.until, self.paused_until or outcome.until)
        else:
            self._failed(run, issue, outcome.reason)

    def _file_found(self, run: Running, issue: Issue, found: Any) -> None:
        """What an agent noticed outside its task becomes a task of its own,
        which waits for the owner: at most MAX_FOUND a run, and none twice."""
        items = [item for item in found or [] if isinstance(item, dict) and str(item.get("title", "")).strip()]
        known = {task.title.strip().lower() for task in self._tasks()}
        who = run.job.role.replace("-", " ").title()
        for item in items[:MAX_FOUND]:
            title = str(item["title"]).strip()
            if title.lower() in known:
                continue
            body = PARAGRAPH.join((
                f"@{self.owner} The {who} found this while working on #{issue.number}.",
                str(item.get("body", "")).strip(),
                f"Remove the `{NEEDS_HUMAN}` label to let the team work on it, or close it.",
            ))  # fmt: skip
            self.github.create_issue(title, body, {NEEDS_HUMAN})
            known.add(title.lower())

    def _failed(self, run: Running, issue: Issue, reason: str) -> None:
        """A run that crashed or timed out is tried once more; after the second
        failure in a row the owner decides."""
        earlier = 0
        for event in reversed(self._events(issue.number)):
            if event.get("role") != run.job.role or "failed" not in event:
                break
            earlier += 1
        event = {"role": run.job.role, "failed": reason[:300]}
        text = f"The {run.job.role.replace('-', ' ')} run failed: {reason}"
        if earlier >= 1:
            self._ask_owner(issue, f"{text}. It failed twice in a row.", event)
        else:
            self._record(issue.number, f"{text}. Trying once more.", event)

    # What each role's verdict means.

    def _triage(self, run: Running, issue: Issue, verdict: dict[str, Any]) -> None:
        decision, note = verdict.get("decision"), verdict.get("comment", "")
        event = {"role": "project-manager", "decision": decision}
        if decision in (DEVELOP, OPS):
            self._move(issue, decision, note, {**event, "branch": self._branch(issue)})
        elif decision == SPLIT:
            self._split(issue, note, verdict.get("parts"), event)
        elif decision == DECLINED:
            self._record(issue.number, note, event)
            self._set_stage(issue, None)
            self.github.add_labels(issue.number, {DECLINED})
            self.github.close(issue.number, not_planned=True)
        elif decision == NEEDS_HUMAN:
            self._ask_owner(issue, note, event)
        else:  # done: nothing to do
            self._record(issue.number, note, {**event, "stage": "done"})
            self._set_stage(issue, None)
            self.github.close(issue.number)

    def _split(self, issue: Issue, note: str, parts: Any, event: dict[str, Any]) -> None:
        """A task too large for one PR becomes its parts, in order: the plan is
        written down on the task, and the parts are filed from it."""
        parts = [p for p in parts or [] if isinstance(p, dict) and str(p.get("title", "")).strip() and p.get("stage") in (DEVELOP, OPS)]
        plan = "\n".join(f"{k}. {part['title']}" for k, part in enumerate(parts, 1))
        if not 2 <= len(parts) <= MAX_PARTS:
            text = f"The Project Manager would split this into {len(parts)} parts, but a split has 2 to {MAX_PARTS}."
            self._ask_owner(issue, PARAGRAPH.join(t for t in (text, plan, note) if t), event)
            return
        plan_text = f"Split into {len(parts)} parts, done one at a time:" + PARAGRAPH + plan
        self._record(issue.number, PARAGRAPH.join(t for t in (note, plan_text) if t), {**event, "stage": SPLIT, "plan": parts})
        self._set_stage(issue, SPLIT)
        self._follow_parts(issue)

    def _follow_parts(self, task: Issue) -> None:
        """File a split task's parts as its sub-issues, let each start once
        every part before it is closed, and close the task after the last."""
        events = self._events(task.number)
        plans = [e["plan"] for e in events if "plan" in e]
        if not plans:
            return
        plan, filed = plans[-1], [e["issue"] for e in events if "part" in e]
        kinds = task.labels & {INCIDENT, NEW_GAME}
        while len(filed) < len(plan):  # one at a time, written down, so a crash files no part twice
            k, part = len(filed) + 1, plan[len(filed)]
            after = f" It starts once #{filed[-1]} is closed." if filed else ""
            body = str(part.get("body", "")).strip() + PARAGRAPH + f"Part {k} of {len(plan)} of #{task.number}.{after}"
            number = self.github.create_issue(part["title"], body, {STAGE + part["stage"], *kinds, *({BLOCKED} if filed else ())})
            self._guarded(task.number, self.github.add_sub_issue, task.number, number)
            self._record(task.number, f"Part {k} of {len(plan)}: #{number}.", {"part": k, "issue": number})
            filed.append(number)
        still_open = {t.number: t for t in self._tasks()}
        waiting = [number for number in filed if number in still_open]
        if not waiting:
            self._record(task.number, f"All {len(filed)} parts are closed. Done.", {"stage": "done"})
            self._set_stage(task, None)
            self.github.close(task.number)
        elif BLOCKED in still_open[waiting[0]].labels:
            self.github.remove_labels(waiting[0], {BLOCKED})

    def _developed(self, run: Running, issue: Issue, verdict: dict[str, Any]) -> None:
        summary = verdict.get("summary", "")
        event = {"role": "developer", "status": verdict.get("status"), "session": run.job.session}
        if verdict.get("status") != "ready":
            self._ask_owner(issue, f"The Developer is stuck: {summary}", event)
            return
        branch = run.job.branch or self._branch(issue)
        pr = self.github.pull_request(branch)
        if pr is None:
            title = verdict.get("title") or issue.title
            pr = self.github.open_pull_request(branch, title, summary + PARAGRAPH + f"Closes #{issue.number}")
        self._move(issue, REVIEW, f"The Developer is done: {summary}" + PARAGRAPH + f"Ready for review in #{pr.number}.", event)

    def _reviewed(self, run: Running, issue: Issue, verdict: dict[str, Any]) -> None:
        approved = verdict.get("decision") == "approve"
        count = 1 + sum(1 for e in self._events(issue.number) if e.get("role") == "reviewer")
        pr = self.github.pull_request(run.job.branch or self._branch(issue))
        heading = f"**Review {count} of {MAX_REVIEWS}: {'approved' if approved else 'changes requested'}**"
        if pr:
            self.github.review(pr.number, heading + PARAGRAPH + verdict.get("review", ""))
        event = {"role": "reviewer", "decision": verdict.get("decision"), "review": count}
        where = f" (#{pr.number})" if pr else ""
        if approved:
            self._move(issue, OPS, f"{heading}{where}. On to the Operator.", event)
        elif count >= MAX_REVIEWS:
            self._ask_owner(issue, f"{heading}{where}, the last of {MAX_REVIEWS}. Please decide how to go on.", event)
        else:
            self._move(issue, DEVELOP, f"{heading}{where}. Back to the Developer.", event)

    def _operated(self, run: Running, issue: Issue, verdict: dict[str, Any]) -> None:
        status, summary = verdict.get("status"), verdict.get("summary", "")
        event = {"role": "operator", "status": status}
        if status == "developer":
            self._move(issue, DEVELOP, f"The Operator sends this back to the Developer: {summary}", event)
        elif status != "ready":
            self._ask_owner(issue, f"The Operator is stuck: {summary}", event)
        else:
            branch = run.job.branch or self._branch(issue)
            pr = self.github.pull_request(branch) or self.github.open_pull_request(
                branch, verdict.get("title") or issue.title, summary + PARAGRAPH + f"Closes #{issue.number}"
            )
            self._move(issue, READY, f"The Operator is done: {summary}" + PARAGRAPH + f"#{pr.number} is ready to merge once @{self.owner} approves it.", event)
            self.github.request_review(pr.number, self.owner)

    def _await_owner(self, issue: Issue) -> None:
        """A ready PR merges once the owner approves it, and goes back to the
        Developer if the owner asks for changes. Only reviews given after the
        PR became ready count."""
        pr = self.github.pull_request(self._branch(issue))
        ready = [e["at"] for e in self._events(issue.number) if e.get("stage") == READY]
        if pr is None or pr.owner_review_at is None or (ready and pr.owner_review_at <= ready[-1]):
            return
        event = {"role": "owner", "decision": pr.owner_review}
        if pr.owner_review == "CHANGES_REQUESTED":
            self._move(issue, DEVELOP, f"@{self.owner} asked for changes in #{pr.number}. Back to the Developer.", event)
        elif pr.owner_review == "APPROVED":
            try:
                self.github.merge(pr.number)
            except Exception as error:  # a red check, a conflict: the owner decides
                self._ask_owner(issue, f"Merging #{pr.number} failed: {error}", event)
                return
            self._record(issue.number, f"Merged #{pr.number}. Done.", {**event, "stage": "done"})
            self._set_stage(issue, None)
            self.github.close(issue.number)
            self.agents.clean_up(issue.number)

    # Writing GitHub.

    def _record(self, number: int, text: str, event: dict[str, Any]) -> None:
        marker = json.dumps(event, ensure_ascii=True).replace(">", "\\u003e")  # JSON's own escape
        self.github.comment(number, text + PARAGRAPH + f"<!-- team {marker} -->")

    def _set_stage(self, issue: Issue, stage: str | None) -> None:
        old = {label for label in issue.labels if label.startswith(STAGE)}
        new = {STAGE + stage} if stage else set()
        if old - new:
            self.github.remove_labels(issue.number, old - new)
        if new - old:
            self.github.add_labels(issue.number, new - old)

    def _move(self, issue: Issue, stage: str, text: str, event: dict[str, Any]) -> None:
        self._record(issue.number, text, {**event, "stage": stage})
        self._set_stage(issue, stage)

    def _ask_owner(self, issue: Issue, text: str, event: dict[str, Any]) -> None:
        how = f"Answer in a comment here, then remove the `{NEEDS_HUMAN}` label to let the team go on."
        self._record(issue.number, f"@{self.owner} {text}" + PARAGRAPH + how, {**event, "stage": NEEDS_HUMAN})
        self.github.add_labels(issue.number, {NEEDS_HUMAN})


def _quote(comment: Comment) -> str:
    text = MARKER.sub("", comment.body).strip()
    return f"**{comment.author}** ({comment.created:%Y-%m-%d %H:%M}):\n{text}"


def _priority(issue: Issue) -> tuple[int, int]:
    """Incidents first, then new games, then the rest; older first."""
    kind = 0 if INCIDENT in issue.labels else 1 if NEW_GAME in issue.labels else 2
    return kind, issue.number
