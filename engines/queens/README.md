# Queens

Place N queens on an N×N board of N coloured regions: one per row, column and
region, and no two touching, not even diagonally.

```
uv run python -m engines.queens examples/queens/queens1.png -o solved.png
```

## Solver

* Every row, column and region is a *unit* needing exactly one queen. The
  cells still open for a queen form one bitmask. A queen clears its row,
  column, region and its 8 neighbours from it, using a mask computed in advance.
* At each node: an open unit with no free cell is a dead end. One with a
  single free cell is forced. Otherwise branch on the unit with the fewest
  free cells, as in Patches and Sudoku.
* Random 14×14 boards: from more than 10 s (plain row-by-row backtracking) to
  under 10 ms. Every 16×16 test board finishes within 15 ms.

## OCR

1. **Grid:** the shared lattice finder in [`engines/vision`](../vision).
2. **Region colour:** the median of a cell's lighter pixels, so queens or
   crosses already on the board and the borders are ignored.
3. **Regions:** cells within an RGB distance of 25 share a region. On queens1,
   cells of one region match exactly and the closest two regions are 50 apart.
