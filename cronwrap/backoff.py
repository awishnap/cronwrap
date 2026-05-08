"""Backoff strategies for retry delays."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

BackoffStrategy = Literal["fixed", "linear", "exponential", "jitter"]


@dataclass
class BackoffConfig:
    """Configuration for retry backoff behaviour."""

    strategy: BackoffStrategy = "fixed"
    base_delay: float = 1.0
    max_delay: float = 300.0
    multiplier: float = 2.0
    jitter_range: float = 0.5

    _VALID_STRATEGIES: tuple[str, ...] = field(
        default=("fixed", "linear", "exponential", "jitter"),
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.strategy not in self._VALID_STRATEGIES:
            raise ValueError(
                f"strategy must be one of {self._VALID_STRATEGIES}, got {self.strategy!r}"
            )
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.multiplier <= 0:
            raise ValueError("multiplier must be > 0")
        if not (0.0 <= self.jitter_range <= 1.0):
            raise ValueError("jitter_range must be between 0.0 and 1.0")


class BackoffCalculator:
    """Computes the delay before a retry attempt given a BackoffConfig."""

    def __init__(self, config: BackoffConfig) -> None:
        self._cfg = config

    def delay_for(self, attempt: int) -> float:
        """Return the delay in seconds for *attempt* (1-based).

        :param attempt: The attempt number that just failed (>= 1).
        :returns: Seconds to wait before the next attempt.
        """
        if attempt < 1:
            raise ValueError("attempt must be >= 1")

        cfg = self._cfg
        strategy = cfg.strategy

        if strategy == "fixed":
            delay = cfg.base_delay
        elif strategy == "linear":
            delay = cfg.base_delay * attempt
        elif strategy == "exponential":
            delay = cfg.base_delay * (cfg.multiplier ** (attempt - 1))
        elif strategy == "jitter":
            base = cfg.base_delay * (cfg.multiplier ** (attempt - 1))
            spread = base * cfg.jitter_range
            delay = base + random.uniform(-spread, spread)
        else:  # pragma: no cover
            delay = cfg.base_delay

        return max(0.0, min(delay, cfg.max_delay))

    def __repr__(self) -> str:  # pragma: no cover
        return f"BackoffCalculator(config={self._cfg!r})"
