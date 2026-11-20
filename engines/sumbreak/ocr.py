"""Read a Sumbreak board from a screenshot.

LinkedIn draws each tile as a coloured square or, for some guests, as a
coloured circle that grows with its number, on a pale card. An emptied cell is
pale beige or shows nothing. There are no grid lines, so the shared grid
finder (`engines.vision.grid`) has nothing to go on: the tiles themselves
show where the cells are.

1. **Tiles:** the clearly coloured pixels are cut into blobs, the groups of
   them that touch. A blob is a tile if it is about as high as wide and fills
   most of its box: a square nearly all of it, a circle 79%. Text, confetti
   and specks don't.
2. **Board:** tiles whose middles are as high (or as far left) as each
   other's are in one row (column). The step between cells is the most usual
   distance from a tile to the nearest one in its row or column. On a board
   that can be solved, every tile has a neighbour one step away, so the
   board is the biggest group of tiles linked that way. Coloured things
   elsewhere on the page, such as a signed-in member's logo and photo in the
   top bar, are not linked to it, even when they sit above a column.
3. **Grid:** the board's rows and columns are evenly spaced, and a row or
   column may be empty: every step between two of them must be a whole
   number of pitches.
4. **Numbers:** a tile's number is printed in a darker shade of its colour.
   Its pixels go to the shared glyph reader.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, Lattice, load_rgb, read_number
from ..vision.morphology import crop
from .model import DOUBLE, Puzzle, Tile

COLOURFUL = 40  # a pixel whose channels differ by more than this is part of a tile (tiles ~90-200, the card 5)
MIN_SIDE = 12  # px; anything smaller can't hold a readable number
ROUND = 0.8  # a tile's box is at most this far from square (height / width)
FILLED = 0.65  # share of its box a tile fills: a square ~0.98, a circle 0.79, a letter less
ALIGNED = 0.25  # of the usual tile's side: how far apart middles in one row or column may be
LINKED = 1.5  # steps between cells: neighbours on the board are 1 apart, the next tiles but one 2
ON_LATTICE = 0.15  # of the pitch: how far a tile's middle may be off its cell's
MIN_CELLS = 3  # rows and columns; LinkedIn's result screen has a 2x2 board as an icon
DARKER = 50  # a number's pixels are darker than their tile by more than this
SPECK = 0.3  # of the tallest mark on a tile: anything shorter is a speck, not a mark
SIGN = 0.8  # of the tallest mark: a shorter one is a sign, not a digit (the x of x2 is 0.58 of its 2)
STROKES = 0.8  # share of an x's two diagonals that are ink


@dataclass(frozen=True)
class Scan:
    """What `scan` saw: the puzzle plus where its grid is in the image."""

    puzzle: Puzzle
    grid: GridGeometry


@dataclass(frozen=True)
class _Tile:
    top: int
    left: int
    bottom: int  # exclusive
    right: int  # exclusive

    @property
    def middle(self) -> tuple[float, float]:
        return (self.left + self.right) / 2, (self.top + self.bottom) / 2

    @property
    def side(self) -> int:
        return min(self.bottom - self.top, self.right - self.left)


def read_puzzle(image: ImageSource) -> Puzzle:
    return scan(image).puzzle


def scan(image: ImageSource) -> Scan:
    rgb = load_rgb(image)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]  # 5x faster than max and min along the colour axis
    colourful = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b) > COLOURFUL
    tiles = [tile for tile in _blobs(colourful) if _is_tile(tile, colourful)]
    if not tiles:
        raise ValueError("no tiles in the image")
    tolerance = ALIGNED * float(np.median([tile.side for tile in tiles]))
    tiles = _on_board(tiles, tolerance)
    xs = _lattice([tile.middle[0] for tile in tiles], tolerance)
    ys = _lattice([tile.middle[1] for tile in tiles], tolerance)
    if abs(ys.pitch / xs.pitch - 1) > ON_LATTICE:
        raise ValueError("the tiles are not on a grid of square cells")
    grid = GridGeometry(xs, ys)
    numbers: list[list[int | None]] = [[None] * grid.cols for _ in range(grid.rows)]
    for tile in tiles:
        x, y = tile.middle
        row, col = _index(y, ys), _index(x, xs)
        box = slice(tile.top, tile.bottom), slice(tile.left, tile.right)
        label = _label(rgb[box], colourful[box])
        if label is None or numbers[row][col] is not None:
            raise ValueError(f"no single number on the tile in row {row + 1}, column {col + 1}")
        if isinstance(label, str) and label != DOUBLE:
            raise ValueError(f"a tile showing {label} in row {row + 1}, column {col + 1}: only numbers and x2 are known")
        numbers[row][col] = label
    return Scan(Puzzle(tuple(tuple(row) for row in numbers)), grid)


def _blobs(mask: np.ndarray) -> list[_Tile]:
    """The boxes of the groups of True pixels that touch (side by side or one
    above the other).

    Each row's runs of True pixels are joined with the runs they overlap in the
    row above, in a union-find, so it takes one pass however big a blob is."""
    padded = np.zeros((mask.shape[0], mask.shape[1] + 2), dtype=np.int8)
    padded[:, 1:-1] = mask
    steps = np.diff(padded, axis=1)
    rows, starts = np.nonzero(steps == 1)
    _, ends = np.nonzero(steps == -1)  # in the same order: row by row, left to right
    parent = list(range(len(rows)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first_in_row = np.searchsorted(rows, np.arange(mask.shape[0] + 1))
    for y in range(1, mask.shape[0]):
        above, here = range(first_in_row[y - 1], first_in_row[y]), range(first_in_row[y], first_in_row[y + 1])
        i, j = above.start, here.start
        while i < above.stop and j < here.stop:
            if starts[i] < ends[j] and starts[j] < ends[i]:
                parent[root(j)] = root(i)
            if ends[i] < ends[j]:
                i += 1
            else:
                j += 1

    boxes: dict[int, list[int]] = {}
    for k in range(len(rows)):
        box = boxes.setdefault(root(k), [rows[k], starts[k], rows[k] + 1, ends[k]])
        box[0], box[1] = min(box[0], rows[k]), min(box[1], starts[k])
        box[2], box[3] = max(box[2], rows[k] + 1), max(box[3], ends[k])
    return [_Tile(int(t), int(l), int(b), int(r)) for t, l, b, r in boxes.values()]


def _is_tile(tile: _Tile, colourful: np.ndarray) -> bool:
    height, width = tile.bottom - tile.top, tile.right - tile.left
    if min(height, width) < MIN_SIDE or min(height, width) < ROUND * max(height, width):
        return False
    return colourful[tile.top : tile.bottom, tile.left : tile.right].mean() >= FILLED


def _on_board(tiles: list[_Tile], tolerance: float) -> list[_Tile]:
    """The biggest group of tiles linked by neighbours one step apart in a row
    or a column, the step being the most usual distance between such tiles."""

    def apart(a: _Tile, b: _Tile) -> float | None:
        """How far apart in their row or column; None if in neither."""
        (ax, ay), (bx, by) = a.middle, b.middle
        if abs(ay - by) <= tolerance:
            return abs(ax - bx)
        return abs(ay - by) if abs(ax - bx) <= tolerance else None

    nearest = [
        min((d for other in tiles if other is not tile and (d := apart(tile, other)) is not None), default=None)
        for tile in tiles
    ]
    steps = [d for d in nearest if d is not None]
    if not steps:
        return []
    reach = LINKED * float(np.median(steps))
    left = set(range(len(tiles)))
    groups = []
    while left:
        group, todo = set(), [left.pop()]
        while todo:
            i = todo.pop()
            group.add(i)
            linked = {j for j in left if (d := apart(tiles[i], tiles[j])) is not None and d <= reach}
            left -= linked
            todo += linked
        groups.append(group)
    return [tiles[i] for i in max(groups, key=len)]


def _lattice(middles: list[float], tolerance: float) -> Lattice:
    """The rows (or columns) through `middles`: evenly spaced, some maybe empty."""
    lines: list[list[float]] = []
    for middle in sorted(middles):
        if lines and middle - lines[-1][-1] <= tolerance:
            lines[-1].append(middle)
        else:
            lines.append([middle])
    centres = [sum(line) / len(line) for line in lines]
    if len(centres) < 2:
        raise ValueError("the tiles are not on a grid")
    span = centres[-1] - centres[0]
    pitch = span / round(span / min(b - a for a, b in zip(centres, centres[1:])))  # averaged over the board
    steps = [(c - centres[0]) / pitch for c in centres]
    if any(abs(step - round(step)) > ON_LATTICE for step in steps):
        raise ValueError("the tiles are not evenly spaced")
    cells = round(steps[-1]) + 1
    if cells < MIN_CELLS:
        raise ValueError(f"{cells} rows or columns of tiles is too few for a board")
    return Lattice(centres[0] - pitch / 2, pitch, cells)


def _index(middle: float, lattice: Lattice) -> int:
    return int((middle - lattice.start) // lattice.pitch)


def _label(box: np.ndarray, colourful: np.ndarray) -> Tile | None:
    """What a tile shows, from the pixels of its box: its number, DOUBLE for
    "x2", what else it shows if it has a sign ("x", "x4", "an unknown sign"),
    or None if it shows nothing.

    The tile's own colour is the most common one in it. The ink is the pixels
    darker than halfway to its darkest: the paler edges of small, blurry
    digits would close the gap in a 6, which then reads as 8. The ink may be
    grey: "x2" is printed in a greyish purple.

    The digits of a number are all as tall. A shorter mark is a sign, and so
    is an x of any height: the result screen's icon shows a tile with only an
    x on it. An x before the digits stands for "times"; any other sign is not
    known. A speck is no mark."""
    brightness = box.mean(axis=2)
    colour = np.median(brightness[colourful])
    darkest = brightness.min()
    if darkest > colour - DARKER:
        return None
    ink = brightness < (colour + darkest) / 2
    marks = _marks(ink)
    tallest = max(mark.shape[0] for _, mark in marks)
    marks = [(left, mark) for left, mark in marks if mark.shape[0] >= SPECK * tallest]
    signs = [i for i, (_, mark) in enumerate(marks) if mark.shape[0] < SIGN * tallest or _is_times(mark)]
    if not signs:
        return read_number(ink.astype(float))
    if signs != [0] or not _is_times(marks[0][1]):
        return "an unknown sign"
    left, sign = marks[0]
    digits = ink.copy()
    digits[:, : left + sign.shape[1]] = False
    factor = read_number(digits.astype(float))
    return "x" if factor is None else DOUBLE if factor == 2 else f"x{factor}"


def _marks(ink: np.ndarray) -> list[tuple[int, np.ndarray]]:
    """The ink cut at empty columns into marks, left to right: where each
    starts, and its pixels cut to their box."""
    columns = np.flatnonzero(ink.any(axis=0))
    runs = np.split(columns, np.flatnonzero(np.diff(columns) > 1) + 1)
    return [(int(run[0]), crop(ink[:, run[0] : run[-1] + 1])) for run in runs]


def _is_times(mark: np.ndarray) -> bool:
    """Is `mark` an x: two strokes from corner to corner, with nothing at the
    middles of its sides (as a + would have)?"""
    height, width = mark.shape
    if not ROUND <= width / height <= 1 / ROUND:
        return False
    rows = np.arange(height)
    cols = np.round(rows * (width - 1) / max(1, height - 1)).astype(int)
    on_strokes = np.concatenate([mark[rows, cols], mark[rows, width - 1 - cols]]).mean()
    band_h, band_w = max(1, height // 5), max(1, width // 5)
    across = slice(2 * height // 5, 3 * height // 5 + 1), slice(2 * width // 5, 3 * width // 5 + 1)
    sides = mark[:band_h, across[1]], mark[-band_h:, across[1]], mark[across[0], :band_w], mark[across[0], -band_w:]
    return on_strokes >= STROKES and not any(side.any() for side in sides)
