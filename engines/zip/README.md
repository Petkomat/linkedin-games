# Zip

Draw one path through every cell, moving up, down, left or right. It starts
on 1, passes the numbers in order, ends on the highest one, and never
crosses a wall.

There is no `python -m engines.zip` or solution image yet; the game is played
with [`engines.play`](../play).

## Solver: links, not a walk from 1

`solve` decides, for pairs of neighbouring cells, whether the path runs
between them (a *link*). Linked cells form fragments, which must stay
consistent:
- every cell has two links, except 1 and the last number, which have one;
- no loops;
- the fragment holding 1 joins the one holding the end only as the very
  last link;
- the numbers along a fragment are consecutive and in order.

A cell with exactly as many usable links left as it still needs takes them
all. These forced links cascade from corners, walls and numbers. The search
only branches when that stalls: it links or forbids one edge of the most
constrained cell.

Growing the path from 1 stalled on 9×9 and larger. Links solve random 8×8
boards in at most 0.2 s.

## Walk: the path a player draws

The game only lets you grow one path from 1 and pull it back, so `solve`'s
order can't be entered. `walk` draws from 1 instead. The path's end moves on
one cell at a time and backs up when every way on fails. The propagation
above looks ahead:
- a step that leads straight to a contradiction is never drawn;
- links that are forced further along are simply followed.

Every cell drawn and every cell taken back goes to the trace that
[`moves.py`](moves.py) replays as one held drag.

Random boards from 6×6 to 8×8 take at most 70 ms, and 9×9 takes up to 2 s.
10×10 boards with 20 numbers take up to 39 s. A batch with 12 numbers didn't
finish within a few minutes, because the walk can only branch at the end of
the path. Trying the tightest step first only helped on 10×10 (39 s → 4 s).

## OCR

1. **Grid:** the shared lattice finder in [`engines/vision`](../vision).
   zip2.jpg has buttons, and then a panel, one row's height below the board.
   The finder drops end rows that the board's column lines don't run through.
2. **Numbers:** white digits on a black disc. The clearly white pixels inside
   the disc go to the shared glyph reader. The grey edges of the strokes are
   left out, because they close the gap in a blurry 6 so that it reads as 8.
3. **Walls:** thick black bars across a border. Over 80% of the pixels around
   a wall's border midpoint are black, against 0% elsewhere. Grid lines are
   grey and the drawn path is coloured.
