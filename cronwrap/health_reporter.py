"""Formats and serialises HealthStatus for reporting."""
from __future__ import annotations

from typing import Any, Dict, List

from cronwrap.health import HealthStatus


class HealthReport:
    """Aggregates multiple HealthStatus objects into a single report."""

    def __init__(self, statuses: List[HealthStatus]) -> None:
        self.statuses = statuses

    @property
    def all_healthy(self) -> bool:
        return all(s.is_healthy for s in self.statuses)

    @property
    def unhealthy(self) -> List[HealthStatus]:
        return [s for s in self.statuses if not s.is_healthy]

    def summary(self) -> str:
        total = len(self.statuses)
        bad = len(self.unhealthy)
        if bad == 0:
            return f"All {total} job(s) healthy."
        names = ", ".join(s.job_name for s in self.unhealthy)
        return f"{bad}/{total} job(s) unhealthy: {names}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_healthy": self.all_healthy,
            "total": len(self.statuses),
            "unhealthy_count": len(self.unhealthy),
            "jobs": [_status_to_dict(s) for s in self.statuses],
        }


class HealthReporter:
    """Builds HealthReport objects from collected statuses."""

    def __init__(self) -> None:
        self._statuses: List[HealthStatus] = []

    def add(self, status: HealthStatus) -> None:
        """Register a HealthStatus for inclusion in the next report."""
        self._statuses.append(status)

    def report(self) -> HealthReport:
        """Return a snapshot report of all registered statuses."""
        return HealthReport(list(self._statuses))

    def clear(self) -> None:
        """Reset collected statuses."""
        self._statuses.clear()


def _status_to_dict(status: HealthStatus) -> Dict[str, Any]:
    return {
        "job_name": status.job_name,
        "is_healthy": status.is_healthy,
        "failure_streak": status.failure_streak,
        "last_run": status.last_run.isoformat() if status.last_run else None,
        "last_success": status.last_success.isoformat() if status.last_success else None,
        "details": status.details,
    }
