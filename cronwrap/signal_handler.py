"""Graceful shutdown support via OS signal handling for cron jobs."""

from __future__ import annotations

import signal
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SignalConfig:
    """Configuration for signal handling behaviour."""

    handle_sigterm: bool = True
    handle_sigint: bool = True
    propagate_to_child: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.handle_sigterm, bool):
            raise TypeError("handle_sigterm must be a bool")
        if not isinstance(self.handle_sigint, bool):
            raise TypeError("handle_sigint must be a bool")
        if not isinstance(self.propagate_to_child, bool):
            raise TypeError("propagate_to_child must be a bool")


class ShutdownRequestedError(Exception):
    """Raised when a termination signal is received during job execution."""

    def __init__(self, sig: int) -> None:
        self.sig = sig
        super().__init__(f"Shutdown requested via signal {sig}")


class SignalHandler:
    """Registers OS signal handlers and tracks shutdown state."""

    def __init__(self, config: Optional[SignalConfig] = None) -> None:
        self.config = config or SignalConfig()
        self._shutdown_requested: bool = False
        self._received_signal: Optional[int] = None
        self._previous_handlers: dict = {}
        self._callbacks: List[Callable[[int], None]] = []

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    @property
    def received_signal(self) -> Optional[int]:
        return self._received_signal

    def add_callback(self, fn: Callable[[int], None]) -> None:
        """Register a callback invoked when a signal is received."""
        self._callbacks.append(fn)

    def register(self) -> None:
        """Install signal handlers according to config."""
        if self.config.handle_sigterm:
            self._previous_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM, self._handle
            )
        if self.config.handle_sigint:
            self._previous_handlers[signal.SIGINT] = signal.signal(
                signal.SIGINT, self._handle
            )
        logger.debug("Signal handlers registered: %s", list(self._previous_handlers))

    def restore(self) -> None:
        """Restore previously installed signal handlers."""
        for sig, handler in self._previous_handlers.items():
            signal.signal(sig, handler)
        self._previous_handlers.clear()
        logger.debug("Signal handlers restored")

    def _handle(self, sig: int, _frame: object) -> None:
        logger.warning("Signal %d received — requesting shutdown", sig)
        self._shutdown_requested = True
        self._received_signal = sig
        for cb in self._callbacks:
            try:
                cb(sig)
            except Exception as exc:  # pragma: no cover
                logger.error("Signal callback raised: %s", exc)

    def raise_if_shutdown(self) -> None:
        """Raise ShutdownRequestedError if a signal has been received."""
        if self._shutdown_requested:
            raise ShutdownRequestedError(self._received_signal)  # type: ignore[arg-type]

    def __enter__(self) -> "SignalHandler":
        self.register()
        return self

    def __exit__(self, *_: object) -> None:
        self.restore()
