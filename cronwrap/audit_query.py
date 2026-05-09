"""Query helpers for the audit log."""
from __future__ import annotations

from typing import Callable, List, Optional

from cronwrap.audit import AuditEvent, AuditLog


class AuditQuery:
    """Fluent interface for filtering audit events."""

    def __init__(self, events: List[AuditEvent]) -> None:
        self._events = list(events)

    @classmethod
    def for_job(cls, audit_log: AuditLog, job_name: str) -> "AuditQuery":
        return cls(audit_log.get_events(job_name))

    def by_event_type(self, event_type: str) -> "AuditQuery":
        return AuditQuery([e for e in self._events if e.event_type == event_type])

    def failures(self) -> "AuditQuery":
        return self.by_event_type("failure")

    def successes(self) -> "AuditQuery":
        return self.by_event_type("success")

    def since(self, iso_timestamp: str) -> "AuditQuery":
        return AuditQuery([e for e in self._events if e.timestamp >= iso_timestamp])

    def where(self, predicate: Callable[[AuditEvent], bool]) -> "AuditQuery":
        return AuditQuery([e for e in self._events if predicate(e)])

    def latest(self, n: int = 1) -> List[AuditEvent]:
        return self._events[-n:]

    def count(self) -> int:
        return len(self._events)

    def all(self) -> List[AuditEvent]:
        return list(self._events)

    def average_duration(self) -> Optional[float]:
        durations = [
            e.duration_seconds
            for e in self._events
            if e.duration_seconds is not None
        ]
        if not durations:
            return None
        return sum(durations) / len(durations)

    def consecutive_failures(self) -> int:
        """Count trailing consecutive failure events."""
        count = 0
        for event in reversed(self._events):
            if event.event_type == "failure":
                count += 1
            else:
                break
        return count
