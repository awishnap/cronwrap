"""Middleware that redacts sensitive output before it is stored or forwarded."""
from __future__ import annotations

from typing import Callable

from cronwrap.redact import RedactConfig, Redactor


class RedactMiddleware:
    """Wraps a callable and redacts its stdout/stderr captured output.

    The middleware itself does not capture output — it post-processes
    plain-text strings produced by other layers (e.g. OutputCapture).
    """

    def __init__(self, config: RedactConfig | None = None) -> None:
        self._redactor = Redactor(config)
        self._last_redacted: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, fn: Callable[[], str]) -> str:
        """Execute *fn*, redact its return value, and cache the result."""
        raw = fn()
        redacted = self._redactor.redact(raw)
        self._last_redacted = redacted
        return redacted

    def clean(self, text: str) -> str:
        """Convenience method — redact *text* without executing a callable."""
        return self._redactor.redact(text)

    def clean_dict(self, data: dict) -> dict:
        """Convenience method — redact sensitive values in *data*."""
        return self._redactor.redact_dict(data)

    @property
    def last_redacted(self) -> str | None:
        """The most recently redacted string, or *None* if *run* was never called."""
        return self._last_redacted

    @property
    def config(self) -> RedactConfig:
        return self._redactor.config
