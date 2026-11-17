"""What the team works with: tasks (GitHub issues), their comments and PRs,
and what an agent run ends with."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# The labels that carry a task's state on GitHub.
STAGE = "stage:"  # stage:triage, stage:develop, stage:review, stage:ops, stage:ready
TRIAGE, DEVELOP, REVIEW, OPS, READY = "triage", "develop", "review", "ops", "ready"
SPLIT = "split"  # stage:split, a task done as its parts, its sub-issues
NEEDS_HUMAN = "needs-human"
BLOCKED = "blocked"  # a part that waits for the part before it
INCIDENT = "kind:incident"
NEW_GAME = "kind:new-game"
DECLINED = "declined"


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    author: str
    labels: frozenset[str]
    created: datetime
    updated: datetime
    assignees: frozenset[str] = frozenset()

    @property
    def stage(self) -> str | None:
        stages = [label.removeprefix(STAGE) for label in self.labels if label.startswith(STAGE)]
        return stages[0] if len(stages) == 1 else None


@dataclass(frozen=True)
class Comment:
    author: str
    body: str
    created: datetime


@dataclass(frozen=True)
class PullRequest:
    number: int
    branch: str
    url: str
    owner_review: str | None = None  # the owner's latest review: APPROVED or CHANGES_REQUESTED
    owner_review_body: str = ""
    owner_review_at: datetime | None = None


@dataclass(frozen=True)
class Job:
    """One agent run the orchestrator asks for."""

    role: str
    issue: int
    title: str
    prompt: str
    branch: str | None  # the task's branch, checked out in its own worktree; None: no worktree
    session: str  # the Claude session id
    resume: bool  # continue that session instead of starting it


@dataclass(frozen=True)
class Verdict:
    """An agent run that finished and said how it went."""

    data: dict[str, Any]


@dataclass(frozen=True)
class Failed:
    reason: str


@dataclass(frozen=True)
class UsageLimited:
    until: datetime


Outcome = Verdict | Failed | UsageLimited


@dataclass
class Running:
    agent: str  # the id the agent starter gave it
    job: Job
    stage: str
    started: datetime
    kind: str = field(default="task")
