# Sumbreak

LinkedIn tells guests: "Drag to combine matching neighbor cells. Repeat until
one cell remains." Every cell holds a numbered tile, or a x2 tile. Dragging a
tile onto a neighbour with the same number merges them: the neighbour now
shows the sum, and the dragged tile's cell stays empty. A x2 tile merges with
any number next to it and doubles it.

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

On 2026-11-20 the daily board (sumbreak5.png) had two **x2 tiles**: purple
squares with "×2" on a pale diamond, called "Multiply by 2" for screen
readers. The How to play a guest sees still has only the one line above, so
a guest tried them on that board:
- **A x2 tile doubles the number it merges with, either way round.** A 1
  dragged onto it leaves 2 on the x2 tile's cell; the x2 tile dragged onto a
  1 leaves 2 on the 1's cell. The x2 tile dragged onto a 4 leaves 8, and a 16
  dragged onto it leaves 32. Only neighbours were tried, and the solver
  merges it only with a neighbour, as any tile.
- **Undo** brings a merged x2 tile back.
- The board was won with 7 merges, ending in 32. Without doubling its
  numbers add up to 27, which no merges of equal numbers can make.
- **Not known:** what two x2 tiles do when merged. sumbreak5's aren't
  neighbours, so it wasn't tried, and the solver never merges two of them.
- **The look with circles** draws a x2 tile as a purple scalloped circle
  with "×2" in it, as big as a 4's circle (sumbreak6.png, the same board).

## Solver

Numbers only grow, so a tile with the smallest number on the board can only
ever merge with another tile of that number or with a x2 tile, and that tile
must already be its neighbour (a x2 tile that doubled something else shows
at least twice the smallest number). So the smallest tiles are paired off
first. Each one is a *unit*, and its options are its merges: onto an equal
or x2 neighbour, or that neighbour onto it. The search branches on the unit
with the fewest options. One with none is a dead end, and one with a single
option is forced.

A merge isn't an option if the board it leaves can't end in one tile:
* the tiles fall apart into groups with empty cells between them, which can
  never meet again;
* a tile has no neighbour with its number, with a smaller one that could
  double up to it, or a x2 tile. Its neighbours only grow or leave, so it is
  stuck;
* the smallest tiles can't each get a partner of their own: a neighbour with
  their number, or a x2 tile. Neighbours are on cells of different colours of
  a chessboard, so this is a matching, found by augmenting paths;
* the tiles up to some number t, in a group that touches, can't end up as
  tiles of 2t. They can only merge with each other and with the group's x2
  tiles until they reach 2t, and they can't stay smaller. Merging two keeps
  the group's sum, and a x2 tile adds a number up to t, the smallest one
  doubled a few times. So a group r short of a multiple of 2t needs at least
  as many x2 tiles as r, counted in smallest numbers, has ones in binary.

The checks are only valid on boards where every number is the smallest one
doubled, so `solve` returns None for any other board. Merging and doubling
keep a number's odd part, so no other board can end in one tile anyway.
Merges that leave a hole at the edge of the board are tried first, because a
hole in the middle more often cuts the tiles apart later. Boards already seen
to fail are remembered. Two x2 tiles are never merged, since what that does
is not known.

Measured on 30 random boards per size. The generator breaks a tile in halves
again and again until the grid is full, and on boards with x2 tiles some
breaks leave a half and a x2 tile instead (`tests/sumbreak/generator.py`):

| Board | x2 tiles | Median | Slowest | Boards with a wrong guess |
|---|---|---|---|---|
| 3x3 | none | 0.9 ms | 1.4 ms | 0 of 30 |
| 3x3 | 2 | 0.8 ms | 1.6 ms | 1 of 30 |
| 5x5 | none | 11 ms | 27 ms | 17 of 30 |
| 5x5 | 3 | 14 ms | 94 ms | 25 of 30 |
| 5x5 | 6 | 14 ms | 128 ms | 28 of 30 |
| 7x7 | none | 44 ms | 282 ms | 23 of 30 |
| 7x7 | 6 | 87 ms | 0.9 s | 28 of 30 |
| 7x7 | 12 | 181 ms | 1.3 s | 30 of 30 |
| 8x8 | none | 104 ms | 1.2 s | 24 of 30 |
| 8x8 | 8 | 245 ms | 0.8 s | 29 of 30 |
| 8x8 | 16 | 643 ms | 35 s | 29 of 30 |

These boards are crowded with small numbers, which pair up in the most ways.
A x2 tile goes with any number, so it adds ways too: with a quarter of an
8x8 board's cells x2 tiles, 13 of 30 boards take over a second, and the
slowest tries 68,000 merges. The daily boards so far are 3x3, with 2 x2
tiles on sumbreak5, which takes 0.3 ms. With numbers as spread out as
sumbreak1's (128 on a 3x3, three doublings more than the fewest that fill
it), 8x8 boards take at most 0.4 s, and with 8 x2 tiles 3.4 s (median
0.18 s). sumbreak1 itself takes 1 ms and no wrong guess. Without the checks, the search took up to 7 s on 7x7 boards.

## OCR

There are no grid lines, so the shared grid finder can't be used; the tiles
show where the cells are.

1. **Tiles:** pixels whose colour channels differ by more than 40 (tiles
   90–200; the card, the page and an empty beige cell under 15) are cut into
   blobs of touching pixels, with a union-find over each row's runs. A blob is
   a tile if it is about as high as wide and fills at least 65% of its box (a
   square 98%, a circle 79%, the scalloped x2 circle 75%). A x2 tile of a
   spikier shape would fill less (a 12-pointed star 55-67%), so a blob
   filling at least 40% is a tile too if it shows "×2".
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
   Its ink, the pixels darker than halfway from the tile's colour to the
   darkest one, is cut into marks at empty columns, by the shared
   `split_glyphs` that `read_number` uses too. Paler edges would close the
   gap of a small 6, which then reads as 8.
5. **x2:** the digits of a number are all as tall. A mark under 80% of the
   tallest is a sign, and so is one shaped like an x (two diagonals, give or
   take a pixel, and nothing at the middles of its sides, as a + would
   have). "×2" is printed in a greyish purple, its × 58-64% as tall as its 2
   and only 9 px across on circles. An x before the digits
   stands for "times": the digits after it are read, and 2 makes a x2 tile.
   The shared glyph reader always answers with its nearest digit and drops
   short marks, so a × would read as nothing and ×2 as 2: signs never reach
   it.
6. **Refused:** `scan` raises ValueError rather than guess for
   - a tile with any other sign: an x alone, as on the result screen's icon
     (sumbreak-result1.png), another factor such as ×4, or a sign that is no
     x;
   - a coloured shape on a cell, at least 0.3 of a cell across, that is no
     tile and doesn't show "×2", such as a special tile of an unknown shape.
     A tile that is not seen would otherwise be read as an empty cell. This
     only covers cells of the grid the tiles span: a row or column at the
     edge with nothing but such shapes on it is not seen at all.

   A symbol as tall as the digits and not shaped like an x is not caught: it
   goes to the shared glyph reader, which answers with its nearest digit (a
   + painted on a tile reads as 1). The daily check and the player take a board that `scan` refuses as no
   board: they never play it.

Tested on the real board in both looks, at devicePixelRatio 1 and 2, on a
game in progress with emptied cells, on the board with x2 tiles in both
looks at both scales, and on the result screen (no board). sumbreak5.png is also edited to
show an x alone and a ×4, which are refused. 6x6 boards with empty cells are
drawn the way LinkedIn draws them, as squares and as circles, at both scales
(`tests/sumbreak/pictures.py`), and so is a top bar with things above two of
the columns. So are 6x6 boards with x2 tiles: squares with a diamond, and
starbursts with shallow and with deep points, which are read; and starbursts
so spiky that they fill a third of their box, which are refused. A 2x
screenshot reads in about 0.12 s.

## Moves

Each merge is a drag from the tile onto its neighbour, a x2 tile's merges
too. A merge the solver takes back is undone with the Undo button, one click
per merge, newest first.
The player finds the button on the page by its text, because it isn't on the
board. On a big board the solver may take back dozens of merges. A person
tries a few things and then thinks harder instead, so only the first 5
merges that fail are made on the board. The search's later dead ends are
thought through without touching it.
