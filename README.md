# linkedin-games

**LinkedIn games: Think like a robot, move like a human**

Solvers for the LinkedIn daily games: screenshot in, solved screenshot out,
or play today's game in Chrome. Covered so far: Patches, Queens, Mini Sudoku,
Sumbreak, Tango, Wend and Zip, the logic games, which rules and search solve from the
screen alone. The knowledge games, such as Pinpoint and Crossclimb, need world
knowledge and are out of scope.

```
uv sync
uv run python -m engines.<game> examples/<game>/<file>.png -o solved.png
uv run pytest

uv sync --extra browser
uv run --extra browser python -m engines.play <game>     # or several games, or all
```

## Layout

```
engines/
  common/     plumbing shared by every game: command line, bit sets, text boards, Cell/Edge,
              solver traces and the actions (click, drag, key, button) moves are made of
  vision/     image processing shared by every game: loading, grid finding,
              binary morphology, digit and letter reading
  play/       plays a game in Chrome with Playwright: screenshot, solve, mouse
  patches/    model.py, solver.py, ocr.py, moves.py, render.py, __main__.py; one folder per game
  queens/
  sudoku/
  sumbreak/
  tango/
  wend/       plus enable1.txt, the English word list
  zip/        no render or command line yet; played with engines.play
tests/
  helpers.py  shared test helpers: example screenshots, time-limited solve, text boards,
              random paths through every cell
  <game>/     test_<game>_*.py (file names are unique across games)
examples/     real screenshots, one folder per game
```

Every game follows the same shape: a pure `solve(puzzle)` backtracking engine,
`read_puzzle(screenshot)` OCR, and `moves(puzzle)`, which enters the solution
in the order the solver found it, wrong guesses included. All of them are
tested test-first. See each engine's README for its algorithm, and
[`engines/play`](engines/play) for playing on LinkedIn.

## How it improves itself

A small team of Claude agents keeps the repo growing and working. Once a day,
two plain scripts on GitHub Actions look at LinkedIn: the Scout spots a new
game, the Watcher a built game that fails today's board, and each files an
issue. The owner can open one too. The Project Manager triages it, the
Developer builds or fixes it test-first, the Reviewer judges the PR, and the
Operator gets it ready to merge. GitHub issues and their labels are the only
state.

Each agent is a headless `claude` run in its own git worktree, with only its
role's tools. Agents go to LinkedIn only as a guest, never use the owner's
account, and never push to main or merge: the owner approves every merge.

```
uv run python -m team labels     # once: the labels the team uses
uv run python -m team run        # start: the orchestrator, board on http://127.0.0.1:8765
uv run python -m team stop       # stop: the orchestrator and its agents
```

Setup (a bot account and its token, `~/.linkedin-games/team.env`, branch
protection on main) and the pipeline in detail are in
[team/README.md](team/README.md). [docs/orchestration.md](docs/orchestration.md)
is the big picture, and [GLOSSARY.md](GLOSSARY.md) defines the words.
