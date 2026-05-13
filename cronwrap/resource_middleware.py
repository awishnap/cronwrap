"""Middleware that wraps job execution with resource monitoring."""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from cronwrap.resource_monitor import ResourceMonitor, ResourceSummary


class ResourceMiddleware:
    """Runs a background polling thread while the job executes and
    exposes a :class:`ResourceSummary` after the run completes."""

    def __init__(
        self,
        job_name: str,
        pid: Optional[int] = None,
        poll_interval: float = 1.0,
    ) -> None:
        self._monitor = ResourceMonitor(job_name, pid=pid, interval=poll_interval)
        self._poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._summary: Optional[ResourceSummary] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, func: Callable, *args, **kwargs):
        """Execute *func* while polling resources in the background.

        Returns the return value of *func*.
        Raises any exception that *func* raises.
        """
        self._monitor.reset()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        try:
            return func(*args, **kwargs)
        finally:
            self._stop_event.set()
            self._thread.join(timeout=self._poll_interval * 2)
            self._summary = self._monitor.summary()

    def dry_run(self) -> dict:
        """Return configuration metadata without executing anything."""
        return {
            "middleware": "ResourceMiddleware",
            "job_name": self._monitor._job_name,
            "poll_interval": self._poll_interval,
        }

    @property
    def summary(self) -> Optional[ResourceSummary]:
        """Resource summary from the most recent :meth:`run` call."""
        return self._summary

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            self._monitor.poll()
            self._stop_event.wait(timeout=self._poll_interval)
