# Play

Plays today's game on LinkedIn: screenshot, OCR, solve, then mouse and
keyboard. No LLM is involved anywhere.

```
uv sync --extra browser
uv run --extra browser python -m engines.play queens     # or tango, sudoku, patches, wend, zip
```

1. Chrome opens with its own profile (default `~/.linkedin-games/chrome-profile`).
   The first time, log in by hand in that window. The login is kept in the
   profile, so no password is stored anywhere.
2. The game's start button is clicked: a button named Start, Play or Resume,
   possibly inside an iframe. If there isn't one, press it yourself.
3. The screen is read until the same board is read twice in a row, so a
   board that is still fading in isn't played, and that board has a solution.
4. The moves are played, and the screen is saved as `<game>_played.png`.

Playwright is an optional extra, so the solvers still need only numpy and
Pillow. It drives the Chrome that is already installed, so it downloads no
browser of its own.

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
| Wend | a word | drag from its first letter to its last | nothing (see below) |
| Zip | the next cell of the path | one held drag from 1, onto the cell | drag back onto the cell before |

- **Wend:** the game knows the hidden words. A decoy (a real word that isn't
  hidden) is rejected and vanishes, so taking it back needs no input. A
  hidden word stays once found, so it is never dragged twice, even if the
  solver dropped it and placed it again.
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
- Wend rejecting decoys;
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

- **Humanizing:** the mouse moves in straight lines at constant speed, with
  fixed pauses.
- **Zip on big boards:** `walk` branches only at the end of the path. Random
  8×8 boards take at most 70 ms, 9×9 up to 2 s, and sparse 10×10 boards much
  longer.
- **LinkedIn's terms:** the User Agreement forbids bots and automated access,
  and solve times show on connections' leaderboards. Use at your own risk.
