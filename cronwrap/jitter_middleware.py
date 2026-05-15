"""Middleware that wraps a callable with jitter delay."""

from __future__ import annotations

from typing import Callable, Optional

from .jitter import JitterConfig, JitterManager


class JitterMiddleware:
    """Injects a random delay before executing a job function.

    Useful for staggering cron jobs that run on many hosts simultaneously.
    """

    def __init__(self, config: Optional[JitterConfig] = None) -> None:
        self._config = config or JitterConfig()
        self._manager = JitterManager(self._config)

    def run(self, fn: Callable[[], object]) -> object:
        """Apply jitter delay then execute *fn*, returning its result."""
        return self._manager.run(fn)

    def dry_run(self) -> dict:
        """Return metadata about the jitter that would be applied."""
        delay = self._manager.dry_run()
        return {
            "enabled": self._config.enabled,
            "strategy": self._config.strategy,
            "max_seconds": self._config.max_seconds,
            "sampled_delay": delay,
        }

    @property
    def config(self) -> JitterConfig:
        return self._config
