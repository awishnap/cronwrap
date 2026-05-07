"""Rate limiting for cron job executions."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting job executions."""

    max_runs: int = 0          # 0 means no limit
    window_seconds: int = 3600  # default: 1 hour window

    def __post_init__(self) -> None:
        if self.max_runs < 0:
            raise ValueError("max_runs must be >= 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

    @property
    def enabled(self) -> bool:
        return self.max_runs > 0


class RateLimitExceededError(Exception):
    """Raised when a job exceeds its configured rate limit."""

    def __init__(self, job_name: str, max_runs: int, window_seconds: int) -> None:
        self.job_name = job_name
        self.max_runs = max_runs
        self.window_seconds = window_seconds
        super().__init__(
            f"Job '{job_name}' exceeded rate limit of {max_runs} runs "
            f"per {window_seconds}s window."
        )


class RateLimiter:
    """Tracks and enforces execution rate limits for a named job."""

    def __init__(self, job_name: str, config: RateLimitConfig) -> None:
        self.job_name = job_name
        self.config = config
        self._timestamps: list[float] = []

    def _prune(self, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.config.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    def check(self, now: Optional[float] = None) -> None:
        """Raise RateLimitExceededError if the limit has been reached."""
        if not self.config.enabled:
            return
        now = now if now is not None else time.monotonic()
        self._prune(now)
        if len(self._timestamps) >= self.config.max_runs:
            raise RateLimitExceededError(
                self.job_name, self.config.max_runs, self.config.window_seconds
            )

    def record(self, now: Optional[float] = None) -> None:
        """Record a successful execution attempt."""
        now = now if now is not None else time.monotonic()
        self._timestamps.append(now)

    @property
    def run_count(self) -> int:
        """Number of runs recorded within the current window."""
        self._prune(time.monotonic())
        return len(self._timestamps)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RateLimiter(job={self.job_name!r}, "
            f"runs={self.run_count}/{self.config.max_runs}, "
            f"window={self.config.window_seconds}s)"
        )
