"""Vocabulary shared by the grid games."""

Cell = tuple[int, int]  # (row, col), 0-indexed from the top-left corner
Edge = frozenset[Cell]  # the border between two orthogonally adjacent cells
