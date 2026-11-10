"""Seam: the timed mouse positions of a drag, in cells (no browser needed)."""

import random

import pytest

from engines.common.actions import Drag
from engines.play.motion import Hand, drag
from engines.zip.moves import moves as zip_moves
from tests.zip.generator import random_puzzle

STEADY = Hand(hesitate_chance=0)  # no random hesitations, to measure speed

# Along the top row, then down the right column: one turn, at (0, 5).
CORNER = tuple((0, c) for c in range(6)) + tuple((r, 5) for r in range(1, 6))
# Right to (0, 2), then back to (0, 1) and down: Zip backing out of a dead end.
DEAD_END = ((0, 0), (0, 1), (0, 2), (0, 1), (1, 1))


def cells_seen(timeline) -> list[tuple[int, int]]:
    """The cells the mouse is in, in order, each listed once per visit."""
    seen = []
    for _, row, col in timeline:
        cell = (round(row), round(col))
        if not seen or seen[-1] != cell:
            seen.append(cell)
    return seen


def zip_paths():
    """The drags Zip makes on random boards, some of them backing out of dead ends."""
    for seed in range(6):
        (drag_action,) = [a for a in zip_moves(random_puzzle(6, seed, numbers=8)) if isinstance(a, Drag)]
        yield drag_action.cells


@pytest.mark.parametrize("cells", list(zip_paths()))
def test_the_page_sees_exactly_the_cells_of_the_path_in_order(cells):
    assert cells_seen(drag(cells, random.Random(0))) == list(cells)


@pytest.mark.parametrize("cells", list(zip_paths()))
def test_the_mouse_crosses_from_cell_to_cell_well_away_from_the_corners(cells):
    # Near a corner it could touch a diagonal neighbour that isn't on the path.
    timeline = drag(cells, random.Random(0))

    assert not any(abs(row - round(row)) > 0.4 and abs(col - round(col)) > 0.4 for _, row, col in timeline)


def test_the_mouse_is_slower_at_a_turn_than_along_a_straight_run():
    timeline = drag(CORNER, random.Random(0), STEADY)

    speeds = {"turn": [], "straight": []}
    for (t0, r0, c0), (t1, r1, c1) in zip(timeline, timeline[1:]):
        if t1 > t0:
            where = "turn" if (round(r1), round(c1)) == (0, 5) else "straight"
            if (round(r1), round(c1)) in ((0, 2), (0, 3), (0, 5)):
                speeds[where].append(((r1 - r0) ** 2 + (c1 - c0) ** 2) ** 0.5 / (t1 - t0))
    average = {where: sum(s) / len(s) for where, s in speeds.items()}

    assert average["turn"] < 0.5 * average["straight"]


def test_the_hand_stops_for_a_moment_where_it_backs_out_of_a_dead_end():
    timeline = drag(DEAD_END, random.Random(0), STEADY)

    still = [
        t1 - t0
        for (t0, r0, c0), (t1, r1, c1) in zip(timeline, timeline[1:])
        if (r0, c0) == (r1, c1) and (round(r1), round(c1)) == (0, 2)
    ]
    assert still and max(still) >= 0.3


def test_the_hand_never_draws_the_same_path_twice_alike():
    first, second = (drag(CORNER, random.Random(seed)) for seed in (1, 2))

    assert first[-1][0] != second[-1][0], "different timing"
    assert [p[1:] for p in first] != [p[1:] for p in second], "different line"


def test_the_line_runs_off_the_middles_of_the_cells():
    timeline = drag(CORNER, random.Random(0))

    assert max(abs(row - round(row)) + abs(col - round(col)) for _, row, col in timeline) > 0.05


def test_a_short_drag_still_takes_about_half_a_second():
    # A one-cell patch: pressed and released in the same cell.
    durations = [drag(((2, 2), (2, 2)), random.Random(seed))[-1][0] for seed in range(20)]

    assert all(0.45 <= seconds <= 0.65 for seconds in durations)
