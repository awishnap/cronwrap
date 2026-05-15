"""Middleware that wraps a callable with cooldown enforcement."""
from __future__ import annotations

from typing import Any, Callable

from cronwrap.cooldown import CooldownConfig, CooldownManager


class CooldownMiddleware:
    """Enforce a minimum gap between successive executions of a job.

    Usage::

        cfg = CooldownConfig(seconds=300, state_dir="/var/run/cronwrap/cd")
        mw  = CooldownMiddleware("my_job", cfg)
        mw.run(my_callable)
    """

    def __init__(self, job_name: str, config: CooldownConfig) -> None:
        self._job_name = job_name
        self._manager = CooldownManager(config)

    def run(self, fn: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        """Check cooldown, execute *fn*, then record the run timestamp."""
        self._manager.check(self._job_name)
        try:
            result = fn(*args, **kwargs)
        finally:
            self._manager.record(self._job_name)
        return result

    def dry_run(self) -> dict[str, Any]:
        """Return cooldown status without executing or mutating state."""
        remaining = self._manager.remaining(self._job_name)
        return {
            "job_name": self._job_name,
            "in_cooldown": remaining > 0,
            "remaining_seconds": round(remaining, 2),
        }

    def reset(self) -> None:
        """Clear the cooldown state so the job may run immediately."""
        self._manager.reset(self._job_name)
