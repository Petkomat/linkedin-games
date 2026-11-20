# Patches

Tile the grid with rectangles. Each rectangle holds exactly one *root* (badge),
has the root's shape (square / tall / wide / any) and, if the badge shows a
number, has that area.

```
uv run python -m engines.patches examples/patches/patches1.png -o solved.png
```

| Module          | Role                                                                  |
| --------------- | --------------------------------------------------------------------- |
| `model.py`      | `Puzzle`, `Root`, `Shape`, `Rect`                                      |
| `solver.py`     | `solve(puzzle) -> {Root: Rect} \| None`, backtracking, first solution   |
| `ocr.py`        | `read_puzzle(png) -> Puzzle` (and `scan` with pixel geometry/colours)  |
| `render.py`     | Solution drawn over the screenshot                                     |

Grid finding, binary morphology and the digit reader are shared with the
other engines in [`engines/vision`](../vision).

## Solver

* **Candidates up front.** A numbered root only gets sizes that divide its
  number (7 → 1×7 or 7×1; a square 9 → only 3×3). Shape filters the rest, and
  any rectangle containing a second root is dropped. Each candidate is stored
  as a cell bitmask (a Python int), so an overlap test is a single AND.
* **Branch on the most constrained root**, the one with the fewest candidates
  still free.
* **Forward checks at every node:** a free cell no root can reach any more
  means a dead end. A free cell exactly one root can reach is *forced*, so
  that root keeps only candidates covering it. Two bitmasks track which cells
  one root can reach and which two or more can.
* Random 12×12 puzzles: the worst case drops from over 85 s (plain search) to
  about 0.15 s.

## OCR

1. **Grid.** Per column, count ridge pixels (darker than the pixels 2 px left
   and right). The longest evenly spaced run of peaks is the lattice. Rows are
   then counted only inside that span, and vice versa.
2. **Badge.** A cell's background is the median of its outer ring. The badge
   is the blob of clearly different colour that reaches the cell centre. This
   ignores part-drawn patches and the cursor.
3. **Shape.** The "any" badge is a plus sign, so its bounding-box corners are
   empty. Otherwise the aspect ratio gives square, tall or wide.
4. **Number.** White pixels inside the eroded badge, split into glyphs at
   empty columns. Each glyph is narrowed to digits with the same number of
   holes (font-independent), then matched by HOG descriptor against digits
   rendered from Pillow's bundled font at several stroke weights. No digit
   samples come from the screenshots, so the OCR tests aren't circular.
