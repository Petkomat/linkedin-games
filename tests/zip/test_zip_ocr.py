from engines.zip import read_puzzle
from tests.helpers import example

from .boards import ZIP1, ZIP2


def test_reads_the_numbers():
    # zip1.png has the start of a path drawn over the 1, and the pointer on it.
    assert read_puzzle(example("zip", "zip1.png")) == ZIP1


def test_reads_the_walls():
    # zip2.jpg is a blurry video frame with half the path drawn, and buttons
    # below the board one row's height apart.
    assert read_puzzle(example("zip", "zip2.jpg")) == ZIP2
