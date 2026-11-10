# linkedin-games
Let's cheat a bit :rocket:

Solvers for the LinkedIn daily games: screenshot in, solved screenshot out.

```
uv sync
uv run python -m engines.<game> examples/<game>/<file>.png -o solved.png
uv run pytest
```

## Layout

```
engines/
  common/     plumbing shared by every game: command line, bit sets, text boards, Cell/Edge
  vision/     image processing shared by every game: loading, grid finding,
              binary morphology, digit and letter reading
  patches/    model.py, solver.py, ocr.py, render.py, __main__.py; one folder per game
  queens/
  sudoku/
  tango/
  wend/       plus enable1.txt, the English word list
  zip/        solver only so far
tests/
  helpers.py  shared test helpers: example screenshots, time-limited solve, text boards
  <game>/     test_<game>_*.py (file names are unique across games)
examples/     real screenshots, one folder per game
```

Every game follows the same shape: a pure `solve(puzzle)` backtracking engine
plus `read_puzzle(screenshot)` OCR. Both are tested test-first. See each
engine's README for its algorithm.
