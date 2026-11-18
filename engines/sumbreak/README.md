# Sumbreak

LinkedIn tells guests: "Drag to combine matching neighbor cells. Repeat until
one cell remains." Every cell holds a numbered tile. Dragging a tile onto a
neighbour with the same number merges them: the neighbour now shows the sum,
and the dragged tile's cell stays empty.

```
uv run python -m engines.sumbreak examples/sumbreak/sumbreak1.png -o solved.png
```

## The rules, as tried on LinkedIn

The one-line rules leave a lot open, so on 2026-11-18 a guest tried them on
the first board (sumbreak1.png):
- **Neighbours** are the cells above, below, left and right. Two equal tiles
  on a diagonal don't merge.
- **Tiles never move.** An emptied cell stays empty, a tile can't be dragged
  into one, and a merge never reaches across one.
- **The sum goes where the tile is dropped.** Clicking a tile and then its
  neighbour does the same as dragging it there.
- **Undo** takes back the last merge, one per click. Ctrl+Z does nothing.
- **Two looks.** Some guests see square tiles; others see circles that grow
  with their number (sumbreak2.png, sumbreak3.png), on the same grid. With
  squares, an invisible button covers each whole cell, so a press anywhere
  in it counts. The circles' page wasn't looked into. Presses land at
  random up to 0.3 of a cell off the middle, which can be outside a 1's
  circle (0.19 of a cell across from its middle), and the one guest play
  whose result icon showed circles merged every tile.
- After the last merge, the lone tile shows for a moment, then a blank page
  with LinkedIn's logo, then the result screen (sumbreak-result1.png).

## Solver

Numbers only grow, so a tile with the smallest number on the board can only
ever merge with another tile of that number, and that tile must already be
its neighbour. So the smallest tiles are paired off first. Each one is a
*unit*, and its options are its merges: onto an equal neighbour, or that
neighbour onto it. The search branches on the unit with the fewest options.
One with none is a dead end, and one with a single option is forced.

A merge isn't an option if the board it leaves can't end in one tile:
* the tiles fall apart into groups with empty cells between them, which can
  never meet again;
* a tile has no neighbour with its number, or with a smaller one that could
  double up to it. Its neighbours only grow or leave, so it is stuck;
* the smallest tiles can't all be paired off with a neighbour. Neighbours are
  on cells of different colours of a chessboard, so this is a matching,
  found by augmenting paths;
* the tiles up to some number t, in a group that touches, add up to no whole
  number of tiles of 2t. They can only merge with each other until they
  reach 2t, and they can't stay smaller.

The checks are only valid on boards where every number is the smallest one
doubled, so `solve` returns None for any other board. Merging keeps a
number's odd part, so no other board can end in one tile anyway. Merges that
leave a hole at the edge of the board are tried first, because a hole in the
middle more often cuts the tiles apart later. Boards already seen to fail are
remembered.

Measured on 30 random boards per size. The generator breaks a tile in halves
again and again until the grid is full (`tests/sumbreak/generator.py`):

| Board | Median | Slowest | Boards with a wrong guess |
|---|---|---|---|
| 3x3 | 0.9 ms | 1.4 ms | 0 of 30 |
| 5x5 | 9.8 ms | 27 ms | 17 of 30 |
| 7x7 | 42 ms | 210 ms | 23 of 30 |
| 8x8 | 88 ms | 1.1 s | 24 of 30 |

These boards are crowded with small numbers, which pair up in the most ways.
With numbers as spread out as sumbreak1's (128 on a 3x3, three doublings more
than the fewest that fill it), 8x8 boards take at most 0.4 s. sumbreak1
itself takes 1 ms and no wrong guess. Without the checks, the search took up
to 7 s on 7x7 boards.

## OCR

There are no grid lines, so the shared grid finder can't be used; the tiles
show where the cells are.

1. **Tiles:** pixels whose colour channels differ by more than 40 (tiles
   90–200; the card, the page and an empty beige cell under 15) are cut into
   blobs of touching pixels, with a union-find over each row's runs. A blob is
   a tile if it is about as high as wide and fills at least 65% of its box (a
   square 98%, a circle 79%).
2. **Board:** tiles whose middles are level make up a row, and tiles one
   above the other a column. The step between cells is the most usual
   distance from a tile to the nearest one in its row or column. On a board
   that can be solved, every tile has a neighbour one step away. So the board
   is the biggest group of tiles linked that way, and coloured things
   elsewhere aren't part of it, even right above a column: a signed-in
   member's top bar has LinkedIn's blue logo, a red dot and a round photo.
3. **Grid:** the pitch is the board's span divided by its number of steps.
   Rows and columns may be empty, and every tile must sit within 15% of a
   pitch of its cell's middle. A board has at least 3 rows and 3 columns. The
   result screen's icon is a 2x2 board of numbers.
4. **Numbers:** a number is printed in a darker shade of its tile's colour.
   Its pixels, darker than halfway from the tile's colour to the darkest one,
   go to the shared glyph reader. Paler edges would close the gap of a small
   6, which then reads as 8.

Tested on the real board in both looks, at devicePixelRatio 1 and 2, on a
game in progress with emptied cells, and on the result screen (no board).
6x6 boards with empty cells are drawn the way LinkedIn draws them, as
squares and as circles, at both scales (`tests/sumbreak/pictures.py`), and
so is a top bar with things above two of the columns. A 2x screenshot reads
in about 0.13 s.

## Moves

Each merge is a drag from the tile onto its neighbour. A merge the solver
takes back is undone with the Undo button, one click per merge, newest first.
The player finds the button on the page by its text, because it isn't on the
board. On a big board the solver may take back dozens of merges. A person
tries a few things and then thinks harder instead, so only the first 5
merges that fail are made on the board. The search's later dead ends are
thought through without touching it.
