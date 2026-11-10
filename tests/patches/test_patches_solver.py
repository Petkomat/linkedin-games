import pytest

from engines.patches import Puzzle, Rect, Root, Shape, solve
from tests.helpers import solve_within

from .generator import random_puzzle


def assert_obeys_the_rules(puzzle: Puzzle, solution: dict[Root, Rect]) -> None:
    assert set(solution) == set(puzzle.roots)
    owner = {}
    for root, rect in solution.items():
        assert rect.top <= root.row < rect.top + rect.height, (root, rect)
        assert rect.left <= root.col < rect.left + rect.width, (root, rect)
        if root.size is not None:
            assert rect.height * rect.width == root.size, (root, rect)
        if root.shape is Shape.SQUARE:
            assert rect.height == rect.width, (root, rect)
        if root.shape is Shape.TALL:
            assert rect.height > rect.width, (root, rect)
        if root.shape is Shape.WIDE:
            assert rect.width > rect.height, (root, rect)
        for r in range(rect.top, rect.top + rect.height):
            for c in range(rect.left, rect.left + rect.width):
                assert (r, c) not in owner, f"{(r, c)} is in two patches"
                owner[(r, c)] = root
    assert len(owner) == puzzle.rows * puzzle.cols, "some cells are not covered"



def test_single_root_claims_the_whole_grid():
    root = Root(0, 0, Shape.ANY)
    puzzle = Puzzle(rows=2, cols=3, roots=(root,))

    assert solve(puzzle) == {root: Rect(top=0, left=0, height=2, width=3)}


def test_tall_roots_split_the_grid_into_columns():
    a, b = Root(0, 0, Shape.TALL), Root(1, 1, Shape.TALL)
    puzzle = Puzzle(rows=2, cols=2, roots=(a, b))

    assert solve(puzzle) == {a: Rect(0, 0, 2, 1), b: Rect(0, 1, 2, 1)}


def test_numbered_root_gets_exactly_that_area():
    a, b = Root(0, 0, Shape.ANY, size=2), Root(0, 2, Shape.ANY, size=1)
    puzzle = Puzzle(rows=1, cols=3, roots=(a, b))

    assert solve(puzzle) == {a: Rect(0, 0, 1, 2), b: Rect(0, 2, 1, 1)}


def test_unsolvable_puzzle_returns_none():
    # Two 1x1 patches can never tile a 2x2 grid.
    puzzle = Puzzle(rows=2, cols=2, roots=(Root(0, 0, Shape.ANY, 1), Root(1, 1, Shape.ANY, 1)))

    assert solve(puzzle) is None


def test_solves_the_patches3_example():
    # examples/patches/patches3.png shows this board already solved.
    roots = {
        "blue": Root(0, 1, Shape.ANY, 5),
        "gold": Root(0, 3, Shape.ANY, 3),
        "orange": Root(1, 5, Shape.ANY, 3),
        "red": Root(2, 0, Shape.ANY, 3),
        "purple": Root(2, 2, Shape.WIDE),
        "green": Root(3, 3, Shape.SQUARE),
        "teal": Root(3, 5, Shape.ANY, 3),
        "gray": Root(4, 0, Shape.ANY, 3),
        "magenta": Root(5, 2, Shape.ANY, 3),
        "brown": Root(5, 4, Shape.ANY, 3),
    }
    puzzle = Puzzle(rows=6, cols=6, roots=tuple(roots.values()))

    solution = solve(puzzle)

    assert solution == {
        roots["red"]: Rect(0, 0, 3, 1),
        roots["blue"]: Rect(0, 1, 5, 1),
        roots["gold"]: Rect(0, 2, 1, 3),
        roots["orange"]: Rect(0, 5, 3, 1),
        roots["purple"]: Rect(1, 2, 2, 3),
        roots["gray"]: Rect(3, 0, 3, 1),
        roots["green"]: Rect(3, 2, 2, 2),
        roots["brown"]: Rect(3, 4, 3, 1),
        roots["teal"]: Rect(3, 5, 3, 1),
        roots["magenta"]: Rect(5, 1, 1, 3),
    }


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("n", [10, 12])
def test_solves_random_puzzles_quickly(n, seed):
    puzzle = random_puzzle(n, seed)

    solution = solve_within(solve, puzzle, seconds=1.0)

    assert solution is not None
    assert_obeys_the_rules(puzzle, solution)
