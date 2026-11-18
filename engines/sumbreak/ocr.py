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
2. **Grid:** the board's tiles line up in rows and columns. Tiles whose
   middles are as high (or as far left) as each other's make up a row (a
   column). Tiles alone in their row or column are something else on the
   page, such as an icon. The pitch is the smallest step between two rows or
   columns, and every other step must be a whole number of pitches: a row or
   column may be empty.
3. **Numbers:** a tile's number is printed in a darker shade of its colour.
   Its pixels go to the shared glyph reader.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import GridGeometry, ImageSource, Lattice, load_rgb, read_number
from .model import Puzzle

COLOURFUL = 40  # a pixel whose channels differ by more than this is part of a tile (tiles ~90-200, the card 5)
MIN_SIDE = 12  # px; anything smaller can't hold a readable number
ROUND = 0.8  # a tile's box is at most this far from square (height / width)
FILLED = 0.65  # share of its box a tile fills: a square ~0.98, a circle 0.79, a letter less
ALIGNED = 0.25  # of the smallest tile's side: how far apart middles in one row or column may be
ON_LATTICE = 0.15  # of the pitch: how far a tile's middle may be off its cell's
MIN_CELLS = 3  # rows and columns; LinkedIn's result screen has a 2x2 board as an icon
DARKER = 50  # a number's pixels are darker than their tile by more than this


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
    colourful = rgb.max(axis=2) - rgb.min(axis=2) > COLOURFUL
    tiles = _on_board([tile for tile in _blobs(colourful) if _is_tile(tile, colourful)])
    xs = _lattice([tile.middle[0] for tile in tiles], tiles)
    ys = _lattice([tile.middle[1] for tile in tiles], tiles)
    if xs.pitch and abs(ys.pitch / xs.pitch - 1) > ON_LATTICE:
        raise ValueError("the tiles are not on a grid of square cells")
    grid = GridGeometry(xs, ys)
    numbers: list[list[int | None]] = [[None] * grid.cols for _ in range(grid.rows)]
    for tile in tiles:
        x, y = tile.middle
        row, col = _index(y, ys), _index(x, xs)
        number = _number(rgb[tile.top : tile.bottom, tile.left : tile.right], colourful[tile.top : tile.bottom, tile.left : tile.right])
        if number is None or numbers[row][col] is not None:
            raise ValueError(f"no single number on the tile in row {row + 1}, column {col + 1}")
        numbers[row][col] = number
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


def _on_board(tiles: list[_Tile]) -> list[_Tile]:
    """The tiles that share a row and a column with other tiles, again and
    again until no more drop out."""
    while True:
        tolerance = ALIGNED * min((tile.side for tile in tiles), default=0)
        kept = [
            tile
            for tile in tiles
            if sum(abs(other.middle[1] - tile.middle[1]) <= tolerance for other in tiles) > 1
            and sum(abs(other.middle[0] - tile.middle[0]) <= tolerance for other in tiles) > 1
        ]
        if len(kept) == len(tiles):
            return kept
        tiles = kept


def _lattice(middles: list[float], tiles: list[_Tile]) -> Lattice:
    """The rows (or columns) through `middles`: evenly spaced, some maybe empty."""
    if not tiles:
        raise ValueError("no tiles in the image")
    tolerance = ALIGNED * min(tile.side for tile in tiles)
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


def _number(box: np.ndarray, colourful: np.ndarray) -> int | None:
    """The number on a tile, from the pixels of its box.

    The tile's own colour is the most common one in it. The number's pixels
    are those darker than halfway to its darkest: the paler edges of small,
    blurry digits would close the gap in a 6, which then reads as 8."""
    brightness = box.mean(axis=2)
    colour = np.median(brightness[colourful])
    darkest = brightness[colourful].min()
    if darkest > colour - DARKER:
        return None
    return read_number((colourful & (brightness < (colour + darkest) / 2)).astype(float))
