"""Jitter support for cron job scheduling to avoid thundering herd problems."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class JitterConfig:
    """Configuration for execution jitter."""

    max_seconds: float = 0.0
    strategy: str = "uniform"  # uniform | gaussian
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.max_seconds < 0:
            raise ValueError("max_seconds must be >= 0")
        valid = {"uniform", "gaussian"}
        if self.strategy not in valid:
            raise ValueError(f"strategy must be one of {valid}, got {self.strategy!r}")

    @property
    def enabled(self) -> bool:
        return self.max_seconds > 0


class JitterError(Exception):
    """Raised when jitter application fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class JitterManager:
    """Applies randomised delay before executing a callable."""

    def __init__(
        self,
        config: JitterConfig,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._sleep = sleep_fn
        self._rng = random.Random(config.seed)

    def delay(self) -> float:
        """Return the computed jitter delay in seconds (0 if disabled)."""
        if not self._config.enabled:
            return 0.0
        if self._config.strategy == "uniform":
            return self._rng.uniform(0, self._config.max_seconds)
        # gaussian: mu=0, sigma=max_seconds/3 clamped to [0, max_seconds]
        value = self._rng.gauss(0, self._config.max_seconds / 3)
        return max(0.0, min(self._config.max_seconds, value))

    def run(self, fn: Callable[[], object]) -> object:
        """Sleep for the jitter delay then call *fn*."""
        seconds = self.delay()
        if seconds > 0:
            self._sleep(seconds)
        return fn()

    def dry_run(self) -> float:
        """Return the delay that *would* be applied without sleeping."""
        return self.delay()
