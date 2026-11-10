"""English words for Wend.

`enable1.txt` is the ENABLE word list (Enhanced North American Benchmark
LEXicon), which is in the public domain: 172,823 lower-case words, one per
line, as published at github.com/dolph/dictionary.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

WORD_LIST = Path(__file__).with_name("enable1.txt")


@cache
def english_words() -> frozenset[str]:
    """Every word in the list, upper case (the board shows capitals)."""
    return frozenset(WORD_LIST.read_text(encoding="ascii").upper().split())


@cache
def words_of_length(n: int) -> tuple[frozenset[str], frozenset[str]]:
    """The n-letter words, and every proper prefix of them (to prune a search early)."""
    words = frozenset(w for w in english_words() if len(w) == n)
    prefixes = frozenset(w[:k] for w in words for k in range(1, n))
    return words, prefixes
