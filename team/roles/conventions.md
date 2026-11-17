# You are on the LinkedIn games team

This repo holds bots that solve and play LinkedIn's daily puzzle games:
screenshot in, solution out, and human-like moves in Chrome. A small team of
agents keeps it growing and working: the Project Manager triages tasks, the
Developer builds and fixes, the Reviewer judges, the Operator gets PRs ready
to merge, and the owner approves every merge. Read GLOSSARY.md for the words
the team uses.

You run headless: nobody answers questions while you work. If you can't go on,
finish with the verdict that hands the task to the owner, and say exactly what
you need.

Your shell is Bash. Your role allows only some commands, and anything else is
refused, never asked. A refusal isn't the end: do the same another way your
role allows, such as the Edit tool rather than a script to change a file, or
`uv run python` rather than `python`. Hand the task to the owner only when no
allowed way is left, and name the command that was refused.

## How the repo works

- Python 3.10+, managed by uv. `uv run pytest tests/<game>` tests one game,
  `uv run pytest` everything. pyproject.toml and uv.lock are shared: never
  change dependencies; a new one needs the owner.
- Files are UTF-8 with LF line endings. A script that writes files on this
  Windows machine must pass encoding="utf-8" and newline="\n".
- One folder per game, all the same shape (engines/queens is a good model):
  - engines/<game>/model.py (the puzzle), solver.py (`solve(puzzle, trace=None)`),
    ocr.py (`scan(image)`, a scan with `.puzzle` and `.grid`), moves.py (the
    solver's trace as Click/Drag/Press/Think actions), render.py (the solution
    as text and as a picture), __main__.py (screenshot in, solved picture out),
    README.md (the rules, the algorithm, the OCR, measured speed)
  - tests/<game>/__init__.py and test_<game>_*.py (file names unique across
    games), boards.py with text boards, generator.py for random boards
  - examples/<game>/<game>N.png: real screenshots
  - an entry in engines/play/games.py, which makes the game playable and
    adds it to the daily guest check
- Shared code; reuse it instead of copying:
  - engines/common: run_cli, set_bits, letter and board_text, Cell and Edge,
    Trace / traced / left_on_board (trace.py), actions Click / Drag / Press / Think
  - engines/vision: open_image / load_rgb, find_grid -> GridGeometry,
    morphology, read_number and read_letter (glyphs.py)
  - tests/helpers.py: example(), solve_within(), text_grid(), random_path()
- Solvers: forced moves first, then branch on the unit (row, column, region
  or cell) with the fewest options. Every solver takes an optional trace, and
  moves.py replays it, wrong guesses and take-backs included: the bot must
  look like a person thinking, not print the answer in reading order.
- Lean on purpose: numpy and Pillow only. No Tesseract, no torch, no LLM
  image understanding: hand-rolled OCR is part of the showcase.

## LinkedIn

Only ever as a guest, in a fresh browser:
- `uv run --extra browser python -m engines.play.guest shot <slug> --out FILE.png`
  screenshots today's board of any game on linkedin.com/games/<slug>/
- `uv run --extra browser python -m engines.play.guest play <game> --out DIR`
  reads, solves and plays a registered game, and films it
- `uv run --extra browser python -m engines.play.check <game>` reads and
  solves without playing

Never run `python -m engines.play` itself and never touch ~/.linkedin-games:
that is the owner's LinkedIn account. Open each LinkedIn page as few times as
you need; LinkedIn doesn't welcome bots.

## Git

- Work on your branch only. Never push to main and never merge: the owner
  approves, then the orchestrator merges.
- Plain commit messages. No Co-Authored-By lines and no other Claude
  attribution in commits or PR text.

## What you find along the way

If you notice a real problem outside your task, such as a bug from history or
a helper copied between games, don't fix it on this branch. List it in your
verdict's `found`: a title, and what you saw and where. At most two. The
orchestrator files each one as a new task, which waits for the owner.
