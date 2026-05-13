"""Middleware that wraps job execution with graceful shutdown via SignalHandler."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from cronwrap.signal_handler import SignalConfig, SignalHandler, ShutdownRequestedError

logger = logging.getLogger(__name__)


class SignalMiddleware:
    """Wraps a callable with signal-aware lifecycle management.

    Usage::

        middleware = SignalMiddleware(job_name="backup")
        result = middleware.run(my_job_fn)
    """

    def __init__(
        self,
        job_name: str,
        config: Optional[SignalConfig] = None,
        on_shutdown: Optional[Callable[[int], None]] = None,
    ) -> None:
        if not job_name or not job_name.strip():
            raise ValueError("job_name must not be blank")
        self.job_name = job_name.strip()
        self.config = config or SignalConfig()
        self._on_shutdown = on_shutdown
        self._handler = SignalHandler(config=self.config)
        if on_shutdown is not None:
            self._handler.add_callback(on_shutdown)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, fn: Callable[[], None]) -> bool:
        """Execute *fn* inside a signal-guarded context.

        Returns True on clean completion, False when a shutdown signal
        interrupted execution.
        """
        logger.debug("[%s] SignalMiddleware: registering handlers", self.job_name)
        with self._handler:
            try:
                fn()
                self._handler.raise_if_shutdown()
                logger.debug("[%s] SignalMiddleware: completed cleanly", self.job_name)
                return True
            except ShutdownRequestedError as exc:
                logger.warning(
                    "[%s] SignalMiddleware: job interrupted by signal %d",
                    self.job_name,
                    exc.sig,
                )
                return False

    def dry_run(self) -> dict:
        """Return configuration summary without executing anything."""
        return {
            "job_name": self.job_name,
            "handle_sigterm": self.config.handle_sigterm,
            "handle_sigint": self.config.handle_sigint,
            "propagate_to_child": self.config.propagate_to_child,
            "has_shutdown_callback": self._on_shutdown is not None,
        }
