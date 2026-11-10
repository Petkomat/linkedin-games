# Play

Plays today's game on LinkedIn: screenshot, OCR, solve, then mouse and
keyboard. No LLM is involved anywhere.

```
uv sync --extra browser
uv run --extra browser python -m engines.play queens     # or tango, sudoku, patches, wend, zip
```

1. Chrome opens with its own profile (default `~/.linkedin-games/chrome-profile`).
   If you aren't logged in to LinkedIn there, it opens the login page and
   waits for you. The login is kept in the profile, so no password is stored
   anywhere. Google refuses to sign in inside a browser that is being
   remote-controlled. To sign in with Google, run
   `uv run --extra browser python -m engines.play --login` once first: it
   opens an ordinary Chrome window on the same profile. Log in there, then
   close the window.
2. The game opens with its board already showing; no game has a start button.
   The screen is read until the same board is read twice in a row, so a
   board that is still fading in isn't played, and that board has a solution.
3. The moves are played. Two seconds after the last one, the screen is saved
   as `plays/<game>/<date>_<time>.png`, for example
   `plays/zip/2026-11-10_14-03-07.png` (`-o` saves it elsewhere). Next to it,
   a `.md` file of the same name holds the solution as a readable table, with a
   legend ([`report.py`](report.py)). It is written as soon as the board is
   solved, before the first move. `plays/` is
   in `.gitignore`, because the screenshots show your LinkedIn page. The
   browser stays open until you close its window (or press Ctrl+C), so nothing
   is cut off and you can look at the result.

Playwright is an optional extra, so the solvers still need only numpy and
Pillow. It drives the Chrome that is already installed, so it downloads no
browser of its own. Chrome is started with its sandbox on. Playwright turns
it off by default, which makes Chrome show a warning bar about `--no-sandbox`.

## Moves follow the solver

A player who enters the answer in reading order gives away that they knew it.
Instead, each solver writes a *trace* ([`trace.py`](../common/trace.py)): what
it put on the board, in the order it did, including guesses that later failed
and what it took back when they did. Each game's `moves.py` turns that trace
into input:

| Game | The solver places... | entered as | Taking it back |
|---|---|---|---|
| Queens | a queen | two clicks (empty → X → queen) | one click (queen → empty) |
| Tango | a sun or a moon | one or two clicks (empty → sun → moon) | two or one clicks (→ empty) |
| Mini Sudoku | a digit (givens skipped) | click the cell, type the digit | click the cell, Backspace |
| Patches | a patch | drag from corner to corner | click the patch |
| Wend | a word | drag from its first letter to its last | click its first letter (not once it has a ✓) |
| Zip | the next cell of the path | one held drag from 1, onto the cell | drag back onto the cell before |

- **Wend:** any real word stays on the board, hidden or not. A hidden word
  gets a ✓ and is locked: it can't and mustn't be removed. Any other word is
  removed by clicking its first letter, and a wrong word left behind gets in
  the way. On the first live run, the solver tried ESS and then dropped it,
  but ESS stayed on the board. The next drag (SETS) started on one of its
  tiles, which made the game extend it to TESS. So every wrong word the
  solver drops is clicked away. The solver can't see the ✓s, so the moves
  apply what a player would see: a ✓ word is dragged once and kept, even if
  the solver drops it and places it again later. A wrong word that would
  cross a ✓ word is never tried.
- **Zip:** `solve` decides links between cells anywhere on the board, which
  the game can't take as input: it only grows one path from 1. So the moves
  come from `walk` ([`solver.py`](../zip/solver.py)), which draws from 1 as a
  player does and uses the same propagation to see ahead. A step that
  propagation rejects at once is never drawn, the way a player wouldn't try a
  move that obviously fails. Dead ends found further on are drawn and then
  taken back.

On the example screenshots, most solvers deduce everything without a wrong
guess. The tests use harder boards to check that failed guesses are entered
and taken back.

**To check on the first live run.** The controls above come from your
description and from third-party guides, not from LinkedIn. The ones least
certain:
- the Tango click cycle;
- Backspace in Mini Sudoku;
- clicking a patch to remove it;
- dragging back in Zip.

Each one is a constant or a small function in that game's `moves.py`.

## Coordinates

`scan()` already knows where every cell is in the screenshot.
[`Screen`](screen.py) maps a cell's centre to the page by dividing by the
page's `devicePixelRatio`, because Playwright screenshots in device pixels
but moves the mouse in page pixels. The screenshot is of the window only
(not the full page), so the board must be visible in the window. The board
isn't looked up in the page's HTML at all, so it doesn't matter if the game
sits in an iframe.

## Live check

`uv run --extra browser python -m engines.play.check [game ...]` checks that
the solvers still work on LinkedIn without playing anything. It opens each
game as a guest (not logged in) in headless Chrome and clicks the guests'
"Start game". It moves the mouse aside, because a pointer resting on a cell
highlights it, then reads and solves the board. It saves `checks/<game>.png`
and `.md`, and exits with 1 if any game fails.

GitHub Actions runs it every Sunday and Wednesday at 10:00 UTC, and on demand
from the Actions tab ([`live-check.yml`](../../.github/workflows/live-check.yml)).
Each run's screenshots and solutions are kept as its `live-check` artifact.
GitHub turns off scheduled workflows in a repository with no activity for 60
days.

## Tests

- `tests/<game>/test_<game>_moves.py`: the moves are replayed on a small model
  of the game's controls (for example, Queens' click cycle). They must end at
  the answer. On a board where the solver guesses wrong, the wrong guess must
  show up on the way and be undone.
- `tests/play/test_play_screen.py`: cell to mouse position, at scale 1 and 2.
- `tests/play/test_play_in_browser.py`: headless Chrome at scale 2 on a local
  page that shows an example screenshot and records every pointer and key
  event. The player reads, solves and plays that page. The recorded events
  must hit the cells of the moves worked out from the original screenshot
  file. It is skipped without the `browser` extra.

## Not done yet

- **Humanizing:** so far only these:
  - **Thinking and bursts** ([`timing.py`](timing.py)): each solver marks
    *thoughts* in its trace, the moves it worked out together. Each Tango line
    it deduces is one thought, and so is taking back a failed guess. Every
    other placement is a thought of its own. The player thinks once per
    thought, then makes that thought's moves 0.3–0.8 s apart.
  - **Thinking time:** never under 1.5 s and 2 s on average, with a long tail.
    The time above 1.5 s is log-normal, the usual shape of human response
    times. The median is 1.83 s, 1 move in 10 takes over 2.6 s and 1 in 100
    over 4.2 s. Set these with `--pause`, `--shortest-pause` and
    `--pause-tail`. A normal curve couldn't spread more without breaking
    either the average or the floor.
  - **Typing:** a digit is typed 0.3 s after the click that selected its cell.
  - **Spots:** the mouse is pressed and released on a random spot of its
    cell, drawn from a bell curve around the middle (σ = 15% of a cell) and at
    least 20% of a cell from the edges. Both clicks of a queen hit the same
    spot, like a double click.
  - **Drags** move like a hand ([`motion.py`](motion.py)):
    - A path is cut into *strokes*, the straight runs between turns. Each
      stroke starts slowly, is fastest in the middle and slows down before
      the turn. This minimum-jerk speed profile is how people move a hand,
      with a little even speed mixed in so the hand never quite stops.
    - A stroke takes 0.15 s plus 0.07 s per cell. Each stroke is randomly up
      to 30% slower or 40% faster.
    - Each turn is aimed at a random spot near the turning cell's middle, so
      the runs lean slightly off the middles. Corners are cut in a small
      curve inside the turning cell.
    - The hand hesitates at one turn in five, for 0.1 to 0.3 s. Where Zip backs
      out of a dead end, it always stops for 0.3 to 0.6 s.
    - Every position stays inside a cell of the path, and the mouse crosses
      between cells away from their corners, so the game sees exactly the
      path's cells, in order.
    - A drag takes at least 0.5 to 0.6 s, so a patch is drawn in about half
      a second. The zip2 path takes 7 to 8.5 s.
- **Zip on big boards:** `walk` branches only at the end of the path. Random
  8×8 boards take at most 70 ms, 9×9 up to 2 s, and sparse 10×10 boards much
  longer.
- **LinkedIn's terms:** the User Agreement forbids bots and automated access,
  and solve times show on connections' leaderboards. Use at your own risk.
