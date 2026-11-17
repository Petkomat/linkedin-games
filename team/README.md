# The agent team

A small team of Claude agents keeps this repo growing and working. When
LinkedIn launches a new logic game, the team builds its engine test-first,
reviews it, and gets it ready to merge. When a built game stops reading
today's board, it fixes it. The owner approves every merge.

The words are defined in [GLOSSARY.md](../GLOSSARY.md). The decisions behind
the design are in [docs/adr](../docs/adr).

## The pipeline

```
GitHub Actions, daily (daily.yml)        the owner's machine (python -m team run)
  Scout   ─ new game on the hub ─┐
  Watcher ─ a game fails today ──┼─► issue ─► Project Manager ─► Developer ⇄ Reviewer ─► Operator ─► owner approves ─► merged
  the owner ─ any task ──────────┘            (triage)           (≤ 3 reviews)                        (on GitHub)
```

| Stage | Who | When it's done |
|---|---|---|
| triage | Project Manager (Sonnet) | develop · ops · declined (a knowledge game) · needs-human · done |
| develop | Developer ×2 (Opus) | builds test-first, plays once as a guest, pushes → review |
| review | Reviewer ×2 (Opus) | its review goes on the PR: approve → ops · changes → develop; after the third, the owner decides |
| ops | Operator ×1 (Sonnet) | rebase, tests, CI → ready |
| ready | the owner | approves the PR: the orchestrator merges it and closes the task |

- **GitHub is the only state.** A task is an issue, and its stage is a label.
  The team's account is the assignee of every task it works on, and stays so
  once the task is done, unless someone was assigned already.
  What routing must remember (failed runs, reviews, branches, Claude sessions)
  is in the bot's comments, as a hidden marker under the readable text.
- **Routing is fixed code** ([orchestrator.py](orchestrator.py)). Agents use
  judgement only inside their own stage, and end with a verdict in a fixed
  format.
- **Each agent** is the `claude` CLI, run headless in its task's own git
  worktree. Its role's prompt is [roles/](roles), and it may use only its
  role's tools ([roles.py](roles.py)): anything else is refused, never asked.
- **Queue order**: incidents, then new games, then the rest. A run that fails
  is retried once; a second failure goes to the owner. At Claude's usage
  limit, the team pauses until the limit resets.
- **The Scout and the Watcher** are plain scripts, not agents
  ([scout.py](scout.py), [watcher.py](watcher.py), [daily.py](daily.py)).
  They run on GitHub at a random time each day, open each LinkedIn page once
  as a guest, and stop at the first sign of a block.

## Running it

```
uv run python -m team labels     # once: the labels the team uses
uv run python -m team run        # the orchestrator; the board is on http://127.0.0.1:8765
uv run python -m team stop
.\team\install.ps1               # or: start it at every logon (-Remove to undo)
```

The board shows every agent at work (its role, task, stage, time and latest
step) with its live log and its prompt, what waits for the owner, the queue,
and recent runs. Each run's raw output is in ~/.linkedin-games/team/logs, and
the orchestrator's own log is ~/.linkedin-games/team/orchestrator.log.

## When it's your turn

The team mentions you on GitHub, and the board lists the task under
"Waiting for you".

- **A PR is ready** (`stage:ready`, with a review request): approve it and
  the orchestrator merges it within a minute. Request changes instead, and
  the task goes back to the Developer with your review.
- **A question** (`needs-human`): the Project Manager can't tell if a game
  is a logic game, a Developer or Operator is stuck, a run failed twice, the
  third review didn't approve, or a merge failed. Answer in
  a comment on the issue, then remove the `needs-human` label. The task goes
  on where it stopped, and the agent reads your comment. A Developer picks up
  its own earlier session.

## Setup

1. A GitHub account for the agents, added to the repo as a collaborator. It
   needs a classic token with the `repo` and `workflow` scopes.
2. `~/.linkedin-games/team.env`, outside the repo:
   ```
   GH_TOKEN=ghp_...
   TEAM_BOT=<the account's login>
   TEAM_BOT_EMAIL=<its email>
   ```
   The orchestrator and every agent act as that account. Commits are its own,
   and git pushes use its token.
3. Branch protection on main that requires one approving review. The bot's
   PRs then merge only once the owner approves them.
4. Claude Code signed in with the owner's own subscription.

## Safety

- Only issues opened by the owner, the bot or the daily workflow are worked
  on, and only their comments reach an agent. Anyone can open an issue on a
  public repo, so this keeps strangers from steering the agents.
- Agents never use the owner's LinkedIn account. They only go to LinkedIn as
  a guest, in a fresh browser ([ADR 0002](../docs/adr/0002-agents-never-use-the-linkedin-account.md)).
- The permission lists are guardrails, not a sandbox: `uv run` runs any
  Python. The real limits are branch protection, the bot's own
  account, and the owner's review.
