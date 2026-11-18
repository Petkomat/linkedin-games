"""A stand-in for the player's clock, so that timing checks don't depend on how
busy the machine is: its time moves only when the player waits, or when the
stand-in page says something took a while."""

from __future__ import annotations

from engines.play.browser import Clock


class StandInClock(Clock):
    def __init__(self) -> None:
        self.time = 0.0

    def now(self) -> float:
        return self.time

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("sleep length must be non-negative")  # as time.sleep says
        self.time += seconds

    def spend(self, seconds: float) -> None:
        """Something other than waiting takes `seconds`, such as a mouse move."""
        self.time += seconds
