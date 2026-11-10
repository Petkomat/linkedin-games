"""From board cells to mouse positions on the page."""

from __future__ import annotations

from dataclasses import dataclass

from ..common import Cell
from ..vision import GridGeometry


@dataclass(frozen=True)
class Screen:
    """Where a screenshot's grid is, for the mouse.

    `scale` is screenshot pixels per page pixel (the page's devicePixelRatio):
    2 on a high-resolution screen, where the screenshot has twice the pixels
    of the page coordinates the mouse is moved in.
    """

    grid: GridGeometry
    scale: float = 1.0

    def point(self, cell: Cell) -> tuple[float, float]:
        """Page position of the middle of `cell`."""
        x, y = self.grid.center(*cell)
        return x / self.scale, y / self.scale
