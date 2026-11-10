"""Plain-text boards for the terminal."""

from __future__ import annotations

from collections.abc import Sequence
from string import ascii_letters, digits

_SYMBOLS = ascii_letters[26:] + ascii_letters[:26] + digits  # A-Z, then a-z, then 0-9


def letter(index: int) -> str:
    """A one-character name for item `index`: A, B, ..., Z, a, ..., z, 0, ..., 9."""
    return _SYMBOLS[index] if index < len(_SYMBOLS) else "?"


def board_text(rows: Sequence[Sequence[str]]) -> str:
    """One line per row, cells separated by spaces."""
    return "\n".join(" ".join(row) for row in rows)
