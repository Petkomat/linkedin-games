# How the agent team is orchestrated

The big picture: how work enters the system, how it moves from role to role,
where state lives, and what happens when something breaks. For setup and
commands, see [team/README.md](../team/README.md). For the words used here,
see [GLOSSARY.md](../GLOSSARY.md).

## In one paragraph

GitHub is the only shared memory. A task is an issue, and its stage is a
label (`stage:triage`, `stage:develop`, and so on). A Python loop on your PC,
the orchestrator, polls GitHub every 60 seconds. It starts the right Claude
agent for each task, waits for that agent's structured verdict, and turns the
verdict into the next label and a comment. Agents never hand work to each
other directly. Each one ends with a verdict, and fixed code in
[orchestrator.py](../team/orchestrator.py) decides what comes next. New work
comes from three places: you (any issue you open), and the Scout and the
Watcher, two plain scripts that run once a day in GitHub Actions.

## The moving parts

```
  GitHub Actions, once a day             GitHub: the only state              Your PC: uv run python -m team run
 ┌───────────────────────────┐        ┌──────────────────────────┐        ┌──────────────────────────────────┐
 │ Scout:   new game on hub  │─issue─►│ issues, labels, comments │◄─poll──│ orchestrator: a tick every 60 s  │
 │ Watcher: broken game,     │─issue─►│ PRs, reviews             │─write─►│ starts `claude -p` per task,     │
 │   red CI, idle team       │        │ branches                 │        │ in git worktrees                 │
 └───────────────────────────┘        └──────────────────────────┘        │ board: http://127.0.0.1:8765     │
                                          ▲                               └──────────────────────────────────┘
                                          │ you: open issues, answer questions, approve PRs
```

| Piece | Runs where | What it is |
|---|---|---|
| Scout, Watcher | GitHub Actions, [daily.yml](../.github/workflows/daily.yml) | Python scripts with no LLM: [scout.py](../team/scout.py), [watcher.py](../team/watcher.py), [daily.py](../team/daily.py) |
| Orchestrator | Your PC, started at logon by [install.ps1](../team/install.ps1) | A tick loop that uses only the standard library: [orchestrator.py](../team/orchestrator.py) |
| Agents | Your PC, started by the orchestrator | The `claude` CLI, run headless (`claude -p`): [agents.py](../team/agents.py) |
| Roles | Prompts and permissions | [roles/*.md](../team/roles) for the instructions, [roles.py](../team/roles.py) for model, slots, timeout, allowed tools and verdict schema |
| Board | Your PC | A localhost page with live agent logs: [board.py](../team/board.py) |

| Role | Model | At once | Time limit | Works in |
|---|---|---|---|---|
| Project Manager | Sonnet | 1 | 20 min | a read-only checkout of `origin/main` |
| Developer | Opus | 2 | 4 h | the task's worktree |
| Reviewer | Opus | 2 | 1 h | the task's worktree |
| Operator | Sonnet | 1 | 1 h | the task's worktree |

## How changes are detected

Nothing here uses webhooks. Everything is polling, at two speeds.

### Changes on LinkedIn: once a day, in the cloud

The daily workflow runs at 08:30 UTC, then waits a random 0 to 2 hours. It
opens one fresh, never-logged-in Chrome, loads each page once and never
retries. If the hub answers 429, 999 or 5xx, it files a "blocked" incident
and stops.

- **Scout: is there a new game?** It parses the game cards on
  linkedin.com/games and subtracts two sets:
  - games already built: the slugs in
    [engines/play/games.py](../engines/play/games.py)
  - games already known: every `kind:new-game` issue ever filed, open or
    closed, recognised by a hidden `<!-- scout {"slug": ...} -->` marker in
    its body. A declined game is a closed issue that still carries the
    marker, so it is never filed again.

  For each game that is left, it opens the game, clicks the **?** button,
  quotes the rules, takes a screenshot and files "New game: X" with
  `kind:new-game`. If the hub shows no cards at all, it files a "hub"
  incident.
- **Watcher: did something break?** It reads and solves (never plays) today's
  board for every built game, then files one incident for each problem:
  - `game:<name>`: that game failed to read or solve;
  - `blocked`: every game failed, which probably means LinkedIn blocked the
    guest;
  - `ci`: the latest `tests.yml` run on main is red;
  - `team`: a task has sat in a working stage for 24 hours with nothing
    happening to it. Your PC is off, or the orchestrator died. This is the
    only check on the orchestrator's health, and it works because it runs in
    the cloud.

  Each problem keeps one open incident. The key is a hidden
  `<!-- watch {"watch": key} -->` marker. If the problem shows up again, the
  Watcher adds a "Seen again" comment and opens no new issue. Once you close
  the incident, the next occurrence opens a new one.

Screenshots go to the run's `daily` artifact. A Developer fetches them with
`gh run download`.

### Changes on GitHub: every 60 seconds, on your PC

Each tick re-reads all open issues with `gh issue list`. It keeps only issues
opened by you, the bot account, or `github-actions[bot]`. Issues from anyone
else are ignored. What a tick notices:

| You or the system do this | The orchestrator reacts on the next tick |
|---|---|
| open an issue | it has no stage, so it gets `stage:triage` |
| remove `needs-human` | the task runs again, in the stage its label still shows |
| approve the PR of a `stage:ready` task | squash-merge, delete the branch, close the issue, remove the worktree |
| request changes on that PR | `stage:develop`; your review goes into the Developer's prompt |
| close an issue | any task waiting for it loses `blocked`, and so does the next part of a split |
| change a stage label yourself | the task is routed by the new label (see the notes at the end) |

**A comment on its own wakes nothing up.** Comments are only read when the
next agent for that task starts. Removing `needs-human` is the "go" signal.

## The tick

```
tick(now):
  1. collect   for each running agent: finished? over its time limit (then kill it)?
               if finished, re-read the issue; if it was closed or moved meanwhile, drop the result;
               otherwise apply the verdict (labels + comment)
  2. tidy up   every trusted open issue:
                 no stage         → add stage:triage
                 stage:ready      → look for your PR review
                 stage:split      → file the next part, unblock the next part, close when all are done
                 blocked + wait   → unblock once the issue it waits for is closed
  3. start     unless paused for the usage limit: in priority order
               (incidents, then new games, then the rest; older first),
               start an agent for each task in triage/develop/review/ops
               that isn't needs-human, blocked or already running, while that role has a free slot
```

Each step for one task runs in its own `try` block. A failing `gh` call is
noted on the board and tried again on the next tick. It doesn't stop the
other tasks.

## Where the state lives

There are two layers, both on GitHub.

1. **Labels: where a task is.** It has one `stage:*` label, plus
   `needs-human` (waiting for you), `blocked` (waiting for another issue),
   `kind:incident` or `kind:new-game` (priority), and `declined`.
2. **Hidden markers in the bot's comments: what routing must remember.**
   Every state change is a readable comment that ends in a JSON marker:

   ```
   The Developer is done: Added the Sumbreak engine, test-first...

   Ready for review in #14.

   <!-- team {"role": "developer", "status": "ready", "session": "3f2c...", "stage": "review"} -->
   ```

   Routing reads its history back from these markers: the task's branch, how
   many reviews it has had, whether the run before also failed, the
   Developer's Claude session, a split's plan and its filed parts, what a
   waiting task waits for, and whether a stuck task has already used its one
   try with the Project Manager. Only markers in comments by the bot count.

The orchestrator keeps only one thing in memory: which agents are running
right now. Restarting it loses nothing on GitHub.

## Hand-overs

```
issue ─► triage ─► develop ─► review ─► ops ─► ready ─► merged, issue closed
          PM       Developer  Reviewer  Operator  you

back to develop:  Reviewer "changes" · Operator "developer" · your "request changes"
back to triage:   Developer or Operator "stuck" (once per task)
to you:           needs-human, from any stage
```

An agent's run ends with JSON that must match its role's schema. The
orchestrator turns it into the next step:

| Stage | Agent says | The orchestrator then |
|---|---|---|
| triage | `develop` / `ops` | posts the PM's comment as the brief, records the branch `team/<n>-<slug>`, sets the stage |
| | `split` (2 to 6 parts) | `stage:split`; files each part as a sub-issue with its own stage, inheriting the kind label. Parts 2 and later start `blocked`, and each is unblocked when the one before it closes. The parent closes after the last part |
| | `wait` for #n | the chosen stage plus `blocked`; unblocked once #n is closed |
| | `declined` | adds the `declined` label and closes the issue as "not planned" |
| | `done` | closes the issue |
| | `needs-human` | adds `needs-human`, with the PM's question for you |
| develop | `ready` | opens the PR from the Developer's summary (with "Closes #n"), then `stage:review` |
| | `stuck` | first time: back to triage with the stuck report. Second time: `needs-human` |
| review | `approve` | posts the review on the PR, then `stage:ops` |
| | `changes` | posts the review, then `stage:develop`. After the third review that doesn't approve: `needs-human` |
| ops | `ready` | opens the PR if there isn't one, sets `stage:ready`, requests your review and mentions you |
| | `developer` | `stage:develop` (a conflict in game logic, failing code) |
| | `stuck` | the same as a stuck Developer |
| ready | *(you)* approve | merges (squash), closes the issue, removes the worktree |
| | *(you)* request changes | `stage:develop` |

The orchestrator does all the writing to GitHub: labels, comments, opening
PRs, posting reviews, merging. Agents only push their own branch. The
Reviewer can't even do that: it reads, and the orchestrator posts its review.

### What carries over from one agent to the next

- **The prompt is rebuilt from GitHub every time.** It contains the role's
  instructions ([conventions.md](../team/roles/conventions.md) plus the
  role's file), the issue body, every comment from you or the bot (markers
  stripped), and, if there is a PR, its reviews and comments. So the PM's
  comment *is* the Developer's brief, and the Reviewer's review is what the
  Developer reads on the next round.
- **One worktree per task**, at `..\linkedin-games-team\<n>` on the task's
  branch. It is made from the branch on GitHub if one exists, otherwise from
  `origin/main`. The Developer, Reviewer and Operator all work in that same
  folder, so files pass between them on disk. This is how the Reviewer sees
  the Developer's guest-play screenshot in `.team/guest/`.
- **The Developer's own Claude session.** Its session id is in the marker,
  and later Developer rounds use `--resume`, so it remembers its own
  reasoning. Every other role starts a fresh session on every run.
- **The review count**, from the markers. The Reviewer's prompt says
  "review k of 3".

## Your touchpoints

The team asks for you in three ways: a GitHub @-mention, a review request,
and the board's "Waiting for you" list. You are never assigned; the bot stays
the assignee of work it did.

- **`stage:ready` with a review request**: approve the PR to merge it, or
  request changes to send it back to the Developer.
- **`needs-human`**: answer in a comment, then remove the label.
- **A new issue with `needs-human` that an agent found** while working on
  something else (at most two per run): remove the label to hand it to the
  team (it goes to triage), or close it.
- **Anything you want done**: open an issue. Add `kind:incident` or
  `kind:new-game` if it should jump the queue.

## When things go wrong

| What happens | What the team does |
|---|---|
| An agent crashes, times out, or ends without a valid verdict | posts "Trying once more", and the stage stays, so it restarts on the next tick. A second failure in a row by the same role: `needs-human` |
| A Developer or Operator says `stuck` | the PM gets one try at sorting it out: a new brief, wait, done, or a question for you. If it gets stuck again, it goes to you |
| Claude's usage limit | stops starting agents until the limit resets (or for an hour if the reset time is unknown). Bookkeeping such as merges and unblocking goes on |
| A `gh` or `git` error | noted on the board, tried again on the next tick |
| The merge fails (red check, conflict) | `needs-human` |
| The orchestrator stops or restarts | running agents are killed. Their tasks start again from their stage label; the worktree stays on disk |
| Your PC is off | nothing runs locally; the next daily Watcher files the `team` incident |

## Safety in short

- Only issues and comments from you, the bot or the workflow ever reach an
  agent, which matters because the repo is public.
- Each role has a list of tools it may use. Anything else is refused, never
  asked (`--permission-mode dontAsk`). PowerShell and your MCP servers are
  off.
- Agents act as the bot account (its token, its git identity). Branch
  protection means nothing merges without your approval and a green `tests`
  check.
- LinkedIn is reached only as a guest in a fresh browser, never with your
  account ([ADR 0002](adr/0002-agents-never-use-the-linkedin-account.md)).

## Notes worth knowing

- **Removing `needs-human` resumes the stage the label still shows.** After
  the third review, that stage is still `review`, so removing the label runs
  a fourth Reviewer pass, not the Developer. To send the task somewhere else,
  change its `stage:*` label yourself, then remove `needs-human`.
- **Changing a label while an agent runs** doesn't stop that agent. It runs
  to the end, its verdict is dropped, and the agent for the new stage starts
  after it.
- **Only an approval given after the "ready" comment counts.** An earlier
  approval is ignored.

## Where to look

- The board, http://127.0.0.1:8765: running agents with their live log and
  prompt, what waits for you, the queue, recent runs, and errors.
- `~/.linkedin-games/team/logs/`: each run's prompt (`.prompt.md`), its raw
  stream (`.jsonl`) and its stderr.
- `~/.linkedin-games/team/orchestrator.log`: the orchestrator's own log.
- The task's issue: its comments are the full history, readable by people
  and by the code.
