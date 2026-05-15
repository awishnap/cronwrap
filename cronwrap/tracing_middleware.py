"""Middleware that wraps a callable in a tracing span."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwrap.tracing import Span, Tracer, TracingConfig


class TracingMiddleware:
    """Wraps job execution in a tracing span.

    Example::

        mw = TracingMiddleware(job_name="backup", tracer=tracer)
        result = mw.run(lambda: do_backup())
    """

    def __init__(
        self,
        job_name: str,
        tracer: Optional[Tracer] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        if not job_name or not job_name.strip():
            raise ValueError("job_name must not be blank")
        self._job_name = job_name
        self._tracer = tracer or Tracer()
        self._tags = tags or {}
        self._last_span: Optional[Span] = None

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    @property
    def last_span(self) -> Optional[Span]:
        return self._last_span

    def run(self, fn: Callable[[], Any]) -> Any:
        """Execute *fn* inside a span; finish the span whether or not fn raises."""
        span = self._tracer.start_span(self._job_name, tags=self._tags)
        self._last_span = span
        try:
            result = fn()
        except Exception as exc:
            if span is not None:
                span.finish(error=str(exc))
            raise
        else:
            if span is not None:
                span.finish()
            return result

    def dry_run(self) -> Optional[Span]:
        """Start and immediately finish a span without executing any work."""
        span = self._tracer.start_span(self._job_name, tags={**self._tags, "dry_run": "true"})
        if span is not None:
            span.finish()
        self._last_span = span
        return span
