"""Deadline enforcement for cron jobs — hard wall-clock cutoff distinct from per-attempt timeout."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class DeadlineExceededError(Exception):
    """Raised when a job runs past its absolute deadline."""

    def __init__(self, job_name: str, deadline: datetime) -> None:
        self.job_name = job_name
        self.deadline = deadline
        super().__init__(
            f"Job '{job_name}' exceeded deadline {deadline.isoformat()}"
        )


@dataclass
class DeadlineConfig:
    """Configuration for absolute deadline enforcement."""

    # Maximum wall-clock seconds the entire job (including retries) may run.
    # 0 means no deadline.
    max_runtime_seconds: int = 0
    # Whether to raise immediately or just record the breach.
    strict: bool = True

    def __post_init__(self) -> None:
        if self.max_runtime_seconds < 0:
            raise ValueError("max_runtime_seconds must be >= 0")
        if not isinstance(self.strict, bool):
            raise TypeError("strict must be a bool")

    @property
    def enabled(self) -> bool:
        return self.max_runtime_seconds > 0


class DeadlineTracker:
    """Tracks an absolute deadline for a running job."""

    def __init__(self, job_name: str, config: DeadlineConfig) -> None:
        self._job_name = job_name
        self._config = config
        self._start: Optional[float] = None
        self.breached: bool = False

    def start(self) -> None:
        """Record the start time."""
        self._start = time.monotonic()

    def elapsed_seconds(self) -> float:
        """Return seconds elapsed since start, or 0 if not started."""
        if self._start is None:
            return 0.0
        return time.monotonic() - self._start

    def remaining_seconds(self) -> Optional[float]:
        """Seconds until deadline, or None if disabled."""
        if not self._config.enabled:
            return None
        return max(0.0, self._config.max_runtime_seconds - self.elapsed_seconds())

    def check(self) -> None:
        """Raise DeadlineExceededError (if strict) or set breached flag when past deadline."""
        if not self._config.enabled or self._start is None:
            return
        if self.elapsed_seconds() >= self._config.max_runtime_seconds:
            self.breached = True
            if self._config.strict:
                raise DeadlineExceededError(
                    self._job_name,
                    datetime.now(timezone.utc),
                )

    def reset(self) -> None:
        """Reset the tracker to its initial state, clearing start time and breach flag.

        Useful when re-running a job under the same tracker instance without
        creating a new one (e.g. in test harnesses or job schedulers).
        """
        self._start = None
        self.breached = False

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DeadlineTracker(job={self._job_name!r}, "
            f"max={self._config.max_runtime_seconds}s, "
            f"elapsed={self.elapsed_seconds():.1f}s)"
        )
