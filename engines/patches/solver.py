"""Backtracking solver for Patches.

Every root gets a list of candidate rectangles up front. Only sizes that divide
the root's number and fit its shape are generated, and no candidate may contain
another root. Cells are bits in a Python int, so an overlap test is a single AND.

At every node of the search:
  * each unplaced root's candidates are filtered to those still free;
  * a free cell that no root can still reach means the branch is dead;
  * a free cell that only one root can reach is *forced* into that root,
    which drops all of its candidates that miss the cell;
  * we branch on the root with the fewest remaining candidates.
The search stops at the first complete tiling. Every patch it places and
every patch it removes again when a guess fails is written to `trace`.
"""

from __future__ import annotations

from ..common.trace import Trace
from .model import Puzzle, Rect, Root, Shape

Candidate = tuple[Rect, int]  # rectangle and its cell bitmask


def solve(puzzle: Puzzle, trace: Trace | None = None) -> dict[Root, Rect] | None:
    trace = Trace() if trace is None else trace
    root_bits = 0
    for root in puzzle.roots:
        root_bits |= _bit(root.row, root.col, puzzle.cols)

    candidates = {root: _candidates(root, puzzle, root_bits) for root in puzzle.roots}
    full = (1 << (puzzle.rows * puzzle.cols)) - 1
    placed: dict[Root, Rect] = {}

    def search(covered: int, remaining: list[Root]) -> bool:
        if not remaining:
            return covered == full
        branch = _choose_branch(candidates, covered, remaining, full)
        if branch is None:
            return False
        root, options = branch
        rest = [r for r in remaining if r is not root]
        mark = trace.mark()
        for rect, mask in options:
            placed[root] = rect
            trace.put(rect)
            if search(covered | mask, rest):
                return True
            trace.back_to(mark)
        del placed[root]
        return False

    return dict(placed) if search(0, list(puzzle.roots)) else None


def _choose_branch(
    candidates: dict[Root, list[Candidate]], covered: int, remaining: list[Root], full: int
) -> tuple[Root, list[Candidate]] | None:
    """Pick the most constrained root and its options, or None on a dead end."""
    live: list[tuple[Root, list[Candidate], int]] = []
    once = twice = 0  # free cells reachable by at least one / at least two roots
    for root in remaining:
        options = [c for c in candidates[root] if not c[1] & covered]
        if not options:
            return None
        reach = 0
        for _, mask in options:
            reach |= mask
        twice |= once & reach
        once |= reach
        live.append((root, options, reach))

    free = full & ~covered
    if once & free != free:  # a free cell that nobody can cover any more
        return None
    sole = free & ~twice  # free cells exactly one root can still cover

    best: tuple[Root, list[Candidate]] | None = None
    for root, options, reach in live:
        forced = sole & reach
        if forced:
            options = [c for c in options if c[1] & forced == forced]
            if not options:
                return None
        if best is None or len(options) < len(best[1]):
            best = (root, options)
    return best


def _bit(row: int, col: int, cols: int) -> int:
    return 1 << (row * cols + col)


def _rect_mask(rect: Rect, cols: int) -> int:
    row_bits = ((1 << rect.width) - 1) << rect.left
    mask = 0
    for r in range(rect.top, rect.top + rect.height):
        mask |= row_bits << (r * cols)
    return mask


def _shape_allows(shape: Shape, height: int, width: int) -> bool:
    if shape is Shape.SQUARE:
        return height == width
    if shape is Shape.TALL:
        return height > width
    if shape is Shape.WIDE:
        return width > height
    return True


def _dimensions(root: Root, rows: int, cols: int) -> list[tuple[int, int]]:
    """All (height, width) that fit the grid, the root's shape and its size.

    With a size we only walk its divisors, so a 7 is 1x7 or 7x1 and nothing else,
    and a SQUARE 9 is only 3x3.
    """
    if root.size is None:
        dims = [(h, w) for h in range(1, rows + 1) for w in range(1, cols + 1)]
    else:
        dims = [(h, root.size // h) for h in range(1, root.size + 1) if root.size % h == 0]
    return [
        (h, w) for h, w in dims if h <= rows and w <= cols and _shape_allows(root.shape, h, w)
    ]


def _candidates(root: Root, puzzle: Puzzle, root_bits: int) -> list[tuple[Rect, int]]:
    own_bit = _bit(root.row, root.col, puzzle.cols)
    out = []
    for height, width in _dimensions(root, puzzle.rows, puzzle.cols):
        for top in range(max(0, root.row - height + 1), min(root.row, puzzle.rows - height) + 1):
            for left in range(max(0, root.col - width + 1), min(root.col, puzzle.cols - width) + 1):
                rect = Rect(top, left, height, width)
                mask = _rect_mask(rect, puzzle.cols)
                if mask & root_bits == own_bit:  # contains its own root and no other
                    out.append((rect, mask))
    return out
