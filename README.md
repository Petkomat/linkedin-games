# linkedin-games

**LinkedIn games: Think like a robot, move like a human**

Solvers for the LinkedIn daily games: screenshot in, solved screenshot out,
or play today's game in Chrome.

```
uv sync
uv run python -m engines.<game> examples/<game>/<file>.png -o solved.png
uv run pytest

uv sync --extra browser
uv run --extra browser python -m engines.play <game>
```

## Layout

```
engines/
  common/     plumbing shared by every game: command line, bit sets, text boards, Cell/Edge,
              solver traces and the actions (click, drag, key) moves are made of
  vision/     image processing shared by every game: loading, grid finding,
              binary morphology, digit and letter reading
  play/       plays a game in Chrome with Playwright: screenshot, solve, mouse
  patches/    model.py, solver.py, ocr.py, moves.py, render.py, __main__.py; one folder per game
  queens/
  sudoku/
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
