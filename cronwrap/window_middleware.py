"""Middleware that enforces execution windows before running a job."""
from __future__ import annotations

from datetime import time
from typing import Any, Callable, Optional

from cronwrap.window import WindowConfig, WindowGuard, WindowViolationError


class WindowMiddleware:
    """Wraps a callable and enforces time-window restrictions.

    If the current time is outside every configured window the callable is
    skipped and ``WindowViolationError`` is raised.  When the config is
    disabled or no windows are defined the callable is executed unconditionally.
    """

    def __init__(self, job_name: str, config: WindowConfig) -> None:
        self._job_name = job_name
        self._guard = WindowGuard(config)
        self._last_result: Optional[Any] = None
        self._skipped: bool = False

    @property
    def config(self) -> WindowConfig:
        return self._guard.config

    @property
    def last_result(self) -> Optional[Any]:
        return self._last_result

    @property
    def skipped(self) -> bool:
        return self._skipped

    def run(self, fn: Callable[[], Any], at: Optional[time] = None) -> Any:
        """Enforce the window and execute *fn* if allowed.

        Raises:
            WindowViolationError: when the current time is outside all windows.
        """
        self._skipped = False
        self._guard.enforce(self._job_name, at)
        self._last_result = fn()
        return self._last_result

    def dry_run(self, at: Optional[time] = None) -> dict:
        """Return a dict describing what would happen without executing."""
        return self._guard.dry_run(self._job_name, at)
