"""Middleware that wraps a callable with concurrency-limit enforcement."""
from __future__ import annotations

from typing import Any, Callable

from cronwrap.concurrency import ConcurrencyConfig, ConcurrencyManager


class ConcurrencyMiddleware:
    """Wraps a job callable, enforcing per-job concurrency limits.

    Usage::

        mw = ConcurrencyMiddleware(manager)
        mw.run("backup", do_backup)
    """

    def __init__(self, manager: ConcurrencyManager | None = None) -> None:
        self._manager = manager or ConcurrencyManager()

    def register(self, job_name: str, config: ConcurrencyConfig) -> None:
        """Register *job_name* with the given concurrency config."""
        self._manager.register(job_name, config)

    def run(self, job_name: str, fn: Callable[[], Any]) -> Any:
        """Acquire a slot, execute *fn*, then release the slot.

        Raises ConcurrencyLimitError if no slot is available.
        """
        self._manager.acquire(job_name)
        try:
            return fn()
        finally:
            self._manager.release(job_name)

    def dry_run(self, job_name: str) -> dict[str, Any]:
        """Return concurrency status for *job_name* without executing."""
        slots = self._manager.available_slots(job_name)
        config = self._manager._configs.get(job_name)
        return {
            "job_name": job_name,
            "enabled": config.enabled if config else False,
            "max_parallel": config.max_parallel if config else None,
            "available_slots": slots,
        }
