# Tango

Fill an N×N grid with suns and moons:
- No three equal symbols in a row or column.
- Every row and column holds N/2 of each.
- Cells joined by `=` match, and cells joined by `×` differ.

```
uv run python -m engines.tango examples/tango/tango1.png -o solved.png
```

## Solver: line patterns

* Each row and column keeps a list of candidate **patterns**: n-bit masks with
  n/2 suns, no three equal neighbours, and agreeing with the signs inside that
  line. Every sign sits between neighbours, so it falls inside exactly one
  line.
* **Propagation:** drop patterns that clash with known cells. A cell on which
  all remaining patterns agree (the AND / OR of the patterns) is fixed, which
  narrows the crossing line, and so on. A line with no patterns left is a
  dead end.
* **Branch on the line with the fewest patterns left**, the same principle as
  the other solvers.
* Random 12×12 boards: from more than 5 s (plain cell-by-cell backtracking)
  to 3 ms. 16×16 boards take at most about 20 ms.

The stress-test boards come from mixing a checkerboard with 2×2 "switch"
flips, which keep every row and column count. Building boards row by row took
up to 13 s each at 14×14.

## OCR

1. **Grid:** the shared lattice finder in [`engines/vision`](../vision).
2. **Givens:** a cell holds a symbol if enough of its pixels are strongly
   saturated, since the board is white and grey. Orange (red > blue) means
   sun, and blue means moon. Only symbols on **grey** cells are given.
   Symbols on white cells are the player's own moves, so a screenshot of a
   game in progress still reads as the original puzzle (see `tango2.png`).
3. **Signs:** look at a small window around the midpoint of every border
   between two cells. Dark, unsaturated pixels there are sign ink. `=` is two
   bars with a gap between them, while `×` is one stroke, so counting the
   bands of inked rows tells them apart.

The rendered solution wipes whatever the player had placed and draws the
answer in every cell that is not given.

```
Read 6x6:          ('x' / '=' between two cells is a sign)
. . . . S S
    x
. .x. . S M
  x
.=. . . . .
. . . . .x.
        x
S M . .=. .
      =
M M . . . .
```
