"""Seam: where the mouse goes for a cell of a grid found in a screenshot."""

from engines.play.screen import Screen
from engines.vision import GridGeometry, Lattice

# Columns start at x = 100 and rows at y = 40 in the screenshot; cells are 50 px.
GRID = GridGeometry(xs=Lattice(start=100, pitch=50, cells=6), ys=Lattice(start=40, pitch=50, cells=6))


def test_the_mouse_goes_to_the_middle_of_the_cell():
    assert Screen(GRID, scale=1).point((2, 3)) == (275, 165)


def test_a_high_resolution_screenshot_has_two_pixels_per_page_pixel():
    # Playwright screenshots in device pixels but moves the mouse in page (CSS) pixels.
    assert Screen(GRID, scale=2).point((2, 3)) == (137.5, 82.5)


def test_a_position_between_middles_is_measured_in_cells():
    # A quarter of a 50 px cell up and to the right of (2, 3)'s middle, on a 2x screen.
    assert Screen(GRID, scale=2).position(1.75, 3.25) == (143.75, 76.25)
