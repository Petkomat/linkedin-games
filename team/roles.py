"""The roles that run as Claude agents: the stage each works in, its model,
how many may run at once, how long a run may take, what it may do without
asking, and the verdict it must end with."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from .model import DECLINED, DEVELOP, NEEDS_HUMAN, OPS, REVIEW, SPLIT, TRIAGE


def bash(*commands: str) -> tuple[str, ...]:
    """Permission rules for these commands, with or without arguments."""
    return tuple(rule for c in commands for rule in (f"Bash({c})", f"Bash({c} *)"))


@dataclass(frozen=True)
class Role:
    name: str
    stage: str  # the stage whose tasks this role works on
    model: str
    slots: int  # agents of this role that may run at once
    timeout: timedelta
    worktree: bool  # works in the task's own worktree (else in the main checkout, read-only)
    allowed: tuple[str, ...]  # tools it may use without asking; everything else is refused
    key: str  # the verdict's deciding field
    answers: tuple[str, ...]  # what that field may say
    texts: tuple[str, ...] = field(default=())  # the verdict's other fields, all text
    required: tuple[str, ...] = field(default=())  # which of those it must give
    lists: tuple[tuple[str, dict[str, Any]], ...] = field(default=())  # fields that are lists: (name, item schema)

    @property
    def schema(self) -> dict[str, Any]:
        properties: dict[str, Any] = {self.key: {"type": "string", "enum": list(self.answers)}}
        properties.update({name: {"type": "string"} for name in self.texts})
        properties.update({name: {"type": "array", "items": item} for name, item in (*self.lists, ("found", FOUND))})
        return {"type": "object", "properties": properties, "required": [self.key, *self.required]}


def _item(*required: str, **properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": list(required)}


TEXT = {"type": "string"}
MAX_FOUND = 2  # problems one run may report; the orchestrator files no more
MAX_PARTS = 6  # parts one task may be split into; more, and the owner decides
# Something an agent noticed outside its task, such as a bug from history: filed as a new task.
FOUND = _item("title", "body", title=TEXT, body=TEXT)
# One part of a split task, in the order the team does them.
PART = _item("title", "body", "stage", title=TEXT, body=TEXT, stage={"type": "string", "enum": [DEVELOP, OPS]})


READ_GIT = bash("git status", "git diff", "git log", "git show")
READ_SHELL = bash("ls", "cat", "head", "tail", "grep", "wc", "file", "sed -n", "pwd")  # every role may look

PROJECT_MANAGER = Role(
    "project-manager", TRIAGE, "sonnet", 1, timedelta(minutes=20), worktree=False,
    allowed=(*bash("git log"), *READ_SHELL),
    key="decision", answers=(DEVELOP, OPS, SPLIT, DECLINED, NEEDS_HUMAN, "done"),
    texts=("comment",), required=("comment",), lists=(("parts", PART),),
)
DEVELOPER = Role(
    "developer", DEVELOP, "opus", 2, timedelta(hours=4), worktree=True,
    allowed=(
        "Edit", "Write", "Skill",
        *bash("uv run", "uv sync", "gh run download", "gh run view"), *READ_SHELL,
        *READ_GIT, *bash("git add", "git commit", "git push", "git restore", "git rm", "git mv", "git fetch"),
    ),
    key="status", answers=("ready", "stuck"),
    texts=("summary", "title"), required=("summary",),
)
REVIEWER = Role(
    "reviewer", REVIEW, "opus", 2, timedelta(hours=1), worktree=True,
    allowed=(*bash("uv run", "uv sync", "git fetch"), *READ_GIT, *READ_SHELL),
    key="decision", answers=("approve", "changes"),
    texts=("review",), required=("review",),
)
OPERATOR = Role(
    "operator", OPS, "sonnet", 1, timedelta(hours=1), worktree=True,
    allowed=("Edit", "Write", *bash("git", "uv run", "uv sync", "gh pr checks", "gh run view", "gh run list", "gh run watch"), *READ_SHELL),
    key="status", answers=("ready", "developer", "stuck"),
    texts=("summary", "title"), required=("summary",),
)

ROLES = {role.stage: role for role in (PROJECT_MANAGER, DEVELOPER, REVIEWER, OPERATOR)}  # by stage
BY_NAME = {role.name: role for role in ROLES.values()}
