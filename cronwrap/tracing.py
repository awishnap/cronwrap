"""Lightweight tracing support for cron job execution spans."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TracingConfig:
    enabled: bool = True
    service_name: str = "cronwrap"
    max_spans: int = 1000

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not self.service_name or not self.service_name.strip():
            raise ValueError("service_name must not be blank")
        if self.max_spans < 1:
            raise ValueError("max_spans must be at least 1")


@dataclass
class Span:
    trace_id: str
    span_id: str
    job_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def finished(self) -> bool:
        return self.end_time is not None

    def finish(self, error: Optional[str] = None) -> None:
        self.end_time = time.monotonic()
        if error is not None:
            self.error = error

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "job_name": self.job_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "tags": self.tags,
            "error": self.error,
        }


class Tracer:
    def __init__(self, config: Optional[TracingConfig] = None) -> None:
        self._config = config or TracingConfig()
        self._spans: List[Span] = []

    @property
    def config(self) -> TracingConfig:
        return self._config

    def start_span(self, job_name: str, tags: Optional[Dict[str, str]] = None) -> Optional[Span]:
        if not self._config.enabled:
            return None
        span = Span(
            trace_id=uuid.uuid4().hex,
            span_id=uuid.uuid4().hex,
            job_name=job_name,
            start_time=time.monotonic(),
            tags=dict(tags or {}),
        )
        if len(self._spans) >= self._config.max_spans:
            self._spans.pop(0)
        self._spans.append(span)
        return span

    def spans(self) -> List[Span]:
        return list(self._spans)

    def spans_for_job(self, job_name: str) -> List[Span]:
        return [s for s in self._spans if s.job_name == job_name]

    def clear(self) -> None:
        self._spans.clear()
