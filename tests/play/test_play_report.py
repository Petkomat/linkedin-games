"""Seam: the readable solution saved next to each play's screenshot."""

from datetime import datetime

from engines.play.games import GAMES
from engines.play.report import report
from engines.sudoku import Puzzle as SudokuPuzzle
from engines.sumbreak import Puzzle as SumbreakPuzzle
from engines.zip import Puzzle as ZipPuzzle
from tests.sudoku.boards import SUDOKU1

STARTED = datetime(2026, 11, 10, 14, 3, 7)


def test_a_sudoku_is_saved_as_its_table_of_digits():
    assert report(GAMES["sudoku"], SudokuPuzzle(SUDOKU1), STARTED) == """\
# Sudoku, 2026-11-10 14:03:07

```
1 2 3 | 4 5 6
5 4 6 | 2 1 3
-------------
2 3 4 | 5 6 1
6 5 1 | 3 2 4
-------------
4 6 2 | 1 3 5
3 1 5 | 6 4 2
```

Lines separate the boxes.
"""


def test_a_zip_is_saved_as_the_order_in_which_the_path_visits_the_cells():
    puzzle = ZipPuzzle(rows=2, cols=2, numbers={(0, 0): 1, (1, 0): 2})

    assert report(GAMES["zip"], puzzle, STARTED) == """\
# Zip, 2026-11-10 14:03:07

```
1 2
4 3
```

The order in which the path visits each cell; 1 is the start.
"""


def test_a_sumbreak_is_saved_as_when_and_where_each_tile_is_dragged():
    # 1 + 1 = 2 to the right, 2 + 2 = 4 up, 4 + 4 = 8 to the right, 8 + 8 = 16 down
    puzzle = SumbreakPuzzle(((1, 1, 4), (None, 2, 8)))

    assert report(GAMES["sumbreak"], puzzle, STARTED) == """\
# Sumbreak, 2026-11-10 14:03:07

```
1> 3> 4v
 . 2^  *
```

Each tile is dragged onto the neighbour its arrow points to, in the merge with its number (1 is the first). * is the tile left at the end, . an empty cell.
"""


def test_every_game_saves_a_legend():
    assert all(game.legend for game in GAMES.values())
