"""Middleware that integrates Debouncer into the cronwrap execution pipeline."""

from __future__ import annotations

from cronwrap.debounce import DebounceConfig, Debouncer, DebounceError


class DebounceMiddleware:
    """Wraps a callable with debounce checking and state recording."""

    def __init__(self, job_name: str, config: DebounceConfig) -> None:
        self.job_name = job_name
        self.config = config
        self._debouncer = Debouncer(config)

    def run(self, func, *args, **kwargs):
        """Check cooldown, run *func*, then record the run timestamp.

        Raises DebounceError without calling *func* if still in cooldown.
        Returns whatever *func* returns on success.
        """
        self._debouncer.check(self.job_name)
        try:
            result = func(*args, **kwargs)
        finally:
            # Record even on exception so a crashing job still resets the window.
            self._debouncer.record(self.job_name)
        return result

    def dry_run(self) -> dict:
        """Return debounce state without executing anything."""
        from pathlib import Path
        import time

        last = self._debouncer._last_run(self.job_name)
        if last is None or not self.config.enabled:
            remaining = 0.0
            blocked = False
        else:
            elapsed = time.monotonic() - last
            remaining = max(0.0, self.config.cooldown_seconds - elapsed)
            blocked = remaining > 0

        return {
            "job_name": self.job_name,
            "cooldown_seconds": self.config.cooldown_seconds,
            "enabled": self.config.enabled,
            "blocked": blocked,
            "remaining_seconds": round(remaining, 2),
        }

    def reset(self) -> None:
        """Manually clear the debounce state for this job."""
        self._debouncer.reset(self.job_name)
