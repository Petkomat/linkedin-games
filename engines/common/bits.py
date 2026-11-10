"""Python ints as bit sets, which the solvers use for sets of cells or digits."""

from __future__ import annotations

from collections.abc import Iterator


def set_bits(mask: int) -> Iterator[int]:
    """Indices of the 1 bits of `mask`, lowest first."""
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low
