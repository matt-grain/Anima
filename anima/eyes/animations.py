# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Animation classes for smooth transitions and variations.
"""

import time


def millis() -> int:
    """Get current time in milliseconds."""
    return int(time.time() * 1000)


class RampAnimation:
    """Linear ramp from 0 to 1 over interval."""

    def __init__(self, interval: int, speed_multiplier: float = 1.0):
        self._base_interval = interval
        self.speed_multiplier = speed_multiplier
        self.start_time = millis()

    @property
    def interval(self) -> int:
        return int(self._base_interval / max(0.1, self.speed_multiplier))

    def restart(self):
        self.start_time = millis()

    def get_elapsed(self) -> int:
        return millis() - self.start_time

    def get_value(self) -> float:
        elapsed = self.get_elapsed()
        if self.interval <= 0:
            return 1.0
        if elapsed < self.interval:
            return elapsed / self.interval
        return 1.0


class TrapeziumAnimation:
    """Trapezium-shaped animation (ramp up, hold, ramp down)."""

    def __init__(self, t0: int, t1: int, t2: int, speed_multiplier: float = 1.0):
        self._t0 = t0  # Ramp up time
        self._t1 = t1  # Hold time
        self._t2 = t2  # Ramp down time
        self.speed_multiplier = speed_multiplier
        self.start_time = millis()

    @property
    def interval(self) -> int:
        return int((self._t0 + self._t1 + self._t2) / max(0.1, self.speed_multiplier))

    def restart(self):
        self.start_time = millis()

    def get_elapsed(self) -> int:
        return millis() - self.start_time

    def get_value(self) -> float:
        speed = max(0.1, self.speed_multiplier)
        t0 = int(self._t0 / speed)
        t1 = int(self._t1 / speed)
        t2 = int(self._t2 / speed)
        elapsed = self.get_elapsed()
        total = t0 + t1 + t2

        if elapsed > total:
            return 0.0
        if elapsed < t0:
            return elapsed / t0 if t0 > 0 else 1.0
        elif elapsed < t0 + t1:
            return 1.0
        else:
            return 1.0 - (elapsed - t1 - t0) / t2 if t2 > 0 else 0.0


class TrapeziumPulseAnimation:
    """Repeating trapezium pulse animation."""

    def __init__(
        self,
        t0: int = 0,
        t1: int = 1000,
        t2: int = 0,
        t3: int = 1000,
        t4: int = 0,
        speed_multiplier: float = 1.0,
    ):
        self._t0 = t0  # Initial delay
        self._t1 = t1  # Ramp up
        self._t2 = t2  # Hold
        self._t3 = t3  # Ramp down
        self._t4 = t4  # Final delay
        self.speed_multiplier = speed_multiplier
        self.start_time = millis()

    @property
    def interval(self) -> int:
        return int((self._t0 + self._t1 + self._t2 + self._t3 + self._t4) / max(0.1, self.speed_multiplier))

    def restart(self):
        self.start_time = millis()

    def get_elapsed(self) -> int:
        return millis() - self.start_time

    def get_value(self) -> float:
        if self.interval == 0:
            return 0.0

        speed = max(0.1, self.speed_multiplier)
        t0 = int(self._t0 / speed)
        t1 = int(self._t1 / speed)
        t2 = int(self._t2 / speed)
        t3 = int(self._t3 / speed)

        elapsed = self.get_elapsed() % self.interval

        if elapsed < t0:
            return 0.0
        if elapsed < t0 + t1:
            return (elapsed - t0) / t1 if t1 > 0 else 1.0
        elif elapsed < t0 + t1 + t2:
            return 1.0
        elif elapsed < t0 + t1 + t2 + t3:
            return 1.0 - (elapsed - t2 - t1 - t0) / t3 if t3 > 0 else 0.0
        return 0.0

    def set_triangle(self, t: int, delay: int):
        self._t0 = 0
        self._t1 = t // 2
        self._t2 = 0
        self._t3 = self._t1
        self._t4 = delay


class AsyncTimer:
    """Timer that fires periodically."""

    def __init__(self, interval: int):
        self._base_interval = interval
        self.speed_multiplier = 1.0
        self._start_time = 0
        self._is_active = False
        self._is_expired = False

    @property
    def interval(self) -> int:
        return int(self._base_interval / max(0.1, self.speed_multiplier))

    def start(self):
        self.reset()
        self._is_active = True

    def reset(self):
        self._start_time = millis()

    def stop(self):
        self._is_active = False

    def update(self) -> bool:
        if not self._is_active:
            return False

        self._is_expired = False
        if millis() - self._start_time >= self.interval:
            self._is_expired = True
            self.reset()
        return self._is_expired

    def is_expired(self) -> bool:
        return self._is_expired
