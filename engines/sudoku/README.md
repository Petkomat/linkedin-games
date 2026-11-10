# Sudoku

LinkedIn's Mini Sudoku is 6×6 with 2×3 boxes. The engine works for any N×N
board; the box shape is the most square one that divides N (9 → 3×3).

```
uv run python -m engines.sudoku examples/sudoku/sudoku1.png -o solved.png
```

## Solver

Same principles as the Patches solver:

* **Candidates as bitmasks**, one int per cell.
* **Forced moves first.** Removing a candidate propagates. A cell with one
  candidate left takes it (naked single). A digit with one possible cell left
  in a row, column or box goes there (hidden single).
* **Dead ends:** a cell with no candidates, or a digit with nowhere left to go
  in some row, column or box. Givens that contradict each other are caught
  the same way, so `solve` returns `None`.
* **Branch on the empty cell with the fewest candidates.** Stop at the first
  solution.

A 6×6 board is solved instantly by anything, so the heuristics are tested on
famously hard 9×9 puzzles. "Anti brute force" took more than 20 s with plain
row-by-row backtracking and takes 2 ms here. The others take at most about
20 ms.

## OCR

1. **Grid:** the shared lattice finder in [`engines/vision`](../vision). It
   also sees the 4 px box borders, by comparing pixels 2 and 4 px apart.
2. **Givens:** in each cell (inset past the thick borders), ink is darkness
   relative to the cell's median, so highlighted cells still work.
3. **Digits:** the shared HOG + hole-count reader, matched against Pillow's
   bundled font.
