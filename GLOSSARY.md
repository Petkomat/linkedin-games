# LinkedIn games

Bots that solve and play LinkedIn's daily puzzle games, and the team of agents
that adds new games and repairs the ones that break.

## Games

**Logic game**:
A game a program can solve from the screen using only its rules, search,
arithmetic and a fixed word list. Only logic games are built.
_Avoid_: LLM-less game

**Knowledge game**:
A game whose solving needs world knowledge or judgement about meaning, such as
Pinpoint's categories or Crossclimb's clues. Declined, and remembered as declined.
_Avoid_: LLM game

**Teaser**:
An announcement of a game that is not playable yet. Noted, never worked on.

## Team

**Role**:
A job on the team (Scout, Watcher, Project Manager, Developer, Reviewer, Operator).
_Avoid_: agent (when the job is meant)

**Agent**:
One running instance of a role. Two Developer agents can work at the same time.

**Scout**:
The role that notices a new playable game.
_Avoid_: change detector

**Watcher**:
The role that keeps an eye on the games already built and on the team itself,
and reports incidents.

**Project Manager**:
The role that takes a task, judges what it is, and hands it to the role that
should start on it.
_Avoid_: dispatcher

**Developer**:
The role that builds or fixes a game test-first and opens the PR.
_Avoid_: implementor

**Reviewer**:
The role that judges a PR on correctness, efficiency, robustness, human-like
play and a lean stack, not on code style.
_Avoid_: senior reviewer

**Operator**:
The role that looks after CI, the machine the team runs on, and merging.
_Avoid_: system guy

## Work

**Task**:
One unit of work handed out by the Project Manager: a new game, an incident,
or anything you ask for.

**Incident**:
A failure of something already built, such as a game that no longer reads
today's board, found by the Watcher.

**PR**:
A proposed change to the main branch, with its reviews. MR means the same.

**Review**:
A Reviewer's verdict on a PR, written on the PR. A PR gets at most three.
