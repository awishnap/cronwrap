"""Execution sampling — run a job only a fraction of the time."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


class SamplingError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class SamplingConfig:
    """Configuration for probabilistic job sampling."""

    rate: float = 1.0          # 0.0 – 1.0; 1.0 means always run
    seed: int | None = None    # optional RNG seed for reproducibility

    def __post_init__(self) -> None:
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError(
                f"rate must be between 0.0 and 1.0, got {self.rate!r}"
            )

    @property
    def enabled(self) -> bool:
        """Sampling is active only when rate is below 1.0."""
        return self.rate < 1.0


class SamplingMiddleware:
    """Wraps a callable and skips execution based on the sampling rate."""

    def __init__(self, config: SamplingConfig) -> None:
        self._config = config
        self._rng = random.Random(config.seed)
        self._last_skipped: bool = False

    @property
    def config(self) -> SamplingConfig:
        return self._config

    @property
    def last_skipped(self) -> bool:
        """True if the most recent call to run() was skipped."""
        return self._last_skipped

    def run(self, fn, *args, **kwargs):
        """Execute *fn* unless the sample roll says to skip."""
        if self._config.enabled and self._rng.random() >= self._config.rate:
            self._last_skipped = True
            return None
        self._last_skipped = False
        return fn(*args, **kwargs)

    def dry_run(self) -> dict:
        """Return sampling configuration without executing anything."""
        return {
            "rate": self._config.rate,
            "enabled": self._config.enabled,
            "seed": self._config.seed,
        }
