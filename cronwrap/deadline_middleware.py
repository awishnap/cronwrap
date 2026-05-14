"""Middleware that integrates DeadlineTracker into the job execution lifecycle."""
from __future__ import annotations

from typing import Callable, Optional

from cronwrap.deadline import DeadlineConfig, DeadlineExceededError, DeadlineTracker


class DeadlineMiddleware:
    """Wraps a callable with deadline enforcement."""

    def __init__(self, job_name: str, config: Optional[DeadlineConfig] = None) -> None:
        self._job_name = job_name
        self._config = config or DeadlineConfig()
        self._tracker = DeadlineTracker(job_name, self._config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, func: Callable[[], int]) -> int:
        """Execute *func* and enforce the deadline.  Returns the exit code."""
        self._tracker.start()
        try:
            result = func()
            self._tracker.check()
            return result
        except DeadlineExceededError:
            raise
        except Exception:
            # Still check deadline even when the wrapped function itself fails.
            self._tracker.check()
            raise

    def dry_run(self) -> dict:
        """Return metadata about the deadline configuration without running anything."""
        return {
            "job_name": self._job_name,
            "enabled": self._config.enabled,
            "max_runtime_seconds": self._config.max_runtime_seconds,
            "strict": self._config.strict,
        }

    @property
    def tracker(self) -> DeadlineTracker:
        """Expose the underlying tracker for inspection after execution."""
        return self._tracker
