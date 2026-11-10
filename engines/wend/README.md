# Wend

The board is a grid of letter tiles, some cells grey (no tile). Find the hidden
words of the given lengths:
- Each word runs along a path of tiles, stepping up, down, left or right.
- Every tile is used by exactly one word.

```
uv run python -m engines.wend examples/wend/wend2.png -o solved.png
```

## Dictionary

[`enable1.txt`](enable1.txt) is the ENABLE word list (172,823 words, public
domain), unchanged from github.com/dolph/dictionary. It includes rare words,
but both examples still have exactly one answer with it.

## Solver: placements, then an exact cover

1. **Placements:** for each word length asked for, every path of tiles that
   spells a word of that length. The path search stops as soon as its letters
   stop being the start of any word of that length (a prefix set).
2. **Exact cover:** choose placements so that every tile is used exactly once
   and each length is used as often as asked. **Branch on the free tile that
   the fewest placements can still cover**, the same principle as the other
   solvers: no placements left is a dead end, and one is a forced move.

Boards hide decoy words, and the solver never commits to a word on its own:
a word is only kept if the rest of the board can still be covered. wend2
spells 10 three-letter words (HOG, GIN, NIL, ...), 8 four-letter words (GOLD,
WING, LINE, ...) and two six-letter ones (ENGINE, ENGILD), yet only one set
of words uses every tile.

Random 8×8 boards (random words written along a random path through every
cell):
- Picking one placement per length, in the order given, took more than 1 s on
  half of them.
- Branching on the tile with the fewest placements takes at most 17 ms.
- 10×10 takes at most 0.9 s and 12×12 up to 46 s. Real boards are 5×5.

## OCR

1. **Grid:** the shared lattice finder in [`engines/vision`](../vision).
   wend2.png is a high-resolution screenshot whose lines are too thick for it,
   so the finder retries on a half-size copy when the cells it finds aren't
   square.
2. **Grey cells:** a cell whose middle is a flat mid grey has no tile. Tiles
   are white, or green / pink while the player is selecting a word.
3. **Letters:** the tile's dark pixels go to the shared HOG glyph reader
   (`engines/vision/glyphs.py`). It narrows the candidates by number of holes
   (A, D, O, P, Q, R have one; B has two), then compares them with letters
   rendered from Pillow's bundled font.
4. **Word lengths:** below the board, each word is a row of light grey
   squares. The squares in each row are counted; the wide grey Undo button
   isn't square, so it doesn't count. wend1.png is cropped above them, so it
   reads no lengths.

A tile covered by the mouse pointer can't be read, so take screenshots with
the pointer off the board.
