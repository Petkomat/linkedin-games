"""How a hand moves the mouse: where it presses, and how it drags through cells.

A drag through a path of cells is cut into *strokes*, straight runs from one
turn to the next. Each stroke:
- starts slowly, is fastest in the middle and slows down again before the
  turn. This is a minimum-jerk speed profile, the way people move a hand from
  A to B, blended with a little even speed so the hand never quite stops;
- takes longer the longer it is, at a speed that varies from stroke to stroke;
- runs a little off the middles of its cells, because each turn is aimed at a
  random spot near the turning cell's middle, so runs lean slightly.

Corners are cut in a small curve inside the turning cell. Now and then the
hand hesitates at a turn, and it always stops for a moment where it goes back
the way it came, which is Zip backing out of a dead end.

Positions are in cells: (row, col), with each cell's middle on whole numbers,
so rounding a position gives its cell. Every position stays well inside a
cell of the path, and two positions in a row are at most STEP apart, so the
page sees exactly the path's cells, in order.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from ..common import Cell

Point = tuple[float, float]  # (row, col) in cells
Timed = tuple[float, float, float]  # (seconds since the press, row, col)

FRAME = 1 / 60  # s between two mouse positions
STEP = 0.25  # cells: the farthest apart two positions in a row may be
PEAK_SPEED = 1.7  # the fastest point of a stroke, as a multiple of its average speed
EASE = 0.75  # share of a stroke that follows the minimum-jerk profile; the rest is even
SPOT_SPREAD, SPOT_REACH = 0.15, 0.3  # where the mouse is pressed or released, in cells
AIM_SPREAD, AIM_REACH = 0.08, 0.15  # how far off a turning cell's middle the hand aims
CUT = (0.1, 0.2)  # cells before a turn where the hand starts its curve


@dataclass(frozen=True)
class Hand:
    """How fast and how steadily the hand moves; times in seconds."""

    stroke: float = 0.15  # every stroke, however short
    per_cell: float = 0.07  # plus this for each cell it runs
    speed_spread: float = 0.15  # standard deviation of a stroke's time factor (1 = as above)
    corner: float = 0.08  # the curve at a turn
    hesitate_chance: float = 0.2  # of pausing at a turn
    hesitation: tuple[float, float] = (0.1, 0.3)
    dead_end: tuple[float, float] = (0.3, 0.6)  # stop where it goes back the way it came
    shortest: float = 0.5  # a drag takes at least this (times 1 to 1.2), e.g. a patch


INSTANT = Hand(0, 0, 0, 0, 0, (0, 0), (0, 0), 0)  # for tests: the same path, without waiting


def spot(rng: random.Random) -> Point:
    """Where in a cell the mouse is pressed or released, as (row, col) from its
    middle: a bell curve around the middle, cut off well before the edges."""
    return _bell(rng, SPOT_SPREAD, SPOT_REACH), _bell(rng, SPOT_SPREAD, SPOT_REACH)


def drag(cells: Sequence[Cell], rng: random.Random, hand: Hand = Hand()) -> list[Timed]:
    """The timed positions of a drag that presses on the first cell, goes
    through the others in order and releases on the last one.

    Consecutive cells are neighbours, except for a patch, whose drag goes
    straight from one corner to the opposite one."""
    timeline = [(0.0, *_plus(cells[0], spot(rng)))]
    entry = timeline[0][1:]
    for before, cell, after in zip(cells, cells[1:], cells[2:]):
        way_in, way_out = _way(before, cell), _way(cell, after)
        if way_in == way_out:
            continue
        aim = _plus(cell, (_bell(rng, AIM_SPREAD, AIM_REACH), _bell(rng, AIM_SPREAD, AIM_REACH)))
        if way_out == (-way_in[0], -way_in[1]):  # back the way it came
            _stroke(timeline, entry, aim, rng, hand)
            _hold(timeline, rng.uniform(*hand.dead_end))
            entry = aim
        else:
            cut = rng.uniform(*CUT)
            corner_in = (aim[0] - cut * way_in[0], aim[1] - cut * way_in[1])
            corner_out = (aim[0] + cut * way_out[0], aim[1] + cut * way_out[1])
            _stroke(timeline, entry, corner_in, rng, hand)
            if rng.random() < hand.hesitate_chance:
                _hold(timeline, rng.uniform(*hand.hesitation))
            _curve(timeline, corner_in, aim, corner_out, hand.corner * _factor(rng, hand))
            entry = corner_out
    _stroke(timeline, entry, _plus(cells[-1], spot(rng)), rng, hand)
    return _at_least(timeline, hand.shortest * rng.uniform(1.0, 1.2))


def _stroke(timeline: list[Timed], start: Point, end: Point, rng: random.Random, hand: Hand) -> None:
    """A straight run: slow, fast, slow."""
    length = math.dist(start, end)
    seconds = (hand.stroke + hand.per_cell * length) * _factor(rng, hand)
    steps = max(1, math.ceil(seconds / FRAME), math.ceil(PEAK_SPEED * length / STEP))
    began = timeline[-1][0]
    for k in range(1, steps + 1):
        tau = k / steps
        share = EASE * (10 * tau**3 - 15 * tau**4 + 6 * tau**5) + (1 - EASE) * tau
        timeline.append((began + seconds * tau, *_between(start, end, share)))


def _curve(timeline: list[Timed], start: Point, control: Point, end: Point, seconds: float) -> None:
    """A corner cut as a quadratic Bezier curve from `start` to `end`."""
    steps = max(1, math.ceil(seconds / FRAME), math.ceil((math.dist(start, control) + math.dist(control, end)) / STEP))
    began = timeline[-1][0]
    for k in range(1, steps + 1):
        u = k / steps
        point = tuple((1 - u) ** 2 * s + 2 * u * (1 - u) * c + u**2 * e for s, c, e in zip(start, control, end))
        timeline.append((began + seconds * u, *point))


def _hold(timeline: list[Timed], seconds: float) -> None:
    """Keep still for `seconds`."""
    t, row, col = timeline[-1]
    timeline.append((t + seconds, row, col))


def _at_least(timeline: list[Timed], seconds: float) -> list[Timed]:
    """The timeline slowed down evenly if it is shorter than `seconds`."""
    total = timeline[-1][0]
    if total == 0 or total >= seconds:
        return timeline
    return [(t * seconds / total, row, col) for t, row, col in timeline]


def _factor(rng: random.Random, hand: Hand) -> float:
    """How much slower or faster than usual this stroke is."""
    return min(1.4, max(0.7, rng.gauss(1, hand.speed_spread)))


def _bell(rng: random.Random, spread: float, reach: float) -> float:
    return min(reach, max(-reach, rng.gauss(0, spread)))


def _way(a: Cell, b: Cell) -> tuple[int, int]:
    return b[0] - a[0], b[1] - a[1]


def _plus(cell: Cell, offset: Point) -> Point:
    return cell[0] + offset[0], cell[1] + offset[1]


def _between(start: Point, end: Point, share: float) -> Point:
    return start[0] + (end[0] - start[0]) * share, start[1] + (end[1] - start[1]) * share
