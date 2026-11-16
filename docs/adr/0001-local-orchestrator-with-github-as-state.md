# A local orchestrator, with GitHub as the only state

The agent team is driven by a small orchestrator in this repo, written with
Python's standard library only. It starts each agent as the unmodified `claude`
CLI in its own git worktree. Issues, labels and PRs on GitHub are the only state,
and the hand-offs between roles are fixed code; agents use judgement only inside
their own stage. The Scout and the Watcher are plain scripts in GitHub Actions,
so new games and incidents are filed even when the local machine is off.

## Considered options

- **Paperclip**: the closest match to "a company of agents", with a strong live
  dashboard. Rejected because with a Claude subscription it needs WSL2 on Windows
  (issue #17968, Nov 2026), brings a Node and Postgres server, keeps its own
  ticket system beside GitHub Issues, and released almost weekly.
- **Claude Agent SDK**: its documentation expects an API key, while the
  unmodified `claude` CLI signed in with the user's own subscription is plainly
  allowed.
- **Claude's GitHub Action for every role**: workable, and the likely next step.
  Building stays local for now because the user asked for a version on their
  machine. Because the state already lives in GitHub, moving means replacing only
  how an agent is started.
